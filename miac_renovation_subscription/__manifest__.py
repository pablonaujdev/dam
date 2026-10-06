# -*- coding: utf-8 -*-
{
    'name': "MIAC Renovation Subscription",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Adaptado a las APIs y vistas de Odoo 19; conserva los datos existentes.
        Generar el presupuesto 2 meses antes y hereda lot/num serie.
    ''',
    'summary': '''
        Generar el presupuesto 2 meses antes y hereda lot/num serie.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'sale_subscription', 'sale_purchase_lot',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_view.xml',
        'views/sale_order_view.xml',
        'views/sale_order_line_view.xml',
        'wizards/sale_order_cancel_wiz_view.xml',
        'datas/cron_renovation_subscription.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
