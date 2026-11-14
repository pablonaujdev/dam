# Recepción IMAP sin alterar el estado de lectura

Módulo `jh_fetchmail_preserve_unread`. Disponible con el mismo nombre técnico,
modelo y campos para V17 (17.0.1.1.0) y V19 (19.0.1.1.0).

## Comportamiento

- No cambia el buzón del cliente, sus carpetas, sus alias ni su servidor SMTP.
- Es opcional por servidor entrante y está desactivado al instalarse.
- Abre INBOX mediante EXAMINE y descarga mediante UID FETCH BODY.PEEK[].
- Recoge mensajes nuevos tanto leídos como no leídos. No utiliza UNSEEN.
- Un UID pertenece a un servidor, carpeta y generación UIDVALIDITY concretos.
- Una huella SHA-256 de Message-ID, única en la base, impide que dos buzones
  importen simultáneamente el mismo mensaje. La huella y la importación se
  confirman juntas; si falla la importación, ambas se revierten.
- Guarda cada resultado y la importación en la misma transacción PostgreSQL.
- Utiliza un bloqueo de sesión por servidor, conservado entre commits.
- Impide inicializar dos servidores con la misma identidad de conexión.
- Procesa como máximo 50 mensajes por ejecución. Reserva hasta la mitad del lote
  para reintentos; los fallos no impiden recoger mensajes posteriores.
- Los fallos de procesamiento tienen tres intentos separados 15 minutos.
  Un administrador puede reiniciar los intentos desde los registros de recepción.
- Un mensaje eliminado en Outlook antes de descargarlo se registra como ausente.
- Los errores de conexión no consumen intentos de procesamiento: se vuelve a
  intentar en la siguiente ejecución del cron y se muestra el error del servidor.
- Un cambio de UIDVALIDITY o un retroceso de UIDNEXT detiene el proceso. Nunca
  reinicia automáticamente el punto de avance ni recorre el histórico.
- Conserva el enrutamiento nativo: el registro de UID no corrige alias, permisos
  de remitentes ni tokens OAuth. Las notificaciones quedan en cola.

## Instalación y activación manual

1. Instalar el módulo mediante Aplicaciones en un entorno de pruebas aislado.
   La instalación o actualización crea los campos y restricciones del módulo.
   El despliegue y la configuración del cliente se realizan por separado de las pruebas.
2. En pruebas, usar exclusivamente un buzón de prueba. No conectar staging ni
   Docker al buzón productivo: dos bases distintas no comparten los registros UID.
3. En el servidor entrante confirmado, abrir **Preserve read status** y activar
   **Preserve mailbox read status**. Guardar. Desde ese momento el recogedor se
   detiene hasta que se establezca el punto de inicio.
4. Conciliar los mensajes anteriores que deban importarse. El módulo no decide
   cuáles de los mensajes ya existentes son pendientes ni los importa al activarse.
5. Pulsar **Set starting point**. La confirmación excluye TODOS los mensajes que
   están entonces en INBOX, incluidos los no leídos. No descarga sus cuerpos.
6. A partir de ese punto, el cron habitual y **Fetch Now** utilizan el registro UID.
   Los mensajes que lleguen después se importan sin alterar sus marcas de lectura.
7. Revisar **Failed messages**, **Collection error** y **Collection receipts**.
   Corregir la causa antes de pulsar **Retry** en un mensaje fallido.

El modo, servidor y cuenta quedan protegidos después de inicializarse. Para
detenerlo, archivar el servidor; no desactivar el modo ni eliminar los registros
de recepción para volver al recogedor nativo, pues los mensajes siguen no leídos.
No desinstalar el módulo con el servidor activo. Cambiar de cuenta, reconciliar
UIDVALIDITY o retroceder el punto inicial exige una intervención controlada.

## Respuestas al buzón de cada remitente

Esta funcionalidad es opcional y no se activa al actualizar el módulo. No cambia
el SMTP, los permisos SendAs, los alias de Odoo ni la configuración de Microsoft 365.
La cuenta de Oficina se conserva para los hilos enviados antes del cambio.

Para cada cuenta personal, en **Ajustes → Técnico → Correo → Servidores de correo
de entrada**, un administrador debe:

1. Configurar y autorizar mediante OAuth su propia cuenta Microsoft 365 y usar
   **Probar y confirmar**. Usar el buzón personal, no copiar el token de Oficina.
2. Activar **Preserve mailbox read status** y **Only replies to Odoo documents**.
   Seleccionar el usuario interno en **Mailbox user**. Su correo debe coincidir
   con el login IMAP; alias de envío distintos del login no están soportados.
3. Conciliar pendientes y fijar **Set starting point**. Todo lo que ya existe
   en INBOX queda excluido, incluso los mensajes no leídos.
4. Solo después habilitar **Receive replies at sender address** y guardar.
5. Enviar un correo desde un documento Odoo con ese remitente. Comprobar en el
   mensaje recibido que **Reply-To / Responder a** contiene su dirección personal.
