# sale_commission_salesman — migración a Odoo 19

Fecha: 2026-10-06. Rama: `staging_v19`.

## Resultado

Adaptación local del módulo OCA/Tecnativa del respaldo a **19.0.1.0.0**.
Instalado y actualizado en el Docker aislado `miac_v19`. Se conservan nombre
técnico, campo `res.partner.salesman_as_agent`, XML IDs, autoría, licencia
AGPL-3, iconos y archivos de traducción originales. Las referencias upstream
a Odoo 17 del README identifican la procedencia; esta adaptación no se presenta
como una versión oficial descargada de OCA para 19.

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons`, Odoo local
`C:\Program Files\Odoo 19.0e.20260105` y repositorio. Sin búsqueda web ni descargas.

## Comportamiento

- Primero utiliza los agentes del cliente obtenidos por el flujo OCA.
- Si no se obtienen agentes, propone el contacto del vendedor del pedido
  (`user_id`) o de la factura/rectificativa de cliente (`invoice_user_id`).
- El vendedor necesita `agent`, `salesman_as_agent` y una comisión configurada.
  Activar la opción sin comisión conserva la restricción original de validación.
- No añade el vendedor junto a agentes del cliente ni sustituye agentes
  proporcionados expresamente en los valores de la línea.
- No asigna el vendedor en productos exentos, secciones, notas, compras o
  asientos ordinarios. El módulo conserva las reglas OCA de agentes del cliente.
- Conserva los tipos de liquidación admitidos por el comportamiento original
  del vendedor, incluido `manual`.
- Cambiar el vendedor **no recalcula los agentes existentes**. Para aplicar
  el nuevo vendedor se usa «Regenerar agentes» en documentos editables.
  Esa acción nativa reconstruye los agentes: puede reemplazar ajustes manuales
  de las líneas seleccionadas y debe utilizarse de forma deliberada.
- El traslado a factura utiliza el flujo nativo. Una factura parcial posterior
  mantiene los agentes de las líneas del pedido, aunque cambie el vendedor.
- Rectificativas conservan el signo negativo de comisión de OCA.

## Integración con MIAC/JH

JH reemplaza `_compute_agent_ids` sin llamar a `super()`. La adaptación retira
los overrides originales de ese cálculo e incorpora el fallback en
`_prepare_agents_vals_partner` de las líneas de venta y factura. Tanto OCA
como JH utilizan ese método, por lo que no se necesita modificar JH ni añadirlo
como dependencia del módulo.

Después de obtener los valores de `super()`, se utiliza `_prepare_agent_vals`
para preparar al vendedor. Así se conserva la selección por categoría de JH
y la prioridad posterior de una comisión elegida manualmente. La prueba
integrada valida comisión del agente, categoría, selección manual y traslado
de esta última a factura.

Dependencias directas: `sale_commission_oca`, `account_commission_oca` y
`commission_oca`. La vista mantiene el XML ID propio `view_partner_form_agent`
y hereda `commission_oca.view_partner_form_agent`. La opción queda junto a
la comisión y se oculta si el contacto no tiene usuarios asociados.

`hr_commission_oca` permanece independiente: se verificó un vendedor vinculado
a un empleado, con `agent_type=salesman`, además de sus tres regresiones OCA.

## Archivos modificados

- `sale_commission_salesman/__manifest__.py`: versión, dependencias y descripción.
- `sale_commission_salesman/models/sale_order.py` y `account_move.py`: fallback.
- `sale_commission_salesman/models/res_partner.py`: ayuda del campo en dos líneas.
- `sale_commission_salesman/views/res_partner_views.xml`: referencia OCA 19.
- `sale_commission_salesman/tests/test_sale_commission_salesman.py`: cinco
  escenarios originales adaptados y once escenarios adicionales.
- README, descripción fuente y descripción HTML: procedencia y comportamiento en 19.
- `tools/validate_jh_odoo19.py`: módulo incluido en la validación estática.

No se cambió código, versión ni datos oficiales de las dependencias OCA.
No se modificó código ni versión de JH.

## Pruebas y evidencia

| Comprobación | Resultado |
| --- | --- |
| Instalación en `miac_salesman19_clean`, solo dependencias OCA | Correcta |
| Actualización y pruebas en esa base | 14 aprobadas; 2 de integración JH/HR omitidas allí |
| Pruebas integradas en `miac_v19` | 50 aprobadas; ninguna omitida; 0 fallos y 0 errores |
| Actualización final de `sale_commission_salesman` | Correcta, salida 0 |
| Validación estática | 26 dependencias, 8 archivos Python, 1 XML y vista compuesta correctos |
| `git diff --check` | Correcto |

Desglose de las 50 pruebas integradas:

- 16 de `sale_commission_salesman`.
- 10 de JH.
- 17 de `account_commission_oca`.
- 4 de `sale_commission_oca`.
- 3 de `hr_commission_oca`.

Incluyen prioridades y asignaciones explícitas; productos exentos; ausencia
de vendedor configurado; conservación al cambiar vendedor; regeneración
repetida sin duplicados; facturación parcial; facturas directas y rectificativas;
exclusión de compras/asientos; liquidaciones repetidas sin duplicados; vista
de contactos y acceso restringido a documentos de otra compañía.

La preparación inicial de las pruebas requería permisos de ventas además de
los contables del helper nativo. Se corrigió usando `get_default_groups`,
siguiendo los patrones locales de Odoo 19, sin ampliar permisos del módulo.

Logs y respaldo en `C:\Proyectos FL\DAM\miac_v19`:

- `salesman-clean-verified.log`
- `salesman-miac-tests.log`
- `salesman-miac-update.log`
- `miac_v19-before-salesman-20261006.dump`
- `miac_v19-before-salesman-filestore-20261006.tar.gz`

### Repetir las pruebas

Desde la carpeta de Docker, sin otro proceso Odoo sobre la misma base:

```powershell
docker compose stop web
docker compose run --rm --no-deps web -u sale_commission_salesman,sale_commission_oca,account_commission_oca,hr_commission_oca,jh_sales_subscription --test-enable --test-tags salesman_migration19,jh_migration19,/sale_commission_oca,/account_commission_oca,/hr_commission_oca --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/salesman-repeat.log
docker compose up -d web
```

## Conservación y pendientes

La instalación no ejecuta conversiones, crons, backfill ni recomputaciones
masivas de agentes. No se escriben comisiones al consultar documentos.
Al finalizar las pruebas el ensayo conserva cero pedidos, asientos y
liquidaciones; los datos de las pruebas son transaccionales.

`miac_v19` se deja iniciado en `http://localhost:8079`. La ejecución de crons
continúa deshabilitada con `max_cron_threads=0`; no hay servidores de correo
activos y SMTP apunta a `127.0.0.1:1`.

La conservación de históricos reales y la aceptación del cliente se comprobarán
posteriormente en una copia migrada de MIAC. No se actuó sobre la base del cliente,
no se actualizaron libros de seguimiento y no se creó ningún commit.

Commit recomendado: `[IMP] #xxxxxx Migra comisiones del vendedor a Odoo 19`.
