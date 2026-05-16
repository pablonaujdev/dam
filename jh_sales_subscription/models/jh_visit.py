# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class JhVisit(models.Model):
    _name = 'jh.visit'
    _description = 'Visitas'
    _order = 'date desc, id desc'

    @api.model
    def _auto_init(self):
        """Elimina la foreign key constraint si existe antes de cambiar el tipo de campo."""
        cr = self.env.cr
        table_name = self._table

        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [table_name])
        table_exists = cr.fetchone()[0]

        if table_exists:
            cr.execute("""
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = %s
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND kcu.column_name = 'commercial_id'
            """, [table_name])

            constraints = cr.fetchall()
            for constraint_row in constraints:
                constraint_name = constraint_row[0]
                try:
                    cr.execute(f"""
                        ALTER TABLE {table_name} 
                        DROP CONSTRAINT IF EXISTS {constraint_name} CASCADE
                    """)
                    _logger.info(f"Constraint {constraint_name} eliminada exitosamente")
                except Exception as e:
                    _logger.warning(f"No se pudo eliminar constraint {constraint_name}: {e}")

        return super()._auto_init()

    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
    )
    commercial_id = fields.Char(
        string='Comercial',
        required=True,
    )
    alert = fields.Char(
        string='Alerta',
    )
    codigo_taller = fields.Char(
        string='Código Taller',
    )
    code = fields.Char(
        string='Código',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        index=True,
        ondelete='cascade',
    )
    observations = fields.Text(
        string='Observaciones',
    )


class ResPartnerInheritVisits(models.Model):
    _inherit = 'res.partner'

    jh_visit_ids = fields.One2many(
        'jh.visit',
        'partner_id',
        string='Visitas',
        copy=False,
    )
