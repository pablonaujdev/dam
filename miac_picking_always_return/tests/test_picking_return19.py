# Part of Avannubo. License AGPL-3.
from unittest.mock import patch

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, new_test_user, tagged
from odoo.tools.safe_eval import safe_eval
from odoo.addons.stock.tests.common import TestStockCommon


@tagged('post_install', '-at_install', 'picking_return19')
class TestPickingReturn19(TestStockCommon):
    def _picking(self, kind='outgoing', quantity=2, **extra):
        picking_type, source, target = {
            'outgoing': (self.picking_type_out, self.stock_location, self.customer_location),
            'incoming': (self.picking_type_in, self.supplier_location, self.stock_location),
            'internal': (self.picking_type_int, self.stock_location, self.shelf_1),
        }[kind]
        values = {
            'picking_type_id': picking_type.id,
            'location_id': source.id, 'location_dest_id': target.id,
            'move_ids': [Command.create({
                'product_id': self.productA.id, 'product_uom_qty': quantity,
                'product_uom': self.productA.uom_id.id,
                'location_id': source.id, 'location_dest_id': target.id,
            })],
        }
        values.update(extra)
        return self.env['stock.picking'].create(values)

    def _state_picking(self, state):
        picking = self._picking()
        if state == 'waiting':
            parent = self._picking('incoming')
            parent.action_confirm()
            picking.move_ids.move_orig_ids = [Command.link(parent.move_ids.id)]
        if state != 'draft':
            picking.action_confirm()
        if state == 'assigned':
            self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 2)
            picking.action_assign()
        elif state == 'done':
            picking.move_ids.write({'quantity': 2, 'picked': True})
            picking.button_validate()
        elif state == 'cancel':
            picking.action_cancel()
        self.assertEqual(picking.state, state)
        return picking

    def _wizard(self, picking, form=False):
        model = picking.env['stock.return.picking'].with_context(
            active_id=picking.id, active_ids=picking.ids, active_model='stock.picking',
        )
        return Form(model).save() if form else model.create({})

    def _snapshot(self, picking):
        self.env.flush_all()
        return {
            'state': picking.state, 'write_date': picking.write_date,
            'date_done': picking.date_done, 'scheduled_date': picking.scheduled_date,
            'moves': [(move.id, move.state, move.product_uom_qty, move.quantity, move.picked)
                      for move in picking.move_ids],
            'quants': self.env['stock.quant'].search([
                ('product_id', '=', self.productA.id),
            ]).read(['quantity', 'reserved_quantity', 'location_id']),
        }

    def test_allowed_states_open_without_writing_origin(self):
        for state in ('confirmed', 'waiting', 'assigned', 'done'):
            picking = self._state_picking(state)
            before = self._snapshot(picking)
            original_write = type(picking).write
            writes = []
            def observe_write(records, values):
                if picking.id in records.ids:
                    writes.append(values.copy())
                return original_write(records, values)
            with patch.object(type(picking), 'write', observe_write):
                wizard = self._wizard(picking, form=True)
            self.assertTrue(picking._can_return())
            self.assertTrue(wizard.product_return_moves)
            self.assertEqual(wizard.product_return_moves.quantity, 0)
            self.assertFalse(writes)
            self.assertEqual(self._snapshot(picking), before)
            wizard.unlink()
            self.assertEqual(self._snapshot(picking), before)

    def test_draft_and_cancelled_cannot_open_or_create(self):
        for state in ('draft', 'cancel'):
            picking = self._state_picking(state)
            self.assertFalse(picking._can_return())
            before = self._snapshot(picking)
            with self.assertRaises(UserError), self.env.cr.savepoint():
                self._wizard(picking)
            self.assertEqual(self._snapshot(picking), before)

    def test_button_visibility_and_native_permissions(self):
        view = self.env['stock.picking'].get_view(
            view_id=self.env.ref('stock.view_picking_form').id, view_type='form')
        arch = etree.fromstring(view['arch'])
        action_id = self.env.ref('stock.act_stock_return_picking').id
        button = arch.xpath(f"//button[@name='{action_id}']")
        self.assertEqual(len(button), 1)
        combined_arch = self.env.ref('stock.view_picking_form')._get_combined_arch()
        original_button = combined_arch.xpath(f"//button[@name='{action_id}']")
        self.assertEqual(original_button[0].get('groups'), 'base.group_user')
        for state in ('draft', 'confirmed', 'waiting', 'assigned', 'done', 'cancel'):
            invisible = safe_eval(button[0].get('invisible'), {'state': state})
            self.assertEqual(invisible, state in ('draft', 'cancel'))

    def test_open_wizard_rejects_later_cancellation(self):
        picking = self._state_picking('confirmed')
        wizard = self._wizard(picking)
        wizard.product_return_moves.quantity = 1
        picking.action_cancel()
        for action in ('action_create_returns', 'action_create_returns_all', 'action_create_exchanges'):
            with self.assertRaisesRegex(UserError, 'no longer allows a return'), self.env.cr.savepoint():
                getattr(wizard, action)()
        self.assertFalse(picking.return_ids)

    def test_open_wizard_rechecks_state_before_any_copy(self):
        picking = self._state_picking('confirmed')
        wizard = self._wizard(picking)
        wizard.product_return_moves.quantity = 1
        # Simulate a stale wizard whose origin eligibility changed. Never force a stock state.
        with patch.object(type(picking), '_can_return', return_value=False), \
                patch.object(type(picking), 'copy', side_effect=AssertionError('Must not copy')):
            with self.assertRaisesRegex(UserError, 'no longer allows a return'):
                wizard.action_create_returns()

    def test_pending_returns_preserve_origin_and_native_links(self):
        for kind in ('outgoing', 'incoming', 'internal'):
            picking = self._picking(kind)
            picking.action_confirm()
            old_state = picking.state
            source_move = picking.move_ids
            wizard = self._wizard(picking)
            wizard.product_return_moves.quantity = 1
            action = wizard.action_create_returns()
            returned = self.env['stock.picking'].browse(action['res_id'])
            self.assertEqual(picking.state, old_state)
            self.assertFalse(picking.date_done)
            self.assertEqual(returned.return_id, picking)
            self.assertEqual(returned.move_ids.origin_returned_move_id, source_move)
            self.assertIn(source_move, returned.move_ids.move_orig_ids)
            self.assertEqual(returned.location_id, picking.location_dest_id)
            return_type = picking.picking_type_id.return_picking_type_id
            expected_target = (return_type.default_location_dest_id
                               if return_type.code == 'incoming' else picking.location_id)
            self.assertEqual(returned.location_dest_id, expected_target)
            self.assertEqual(returned.picking_type_id, return_type or picking.picking_type_id)
            self.assertNotIn(returned.state, ('done', 'cancel'))

    def test_zero_quantities_create_no_return(self):
        picking = self._state_picking('confirmed')
        wizard = self._wizard(picking)
        with self.assertRaisesRegex(UserError, 'non-zero quantity'), self.env.cr.savepoint():
            wizard.action_create_returns()
        self.assertFalse(picking.return_ids)
        self.assertEqual(picking.state, 'confirmed')

    def test_return_all_pending_uses_native_quantity_not_demand(self):
        picking = self._state_picking('confirmed')
        self.assertEqual(picking.move_ids.quantity, 0)
        wizard = self._wizard(picking)
        with self.assertRaisesRegex(UserError, 'non-zero quantity'), self.env.cr.savepoint():
            wizard.action_create_returns_all()
        self.assertFalse(picking.return_ids)
        self.assertEqual(picking.move_ids.product_uom_qty, 2)

    def test_return_all_ready_uses_reserved_quantity(self):
        picking = self._state_picking('assigned')
        quantity = picking.move_ids.quantity
        action = self._wizard(picking).action_create_returns_all()
        returned = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(returned.move_ids.product_uom_qty, quantity)
        self.assertEqual(picking.state, 'assigned')
        self.assertFalse(picking.date_done)

    def test_partial_and_repeated_returns_use_remaining_native_quantity(self):
        picking = self._state_picking('done')
        wizard = self._wizard(picking)
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        first = self.env['stock.picking'].browse(action['res_id'])
        first.move_ids.write({'quantity': 1, 'picked': True})
        first.button_validate()
        action = self._wizard(picking).action_create_returns_all()
        second = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(second.move_ids.product_uom_qty, 1)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(len(picking.return_ids), 2)

    def test_repeated_products_and_different_units_keep_their_moves(self):
        picking = self._state_picking('confirmed')
        second = self.env['stock.move'].create({
            'product_id': self.productA.id, 'product_uom_qty': 1,
            'product_uom': self.uom_dozen.id, 'picking_id': picking.id,
            'location_id': picking.location_id.id, 'location_dest_id': picking.location_dest_id.id,
        })
        second._action_confirm(merge=False)
        wizard = self._wizard(picking)
        for line in wizard.product_return_moves:
            line.quantity = 1
        action = wizard.action_create_returns()
        returned = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(len(returned.move_ids), 2)
        for move in returned.move_ids:
            self.assertEqual(move.product_uom, move.origin_returned_move_id.product_uom)
            self.assertEqual(move.product_uom_qty, 1)

    def test_native_exclusions_of_cancelled_and_inventory_moves(self):
        picking = self._picking()
        cancelled = self.env['stock.move'].create({
            'product_id': self.productB.id, 'product_uom_qty': 1,
            'product_uom': self.productB.uom_id.id, 'picking_id': picking.id,
            'location_id': picking.location_id.id, 'location_dest_id': picking.location_dest_id.id,
        })
        inventory = self.env['stock.move'].create({
            'product_id': self.productC.id, 'product_uom_qty': 1,
            'product_uom': self.productC.uom_id.id, 'picking_id': picking.id,
            'location_id': picking.location_id.id, 'location_dest_id': self.scrap_location.id,
        })
        cancelled._action_cancel()
        picking.action_confirm()
        wizard = self._wizard(picking)
        self.assertFalse(wizard.product_return_moves.move_id & (cancelled | inventory))
        self.assertEqual(wizard.product_return_moves.product_id, self.productA)

    def test_inventory_user_and_company_rules(self):
        picking = self._state_picking('confirmed')
        wizard = self._wizard(picking.with_user(self.user_stock_user))
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        returned = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(returned.company_id, picking.company_id)
        other_company = self.env['res.company'].create({'name': 'Other return company'})
        outsider = new_test_user(self.env, login='return19_other_company',
                                 groups='stock.group_stock_user',
                                 company_id=other_company.id,
                                 company_ids=[Command.set([other_company.id])])
        restricted = picking.with_user(outsider).with_context(allowed_company_ids=[other_company.id])
        self.assertFalse(restricted.has_access('read'))
        with self.assertRaises(AccessError):
            restricted._can_return()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self._wizard(restricted)

    def test_multiple_pickings_keep_native_single_origin_limit(self):
        first = self._state_picking('confirmed')
        second = self._state_picking('confirmed')
        with self.assertRaisesRegex(UserError, 'one picking at a time'), self.env.cr.savepoint():
            self.env['stock.return.picking'].with_context(
                active_id=first.id, active_ids=(first | second).ids,
                active_model='stock.picking',
            ).create({})

    def test_miac_subscription_dates_and_sale_links(self):
        if 'sale.subscription.plan' not in self.env or 'days_to_activate' not in self.env['product.product']._fields:
            self.skipTest('MIAC integration is checked when subscription activation is installed')
        partner = self.env['res.partner'].create({'name': 'MIAC return subscription customer'})
        plan = self.env['sale.subscription.plan'].create({
            'name': 'Return monthly', 'billing_period_value': 1, 'billing_period_unit': 'month',
        })
        service = self.env['product.product'].create({
            'name': 'MIAC recurring return service', 'type': 'service', 'recurring_invoice': True,
        })
        order = self.env['sale.order'].create({
            'partner_id': partner.id, 'warehouse_id': self.warehouse_1.id, 'plan_id': plan.id,
            'order_line': [Command.create({'product_id': service.id, 'product_uom_qty': 1, 'price_unit': 100}),
                           Command.create({'product_id': self.productA.id, 'product_uom_qty': 2, 'price_unit': 20})],
        })
        order.action_confirm()
        picking = order.picking_ids.filtered(lambda item: item.picking_type_code == 'outgoing')[:1]
        dates = order.start_date, order.next_invoice_date, order.end_date
        wizard = self._wizard(picking, form=True)
        wizard.unlink()
        self.assertEqual((order.start_date, order.next_invoice_date, order.end_date), dates)
        picking.move_ids.write({'quantity': 2, 'picked': True})
        picking.button_validate()
        dates = order.start_date, order.next_invoice_date, order.end_date
        wizard = self._wizard(picking)
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        returned = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(returned.sale_id, order)
        self.assertEqual(returned.move_ids.sale_line_id, picking.move_ids.sale_line_id)
        returned.move_ids.write({'quantity': 1, 'picked': True})
        returned.button_validate()
        self.assertEqual((order.start_date, order.next_invoice_date, order.end_date), dates)

    def test_purchase_links_remain_native(self):
        if 'purchase.order' not in self.env:
            self.skipTest('Purchase integration is checked when purchase_stock is installed')
        vendor = self.env['res.partner'].create({'name': 'MIAC return purchase supplier'})
        purchase = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [Command.create({'product_id': self.productA.id, 'product_qty': 2,
                                           'price_unit': 10, 'date_planned': fields.Datetime.now()})],
        })
        purchase.button_confirm()
        picking = purchase.picking_ids[:1]
        wizard = self._wizard(picking)
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        returned = self.env['stock.picking'].browse(action['res_id'])
        self.assertEqual(returned.move_ids.purchase_line_id, purchase.order_line)
        self.assertEqual(returned.move_ids.origin_returned_move_id, picking.move_ids)
