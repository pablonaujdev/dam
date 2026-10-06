"""Audit local addon mappings and optional database metadata with SELECT only.

This tool does not rename, merge, install, update, or uninstall modules.
Its JSON output is a review input for the migration of a separate MIAC copy.
"""

import argparse
import ast
import csv
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "MIAC_MODULE_MAPPING_19.json"
SOURCE_ADDONS = Path(r"C:\Proyectos FL\DAM\respaldo\addons")
ODOO_SERVER = Path(r"C:\Program Files\Odoo 19.0e.20260105\server")


def load_manifest(folder):
    return ast.literal_eval((folder / "__manifest__.py").read_text(encoding="utf-8-sig"))


def declared_xmlids(folder, manifest):
    """Only data IDs: HTML element IDs inside view architectures are excluded."""
    result = set()
    for relative in manifest.get("data", []):
        path = folder / relative
        if path.suffix == ".xml":
            root = ET.parse(path).getroot()
            for node in root.iter():
                if node.tag in {"record", "template", "menuitem", "report", "act_window"}:
                    if xmlid := node.get("id"):
                        result.add(xmlid.split(".", 1)[-1])
        elif path.suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                result.update(row["id"] for row in csv.DictReader(stream) if row.get("id"))
    return result


def legacy_references(folder, manifest, obsolete):
    """Inspect dependency names and explicit XML-ID lookups, not model names."""
    found = []
    for dependency in manifest.get("depends", []):
        if dependency in obsolete:
            found.append({"file": "__manifest__.py", "reference": dependency})
    for path in sorted(folder.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"ref", "_xmlid_lookup", "_xmlid_to_res_id", "_xmlid_to_res_model_res_id"}:
                continue
            for argument in node.args[:1]:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    if argument.value.split(".", 1)[0] in obsolete:
                        found.append({"file": path.relative_to(folder).as_posix(), "line": node.lineno, "reference": argument.value})
    for relative in manifest.get("data", []) + manifest.get("demo", []):
        path = folder / relative
        if path.suffix == ".xml":
            for node in ET.parse(path).iter():
                for name, value in node.attrib.items():
                    references = []
                    if name in {"ref", "t-call", "inherit_id", "groups", "id"}:
                        references.extend(value.split(","))
                    references.extend(re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", value))
                    references.extend(re.findall(r"%\(([^)]+)\)[ds]", value))
                    for reference in references:
                        reference = reference.strip().lstrip("!")
                        if reference.split(".", 1)[0] in obsolete:
                            found.append({"file": relative, "reference": reference})
        elif path.suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    for key, value in row.items():
                        if key and key.endswith(":id") and value and value.split(".", 1)[0] in obsolete:
                            found.append({"file": relative, "reference": value})
    return found


def inspect_sources(plan, repo, backup, server):
    changes = plan["module_changes"]
    by_target = {change["target"]: change for change in changes if change["kind"] == "rename"}
    obsolete = {change["source"] for change in changes}
    inventory, errors, mapping_evidence = [], [], []
    dependencies = {}

    def visit(module, ancestry=()):
        if module in ancestry:
            raise ValueError("Dependency cycle: " + " -> ".join((*ancestry, module)))
        if module in dependencies:
            return
        folder = repo / module
        is_repo = (folder / "__manifest__.py").is_file()
        if not is_repo:
            folder = server / "odoo" / "addons" / module
        if not (folder / "__manifest__.py").is_file():
            raise ValueError("Missing dependency: " + module)
        manifest = load_manifest(folder)
        if not manifest.get("installable", True):
            raise ValueError("Non-installable dependency: " + module)
        if is_repo and not str(manifest.get("version", "")).startswith("19.0."):
            raise ValueError("Repository dependency is not V19: " + module)
        for dependency in manifest.get("depends", []):
            visit(dependency, (*ancestry, module))
        dependencies[module] = str(folder)

    for folder in sorted(repo.iterdir()):
        if not (folder / "__manifest__.py").is_file():
            continue
        manifest = load_manifest(folder)
        if not str(manifest.get("version", "")).startswith("19.0."):
            continue
        change = by_target.get(folder.name)
        source_name = change["source"] if change else folder.name
        source_folder = backup / source_name
        source_available = (source_folder / "__manifest__.py").is_file()
        entry = {"module": folder.name, "version": manifest["version"], "source_module": source_name,
                 "source_available_in_backup": source_available, "dependencies": manifest.get("depends", []),
                 "legacy_references": legacy_references(folder, manifest, obsolete)}
        if source_available:
            entry["source_version"] = load_manifest(source_folder).get("version")
        if entry["legacy_references"]:
            errors.append({"module": folder.name, "problem": "legacy_module_references"})
        try:
            visit(folder.name)
        except ValueError as error:
            errors.append({"module": folder.name, "problem": str(error)})
        inventory.append(entry)
    for change in changes:
        source = backup / change["source"]
        target = repo / change["target"]
        if not (target / "__manifest__.py").is_file():
            target = server / "odoo" / "addons" / change["target"]
        old_ids = declared_xmlids(source, load_manifest(source))
        new_ids = declared_xmlids(target, load_manifest(target))
        missing = sorted(old_ids - new_ids)
        mapping_evidence.append({**change, "source_declared_ids": len(old_ids), "shared_declared_ids": len(old_ids & new_ids),
                                 "source_ids_absent_in_target": missing})
        if change["kind"] in {"rename", "merge"} and missing:
            errors.append({"module": change["target"], "problem": "source_xmlids_need_individual_mapping", "xmlids": missing})
    return {"scope": "V19 addons present in repository; no claim about the full MIAC inventory",
            "module_count": len(inventory), "dependency_closure_count": len(dependencies),
            "modules": inventory, "mapping_evidence": mapping_evidence, "errors": errors}


def mapping_status(change, source, target, source_ids, collisions):
    if collisions:
        return "conflicting_xmlids_require_review"
    if source and source["state"] in {"installed", "to upgrade", "to remove"}:
        if str(source.get("latest_version") or "").startswith("19.0") and change["kind"] == "rename":
            return "source_identity_requires_review"
        if change["kind"] == "rename" and target:
            return "rename_requires_target_metadata_review"
        return change["kind"] + "_pending"
    if source_ids:
        return "legacy_namespace_requires_review"
    if target and target["state"] == "installed":
        return "target_installed_no_legacy_evidence_not_proof_of_data_migration"
    return "not_installed_in_this_database"


def inspect_database(connection, plan):
    """No ORM or migration library: the connection must reject database writes."""
    from psycopg2 import sql

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_setting('transaction_read_only')")
        database, readonly = cursor.fetchone()
        if readonly != "on":
            raise RuntimeError("A READ ONLY transaction is required")
        names = sorted({entry[key] for entry in plan["module_changes"] for key in ("source", "target")})
        cursor.execute("SELECT id, name, state, latest_version FROM ir_module_module WHERE name = ANY(%s)", (names,))
        modules = {name: {"id": module_id, "name": name, "state": state, "latest_version": version}
                   for module_id, name, state, version in cursor.fetchall()}
        cursor.execute("SELECT module, COUNT(*) FROM ir_model_data WHERE module = ANY(%s) GROUP BY module", (names,))
        counts = dict(cursor.fetchall())
        mappings = []
        for change in plan["module_changes"]:
            old, new = change["source"], change["target"]
            cursor.execute("""SELECT old.name, old.model, old.res_id, new.model, new.res_id
                FROM ir_model_data old JOIN ir_model_data new ON new.name=old.name
                WHERE old.module=%s AND new.module=%s AND (old.model,old.res_id)<>(new.model,new.res_id)
                ORDER BY old.name""", (old, new))
            collisions = cursor.fetchall()
            cursor.execute("""SELECT owner.name, owner.state FROM ir_module_module_dependency dep
                JOIN ir_module_module owner ON owner.id=dep.module_id
                WHERE dep.name=%s AND owner.state IN ('installed','to upgrade','to install') ORDER BY owner.name""", (old,))
            dependencies = cursor.fetchall()
            cursor.execute("SELECT id, key, active FROM ir_ui_view WHERE key LIKE %s ORDER BY id", (old + ".%",))
            view_keys = cursor.fetchall()
            source, target = modules.get(old), modules.get(new)
            mappings.append({**change, "source_module": source, "target_module": target,
                             "source_xmlid_count": counts.get(old, 0), "target_xmlid_count": counts.get(new, 0),
                             "conflicting_xmlids": collisions, "active_module_dependencies_on_source": dependencies,
                             "legacy_view_keys": view_keys,
                             "status": mapping_status(change, source, target, counts.get(old, 0), collisions)})
        cursor.execute("""SELECT f.model, f.name, f.ttype, f.relation,
                ARRAY(SELECT DISTINCT d.module FROM ir_model_data d
                      WHERE d.model='ir.model.fields' AND d.res_id=f.id ORDER BY d.module)
            FROM ir_model_fields f
            WHERE (f.model='res.partner' AND f.name IN ('agent_ids','commission_agent_ids','customer_payment_mode_id','supplier_payment_mode_id','agent_type','employee'))
               OR (f.model IN ('account.move','sale.order') AND f.name='payment_mode_id')
            ORDER BY f.model,f.name""")
        fields = cursor.fetchall()
        cursor.execute("""SELECT table_name,column_name,data_type FROM information_schema.columns
            WHERE table_schema='public' AND table_name='res_partner'
              AND column_name IN ('customer_payment_mode_id','supplier_payment_mode_id') ORDER BY column_name""")
        company_payment_storage = cursor.fetchall()
        data_counts = {}
        for table in ("commission", "commission_section", "commission_settlement", "commission_settlement_line",
                      "sale_order_line_agent", "account_invoice_line_agent", "partner_agent_rel", "account_payment_mode"):
            cursor.execute("SELECT to_regclass(%s)", (table,))
            if cursor.fetchone()[0]:
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                data_counts[table] = cursor.fetchone()[0]
        relation_fingerprint = None
        if "partner_agent_rel" in data_counts:
            cursor.execute("""SELECT md5(COALESCE(string_agg(partner_id::text||':'||agent_id::text,',' ORDER BY partner_id,agent_id),''))
                FROM partner_agent_rel""")
            relation_fingerprint = cursor.fetchone()[0]
        cursor.execute("SELECT to_regclass('ir_property')")
        payment_properties = []
        if cursor.fetchone()[0]:
            cursor.execute("""SELECT f.name,p.company_id,COUNT(*) FROM ir_property p
                JOIN ir_model_fields f ON f.id=p.fields_id
                WHERE f.model='res.partner' AND f.name IN ('customer_payment_mode_id','supplier_payment_mode_id')
                GROUP BY f.name,p.company_id ORDER BY f.name,p.company_id""")
            payment_properties = cursor.fetchall()
    return {"database": database, "read_only": readonly, "mappings": mappings, "field_metadata": fields,
            "company_payment_storage": company_payment_storage, "legacy_payment_properties_by_company": payment_properties,
            "data_counts": data_counts, "partner_agent_pairs_md5": relation_fingerprint,
            "acceptance": "Metadata audit only; no data migration or functional acceptance performed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--source-addons", type=Path, default=SOURCE_ADDONS)
    parser.add_argument("--odoo-server", type=Path, default=ODOO_SERVER)
    parser.add_argument("--database-only", action="store_true")
    parser.add_argument("--database")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="openpg")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.database_only and not args.database:
        parser.error("--database-only requires --database")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "policy": plan["execution_policy"]}
    if not args.database_only:
        report["sources"] = inspect_sources(plan, args.repo, args.source_addons, args.odoo_server)
    if args.database:
        import psycopg2

        password = os.environ.get("MIAC_PREFLIGHT_PASSWORD") or getpass.getpass("Password (not stored): ")
        connection = psycopg2.connect(host=args.host, port=args.port, dbname=args.database, user=args.user,
                                     password=password, connect_timeout=10,
                                     options="-c default_transaction_read_only=on -c statement_timeout=60000")
        try:
            connection.set_session(readonly=True, autocommit=False)
            report["database"] = inspect_database(connection, plan)
            connection.rollback()
        finally:
            connection.close()
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    errors = report.get("sources", {}).get("errors", [])
    print(json.dumps({"output": str(args.output), "source_modules": report.get("sources", {}).get("module_count"),
                      "source_errors": len(errors), "database_read_only": report.get("database", {}).get("read_only")}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
