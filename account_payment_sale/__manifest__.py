# Copyright 2014-2016 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# @author Alexis de Lattre <alexis.delattre@akretion.com>

{
    "name": "Account Payment Sale",
    "version": "19.0.1.0.0",
    "category": "Banking addons",
    "license": "AGPL-3",
    "summary": "Adds payment mode on sale orders",
    "author": "Akretion, " "Tecnativa, " "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment",
    "description": """
Conserva los modos de pago OCA en pedidos de venta de Odoo 19.
Traslada el modo a las facturas y evita consolidar modos incompatibles.

Estructura tecnica:
- models/sale_order.py: campo editable, compute por compania y hooks nativos de facturacion.
- models/sale_report.py: modo de pago en el analisis estandar de ventas.
- views/: formulario e informe QWeb; tests/: fixtures sin datos demo.
- Adaptacion local de la fuente OCA 17; no es una descarga oficial OCA 19.

Logica de negocio:
Propone el modo de cobro del cliente y admite su seleccion manual en el pedido.
La factura respeta el modo seleccionado y las reglas bancarias de account_payment_mode 19.
Las claves nativas de agrupacion se amplian con el modo de pago.
""",
    "depends": ["sale", "account_payment_mode"],
    "data": ["views/sale_order_view.xml", "views/sale_report_templates.xml"],
    "auto_install": True,
}
