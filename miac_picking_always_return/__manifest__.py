# Part of Avannubo. License AGPL-3.
{
    'name': 'MIAC Picking Always Return',
    'version': '19.0.1.0.0',
    'summary': 'Devoluciones desde albaranes pendientes o realizados',
    'description': """
Permite devolver albaranes confirmados, en espera, preparados y realizados.
Reutiliza el asistente nativo sin escribir artificialmente el estado del origen.

Estructura técnica:
- models/stock_picking.py extiende stock.picking._can_return() con super().
- wizards/stock_picking_return.py comprueba el estado antes de _create_return().
- Las líneas del asistente se calculan con los permisos del usuario, sin sudo.
- views/stock_picking_view.xml adapta la visibilidad del botón nativo.
- No añade campos, modelos de negocio, permisos ni acciones paralelas.

Lógica de negocio:
Permite devoluciones de entregas, recepciones y transferencias internas
pendientes o realizadas. Los borradores y cancelados no admiten devolución,
incluso si su estado cambia mientras el asistente permanece abierto.
Las cantidades comienzan en cero y se seleccionan manualmente o mediante
Devolver todo con el cálculo de Odoo 19, que puede devolver cero en pendientes.
Crear una devolución no valida ni completa automáticamente el albarán original.
Ubicaciones, reservas, lotes, series, unidades y vínculos siguen el flujo nativo.
""",
    'author': 'Avannubo',
    'website': 'http://www.avannubo.com',
    'license': 'AGPL-3',
    'sequence': 1,
    'category': 'Inventory',
    'depends': ['stock'],
    'data': ['views/stock_picking_view.xml'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
