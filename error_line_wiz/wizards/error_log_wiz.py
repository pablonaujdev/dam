# -*- coding: utf-8 -*-

from odoo import fields, models, _, api



class ErrorLogWiz(models.TransientModel):

    _name = "error.log.wiz"
    _description = "Error Log Wiz"

    message = fields.Char(string='Error', help="Muestra el resumen del resultado fallido de una operación.\nEl detalle se presenta en las líneas del asistente compartido.")
    error_line_ids = fields.One2many('error.log.wiz.line', 'wiz_id', help="Enumera los errores detectados durante la operación.\nCada línea conserva el mensaje del módulo que utiliza el asistente.")









