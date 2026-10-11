# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Fiscal Position Autodetect optional VIES",
    "version": "19.0.1.0.0",
    "description": """
Separa las posiciones fiscales automáticas según el resultado VIES del contacto.
Conserva la clasificación con/sin VIES válido y las reglas nativas de Odoo 19.

Estructura técnica:
- models/account_fiscal_position.py extiende account.fiscal.position y conserva
  vat_vies_required mediante el hook nativo _get_fpos_validation_functions.
- views/account_fiscal_position_view.xml muestra la casilla junto a NIF requerido.
- tests/test_account_fiscal_position_vies.py verifica selección, facturas e integración.
- No modifica search, contactos ni verificaciones externas de base_vat.

Lógica funcional:
Las posiciones marcadas corresponden al contacto comercial con VIES válido;
las desmarcadas corresponden al contacto sin VIES válido, también las genéricas.
Se respeta la dirección efectiva elegida por Odoo, las posiciones manuales,
el país, la provincia, el código postal, la compañía y la secuencia.
La comprobación nativa NIF/VIES de la compañía permanece activa y los datos
existentes no se recalculan al instalar ni actualizar el módulo.
""",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["victoralmau"],
    "website": "https://github.com/OCA/account-fiscal-rule",
    "depends": [
        "account",
        "base_vat",
    ],
    "data": ["views/account_fiscal_position_view.xml"],
    "external_dependencies": {},
    "application": True,
    "installable": True,
    "auto_install": False,
}
