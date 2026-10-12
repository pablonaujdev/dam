# MIAC — Incidencias posteriores a la migración a Odoo 19

## Alcance

Entorno de ensayo aislado, creado el 12/10/2026 después del éxito del servicio
Odoo Upgrade, solicitud **4786111**. Este documento registra restauración,
arranque y validación funcional posterior. Las correcciones previas al envío
continúan en `MIAC_CORRECCIONES_BD_UPGRADE_17_19.md` y no se reaplican sobre V19.

## Entorno

- ZIP de origen: `C:\Users\pablo\Downloads\4786111-upgraded.zip`.
- Compose y configuración: `C:\Proyectos FL\DAM\miac_v19_migrada`.
- Proyecto Docker: `miac_v19_migrada`.
- Odoo: `miac_v19_migrada`; PostgreSQL: `miac_v19_migrada_db`.
- Base: `miac_v19_migrada`; puerto web local: **8080**; PostgreSQL local: **5440**.
- Repositorio montado de solo lectura: `C:\Proyectos FL\FL repos\dam`.
- Fuentes Enterprise 19 locales: volumen `miac_v19_odoo19-source`, montado
  en `/opt/odoo19-local`, igual que en el entorno limpio anterior.
- Imagen final: `miac_v19_migrada-odoo:19.0`, núcleo `19.0-20260926`, con
  dependencias Python del ensayo. La imagen anterior `miac_v19-odoo:19.0`
  se usó únicamente en los primeros intentos y permanece sin sustituir.
- Datos y filestore separados de `miac17` y de la instalación limpia `miac_v19`.
- Crons desactivados mediante `max_cron_threads = 0`. SMTP de configuración
  dirigido a localhost puerto 1. Los servidores SMTP restaurados deben quedar
  desactivados antes de iniciar la base, porque tienen prioridad sobre esa
  configuración; no se permite enviar correos reales durante este ensayo.

## Restauración y adjuntos

El ZIP contiene `dump.sql` (390.234.556 bytes) y 420 entradas de filestore.
El filestore V17 local contiene 20.832 archivos (2.573.217.977 bytes).
Se copia íntegramente a la carpeta del nuevo nombre de base y después se
superponen los archivos entregados por Upgrade. Esto conserva los archivos
anteriores y da prioridad a los archivos nuevos del ZIP; no modifica el origen.
El resultado debe contrastarse con `ir_attachment.store_fname` restaurado.

El dump se restaura con `psql -X -v ON_ERROR_STOP=1` en un PostgreSQL nuevo,
sin sobrescribir bases anteriores. El archivo y log de restauración quedan
en la carpeta `restore`/`logs` de este entorno.

## Registro de incidencias

Se incorporará una sección por bloqueo confirmado: error exacto, causa,
consulta de diagnóstico, alcance, respaldo, corrección reproducible,
reversión, verificaciones y pendientes. La creación del entorno no supone
aceptación funcional ni conservación certificada de todos los datos.

## Hallazgo previo — Addons que todavía declaran V17

La inspección del repositorio identificó:

| Módulo | Versión en el manifiesto |
|---|---|
| `base_edi` | `17.0.1.1.1` |
| `dam_website_page_porter` | `17.0.1.0.2` |
| `edi_account_oca` | `17.0.1.0.0` |
| `edi_exchange_template_oca` | `17.0.1.0.0` |
| `edi_oca` | `17.0.1.3.0` |

No se alteran versiones para aparentar compatibilidad ni se desinstalan módulos
del dump por este hallazgo. La carga real y el estado de cada módulo deben
comprobarse al arrancar el registro y documentarse abajo.

## POST-001 — Restauración: unaccent no es IMMUTABLE

**Error:** `functions in index expression must be marked IMMUTABLE`, línea
1243520 del dump, al crear `account_account__name_index`. La extensión recién
creada declara `public.unaccent(text)` STABLE; Odoo la requiere IMMUTABLE para
sus índices GIN. Fuente: `odoo/service/db.py`, `_initialize_db`, en el Odoo 19
local, que ejecuta `ALTER FUNCTION unaccent(text) IMMUTABLE`.

Se respaldó la restauración parcial en `restore/before_post_001.dump`.
Se alteró exclusivamente la firma `unaccent(text)` y se reanudó el SQL desde
el primer índice fallido. `restore/resume_001.sql` conserva el encabezado de
sesión del dump y el resto desde la línea fallida. La reanudación terminó con
código 0; no se volvieron a insertar datos. Logs: `logs/restore.log` y
`logs/resume_001.log`.

