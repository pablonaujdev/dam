from odoo import models, api, fields

class AccountMoveInherit (models.Model):
    _inherit = 'account.move'

    jh_country_id = fields.Many2one(related='partner_id.country_id', string='País', store=True)
    jh_state_id = fields.Many2one(related='partner_id.state_id', string='Provincia', store=True)

    def _jh_sync_invoice_lot_to_sale_lines(self):
        for move in self:
            if not move.is_sale_document(include_receipts=True) or move.state != 'draft':
                continue
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type in (False, 'product') and l.sale_line_ids
            ):
                if len(line.sale_line_ids) == 1:
                    sale_line = line.sale_line_ids[:1]
                    if sale_line.lot_id != line.jh_sale_lot_id:
                        sale_line.with_context(skip_invoice_lot_sync=True).write({
                            'lot_id': line.jh_sale_lot_id.id or False,
                        })

    def write(self, vals):
        res = super().write(vals)
        if vals.get('invoice_line_ids') or vals.get('line_ids'):
            self._jh_sync_invoice_lot_to_sale_lines()
        return res

    def action_post(self):
        self._jh_sync_invoice_lot_to_sale_lines()
        return super().action_post()
