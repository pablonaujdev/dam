# MIAC — Registro de correcciones de base para Odoo Upgrade 17 → 19

Fecha: 12/10/2026. Entorno autorizado en este ensayo: base `miac`, PostgreSQL
`miac17-db`. Este documento no autoriza ejecutar cambios en producción.

## Orden de ejecución

1. Preparar una copia V17 con código V17, mantener correo bloqueado y crons
   desactivados, y terminar las actualizaciones de módulos del origen.
2. Detener el servicio web y conservar un respaldo completo de la base, así como
   el filestore correspondiente. Guardar hash, fecha, versión y logs del ensayo.
3. Ejecutar exclusivamente las correcciones aprobadas para esa fase, por orden.
   Cada incidencia debe tener precondiciones, transacción y comprobación posterior.
4. Exportar nuevamente la base corregida y cargar ese nuevo SQL a Odoo Upgrade.
   El SQL enviado antes del ajuste no cambia automáticamente.
5. Repetir el servicio de upgrade, incorporar la siguiente incidencia confirmada
   y registrar el resultado. No borrar campos en bloque por similitud de errores.
6. Sobre la base devuelta por Odoo, aplicar la correspondencia de módulos y
   actualizar los addons V19 conforme al plan revisado. Esa fase es distinta
   de estas correcciones de origen; no ejecutarla sobre V17.
7. Validar datos, filestore y funciones antes de autorizar producción.

Las correcciones probadas deben ejecutarse sobre la copia final de producción
antes del último envío, con su respaldo propio. No reutilizar el dump del ensayo
como si fuera la base final del cliente.

## Registro

| ID | Fase | Incidencia | Ajuste | Estado |
|---|---|---|---|---|
| 001 | Origen V17, antes del envío | `sale.subscription.report.payment_mode_id` atribuido a `sale_subscription` | Reasignar únicamente el XML ID a `account_payment_sale` | Aplicado; el intento #4786089 avanzó hasta V19 sin repetir este bloqueo |
| 002 | Copia V17 final, antes del envío | CHECK OCA `account_move_name_state_diagonal` incompatible con un estado transitorio del upgrade | Retirar solo ese CHECK, sin modificar documentos | Aplicado y comprobado localmente; siguiente intento remoto pendiente |

## 001 — Campo heredado de modo de pago en el análisis de suscripciones

### Error y causa

Solicitud de ensayo Odoo Upgrade #4782313. El proceso hacia V19 se detuvo durante
su paso intermedio por V18, al procesar datos técnicos obsoletos:

```text
It looks like you forgot to call util.remove_field on the following fields:
sale.subscription.report.payment_mode_id
```

En las fuentes V17, `account_payment_sale/models/sale_report.py` declara
`sale.report.payment_mode_id`. `sale.subscription.report` hereda `sale.report`
y usa `_auto = False`: es un análisis, no una tabla de documentos de negocio.
La reflexión de campos de V17 crea XML IDs para campos heredados también bajo
el módulo que introduce el modelo hijo. En la copia se encontró:

| Elemento | Valor anterior | Valor posterior |
|---|---|---|
| Campo | ID 14437, `sale.subscription.report.payment_mode_id` | Conservado |
| Tipo / relación | `many2one` / `account.payment.mode` | Conservados |
| XML ID, ID interno 61396 | `sale_subscription.field_sale_subscription_report__payment_mode_id` | `account_payment_sale.field_sale_subscription_report__payment_mode_id` |
| `noupdate` | `False` | Conservado |

El servidor de upgrade no carga los addons OCA/personalizados del origen.
El campo heredado aparecía atribuido al módulo estándar actualizado y entraba
en su limpieza. Se corrige su propiedad técnica para identificarlo como parte
del addon que aporta la función. No se ejecuta `util.remove_field`, no se
elimina `ir_model_fields`, no se desinstala ningún módulo ni se toca una columna.

La copia examinada no tenía la vista SQL `sale_subscription_report`; el script
no depende de su existencia y no la crea. Los valores comerciales de modos de
pago residen en `sale_order` y `account_move`, que permanecen intactos.

### Prevalidación de lectura

