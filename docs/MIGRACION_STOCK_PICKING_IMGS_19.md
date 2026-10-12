# Migración de stock_picking_imgs a Odoo 19

Fecha: 11 de octubre de 2026 (America/Bogota). Rama: `staging_v19`.

## Resultado y alcance

Implementado e instalado en el ensayo aislado `miac_v19`, versión `19.0.1.0.0`.
Las 12 pruebas propias y las 13 de informes MIAC pasan. JH pasa 9 de 10;
la aceptación conjunta queda pendiente del conflicto de filtros descrito abajo.
La validación con productos y datos reales de MIAC sigue pendiente en una copia migrada separada.

Fuentes utilizadas exclusivamente:

- Original: `C:\Proyectos FL\DAM\respaldo\addons\stock_picking_imgs`.
- Odoo 19: `C:\Program Files\Odoo 19.0e.20260105\server\odoo\addons`.
- Repositorio actual e informes MIAC ya migrados.

No se han realizado búsquedas externas ni descargas. Es una personalización de Avannubo.

## Código incorporado

| Archivos | Cambio |
|---|---|
| `stock_picking_imgs/__manifest__.py` | Versión inicial 19, descripción funcional/técnica; dependencias `sale`, `stock`; instalación manual. |
| `stock_picking_imgs/models/{sale_order_line,stock_move,stock_move_line}.py` | Conserva `image`, relacionado con `product_id.image_128`, readonly, sin almacenamiento y `compute_sudo=False`. Ayuda de dos líneas y dependencias explícitas de imagen de plantilla/variante para invalidar la caché. |
| `stock_picking_imgs/views/sale_order_view.xml` | Miniatura 48 × 48 antes del producto en la lista de líneas de venta. |
| `stock_picking_imgs/views/stock_picking_view.xml` | Lista nativa `move_ids`; miniatura antes del producto. |
| `stock_picking_imgs/views/sale_order_report.xml` | Columna de imagen en productos y combinaciones; columna vacía en resúmenes; ajuste dinámico de colspan de secciones. Prioridad 180, posterior a MIAC (160). |
| `stock_picking_imgs/views/stock_picking_report.xml` | Herencia limitada expresamente a `stock_move_table`, la tabla principal de pendientes. |
| `stock_picking_imgs/i18n/es.po` | Traducción española de etiquetas, ayuda e imágenes de producto. |
| `stock_picking_imgs/tests/` | 12 pruebas funcionales y de composición/renderizado HTML/PDF. |

Se mantienen nombre técnico, clases existentes, XML IDs, autoría, licencia AGPL-3 e icono.
No se modifica `miac_custom_reports` ni se declara como dependencia.
No se han incorporado archivos compilados, campos persistentes, permisos, acciones, adjuntos ni copias históricas.

La fotografía sigue al producto actual. Los informes antiguos también muestran su imagen actual
cuando se vuelven a imprimir. Los productos sin fotografía dejan vacía la celda impresa;
en pantalla el widget nativo puede mostrar su marcador de imagen ausente.

En impresión ambos ejes se limitan a 80 puntos y se conserva la proporción.
No hay imágenes en tablas de realizados, lotes/series, paquetes ni cantidades restantes.
El propio albarán pendiente generado como entrega parcial sí tiene imágenes en su tabla principal.

## Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| AST, manifests, dependencias, XML y composición estática de vistas | Correcta: grafo de 26 módulos, 4 vistas personalizadas compuestas. |
| Instalación `-i stock_picking_imgs` | Correcta; registro y cuatro vistas cargados. |
| Actualización `-u stock_picking_imgs` | Correcta; versión instalada `19.0.1.0.0`. |
| `picking_images19` | 12/12, cero fallos y errores en ejecución final. |
| `miac_reports19` | 13/13 en ejecución conjunta. |
| `jh_migration19` | 9/10; falla exclusivamente la unicidad de filtros de precio. |
| Ejecución conjunta | 34/35; un fallo y cero errores. Las cifras de `odoo.tests.stats` incluyen setup/teardown; los recuentos anteriores corresponden a métodos de prueba. |
| Pantallas de venta e Inventario | Columna Imagen antes de Producto, etiqueta española; imágenes cargadas con límites 48 × 48. |
| HTML/PDF | Presupuesto, proforma, pedido, anticipos, combinaciones, secciones/subsecciones, resumen agrupado, productos repetidos con lotes distintos, documentos de varias páginas, recepciones/entregas pendientes, realizado con paquete y entrega parcial. |
| Importes y cantidades | Conservados en los casos de prueba; se verifican base, impuestos y total. |
| Acceso | Vendedor autorizado puede leer la imagen; lectura de líneas de otra compañía denegada; no se elevan los cálculos relacionados. |
| Contenedor | `miac_v19`: iniciado y saludable; PostgreSQL saludable. |
| Correo y tareas | Cero servidores de correo activos y cero crons activos; configuración SMTP de ensayo bloqueada. |

