from odoo import models, fields
from odoo.tools import SQL
from odoo.exceptions import UserError


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    jh_client_sheet_ids = fields.One2many(
        'jh.client.sheet', 'parent_id', string='Histórico de Ventas', readonly=True,
        help='Consulta las ventas contabilizadas del contacto.\nLos abonos conservan el signo negativo del histórico MIAC.')


class JhClientSheet(models.Model):
    _name = 'jh.client.sheet'
    _description = 'Histórico de ventas por cliente/producto'
    _auto = False
    _order = 'jh_quantity_sold desc'

    parent_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    jh_date = fields.Date(string='Fecha', readonly=True)
    jh_account_move = fields.Many2one('account.move', string='Factura', readonly=True)
    jh_product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    jh_quantity_sold = fields.Float(string='Cantidad Vendida', readonly=True)
    jh_amount_bruto = fields.Float(string='Importe Ventas (Sin IVA)', readonly=True)
    jh_sale_lot_id = fields.Char(string='Lote Num Serie', readonly=True)
    jh_company_id = fields.Many2one('res.company', readonly=True,
        help='Compañía de la factura de origen.\nLimita la consulta a las compañías permitidas al usuario.')

    @property
    def _table_query(self):
        return SQL("""
            SELECT line.id, line.partner_id AS parent_id, line.date AS jh_date,
                   move.id AS jh_account_move, line.product_id AS jh_product_id,
                   CASE WHEN move.name ILIKE %s THEN -line.quantity ELSE line.quantity END AS jh_quantity_sold,
                   CASE WHEN move.name ILIKE %s THEN -line.price_subtotal ELSE line.price_subtotal END AS jh_amount_bruto,
                   line.sale_lot_id AS jh_sale_lot_id, line.company_id AS jh_company_id
              FROM account_move_line line JOIN account_move move ON move.id = line.move_id
             WHERE line.product_id IS NOT NULL AND move.state = 'posted'
               AND (move.name ILIKE %s OR move.name ILIKE %s)
        """, 'RFV%', 'RFV%', 'FV%', 'RFV%')

    def action_invoice_pdf(self):
        """Abre la factura en PDF (misma lógica que el botón de imprimir factura)."""
        self.ensure_one()
        if not self.jh_account_move:
            raise UserError('No hay factura asociada a esta línea.')
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        if not report:
            report = self.env.ref('account.action_report_invoice', raise_if_not_found=False)
        if report:
            return report.report_action(self.jh_account_move)
        if hasattr(self.jh_account_move, 'action_invoice_print'):
            return self.jh_account_move.action_invoice_print()
        raise UserError('No se encontró el reporte de factura.')
