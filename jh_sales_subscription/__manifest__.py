# -*- coding: utf-8 -*-
{
    'name': "Personalizaciones MIAC - DAM",
    'summary': "Notificación de suscripciones próximas a vencer",
    'description': """
        Personalizaciones MIAC compatibles con Odoo 19.
        Conserva precios y descuentos negociados, condiciones de renovación,
        lotes, contactos de entrega, comisiones OCA manuales y por categoría,
        liquidaciones, visitas, adjuntos e históricos manuales.
        Facturación, consolidación y validaciones de renovación nativas de Odoo 19.
        Informes de facturas con costes por compañía, IVA y exportación XLSX/CSV.
        Histórico automático de consulta, sin regenerar datos al abrir contactos.
        Automatizaciones por lotes y avisos de vencimiento sin duplicados.
    """,
    'author': "JPHA - DAM",
    'website': "https://www.dammad.es",
    'category': 'Sales',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',

    # Módulos requeridos
    'depends': ['base', 'sale', 'mail', 'sale_subscription', 'miac_line_subscription', 'commission_oca', 'sale_commission_oca', 'commission_by_category', 'account', 'product', 'base_automation', 'purchase', 'contacts', 'sale_stock', 'sale_purchase', 'purchase_stock', 'account_payment_mode', 'account_commission_oca', 'sale_purchase_lot'],

    # Archivos cargados siempre (orden: jh_client_sheet antes de actions_jh_visit)
    'data': [
        'security/ir.model.access.csv',
        'security/jh_company_rules.xml',
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
