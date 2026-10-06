# -*- coding: utf-8 -*-
{
    'name': "Sale Subscription Start Date",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Ajusta las fechas de activación del contrato tras cada entrega completada.
        Conserva los días por producto y categoría y el calendario de V17 en Odoo 19.

        Estructura técnica:
        - models/product_category.py: propagación de days_to_activate.
        - models/product_template.py: creación múltiple, categoría y valores explícitos.
        - models/stock_picking.py: _action_done y fecha prevista por zona de compañía.
        - views/: campos existentes de producto, categoría y fecha de inicio nativa.
        - Reutiliza subscription_plan_default y sincronización de subscription_date_lines.

        Lógica de negocio:
        Cada entrega positiva a cliente recalcula inicio y próxima factura desde
        su fecha prevista más el máximo de días de los productos entregados.
        El fin es el inicio más una recurrencia nativa. Se aplica también con
        facturas contabilizadas, sin cambiarlas: puede retroceder el calendario.
        Excluye devoluciones, traslados, presupuestos, upsells y contratos cerrados.
        Los asistentes pendientes no activan y las fechas particulares de línea
        se conservan. No fuerza cantidades, prorrateos ni conversiones históricas.
    ''',
    'summary': '''
        Activación del contrato desde cada entrega completada y días de producto/categoría.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'sale',
        'sale_subscription',
        'stock',
        'sale_stock',
        'sale_subscription_stock',
        'subscription_date_lines',
    ],
    'data': [
        'views/sale_order_view.xml',
        'views/product_category_view.xml',
        'views/product_template_view.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