**Para repetir desde cero:** insertar el ajuste después de crear la extensión
`unaccent` y antes de los índices, o restaurar datos e índices por separado.
La línea 1243520 solo corresponde a este archivo, no a futuros dumps. No
reaplicar todo el dump sobre una restauración parcial sin revisar duplicados.

Script ejecutable: `scripts/migration/post_001_unaccent_immutable.sql`.

```sql
-- Solo en el PostgreSQL del nuevo ensayo V19, antes de restaurar los indices.
-- Mismo ajuste aplicado por odoo/service/db.py al preparar una base Odoo.
\set ON_ERROR_STOP on
BEGIN;
DO $guard$
BEGIN
    IF to_regprocedure('public.unaccent(text)') IS NULL THEN
        RAISE EXCEPTION 'No existe la extension unaccent esperada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc
                   WHERE oid = 'public.unaccent(text)'::regprocedure
                     AND provolatile IN ('s', 'i')) THEN
        RAISE EXCEPTION 'Funcion unaccent inesperada: revisar antes de continuar';
    END IF;
END;
$guard$;
ALTER FUNCTION public.unaccent(text) IMMUTABLE;
SELECT proname, provolatile FROM pg_proc
WHERE oid = 'public.unaccent(text)'::regprocedure;
COMMIT;
```

**Reversión:** restaurar el respaldo en una base aislada. No devolver la función
a STABLE sobre una base operativa que ya usa los índices funcionales de Odoo.
No se modificaron registros comerciales con este ajuste.

## Preparación de seguridad del ensayo — Neutralización nativa

Antes de iniciar el web se ejecutó la herramienta oficial `odoo neutralize`,
que trabaja sobre la base restaurada. Desactiva servidores de correo, marca
la base neutralizada y aplica los scripts de neutralización de los módulos
instalados disponibles (incluidos servicios de pago/integraciones cuando el
addon aporta uno). Fue exitosa. Repetición:

```powershell
docker compose -f "C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml" run --rm --no-deps --entrypoint python3 web /usr/bin/odoo neutralize -c /etc/odoo/miac.conf -d miac_v19_migrada
```

La herramienta deja un SMTP ficticio activo con host `invalid`. Se comprobó
que hay **cero SMTP reales activos**. Conserva activo el cron nativo de limpieza;
ningún cron se ejecuta porque el proceso arranca con `max_cron_threads = 0`.
No habilitar correo, pagos ni tareas antes de aceptar funcionalmente el ensayo.
No usar este comando sobre producción.

## POST-002 — Login: nueva columna de account_payment_mode ausente

**Error:** `column res_company.keep_partner_bank_without_payment_mode does not exist`.
El código V19 del addon se carga, pero el dump todavía conserva esquema V17.
No se añade una columna manualmente: se actualiza el módulo mediante Odoo.
Respaldo previo: `restore/before_post_002.dump`.

```powershell
docker compose -f "C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml" run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u account_payment_mode --stop-after-init --no-http --max-cron-threads=0
```

La primera ejecución con las fuentes locales se detuvo por POST-003. Con el
núcleo de la imagen, `account_payment_mode` alcanzó versión `19.0.1.1.0`; la
actualización global se detuvo más adelante por POST-004. Estos comandos pueden
confirmar módulos intermedios antes de un fallo posterior: no asumir reversión
global. Los logs completos se conservan en `logs/update_account_payment_mode*.log`.
Para revertir el conjunto, restaurar el respaldo aislado.

## POST-003 — Fuentes nativas anteriores a las vistas del dump

**Primer error:** campo nativo `account.move.is_exact_move_duplicate` ausente.
El metadato recibido pertenece a `account`; las fuentes de enero de 2026 no
lo declaran. La imagen Docker previa sí lo declara. Se cambió el núcleo a
`/usr/bin/odoo`, con addons comunitarios del paquete primero, addons Enterprise
locales después y el repositorio al final. No se eliminó el campo de las vistas.

**Segundo error:** `iap_action_view_my_services` no es una acción válida en
`res.config.settings`. La imagen anterior contiene Odoo `19.0-20260803` y no
implementa el método usado en las vistas recibidas. Se construye una imagen
exclusiva del ensayo con `build --pull`; no se sustituye la imagen del entorno
limpio. Los complementos Enterprise locales siguen requiriendo comprobación
frente a este núcleo; no se certifica su compatibilidad solo por arrancar.

```powershell
docker compose -f "C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml" build --pull web
```

