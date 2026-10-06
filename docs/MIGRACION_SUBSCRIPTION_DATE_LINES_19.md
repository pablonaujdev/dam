# subscription_date_lines — migración a Odoo 19

Fecha: 2026-10-06. Rama: `staging_v19`.

## Resultado y versiones

Implementado y validado en instalaciones aisladas, sin datos del cliente.

| Módulo | Versión | Cambio |
| --- | --- | --- |
| subscription_date_lines | 19.0.1.0.0 | Migración del código Avannubo, fechas individuales y plan del producto |
| miac_line_subscription | 19.0.1.0.1 | Dependencia explícita y columnas originales de fechas individuales |
| miac_renovation_subscription | 19.0.1.0.1 | Corrección de referencia de origen para productos/precios iguales con lotes distintos |
| jh_sales_subscription | 19.0.1.0.1 | Código y versión conservados; diez regresiones ejecutadas |

Fuentes: respaldo local `C:\Proyectos FL\DAM\respaldo\addons`, instalación
`C:\Program Files\Odoo 19.0e.20260105` y módulos del repositorio. Sin consultas
web ni descargas externas.

## Comportamiento

- Se conservan nombres técnicos, autoría Avannubo, licencia AGPL-3, XML IDs y
  campos `date_subs_start`, `date_subs_end`, `subscription_plan_default` y
  `partial_invoice`. El icono original se conserva.
- Fechas independientes, almacenadas y editables; no se convierten en campos
  relacionados con la cabecera. No se rellenan al leer, imprimir o actualizar
  el módulo.
- Creación múltiple: las líneas recurrentes reciben fechas del contrato cuando
  no se indican expresamente. Un `False` explícito se respeta.
- Cambios de cabecera: por cada fecha se actualizan solo líneas vacías o cuyo
  valor anterior coincide con la cabecera anterior. Las fechas particulares
  diferentes se conservan. Los valores explícitos de comandos de línea tienen
  prioridad en la misma operación.
- Al cambiar producto/pedido, se completan fechas vacías de líneas recurrentes
  y se conservan las particulares. No se limpian datos al pasar a no recurrente.
- Renovaciones, upsells y duplicaciones inicializan las fechas del nuevo pedido
  mediante `copy=False`, sin copiar intervalos particulares del contrato anterior.
- Plan predeterminado: solo para productos recurrentes, sin sustituir un plan
  existente ni el de una plantilla. Un único plan se propone; varios generan
  aviso en pantalla y requieren elección manual antes de confirmar una
  suscripción. La validación de confirmación sigue siendo la nativa.
- La eliminación explícita de plan se respeta en esa operación. Si todos los
  productos permiten venta única y el pedido no es una suscripción, no se fuerza
  un plan. Una edición posterior de productos puede proponerlo de nuevo si el
  pedido vuelve a necesitar suscripción y sigue sin plan.
- `partial_invoice` conserva el valor histórico, sin bloquear
  `next_invoice_date` ni escribir `qty_to_invoice`.
- Fechas individuales destinadas al seguimiento: no filtran líneas facturables
  ni modifican cantidades, prorrateos, precios, descuentos o periodos nativos.
- Tres referencias transitorias no almacenadas permiten cambios sucesivos de
  cabecera y distinguen el plan sugerido durante la edición. No añaden columnas
  a `sale_order` ni requieren conversiones de datos.
- La lista MIAC de licencias vuelve a mostrar `date_subs_start` y
  `date_subs_end`. Los campos relacionados de cabecera anteriores permanecen.

## Corrección detectada durante la integración

La nueva prueba con dos líneas del mismo producto **y precio**, pero lotes
distintos, detectó que el cálculo nativo de `parent_line_id` podía intercambiar
las referencias de origen. El emparejamiento nativo utiliza producto, unidad,
moneda, plan y precio; no distingue lotes.

La corrección se ubica en `miac_renovation_subscription`, que ya depende de
`sale_subscription` y `sale_purchase_lot`. Después del cálculo nativo, si la
referencia encontrada pertenece a otro lote, busca una coincidencia única con
el lote correcto y las mismas claves nativas. Si es ambigua, deja la referencia
vacía en lugar de asignar otra licencia. No añade una lógica de precios ni
modifica el código de JH. La corrección se aplica también al recalcular lotes.

