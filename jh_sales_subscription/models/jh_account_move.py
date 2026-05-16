from odoo import models, api, fields

class AccountMoveInherit (models.Model):
    _inherit = 'account.move'

    jh_country_id = fields.Many2one(related='partner_id.country_id', string='País', store=True)
    jh_state_id = fields.Many2one(related='partner_id.state_id', string='Provincia', store=True)
