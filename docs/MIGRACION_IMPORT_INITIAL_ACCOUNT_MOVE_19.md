# import_initial_account_move — migración a Odoo 19

Fecha: 2026-10-06. Rama: `staging_v19`.

## Resultado

Implementados e instalados `import_initial_account_move` y `error_line_wiz`,
ambos con versión **19.0.1.0.0**. Instalación y actualización verificadas en
Docker aislado. La aceptación con datos reales de MIAC queda pendiente.

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons`,
instalación `C:\Program Files\Odoo 19.0e.20260105` y repositorio actual.
Se conservan autoría, metadatos de licencia originales, nombres técnicos,
XML IDs, menú, campos existentes y método `import_xls_file`.

## Uso y validaciones

El asistente admite `.xlsx` y `.xlsm`; lee la primera hoja en memoria mediante
`openpyxl`, declarado como dependencia Python. Las primeras siete columnas
deben conservar este orden:

| Columna | Comportamiento |
| --- | --- |
| ASIENTO | Identificador obligatorio; agrupa líneas aunque no sean consecutivas |
| FECHA | Vencimiento obligatorio de la línea: fecha Excel, YYYY-MM-DD o DD/MM/YYYY |
| DEBIT | Importe numérico, finito y no negativo |
| CREDIT | Importe numérico, finito y no negativo |
| Empresa | Nombre exacto de un único contacto activo y compatible |
| CUENTA | Código obligatorio de una cuenta activa y accesible en la compañía |
| DESCRIPCION | Concepto de la línea; sin contenido se utiliza «Imported» |

- La fecha contable procede del asistente; no de FECHA.
- Se ignoran filas completamente vacías y se incluye la última fila.
- Los códigos escritos como texto conservan ceros iniciales. Los números
  enteros no reciben `.0`. Identificadores y códigos admiten hasta 128 caracteres.
- Las fórmulas requieren resultados calculados guardados en el archivo.
  El importador no calcula fórmulas: hay que recalcular y guardar en Excel.
- Una línea no admite debe y haber simultáneamente positivos. Cada grupo
  debe equilibrarse con la precisión de la moneda de compañía.
- No se generan contrapartidas. `account_dif_id` permanece oculto e inactivo.
- Los asientos se crean en borrador, sin contabilizar ni conciliar.
- Las cuentas se resuelven mediante los patrones `company_ids` de Odoo 19,
  dentro de la compañía del diario y sus reglas de acceso. Se rechazan diarios
  inactivos o fuera de las compañías permitidas y cuentas/diarios en otra moneda.
- Con Empresa informada, el contacto debe existir y ser único. Sin Empresa,
  las cuentas de clientes/proveedores se rechazan; otras cuentas la admiten vacía.
- No se crean cuentas o contactos. Acceso exclusivo para usuarios y
  administradores contables, sin `sudo()`.

La plantilla mantiene `static/data/Import_Account_Move.xlsx` y contiene un
ejemplo equilibrado de 100 al debe y 100 al haber en líneas distintas.
**Antes de usarla, sustituir las cuentas, el contacto y el vencimiento por los
datos correspondientes a la compañía de destino.**

## Atomicidad y duplicados

Se valida todo el archivo antes de crear movimientos. La creación completa
ocurre en un único `savepoint`, mediante comandos ORM y comprobaciones nativas.
Si falla un asiento, no queda ningún asiento de ese intento; otras operaciones
de la transacción se conservan. Se retiró el `rollback()` global y la lógica
que desactivaba controles contables.

El nuevo campo `account.move.import_initial_asiento` es no copiable. La
restricción nativa `account_move_import_initial_asiento_unique` impide repetir
compañía, diario, fecha contable e identificador, también con dos importaciones
simultáneas. Los asientos ordinarios conservan el campo vacío y quedan fuera
de este control. El mismo identificador es válido con otra fecha, diario o compañía.

También se detectan referencias antiguas exactas
`Import Accounting Entries <ASIENTO>` en la misma compañía, diario y fecha.
La actualización no rellena identificadores históricos ni modifica asientos
existentes. Los errores de validación indican fila y asiento; los errores de
creación identifican el asiento que estaba creándose.

`error_line_wiz` conserva sus modelos compartidos y permisos de usuarios
internos para otros consumidores, incluido el futuro `miac_import_wurth`.
Se adaptó su lista a Odoo 19 y se mantiene el detalle de solo lectura.

## Archivos principales

- `import_initial_account_move/__manifest__.py`: versión, descripción y dependencia Python.
- `import_initial_account_move/models/account_move.py`: identificador y restricción única.
- `import_initial_account_move/wizards/import_account_move_wiz.py`: lectura, validación y creación.
- Vistas y seguridad del importador: interfaz existente y acceso contable.
- `import_initial_account_move/static/data/Import_Account_Move.xlsx`: ejemplo corregido.
- `import_initial_account_move/tests/test_import19.py`: 14 pruebas funcionales.
- Manifest, modelo transitorio y vista de `error_line_wiz`: adaptación a 19.
- `tools/validate_jh_odoo19.py`: incorporación de ambos módulos a la revisión estática.
- `tools/test_initial_import_concurrency19.py`: prueba real con dos transacciones.

## Evidencia de validación

| Comprobación | Resultado |
| --- | --- |
| Instalación de error_line_wiz y después del importador en miac_import19_clean | Correcta |
| Actualización de ambos módulos en la base limpia | Correcta; 14 pruebas, 0 fallos, 0 errores |
| Instalación integrada en miac_v19 y regresiones JH | 24 pruebas: 14 del importador + 10 de JH, 0 fallos, 0 errores |
| Actualización final de ambos módulos en miac_v19 | Correcta, salida 0 |
| Dos transacciones concurrentes con el mismo identificador | Un asiento; segundo intento rechazado; bloqueo del índice único observado |
| Limpieza de la prueba concurrente | Cero asientos temporales restantes |
| Estado de miac_v19 después de las pruebas | Cero asientos y cero pedidos; contenedor healthy |
| Acceso autenticado y descarga HTTP de la plantilla | HTTP 200; SHA-256 idéntico al archivo del repositorio |
| Validación estática y git diff --check | Correctos |

Las pruebas cubren grupos no consecutivos, filas vacías/finales, fechas,
códigos, archivos defectuosos y fórmulas sin resultado; cuentas y contactos
inválidos; moneda y compañía; descuadres; duplicados actuales/antiguos;
permisos; reversión de creación parcial; vistas y plantilla. Incluyen un
fallo nativo provocado en el segundo asiento para comprobar la reversión del lote
y la conservación de operaciones ajenas al importador.

Las pruebas negativas del índice único generan mensajes SQL de error esperados
en el log; el resultado de las suites es **cero fallos y cero errores**.

Evidencia y respaldo en `C:\Proyectos FL\DAM\miac_v19`:

- `initial-import-clean-verified.log`
- `initial-import-miac-tests.log`
- `initial-import-miac-update.log`
- `initial-import-concurrency.log`
- `miac_v19-before-initial-import-20261006.dump`
- `miac_v19-before-initial-import-filestore-20261006.tar.gz`

El ensayo está disponible en `http://localhost:8079`. El ejecutor de crons
permanece deshabilitado con `max_cron_threads=0` aunque haya registros cron activos.
No hay servidores de correo saliente activos y SMTP apunta a `127.0.0.1:1`.

### Repetir las pruebas

Desde `C:\Proyectos FL\DAM\miac_v19`, detener primero el servicio web para
ejecutar las pruebas sin otro proceso Odoo sobre la misma base:

```powershell
docker compose stop web
docker compose run --rm --no-deps web -u error_line_wiz,import_initial_account_move,jh_sales_subscription --test-enable --test-tags initial_import19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/initial-import-repeat.log
docker compose up -d web
```

La herramienta de concurrencia solo acepta `miac_import19_clean`: prepara
datos propios mediante ORM, confirma las transacciones necesarias para probar
la concurrencia y elimina sus registros al finalizar. No admite la base MIAC.

## Límites y pendientes

- Validar posteriormente una copia de MIAC migrada a 19 y la aceptación del usuario.
- No se ejecutaron conversiones ni importaciones sobre datos del cliente.
- No se actualizaron libros de presupuesto o seguimiento.
- No se modificó el código de JH ni se creó ningún commit.

Commit recomendado: `[IMP] #xxxxxx Migra importación de asientos a Odoo 19`.
