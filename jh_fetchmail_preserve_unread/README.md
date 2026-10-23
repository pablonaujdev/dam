# Recepción IMAP sin alterar el estado de lectura

Módulo `jh_fetchmail_preserve_unread`. Disponible con el mismo nombre técnico,
modelo y campos en `staging` (17.0.1.0.0) y `staging_v19` (19.0.1.0.0).

## Comportamiento

- No cambia el buzón del cliente, sus carpetas, sus alias ni su servidor SMTP.
- Es opcional por servidor entrante y está desactivado al instalarse.
- Abre INBOX mediante EXAMINE y descarga mediante UID FETCH BODY.PEEK[].
- Recoge mensajes nuevos tanto leídos como no leídos. No utiliza UNSEEN.
- Un UID pertenece a un servidor, carpeta y generación UIDVALIDITY concretos.
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
   La instalación crea las tablas y campos del módulo. Este trabajo entrega el
   código; no ejecuta instalaciones ni actualizaciones de bases de datos.
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

## Migración de Odoo 17 a 19

1. Detener la recogida en Odoo 17 antes del respaldo final.
2. Migrar la base completa con `jh.fetchmail.receipt`, sus claves únicas y los
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

Estas pruebas requieren instalar el módulo en una base desechable y ejecutar
el test runner de la versión correspondiente; están preparadas, no ejecutadas
contra una base existente. No usar la base del cliente para esas pruebas.

Antes de producción, validar también en un buzón de prueba Microsoft 365 que
EXAMINE y BODY.PEEK conservan las marcas observadas en Outlook, y probar el paso
de la última recogida V17 a la primera V19 sin nuevos registros duplicados.