6. Responder desde otra cuenta, dejarlo sin leer y recoger. Verificar que llega
   al Outlook del usuario y al documento original una sola vez, incluso tras
   repetir la recogida; Outlook debe conservar el estado de lectura.

El destino depende del **remitente del mensaje**, no del usuario que ejecuta el
cron. Los envíos automáticos con un remitente habilitado usan la misma regla;
los demás conservan el destino nativo. Un `reply_to` explícito en plantillas o
integraciones se respeta: revisar las plantillas que fuerzan Oficina. La implementación
V19 también contempla la generación por lotes con remitentes diferentes.

Si se desactiva o cambia el correo del usuario, la dirección deja de utilizarse
para nuevos envíos. Antes de archivar/desconfirmar el servidor, deshabilitar
**Receive replies at sender address**. Las respuestas a mensajes ya enviados
seguirán llegando a esa cuenta: mantener su recogida hasta conciliar esos hilos.
Un token caducado requiere reautorización; el módulo no concede permisos de Microsoft.

### Recepción de respuestas y exclusiones

- **Processed**: respuesta asociada al documento original mediante References o
  In-Reply-To. Mantiene el enrutamiento y las comprobaciones de permisos nativas.
- **Unrelated message**: no hay referencia reconocida a un documento de Odoo.
  Se registra únicamente el recibo técnico; no se guarda su cuerpo ni adjuntos,
  no se crean documentos y no se envían rebotes por esos correos personales.
- **Already imported**: otra cuenta o recogida ya importó ese Message-ID.
- **Failed**: referencia a un documento eliminado, ruta rechazada, respuesta sin
  Message-ID u otro error. Se conserva el mecanismo de tres intentos y revisión.

Los avisos de correo a usuarios internos que ya figuran como destinatarios del
original se omiten para evitar una segunda copia en Outlook. Se conservan los
avisos a otros seguidores y las notificaciones internas de Odoo.

La recogida sigue limitada a **INBOX**. Las reglas de Outlook que mueven correos a
otra carpeta antes de recogerlos pueden impedir su importación. No se sincroniza
la carpeta Enviados: si el usuario contesta desde Outlook, su mensaje saliente no
se incorpora automáticamente al documento. Para registrar también esos envíos,
debe responder desde Odoo. Una respuesta sin referencias reconocibles queda omitida;
no se enlaza por asunto, para evitar asociar correspondencia al documento equivocado.

Los recibos antiguos y los puntos de inicio se conservan al actualizar. Los
anteriores mensajes importados se detectan por `mail.message.message_id`; no se
rellenan huellas de forma retroactiva ni se relee el histórico. Los fallos previos
no se reinician automáticamente. Para revisarlos: decidir si son respuestas o
correo ordinario antes de cambiar el modo o reintentarlos.

## Migración de Odoo 17 a 19

1. Detener la recogida en Odoo 17 antes del respaldo final.
2. Migrar la base completa con `jh.fetchmail.receipt`, sus claves únicas (incluida
   `jh_message_key`), usuarios, opciones de respuesta personal y los
   campos `jh_*` de `fetchmail.server`, conservando los IDs de servidor.
3. Usar el módulo de Odoo 19 y comprobar sus restricciones y vistas. Esta versión
   utiliza `_fetch_mail`, `_connect__`, `models.Constraint` y el progreso de cron
   propios de Odoo 19; no reemplaza los ficheros estándar de Odoo.
4. Comprobar que se conserva UIDVALIDITY y el último UID, sin volver a inicializar.
5. Habilitar la recogida en un solo entorno productivo. Mantener el servidor
   entrante archivado en las copias de staging y Docker.

## Pruebas

Sin Odoo ni base de datos:

```text
python jh_fetchmail_preserve_unread/tests/test_imap_inbox_standalone.py -v
```

El archivo `tests/test_fetchmail.py` añade pruebas TransactionCase de doble
recogida, rollback de registros parciales, tres fallos y reintento manual,
mensajes leídos, eliminación antes de descarga, protección de configuración,
UIDVALIDITY, UIDNEXT y bloqueo entre dos conexiones PostgreSQL.

`tests/test_personal_replies.py` comprueba el Reply-To, requisitos de activación,
importación real con adjuntos, exclusiones, duplicados, rollback/reintento,
notificaciones, rutas rechazadas y preservación de un Reply-To explícito.
Estas pruebas se ejecutan mediante el test runner en bases desechables.
No usar la base del cliente para esas pruebas.

La validación local del 13/11/2026 incluye Odoo 17 y 19, instalación/actualización
del módulo, pruebas ORM y SMTP/IMAP reales con GreenMail. También se verificó una
respuesta entregada a dos cuentas y recogida por dos conexiones PostgreSQL
simultáneas: un solo mensaje en Odoo y un recibo de duplicado.
Esto no sustituye la prueba piloto de OAuth y entrega en Microsoft 365 del cliente.

Antes de producción, validar también en un buzón de prueba Microsoft 365 que
EXAMINE y BODY.PEEK conservan las marcas observadas en Outlook, y probar el paso
de la última recogida V17 a la primera V19 sin nuevos registros duplicados.
