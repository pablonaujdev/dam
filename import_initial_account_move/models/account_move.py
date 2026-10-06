# Original customization: Avannubo. License AGPL-3.
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    import_initial_asiento = fields.Char(string='Imported entry identifier', copy=False, index=True, help="Conserva el identificador ASIENTO del archivo de apertura importado.\nImpide duplicados en la misma compañía, diario y fecha contable.")

    _import_initial_asiento_unique = models.Constraint(
        'UNIQUE(company_id, journal_id, date, import_initial_asiento)',
        'An imported entry identifier already exists for this company, journal and accounting date.',
    )