Las pruebas propias verifican cambios de foto y de producto, variante con fotografía particular,
producto sin foto, dimensiones reales de imágenes horizontales/verticales, productos combinados,
resúmenes sin fotografía arbitraria, alineación de columnas, lotes, finalización y entregas parciales.
Se revisaron visualmente páginas renderizadas de los PDF, incluida la venta de tres páginas.
Los informes de factura y rectificativa se ejecutaron dentro de las regresiones MIAC.

### Incidencia ajena al módulo: filtros duplicados en JH/OCA

Prueba: `TestJhMigration19.test_legacy_price_filters_use_native_invoice_analysis`.
Obtiene dos filtros `without_price` y dos `with_price`, cuando espera uno de cada uno.

Las dos herencias existentes que los insertan son:

- `jh_sales_subscription/views/actions_jh_account_invoice_report.xml`,
  XML ID `custom_account_invoice_report_search_inherit`.
- `account_invoice_line_report/report/account_invoice_report_view.xml`,
  XML ID `view_account_invoice_report_search`.

Ambas heredan `account.view_account_invoice_report_search` y utilizan los mismos nombres y dominios.
Ninguna vista de `stock_picking_imgs` hereda ese análisis de facturas.
La instalación reciente del módulo OCA ha expuesto esta duplicidad; no es causada por las imágenes.
Recomendación: unificar los filtros en la integración JH/OCA con una adaptación separada y su versionado,
conservando los filtros geográficos y fiscales de JH. No se han cambiado estos módulos ni sus pruebas
para ocultar el fallo. Hasta resolverlo no se declara aprobada la aceptación completa solicitada.

## Evidencias y reproducción

Respaldos previos, fuera del repositorio:

- `C:\Proyectos FL\DAM\miac_v19\picking-imgs19-before-20261011.dump`.
- `C:\Proyectos FL\DAM\miac_v19\picking-imgs19-filestore-before-20261011.tar.gz`.

Logs finales:

- `C:\Proyectos FL\DAM\miac_v19\picking-imgs19-acceptance-20261011.log`: 12 propias sin fallos.
- `C:\Proyectos FL\DAM\miac_v19\picking-imgs19-integration-final-20261011.log`: 35 conjuntas, incidencia JH.

Los logs iniciales documentan ajustes durante la implementación y no constituyen el resultado final.
PDF, HTML y páginas PNG: `C:\Proyectos FL\DAM\miac_v19\picking-images19-validation`.
Capturas: `sale-ui.png`, `picking-ui.png` en esa misma carpeta.

Ejemplo de verificación estática desde el repositorio:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py --module stock_picking_imgs
```

Para repetir pruebas, detener el servicio web del ensayo y ejecutar una instancia de prueba:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' stop web
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' run --rm -T web -d miac_v19 -u stock_picking_imgs,miac_custom_reports,jh_sales_subscription --test-enable --test-tags picking_images19,miac_reports19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' start web
```

Se conservaron únicamente documentos identificados como prueba para revisión de pantalla:
presupuesto `S01156` (ID 1217), recepción `WH/IN/00004` (ID 423) y productos 1766–1768.
Las transacciones de las pruebas automáticas se revierten por el framework nativo.

## Límites y pendientes

- Pendiente la corrección separada de los filtros duplicados y repetir las 10 regresiones de JH.
- Pendiente aceptación funcional con fotografías, compañías y documentos reales en una copia de MIAC.
- No se han convertido ni actualizado datos del cliente; no se han reorganizado históricos.
- No se ha modificado el Excel ni se han creado commits.
- El ensayo se deja iniciado; correo y automatizaciones permanecen desactivados.

Commit recomendado: `[IMP] #xxxxxx Migra imágenes de ventas y albaranes a Odoo 19`.
