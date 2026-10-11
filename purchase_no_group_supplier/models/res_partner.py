# -*- coding: utf-8 -*-
# Part of Avannubo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    no_group_purchase = fields.Boolean(string='No Group Purchase', default=True,
        help=("Separates automatic purchases from different sales orders for this vendor.\n"
              "Lines of one sale can share a compatible draft purchase; replenishment without sales follows native rules."))


