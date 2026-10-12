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

## POST-008 — Contactos: zip_id sin definición

Error del navegador el 12/10/2026 a las 16:28:14 UTC:
`"res.partner"."zip_id" field is undefined`.
La base conserva instalado `base_location` V17 y sus vistas, pero faltaba el
código en el repositorio. Se comprobó primero disponibilidad oficial OCA V19.

Se incorporan sin cambios de código, autoría, licencia o versiones oficiales:
- `base_location`: **19.0.1.0.1**, 95 archivos.
- `base_location_geonames_import`: **19.0.1.0.0**, 91 archivos; también constaba
  instalado en V17 y se conserva su funcionalidad. No se ejecuta su importador.

Fuente: [OCA/partner-contact](https://github.com/OCA/partner-contact/tree/b22f62266ad1bf80192bd046293a3f3c27a73625).
Revisión fija: `b22f62266ad1bf80192bd046293a3f3c27a73625`.
Dependencias nativas `base_address_extended` y `contacts`, disponibles.
No contienen scripts propios de migración en esta revisión.

Respaldo: `restore/before_post_008.dump`. Web detenido durante actualización:

```powershell
$miacCompose = 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml'
docker compose -f $miacCompose stop web
# Realizar respaldo de la base y conservar el filestore antes de continuar.
docker compose -f $miacCompose run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u base_location,base_location_geonames_import --stop-after-init --no-http --max-cron-threads=0
docker compose -f $miacCompose up -d web
```

Resultado: código 0. Huellas de direcciones de **13.327 contactos**, incluyendo
archivados, idénticas antes/después (`zip_id`, `city_id`, código postal, ciudad,
país, provincia, calle y segunda línea). Tres contactos tienen ZIP vinculado.
El catálogo existente contiene una ciudad y un código postal; sus filas e IDs
se conservaron íntegramente, sin añadir datos geográficos. Evidencias:
`logs/post_008_before.json`, `post_008_after.json`, `update_base_location.log`.

La primera auditoría completa mostró otros cuatro campos no cargados; se
resuelven en POST-009/010, sin considerar suficiente la mera compilación XML.
Para revertir, restaurar el respaldo y sus fuentes en una base aislada;
retirar código dejando sus vistas en la base vuelve a provocar el error.

## POST-009 — Otros campos ausentes en Contactos y vista antigua duplicada

La arquitectura del formulario contenía `is_customer`, `is_supplier`,
`not_in_mod347` y `agent_ids` sin metadatos Python. Diagnóstico confirmado:
- `partner_manual_rank` instalado V17, sin código disponible.
- `l10n_es_aeat_mod347` pendiente de actualizar V17, sin código disponible.
- `commission.view_partner_form_agent` seguía activa aunque ya existe su
  equivalente V19 `commission_oca.view_partner_form_agent`.

Se añaden módulos oficiales, sin modificaciones:
- `partner_manual_rank`: **19.0.1.0.0**, revisión `b22f62266ad1bf80192bd046293a3f3c27a73625` de [OCA/partner-contact](https://github.com/OCA/partner-contact/tree/b22f62266ad1bf80192bd046293a3f3c27a73625/partner_manual_rank).
- `l10n_es_aeat_mod347`: **19.0.1.0.3**, revisión `f04d5c17e2e4929ba466bfd73e2628991bef4d4f` de [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod347).

Sus dependencias ya están disponibles en el ensayo. No se generan informes
347, no se importan datos y no se recalculan declaraciones por esta intervención.

Respaldo antes de estos cambios: `restore/before_post_009.dump`.
Se retira únicamente la vista antigua de agentes (ID 3605 en este ensayo),
conservando su registro/XML ID, y se utiliza su equivalente vigente activa
(ID 7421). No se desinstalan módulos ni se modifica la relación de agentes.
Ambas versiones utilizan `partner_agent_rel(partner_id, agent_id)`.
No se cambian membresías de grupos; su correspondencia histórica OCA sigue
pendiente de revisión específica de permisos y namespaces.

Script idempotente, condicionado a que exista la vista V19 equivalente y
el campo vigente, reproducido íntegramente:

```sql
-- Ensayo V19: retirar solo la vista V17 duplicada, conservando todos sus registros.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
DO $miac$
DECLARE old_view integer; new_view integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Este ajuste exige la copia migrada V19';
    END IF;
    SELECT v.id INTO old_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'commission' AND d.name = 'view_partner_form_agent'
      AND v.model = 'res.partner' FOR UPDATE OF v;
    SELECT v.id INTO new_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'commission_oca' AND d.name = 'view_partner_form_agent'
      AND v.model = 'res.partner' AND v.active
      AND v.arch_db::text LIKE '%commission_agent_ids%';
    IF old_view IS NULL OR new_view IS NULL OR old_view = new_view THEN
        RAISE EXCEPTION 'No existe el par de vistas V17/V19 esperado; no se modifica nada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids') THEN
        RAISE EXCEPTION 'No existe el campo actual de agentes';
    END IF;
    IF EXISTS (SELECT 1 FROM ir_ui_view WHERE id = old_view AND active) THEN
        UPDATE ir_ui_view SET active = false WHERE id = old_view;
        RAISE NOTICE 'Vista V17 % retirada; vista V19 % conservada', old_view, new_view;
    ELSE
        RAISE NOTICE 'La vista V17 ya esta inactiva; no hay cambios';
    END IF;
END;
$miac$;
COMMIT;
```

La actualización de `partner_manual_rank,l10n_es_aeat_mod347` detectó POST-010;
`InFailedSqlTransaction` no debe tratarse como causa independiente. Se conserva
el primer log en `logs/update_partner_manual_rank_mod347.log`.
La retirada de la vista se ejecutó dos veces: la segunda no introdujo cambios.

**Reversión acotada de la vista:** con web detenido, verificar el XML ID y
reactivar únicamente `commission.view_partner_form_agent` mediante un
`UPDATE ir_ui_view SET active=true` unido a ese XML ID. Reintroduce el campo
obsoleto si no se restaura también el código V17; no usarlo como reparación
sobre el entorno V19 actual. Para revertir todo, restaurar el respaldo.

## POST-010 — Exclusión 347 por compañía y referencia Studio de agentes

### Conversión de exclusión fiscal

Error de actualización: `cannot cast type boolean to jsonb` al convertir
`res_partner.not_in_mod347`. El origen tiene un booleano compartido; el código
OCA V19 lo declara `company_dependent=True` y Odoo almacena JSON por compañía.
La conversión automática por cast no expresa esa correspondencia.

Se conserva cada booleano previo bajo la clave de **cada compañía existente**,
incluidas archivadas; los valores NULL continúan NULL. En esta copia hay una
compañía. No se ponen todos los contactos a false ni se decide según la compañía
del contacto: el indicador anterior era compartido. El default SQL booleano
se retira antes de cambiar el tipo; Odoo administra el default del campo V19.

Una compañía que se cree posteriormente debe revisar sus exclusiones fiscales;
no existía en el momento de la conversión y no tiene una clave de este mapa.
La conversión se aplica al origen actualizado de este ensayo, no a V17 ni a
producción sin revisión y autorización del procedimiento correspondiente.

### Personalización Studio conservada

La lista Studio `studio_customization.odoo_studio_res_part_ba3d9bec-174c-46a2-92cf-944a3362972b`
(ID 4077) todavía insertaba `<field name="agent_ids"/>`. Se conserva la vista,
sus opciones, otras columnas y traducciones, sustituyendo únicamente ese
atributo por `commission_agent_ids`. No se desactiva la personalización Studio.

Script transaccional e idempotente (requiere el XML ID exacto de esta base;
si difiere en otra copia, revisar y adaptar, no ejecutar a ciegas):

```sql
-- Solo en la copia V19, con respaldo previo y el web detenido.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
DO $miac$
DECLARE column_type text; company_args text; studio_view integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Este ajuste exige la copia migrada V19';
    END IF;
    SELECT data_type INTO column_type FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'res_partner'
      AND column_name = 'not_in_mod347';
    IF column_type = 'boolean' THEN
        LOCK TABLE res_company IN SHARE MODE;
        LOCK TABLE res_partner IN ACCESS EXCLUSIVE MODE;
        SELECT string_agg(format('%L, not_in_mod347', id::text), ', ' ORDER BY id)
          INTO company_args FROM res_company;
        IF company_args IS NULL THEN RAISE EXCEPTION 'No existen companias'; END IF;
        ALTER TABLE res_partner ALTER COLUMN not_in_mod347 DROP DEFAULT;
        EXECUTE format('ALTER TABLE res_partner ALTER COLUMN not_in_mod347 TYPE jsonb
          USING CASE WHEN not_in_mod347 IS NULL THEN NULL
          ELSE jsonb_build_object(%s) END', company_args);
        RAISE NOTICE 'Indicador compartido conservado por cada compania actual';
    ELSIF column_type = 'jsonb' THEN
        RAISE NOTICE 'Indicador ya convertido; no se modifica';
    ELSE
        RAISE EXCEPTION 'Tipo de columna inesperado: %', column_type;
    END IF;
    SELECT v.id INTO studio_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'studio_customization'
      AND d.name = 'odoo_studio_res_part_ba3d9bec-174c-46a2-92cf-944a3362972b'
      AND v.model = 'res.partner' AND v.type = 'list' FOR UPDATE OF v;
    IF studio_view IS NULL THEN
        RAISE EXCEPTION 'No existe la vista Studio esperada; revisar antes de continuar';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids') THEN
        RAISE EXCEPTION 'No existe el campo vigente de agentes';
    END IF;
    UPDATE ir_ui_view v SET arch_db = (
        SELECT jsonb_object_agg(lang, replace(xml, 'name="agent_ids"', 'name="commission_agent_ids"'))
        FROM jsonb_each_text(v.arch_db) AS arch(lang, xml)
    ) WHERE v.id = studio_view AND EXISTS (
        SELECT 1 FROM jsonb_each_text(v.arch_db) AS arch(lang, xml)
        WHERE strpos(xml, 'name="agent_ids"') > 0
    );
END;
$miac$;
COMMIT;
```

La segunda ejecución no vuelve a convertir valores ni a modificar referencias.
Ambos scripts están también en `scripts/migration/post_009_*.sql` y
`scripts/migration/post_010_*.sql` para ejecución con `psql -X -v ON_ERROR_STOP=1`.

Después de ejecutarlos con web detenido y respaldo previo:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml' run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u partner_manual_rank,l10n_es_aeat_mod347 --stop-after-init --no-http --max-cron-threads=0
docker compose -f 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml' up -d web
```

Resultado: código 0; log `logs/update_contacts_after_flag_conversion.log`.

### Reversión y comprobaciones

La reversión segura es restaurar `before_post_009.dump` en un destino aislado
junto con el código y filestore correspondientes. No convertir JSON a booleano
sin comprobar primero que todas las compañías conservan el mismo valor: si
se han editado exclusiones independientes después, esa reversión perdería
su significado. El JSON nuevo queda respaldado en
`logs/post_010_after_flags.json`, y los valores originales en
`logs/post_010_before_flags.json`.

Validaciones del ensayo:
- Los 13.327 indicadores originales se compararon uno por uno con el valor
  resultante de cada compañía existente: coinciden, incluidos NULL.
- Huella de `customer_rank` y `supplier_rank` conservada.
- **1.184 vínculos de agentes** conservados; huella de toda la relación idéntica.
- Once vistas principales de Contactos (formulario, lista, kanban, búsqueda),
  incluidas sub-vistas relacionales: ningún campo usado en el XML falta en
  Python o en los metadatos de `get_views()` enviados al navegador.
- La lista Studio conserva su columna de agentes con el nombre vigente.
- Las sesiones ORM de auditoría terminaron con rollback; no se crearon ni
  editaron contactos funcionales ni se generaron declaraciones fiscales.
- Logs: `post_009_view_retirement_*.log`, `post_010_apply_*.log`,
  `post_010_final_view_audit.log`; snapshot de agentes en `post_009_before.json`.
- Se preservan versiones, autoría y licencias oficiales de los cuatro addons
  incorporados. No se modifican manifests de otros módulos, Excel ni commits.

Pendiente: apertura visual con la sesión real del usuario y sus permisos;
revisión funcional de GeoNames (sin descargar/importar geografía real durante
este arreglo), clasificación manual, configuración de agentes y modelo 347.
Esto no resuelve la fusión general de módulos/grupos OCA pendiente ni certifica
la migración fiscal completa.

## Auditoría transversal — Cobertura real V17/V19 después de POST-010

Se realizó un cruce completo de los 317 módulos instalados en V17 contra la
base migrada, fuentes e importación efectiva V19. Se detectaron 15 fuentes OCA
aún ausentes (todas disponibles oficialmente en 19.0) y `hr_commission_oca`
disponible sin instalar. El control anterior del presupuesto no acreditaba
la cobertura de todos los módulos de la base real.

Listado completo, versiones, fuentes oficiales, estados y excepciones:
[MIAC_AUDITORIA_COMPLETA_MODULOS_V17_V19.md](MIAC_AUDITORIA_COMPLETA_MODULOS_V17_V19.md).
No se instalaron módulos ni se aplicaron conversiones durante esta auditoría.

## Incorporación de las 15 fuentes OCA pendientes al repositorio

Fecha: 12/10/2026. Alcance solicitado: descargar y colocar los módulos en el
repositorio. Se incorporaron las quince fuentes oficiales V19 detectadas en
la auditoría, conservando íntegramente versiones, autoría, licencias y scripts
upstream. No se ejecutó instalación/actualización de base en este paso.

| Módulo incorporado | Versión oficial | Revisión exacta |
|---|---|---|
| `account_banking_mandate` | `19.0.1.0.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_mandate) |
| `account_banking_pain_base` | `19.0.1.1.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_pain_base) |
| `account_banking_sepa_credit_transfer` | `19.0.1.0.0` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_sepa_credit_transfer) |
| `account_banking_sepa_direct_debit` | `19.0.1.1.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_sepa_direct_debit) |
| `account_payment_order` | `19.0.1.0.7` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_payment_order) |
| `account_financial_report` | `19.0.0.0.26` | [OCA/account-financial-reporting](https://github.com/OCA/account-financial-reporting/tree/0078bc03f234d1caa8b9f40324678ce9dbed2a72/account_financial_report) |
| `account_move_name_sequence` | `19.0.1.0.3` | [OCA/account-financial-tools](https://github.com/OCA/account-financial-tools/tree/ddcabb93373382148826f97bf9935424d03ddea5/account_move_name_sequence) |
| `account_statement_base` | `19.0.1.0.1` | [OCA/account-reconcile](https://github.com/OCA/account-reconcile/tree/5402de2e9bb8e2cdd271d28c8d33a24eae3725c4/account_statement_base) |
| `account_statement_import_base` | `19.0.1.0.0` | [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import/tree/65316c38d7a5586456bc751d8939b84f1cf0bc2e/account_statement_import_base) |
| `account_statement_import_file` | `19.0.1.0.0` | [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import/tree/65316c38d7a5586456bc751d8939b84f1cf0bc2e/account_statement_import_file) |
| `l10n_es_account_statement_import_n43` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_account_statement_import_n43) |
| `l10n_es_aeat_mod111` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod111) |
| `l10n_es_aeat_mod123` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod123) |
| `l10n_es_aeat_mod349` | `19.0.1.1.2` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod349) |
| `l10n_es_toponyms` | `19.0.1.0.1` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_toponyms) |

