# License AGPL-3.0 or later. Original customization: Avannubo.
from odoo import api, fields, models
from . import report_sync


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank', compute='_compute_partner_bank_id', store=True, readonly=False, check_company=True, tracking=True, ondelete='restrict', help='Selecciona una cuenta de la empresa para mostrarla en el pedido.\nConserva una seleccion manual valida y limita la cuenta a la compania del documento.')
    bank_partner_id = fields.Many2one('res.partner', compute='_compute_bank_partner_id', help='Identifica el contacto bancario de la empresa del pedido.\nSe utiliza para seleccionar cuentas de la compania correspondiente.')

    @api.depends('company_id', 'company_id.partner_id')
    def _compute_bank_partner_id(self):
        for order in self:
            order.bank_partner_id = order.company_id.partner_id

    @api.depends('company_id', 'company_id.partner_id', 'company_id.partner_id.bank_ids', 'company_id.partner_id.bank_ids.company_id')
    def _compute_partner_bank_id(self):
        for order in self:
            banks = order.bank_partner_id.bank_ids.filtered(lambda bank: not bank.company_id or bank.company_id == order.company_id)
            if order.partner_bank_id not in banks:
                order.partner_bank_id = banks[:1]

    def partner_banks_to_show(self):
        self.ensure_one()
        mode = self.payment_mode_id
        if not mode:
            return self.env['res.partner.bank']
        if report_sync.is_sepa(self):
            # Optional until the independent OCA mandate migration is accepted.
            return report_sync.mandate_bank(self)
        if mode.show_bank_account_from_journal:
            journals = mode.fixed_journal_id if mode.bank_account_link == 'fixed' else mode.variable_journal_ids
            return journals.filtered(lambda journal: journal.company_id == self.company_id).bank_account_id
        return self.partner_bank_id.filtered(lambda bank: bank.partner_id == self.company_id.partner_id
            and (not bank.company_id or bank.company_id == self.company_id))

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        values['client_ref'] = self.client_order_ref
        return values

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'client_order_ref', 'note'} & set(vals):
            return super().write(vals)
        invoices, pickings = report_sync.related_documents(self)
        old_invoices, old_pickings = report_sync.snapshot(invoices), report_sync.snapshot(pickings)
        result = super().write(vals)
        report_sync.sync(invoices, old_invoices)
        report_sync.sync(pickings, old_pickings)
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

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
