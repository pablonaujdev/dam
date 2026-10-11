# -*- coding: utf-8 -*-
{
    'name': "Avannubo Declaración Responsable",
    'sequence': 1,
    'version': '19.0.1.0.0',
    'category': 'Base',
    'description': '''
        Muestra en Ajustes la declaración responsable original de Avannubo.
        Conserva su firma y el mensaje informativo del plan de facturación.

        Estructura técnica:
        - views/res_config_settings_view.xml hereda res.config.settings de base_setup.
        - El bloque nativo se sitúa después de Acerca de, con sus permisos existentes.
        - static/src/webclient/res_config_settings_template_view.xml extiende
          la plantilla res_config_edition en web.assets_backend de Odoo 19.
        - static/src/imgs/firma.png conserva la firma del respaldo sin modificaciones.
        - No añade modelos, campos, métodos, menús ni reglas de acceso.

        Lógica funcional:
        Los administradores consultan el texto firmado y el mensaje del plan en
        Ajustes generales. El contenido se conserva literalmente desde el origen.
    ''',
    'summary': '''
        Añade en Ajustes una declaración responsable.
    ''',
    'author': "Avannubo",
    'website': "http://www.avannubo.com",
    'depends': [
        'base',
        'base_setup',
        'web',
    ],
    'data': [
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'avannubo_declaracion_responsable/static/src/webclient/*.xml',
        ]
    },
    "license": "AGPL-3",
    'application': True,
    'installable': True,
    'auto_install': False,
}
