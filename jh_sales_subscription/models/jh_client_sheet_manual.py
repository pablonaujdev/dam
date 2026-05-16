# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartnerInheritManualSheet(models.Model):
    _inherit = 'res.partner'

    jh_manual_sheet_ids = fields.One2many(
        'jh.client.sheet.manual',
        'parent_id',
        string='Histórico Manual',
        copy=False,
    )


class JhClientSheetManual(models.Model):
    _name = 'jh.client.sheet.manual'
    _description = 'Histórico manual de ventas por cliente (diligenciamiento manual)'
    _order = 'jh_date desc, id desc'

    @api.model
    def _auto_init(self):
        """Elimina la foreign key constraint si existe antes de cambiar el tipo de campo."""
        # Ejecutar antes de que Odoo procese los campos
        cr = self.env.cr
        table_name = self._table
        
        # Verificar si la tabla existe
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [table_name])
        table_exists = cr.fetchone()[0]
        
        if table_exists:
            # Buscar todas las constraints de foreign key en la columna jh_account_move
            cr.execute("""
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = %s
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND kcu.column_name = 'jh_account_move'
            """, [table_name])
            
            constraints = cr.fetchall()
            
            # Eliminar todas las constraints encontradas
            for constraint_row in constraints:
                constraint_name = constraint_row[0]
                try:
                    cr.execute(f"""
                        ALTER TABLE {table_name} 
                        DROP CONSTRAINT IF EXISTS {constraint_name} CASCADE
                    """)
                    _logger.info(f"Constraint {constraint_name} eliminada exitosamente")
                except Exception as e:
                    # Log pero no fallar si la constraint ya no existe
                    _logger.warning(f"No se pudo eliminar constraint {constraint_name}: {e}")
        
        # Llamar al metdo padre para que Odoo procese los campos normalmente
        return super()._auto_init()

    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente comercial',
        related='parent_id.commercial_partner_id',
        store=False,
        readonly=True,
    )

    parent_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        index=True,
        ondelete='cascade',
    )
    jh_date = fields.Date(string='Fecha')
    jh_account_move = fields.Char(
        string='Factura',
        help='Número de factura (ingreso manual)',
    )
    jh_product_id = fields.Many2one(
        'product.product',
        string='Producto',
    )
    jh_quantity_sold = fields.Float(string='Cantidad Vendida')
    jh_amount_bruto = fields.Float(string='Importe Ventas (Sin IVA)')
    jh_sale_lot_id = fields.Char(string='Lote Num Serie')

    def action_attach_invoice_pdf(self):
        """Abre un diálogo para adjuntar un PDF de factura."""
        self.ensure_one()
        # Buscar si ya existe un attachment para esta línea
        existing_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], limit=1)
        
        return {
            'name': 'Adjuntar PDF de Factura',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'form',
            'target': 'new',
            'res_id': existing_attachment.id if existing_attachment else False,
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_name': f'Factura_{self.jh_account_move or "N/A"}.pdf',
                'default_type': 'binary',
                'default_mimetype': 'application/pdf',
            },
        }

    def action_view_invoice_pdf(self):
        """Abre el PDF adjunto de la factura."""
        self.ensure_one()
        # Buscar el attachment asociado a esta línea
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], limit=1)
        
        if not attachment:
            raise UserError('No hay PDF adjunto para esta línea.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    def _compute_has_pdf_attachment(self):
        """Calcula si hay un PDF adjunto."""
        for rec in self:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', rec._name),
                ('res_id', '=', rec.id),
            ], limit=1)
            rec.has_pdf_attachment = bool(attachment)
    
    has_pdf_attachment = fields.Boolean(
        string='Tiene PDF',
        compute='_compute_has_pdf_attachment',
        store=False,
    )
    
    @api.model
    def create(self, vals_list):
        recs = super().create(vals_list)
        return recs
    
    def write(self, vals):
        res = super().write(vals)
        return res

    def _get_lot_from_invoice_line(self, invoice_line):
        """Obtiene el lote/serie de una línea de factura (misma lógica que commission_settlement_line)."""
        if not invoice_line:
            return None
        try:
            if hasattr(invoice_line, 'jh_sale_lot_id') and invoice_line.jh_sale_lot_id:
                val = invoice_line.jh_sale_lot_id
                if isinstance(val, models.Model):
                    return val.name or str(val) or None
                return str(val).strip() or None
        except Exception:
            pass
        try:
            if hasattr(invoice_line, 'lot_id') and invoice_line.lot_id:
                return invoice_line.lot_id.name or None
        except Exception:
            pass
        sale_line = None
        try:
            if hasattr(invoice_line, 'sale_line_ids') and invoice_line.sale_line_ids:
                sale_line = invoice_line.sale_line_ids[0]
            else:
                sale_line = self.env['sale.order.line'].search([
                    ('invoice_lines', 'in', invoice_line.id)
                ], limit=1)
        except Exception:
            pass
        if sale_line:
            try:
                if hasattr(sale_line, 'lot_id') and sale_line.lot_id:
                    return sale_line.lot_id.name or None
            except Exception:
                pass
            try:
                move_lines = self.env['stock.move.line'].search([
                    ('move_id.sale_line_id', '=', sale_line.id),
                    ('product_id', '=', invoice_line.product_id.id),
                ])
                lot_names = move_lines.mapped('lot_id.name')
                if lot_names:
                    return ', '.join(filter(None, lot_names))
            except Exception:
                pass
        return None

