"""Tests for migration classification and source references; no database writes."""

from pathlib import Path
import tempfile
import unittest

from preflight_module_mapping19 import declared_xmlids, inspect_database, legacy_references, mapping_status


class ModuleMappingTests(unittest.TestCase):
    def test_rename_keeps_existing_module_pending(self):
        old = {"state": "installed", "latest_version": "17.0.1.0.0"}
        self.assertEqual(mapping_status({"kind": "rename"}, old, None, 2, []), "rename_pending")

    def test_existing_destination_requires_review_even_if_uninstalled(self):
        old = {"state": "installed", "latest_version": "17.0.1.0.0"}
        self.assertEqual(mapping_status({"kind": "rename"}, old, {"state": "uninstalled"}, 2, []),
                         "rename_requires_target_metadata_review")

    def test_payment_merge_is_not_a_rename(self):
        old = {"state": "installed", "latest_version": "17.0.1.0.3"}
        self.assertEqual(mapping_status({"kind": "merge"}, old, {"state": "installed"}, 9, []), "merge_pending")

    def test_conflicting_external_ids_block_any_mapping(self):
        self.assertEqual(mapping_status({"kind": "merge"}, None, None, 0, [("same_name", "ir.ui.view", 1, "ir.ui.view", 2)]),
                         "conflicting_xmlids_require_review")

    def test_native_v19_name_must_not_be_treated_as_old_oca(self):
        old = {"state": "installed", "latest_version": "19.0.1.0"}
        self.assertEqual(mapping_status({"kind": "rename"}, old, None, 0, []), "source_identity_requires_review")

    def test_clean_installation_does_not_prove_data_migration(self):
        self.assertEqual(mapping_status({"kind": "rename"}, None, {"state": "installed"}, 0, []),
                         "target_installed_no_legacy_evidence_not_proof_of_data_migration")

    def test_old_namespace_without_source_module_is_reported(self):
        self.assertEqual(mapping_status({"kind": "view_replacement"}, None, {"state": "installed"}, 4, []),
                         "legacy_namespace_requires_review")

    def test_module_references_are_detected_without_matching_model_names(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "models.py").write_text("model = 'commission.settlement'\nenv.ref('hr_commission.view_settlement_form')\n", encoding="utf-8")
            (folder / "view.xml").write_text('<odoo><record id="local_view" model="ir.ui.view"><field name="model">commission.settlement</field><field name="inherit_id" ref="account_commission.view_settlement_form"/></record></odoo>', encoding="utf-8")
            manifest = {"depends": ["commission"], "data": ["view.xml"]}
            found = legacy_references(folder, manifest, {"commission", "hr_commission", "account_commission"})
            self.assertEqual({row["reference"] for row in found},
                             {"commission", "hr_commission.view_settlement_form", "account_commission.view_settlement_form"})

    def test_html_ids_are_not_treated_as_data_xmlids(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "view.xml").write_text('<odoo><record id="actual_view" model="ir.ui.view"><field name="arch" type="xml"><list><field name="name" id="html_only"/></list></field></record></odoo>', encoding="utf-8")
            self.assertEqual(declared_xmlids(folder, {"data": ["view.xml"]}), {"actual_view"})

    def test_database_inspection_refuses_writable_transactions(self):
        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def execute(self, query):
                self.query = query

            def fetchone(self):
                return ("test", "off")

        class Connection:
            def cursor(self):
                return Cursor()

        with self.assertRaisesRegex(RuntimeError, "READ ONLY"):
            inspect_database(Connection(), {"module_changes": []})


if __name__ == "__main__":
    unittest.main()