Se descargaron archivos ZIP de las revisiones fijadas y se extrajeron únicamente
las quince carpetas de módulos. **781 archivos** comprobados contra los SHA de
blobs Git de las fuentes oficiales; no se sobrescribieron carpetas existentes.

Validaciones:
- 184 archivos Python compilados en memoria, sin generar `__pycache__`.
- 97 XML analizados correctamente.
- Todos los recursos `data`/`demo` de los manifests existen.
- Cierre recursivo de 45 dependencias Odoo: cero fuentes ausentes.
- Python externo requerido: `chardet`, `lxml`, `unidecode`, importaciones
  verificadas correctamente en `miac_v19_migrada`.
- Las carpetas están disponibles a través del montaje de solo lectura del repo.
- No se modificó código upstream ni se incrementaron sus versiones.
- No se reinició Odoo, no se instalaron/actualizaron módulos en BD, no se
  convirtieron datos, no se modificó Excel y no se crearon commits.

Evidencias: `logs/oca_15_download_verified.json`,
`logs/oca_15_static_validation.json`. Archivos ZIP retenidos en
`restore/oca_download_15` para reproducir las revisiones.

### Estado posterior de los pendientes

La carencia de **fuentes** de los quince módulos queda resuelta. Su actualización
sobre la base migrada, ejecución de scripts de datos y pruebas de banca,
extractos, informes, numeración y declaraciones fiscales siguen pendientes.
No confundir sus filas `installed` heredadas de V17 con una actualización V19.