## Validación realizada

| Entorno / comprobación | Resultado |
| --- | --- |
| Fuentes locales: Python, XML, dependencias y XPath del nuevo módulo | Correcto; 35 módulos en el grafo |
| Fuentes locales: integración con JH y dependencias | Correcto; 54 módulos, 61 archivos Python, 36 XML, 47 vistas compuestas |
| Base independiente `miac_dates19_clean`: instalación y actualización | Correcto; módulo instalado en 19.0.1.0.0 |
| Suite del módulo en la base independiente | 13 pruebas, 0 fallos, 0 errores |
| Base `miac_v19`: instalación e integración, seguida de actualización | Correcto |
| Suite integrada del módulo y regresiones JH | 23 pruebas: 13 + 10; 0 fallos, 0 errores |
| Datos de prueba persistentes en miac_v19 | 0 pedidos, 0 facturas; pruebas revertidas |
| Referencias transitorias en la tabla sale_order | Sin columnas date_subs_* |
| Acceso tras iniciar el servicio | Autenticación correcta; /odoo HTTP 200, 0,802 s |
| Contenedores | miac_v19 y miac_v19_db saludables |

Casos cubiertos: creación múltiple, fechas omitidas/expresas/vacías, líneas no
recurrentes, cambios por lotes de contratos, comandos de cabecera y líneas
simultáneos, productos y pedidos cambiados, formularios con cambios sucesivos,
planes únicos/conflictivos/manuales/plantillas, ventas únicas, renovación,
upsell, copia, productos repetidos con lotes diferentes y cantidades/periodos
nativos independientes de las fechas particulares.

Las diez regresiones JH incluyen precios negociados y ceros explícitos,
renovación con condiciones/tarifa, rechazo de duplicados confirmados,
comisiones, estado de facturación, crons/avisos, informes/exportaciones,
histórico/adjuntos y filtros de precios.

Los logs finales no presentan errores de instalación ni de pruebas. Existen
advertencias previas del proyecto sobre botones con icono sin título y etiquetas
duplicadas; no bloquean esta migración.

## Evidencia y repetición

Archivos locales en `C:\Proyectos FL\DAM\miac_v19`:

- `subscription-dates-clean-update.log`: 13 pruebas correctas.
- `subscription-dates-miac-final.log`: actualización y 23 pruebas correctas.
- `miac_v19-before-subscription-dates-20261006.dump`: respaldo previo del ensayo.
- `miac_v19-before-subscription-dates-filestore-20261006.tar.gz`: filestore previo.

Los logs iniciales conservan el diagnóstico: incompatibilidad del helper de
pruebas con una tupla de excepciones y el caso de origen/lote corregido después.

Validación estática desde el repositorio:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py --module subscription_date_lines
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py --module jh_sales_subscription
```

Repetición autorizada en el Docker aislado, desde su carpeta de configuración:

```powershell
docker compose stop web
docker compose run --rm --no-deps web -u subscription_date_lines,miac_renovation_subscription,miac_line_subscription,jh_sales_subscription --test-enable --test-tags subscription_dates19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0
docker compose up -d web
```

Correo bloqueado a `127.0.0.1:1`; `max_cron_threads=0`. El ensayo utiliza la
copia local de Odoo 19 Enterprise y el repositorio de addons montado en lectura.

## Pendiente antes de aceptar datos reales

- Ensayo separado sobre una copia de MIAC previamente migrada a 19: comparar
  fechas, planes, relaciones de origen, lotes y el indicador histórico con V17.
- Aceptación funcional del usuario. La validación limpia no acredita la
  conservación de los registros de producción.
- Migraciones independientes de `avannubo_prorrate_invoice`,
  `partner_list_sale_line` y `purchase_subscription`, que consumen estos campos.
- Al migrar `sale_subscription_start_date`, reutilizar el campo y la selección
  de plan de este módulo mediante dependencia; retirar la implementación
  duplicada conservando datos e identificadores.

No se ejecutaron conversiones sobre el cliente, SQL correctivo ni
desinstalaciones. No se modificó el Excel ni se creó un commit.