Configuración anterior respaldada en `restore/before_native_switch_*`.

## POST-004 — Tabla nueva de anotaciones MIS ausente

**Error:** `relation mis_report_instance_annotation does not exist`, al crear
el índice en `mis_builder/models/mis_report_instance_annotation.py:init()`.
MIS Builder seguía instalado con versión V17; se actualiza su esquema por ORM.

```powershell
docker compose -f "C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml" run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u mis_builder --stop-after-init --no-http --max-cron-threads=0
```

El módulo alcanzó `19.0.1.2.1` y creó su tabla. La ejecución después se detuvo
por POST-005. Log: `logs/update_mis_builder.log`. No crear tablas a mano para
simular un esquema actualizado.

## POST-005 — Nueva columna AEAT y actualización de addons disponibles

**Error:** `column res_company.representative_vat does not exist`, declarada
por `l10n_es_aeat` V19. Al validar vistas, Odoo lee la compañía completa y falla
por campos de otros addons aún no actualizados; `InFailedSqlTransaction` es una
consecuencia, no la causa primaria.

Se preparó una actualización de los 50 módulos ya instalados que tienen fuente
V19 instalable en el repositorio. Lista exacta: `logs/update_targets.json`.
No se ejecuta un renombrado manual de namespaces por este paso. Odoo puede
instalar las dependencias nuevas declaradas por los módulos actualizados; en
este ensayo instaló las comisiones `_oca`. Conviven con metadatos de módulos
antiguos, por lo que sigue siendo necesaria la revisión de correspondencias.
El primer intento se detuvo en POST-003/IAP; no se considera actualización total
exitosa. Log: `logs/update_available_addons.log`.

## Verificación del filestore

`logs/filestore_audit.json` compara todas las referencias de archivos de los
adjuntos restaurados contra el filestore compuesto del nuevo entorno:
**20.905 archivos distintos referenciados, cero ausentes**. Esto comprueba
presencia; no reemplaza la revisión de apertura y contenido de adjuntos reales.

Recuentos observados después de restaurar el dump: 4.766 pedidos, 30.639
movimientos contables, 91.701 líneas contables y 35.235 adjuntos. Los nuevos
movimientos creados por el servicio de upgrade explican que el total no sea el
mismo que el origen V17; comparar sus efectos fiscales/contables en aceptación.

## Pendiente — Correspondencias OCA y módulos sin fuente disponible

El dump mantiene módulos con nombres V17, por ejemplo `commission`,
`account_commission`, `hr_commission`, `account_payment_partner`. También existen
avisos de addons sin fuente, incluyendo banca SEPA, secuencias y otras
localizaciones. El inventario de módulos preparados no equivale a cargar todos
los módulos existentes en la base real.

Revisar la correspondencia en `MIAC_MODULE_MAPPING_19.json` y
`MIGRACION_CORRESPONDENCIAS_19.md` contra los metadatos de esta copia. No hacer
renombres masivos ni desinstalaciones para ocultar los avisos. La fusión de
`account_payment_partner` y los renombres de comisiones requieren un script
específico, revisión de colisiones y comprobación de agentes/liquidaciones.
Esas transformaciones no se ejecutan dentro de la preparación inicial descrita.

## POST-006 — JH: XPath de factura dependiente del orden de vistas

**Error:** `//field[@name='invoice_line_id']` no localizado en la vista padre,
en `jh_sales_subscription/views/actions_jh_commission_settlement_line.xml`.

JH heredaba `commission_oca.view_settlement_form`, pero la columna se añade
en su extensión `account_commission_oca.view_settlement_form`. En la base
restaurada, la vista JH conservaba un ID anterior al de la extensión recién
instalada; con prioridades iguales, su XPath podía ejecutarse primero. No es
un problema de importes ni una razón para eliminar la columna.

Se cambió únicamente el padre a la vista que declara esa columna, conservando
el XML ID propio y los XPath. Se aplicó `development-conventions`; manifest
versionado una vez de `19.0.1.1.0` a **`19.0.1.1.1`**, con explicación funcional.
No se añadió dependencia: `account_commission_oca` ya estaba declarada.

**Repetición:** desplegar la versión corregida del código y actualizar JH con
sus dependencias preparadas. No modificar directamente la arquitectura en SQL.
**Reversión:** restaurar el respaldo del ensayo y la revisión de código anterior;
volver al padre genérico reintroduce el problema de orden.

Log: `logs/update_available_addons_current_image.log` muestra el fallo;
`logs/update_available_addons_jh_view_fix.log` muestra el intento exitoso.
La composición de la vista final de liquidaciones se verificó por ORM.