`hr_commission_oca` ya tenía fuente disponible y continúa pendiente de su
instalación/correspondencia; no forma parte de los quince descargados.
Antes de actualizar la base, preparar el respaldo y el orden de dependencias,
revisar sus migraciones y conservar la neutralización del ensayo. Añadir fuentes
a un montaje no acredita actualización del esquema ni del registro de Odoo.

## Revalidación después de incorporar las fuentes OCA

12/10/2026: se volvió a consultar la base V17 en directo; sus **317 módulos
instalados** coinciden con la auditoría completa anterior. Se contrastaron sus
destinos con las carpetas actuales y los estados/versiones reales de V19:

- **Cero fuentes V19 ausentes** entre los addons de origen que se conservarán.
- Cierre recursivo de **130 módulos/dependencias**, sin fuentes ausentes.
- Los 15 módulos recién incorporados continúan con versión V17 en la base:
  requieren actualización; la copia de archivos no ejecutó sus migraciones.
- `hr_commission_oca` está disponible en el repo, versión `19.0.1.0.0`, pero
  sigue `uninstalled`: requiere instalación y correspondencia con HR antiguo.
- Permanecen revisiones de namespaces, sustituciones/exclusiones y tema web,
  detalladas en la auditoría. No se convierten en descargas nuevas por este control.
- No se carga un registro nuevo con estos addons sin actualizar primero el
  esquema: incorporar código y tener filas installed no prueba funcionamiento.
- No se instaló/actualizó ningún addon ni se modificaron datos o Excel. PostgreSQL
  V17 se volvió a detener después de la lectura, conservando su estado inicial.

Evidencia: `C:\Proyectos FL\DAM\miac_v19_migrada\logs\inventory_after_oca_download.json`.

## POST-011 — Acceso a Contabilidad: columna nueva N43 ausente

**Estado: documentado y diagnosticado; corrección de BD pendiente.**

Error facilitado por el usuario el 12/10/2026 a las 17:04:18 UTC
(12:04:18 America/Bogota), al abrir Contabilidad en `127.0.0.1:8080`,
modelo `account.journal`:

```text
psycopg2.errors.UndefinedColumn:
column account_journal.n43_partner_search does not exist
```

La llamada es `account.journal.web_search_read`. Durante la lectura de
actividades y comprobación de acceso, Odoo consulta los campos del diario y
PostgreSQL rechaza la columna inexistente. El `KeyError: 11` inicial corresponde
al intento de leer un valor fuera de caché; la causa primaria confirmada es la
columna ausente, no ese KeyError.

### Causa y evidencia de lectura

La fuente OCA V19 recién incorporada declara en
`l10n_es_account_statement_import_n43/models/account_journal.py` el campo
almacenado `n43_partner_search`, selección requerida, valor predeterminado
`all`. Opciones: `none`, `caixabank`, `santander`, `sabadell`, `all`.

El repositorio tiene versión **19.0.1.0.0**, pero la base todavía registra
`l10n_es_account_statement_import_n43` como installed **17.0.1.0.1**.
Sus dependencias `account_statement_import_file`, `account_statement_import_base`
y `account_statement_base` también mantienen versión V17. La consulta de
columnas encontró `n43_date_type`, pero **no** `n43_partner_search`.

La incorporación de archivos activó la posibilidad de cargar el código nuevo,
sin crear por sí sola las columnas. Este bloqueo corresponde a la actualización
pendiente de los quince addons, no a un módulo adicional por descargar.

```sql
SELECT name, state, latest_version FROM ir_module_module
WHERE name IN ('l10n_es_account_statement_import_n43',
               'account_statement_import_file',
               'account_statement_import_base', 'account_statement_base');

SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'account_journal'
  AND column_name IN ('n43_date_type', 'n43_partner_search');
```

### Corrección propuesta, todavía no ejecutada

1. Detener el web del ensayo y respaldar base/filestore.
2. Revisar las migraciones de los quince addons incorporados y actualizar el
   bloque pendiente en orden de dependencias. N43 depende de la cadena de
   importación de extractos. Evitar corregir únicamente esta columna mediante
   `ALTER TABLE`: dejaría campos, metadatos, valores requeridos y vistas sin
   actualizar y podrían aparecer los siguientes errores de esquema.
3. Usar la actualización ORM de Odoo, con `--stop-after-init`, sin HTTP ni crons.
   Registrar los logs y revisar las confirmaciones parciales si hay otro fallo.
4. Comprobar versión V19, existencia del campo/columna y valores válidos en los
   diarios. Mantener correo y tareas automáticas neutralizados.

Comando dirigido a N43, como parte del plan de actualización de sus dependencias
y restantes addons pendientes; se entrega para preparación, no se ha ejecutado:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml' run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u l10n_es_account_statement_import_n43 --stop-after-init --no-http --max-cron-threads=0
```

### Validación requerida y reversión

- Abrir el tablero de Contabilidad y diarios con el usuario afectado y sus
  compañías, incluyendo lectura de actividades que aparece en la traza.
- Comprobar los ajustes N43, fecha de operación/valor y selección de búsqueda
  de contactos. El default `all` debe revisarse funcionalmente tras actualizar.
- Comparar diarios, saldos, números e importes contables antes/después; ninguna
  prueba debe contabilizar o importar extractos reales sin autorización.
- Si falla la actualización, restaurar el respaldo en un destino aislado con
  las fuentes correspondientes. No retirar la columna o el addon a ciegas.

Log original: adjunto
`C:\Users\pablo\.codex\attachments\47d9e8cc-74f8-4ec7-827d-885a622384ca\Texto pegado.txt`.
En esta intervención se hicieron únicamente SELECT y lectura de fuentes,
además de actualizar este documento. No se modificaron código de módulos,
manifests, datos/esquema de BD, Excel ni se crearon commits.

## POST-012 — Lista de facturas: campo Studio de agente con relación antigua

**Estado: corrección de metadatos aplicada y validada; apertura con la sesión del usuario pendiente.**

Error al acceder a Clientes → Facturas el 12/10/2026 a las 17:14:46 UTC
(12:14:46 America/Bogota), en `127.0.0.1:8080`:

```text
OwlError: "account.move"."x_studio_agente" field is undefined
```

### Diagnóstico confirmado por SELECT

El campo no se ha perdido de la base:

| Elemento | Estado observado |
|---|---|
| Definición | `ir_model_fields` ID 18548, `account.move.x_studio_agente` |
| Origen / tipo | Studio, `state=manual`, `ttype=char`, `store=True` |
| Relación actual | **`partner_id.agent_ids.name`** |
| Columna física | `account_move.x_studio_agente`, `character varying`, existe |
| XML ID del campo | `studio_customization.nuevo_campo_relacion_2776226f-a343-4393-b096-4d0ac094f523` |
| Vista que lo utiliza | Lista Studio, ID 4271, activa, padre 1470 |
| XML ID de vista | `studio_customization.odoo_studio_account__7bb5169b-e3cd-4637-9538-bc3c03d87e15` |

El código OCA V19 define `res.partner.commission_agent_ids`, mientras que el
campo Studio conserva `agent_ids` en su ruta relacionada. El navegador recibe
la columna en la arquitectura de la lista pero no su definición válida en los
metadatos del modelo. Esto continúa la transición del campo de agentes descrita
en POST-009/010: allí se corrigieron vistas de contactos, no esta definición
relacionada de facturas. No es un módulo adicional por descargar.

```sql
SELECT id, model, name, state, ttype, related, store
FROM ir_model_fields
WHERE model = 'account.move' AND name = 'x_studio_agente';

SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'account_move'
  AND column_name = 'x_studio_agente';

SELECT v.id, v.name, v.active, v.inherit_id, d.module, d.name AS xmlid
FROM ir_ui_view v LEFT JOIN ir_model_data d
  ON d.model = 'ir.ui.view' AND d.res_id = v.id
WHERE v.model = 'account.move' AND v.arch_db::text LIKE '%x_studio_agente%';
```

### Corrección propuesta para la ventana de actualización

Con web detenido y respaldo previo, cambiar únicamente la propiedad `related`
del campo a **`partner_id.commission_agent_ids.name`**, conservando el ID, nombre,
tipo, almacenamiento, columna, XML ID y personalización Studio de la lista.
No crear otra columna, borrar el campo ni rellenar históricos masivamente.

SQL propuesto inicialmente; **ejecutado después con autorización del usuario**:

```sql
BEGIN;
SET LOCAL lock_timeout = '10s';
DO $miac$
DECLARE field_id integer; current_related text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Esta correccion exige la copia V19';
    END IF;
    SELECT f.id, f.related INTO field_id, current_related
    FROM ir_model_fields f JOIN ir_model_data d
      ON d.model = 'ir.model.fields' AND d.res_id = f.id
    WHERE f.model = 'account.move' AND f.name = 'x_studio_agente'
      AND f.state = 'manual' AND f.ttype = 'char' AND f.store
      AND d.module = 'studio_customization'
      AND d.name = 'nuevo_campo_relacion_2776226f-a343-4393-b096-4d0ac094f523'
    FOR UPDATE OF f;
    IF field_id IS NULL THEN RAISE EXCEPTION 'No existe el campo Studio esperado'; END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids' AND ttype = 'many2many') THEN
        RAISE EXCEPTION 'No existe el campo actual de agentes';
    END IF;
    IF current_related = 'partner_id.agent_ids.name' THEN
        UPDATE ir_model_fields SET related = 'partner_id.commission_agent_ids.name'
        WHERE id = field_id;
    ELSIF current_related = 'partner_id.commission_agent_ids.name' THEN
        RAISE NOTICE 'La relacion ya esta corregida';
    ELSE
        RAISE EXCEPTION 'Relacion inesperada: %', current_related;
    END IF;
END;
$miac$;
COMMIT;
```

La operación propuesta modifica un único metadato, no los valores almacenados
de `account_move`. Necesita reconstruir el registro de Odoo tras ejecutarse.
Coordinar el reinicio con la actualización de los quince módulos pendientes,
porque persiste también el bloqueo de esquema N43 de POST-011.

### Pruebas de aceptación y reversión

- Capturar antes/después todos los pares `(id, x_studio_agente)` de facturas;
  exigir que la corrección de metadatos no cambie los valores históricos.
- Comprobar el campo en `account.move._fields` y en `get_views()` de la lista,
  además de abrirla con el usuario afectado.
- Probar contactos sin agentes, con uno y con varios, y confirmar el resultado
  del campo Char relacionado: no convertirlo silenciosamente en una lista
  concatenada de agentes ni dar por aceptada la agregación Many2many.
- Validar futuras modificaciones y rectificativas sin alterar facturas
  contabilizadas durante las pruebas de este ensayo.
- Reversión del metadato: con servicio detenido y estado posterior comprobado,
  restaurar `related='partner_id.agent_ids.name'` para ese mismo XML ID; esa ruta
  requiere el código anterior y reproduce el bloqueo en V19. Para deshacer el
  conjunto, restaurar respaldo y fuentes coherentes en un destino aislado.

En el diagnóstico inicial solo se realizaron lecturas. El usuario autorizó
posteriormente aplicar la corrección; el resultado se registra a continuación.

### Ejecución autorizada de POST-012

- Web detenido antes del ajuste; respaldo íntegro en
  `restore/before_post_012.dump`.
- Se actualizó exclusivamente `ir_model_fields.related` de la definición Studio
  identificada por su XML ID, manteniendo campo, columna, vista y almacenamiento.
- Script ejecutable: `scripts/migration/post_012_studio_invoice_agent_related.sql`.
- Dos ejecuciones exitosas; la segunda fue idempotente.
- Odoo reiniciado. El campo está definido en `account.move._fields`; la vista
  de lista ID 1470 y sus extensiones devuelven `x_studio_agente` tanto en la
  arquitectura como en los metadatos de `get_views()`.
- **30.639 movimientos**, con **3.703 valores de agente almacenados**: huella
  completa de `(id, x_studio_agente)` idéntica antes del SQL, después y después
  del reinicio. No se generó recomputación masiva ni se editaron facturas.
- La auditoría ORM terminó con rollback. No se modificaron código de módulos,
  manifests, Excel ni se crearon commits.
- Evidencias: `logs/post_012_before.json`, `post_012_after_sql.json`,
  `post_012_after_restart.json`, `post_012_apply_*.log`, `post_012_validation.log`.

La corrección resuelve la definición Studio rota. El bloqueo N43 de POST-011 y
la actualización de los quince addons siguen pendientes; no se ejecutaron dentro
de este ajuste. Quedan por probar visualmente la lista con la sesión real y
los cambios futuros de agentes (incluidos contactos con varios agentes).

## POST-013 — Lista de facturas: columna bancaria default_batch_booking ausente

**Estado: causa confirmada; actualización del bloque bancario pendiente.**

Error al acceder a Clientes → Facturas el 12/10/2026 a las 17:28:49 UTC
(12:28:49 America/Bogota), modelo `account.move`:

```text
psycopg2.errors.UndefinedColumn:
column account_payment_mode.default_batch_booking does not exist
```

### Recorrido y causa

`account.move.web_search_read` pasa a `web_read`; al presentar una relación
Many2one necesita el `display_name` del modo de pago. La lectura del registro
consulta campos almacenados de `account.payment.mode`, incluido el nuevo campo
que aporta el addon de banca PAIN. PostgreSQL rechaza esa consulta por faltar
la columna. La corrección de la relación Studio POST-012 permanece aplicada;
esta excepción corresponde a otro desfase de código/esquema.

Definición confirmada en las fuentes:
`account_banking_pain_base/models/account_payment_mode.py:default_batch_booking`,
campo Boolean que propone el agrupamiento bancario de órdenes de pago.
`models/account_payment_order.py:_compute_batch_booking` utiliza ese valor.

| Módulo | Versión de BD observada |
|---|---|
| `account_payment_mode` | `19.0.1.1.0` |
| `account_payment_order` | `17.0.1.4.4` |
| `account_banking_pain_base` | `17.0.1.0.0` |
| `account_banking_sepa_credit_transfer` | `17.0.1.0.3` |
| `account_banking_sepa_direct_debit` | `17.0.1.2.2` |

El manifest PAIN disponible es **19.0.1.1.1**, depende de
`account_payment_order`; sus librerías `unidecode` y `lxml` ya se verificaron
al incorporar las fuentes. Actualizar únicamente `account_payment_mode` no
actualiza necesariamente las extensiones que aportan campos a su misma tabla.

### Diagnóstico de lectura ejecutado

```sql
SELECT name, state, latest_version FROM ir_module_module
WHERE name IN ('account_payment_mode', 'account_payment_order',
               'account_banking_pain_base',
               'account_banking_sepa_credit_transfer',
               'account_banking_sepa_direct_debit');

SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'account_payment_mode'
  AND column_name = 'default_batch_booking';
