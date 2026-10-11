# Gestor de configuraciones del reporte de facturas en Odoo 19

Fecha: 2026-10-11. Rama: `staging_v19`.
Origen: commit `637b73ed8a321c0567cda8d517798c13299bf4e0` de Odoo 17.
Módulo: `jh_sales_subscription`, versión `19.0.1.1.0`.

## Funcionalidad

El asistente **Exportar Reporte de Facturas** permite guardar filtros, columnas y
formato CSV/Excel con un nombre, cargarlos, actualizarlos explícitamente, eliminarlos
y administrarlos. Cada configuración es privada por usuario y compañía.

- Una configuración predeterminada se carga al abrir el asistente en su compañía.
- Los períodos mes actual, mes anterior y año actual se calculan al cargar.
  Mes y año actuales terminan en la fecha de consulta; el mes anterior abarca todo el mes.
- Las fechas manuales se conservan tal como se guardaron.
- Cambiar filtros no modifica la configuración guardada hasta pulsar **Actualizar**.
- **Guardar como nueva** conserva la configuración original; requiere otro nombre.
- No se almacenan resultados ni archivos exportados en las configuraciones.
- Si los filtros contienen registros eliminados o compañías inactivas, se avisa sin
  bloquear la apertura del asistente con sus valores normales.

## Adaptación técnica

- Modelo persistente `jh.invoice.report.preset`, campos y XML IDs del cambio original.
- Restricción única mediante `models.Constraint` y acceso mediante `check_access()` de 19.
- Vista y acción de administración de tipo `list`, conservando el XML ID original.
- Regla privada por usuario y compañías activas; comprobación del acceso tras editar
  para impedir transferir una configuración privada mediante RPC.
- Creación y edición múltiple de predeterminadas: prevalece la última del lote por
  usuario y compañía, evitando dejar todas desmarcadas.
- Validación de filtros guardados, opciones y fechas al cargarlos.
- Conservadas las consultas y exportaciones existentes de V19, sin `sudo()`.
- Manifest incrementado una sola vez desde `19.0.1.0.2` por esta mejora independiente.

Archivos: `models/jh_invoice_report_preset.py`, `models/jh_invoice_report_wizard.py`,
`models/__init__.py`, `security/ir.model.access.csv`,
`security/jh_invoice_report_preset_security.xml`,
`views/actions_jh_invoice_report_wizard.xml`, `__manifest__.py` y `tests/`.

## Validación ejecutada

En el Docker aislado `miac_v19`, usando el código Enterprise local de Odoo 19:

- Actualización del módulo correcta; versión instalada `19.0.1.1.0`.
- **18 pruebas aprobadas: 0 fallos y 0 errores.**
  Ocho del gestor y las diez regresiones `jh_migration19` existentes.
- Cobertura: filtros, categorías, agentes, columnas, formato, fechas manuales y relativas,
  febrero bisiesto, predeterminada y nombres únicos, operaciones múltiples,
  privacidad, cambio de propietario, compañías, filtros eliminados/incorrectos,
  edición mediante `Form`, acción de administración y exportaciones CSV/XLSX.
- Sintaxis Python, XML, RelaxNG de las vistas nuevas y `git diff --check` correctos.
- Servicio iniciado y saludable; `/web/login` responde HTTP 200.
- Correo sin servidores activos y ejecución de cron deshabilitada en la configuración.
- Las pruebas se revierten: no dejaron configuraciones persistentes en el ensayo.

Comando de actualización y pruebas, desde `C:\Proyectos FL\DAM\miac_v19`:

```powershell
docker compose stop web
docker compose run --rm --no-deps web -u jh_sales_subscription --test-enable --test-tags jh_report_presets19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/jh-presets19-tests-final-20261011.log
docker compose up -d web
```

Evidencias y respaldo previo en esa carpeta:

- `jh-presets19-tests-final-20261011.log`.
- `jh-presets19-before-20261011.dump`.
- `jh-presets19-before-20261011-filestore.tar.gz`.

El validador estático original detectó diferencias de SHA-256 en los addons OCA
por finales de línea CRLF del checkout Windows. Los archivos coinciden con el lock
al aceptar LF/CRLF equivalentes; no se modificaron los addons ni el archivo de lock.
Con esa normalización temporal, el validador completo terminó correctamente:
54 módulos del grafo, 64 archivos Python, 37 XML y 48 vistas compuestas.

## Límites

El ensayo usa la instalación aislada; queda pendiente la aceptación funcional y la
comprobación con una copia migrada de los datos reales de MIAC. No se ejecutaron
conversiones sobre el cliente ni se modificó el Excel de seguimiento. No se creó commit.
