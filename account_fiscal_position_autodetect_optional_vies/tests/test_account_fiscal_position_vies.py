# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "optional_vies19")
class TestAccountFiscalPositionVies(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        sale_group = cls.env.ref("sales_team.group_sale_manager", raise_if_not_found=False)
        return groups | sale_group if sale_group else groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vies_mock = cls.startClassPatcher(patch(
            "odoo.addons.base_vat.models.res_partner.check_vies", return_value={"valid": False}))
        cls.company = cls.env.company
        cls.company.vat_check_vies = False
        cls.fp_model = cls.env["account.fiscal.position"]
        cls.fp_model.search([("auto_apply", "=", True)]).write({"auto_apply": False})
        cls.fp_vat = cls._position("Without VIES")
        cls.fp_vat_vies = cls._position("With VIES", vat_vies_required=True)
        cls.partner = cls.env["res.partner"].create({
            "name": "Optional VIES company", "vat": "BE0477472701",
            "country_id": cls.env.ref("base.be").id, "is_company": True,
            **({"fiscal_position_type": False} if "fiscal_position_type" in cls.env["res.partner"]._fields else {}),
        })
        cls.child_partner = cls.env["res.partner"].create({
            "name": "Optional VIES child", "parent_id": cls.partner.id,
            "country_id": cls.partner.country_id.id,
        })

    @classmethod
    def _position(cls, name, **values):
        defaults = dict(name=name, company_id=cls.env.company.id, auto_apply=True,
            vat_required=True, sequence=100)
        defaults.update(values)
        values = defaults
        if "fiscal_position_type" in cls.fp_model._fields:
            values.setdefault("fiscal_position_type", False)
        return cls.fp_model.create(values)

    def _detect(self, partner=None, delivery=None, company=None):
        return self.fp_model.with_company(company or self.company)._get_fiscal_position(
            partner if partner is not None else self.partner, delivery=delivery)

    def _create_invoice(self, partner, delivery=None):
        form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
        form.invoice_date = fields.Date.today()
        form.partner_id = partner
        invoice = form.save()
        if delivery:
            invoice.partner_shipping_id = delivery
        return invoice

    def test_invoice_fiscal_position_without_vies(self):
        for partner in (self.partner, self.child_partner):
            self.assertEqual(self._create_invoice(partner).fiscal_position_id, self.fp_vat)

    def test_invoice_fiscal_position_with_vies(self):
        self.company.vat_check_vies = True
        self.partner.vies_valid = True
        for partner in (self.partner, self.child_partner):
            self.assertEqual(self._create_invoice(partner).fiscal_position_id, self.fp_vat_vies)

    def test_commercial_partner_result_wins_over_child(self):
        self.partner.vies_valid = True
        self.child_partner.vies_valid = False
        self.assertEqual(self._detect(self.child_partner), self.fp_vat_vies)

    def test_delivery_and_native_same_prefix_invoicing(self):
        self.partner.vies_valid = True
        delivery = self.env["res.partner"].create({
            "name": "Other delivery", "vat": "DE123456788", "is_company": True,
            "country_id": self.env.ref("base.de").id,
            **({"fiscal_position_type": False} if "fiscal_position_type" in self.partner._fields else {}),
        })
        self.assertEqual(self._detect(delivery=delivery), self.fp_vat)
        self.assertEqual(self._create_invoice(self.partner, delivery).fiscal_position_id, self.fp_vat)
        self.company.vat = "BE0477472701"
        self.assertEqual(self._detect(delivery=delivery), self.fp_vat_vies)

    def test_manual_positions_have_priority(self):
        self.partner.vies_valid = True
        self.partner.property_account_position_id = self.fp_vat
        self.assertEqual(self._detect(), self.fp_vat)
        self.assertEqual(self._create_invoice(self.partner).fiscal_position_id, self.fp_vat)
        self.child_partner.property_account_position_id = self.fp_vat_vies
        self.assertEqual(self._detect(delivery=self.child_partner), self.fp_vat_vies)

    def test_missing_vat_and_generic_positions(self):
        self.partner.vat = False
        self.assertFalse(self._detect())
        generic = self._position("No VAT", vat_required=False)
        self.assertEqual(self._detect(), generic)
        self.partner.vat = "BE0477472701"
        self.partner.vies_valid = True
        self.fp_vat_vies.auto_apply = False
        self.assertFalse(self._detect())
        generic.vat_vies_required = True
        self.assertEqual(self._detect(), generic)

    def test_native_country_state_zip_and_group(self):
        self.partner.write({"country_id": self.env.ref("base.us").id,
            "state_id": self.env.ref("base.state_us_5").id, "zip": "95380"})
        self.fp_vat.write({"country_id": self.partner.country_id.id,
            "state_ids": [Command.set(self.partner.state_id.ids)], "zip_from": "95000", "zip_to": "95999"})
        self.assertEqual(self._detect(), self.fp_vat)
        self.partner.zip = "96000"
        self.assertFalse(self._detect())
        self.partner.zip = "95380"
        self.partner.state_id = self.env.ref("base.state_us_6")
        self.assertFalse(self._detect())
        self.partner.state_id = self.env.ref("base.state_us_5")
        self.fp_vat.country_id = self.env.ref("base.de")
        self.assertFalse(self._detect())
        self.fp_vat.write({"country_id": False, "state_ids": [Command.clear()],
            "country_group_id": self.env.ref("base.europe").id})
        self.assertFalse(self._detect())
        self.fp_vat.country_group_id = False
        self.assertEqual(self._detect(), self.fp_vat)

    def test_native_sequence_company_and_no_match(self):
        other_company = self.env["res.company"].create({"name": "Optional VIES other company"})
        other_position = self._position("Other company", company_id=other_company.id, sequence=1)
        lower_sequence = self._position("Earlier", sequence=10)
        self.assertEqual(self._detect(), lower_sequence)
        self.assertEqual(self._detect(company=other_company), other_position)
        (self.fp_vat | lower_sequence).write({"vat_vies_required": True})
        self.assertFalse(self._detect())
        self.assertFalse(self._detect(partner=self.env["res.partner"]))

    def test_company_vies_checks_remain_active(self):
        self.company.write({"country_id": self.env.ref("base.es").id,
            "account_fiscal_country_id": self.env.ref("base.es").id, "vat_check_vies": True})
        self.vies_mock.return_value = {"valid": False}
        self.vies_mock.reset_mock()
        self.partner._compute_vies_valid()
        self.vies_mock.assert_called_once_with(self.partner.vat, timeout=10)
        self.assertFalse(self.partner.vies_valid)
        self.assertTrue(self.partner.perform_vies_validation)
        self.assertFalse(self.partner._get_vat_required_valid(company=self.company))
        self.assertFalse(self._detect())
        self.vies_mock.return_value = {"valid": True}
        self.partner._compute_vies_valid()
        self.assertTrue(self.partner.vies_valid)
        self.vies_mock.return_value = {"valid": False}
        self.assertEqual(self._detect(), self.fp_vat_vies)
        self.company.vat_check_vies = False
        # As in a new request after saving Settings: this native compute depends
        # on company context and VAT, not directly on the company's VIES flag.
        self.partner.invalidate_recordset(["perform_vies_validation"])
        self.assertEqual(self._detect(), self.fp_vat_vies)
        self.partner.vies_valid = False
        self.assertEqual(self._detect(), self.fp_vat)

    def test_detection_does_not_call_vies(self):
        self.partner.vies_valid = True
        self.env.flush_all()
        self.vies_mock.reset_mock()
        self.assertEqual(self._detect(), self.fp_vat_vies)
        self.vies_mock.assert_not_called()

    def test_search_is_not_filtered_by_legacy_context(self):
        found = self.fp_model.with_context(vat_vies_required=True).search([
            ("id", "in", (self.fp_vat | self.fp_vat_vies).ids)])
        self.assertEqual(set(found.ids), set((self.fp_vat | self.fp_vat_vies).ids))

    def test_form_visibility_preserves_stored_flag(self):
        self.fp_vat_vies.write({"auto_apply": False, "vat_required": False})
        with Form(self.fp_vat_vies) as form:
            self.assertTrue(form._get_modifier("vat_vies_required", "invisible"))
        self.assertTrue(self.fp_vat_vies.vat_vies_required)
        with Form(self.fp_vat_vies) as form:
            form.auto_apply = True
            form.vat_required = True
            self.assertFalse(form._get_modifier("vat_vies_required", "invisible"))
        self.assertTrue(self.fp_vat_vies.vat_vies_required)

    def test_partner_type_integration(self):
        if "fiscal_position_type" not in self.fp_model._fields:
            self.skipTest("B2B/B2C integration is tested when its independent module is installed")
        self.fp_vat_vies.auto_apply = False
        positions = {}
        for partner_type in ("b2b", "b2c"):
            for vies_valid in (False, True):
                positions[(partner_type, vies_valid)] = self._position(
                    f"{partner_type} VIES {vies_valid}", fiscal_position_type=partner_type,
                    vat_vies_required=vies_valid, sequence=10)
        for partner_type in ("b2b", "b2c"):
            for vies_valid in (False, True):
                self.partner.write({"fiscal_position_type": partner_type, "vies_valid": vies_valid})
                expected = positions[(partner_type, vies_valid)]
                self.assertEqual(self._detect(), expected)
                self.assertEqual(self._create_invoice(self.partner).fiscal_position_id, expected)

    def test_sale_order_integration(self):
        if "sale.order" not in self.env:
            self.skipTest("Sales integration is tested when sale is installed")
        self.partner.vies_valid = True
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertEqual(order.fiscal_position_id, self.fp_vat_vies)
        order.partner_id = self.child_partner
        self.assertEqual(order.fiscal_position_id, self.fp_vat_vies)
