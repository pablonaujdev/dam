# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class CommonTestCase(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('sales_team.group_sale_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.bank = cls.env["res.partner.bank"].create(
            {"acc_number": "test", "partner_id": cls.env.user.company_id.partner_id.id}
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "test journal",
                "code": "123",
                "type": "bank",
                "company_id": cls.env.company.id,
                "bank_account_id": cls.bank.id,
            }
        )
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "test_mode",
                "active": True,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.journal.id,
            }
        )
        cls.payment_mode_2 = cls.env["account.payment.mode"].create(
            {
                "name": "test_mode_2",
                "active": True,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.journal.id,
            }
        )
        cls.base_partner = cls.env["res.partner"].create(
            {
                "name": "Dummy",
                "email": "dummy@example.com",
                "customer_payment_mode_id": cls.payment_mode.id,
            }
        )
        cls.products = {
            "serv_order": cls.env["product.product"].create({
                "name": "Test service product order", "type": "service",
                "invoice_policy": "order", "categ_id": cls.product_category.id,
                "list_price": 100,
            }),
        }