```

Segunda consulta: **cero filas**, ausencia física de la columna confirmada.
Las fuentes ya están descargadas. No es otro addon que falte incorporar.

### Corrección propuesta y alcance

Preparar respaldo de base y filestore, detener el web y actualizar mediante
Odoo el bloque bancario en orden de dependencias, junto con el resto del plan
de los quince addons pendientes. Revisar previamente los scripts oficiales de
datos y sus efectos sobre mandatos, modos/órdenes de pago y numeración.
No añadir únicamente `default_batch_booking` por SQL: eso no actualiza los
demás campos, valores, metadatos ni vistas de los addons bancarios.

Comando dirigido al bloque bancario, para el procedimiento revisado del ensayo;
**no se ha ejecutado en esta intervención**:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml' run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -u account_payment_order,account_banking_mandate,account_banking_pain_base,account_banking_sepa_credit_transfer,account_banking_sepa_direct_debit --stop-after-init --no-http --max-cron-threads=0
```

Mantener correo/crons neutralizados. Guardar el log completo y revisar la primera
causa si falla; no asumir reversión global de módulos intermedios ya confirmados.
POST-011/N43 y los demás addons también deben actualizarse para validar el
acceso a Contabilidad en su conjunto.

### Validaciones y reversión requeridas

- Verificar columna, definición ORM y versiones V19 del bloque bancario.
- Leer modos de pago y abrir la lista de facturas con el usuario afectado,
  incluyendo facturas que tengan modo de pago y sus nombres relacionados.
- Comparar modos, mandatos, órdenes y líneas de pago, facturas e importes antes
  y después; no generar ni enviar remesas bancarias reales durante el ensayo.
- Comprobar cómo se inicializa el nuevo booleano en modos existentes y el
  comportamiento de agrupación de órdenes; no cambiar condiciones bancarias
  históricas sin revisar su significado funcional.
- Reversión: restaurar el respaldo en un destino aislado con fuentes y filestore
  coherentes; no retirar columnas para intentar volver a V17 parcialmente.

Esta intervención solo realizó SELECT, lectura de fuentes y documentación.
No se ejecutó el comando de actualización, no se modificaron datos/esquema,
código o manifests, Excel ni se crearon commits.

## POST-014 — Sitio web: herencia incompatible del banner Buzzy

**Estado: causa confirmada; corrección del tema y sus vistas pendiente.**

Error al acceder al sitio web el 12/10/2026 a las 17:43:16 UTC
(12:43:16 America/Bogota), al renderizar `website.snippets`:

```text
ValueError: El elemento '<xpath expr="//div[hasclass('row')]//div[2]">'
no puede ser localizado en la vista padre (view: theme_buzzy.s_banner)
```

### Evidencia y causa

Consultas de lectura en `miac_v19_migrada` identificaron:

| Vista | ID observado | Padre | Sitio | Activa |
|---|---|---|---|---|
| `theme_buzzy.s_banner` | 6117 | 5668 | 1 | Sí |
| `website.s_banner`, copia del sitio | 5668 | Sin padre | 1 | Sí |
| `website.s_banner`, plantilla general | 4579 | Sin padre | Sin sitio | Sí |

La copia del sitio contiene un banner de una sola columna dentro de `row`,
con título, texto y enlace. La herencia 6117 espera una segunda columna y una
imagen dentro de ella; también contiene operaciones sobre una tercera columna.
El XPath que falla tiene **cero coincidencias** en las arquitecturas `en_US`,
`es_ES` y `pt_PT` de la vista padre. Las tres traducciones de la herencia contienen
el XPath incompatible.

El XML local `theme_buzzy/views/snippets/s_banner.xml` **no contiene ese XPath**:
es otra estructura, con referencias a imágenes de cuadrícula y `col-lg-5`.
El manifest local declara `1.0.0`, sin versión mayor de Odoo. Por tanto, existe
un desfase entre las fuentes disponibles y las vistas del tema conservadas en
la base migrada; tener el módulo presente no certifica su compatibilidad con 19.
La ausencia de un XML ID ordinario en una copia de tema no se interpreta, por sí
sola, como corrupción.

Este bloqueo es independiente de las columnas bancarias pendientes de
POST-011/POST-013. Actualizar esos addons no corrige esta herencia QWeb.

### Diagnóstico de lectura reproducible

```sql
SELECT id, key, inherit_id, website_id, active, arch_db
FROM ir_ui_view
WHERE key IN ('website.s_banner', 'theme_buzzy.s_banner')
ORDER BY key, id;
```

Los IDs anteriores son evidencia de este ensayo: cualquier procedimiento futuro
deberá resolver y verificar las vistas por clave, sitio y relación de herencia,
sin asumir que los IDs serán iguales en producción.

### Corrección propuesta para revisión

1. Respaldar base y filestore y guardar todas las traducciones de las vistas
   afectadas antes de intervenir.
2. Comparar la plantilla nativa de 19, las copias del sitio y las fuentes del tema;
   identificar qué arquitectura y contenido del cliente deben conservarse.
3. Adaptar la herencia a esa estructura y revisar el conjunto de XPath del tema.
   No eliminar únicamente el XPath que falla: existen otras operaciones sobre
   columnas ausentes y las fuentes locales también necesitan validación.
4. Revisar las rutas de formas SVG: el padre/local conserva `/web_editor/shape/`
   y la herencia utiliza `/html_editor/shape/`. No se ha demostrado que esas
   rutas causen esta excepción; su carga deberá verificarse por separado.
5. Preparar un ajuste reproducible y acotado para la copia migrada. No reinstalar
   ni restablecer el tema a ciegas, desactivar vistas en bloque o borrar páginas:
   esas acciones pueden sustituir diseño y personalizaciones del sitio.

### Aceptación y límites

- Renderizar `website.snippets` sin errores y abrir el editor del sitio.
- Revisar banner, imágenes y páginas públicas, tanto en español como en las
  demás lenguas configuradas; conservar contenido y diseño acordados.
- Comprobar el resto de snippets y recursos del tema para detectar otras
  herencias incompatibles, incluyendo las copias específicas del sitio.
- Registrar el respaldo, el ajuste finalmente ejecutado y sus comprobaciones
  en esta misma incidencia antes de considerar resuelto el bloqueo.

Esta intervención realizó únicamente consultas SELECT, lectura de XML/manifest
y comprobaciones XPath en memoria. Se documentó la incidencia; **no se alteraron
vistas ni datos**, no se actualizó el tema, no se modificaron código/manifests o
Excel y no se crearon commits. La corrección todavía no se había aplicado en esa fase.

### Corrección aplicada con autorización — 12/10/2026

El usuario solicitó «aplica la corrección». Respaldo íntegro previo:
`C:\Proyectos FL\DAM\miac_v19_migrada\restore\before_post_014.dump`.
Snapshots de diagnóstico en `logs/post_014_*views*.json`; el dump es el respaldo
autoritativo. Las primeras exportaciones pueden tener caracteres mal decodificados;
la exportación final `post_014_views_after_utf8.json` usa UTF-8 explícito.

Con web detenido, se desactivaron **ocho herencias incompatibles comprobadas**.
Se conservaron sus arquitecturas, todas las plantillas padre, textos y páginas.
No se reinstaló el tema ni se desactivaron sus vistas en bloque.

| Herencia desactivada | ID ensayo | Padre conservado | Elemento ausente |
|---|---|---|---|
| `theme_buzzy.s_banner` | 6117 | 5668 | Segunda columna |
| `theme_buzzy.s_three_columns` | 6166 | 5671 | `figure` |
| `theme_buzzy.s_call_to_action` | 6120 | 5678 | `h2` |
| `theme_buzzy.s_showcase` | 6158 | 5687 | `img` |
| `theme_buzzy.s_process_steps` | 6150 | 5689 | `s_process_step_number` |
| `theme_buzzy.s_quotes_carousel` | 6153 | 5684 | `span` anidado del autor |
| `theme_buzzy.s_text_block` | 6163 | 5669 | Clase `container` |
| `theme_buzzy.s_product_catalog` | 6151 | 5675 | `o_we_bg_filter` |

Los siete bloqueos adicionales se reprodujeron uno a uno mediante renderizado
QWeb en una transacción de ensayo que se revirtió; después se aplicó el ajuste.

Scripts reproducibles, después de respaldo y con web detenido:

```powershell
Get-Content -Raw 'scripts\migration\post_014_buzzy_redundant_banner.sql' | docker exec -i miac_v19_migrada_db psql -U openpg -d miac_v19_migrada -v ON_ERROR_STOP=1
Get-Content -Raw 'scripts\migration\post_014_buzzy_other_snippets.sql' | docker exec -i miac_v19_migrada_db psql -U openpg -d miac_v19_migrada -v ON_ERROR_STOP=1
```

El primero comprueba claves, relación de sitio y patrón del banner. El segundo
comprueba siete claves concretas, sitio 1 y hashes de las arquitecturas inglesas
de padre/hijo: si difieren en otra copia, aborta y requiere revisión previa.
Ambos se repitieron correctamente para comprobar idempotencia.
El primer intento del segundo abortó por hashes calculados con una decodificación
incorrecta; no aplicó cambios. Se corrigieron usando los hashes de PostgreSQL.

**Pruebas aprobadas:** renderizado completo de `website.snippets`, sitio 1,
con `MockRequest` nativo de Odoo: español (579115 caracteres), inglés (519970) y
portugués (525166). Los intentos iniciales sin petición HTTP fallaron por falta
de contexto de `request`; con el contexto nativo los tres renderizados terminaron
sin errores. Página pública `/`: HTTP 200. Contenedor iniciado y `healthy`.

**Pendiente:** revisión visual con la sesión real, rutas SVG antiguas y aceptación
funcional completa del tema. Este ajuste desbloquea los snippets conservando las
plantillas del sitio; no certifica toda la migración del tema. Actualizar o
reaplicar el tema puede regenerar herencias y requiere repetir estas pruebas.

Reversión: restaurar el dump en un destino aislado. Reactivar solo estas ocho
vistas revierte este ajuste, pero recupera las incompatibilidades originales.
No se modificaron código Odoo, manifests, Excel ni se crearon commits; los scripts
externos de corrección no requieren cambiar la versión del módulo.

## POST-015 — Lentitud y repetición de cargas del registro

**Estado: diagnóstico confirmado; medidas correctivas pendientes.**

Revisión de solo lectura solicitada por el usuario el 12/10/2026. Logs guardados
fuera del repositorio en `C:\Proyectos FL\DAM\miac_v19_migrada\logs`:
`performance_review_20261012.log` (últimas 2500 líneas) y
`performance_review_full_20261012.log` (ventana 17:41:39–18:11:32 UTC).

### Evidencia

- 191 mensajes `Registry loaded` en aproximadamente 30 minutos; la ventana incluye
  reinicios/pruebas anteriores, pero el tramo 18:07–18:10 muestra recargas continuas
  en PID 1, cada pocos segundos, de los mismos 340 módulos. Recargas de 4–7 segundos.
- `product.product/get_views`: 43,286 s, 5635 consultas, 2,494 s SQL y 40,792 s
  de tiempo restante registrado. `/web/action/load`: 39,512 s y 5547 consultas.
- Imágenes de producto: hasta 42 s. Healthcheck: hasta 47,517 s. Las medianas de
  otras peticiones de menú son pequeñas: el problema no es uniformemente lento.
- El tiempo no SQL incluye ejecución y espera/concurrencia, no exclusivamente CPU.
- Recursos, muestra puntual: Odoo 32,55 % CPU y 1,023 GiB RAM; PostgreSQL 6,05 %
  CPU y 240,8 MiB; límite Docker 11,48 GiB. No hay evidencia de agotamiento de RAM.
- PostgreSQL: varias conexiones `idle in transaction / ClientRead`, sin esperas
  de bloqueo `Lock` en la muestra. No prueba ausencia de bloqueos en otros momentos.
- No se encontraron respuestas HTTP 4xx/5xx en las peticiones capturadas; HTTP 200
  no garantiza éxito RPC. Las excepciones Buzzy encontradas corresponden al error
  previo a POST-014, no demuestran una reaparición después del ajuste.

### Prioridad 1: ciclo de actualización parcial

Estos seis módulos siguen en estado **to upgrade**, con versiones 17:
`commission`, `account_commission`, `hr_commission`, `account_payment_partner`,
`dam_website_page_porter` y `sale_product_template_tags`. Sus fuentes no son
instalables/cargables en este entorno 19 y Odoo los omite repetidamente.

El código activo de Odoo 19 confirma:

- `odoo/modules/loading.py`: al terminar una actualización, crea la marca
  `base.partially_updated_database` si quedan estados `to upgrade/to install/to remove`.
- `odoo/orm/registry.py:Registry.new`: consume esa marca y fuerza otra actualización;
  las actualizaciones emiten señal de cambio de registro.
- `check_signaling`: al detectar otra señal, vuelve a cargar el registro.

Los logs muestran verificaciones completas de campos/vistas y señales repetidas,
coherentes con ese ciclo. La marca no apareció en los SELECT puntuales: se consume
al comenzar la recarga y puede recrearse al final; no se observó directamente
su persistencia entre ciclos. No atribuir la lentitud simplemente al volumen del log.

**Propuesta:** con respaldo y web detenido, revisar y cancelar de forma controlada
las solicitudes de actualización imposibles de estos seis módulos, manteniendo
sus datos y el inventario de transiciones pendientes. No marcarlos como migrados,
no desinstalarlos ni ejecutar una actualización de fuentes V17. La cancelación de
solicitudes es una estabilización operativa, no sustituye las correspondencias
OCA, la preservación de comisiones ni la transición de etiquetas/web ya acordadas.
Revisar la marca de actualización parcial dentro del mismo procedimiento.
Preparar script acotado con precondiciones y auditoría; no se entregó ni ejecutó
SQL correctivo en este diagnóstico.

**Aceptación:** sin recargas continuas durante navegación repetida y healthchecks,
sin aumento continuo de señales, menús e imágenes sin miles de consultas de carga.
Comparar tiempos antes/después con la misma navegación.

### Prioridad 2: integración de comisiones de empleados

Aviso repetido de vista inválida para `commission.settlement`:
`mark_as_invoiced no es una acción válida`. Vista 3998,
`hr_commission.view_settlement_form`, activa, padre 3616.
El método existe en `hr_commission_oca/models/sale_commission_settlement.py`,
pero **hr_commission_oca está uninstalled**. La vista antigua espera una función
que no está cargada. Revisar instalación del equivalente 19 y transición de
vistas/grupos/tipos de agente e históricos. No ocultar el botón para dar por
completada la conservación funcional del módulo.

### Prioridad 3: avisos de menor impacto

- Botones `fa-gear` sin título en personalizaciones Studio de ventas/suscripciones:
  vistas 4063 y 4068, entre otras. Corregibles, sin indicio de ser la causa principal.
- Etiquetas duplicadas: imágenes en movimientos, cliente en líneas de venta y
  fechas de suscripción. Afectan claridad; no justificar borrar campos ni datos.
- `error_line_wiz` sin licencia declarada: corregir manifest con revisión de autoría.
- Fuentes con versión incompatible: `base_edi`, `edi_account_oca`,
  `edi_exchange_template_oca`, `edi_oca`, además de DAM excluido. Revisar si forman
  parte de la instalación y limitar addons_path a fuentes compatibles; no borrarlas
  a ciegas ni asumir que todas son dependencias activas.

### Configuración e incidencias anteriores

`workers=0`, crons=0, correo bloqueado. No aumentar workers antes de resolver el
ciclo: varias instancias pueden amplificar las recargas/señales y no corrigen estados.
El healthcheck cada 15 s participa en las peticiones; no es por sí solo la causa.
El repositorio y filestore están en montajes Windows: evaluar su coste solo después
con una medición comparable; este diagnóstico no demuestra un cuello de botella ahí.

En la revisión actual, `account_payment_order` figura 19.0.1.0.7,
`account_banking_pain_base` 19.0.1.1.1 y N43 19.0.1.0.0. Por tanto, los pendientes
bancarios descritos en POST-011/013 reflejan un estado anterior. Estas versiones
no certifican sus pruebas funcionales, pero no procede volver a tratarlos como
addons todavía en versión 17.

