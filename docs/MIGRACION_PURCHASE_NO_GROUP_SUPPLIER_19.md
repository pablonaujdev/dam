# Compras separadas por pedido de venta en Odoo 19

Fecha: 2026-10-11. Rama: `staging_v19`.
Módulo Avannubo: `purchase_no_group_supplier`, versión `19.0.1.0.0`.

## Implementación y conservación

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons`,
instalación local `C:\Program Files\Odoo 19.0e.20260105` y repositorio.
Se aplicó `development-conventions` antes de editar.

- Incorporado el módulo sin `__pycache__`, `.pyc` ni `.pyo`.
- Conservados autoría Avannubo, AGPL-3, nombre técnico, icono, traducción
  española, XML ID `view_res_partner_no_group_purchase_form_inherit`
  y campo `res.partner.no_group_purchase`, con `default=True`.
- Manifest versionado una sola vez como `19.0.1.0.0`, con descripción
  técnica/funcional y dependencias directas `sale_purchase`, `purchase_stock`
  y `sale_purchase_stock`. Instalación manual.
- Casilla conservada en Compras del contacto, con ayuda de dos líneas y
  traducción española. No se añadieron modelos, campos de seguimiento,
  ACL, menús, crons ni scripts de transformación de datos.

Archivos adaptados: manifest, `models/res_partner.py`,
`models/sale_order_line.py`, `models/stock_rule.py` e `i18n/es.po`.
Añadidos `models/purchase_order_domain.py` y pruebas en `tests/`.
Vista y recursos originales incorporados conservando sus identificadores.

## Reglas funcionales

| Situación | Comportamiento |
|---|---|
| Casilla marcada y compra procedente de venta | Ventas distintas no comparten compra; líneas de una venta pueden compartir un borrador compatible. |
| Casilla desmarcada | Flujo nativo de Odoo 19, que ya separa servicios por venta en su generación habitual. |
| Reposición sin venta | Agrupación nativa, independientemente de la casilla. |
| Referencias con varias ventas sin línea de origen | Error explicativo antes de crear compras del lote. |
| Borrador vinculado a varias ventas | No se reutiliza cuando la casilla está marcada; se conserva sin reorganizarlo. |

**Cambio acordado respecto a V17:** la casilla deja de impedir la reutilización
de compras en reposiciones sin venta asociada. Estas recuperan el flujo nativo.

### Inventario

`_make_po_get_domain()` conserva `super()` y sustituye `group_id.sale_id`
por `sale_line_id.order_id` y, en su ausencia, `reference_ids.sale_ids`.
Una línea de venta determina el pedido antes que las referencias.

Cada venta aporta su ID al dominio, incluso si todavía no existe una compra.
Se elimina el antiguo `id = 0`, que producía una clave común para ventas distintas
en el agrupamiento del lote. El dominio utiliza tuplas, incluidas sus condiciones
relacionales anidadas, para ser utilizable como clave de `_run_buy()`.

La selección considera referencias de stock y líneas de servicio/dropshipping;
no depende exclusivamente de `purchase.order.line.sale_line_id`, que puede estar
vacío en MTO. Excluye compras que contengan vínculos con otras ventas.
Se mantienen proveedor, compañía, moneda, comprador, operación, estado borrador
y las condiciones nativas por fechas. No se reemplaza `_run_buy()`.

### Servicios

Se retira el override de `_purchase_service_match_purchase_order()`, porque
Odoo 19 ya filtra por pedido de venta. Se amplía su hook de dominio para excluir
compras mezcladas, únicamente para proveedores con la casilla marcada.

Las llamadas múltiples de `_purchase_service_create()` se separan por compañía
y venta para líneas marcadas, delegando cada grupo a `super()` y conservando
el diccionario nativo de líneas. Las no marcadas usan el procesamiento nativo.
No se reemplazan cantidades, precios, impuestos ni vínculos de lotes.

## Validación en `miac_v19`

- Respaldo previo de PostgreSQL y filestore.
- Instalación y actualización correctas, versión instalada `19.0.1.0.0`.
- **36 pruebas aprobadas, cero fallos y cero errores:** 17 propias,
  9 nativas de `sale_purchase:TestSalePurchase` y 10 regresiones de JH.
- Servicios en lote: separación de ventas y compañías, agrupación de líneas
  de una venta, precio/cantidad, aumentos y cancelación/reconfirmación.
- Reutilización de borradores y rechazo de compras enviadas, confirmadas,
  canceladas o previamente mezcladas.
- Aprovisionamientos de varias ventas en una llamada, sin compras anteriores,
  con los cuatro modos nativos de agrupación; conservación de precio y cantidades.
- Agrupación diaria: una venta con fechas previstas distintas mantiene compras
  distintas, respetando la restricción nativa.
- Reposición sin venta y casilla desmarcada: agrupación nativa conservada.
- Referencias ambiguas: el lote no crea compras antes del error.
- Confirmación MTO real y aumento posterior: reutilización por referencias
  aunque las líneas de compra no tengan `sale_line_id`.
- Dropshipping real: ventas separadas, productos repetidos, líneas y lotes distintos
  conservados mediante `sale_purchase_lot`.
- Filtros por moneda, operación y compañía y generación de servicios multicompañía.
- Formulario revisado en navegador: casilla en Compras, traducción española,
  valor predeterminado marcado y edición correcta. Contacto de prueba descartado.
- Consola del navegador sin errores ni advertencias durante la revisión.
- No hay cambios de permisos ni uso adicional de `sudo()` en el módulo.
- Validador estático: grafo de 32 módulos, 9 Python, 1 XML y 1 vista compuesta.
- `git diff --check` correcto; Docker iniciado y saludable, crons desactivados
  y correo bloqueado.

Para probar dropshipping se instaló su módulo estándar `stock_dropshipping`
exclusivamente en el ensayo. No es una dependencia obligatoria del módulo migrado.

Odoo nativo toma las referencias de la primera necesidad cuando crea una compra
para varias necesidades agrupadas en un mismo lote. En la prueba de casilla
desmarcada se comprobó también la incorporación de referencias al reutilizar
la compra en una ejecución posterior. No se modificó ese comportamiento nativo.

Comando final desde `C:\Proyectos FL\DAM\miac_v19`, con web detenido:

```powershell
docker compose run --rm --no-deps web -u purchase_no_group_supplier,sale_purchase,jh_sales_subscription --test-enable --test-tags no_group_purchase19,/sale_purchase:TestSalePurchase,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/no-group-purchase19-acceptance-20261011.log
docker compose up -d web
```

Respaldo y evidencias en esa carpeta:

- `no-group-purchase19-before-20261011.dump`.
- `no-group-purchase19-before-20261011-filestore.tar.gz`.
- `no-group-purchase19-acceptance-20261011.log`: aceptación final.
- `no-group-purchase19-final-tests-20261011.log`: suite anterior de 35 pruebas aprobadas.
- `no-group-purchase19-ui-20261011.jpg`: casilla en el contacto nativo.
- Los registros iniciales de instalación/actualización conservan los problemas
  de preparación de pruebas corregidos antes de la aceptación.

## Pendientes y límites

Queda pendiente validar valores y compras reales de MIAC en una copia migrada.
No se han reorganizado compras históricas, realizado conversiones sobre el cliente,
modificado el Excel ni creado commits. No hay hooks de relleno o recálculo masivo;
la definición existente del campo se conserva para mantener sus valores al migrar.
Las advertencias de accesibilidad y etiquetas de otros módulos en el registro del
servidor no son errores de estas pruebas y quedan fuera de esta adaptación.
