# -*- coding: utf-8 -*-
{
    'name': "MIAC Purchase Pricelist Menu",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'description': '''
Ofrece el acceso Tarifas de Proveedor dentro de Compras y Productos.
Conserva la lista MIAC y permite mantener tarifas mediante el formulario nativo.

Estructura técnica:
- views/product_supplierinfo_view.xml: lista de product.supplierinfo, acción y menú.
- La acción abre primero la lista MIAC y después el formulario nativo de Odoo 19.
- El contexto muestra el producto en el formulario independiente.
- i18n/es.po: traducción española del acceso; dependencia única de purchase.

Lógica de negocio:
Conserva las columnas, orden y opcionales de V17, sin edición en línea o masiva.
No aplica filtros predeterminados de vigencia ni de productos activos.
Mantiene precios, variantes, monedas, descuentos y reglas de selección nativas.
La unidad del precio y la compañía se consultan en el formulario nativo.
No añade campos, modelos, permisos, automatizaciones ni reglas de cálculo.
    ''',
    'summary': '''
        Generar una vista para las tarifas de proveedor.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'purchase',
    ],
    'data': [
        'views/product_supplierinfo_view.xml',
    ],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
