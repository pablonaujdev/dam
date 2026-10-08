# -*- coding: utf-8 -*-
{
    'name': "Personalizaciones MIAC - DAM",
    'summary': "Notificación de suscripciones próximas a vencer",
    'description': """
        Gestiona personalizaciones comerciales y de suscripciones de MIAC.
        Conserva las condiciones negociadas de precio y descuento en los pedidos.

        Estructura técnica:
        - models/jh_sale_order_line.py: sale.order y sale.order.line.
        - write de sale.order.line protege precio y descuento manuales al cambiar la cantidad.
        - models/jh_partner_subscription.py y vistas de contactos: suscripciones por dirección de entrega.
        - views/jh_sale_subscription_views.xml: búsqueda de licencias por cliente donde está.
        - models/jh_invoice_report_wizard.py: filtros del Excel por categoría y tipo de cliente.
        - models/jh_sale_order_line.py: estado de facturación según líneas y facturas vinculadas.

        Lógica funcional:
        La tarifa recalcula los valores automáticos, mientras los valores negociados
        permanecen en el pedido y se trasladan a la factura.
        Las direcciones de entrega muestran sus suscripciones en curso en la ficha y el kanban.
        La lista de licencias permite buscar por su dirección de entrega.
        El Excel de facturas admite categorías de producto y facturas de clientes o proveedores.
        El estado de facturación usa las líneas del pedido, también en renovaciones.
        El recálculo actualiza primero el estado de las líneas, sin modificar cantidades
        ni períodos, y respeta el cierre de las líneas recurrentes ya renovadas.
        Corrige estados pendientes con cantidad cero únicamente cuando las facturas
        contabilizadas cubren la cantidad neta y el período, descontando rectificativas.
        Permite limitar el recálculo a los pedidos que actualmente están a facturar.
        Las suscripciones con inicio futuro muestran su primer período pendiente
        como a facturar y reconocen los períodos contabilizados en sus líneas.
        Valida que la fecha de fin no sea anterior al inicio y permite limitar
        la actualización diaria de estados a las suscripciones activas.
        La prefacturación manual respeta el fin del contrato y no fuerza
        la generación de facturas para períodos posteriores a su vencimiento.
    """,
    'author': "JPHA - DAM",
    'website': "https://www.dammad.es",
    'category': 'Sales',
    'version': '17.0.0.7.4',
    'license': 'LGPL-3',

    # Módulos requeridos
    'depends': ['base', 'sale', 'mail', 'sale_subscription', 'miac_line_subscription', 'commission', 'sale_commission', 'commission_by_category', 'account', 'product', 'base_automation', 'purchase'],

    # Archivos cargados siempre (orden: jh_client_sheet antes de actions_jh_visit)
    'data': [
        'security/ir.model.access.csv',
        'data/cron_renovation_advice.xml',
        'data/cron_sale_order_invoice_status.xml',
        'data/cron_commission_liq_date.xml',
        'data/invoice_lot_sync_automation.xml',
        'views/jh_client_sheet_view.xml',
        'views/actions_jh_account_move.xml',
        'views/actions_jh_account_invoice_report.xml',
        'views/actions_jh_sales_subscription.xml',
        'views/actions_jh_res_partner.xml',
        'views/actions_jh_sale_order.xml',
        'views/actions_jh_commission_visibility.xml',
        'views/actions_jh_commission_settlement_line.xml',
        'views/actions_jh_invoice_report_wizard.xml',
        'views/actions_jh_subscription_price_confirmation_wizard.xml',
        'views/actions_jh_visit.xml',
        'views/jh_sale_subscription_views.xml',
        'views/actios_jh_stock_picking.xml',
        'views/menus.xml',
        'reports/jh_commission_settlement_report.xml',
    ],

    'installable': True,
    'application': True,
}
