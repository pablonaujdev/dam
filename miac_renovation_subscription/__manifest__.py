# -*- coding: utf-8 -*-
{
    'name': "MIAC Renovation Subscription",
    'sequence': 1,
    'version': '19.0.1.0.1',
    'category': 'Sale',
    'description': '''
        Prepara presupuestos de renovación con la anticipación de cada compañía.
        Conserva lotes y condiciones en las líneas renovadas de Odoo 19.

        Estructura técnica:
        - models/sale_order.py: cron y preparación nativa de renovación/upsell.
        - models/sale_order_line.py: fechas de contrato y referencias de origen.
        - views/, wizards/ y datas/: configuración, cancelación y cron.

        Lógica de negocio:
        Genera una renovación pendiente por contrato y conserva las condiciones
        mediante parent_line_id. Corrige coincidencias ambiguas de productos
        con el mismo precio usando su lote, conservando las claves nativas de
        moneda, unidad y plan. Si no hay una coincidencia única, no asigna una
        línea de otro lote. No altera precios, cantidades ni periodos facturables.
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
