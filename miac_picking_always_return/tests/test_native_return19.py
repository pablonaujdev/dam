# Part of Avannubo. License AGPL-3.
from odoo.tests import tagged
from odoo.addons.stock.tests.test_stock_return_picking import TestReturnPicking


@tagged('post_install', '-at_install', 'picking_native_return19')
class TestNativeReturnAfterMiac(TestReturnPicking):
    """Replay native returns once all installed MIAC extensions are loaded."""

    allow_inherited_tests_method = True
