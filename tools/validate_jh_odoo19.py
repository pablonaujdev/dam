"""Read-only source checks against the locally installed Odoo 19. No database access."""
import argparse
import ast
import copy
import csv
import re
import pathlib
import hashlib
import json
import sys
from lxml import etree

CUSTOM = ('sale_purchase_lot', 'commission_by_category', 'miac_renovation_subscription', 'miac_line_subscription', 'jh_sales_subscription', 'account_payment_sale', 'miac_custom_reports', 'subscription_date_lines')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--odoo-server', default=r'C:\Program Files\Odoo 19.0e.20260105\server')
    parser.add_argument('--module', default='jh_sales_subscription')
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    server = pathlib.Path(args.odoo_server)
    sys.path.insert(0, str(server))
    import odoo.http
    from odoo.addons.base.models import ir_ui_view
    from odoo.tools.template_inheritance import apply_inheritance_specs
    paths, manifests, graph = {}, {}, []
    def visit(module):
        if module in paths:
            return
        path = root / module
        if not (path / '__manifest__.py').exists():
            path = server / 'odoo' / 'addons' / module
        if not (path / '__manifest__.py').exists():
            raise AssertionError('Missing dependency: ' + module)
        manifest = ast.literal_eval((path / '__manifest__.py').read_text(encoding='utf-8-sig'))
        paths[module], manifests[module] = path, manifest
        for dep in manifest.get('depends', []):
            visit(dep)
        graph.append(module)
    visit(args.module)
    checked_modules = set(CUSTOM) | {args.module}
    lock = json.loads((root / 'docs' / 'OCA_COMMISSION_19.lock.json').read_text(encoding='utf-8'))
    assert lock['commit'] == '74fcdc06111c6271faf12fb3c2e692da076271c2'
    for module, entry in lock['modules'].items():
        if module not in paths:
            continue
        assert manifests[module]['version'] == entry['version']
        for relative, digest in entry['files_sha256'].items():
            assert hashlib.sha256((paths[module] / relative).read_bytes()).hexdigest() == digest, module + '/' + relative
    failures = []
    python_count = xml_count = 0
    schema = etree.RelaxNG(etree.parse(str(server / 'odoo' / 'import_xml.rng')))
    views, children = {}, {}
    xmlids, references = set(), []
    for module in graph:
        path = paths[module]
        if module in checked_modules:
            assert re.fullmatch(r'19\.0\.\d+\.\d+\.\d+', manifests[module]['version']), module
            for filename in path.rglob('*.py'):
                compile(filename.read_text(encoding='utf-8-sig'), str(filename), 'exec')
                python_count += 1
        for filename in path.rglob('*.py'):
            if '__pycache__' in filename.parts:
                continue
            try:
                parsed = ast.parse(filename.read_text(encoding='utf-8-sig'))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for cls in parsed.body:
                if not isinstance(cls, ast.ClassDef):
                    continue
                attributes = {}
                for item in cls.body:
                    if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                        try:
                            attributes[item.targets[0].id] = ast.literal_eval(item.value)
                        except (ValueError, TypeError):
                            pass
                model = attributes.get('_name') or attributes.get('_inherit')
                if isinstance(model, list):
                    model = model[0] if model else None
                if not isinstance(model, str):
                    continue
                xmlids.add(module + '.model_' + model.replace('.', '_'))
                for item in cls.body:
                    if isinstance(item, ast.Assign) and isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Attribute):
                        if isinstance(item.value.func.value, ast.Name) and item.value.func.value.id == 'fields':
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    xmlids.add(module + '.field_' + model.replace('.', '_') + '__' + target.id)
        for filename in manifests[module].get('data', []):
            file = path / filename
            if not file.exists():
                failures.append(f'Missing data file: {file}')
                continue
            if file.suffix == '.csv':
                with file.open(encoding='utf-8-sig', newline='') as stream:
                    for row in csv.DictReader(stream):
                        for key, value in row.items():
                            if key.endswith(':id') and value:
                                references.append((module, value, str(file)))
                continue
            if file.suffix != '.xml':
                continue
            tree = etree.parse(str(file))
            # Odoo resolves local and qualified action interpolation to the same ID.
            for element in tree.iter():
                for attribute, value in list(element.attrib.items()):
                    element.set(attribute, re.sub(r'%\(([^)]+)\)d', lambda match: '%(' + (match[1] if '.' in match[1] else module + '.' + match[1]) + ')d', value))
            if module in checked_modules:
                xml_count += 1
                if not schema.validate(tree):
                    failures.append(f'XML schema: {file}: {schema.error_log.last_error}')
            for node in tree.xpath('//*[@id]'):
                rid = node.get('id')
                xmlids.add(rid if '.' in rid else module + '.' + rid)
            if module in checked_modules:
                for node in tree.xpath('//*[@ref]'):
                    references.append((module, node.get('ref'), str(file)))
                for node in tree.xpath('//*[@groups]'):
                    for rid in node.get('groups').split(','):
                        references.append((module, rid.lstrip('!'), str(file)))
                for node in tree.xpath('//*[@eval]'):
                    for rid in re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", node.get('eval')):
                        references.append((module, rid, str(file)))
            for record in tree.xpath('//record[@model="ir.ui.view"]'):
                rid = record.get('id')
                if not rid:
                    continue
                rid = rid if '.' in rid else module + '.' + rid
                arch = record.find("field[@name='arch']")
                if arch is None or not len(arch):
                    continue
                parent = record.find("field[@name='inherit_id']")
                parent = parent.get('ref') if parent is not None else None
                if parent and '.' not in parent:
                    parent = module + '.' + parent
                priority = record.find("field[@name='priority']")
                priority = int(priority.text or priority.get('eval', '16')) if priority is not None else 16
                mode = record.find("field[@name='mode']")
                mode = mode.text if mode is not None else 'extension'
                specs = copy.deepcopy(arch[0]) if len(arch) == 1 else etree.Element('data')
                if len(arch) > 1:
                    for element in arch:
                        specs.append(copy.deepcopy(element))
                views[rid] = (parent, specs, priority, module, str(file), mode)
            for template in tree.xpath('//template[@id]'):
                rid = template.get('id')
                rid = rid if '.' in rid else module + '.' + rid
                parent = template.get('inherit_id')
                if parent and '.' not in parent:
                    parent = module + '.' + parent
                if parent:
                    specs = etree.Element('data')
                    for element in template:
                        specs.append(copy.deepcopy(element))
                else:
                    specs = copy.deepcopy(template)
                views[rid] = (parent, specs, int(template.get('priority', '16')), module, str(file), 'extension')
    for rid, (parent, _, priority, module, _, mode) in views.items():
        if parent and mode != 'primary':
            children.setdefault(parent, []).append(rid)
        if module in checked_modules and parent and parent not in views:
            failures.append(f'Missing inherited view: {rid} -> {parent}')
    for module, rid, file in references:
        if module not in checked_modules:
            continue
        full = rid if '.' in rid else module + '.' + rid
        if full not in xmlids:
            failures.append(f'Missing XML ID: {full} ({file})')
    checked = set()
    def apply(rid, arch):
        parent, specs, _, module, file, mode = views[rid]
        try:
            arch = apply_inheritance_specs(arch, copy.deepcopy(specs))
            if module in checked_modules:
                checked.add(rid)
        except Exception as error:
            failures.append(f'Inheritance: {rid}: {error}')
            return arch
        return descend(rid, arch)
    def descend(rid, arch):
        for child in sorted(children.get(rid, []), key=lambda item: (views[item][2], graph.index(views[item][3]), item)):
            arch = apply(child, arch)
        return arch
    def base_arch(rid):
        parent, specs, _, _, _, _ = views[rid]
        if parent:
            arch = base_arch(parent)
            return apply_inheritance_specs(arch, copy.deepcopy(specs))
        return copy.deepcopy(specs)
    roots = set()
    for rid, data in views.items():
        if data[3] not in checked_modules:
            continue
        node = rid
        while views.get(node, (None,))[0] in views and views[node][5] != 'primary':
            node = views[node][0]
        roots.add(node)
    for rid in sorted(roots):
        if views[rid][0] and views[rid][0] not in views:
            continue
        try:
            arch = base_arch(rid)
            if views[rid][3] in checked_modules:
                checked.add(rid)
            descend(rid, arch)
        except Exception as error:
            failures.append(f'Root inheritance: {rid}: {error}')
    print(f'Dependency graph: {len(graph)} modules; custom Python: {python_count}; custom XML: {xml_count}; custom views composed: {len(checked)}')
    for failure in failures:
        print(failure)
    return bool(failures)

if __name__ == '__main__':
    sys.exit(main())