```sql
SELECT f.id, f.model, f.name, f.ttype, f.relation, f.state,
       d.id AS xmlid_id, d.module, d.name AS xmlid, d.noupdate
FROM ir_model_fields f
LEFT JOIN ir_model_data d ON d.model = 'ir.model.fields' AND d.res_id = f.id
WHERE f.model IN ('sale.order', 'sale.report', 'sale.subscription.report', 'account.move')
  AND f.name = 'payment_mode_id'
ORDER BY f.model, d.id;
```

Revisar que los dos módulos estén instalados y que el campo de análisis tenga
exactamente el XML ID esperado. El script comprueba esas condiciones y la
versión V17, bloquea colisiones y revierte ante una desviación. No utiliza IDs
fijos: los IDs de la tabla anterior son evidencia de este ensayo.

### Respaldo y ejecución local

Los siguientes comandos corresponden exclusivamente a los nombres verificados
del Docker local. Adaptar contenedor, usuario, base y rutas en cada entorno.
El script `.sql` contiene metacomandos de `psql`; ejecutarlo con `psql`, no
pegarlo directamente en un editor que no admita esos metacomandos.

```powershell
docker stop miac17-web-1
docker exec miac17-db pg_dump -U odoo -d miac -Fc -f /tmp/miac_before_001.dump
docker cp miac17-db:/tmp/miac_before_001.dump 'C:\RUTA_RESPALDO\miac_before_001.dump'
docker exec miac17-db pg_restore --list /tmp/miac_before_001.dump
Get-FileHash -Algorithm SHA256 'C:\RUTA_RESPALDO\miac_before_001.dump'

docker cp 'C:\Proyectos FL\FL repos\dam\scripts\migration\001_payment_mode_report_xmlid.sql' miac17-db:/tmp/001_payment_mode_report_xmlid.sql
docker exec miac17-db psql -X -U odoo -d miac -v ON_ERROR_STOP=1 -f /tmp/001_payment_mode_report_xmlid.sql

# Exportar mientras el origen permanece detenido.
docker exec miac17-db pg_dump -U odoo -d miac --no-owner --no-acl -f /tmp/miac_upgrade_001.sql
docker cp miac17-db:/tmp/miac_upgrade_001.sql 'C:\RUTA_EXPORTACION\miac_upgrade_001.sql'
docker start miac17-web-1
```

Completar las rutas antes de ejecutar. La exportación SQL no incluye los archivos
del filestore. Conservarlos para restaurar el ensayo y desplegar la base migrada.

### Script completo

La copia ejecutable está en `scripts/migration/001_payment_mode_report_xmlid.sql`.
El contenido completo se reproduce al final de este documento para consolidar
las correcciones en un único MD. Si se modifica el script, sincronizar ambas
copias y volver a registrar las pruebas.

### Reversión de esta corrección

Solo si se necesita volver al estado previo en una copia V17 y no se han aplicado
otros cambios posteriores, detener el web, verificar el XML ID y ejecutar:

```sql
BEGIN;
SET LOCAL lock_timeout = '10s';
DO $rollback$
DECLARE target_id integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Reversion limitada al origen V17';
    END IF;
    SELECT d.id INTO target_id
    FROM ir_model_data d JOIN ir_model_fields f
      ON d.model = 'ir.model.fields' AND d.res_id = f.id
    WHERE d.module = 'account_payment_sale'
      AND d.name = 'field_sale_subscription_report__payment_mode_id'
      AND f.model = 'sale.subscription.report' AND f.name = 'payment_mode_id'
    FOR UPDATE OF d;
    IF target_id IS NULL THEN RAISE EXCEPTION 'No existe el estado posterior esperado'; END IF;
    IF EXISTS (SELECT 1 FROM ir_model_data WHERE module = 'sale_subscription'
               AND name = 'field_sale_subscription_report__payment_mode_id') THEN
        RAISE EXCEPTION 'XML ID original ya existe: revisar colision';
    END IF;
    UPDATE ir_model_data SET module = 'sale_subscription' WHERE id = target_id;
END;
$rollback$;
COMMIT;
```

La reversión se entrega para revisión, no se ha ejecutado. Para recuperar una
base completa, restaurar el respaldo en un destino aislado y vacío con su código
y filestore correspondientes; no sobrescribir una base activa a ciegas.

### Evidencias del ensayo local

