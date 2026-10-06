# -*- coding: utf-8 -*-
{
    'name': "Sale Purchase Lot",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Adaptado a las APIs y vistas de Odoo 19; conserva los datos existentes.
        Añade el número de serie el las licencias de compra de un producto.
    ''',
    'summary': '''
        Añade el número de serie el las licencias de compra de un producto.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'sale',
        'purchase',
        'stock', 'sale_stock', 'sale_purchase', 'purchase_stock', 'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/account_move_view.xml',
        'wizards/link_machine_wiz_view.xml',
        'datas/product_template_data.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
