# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sales commissions from salesman",
    "version": "19.0.1.0.0",
    "author": "Tecnativa, " "Odoo Community Association (OCA)",
    "category": "Sales",
    "website": "https://github.com/OCA/commission",
    "license": "AGPL-3",
    "summary": "Asigna el vendedor como agente cuando el cliente no aporta comisiones.",
    "description": """
        Completa agentes de ventas y facturas de cliente desde el vendedor.
        Conserva las comisiones existentes y la configuración OCA en Odoo 19.

        Estructura técnica:
        - models/res_partner.py: salesman_as_agent y validación de comisión.
        - models/sale_order.py y account_move.py: _prepare_agents_vals_partner.
        - views/res_partner_views.xml: opción en la ficha del agente OCA.
        - Reutiliza _prepare_agent_vals, también en la integración MIAC/JH.

        Lógica de negocio:
        Primero obtiene los agentes del cliente mediante el flujo OCA.
        Si no los hay, utiliza el contacto del vendedor marcado como agente
        automático y con comisión configurada. Excluye productos exentos,
        secciones, notas, compras y asientos ordinarios. No recalcula por
        cambiar el vendedor: se utiliza Regenerar agentes en documentos
        editables. Conserva el traslado de agentes a factura y no modifica
        históricos, liquidaciones ni datos al instalar o actualizar.
    """,
    "depends": ["sale_commission_oca", "account_commission_oca", "commission_oca"],
    "data": ["views/res_partner_views.xml"],
    "installable": True,
}
