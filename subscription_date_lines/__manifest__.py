# -*- coding: utf-8 -*-
{
    'name': "Subscriptions Date Lines",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Sale',
    'description': '''
        Conserva fechas individuales editables en las líneas de suscripción.
        Propone el plan del producto y protege los periodos particulares en Odoo 19.

        Estructura técnica:
        - models/: extensiones de sale.order, sale.order.line y product.template.
        - create/write: creación múltiple y sincronización de fechas sin SQL.
        - onchange: referencias transitorias para cambios sucesivos sin guardar.
        - views/: líneas del pedido y plan en los precios recurrentes del producto.
        - Sin acciones, modelos, componentes JS ni tareas automáticas adicionales.

        Lógica de negocio:
        Las líneas recurrentes heredan las fechas del contrato cuando no se
        indican expresamente. Los cambios de cabecera conservan fechas manuales.
        Renovaciones y upsells comienzan con el periodo del nuevo pedido.
        Se propone un único plan predeterminado; los conflictos requieren
        selección manual y se respetan plantillas, planes y ventas únicas.
        Las fechas de línea son de seguimiento: cantidades, periodos e importes
        de facturación siguen el flujo nativo de Odoo 19. partial_invoice conserva
        sus datos históricos sin bloquear fechas ni forzar cantidades.
    ''',
    'summary': '''
        Fechas por línea de suscripción y plan predeterminado del producto.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'sale',
        'sale_subscription'
    ],
    'data': [
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
    ],
    'qweb': [],
    'assets': {},
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
