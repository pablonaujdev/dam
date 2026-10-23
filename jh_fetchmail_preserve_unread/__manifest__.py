{
    'name': 'MIAC - Recepcion IMAP sin alterar lectura',
    'summary': 'Recoge correos una sola vez sin cambiar su estado en Outlook',
    'version': '19.0.1.0.0',
    'author': 'JPHA - DAM',
    'website': 'https://www.dammad.es',
    'license': 'LGPL-3',
    'category': 'Discuss',
    'description': """
Conserva el estado de lectura del buzon compartido al recibir correos en Odoo.
Evita recoger de nuevo los mensajes mediante un registro persistente de UID IMAP.

Estructura tecnica:
- imap_inbox.py: seleccion de INBOX en solo lectura, UIDVALIDITY, UIDNEXT y BODY.PEEK.
- models/fetchmail_server.py: modo opcional de fetchmail.server, punto de inicio,
  bloqueo por sesion PostgreSQL, lotes de 50 y tres intentos separados 15 minutos.
- models/fetchmail_receipt.py: jh.fetchmail.receipt, identificador unico por servidor,
  INBOX, UIDVALIDITY y UID; registro de resultado atomico con message_process.
- views/: configuracion del servidor y consulta administrativa de incidencias.
- tests/: protocolo IMAP y pruebas de integracion del recogedor con IMAP simulado.

Logica de negocio:
La instalacion no activa servidores ni modifica sus credenciales o alias.
El administrador fija expresamente el punto de inicio antes de recoger mensajes:
el historico anterior queda fuera y los pendientes deben conciliarse antes del corte.
Despues se recogen mensajes nuevos, leidos o no, sin cambiar flags ni moverlos.
Los fallidos se revierten y reintentan; tras tres intentos requieren revision manual.
Un cambio de UIDVALIDITY detiene la recogida para conciliar antes de continuar.
Las notificaciones generadas quedan en cola, sin envio SMTP dentro de la importacion.
El registro y el punto de inicio deben migrarse junto con la base a Odoo 19.
""",
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/fetchmail_receipt_views.xml',
        'views/fetchmail_server_views.xml',
    ],
    'installable': True,
    'application': False,
}
