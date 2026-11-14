{
    'name': 'MIAC - Recepcion IMAP sin alterar lectura',
    'summary': 'Respuestas al remitente y recepcion sin alterar lectura ni duplicar',
    'version': '17.0.1.1.0',
    'author': 'JPHA - DAM',
    'website': 'https://www.dammad.es',
    'license': 'LGPL-3',
    'category': 'Discuss',
    'description': """
Conserva la lectura de los buzones y permite responder al remitente original.
Incorpora las respuestas a documentos de Odoo una sola vez, incluso entre cuentas.

Estructura tecnica:

- imap_inbox.py: seleccion de INBOX en solo lectura, UIDVALIDITY, UIDNEXT y BODY.PEEK.
- models/fetchmail_server.py: modo opcional de fetchmail.server, punto de inicio,
  bloqueo por sesion PostgreSQL, lotes de 50 y tres intentos separados 15 minutos.
- models/fetchmail_receipt.py: jh.fetchmail.receipt, identificador unico por servidor,
  INBOX, UIDVALIDITY y UID; huella unica de Message-ID entre buzones, atomica con la importacion.
- models/mail_thread.py: Reply-To por remitente habilitado, validacion de ruta al
  documento original y exclusion de notificaciones a usuarios que ya recibieron el correo.
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
En modo solo respuestas se omiten mensajes sin referencia a una conversacion de
Odoo. Las referencias a documentos eliminados o las rutas rechazadas quedan como
fallos revisables. No se crean registros de negocio por correos personales ajenos.
Para dirigir respuestas al remitente se configura su usuario interno, cuyo correo
debe coincidir con el login IMAP. Se autoriza, confirma e inicializa cada buzon
antes de habilitar la opcion. Cuentas no habilitadas conservan el Reply-To nativo;
las direcciones Reply-To indicadas expresamente por una plantilla se respetan.
La cuenta de Oficina debe seguir recogiendo las respuestas de conversaciones previas.
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
