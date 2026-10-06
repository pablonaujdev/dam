# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    months_renovation = fields.Integer(string='Months for renovation', default=2)








