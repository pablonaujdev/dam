# -*- coding: utf-8 -*-
{
    'name': "MIAC Line Subscription",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Adaptado a las APIs y vistas de Odoo 19; conserva los datos existentes.
        Generar una vista para líneas de subscripciones.
    ''',
    'summary': '''
        Generar una vista para líneas de subscripciones.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'miac_renovation_subscription',
    ],
    'data': [
        'views/sale_order_line_view.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
