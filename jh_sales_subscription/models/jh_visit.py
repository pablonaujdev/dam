# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class JhVisit(models.Model):
    _name = 'jh.visit'
    _description = 'Visitas'
    _order = 'date desc, id desc'


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
