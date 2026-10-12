# -*- coding: utf-8 -*-
{
    'name': "MIAC Purchase To Invoice",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'description': '''
Ofrece el acceso directo Pedidos a Facturar dentro de Compras.
Muestra únicamente pedidos con el estado nativo Pendiente de facturar.

Estructura técnica:
- views/purchase_order_view.xml: acción purchase.order y menú bajo Compras.
- La acción usa vistas nativas list/form y el dominio fijo invoice_status = to invoice.
- i18n/es.po: conserva la traducción española del acceso directo.
- No incorpora modelos, campos, permisos ni métodos de facturación.

Lógica de negocio:
El resultado sigue las políticas y cantidades facturables nativas de Odoo 19.
Las facturas en borrador, cancelaciones y rectificativas afectan al estado nativo.
El dominio obligatorio permanece aplicado al cambiar filtros de búsqueda.
No genera facturas ni modifica cantidades, estados, importes o accesos por compañía.
    ''',
    'summary': '''
        Generar una vista para las compras a facturar.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'purchase',
    ],
    'data': [
        'views/purchase_order_view.xml',
    ],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
