# -*- coding: utf-8 -*-

from odoo import fields, models, _, api



class ErrorLogWizLine(models.TransientModel):

    _name = "error.log.wiz.line"
    _description = "Error Log Wiz Line"

    error = fields.Char(string='Error', help="Explica el error de una fila o registro procesado.\nPermite identificar qué información debe corregirse antes de repetir.")
    wiz_id = fields.Many2one('error.log.wiz', ondelete='cascade', help="Relaciona el detalle con su asistente de errores.\nEl detalle transitorio se elimina junto con el asistente.")







