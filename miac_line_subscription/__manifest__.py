# -*- coding: utf-8 -*-
{
    'name': "MIAC Line Subscription",
    'sequence': 1,
    'version': '19.0.1.0.1',
    'category': 'Sale',
    'description': '''
        Permite consultar las licencias y líneas de suscripción de MIAC.
        Recupera las fechas particulares de cada línea en Odoo 19.

        Estructura técnica:
        - models/sale_order_line.py: estado relacionado de la suscripción.
        - views/sale_order_line_view.xml: lista, filtros y acción de licencias.
        - Dependencias: miac_renovation_subscription y subscription_date_lines.

        Lógica de negocio:
        Muestra date_subs_start y date_subs_end como en el módulo original,
        junto con contrato, categoría, lote y estado. Conserva los campos
        relacionados de fecha del contrato, sus datos y los XML IDs existentes.
    ''',
    'summary': '''
        Generar una vista para líneas de subscripciones.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'miac_renovation_subscription',
        'subscription_date_lines',
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
