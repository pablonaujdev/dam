# License AGPL-3.0 or later. Original customization: Avannubo.
from odoo import api, fields, models
from . import report_sync


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    notes_print = fields.Html('Terms and Conditions', readonly=True, help='Conserva las condiciones de los pedidos para imprimirlas en el albaran.\nSolo se sincroniza automaticamente mientras el documento permanezca abierto.')
    client_ref = fields.Char('Client Ref', help='Agrupa las referencias de los pedidos de venta del albaran.\nRespeta las modificaciones manuales y los documentos finalizados.')
    supplier_ref = fields.Char('Supplier Ref', help='Agrupa las referencias de los pedidos de compra del albaran.\nRespeta las modificaciones manuales y los documentos finalizados.')

    @api.model_create_multi
    def create(self, vals_list):
        picks = super(StockPicking, self.with_context(miac_reports_skip_sync=True)).create(vals_list).with_env(self.env)
        explicit = {}
        for pick, vals in zip(picks, vals_list):
            sales, purchases = report_sync.source_orders(pick)
            seeds = {'client_ref': sales[:1].client_order_ref,
                     'supplier_ref': purchases[:1].partner_ref, 'notes_print': (sales or purchases)[:1].note}
            explicit[pick.id] = {field for field in seeds if field in vals and (vals[field] or False) != (seeds[field] or False)}
        report_sync.sync(picks, explicit=explicit, initial=True)
        return picks

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'sale_id', 'move_ids', 'purchase_id'} & set(vals):
            return super().write(vals)
        previous = report_sync.snapshot(self)
        result = super(StockPicking, self.with_context(miac_reports_skip_sync=True)).write(vals)
        explicit = {pick.id: set(vals) & {'client_ref', 'supplier_ref', 'notes_print'} for pick in self}
        report_sync.sync(self, previous, explicit)
        return result
