# -*- coding: utf-8 -*-
# See README.rst file on addon root folder for license details
from odoo import models, fields


class ProductAgentCommission(models.Model):

    _name = 'product.category.agent.commission'
    _description = 'Product Agent Commission'


    categ_id = fields.Many2one(comodel_name="product.category", string="Category")
    agent_id = fields.Many2one(comodel_name="res.partner", string="Agent", domain=[('agent','=',True)])
    commission_id = fields.Many2one(comodel_name="commission", string="Commission")


