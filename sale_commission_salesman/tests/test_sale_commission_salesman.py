# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "salesman_migration19")
class TestSaleCommissionSalesman(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        groups |= cls.quick_ref("sales_team.group_sale_manager")
        groups |= cls.quick_ref("commission_oca.group_commission_user")
        hr_group = cls.env.ref("hr.group_hr_manager", raise_if_not_found=False)
        if hr_group:
            groups |= hr_group
        return groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.commission_1, cls.commission_2 = cls.env["commission"].create([
            {"name": "Salesman 1%", "fix_qty": 1, "settlement_type": "sale_invoice"},
            {"name": "Salesman 2%", "fix_qty": 2, "settlement_type": "sale_invoice"},
        ])
        cls.product = cls.env["product.product"].create({
            "name": "Salesman service", "type": "service", "list_price": 100,
            "invoice_policy": "order", "taxes_id": [Command.clear()],
            "supplier_taxes_id": [Command.clear()],
        })
        cls.partner = cls.env["res.partner"].create({"name": "Salesman customer"})
        cls.salesman = new_test_user(
            cls.env, login="salesman_test19", name="Salesman 19",
            groups="sales_team.group_sale_salesman,commission_oca.group_commission_user",
            company_id=cls.env.company.id,
        )
        cls.agent = cls.salesman.partner_id
        cls.agent.write({"agent": True, "salesman_as_agent": True,
                         "commission_id": cls.commission_1.id})
        cls.other_salesman = new_test_user(
            cls.env, login="salesman_other19", company_id=cls.env.company.id,
            groups="sales_team.group_sale_salesman,commission_oca.group_commission_user",
        )
        cls.other_agent = cls.other_salesman.partner_id
        cls.other_agent.write({"agent": True, "salesman_as_agent": True,
                               "commission_id": cls.commission_2.id})

    def _order(self, **extra):
        values = {"partner_id": self.partner.id, "user_id": self.salesman.id,
                  "order_line": [Command.create({"product_id": self.product.id,
                      "product_uom_qty": 1, "price_unit": 100, "tax_ids": [Command.clear()]})]}
        values.update(extra)
        return self.env["sale.order"].create(values)

    def _invoice(self, move_type="out_invoice", **extra):
        values = {"partner_id": self.partner.id, "invoice_user_id": self.salesman.id,
                  "move_type": move_type, "invoice_date": date(2026, 1, 15),
                  "invoice_line_ids": [Command.create({"product_id": self.product.id,
                      "quantity": 1, "price_unit": 100, "tax_ids": [Command.clear()]})]}
        values.update(extra)
        return self.env["account.move"].create(values)

    def _assert_agent(self, line, agent=None, commission=None):
        self.assertEqual(len(line.agent_ids), 1)
        self.assertEqual(line.agent_ids.agent_id, agent or self.agent)
        self.assertEqual(line.agent_ids.commission_id, commission or self.commission_1)

    # Original five scenarios, with real equality assertions and OCA 19 names.
    def test_check_salesman_commission(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.commission_id = False

    def test_sale_commission_salesman(self):
        self._assert_agent(self._order().order_line)

    def test_sale_commission_salesman_no_population(self):
        self.partner.commission_agent_ids = [Command.set(self.other_agent.ids)]
        self._assert_agent(self._order().order_line, self.other_agent, self.commission_2)

    def test_invoice_commission_salesman(self):
        invoice = self._invoice(invoice_line_ids=[])
        with Form(invoice) as form:
            with form.invoice_line_ids.new() as line:
                line.product_id = self.product
        self._assert_agent(invoice.invoice_line_ids)

    def test_invoice_commission_salesman_no_population(self):
        self.partner.commission_agent_ids = [Command.set(self.other_agent.ids)]
        self._assert_agent(self._invoice().invoice_line_ids, self.other_agent, self.commission_2)

    def test_salesman_not_enabled_or_not_agent(self):
        self.agent.salesman_as_agent = False
        self.assertFalse(self._order().order_line.agent_ids)
        self.assertFalse(self._invoice().invoice_line_ids.agent_ids)
        self.agent.write({"salesman_as_agent": True, "agent": False})
        self.assertFalse(self._order().order_line.agent_ids)
        self.assertFalse(self._invoice().invoice_line_ids.agent_ids)
        self.agent.write({"salesman_as_agent": False, "commission_id": False})
        self.assertFalse(self._order().order_line.agent_ids)
        self.assertFalse(self._invoice().invoice_line_ids.agent_ids)

    def test_explicit_agents_are_preserved(self):
        agents = [Command.create({"agent_id": self.other_agent.id,
                                 "commission_id": self.commission_2.id})]
        order = self._order(order_line=[Command.create({"product_id": self.product.id,
                                    "price_unit": 100, "agent_ids": agents})])
        self._assert_agent(order.order_line, self.other_agent, self.commission_2)
        invoice = self._invoice(invoice_line_ids=[Command.create({
            "product_id": self.product.id, "price_unit": 100, "agent_ids": agents})])
        self._assert_agent(invoice.invoice_line_ids, self.other_agent, self.commission_2)

    def test_free_products_sections_notes_and_missing_salesman(self):
        self.product.commission_free = True
        self.assertFalse(self._order().order_line.agent_ids)
        self.assertFalse(self._invoice().invoice_line_ids.agent_ids)
        self.product.commission_free = False
        for document, model, field in [(self._order(), "sale.order.line", "order_id"),
                                       (self._invoice(), "account.move.line", "move_id")]:
            for kind in ("line_section", "line_note"):
                line = self.env[model].create({field: document.id, "display_type": kind, "name": kind})
                self.assertFalse(line.agent_ids)
        self.assertFalse(self._order(user_id=False).order_line.agent_ids)
        self.assertFalse(self._invoice(invoice_user_id=self.env.user.id).invoice_line_ids.agent_ids)

    def test_seller_change_preserves_until_regeneration(self):
        order, invoice = self._order(), self._invoice()
        self._assert_agent(order.order_line)
        self._assert_agent(invoice.invoice_line_ids)
        order.user_id = self.other_salesman
        invoice.invoice_user_id = self.other_salesman
        self._assert_agent(order.order_line)
        self._assert_agent(invoice.invoice_line_ids)
        for document, lines in [(order, order.order_line), (invoice, invoice.invoice_line_ids)]:
            document.recompute_lines_agents()
            self._assert_agent(lines, self.other_agent, self.commission_2)
            document.recompute_lines_agents()
            self._assert_agent(lines, self.other_agent, self.commission_2)

    def test_fallback_preserves_manual_settlement_type(self):
        self.commission_1.settlement_type = "manual"
        self._assert_agent(self._order().order_line)
        self._assert_agent(self._invoice().invoice_line_ids)

    def test_invoice_refund_sign_and_excluded_documents(self):
        invoice, refund = self._invoice(), self._invoice("out_refund")
        self._assert_agent(refund.invoice_line_ids)
        self.assertAlmostEqual(invoice.invoice_line_ids.agent_ids.amount, 1)
        self.assertAlmostEqual(refund.invoice_line_ids.agent_ids.amount, -1)
        self.assertFalse(self._invoice("in_invoice").invoice_line_ids.agent_ids)
        self.assertFalse(self._invoice("in_refund").invoice_line_ids.agent_ids)
        move = self.env["account.move"].create({
            "move_type": "entry", "partner_id": self.partner.id,
            "journal_id": self.company_data["default_journal_misc"].id,
            "line_ids": [Command.create({"product_id": self.product.id, "debit": 100,
                "account_id": self.company_data["default_account_expense"].id}),
                Command.create({"credit": 100,
                    "account_id": self.company_data["default_account_revenue"].id})],
        })
        self.assertFalse(move.line_ids.agent_ids)

    def test_partial_invoice_keeps_original_agent(self):
        order = self._order()
        line = order.order_line
        line.product_uom_qty = 4
        order.action_confirm()
        first = order._create_invoices()
        first.invoice_line_ids.filtered("product_id").quantity = 2
        first.action_post()
        order.user_id = self.other_salesman
        second = order._create_invoices()
        self.assertEqual(second.invoice_line_ids.filtered("product_id").quantity, 2)
        self._assert_agent(first.invoice_line_ids.filtered("product_id"))
        self._assert_agent(second.invoice_line_ids.filtered("product_id"))
        self.assertAlmostEqual(first.commission_total + second.commission_total, 4)

    def test_settlement_is_not_duplicated(self):
        invoice = self._invoice()
        invoice.action_post()
        wizard = self.env["commission.make.settle"].create({
            "date_to": date(2026, 2, 1), "agent_ids": [Command.set(self.agent.ids)],
            "settlement_type": "sale_invoice",
        })
        wizard.action_settle()
        settlements = self.env["commission.settlement"].search([("agent_id", "=", self.agent.id)])
        self.assertEqual(len(settlements), 1)
        self.assertAlmostEqual(settlements.total, 1)
        line_ids = settlements.line_ids.ids
        wizard.action_settle()
        self.assertEqual(settlements.line_ids.ids, line_ids)
        invoice.invoice_user_id = self.other_salesman
        self._assert_agent(invoice.invoice_line_ids)
        self.assertEqual(settlements.line_ids.ids, line_ids)

    def test_company_permissions_and_partner_view(self):
        order = self._order().with_user(self.salesman)
        self._assert_agent(order.order_line)
        second_data = self.setup_other_company(name="Salesman forbidden company")
        other = self.env["sale.order"].with_company(second_data["company"]).create({
            "partner_id": self.partner.id, "company_id": second_data["company"].id,
            "user_id": self.salesman.id,
        })
        with self.assertRaises(AccessError):
            other.with_user(self.salesman).with_context(allowed_company_ids=[self.env.company.id]).read(["name"])
        view = self.env["res.partner"].get_view(view_id=self.env.ref("base.view_partner_form").id)
        arch = etree.fromstring(view["arch"].encode())
        option = arch.xpath("//field[@name='salesman_as_agent']")
        self.assertEqual(len(option), 1)
        self.assertEqual(option[0].get("invisible"), "not user_ids")

    def test_miac_manual_category_agent_priority(self):
        if "z_commission_manual" not in self.env["sale.order.line.agent"]._fields:
            self.skipTest("MIAC/JH integration is tested in the MIAC trial database.")
        category = self.env["product.category"].create({"name": "Salesman MIAC category"})
        self.product.categ_id = category
        rule = self.env["product.category.agent.commission"].create({
            "categ_id": category.id, "agent_id": self.agent.id, "commission_id": self.commission_2.id})
        line = self._order().order_line
        self._assert_agent(line, self.agent, self.commission_2)
        self.assertFalse(line.agent_ids.z_commission_manual)
        manual = self.env["commission"].create({"name": "Salesman negotiated 3%", "fix_qty": 3})
        line.agent_ids.commission_id = manual
        rule.commission_id = self.commission_1
        line.product_uom_qty = 2
        self._assert_agent(line, self.agent, manual)
        line.order_id.action_confirm()
        invoice = line.order_id._create_invoices()
        self._assert_agent(invoice.invoice_line_ids.filtered("product_id"), self.agent, manual)

    def test_hr_salesman_integration(self):
        if "salesman" not in dict(self.agent._fields["agent_type"]._description_selection(self.env)):
            self.skipTest("HR commission integration is tested with hr_commission_oca installed.")
        self.env["hr.employee"].create({"name": "Salesman employee", "user_id": self.salesman.id})
        self.agent.agent_type = "salesman"
        self._assert_agent(self._order().order_line)
        self._assert_agent(self._invoice().invoice_line_ids)
