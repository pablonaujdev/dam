# Part of Avannubo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sale Purchase Notification',
    'version': '19.0.1.0.0',
    'summary': 'Avisos internos de compras de licencias al confirmar ventas',
    'description': """
Notifica al contacto configurado cuando una venta genera compras de licencias.
Genera un aviso en cola por venta sin bloquear su confirmación si falla el correo.

Estructura técnica:
- models/res_company.py conserva notify_purchase_license_id y su configuración.
- models/sale_order.py compara purchase_line_ids antes y después de action_confirm.
- datas/sale_purchase_email_template.xml conserva la plantilla con noupdate.
- views/res_company_view.xml muestra el destinatario junto al correo de compañía.
- Cada intento de correo usa un savepoint y la cola nativa, sin envío inmediato.

Lógica de negocio:
Solo avisa si la confirmación crea líneas de compra vinculadas a productos
recurrentes. No avisa por líneas anteriores ni por cambios de cantidades.
Utiliza exclusivamente el destinatario de la compañía de cada venta.
Si falta el destinatario, su correo o la plantilla, o falla su generación,
conserva la venta y las compras y registra una nota interna sin notificaciones.
No modifica plantillas personalizadas, documentos históricos ni sus datos.
""",
    'author': 'Avannubo',
    'website': 'http://www.avannubo.com',
    'license': 'AGPL-3',
    'category': 'Sales',
    'sequence': 1,
    'depends': ['sale_purchase', 'sale_subscription', 'mail'],
    'data': [
        'datas/sale_purchase_email_template.xml',
        'views/res_company_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
