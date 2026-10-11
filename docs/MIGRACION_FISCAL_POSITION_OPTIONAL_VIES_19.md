# Detección de posiciones fiscales por VIES en Odoo 19

Fecha: 2026-10-11. Rama: `staging_v19`.
Módulo: `account_fiscal_position_autodetect_optional_vies`.
Versión: `19.0.1.0.0`.

## Fuentes e implementación

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons`,
instalación local `C:\Program Files\Odoo 19.0e.20260105` y repositorio.
Se aplicaron las convenciones de desarrollo del proyecto.

- Incorporadas fuentes OCA/Tecnativa, licencia AGPL-3, documentación, icono
  y traducción italiana, sin archivos compilados. Los enlaces de la documentación
  original identifican su procedencia V17; esta adaptación local no declara
  disponibilidad oficial de una versión OCA 19.
- Conservados nombre técnico, campo `vat_vies_required` y XML ID
  `account_fiscal_position_form_view`, sin renombrar ni rellenar datos existentes.
- Manifest versionado una sola vez, con descripción técnica/funcional;
  dependencias directas `account` y `base_vat` e instalación manual.
- Sustituidos los overrides antiguos de `search()` y `_get_fiscal_position()`
  por `_get_fpos_validation_functions()`, llamando a `super()`.
- El criterio compara la casilla con `commercial_partner_id.vies_valid`
  de la dirección efectiva seleccionada por Odoo 19.
- Casilla junto a NIF requerido, visible con detección automática y NIF requerido.
  Ocultarla conserva su valor.

Archivos principales: `__manifest__.py`, `models/account_fiscal_position.py`,
`views/account_fiscal_position_view.xml` y
`tests/test_account_fiscal_position_vies.py`, además de los recursos originales.
No se modificó `account_fiscal_position_partner_type` ni se añadió como dependencia.

## Regla funcional preservada

| Casilla | Contacto comercial que coincide |
|---|---|
| Marcada | VIES válido almacenado |
| Desmarcada | VIES no válido almacenado |

La casilla desmarcada no significa ausencia de restricción. Esta clasificación
también se aplica a posiciones automáticas genéricas aunque la casilla esté oculta.
Si ninguna posición cumple todos los criterios, no se asigna una automáticamente.

Las posiciones manuales conservan prioridad. Las comprobaciones nativas de NIF/VIES,
geografía, compañía y secuencia permanecen activas. Por ello, una compañía que exige
VIES puede descartar una posición con NIF requerido para un contacto no validado.
La dirección utilizada es la que decide Odoo: entrega o facturación según sus reglas,
incluida la excepción nativa por prefijo de IVA intracomunitario coincidente.

La selección solo lee el resultado VIES existente. No añade llamadas al servicio,
recálculos de contactos, actualización de documentos ni tareas automáticas.

## Validación en el ensayo aislado

Base y contenedor: `miac_v19`, independientes de la base del cliente.

- Instalación y actualización correctas.
- **27 pruebas aprobadas, cero fallos y cero errores:** 14 del módulo,
  3 de B2B/B2C y 10 regresiones existentes de JH.
- Conservadas y adaptadas las dos pruebas originales de facturas.
- Cobertura: contactos e hijos, dirección efectiva, falta de NIF, posiciones
  manuales y genéricas, país/provincia/código postal/grupo, compañía, secuencia
  y ausencia de coincidencias; combinaciones B2B/B2C y VIES en facturas y ventas.
- Verificación nativa de compañía activada/desactivada; respuestas válidas
  y no válidas del servicio simuladas localmente, sin consultar Internet.
- Comprobado que detectar la posición no llama al servicio VIES.
- Formulario revisado en navegador: casilla visible en su lugar, se oculta
  al quitar NIF requerido y conserva el valor al mostrarse de nuevo.
  Cambios del formulario de prueba descartados sin guardar.
- Consola del navegador sin errores ni advertencias durante la revisión.
- Permisos nativos conservados: usuarios internos pueden leer posiciones;
  administradores contables pueden gestionarlas. No hay nuevas ACL ni menús.
- Validador estático: 19 módulos del grafo, 6 Python, 1 XML y 1 vista compuesta.
- Contenedor iniciado y saludable; correo sin servidores activos y crons
  desactivados con `max_cron_threads=0`.

El registro del servidor conserva advertencias de etiquetas duplicadas y de
accesibilidad de vistas de otros módulos, principalmente JH. No son fallos de
las pruebas ni bloquean la instalación; no se ampliaron los cambios a esos módulos.

Al alternar la verificación de compañía dentro de una misma prueba se invalida
la caché del campo nativo `perform_vies_validation`, reproduciendo una petición
nueva después de guardar Ajustes. No se cambió el compute nativo.

Comando de actualización y pruebas, con el servicio web detenido:

```powershell
docker compose run --rm --no-deps web -u account_fiscal_position_autodetect_optional_vies,account_fiscal_position_partner_type,jh_sales_subscription --test-enable --test-tags optional_vies19,/account_fiscal_position_partner_type,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/optional-vies19-tests-final-20261011.log
docker compose up -d web
```

Respaldo y evidencias en `C:\Proyectos FL\DAM\miac_v19`:

- `optional-vies19-before-20261011.dump`.
- `optional-vies19-before-20261011-filestore.tar.gz`.
- `optional-vies19-tests-final-20261011.log`: resultado final satisfactorio.
- `optional-vies19-install-tests-20261011.log`: primera ejecución; conserva
  los errores de preparación de pruebas corregidos antes del resultado final.
- `optional-vies19-ui-20261011.jpg`: casilla en el formulario nativo.

## Conservación y pendiente

La aceptación técnica se completa en la instalación de ensayo. Queda pendiente
comprobar valores y casos reales de MIAC en una copia previamente migrada.
No se ejecutaron conversiones sobre el cliente, no se recalcularon históricos,
no se modificó el Excel ni se crearon commits. Se preservaron los cambios
pendientes de JH y de otros módulos.