## Resultado final de la preparación

- Docker web y PostgreSQL iniciados y saludables.
- Login de la base migrada: **HTTP 200**.
- `/web/health?db_server_status=true`: `status=pass`, servidor DB disponible.
- URL: **http://localhost:8080/odoo**; base `miac_v19_migrada`.
- Imagen final: Odoo **19.0-20260926**, con la acción IAP requerida disponible.
- Imagen base fijada en Dockerfile mediante digest
  `sha256:dd9013e669caaa23d26765dc55814655eaeecca7cfc2c265dbabae913bce22fd`.
  La etiqueta del nuevo proyecto y los datos están separados de los anteriores.
- Actualización final de addons: **código de salida 0**; registro cargado.
- Los **50 módulos seleccionados** están instalados con versiones coincidentes
  con sus manifests V19. Evidencia: `logs/final_module_audit.json`.
- Vistas de contactos, ventas, compras, facturas, albaranes y liquidaciones:
  **6/6 composiciones correctas**, comprobadas por ORM sin crear documentos;
  la sesión terminó con rollback. Evidencia: `logs/view_audit.log`.
- SMTP reales activos: cero. Crons del proceso: desactivados. No se enviaron
  correos reales ni se modificaron los contenedores/base/filestore anteriores.
- Sintaxis XML y manifest de la corrección JH revisadas. No se ejecutó la batería
  completa de regresiones ni pruebas transaccionales sobre datos reales.
- No se modificó Excel y no se crearon commits.

### Procedimiento reproducible para actualizar los addons seleccionados

Con el web detenido y respaldo previo, reconstruir la imagen fijada y ejecutar
la actualización con **la lista revisada de este ensayo**, no con un `-u all`
indiscriminado:

```powershell
$miacCompose = 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml'
$miacTargets = (Get-Content 'C:\Proyectos FL\DAM\miac_v19_migrada\logs\update_targets.json' -Raw | ConvertFrom-Json) -join ','
docker compose -f $miacCompose stop web
docker compose -f $miacCompose build web
docker compose -f $miacCompose run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u $miacTargets --stop-after-init --no-http --max-cron-threads=0
docker compose -f $miacCompose up -d web
```

No avanzar al arranque si la actualización falla: guardar el log y diagnosticar
la primera causa. Validar la lista y las correspondencias en la copia final de
producción, bajo autorización propia; la lista de este ensayo no demuestra que
los restantes módulos estén resueltos.

### Pendientes que permanecen visibles

Aunque el registro arranca, continúan metadatos de `commission`,
`account_commission`, `hr_commission`, `account_payment_partner`,
`sale_product_template_tags` y `account_move_name_sequence` con versión V17.
También quedan avisos de addons no cargados por falta de fuentes/dependencias.
No se han desinstalado ni borrado sus datos ni se ha aplicado la fusión de
namespaces. Revisar agentes, comisiones, liquidaciones, bancos/SEPA y secuencias
antes de dar por válida la conservación funcional e histórica.

Las vistas compiladas y el login no certifican procesos de ventas, facturación,
renovaciones, impuestos, informes/PDF ni permisos de cada usuario. La base está
preparada para continuar ese ensayo y registrar las siguientes incidencias aquí.

Respaldo final de la base preparada: `restore/post_setup_ready.dump`.
Auditoria final de filestore, despues de actualizar: 20906 archivos referenciados, 0 ausentes (`logs/filestore_audit_final.json`).

## POST-007 — Formulario de ventas: sale.order.type_id no definido

**Error del navegador:** `OwlError: "sale.order"."type_id" field is undefined`,
12/10/2026 a las 15:11:24 UTC. La lista abre, pero el formulario recibe una
arquitectura que usa el campo sin que el registro tenga su definición Python.

### Causa y diagnóstico

El módulo `sale_order_type` constaba instalado en la copia con versión
`17.0.1.0.2`, pero su carpeta no existía en el repositorio V19 montado. Persistían
la vista `sale_order_type.sot_view_order_form` (ID 3708) y una personalización
Studio que utiliza el campo. No es suficiente compilar la arquitectura de una
vista: hay que comprobar que los campos aparecen también en los metadatos del
modelo enviados al cliente mediante `get_views()`.

