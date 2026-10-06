# sale_subscription_start_date — migración a Odoo 19

Fecha: 2026-10-06. Rama: `staging_v19`.

## Resultado y fuentes

Módulo Avannubo adaptado a **19.0.1.0.0**, instalado y actualizado en el Docker
aislado `miac_v19`. Conserva nombre técnico, autoría, licencia AGPL-3, icono,
XML IDs de vistas y los campos `days_to_activate` de producto y categoría.

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons`, instalación
`C:\Program Files\Odoo 19.0e.20260105` y repositorio. Sin consultas web ni descargas.

## Reglas acordadas e implementadas

- **Cada entrega completada** puede recalcular las fechas, incluidas entregas
  parciales, posteriores y de contratos ya facturados.
- Inicio = fecha prevista del albarán + máximo de días de activación de los
  productos efectivamente entregados de ese pedido. Los días son naturales.
- Próxima factura = inicio. Fin = inicio + `plan_id.billing_period`, sin restar
  un día; admite semanas, meses y años según el plan nativo.
- Se captura `scheduled_date` antes de completar el albarán. Su fecha se
  interpreta en la zona horaria del calendario de la compañía, con UTC como
  alternativa si no está configurada; no depende de la zona del usuario.
- El ajuste ocurre en `_action_done()`, después del flujo nativo. Abrir un
  asistente de entrega parcial o fallar una validación no activa el contrato.
- Solo albaranes de salida recién completados, con movimientos terminados,
  cantidad positiva, vínculo a línea de venta y destino cliente; se excluyen
  devoluciones, recepciones, traslados internos y movimientos cancelados.
- Se procesan suscripciones confirmadas, activas o pausadas y con plan;
  quedan fuera presupuestos, upsells y contratos cerrados o renovados.
- Inicio, próxima factura y fin se escriben juntos, respetando las validaciones
  nativas. Si una comprobación falla, la transacción de validación se revierte.
- En lotes se ordenan los albaranes por fecha prevista e ID. Para un mismo
  contrato prevalece el último de ese orden. Entre operaciones distintas se
  conserva la regla de recalcular en cada nueva entrega, aunque retroceda la fecha.
- El chatter identifica el albarán y las tres fechas anteriores/nuevas cuando
  cambian. Volver a procesar un albarán ya completado no reactiva el contrato.

**Contratos facturados:** se comprobó que las facturas contabilizadas mantienen
fecha contable, fecha de factura, estado, importes, cantidades y periodos de
diferimiento. La nueva próxima factura puede retroceder respecto del calendario
anterior; se conserva esa decisión explícita del usuario.

## Productos, categorías e integración

- Las categorías conservan tres días como valor predeterminado.
- Crear productos o cambiar su categoría hereda sus días, salvo un valor
  explícito en la misma operación. Se admite creación múltiple y un valor
  explícito de cero, también mediante contexto de creación.
- Cambiar los días de una categoría reemplaza los de todos sus productos
  accesibles, incluidos archivados y valores particulares, como se acordó.
  No hay propagación masiva al instalar o actualizar.
- No se usa `sudo()` ni se amplían permisos. La validación que actualiza el
  contrato requiere acceso de escritura sobre ese pedido, además del inventario.
- `subscription_plan_default` y la selección del plan pertenecen a la
  dependencia `subscription_date_lines`; se retiró la implementación duplicada.
- Los días aparecen junto al plan existente, una sola vez. Las dos variantes
  nativas de fecha de inicio se etiquetan «Fecha de activación», conservando
  sus grupos y condiciones de edición.
- Se corrigió `sale_suscription_start_date` en las referencias de la traducción española.
- La escritura de cabecera reutiliza la sincronización de fechas por línea:
  actualiza las automáticas y conserva las particulares.

Dependencias: `sale`, `sale_subscription`, `stock`, `sale_stock`,
`sale_subscription_stock` y `subscription_date_lines`. No se cambió código
ni versión de JH, `subscription_date_lines` o las dependencias estándar.

### Efecto nativo de la facturación física

El módulo no escribe cantidades facturables, no añade prorrateos y no
desactiva validaciones contables. Odoo 19 filtra las entregas físicas recurrentes
por el periodo del contrato. **Si la entrega ocurrió antes del nuevo inicio,
queda fuera de ese periodo facturable.**

Una prueba entrega una unidad el 30/01, con fecha prevista 30/01 y tres días
de activación: el contrato comienza el 02/02. El movimiento físico conserva
su unidad entregada, mientras la línea recurrente calcula nativamente cero
entregado y cero facturable para el nuevo periodo. Este resultado debe
considerarse en la aceptación funcional de contratos físicos de MIAC.

## Archivos principales

- `sale_subscription_start_date/__manifest__.py`: versión, descripción y dependencias.
- `models/product_category.py` y `product_template.py`: días y propagación por ORM.
- `models/stock_picking.py`: activación, ordenación y mensajes de auditoría.
- `models/sale_order.py`: conserva la extensión sin la selección duplicada de plan.
- Vistas de pedido/producto, traducción española y `tests/test_activation19.py`.
- `tools/validate_jh_odoo19.py`: inclusión del módulo en las comprobaciones estáticas.

## Validación

| Comprobación | Resultado |
| --- | --- |
| Instalación limpia con dependencias estándar | Correcta |
| Actualización y pruebas en `miac_activation19_clean` | 25 aprobadas, 0 fallos, 0 errores |
| Instalación integrada y pruebas en `miac_v19` | 35 aprobadas, 0 fallos, 0 errores; ninguna omitida |
| Actualización final de `sale_subscription_start_date` | Correcta, salida 0 |
| Revisión estática | 42 dependencias, 17 Python, 5 XML y 5 vistas compuestas correctos |
| `git diff --check` | Correcto |

Las 35 pruebas son **12 de activación, 13 de fechas por línea y 10 de JH**.
Cubren creación múltiple, valores explícitos y productos archivados; entrega
completa/parcial y asistente pendiente; máximo de productos entregados y
cancelados; periodos semanales/mensuales/anuales, fin de mes y zona de compañía;
lotes y varios pedidos; devoluciones/traslados/contratos cerrados/upsells;
facturas contabilizadas intactas; rollback ante un error nativo; fechas manuales;
cantidades nativas, vistas, planes y permisos. JH cubre además precios, lotes,
comisiones, renovaciones, informes y avisos.

Logs y respaldos en `C:\Proyectos FL\DAM\miac_v19`:

- `activation-clean-final.log`
- `activation-miac-tests.log`
- `activation-miac-update.log`
- `miac_v19-before-start-date-20261006.dump`
- `miac_v19-before-start-date-filestore-20261006.tar.gz`

### Repetir las pruebas

Desde la carpeta de Docker, deteniendo antes el servidor que utiliza la base:

```powershell
docker compose stop web
docker compose run --rm --no-deps web -u sale_subscription_start_date,subscription_date_lines,jh_sales_subscription --test-enable --test-tags subscription_activation19,subscription_dates19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/activation-repeat.log
docker compose up -d web
```

## Conservación y cierre

No hay hooks de conversión, cron nuevo, recomputación histórica al leer o
actualizar ni SQL correctivo. No se cambió la base del cliente, no se actualizó
el Excel de seguimiento y no se creó ningún commit.

El ensayo se deja iniciado en `http://localhost:8079`, sin ejecución de crons
(`max_cron_threads=0`), sin servidores de correo activos y SMTP a `127.0.0.1:1`.
Las pruebas son transaccionales y no conservan sus documentos de negocio.

Quedan pendientes el ensayo en una copia real de MIAC previamente migrada y
la aceptación funcional, especialmente las entregas físicas anteriores a la
activación y los recálculos de contratos ya facturados.

Commit recomendado: `[IMP] #xxxxxx Migra activación de suscripciones a Odoo 19`.
