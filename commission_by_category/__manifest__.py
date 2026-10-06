# -*- coding: utf-8 -*-
{
    'name': "Commission by Category",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Adaptado a las APIs y vistas de Odoo 19; conserva los datos existentes.
        Permite tener comisiones especificas por categorìa.
    ''',
    'summary': '''
        Permite tener comisiones especificas por categorìa.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'commission_oca',
        'sale_commission_oca',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
        'views/res_partners_views.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
