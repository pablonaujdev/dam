# -*- coding: utf-8 -*-
{
    'name': "MIAC Quantity Commission",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Commission',
    'description': '''
Muestra la cantidad de la línea de factura en la liquidación de comisiones.
Conserva el valor del documento original, también en facturas rectificativas.

Estructura técnica:
- models/commission_settlement_line.py: extiende commission.settlement.line.
- invoiced_quantity: Float relacionado con invoice_line_id.quantity, almacenado y readonly.
- views/: columna posterior a la factura en la lista del formulario de liquidación.
- i18n/es.po: etiquetas y ayuda en español; comisiones OCA de Odoo 19.

Lógica de negocio:
La cantidad sigue a la línea de factura; sin origen muestra cero.
La columna se muestra en liquidaciones de facturas a usuarios del grupo de facturación.
Una rectificativa conserva su cantidad: no se invierte su signo automáticamente.
No modifica importes, porcentajes ni cálculos de comisión, ni el PDF nativo OCA.
    ''',
    'summary': '''
        Cantidad facturada en líneas de liquidación de comisiones.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'account',
        'commission_oca',
        'account_commission_oca',
    ],
    'data': [
        'views/commission_settlement_line_view.xml',
    ],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