No se modificaron configuración, base/esquema, código Odoo o Excel ni se reinició
ningún servicio. Solo SELECT, lectura de fuentes/logs, captura de evidencias y
esta documentación. No se crearon commits.

### Ajustes aplicados con autorización — 12/10/2026

El usuario solicitó «aplica los ajustes». Se detuvo únicamente
`miac_v19_migrada`, se guardó `restore/before_post_015.dump` y se capturaron
estados de módulos, tipos de agente, liquidaciones y vistas de HR en
`logs/post_015_before.json`.

1. Se ejecutó `scripts/migration/post_015_cancel_unloadable_upgrades.sql`:
   cancela las seis solicitudes `to upgrade` devolviéndolas a `installed`,
   **sin declararlas migradas, cambiar sus versiones o desinstalarlas**.
   Solo admite los seis nombres revisados y aborta si existen otras operaciones
   pendientes. Retira la marca de actualización parcial en la misma transacción.
2. Con web detenido, se instaló `hr_commission_oca` oficial 19.0.1.0.0 usando:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19_migrada\compose.yaml' run --rm --no-deps --entrypoint python3 web /usr/bin/odoo -c /etc/odoo/miac.conf -d miac_v19_migrada -i hr_commission_oca --stop-after-init --no-http --max-cron-threads=0
```

3. Se ejecutó `scripts/migration/post_015_retire_legacy_hr_views.sql`:
   exige equivalente HR instalado en 19 y sus dos vistas activas; desactiva
   únicamente las herencias antiguas `hr_commission.view_partner_form_agent`
   y `hr_commission.view_settlement_form`, conservando sus registros/XML IDs.
4. Se inició el web, conservando crons desactivados y bloqueo de correo.

**Resultados:** cero operaciones de módulos pendientes y sin marca parcial.
Ocho peticiones consecutivas de salud: HTTP 200, 0,022–0,078 segundos.
Esto mide salud HTTP/base, no certifica los tiempos de todos los menús autenticados.
La prueba ORM `get_views` de liquidaciones confirma un único botón
`mark_as_invoiced`, método callable y opción `salesman` disponible.
Comparación por hashes: sin cambios en tipos de agente de contactos ni en
IDs/agentes/estados/fechas de las 27 liquidaciones. No se ejecutó el botón sobre
liquidaciones reales ni se crearon facturas/liquidaciones para la comprobación.
Evidencias: `logs/post_015_install_hr.log`, `post_015_validation.json` y
`post_015_hr_validation.log`.

Las correspondencias completas de namespaces OCA y los módulos sustituidos o
excluidos permanecen pendientes. Las advertencias de módulos antiguos omitidos
pueden seguir apareciendo al arrancar: se conservaron sus metadatos, y **no se
ha ocultado el log ni dado esos módulos por migrados**. Los avisos cosméticos de
etiquetas/Studio/licencia quedan separados; no justifican cambios indiscriminados
ni asumir una licencia desconocida. Validar navegación con la sesión del usuario
antes de certificar rendimiento funcional.

No se cambiaron workers, healthcheck, addons_path, código de módulos o manifests;
las versiones oficiales OCA se conservaron. No se modificó Excel ni se crearon
commits. Reversión íntegra: restaurar `before_post_015.dump` en un destino aislado
con el mismo filestore y fuentes. No desinstalar HR para intentar revertir a mano.

Comprobación adicional tras reinicio: en el tramo 18:15:59–18:16:50 UTC, el
proceso web cargó el registro una sola vez al iniciar; los healthchecks siguientes
usaron cinco consultas y aproximadamente 0,02 s en el log. La señal de registro
permaneció en 603 entre dos comprobaciones. `/web/login`: HTTP 200, 0,636 s;
imágenes de productos 3952 y 4027: HTTP 200, 0,373 y 0,032 s. Muestra posterior
sin carga de navegación: CPU Odoo 0,02 %, RAM 209,9 MiB; no comparar ese porcentaje
como benchmark bajo una carga idéntica. Contenedor `running healthy`.

## POST-016 — Editor web: raíz nula del iframe auxiliar

**Estado: punto de fallo confirmado; corrección JavaScript propuesta, pendiente.**

El usuario reportó el 12/10/2026 a las 18:54:11 UTC (13:54:11 Bogota):
`Cannot read properties of null (reading 'replaceChildren')`, en
`WebsiteBuilderClientAction.resolveIframeLoaded`.

### Evidencia actual

- El asset servido `/web/assets/517c3a3/web.assets_web.min.js` contiene exactamente
  `this.iframefallback.el?.contentDocument.documentElement.replaceChildren()`.
- La fuente activa de Odoo coincide:
  `website/static/src/client_actions/website_preview/website_builder_action.js`,
  método `setIframeLoaded`, línea 646 aproximadamente.
- La instalación local de enero de 19 conserva la misma expresión. El operador
  opcional protege únicamente la ausencia del elemento iframe; no protege
  `contentDocument` ni `documentElement`. El error informado señala que la raíz
  sobre la que se invoca `replaceChildren` es nula.
- La plantilla cliente monta dos iframes; el principal dispara `onIframeLoad`,
  que limpia el auxiliar. El auxiliar no tiene un evento que sincronice esta
  limpieza con el final de su propia carga. Una carrera de carga es una explicación
  coherente; no se reprodujo visualmente ni se capturó el DOM en el instante exacto.
- Logs 18:54:10–18:54:11: sitio `/` HTTP 200, `/website/iframefallback` HTTP 200,
  bundle del constructor HTTP 200 y render de snippets RPC HTTP 200, sin nueva
  excepción de herencia Buzzy en ese tramo. El 200 aislado no certifica éxito RPC.
- Render de `website.iframefallback` en contexto nativo `MockRequest`, sitio 1
  y español: 1348 caracteres, raíz `html`, un `head` y un `body`. La plantilla
  persistida no está vacía ni carece estructuralmente de raíz HTML.
- La consulta pública sin sesión a `/website/iframefallback` redirige al login:
  es normal porque la ruta requiere usuario; no usarla para certificar el iframe
  autenticado.

### Corrección técnica propuesta

Proteger la limpieza del documento auxiliar cuando no exista su raíz, conservando
la resolución de la promesa y el registro nativo de eventos:

```javascript
this.iframefallback.el?.contentDocument?.documentElement?.replaceChildren();
```

Debe aplicarse como ajuste reproducible de la distribución Odoo o mediante una
extensión de assets controlada y versionada, con alcance limitado al método del
constructor. No editar solamente el asset minificado, borrar adjuntos de assets
por SQL, cambiar páginas o reinstalar Buzzy: no corrigen el punto de fallo.
Antes de elegir el mecanismo, revisar los patrones de extensiones web del repo
para evitar duplicar todo el constructor o modificar el núcleo sin trazabilidad.

Validar inicio del editor, recarga, navegación entre páginas, primera carga con
caché vacía y cargas posteriores, tanto vista previa como edición, en navegador
real. Comprobar ausencia del TypeError y que la limpieza/loader/hotkeys continúan
funcionando. La protección evita esa excepción; no sustituye la comprobación del
ciclo completo del iframe.

Esta intervención solo leyó logs, código y assets y renderizó la plantilla en
una transacción revertida. No se modificaron base, código, manifest ni assets,
no se reiniciaron servicios, no se cambió el Excel ni se crearon commits.
El aviso de menú `Missing model website.site.transfer.wizard` visto en los logs
corresponde al porter excluido y se mantiene separado de este TypeError.

## POST-017 — Ecommerce /shop: herencia de filtros incompatible

**Estado: reproducido, causa confirmada; corrección pendiente.**

Error del usuario y del log: `/shop`, HTTP 500, 12/10/2026 18:56:22 UTC
(13:56:22 Bogota). Reproducción por petición pública HTTP también devuelve 500.

```text
ValueError: El elemento '<xpath expr="//div[contains(@t-attf-class,
'products_attributes_filters')]">' no puede ser localizado en la vista padre
```

La excepción visible aparece mientras Odoo construye la página de diagnóstico
500 y vuelve a combinar la vista; el fallo de herencia está confirmado directamente
por la arquitectura, sin atribuirlo a sobrecarga del servidor.

| Vista | ID ensayo | Sitio | Padre |
|---|---|---|---|
| `website_sale.products` estándar | 5442 | General | Sin padre |
| `website_sale.products_attributes` estándar | 5464 | General | 5442 |
| `website_sale.products` copia conservada | 5783 | 1 | Sin padre |
| `website_sale.products_attributes` copia activa | 5790 | 1 | 5783 |

La plantilla general 19 contiene:

```xml
<div t-attf-class="products_attributes_filters d-empty-none ..."/>
```

La copia del sitio conserva:

```xml
<div class="products_attributes_filters"/>
```

El XPath de la vista 5790 tiene cero coincidencias en el padre 5783; sí encuentra
una coincidencia en la plantilla estándar 5442. El contenedor existe en la copia,
pero usa `class`, no `t-attf-class`. Las vistas específicas del sitio prevalecen
sobre la general. Actualizar la plantilla general no garantiza adaptar la copia.

**Ajuste propuesto:** adaptar únicamente ese selector de la herencia específica
para admitir el contenedor fijo y el dinámico, conservando filtros y contenido:

```xml
<xpath expr="//div[hasclass('products_attributes_filters') or contains(@t-attf-class, 'products_attributes_filters')]" position="inside">
```

Respaldar base y todas las traducciones de la vista antes de modificarla.
Resolver por clave/sitio/herencia, no por ID fijo; validar una sola coincidencia
por idioma, preservar el resto de arquitectura y registrar script idempotente.
No desactivar los filtros ni sustituir toda la plantilla personalizada por la
estándar. Después comprobar composición completa, `/shop`, categorías, atributos,
búsqueda y ficha de producto con sesión pública y autenticada. Podrían aparecer
otras incompatibilidades en pasos posteriores del renderizado; no certificar
el ecommerce completo solo por resolver este XPath.

No se modificaron vistas, datos, fuentes, manifests o Excel ni se reiniciaron
servicios. Consultas SELECT, lectura de fuentes y petición HTTP de diagnóstico.
Este bloqueo es distinto de POST-016 (JavaScript del iframe auxiliar).

### Corrección aplicada con autorización — 12/10/2026

El usuario solicitó «aplicalo». Se detuvo el web y se respaldó la base en
`C:\Proyectos FL\DAM\miac_v19_migrada\restore\before_post_017.dump`.
Snapshots completos de las dos vistas del sitio:
`logs/post_017_views_before.json` y `post_017_views_after.json`.

Se ejecutó `scripts/migration/post_017_shop_attributes_xpath.sql`, que resuelve
la herencia por clave, sitio 1 y padre, exige un registro único y comprueba las
traducciones. Sustituye exclusivamente el XPath indicado por la variante que
admite `class` fijo y `t-attf-class`. No se desactivaron filtros ni se reemplazó
la plantilla de productos. El script se repitió correctamente: idempotencia.

```powershell
Get-Content -Raw 'scripts\migration\post_017_shop_attributes_xpath.sql' | docker exec -i miac_v19_migrada_db psql -U openpg -d miac_v19_migrada -v ON_ERROR_STOP=1
```

Se inició el web. Pruebas públicas: `/shop` HTTP 200 (0,922 s), búsqueda
`/shop?search=licencia` HTTP 200 (0,076 s) y ordenación
`/shop?order=name+asc` HTTP 200 (0,071 s). Comparación exacta de todas las
arquitecturas traducidas: padre sin cambios e hija únicamente con la sustitución
revisada. XML válido. Contenedor iniciado y saludable.

Persisten advertencias QWeb de `t-cache` y `t-nocache` en la plantilla conservada
5783; no provocaron error 500 en estas pruebas. Revisarlas en la aceptación
completa de ecommerce, sin eliminar personalizaciones indiscriminadamente.
Quedan por verificar visualmente categorías, atributos, productos, carrito y
sesión autenticada; no se realizaron compras ni pagos durante la prueba.
POST-016, del JavaScript del iframe auxiliar, permanece independiente y pendiente.

No se modificó código de módulos o manifests, Excel ni se crearon commits.
La corrección es un script externo aplicado a la copia migrada, no una actualización
del módulo estándar. Reversión íntegra: restaurar el dump en una copia aislada;
para reversión puntual, revisar el snapshot y restituir la arquitectura original
5790 (recuperaría el error original). Adaptar precondiciones a cualquier otra copia.

## POST-018 — Tarjetas ecommerce: contexto V17 incompleto para V19

**Estado: corrección aplicada como continuación del desbloqueo de /shop.**

Error del usuario, confirmado en logs 12/10/2026 21:51:38 UTC:
`KeyError: ribbon`, `website_sale.products_item` (5437), llamada desde la copia
conservada `website_sale.products` (5783). El ajuste POST-017 corrigió el selector
de filtros, pero no certificaba tarjetas visibles en sesión autenticada. La
petición pública seguía dando 200 sin reproducir esta rama; esa prueba era insuficiente.

La plantilla de tarjetas V19 requiere `ribbon` y `product_href`. El llamador del
sitio mantenía únicamente `product=td_product['product']`. El llamador estándar
V19 también prepara precios, cinta y enlace mediante métodos nativos.

Conservando el diseño/tablas y traducciones del padre, se añadieron dentro de
su llamada `website_sale.products_item`, después de preparar `product`:

```xml
<t t-set="template_price_vals" t-value="get_product_prices(product)"/>
<t t-set="ribbon" t-value="product._get_ribbon(price_vals=template_price_vals, auto_assign_ribbons=auto_assign_ribbons, variant=product_variants[product])"/>
<t t-set="design_field" t-value="website.shop_opt_products_design_classes"/>
<t t-set="product_href" t-value="product._get_product_url(category, product_query_params, grouped_attributes_values)"/>
```

No se añadió una cinta vacía para ocultar el problema; se reutiliza la selección
nativa de cintas manuales/automáticas y enlaces con filtros. No se tocó la tarjeta
estándar ni se publicó/modificó ningún producto.

Respaldo con web detenido: `restore/before_post_018.dump`. Snapshot completo:
`logs/post_018_before.json`. Script:
`scripts/migration/post_018_shop_tile_context.sql`, preparado para este sitio,
con guardas de arquitectura exacta antes/después, todas las traducciones y
transacción. Ejecutado y repetido correctamente (idempotencia). Aplicación:

```powershell
docker cp 'scripts\migration\post_018_shop_tile_context.sql' miac_v19_migrada_db:/tmp/post_018.sql
docker exec miac_v19_migrada_db psql -U openpg -d miac_v19_migrada -v ON_ERROR_STOP=1 -f /tmp/post_018.sql
```

**Verificación:** XML válido en en_US, es_ES y pt_PT. Renderizado individual de
las 20 tarjetas que devuelve el controlador nativo `shop` bajo entorno usuario
37, con `MockRequest`, tarifa existente del sitio, posición fiscal vacía y carrito
vacío: 99476 caracteres en conjunto, sin `KeyError ribbon` ni fallo de tarjetas.
La prueba se revirtió; no creó pedidos/pagos. Su callback de prueba devolvió
inicialmente un entero, que el wrapper HTTP rechazó después de renderizar todas
las tarjetas; no es un error del sitio. El log contiene el resultado
`PRODUCT_TILES_RENDER_OK 20 99476`.

Los intentos de renderizado completo con MockRequest encontraron limitaciones
artificiales de contexto/routing canónico; por ello **no certifican la página
completa autenticada**. Pendiente revisión con la sesión real, cintas visibles,
enlaces, categorías/atributos, precios y carrito. Pruebas HTTP públicas de `/shop`
y búsqueda: 200 tras el ajuste. Contenedor iniciado y saludable.

No se modificó código de módulos o manifests, Excel ni se crearon commits.
Solo se adaptó la arquitectura de la copia migrada, con script externo revisable.
No cambió la versión del addon estándar. Reversión: respaldo aislado o snapshot
previo revisado, sin restablecer a ciegas todo el diseño del ecommerce.
