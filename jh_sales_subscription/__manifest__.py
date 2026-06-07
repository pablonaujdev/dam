# -*- coding: utf-8 -*-
{
    'name': "Personalizaciones MIAC - DAM",
    'summary': "Notificación de suscripciones próximas a vencer",
    'description': """
        Notificación automática de suscripciones próximas a vencer por correo electrónico.
    """,
    'author': "JPHA - DAM",
    'website': "https://www.dammad.es",
    'category': 'Sales',
    'version': '0.1',
    'license': 'LGPL-3',

    # Módulos requeridos
    'depends': ['base', 'sale', 'mail', 'sale_subscription', 'commission', 'sale_commission', 'account', 'product', 'base_automation'],

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
        'views/actions_jh_commission_settlement_line.xml',
        'views/actions_jh_invoice_report_wizard.xml',
        'views/actions_jh_subscription_price_confirmation_wizard.xml',
        'views/actions_jh_visit.xml',
        'views/jh_sale_subscription_views.xml',
        'views/menus.xml',
        'reports/jh_commission_settlement_report.xml',
    ],

    'installable': True,
    'application': True,
}
