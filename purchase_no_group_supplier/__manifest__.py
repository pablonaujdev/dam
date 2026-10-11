# -*- coding: utf-8 -*-
{
    'name': "Supplier No group supplier",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'description': '''
Separa las compras automáticas de pedidos de venta distintos por proveedor.
Permite agrupar líneas de una misma venta y mantiene la reposición nativa.

Estructura técnica:
- res.partner conserva no_group_purchase y su configuración existente.
- stock.rule extiende _make_po_get_domain con relaciones y dominios de Odoo 19.
- sale.order.line divide compras de servicios por compañía y venta, y amplía
  el dominio nativo para excluir compras vinculadas a otras ventas.
- purchase_order_domain centraliza la selección de compras de una sola venta.
- La vista del contacto conserva el XML ID y las pruebas cubren servicios,
  aprovisionamiento, compañías y compatibilidad MIAC.

Lógica funcional:
Con la casilla marcada, las ventas distintas no comparten compra. Se reutilizan
solo borradores compatibles de la misma venta, respetando las reglas nativas.
Desmarcada se utiliza el flujo estándar de Odoo 19, que ya separa servicios.
Las reposiciones sin venta utilizan la agrupación nativa en ambos casos.
No se reorganizan compras históricas ni se modifican contactos al instalar.
    ''',
    'summary': 'Separa las compras automáticas por pedido de venta y proveedor.',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'sale_purchase',
        'purchase_stock',
        'sale_purchase_stock',
    ],
    'data': [
        'views/res_partner_view.xml',
    ],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