- Primera ejecución: cambió únicamente `ir_model_data.module` de la fila 61396.
- Segunda ejecución: aviso «Corrección ya aplicada», sin cambios adicionales.
- Comparación completa del registro de campo antes/después: idéntica.
- Comparación completa del XML ID: idéntica salvo `module`.
- Recuentos de `ir_model_fields` e `ir_model_data`: sin variación.
- Recuentos de negocio conservados: 4.766 pedidos de venta, 30.357 movimientos
  contables, 91.061 líneas contables, 1.829 compras y 35.004 adjuntos.
- Huellas de todos los pares `(id, payment_mode_id)` en pedidos y movimientos:
  idénticas antes/después, incluidos valores vacíos.
- Respaldo custom revisado con `pg_restore --list`, sin restaurar ni convertir.
- No se enviaron correos, no se modificó Excel y no se crearon commits.

Archivos de evidencia locales, fuera del repositorio:
`C:\Proyectos FL\DAM\miac_odoo17_docker\migration_runs\20261012_001`:
`before.json`, `after.json`, `apply_1.log`, `apply_2.log`,
`miac_before_001.dump`, `miac_upgrade_001.sql` y `compose_before.yaml`.

SHA256 del respaldo: `98274e83871d8a71594fb406da5adb0be00d29529763fb5ee331886b2266e350`.

### Separación del código del entorno V17

El contenedor V17 apuntaba al checkout `staging_v19` para JH y fallaba con
`Invalid version '19.0.1.1.0'`. Es una incidencia independiente del rechazo de
Odoo Upgrade. Se sustituyó ese montaje local por
`./addons_v17_snapshot_20261012:/mnt/dam-addons:ro`, conservando el montaje del
respaldo para los demás addons. La carpeta aislada contiene JH y DAM Website
Page Porter extraídos de la rama local `staging`, commit
`637b73ed8a321c0567cda8d517798c13299bf4e0`; JH coincide con la versión instalada
`17.0.0.8.0`. No se cambió de rama ni se alteró código de módulos V19.

La configuración anterior quedó respaldada en `compose_before.yaml`. No volver
a montar el checkout V19 en el servidor V17.

### Pendientes y criterio de cierre

- El intento posterior #4786089 avanzó hasta V19 sin repetir este bloqueo;
  la siguiente incidencia detectada se registra en la sección 002.
- Una actualización de `sale_subscription` en V17 puede volver a registrar un
  XML ID bajo su namespace. Aplicar el ajuste después de las actualizaciones
  del origen; si aparecen aliases adicionales, revisar y adaptar la precondición.
- Los avisos de módulos OCA no cargados y campos serializados de `queue_job`
  que aparecen antes del fallo no justifican borrar esos módulos o campos.
  Registrar nuevas correcciones únicamente ante un bloqueo confirmado.
- La validación con la base migrada V19 y los addons personalizados permanece
  pendiente; esta intervención no certifica la migración completa.

## Cómo incorporar la siguiente incidencia

Añadir una sección `002`, `003`, etc., indicando: log/error exacto, versión y fase,
causa demostrada con fuentes y SELECT, alcance de registros, respaldo,
script transaccional con precondiciones, reversión, evidencia antes/después,
prueba de repetición y resultado del siguiente intento remoto. Mantener un
archivo ejecutable por incidencia y copiar su contenido íntegro a este MD.
Las correcciones de V18/V19 no se ejecutan por defecto en la base V17.

## Referencia metodológica

