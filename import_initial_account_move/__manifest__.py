# -*- coding: utf-8 -*-
{
    'name': 'Import Initial Account Move',
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'account',
    'summary': 'Importa asientos equilibrados desde Excel y conserva su identificador de origen.',
    'description': '''
        Importa asientos contables desde la plantilla Excel de Avannubo.
        Valida el archivo completo y crea movimientos en borrador en Odoo 19.

        Estructura técnica:
        - wizards/: import.initial.account.move.wiz; import_xls_file y validación.
        - models/account_move.py: identificador de origen y restricción única.
        - static/data/Import_Account_Move.xlsx: plantilla de siete columnas.
        - views/ y security/: menú original y acceso exclusivo de contabilidad.
        - Lectura en memoria con openpyxl y creación ORM en un único savepoint.

        Lógica de negocio:
        Agrupa las líneas por ASIENTO, utiliza la fecha contable del asistente
        y conserva FECHA como vencimiento. Exige cuentas compatibles, contactos
        exactos y equilibrio en moneda de compañía. Rechaza duplicados nuevos
        y referencias antiguas. Los errores se muestran con error_line_wiz;
        un fallo no deja asientos parciales. No contabiliza, concilia ni añade
        contrapartidas. No rellena identificadores históricos al actualizar.
    ''',
    'author': 'Avannubo',
    'website': 'https://www.avannubo.com',
    'images': [
    ],
    'depends': [
        'account',
        'error_line_wiz',
    ],
    'external_dependencies': {'python': ['openpyxl']},
    'data': [
        'security/ir.model.access.csv',
        'wizards/import_account_move_wiz_view.xml',
        'views/account_menu_view.xml',
    ],
    'qweb': [
    ],
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
