# License AGPL-3.0 or later. Original customization: Avannubo.
from odoo import api, fields, models
from . import report_sync


class AccountMove(models.Model):
    _inherit = 'account.move'

    client_ref = fields.Char('Client Ref', help='Agrupa las referencias de los pedidos del cliente.\nSe conserva en documentos contabilizados y cuando se modifica manualmente.')
    supplier_ref = fields.Char('Supplier Ref', help='Agrupa las referencias de los pedidos del proveedor.\nSe conserva en documentos contabilizados y cuando se modifica manualmente.')

    def partner_banks_to_show(self):
        self.ensure_one()
        if report_sync.is_sepa(self):
            return report_sync.mandate_bank(self)
        return super().partner_banks_to_show()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self.with_context(miac_reports_skip_sync=True)).create(vals_list).with_env(self.env)
        explicit = {}
        for move, vals in zip(moves, vals_list):
            sales, purchases = report_sync.source_orders(move)
            first = (sales or purchases)[:1]
            seeds = {'client_ref': sales[:1].client_order_ref,
                     'supplier_ref': purchases[:1].partner_ref, 'narration': first.note}
            # Native preparation supplies the first order's text. Preserve distinct manual inputs.
            explicit[move.id] = {field for field in seeds if field in vals and (vals[field] or False) != (seeds[field] or False)}
        report_sync.sync(moves, explicit=explicit, initial=True)
        return moves

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'invoice_line_ids', 'line_ids'} & set(vals):
            return super().write(vals)
        previous = report_sync.snapshot(self)
        result = super(AccountMove, self.with_context(miac_reports_skip_sync=True)).write(vals)
        explicit = {move.id: set(vals) & {'client_ref', 'supplier_ref', 'narration'} for move in self}
        report_sync.sync(self, previous, explicit)
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('miac_reports_skip_sync'):
            return super().create(vals_list)
        moves = self.env['account.move'].browse([vals['move_id'] for vals in vals_list if vals.get('move_id')])
        previous = report_sync.snapshot(moves)
        lines = super().create(vals_list)
        report_sync.sync(moves | lines.move_id, previous)
        return lines

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'move_id', 'sale_line_ids', 'purchase_line_id'} & set(vals):
            return super().write(vals)
        moves = self.move_id | self.env['account.move'].browse(vals.get('move_id') or [])
        previous = report_sync.snapshot(moves)
        result = super().write(vals)
        report_sync.sync(moves | self.move_id, previous)
        return result

    def unlink(self):
        if self.env.context.get('miac_reports_skip_sync'):
            return super().unlink()
        moves = self.move_id
        previous = report_sync.snapshot(moves)
        result = super().unlink()
        report_sync.sync(moves, previous)
        return result