[Odoo: actualizar una base personalizada](https://www.odoo.com/documentation/19.0/developer/howtos/upgrade_custom_db.html).
La solución concreta de la incidencia 001 se basa en el log suministrado,
los metadatos de la copia local y las fuentes locales del modelo y su herencia.

## Anexo — SQL 001 aplicado

```sql
-- MIAC 17 -> 19. Ejecutar en la copia V17 antes de exportarla a Odoo Upgrade.
-- Solo cambia la propiedad de un XML ID; no elimina campos ni columnas.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $miac$
DECLARE
    field_id integer;
    xmlid_id integer;
    owner text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND state = 'installed'
                   AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Este script exige una base de origen Odoo 17';
    END IF;
    IF (SELECT count(*) FROM ir_module_module
        WHERE name IN ('account_payment_sale', 'sale_subscription')
        AND state = 'installed') <> 2 THEN
        RAISE EXCEPTION 'Deben estar instalados account_payment_sale y sale_subscription';
    END IF;
    SELECT id INTO field_id FROM ir_model_fields
    WHERE model = 'sale.subscription.report' AND name = 'payment_mode_id'
      AND ttype = 'many2one' AND relation = 'account.payment.mode' AND state = 'base'
    FOR UPDATE;
    IF field_id IS NULL THEN
        RAISE EXCEPTION 'No se encuentra el campo esperado; revisar antes de continuar';
    END IF;
    IF (SELECT count(*) FROM ir_model_data
        WHERE model = 'ir.model.fields' AND res_id = field_id) <> 1 THEN
        RAISE EXCEPTION 'El campo debe tener exactamente un XML ID; revisar aliases';
    END IF;
    SELECT id, module INTO xmlid_id, owner FROM ir_model_data
    WHERE model = 'ir.model.fields' AND res_id = field_id
      AND name = 'field_sale_subscription_report__payment_mode_id'
      AND module IN ('sale_subscription', 'account_payment_sale') FOR UPDATE;
    IF xmlid_id IS NULL THEN
        RAISE EXCEPTION 'XML ID inesperado; no se modifica nada';
    END IF;
    IF owner = 'sale_subscription' THEN
        IF EXISTS (SELECT 1 FROM ir_model_data
                   WHERE module = 'account_payment_sale'
                   AND name = 'field_sale_subscription_report__payment_mode_id') THEN
            RAISE EXCEPTION 'El XML ID destino ya existe: revisar colision';
        END IF;
        UPDATE ir_model_data SET module = 'account_payment_sale'
        WHERE id = xmlid_id;
        RAISE NOTICE 'Corregido XML ID %, campo %; no se modifica ir_model_fields', xmlid_id, field_id;
    ELSE
        RAISE NOTICE 'Correccion ya aplicada; no hay cambios';
    END IF;
END;
$miac$;
SELECT f.id AS field_id, f.model, f.name, d.id AS xmlid_id,
       d.module, d.name AS xmlid, d.noupdate
FROM ir_model_fields f JOIN ir_model_data d
ON d.model = 'ir.model.fields' AND d.res_id = f.id
WHERE f.model = 'sale.subscription.report' AND f.name = 'payment_mode_id';
COMMIT;
```

## Comprobacion final del entorno y del archivo de envio

- Login V17 en `http://localhost:8077/web/login?db=miac`: HTTP 200.
- El XML ID sigue corregido despues del arranque del registro V17.
- SQL exportado: 375.766.048 bytes; comprobado que contiene la propiedad
  `account_payment_sale` para el XML ID de la incidencia 001.
- SHA256 del SQL corregido: `9d2ee6cec2dea7c2ff71001c240abc18dd2b7aec188332f790e46b7deb1540c1`.
- Codigo de modulos y manifests del repositorio: sin modificaciones.

## 002 — Restricción de numeración OCA durante la contabilización del upgrade

### Error y diagnóstico

Solicitud #4786089, después de 8 min 22 s. Este intento avanzó al paso V19,
sin repetir el bloqueo 001. El script oficial de `account`,
`saas~18.5.1.4/post-remove-tax-tag-invert.py`, contabiliza movimientos durante
la conversión de etiquetas fiscales. El registro se detiene con:

```text
psycopg2.errors.CheckViolation:
new row for relation "account_move" violates check constraint
"account_move_name_state_diagonal"
```

La fila del error es el asiento 107290, generado durante el proceso remoto;
esa ID no existe en el origen local. No se debe buscarlo para renumerarlo en V17.
La comprobación del origen devuelve cero asientos contabilizados sin número.

Fuentes locales revisadas:
`respaldo/addons/account_move_name_sequence/models/account_move.py` y los
métodos `_compute_name`, `_set_next_sequence`, `_locked_increment` y `_post`
del Odoo 19 local, que figuran en la traza. El addon OCA V17 reemplaza el
cálculo del nombre y declara un CHECK inmediato que exige un nombre distinto
de vacío o `/` cuando `state = 'posted'`. Durante el upgrade el addon no se
carga, pero su restricción SQL continúa activa; la traza demuestra que bloquea
la escritura transitoria de `state = 'posted'` antes de completar el cálculo
nativo del número. No se ha reproducido aquí el script privado del proveedor.

### Alcance y prevalidación

Retirar únicamente `account_move_name_state_diagonal` en la copia detenida
que se enviará al upgrade. No retirar otras restricciones, índices o claves
foráneas; no utilizar `CASCADE`. Conservar `ir_model_constraint`, la instalación
del módulo y todos los documentos. No desinstalar el addon ni cambiar nombres,
fechas, estados, secuencias, diarios, impuestos o importes de asientos.

```sql
SELECT c.conname, pg_get_constraintdef(c.oid), c.convalidated
FROM pg_constraint c
WHERE c.conrelid = 'account_move'::regclass
  AND c.conname = 'account_move_name_state_diagonal';

SELECT c.id, c.name, m.name AS module
FROM ir_model_constraint c JOIN ir_module_module m ON m.id = c.module
WHERE c.name = 'account_move_name_state_diagonal';

SELECT count(*) AS posted_without_name FROM account_move
WHERE state = 'posted' AND coalesce(name, '') IN ('', '/');
```

En el ensayo: propietario `account_move_name_sequence`, versión instalada
`17.0.1.0.5`; metadato ID 4213. El script no utiliza esta ID fija. Exige V17,
propiedad OCA, ausencia de asientos sin número y definición SQL exacta revisada.
Si difiere cualquiera de esas condiciones, falla y revierte toda la operación.

### Ejecución y exportación

Detener el web, respaldar la base y conservar el filestore como en 001.
Aplicar 001 y después 002 sobre la copia final destinada al envío. Finalizar
previamente cualquier actualización de addons del origen, porque actualizar
`account_move_name_sequence` puede volver a crear el CHECK.

```powershell
docker cp 'C:\Proyectos FL\FL repos\dam\scripts\migration\002_account_move_name_state_constraint.sql' miac17-db:/tmp/002_account_move_name_state_constraint.sql
docker exec miac17-db psql -X -U odoo -d miac -v ON_ERROR_STOP=1 -f /tmp/002_account_move_name_state_constraint.sql

# Exportar antes de reanudar el servicio de la copia.
docker exec miac17-db pg_dump -U odoo -d miac --no-owner --no-acl -f /tmp/miac_upgrade_002.sql
docker cp miac17-db:/tmp/miac_upgrade_002.sql 'C:\RUTA_EXPORTACION\miac_upgrade_002.sql'
```

La retirada del CHECK es una preparación temporal de la copia de migración:
no es un cambio permanente recomendado para la explotación de la base V17.
En producción se realizará durante la ventana de migración, sobre el origen
congelado/copia de envío. Si se cancela la migración y se continúa operando en
V17, restaurar primero la protección y verificar la base.

### Script completo aplicado

```sql
-- Preparacion exclusiva de la copia MIAC V17 destinada a Odoo Upgrade.
-- No cambia documentos; retira solo el CHECK OCA que bloquea el upgrade nativo.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $miac$
DECLARE
    definition text;
    constraint_type "char";
    expected_definition text := $definition$CHECK ((((COALESCE(name, ''::character varying))::text <> ALL (ARRAY[('/'::character varying)::text, (''::character varying)::text])) OR ((state)::text <> 'posted'::text)))$definition$;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND state = 'installed'
                   AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Este script exige una copia de origen Odoo 17';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'account_move_name_sequence' AND state = 'installed') THEN
        RAISE EXCEPTION 'No esta instalado el modulo de secuencia esperado';
    END IF;
    IF (SELECT count(*) FROM ir_model_constraint c
        JOIN ir_module_module m ON m.id = c.module
        WHERE c.name = 'account_move_name_state_diagonal'
          AND m.name = 'account_move_name_sequence') <> 1 THEN
        RAISE EXCEPTION 'Propiedad de la restriccion inesperada; revisar manualmente';
    END IF;
    LOCK TABLE account_move IN ACCESS EXCLUSIVE MODE;
    IF EXISTS (SELECT 1 FROM account_move
               WHERE state = 'posted' AND coalesce(name, '') IN ('', '/')) THEN
        RAISE EXCEPTION 'Existen asientos contabilizados sin numero: revisar antes de retirar la restriccion';
    END IF;
    SELECT pg_get_constraintdef(oid), contype INTO definition, constraint_type
    FROM pg_constraint WHERE conrelid = 'account_move'::regclass
      AND conname = 'account_move_name_state_diagonal';
    IF definition IS NULL THEN
        RAISE NOTICE 'Restriccion ya retirada; no hay cambios';
    ELSE
        IF constraint_type <> 'c' OR definition <> expected_definition THEN
            RAISE EXCEPTION 'La definicion no coincide con el CHECK OCA revisado: %', definition;
        END IF;
        ALTER TABLE account_move DROP CONSTRAINT account_move_name_state_diagonal;
        RAISE NOTICE 'Retirado exclusivamente el CHECK OCA; documentos y metadatos del modulo conservados';
    END IF;
END;
$miac$;
SELECT count(*) AS constraint_remaining FROM pg_constraint
WHERE conrelid = 'account_move'::regclass AND conname = 'account_move_name_state_diagonal';
SELECT count(*) AS posted_without_name FROM account_move
WHERE state = 'posted' AND coalesce(name, '') IN ('', '/');
COMMIT;
```

### Reversión y prueba de reversibilidad

Para restaurar la protección en V17, detener el web, comprobar la ausencia del
CHECK y de asientos contabilizados sin número, y ejecutar:

```sql
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $guard$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND state = 'installed'
                     AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Reversion limitada al origen V17';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_constraint c
                   JOIN ir_module_module m ON m.id = c.module
                   WHERE c.name = 'account_move_name_state_diagonal'
                     AND m.name = 'account_move_name_sequence') THEN
        RAISE EXCEPTION 'Propiedad de la restriccion inesperada';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'account_move'::regclass
               AND conname = 'account_move_name_state_diagonal') THEN
        RAISE EXCEPTION 'La restriccion ya existe: verificar su definicion';
    END IF;
END;
$guard$;
ALTER TABLE account_move ADD CONSTRAINT account_move_name_state_diagonal
CHECK(COALESCE(name, '') NOT IN ('/', '') OR state!='posted');
COMMIT;
```

Se probó el `ADD CONSTRAINT` dentro de una transacción y PostgreSQL lo validó
contra los datos existentes. Se ejecutó `ROLLBACK` al terminar esa prueba, por
lo que la protección permanece retirada en la copia de envío. No aplicar esta
reversión automáticamente sobre V19: revisar primero el módulo de secuencias
que vaya a utilizarse y su compatibilidad con el flujo nativo.

### Evidencias y archivos de este ensayo

- Primera ejecución: un único CHECK retirado; segunda: sin cambios.
- Huellas de todas las filas y recuentos idénticos antes/después en
  `account_move`, `account_move_line`, `sale_order`, `purchase_order`,
  `ir_attachment`, `ir_model_constraint` e `ir_model_data`.
- Todas las demás restricciones de `account_move` conservan sus definiciones.
- Asientos contabilizados sin número: cero antes/después.
- La corrección 001 permanece en el SQL exportado.
- La exportación no contiene `ADD CONSTRAINT account_move_name_state_diagonal`.
- Sin modificaciones de código de addons, manifests, Excel ni commits.

Evidencias: `C:\Proyectos FL\DAM\miac_odoo17_docker\migration_runs\20261012_002`:
`before.json`, `after.json`, `apply_1.log`, `apply_2.log`,
`miac_before_002.dump` y `miac_upgrade_002.sql`.

SHA256 del respaldo custom:
`4b8d2584d973d9a6dbb1060eeab01a2eccd595aaca1973653dbf28a4299bcc95`.
SHA256 del SQL corregido:
`b8ddf462d3d02cab5958b9eba2b7a0f9c45166c25a310f0dee90d7ef58a0c2a5`.

### Cierre pendiente

El éxito del script y la comparación de datos son comprobaciones locales.
El siguiente intento en Odoo Upgrade debe confirmar que se supera este bloqueo.
Después de recibir la base V19, verificar especialmente los movimientos de la
conversión fiscal, sus nombres, fechas, balance, impuestos y ausencia de números
vacíos/duplicados por diario/compañía según las reglas de numeración aplicables.
La decisión y validación del módulo de secuencias en V19 quedan separadas de esta
corrección; la ausencia del CHECK no garantiza por sí sola la integridad funcional.

Comprobacion final 002: login V17 HTTP 200 tras reiniciar el servicio;
el CHECK sigue ausente despues de cargar el registro.
