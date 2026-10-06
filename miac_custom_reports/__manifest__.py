# -*- coding: utf-8 -*-
{
    'name': "MIAC Custom Reports",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Reports',
    'description': '''
        Conserva los informes comerciales y logisticos MIAC en Odoo 19.
        Propaga referencias y condiciones sin sobrescribir textos manuales ni historicos.

        Estructura tecnica:
        - models/: ventas, compras, facturas, movimientos y albaranes; report_sync centraliza la propagacion.
        - views/: formularios y herencias QWeb de ventas, compras, facturas y entregas.
        - Hooks create/write/unlink por lotes y preparacion nativa de facturas y recepciones.
        - account_payment_sale aporta modos de pago en ventas; no se crean flujos paralelos.

        Logica de negocio:
        Agrupa referencias y notas distintas de todos los pedidos vinculados.
        Actualiza solo documentos abiertos cuyo texto sigue siendo automatico.
        Conserva direcciones, creador, lotes, referencias y cuentas enmascaradas en los PDF.
        Oculta los impuestos por linea sin modificar importes ni los totales fiscales.
        La seleccion por mandato SEPA requiere la migracion bancaria independiente.
    ''',
    'summary': '''
        Modificaciones de reports para MIAC.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'account',
        'sale',
        'purchase',
        'stock',
        'sale_stock',
        'purchase_stock',
        'account_payment_mode',
        'account_payment_sale',
        'sale_purchase_lot',
        'jh_sales_subscription',
    ],
    'data': [
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'views/sale_order_report_view.xml',
        'views/purchase_order_report_view.xml',
        'views/account_move_report_view.xml',
        'views/stock_picking_report_view.xml',
    ],
    'assets': {
    },
    'qweb': [],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
