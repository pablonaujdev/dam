from odoo import models, api, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    jh_client_sheet_ids = fields.One2many('jh.client.sheet',
                                          'parent_id',
                                          string='Histórico de Ventas',
                                          compute='_compute_jh_client_sheet_ids',
                                          store=False)

    def _compute_jh_client_sheet_ids(self):
        for record in self:
            if not record.id:
                record.jh_client_sheet_ids = [(6, 0, [])]
                continue

            # 1) limpiar
            self.env.cr.execute("""
                DELETE FROM jh_client_sheet WHERE parent_id = %s
            """, [record.id])

            # 2) (opción A) insertar en bloque con INSERT...SELECT  (más rápido)
            self.env.cr.execute("""
                INSERT INTO jh_client_sheet
                    (parent_id, jh_date, jh_account_move, jh_product_id, jh_quantity_sold, jh_amount_bruto, jh_sale_lot_id)
                SELECT
                    %s as parent_id,
                    a."date",
                    b.id,
                    a.product_id,
                    CASE WHEN b.name ILIKE %s THEN (a.quantity * -1) ELSE a.quantity END,
                    CASE WHEN b.name ILIKE %s THEN (a.price_subtotal * -1) ELSE a.price_subtotal END,
                    a.sale_lot_id
                FROM account_move_line a
                JOIN account_move b ON a.move_id = b.id
                WHERE a.product_id IS NOT NULL
                  AND (b.name ILIKE %s OR b.name ILIKE %s)
                  AND a.partner_id = %s
                  and b.state = 'posted'
                ORDER BY a.date DESC
            """, [record.id, 'RFV%', 'RFV%', 'FV%', 'RFV%', record.id])

            # 3) cargar ids insertados y ASIGNAR el compute
            self.env.cr.execute("""
                SELECT id FROM jh_client_sheet WHERE parent_id = %s ORDER BY jh_date DESC, id
            """, [record.id])
            ids = [row[0] for row in self.env.cr.fetchall()]

            record.jh_client_sheet_ids = [(6, 0, ids)]

class jh_client_sheet(models.Model):
    _name = 'jh.client.sheet'
    _description = 'Histórico de ventas por cliente/producto'
    _order = 'jh_quantity_sold desc'

    parent_id = fields.Many2one('res.partner', string='Cliente', index=True, ondelete='cascade')
    jh_date = fields.Date(string='Fecha')
    jh_account_move = fields.Many2one('account.move', string='Factura')
    jh_product_id = fields.Many2one('product.product', string='Producto')
    jh_quantity_sold = fields.Float(string='Cantidad Vendida')
    jh_amount_bruto = fields.Float(string='Importe Ventas (Sin IVA)')
    jh_sale_lot_id = fields.Char(string='Lote Num Serie')

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
