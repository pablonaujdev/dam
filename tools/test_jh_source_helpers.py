"""Execute actual migrated helpers with small collaborators; no ORM/database."""
import ast
import copy
import pathlib
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER = pathlib.Path(r'C:\Program Files\Odoo 19.0e.20260105\server')
sys.path.insert(0, str(SERVER))
from odoo.tools import SQL


def load_method(filename, class_name, method_name, parent=object, namespace=None):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    node = copy.deepcopy(next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name))
    node.decorator_list = []
    wrapper = ast.ClassDef(name='Subject', bases=[ast.Name(id='Parent', ctx=ast.Load())], keywords=[], body=[node], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))
    values = {'Parent': parent, 'SQL': SQL}
    values.update(namespace or {})
    exec(compile(module, str(ROOT / filename), 'exec'), values)
    return values['Subject']


class NativeRenewal:
    def _prepare_upsell_renew_order_values(self, state):
        # Native 19 identifies origin lines with parent_line_id.
        return {'order_line': [(0, 0, {'product_id': 9, 'parent_line_id': line.id,
            'price_unit': line.price_unit, 'discount': line.discount}) for line in self.order_line]}


class NativeMailer:
    def _send_mail(self, move, template, **kwargs):
        self.calls.append((move, template, kwargs))
        return len(self.calls)


class SourceRegressionTests(unittest.TestCase):
    def renewal(self, mode):
        subject = load_method('jh_sales_subscription/models/jh_sale_order_line.py',
            'SaleOrderInherit', '_prepare_upsell_renew_order_values', NativeRenewal)()
        subject.env = SimpleNamespace(context={'renewal_pricing_mode': mode})
        subject.order_line = [SimpleNamespace(id=41, lot_id=SimpleNamespace(id=101), display_type=False, price_unit=0, discount=0),
            SimpleNamespace(id=42, lot_id=SimpleNamespace(id=102), display_type=False, price_unit=63, discount=11)]
        return subject._prepare_upsell_renew_order_values('2_renewal')['order_line']

    def test_duplicate_products_keep_origin_lots_and_explicit_zero(self):
        lines = self.renewal('keep_current')
        self.assertEqual([line[2]['lot_id'] for line in lines], [101, 102])
        self.assertEqual([(line[2]['price_unit'], line[2]['discount']) for line in lines], [(0, 0), (63, 11)])

    def test_update_tariff_removes_only_price_conditions(self):
        lines = self.renewal('update_tariff')
        for line in lines:
            self.assertNotIn('price_unit', line[2])
            self.assertNotIn('discount', line[2])
            self.assertIn('parent_line_id', line[2])
            self.assertIn('lot_id', line[2])

    def test_mail_one_delivery_per_recipient(self):
        subject = load_method('jh_sales_subscription/models/jh_sale_order_line.py',
            'AccountMoveSendInherit', '_send_mail', NativeMailer)()
        subject.calls = []
        partners = [2, 3, 4]
        result = subject._send_mail('invoice', 'template', partner_ids=partners, attachments=['PDF'])
        self.assertEqual(result, 3)
        self.assertEqual([call[2]['partner_ids'] for call in subject.calls], [[2], [3], [4]])
        self.assertEqual(partners, [2, 3, 4])
        self.assertTrue(all(call[2]['attachments'] == ['PDF'] for call in subject.calls))

    def test_mail_single_recipient_uses_native_once(self):
        subject = load_method('jh_sales_subscription/models/jh_sale_order_line.py',
            'AccountMoveSendInherit', '_send_mail', NativeMailer)()
        subject.calls = []
        self.assertEqual(subject._send_mail('invoice', 'template', partner_ids=[2]), 1)
        self.assertEqual(len(subject.calls), 1)

    def test_report_composes_native_sql(self):
        class BaseReport:
            def _select(self):
                return SQL('SELECT line.id')
        subject = load_method('jh_sales_subscription/models/jh_account_invoice_report.py',
            'AccountInvoiceReportInherit', '_select', BaseReport)()
        result = subject._select()
        self.assertIsInstance(result, SQL)
        self.assertTrue(result.code.startswith('SELECT line.id,'))
        self.assertIn('line.jh_cost_unit AS jh_cost', result.code)
        self.assertFalse(result.params)

    def test_history_selection_and_signs_are_query_only(self):
        subject = load_method('jh_sales_subscription/models/jh_client_sheet.py', 'JhClientSheet', '_table_query')()
        query = subject._table_query()
        self.assertEqual(query.params, ['RFV%', 'RFV%', 'FV%', 'RFV%'])
        self.assertIn('SELECT line.id', query.code)
        self.assertIn('-line.quantity', query.code)
        self.assertIn("move.state = 'posted'", query.code)
        self.assertNotIn('DELETE ', query.code)
        self.assertNotIn('INSERT ', query.code)


if __name__ == '__main__':
    unittest.main(verbosity=2)
