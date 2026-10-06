# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools import float_compare, float_round, float_repr


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    default_for_lot = fields.Boolean(string="Default For Lot", default=False)






