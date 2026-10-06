# -*- coding: utf-8 -*-
{
    'name': 'Error Line Wiz',
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'base',
    'summary': 'This module add a wizard messages with lines of error',
    'description': '''
        Presenta un resumen de errores con su detalle por línea.
        Conserva el asistente compartido de Avannubo en Odoo 19.

        Estructura técnica:
        - wizards/: modelos transitorios error.log.wiz y error.log.wiz.line.
        - error_log_wiz_view.xml: formulario y lista de detalle de solo lectura.
        - security/: acceso de usuarios internos y aislamiento transitorio nativo.

        Lógica de negocio:
        Los importadores pueden mostrar varios errores en el diálogo existente,
        sin crear modelos paralelos ni modificar registros de negocio. Conserva
        nombres técnicos, XML IDs y compatibilidad con otros módulos consumidores.
    ''',
    'author': 'Avannubo',
    'website': 'https://www.avannubo.com',
    'images': [
    ],
    'depends': [
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/error_log_wiz_view.xml',
    ],
    'qweb': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