```sql
SELECT name, state, latest_version FROM ir_module_module
WHERE name = 'sale_order_type';

SELECT v.id, v.name, d.module, d.name AS xmlid
FROM ir_ui_view v LEFT JOIN ir_model_data d
  ON d.model = 'ir.ui.view' AND d.res_id = v.id
WHERE v.model = 'sale.order' AND v.active
  AND v.arch_db::text LIKE '%type_id%';
```

### Corrección oficial y fuentes

Se comprobó primero la disponibilidad OCA V19 y se incorporó íntegramente
**`sale_order_type` versión `19.0.1.6.0`**, 113 archivos, desde
[OCA/sale-workflow](https://github.com/OCA/sale-workflow/tree/4bf48d6ca94cf9bcc2f37cd8c6b244d27b6c1cb3/sale_order_type).
Commit fijado: `4bf48d6ca94cf9bcc2f37cd8c6b244d27b6c1cb3`.

No se ocultó el campo, no se desinstaló el módulo ni se borraron tipos o vistas
Studio. Se conserva el código oficial, autoría, licencia AGPL-3, XML IDs y
versión upstream sin modificaciones. Dependencias `sale_stock`, `account` y
`sale_management`: ya disponibles e instaladas. Las migraciones oficiales usan
`openupgradelib`, que ya está instalado en la imagen del ensayo.

Se revisaron antes de ejecutar sus dos scripts oficiales:
- `19.0.1.0.0/post-migration.py`: conserva la ruta antigua `route_id` al convertir
  la relación a `route_ids` de múltiples rutas.
- `19.0.1.3.0/post-migration.py`: convierte `analytic_account_id`, cuando existe
  y tiene valor, a distribución analítica del 100 %.

En esta copia ambos tipos no tienen rutas ni cuentas analíticas asignadas.
Una copia de producción con otra configuración debe validar expresamente
estas conversiones y su distribución resultante antes de aceptarla.

### Respaldo, ejecución y repetición

Respaldo previo: `restore/before_post_007.dump`. Instantáneas de asignaciones,
importes y tipos: `logs/post_007_before.json`, `logs/post_007_after.json`.
Se detuvo el web, se actualizó el módulo y se volvió a iniciar:

```powershell
$miacCompose = 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml'
docker compose -f $miacCompose stop web
# Antes de actualizar, realizar el respaldo de la base y conservar su filestore.
docker compose -f $miacCompose run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u sale_order_type --stop-after-init --no-http --max-cron-threads=0
docker compose -f $miacCompose up -d web
```

La carpeta oficial debe estar desplegada antes de ejecutar el comando. Para
reproducirlo en otro servidor, usar la misma revisión verificada y adaptar
configuración/nombre de base. La actualización se aplicó exclusivamente al
ensayo V19, no al origen ni a la instalación limpia anterior.

**Reversión:** restaurar el respaldo previo en un destino aislado, con las fuentes
correspondientes y filestore del mismo ensayo. Retirar la carpeta del módulo
sin restaurar la base reintroduciría el error de definición de campos.

### Validaciones y límites

- Actualización Odoo: código de salida **0**; módulo `19.0.1.6.0` instalado.
- Tres formularios primarios activos de `sale.order` (IDs 1696, 7135 y 2685):
  `get_views()` correcto; `type_id` presente en la arquitectura y en los
  metadatos del modelo en los **tres**. No se cambió la vista Studio.
- Registro Python: `sale.order.type_id` definido.
- Pedidos: 4.766; huella de todas sus asignaciones `(id, type_id)`, números e
  importe total acumulado idénticos antes/después.
- Facturas/asientos: recuento, huella `(id, sale_type_id)` e importe acumulado
  idénticos antes/después.
- Tipos: los dos IDs originales conservados. Registro de diferencias de columnas
  comunes: `logs/post_007_type_changes.json` (0 diferencias).
- Rutas/distribución analítica revisadas por ORM: sin asignaciones, conforme
  a la configuración previa de esta copia.
- Auditoría de metadatos: lectura por ORM, terminada con rollback; no se crearon
  pedidos o facturas de prueba. Log: `logs/post_007_view_audit.log`.
- Web/DB disponibles: health `pass`. Correo/crons mantienen su neutralización.
- No se modificó el Excel ni se creó un commit. No se alteraron manifests de
  módulos existentes; el módulo incorporado conserva su versión oficial.

La comprobación cubre el fallo de definición y la conservación indicada, no
la creación/confirmación de nuevos pedidos ni todas las reglas de tipos. El
usuario debe recargar la página y repetir la apertura del formulario con su
sesión y permisos. Continuar registrando nuevas incidencias si aparecen otros
campos de módulos que todavía no estén disponibles.
