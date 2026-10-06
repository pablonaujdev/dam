# License AGPL-3.0 or later. Original customization: Avannubo.
from odoo import models
from . import report_sync


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        values['supplier_ref'] = self.partner_ref
        return values

    def _prepare_picking(self):
        values = super()._prepare_picking()
        values.update(supplier_ref=self.partner_ref, notes_print=self.note)
        return values

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'partner_ref', 'note'} & set(vals):
            return super().write(vals)
        invoices, pickings = report_sync.related_documents(self)
        old_invoices, old_pickings = report_sync.snapshot(invoices), report_sync.snapshot(pickings)
        result = super().write(vals)
        report_sync.sync(invoices, old_invoices)
        report_sync.sync(pickings, old_pickings)
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or 'order_id' not in vals:
            return super().write(vals)
        invoices, pickings = report_sync.line_documents(self)
        before_invoices, before_pickings = report_sync.snapshot(invoices), report_sync.snapshot(pickings)
        result = super().write(vals)
        report_sync.sync(invoices, before_invoices)
        report_sync.sync(pickings, before_pickings)
        return result

    def unlink(self):
        invoices, pickings = report_sync.line_documents(self)
        before_invoices, before_pickings = report_sync.snapshot(invoices), report_sync.snapshot(pickings)
        result = super().unlink()
        report_sync.sync(invoices, before_invoices)
        report_sync.sync(pickings, before_pickings)
        return result
