# License AGPL-3. Original customization: Avannubo.
{
    'name': 'Stock Picking Images',
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Imágenes de producto en ventas y albaranes pendientes',
    "description": """
Muestra miniaturas del producto en las líneas de ventas y operaciones de albaranes.
Incluye imágenes en informes de ventas y en la tabla principal de albaranes pendientes.

Estructura técnica:
- models/: conserva image relacionado con product_id.image_128 en tres modelos.
- Campos de solo lectura, no almacenados y calculados con permisos del usuario.
- views/: listas de Odoo 19 y herencias QWeb de informes nativos con prioridad 180.
- Secciones y combinaciones mantienen sus columnas, incluyendo lotes MIAC.

Lógica de negocio:
Muestra la imagen actual de cada producto y respeta la imagen de la variante.
Las miniaturas en pantalla miden 48 x 48 px; en impresión no superan 80 pt por lado.
Las filas sin imagen y los resúmenes agrupados permanecen vacíos en esa columna.
El albarán imprime imágenes únicamente en su tabla principal cuando está pendiente.
No amplía las tablas de realizados, lotes, paquetes ni pendientes de entrega parcial.
No modifica cantidades, precios, impuestos, importes, adjuntos ni documentos históricos.
""",
    'author': 'Avannubo',
    'website': 'http://www.avannubo.com',
    'depends': ['sale', 'stock'],
    "data": [
        'views/sale_order_view.xml',
        'views/sale_order_report.xml',
        'views/stock_picking_view.xml',
        'views/stock_picking_report.xml',
    ],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
}
