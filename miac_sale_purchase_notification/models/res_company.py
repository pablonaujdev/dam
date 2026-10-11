# Part of Avannubo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    notify_purchase_license_id = fields.Many2one('res.partner', string='License purchase notification recipient', help='Receives the license purchase notice generated when confirming a sale.\nA single valid email is required; missing configuration does not block confirmation.')
