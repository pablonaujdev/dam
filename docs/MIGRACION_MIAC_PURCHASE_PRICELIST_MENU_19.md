# Migración de miac_purchase_pricelist_menu a Odoo 19

Fecha: 11 de octubre de 2026 (America/Bogota). Rama: `staging_v19`.

## Resultado

Módulo Avannubo incorporado, instalado y actualizado como **19.0.1.0.0** en el Docker aislado
`miac_v19`. Se conservan Compras → Productos → Tarifas de Proveedor y la lista MIAC de V17.
Seis pruebas propias aprobadas. La validación con tarifas y preferencias reales de MIAC sigue
pendiente en una copia migrada separada.

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons\miac_purchase_pricelist_menu`,
instalación local de Odoo 19 y repositorio actual. Sin búsquedas ni descargas externas.

## Código y continuidad

| Archivo | Cambio |
|---|---|
| `miac_purchase_pricelist_menu/__manifest__.py` | Versión inicial 19, descripción funcional/técnica, dependencia única de `purchase`, instalación manual. |
| `miac_purchase_pricelist_menu/views/product_supplierinfo_view.xml` | Arquitectura `list`, acción `list,form`, vínculos explícitos con secuencias 1 y 2; contexto nativo para mostrar la plantilla en el formulario. |
| `miac_purchase_pricelist_menu/i18n/es.po` | Metadatos de Odoo 19; traducción «Tarifas de Proveedor» conservada. |
| `miac_purchase_pricelist_menu/tests/` | Seis pruebas de estructura, formulario, tarifas, unidades, monedas, fechas y permisos. |

Se conservan autoría Avannubo, AGPL-3, icono y los XML IDs:

- `miac_view_product_supplierinfo_view_tree`.
- `product_supplierinfo_action`.
- `menu_product_supplierinfo_s`.

El nombre interno de la vista también se conserva, aunque contenga `tree`.
El menú permanece bajo `purchase.menu_purchase_products`, secuencia 40.
No se añaden modelos, campos, permisos, automatizaciones ni cálculos.
No hay edición en línea ni masiva; la creación y edición usan el formulario nativo.
Se excluyeron archivos compilados del respaldo.

## Columnas y comportamiento acordado

La lista conserva este orden y sus opcionales originales:

1. Proveedor.
2. Plantilla de producto.
3. Variante de producto (opcional, visible).
4. Precio.
5. Moneda.
6. Plazo de entrega (opcional, visible).
7. Nombre de producto del proveedor (opcional, oculto).
8. Código de producto del proveedor (opcional, oculto).
9. Inicio de vigencia (opcional, oculto).
10. Fin de vigencia (opcional, oculto).
11. Cantidad mínima (opcional, oculto).
12. Descuento (opcional, oculto).

No se añadieron columnas de unidad ni compañía, según la decisión del usuario.
La consulta de esos datos en el formulario depende de la configuración y grupos nativos;
no se activaron funcionalidades ni se ampliaron permisos para hacerlos visibles.

Contexto de acción: `{'visible_product_tmpl_id': False}`. En Odoo 19 ese valor hace visible
la plantilla del producto en el formulario independiente. No es un filtro sobre registros.
No se añaden dominio ni filtros predeterminados de vigencia o productos activos.
La búsqueda y agrupaciones son nativas. Se mantiene el acceso estándar de Configuración.

## Validación

| Comprobación | Resultado |
|---|---|
| Instalación y actualización | Correctas; estado `installed`, versión 19.0.1.0.0. |
| Validación estática | AST/XML/PO, dependencias y composición de una vista correctos; grafo de 19 módulos. |
| `miac_pricelist_menu19` | **6/6**, cero fallos y errores en la ejecución final. |
| Vista y acción | Las 12 columnas y sus opcionales coinciden con V17; lista MIAC primero, formulario nativo después. |
| Variantes | Tarifa de plantilla aplicable a ambas variantes; tarifa específica seleccionada para su variante y cantidad mínima. |
| Precio de compra | Mediante el formulario nativo de compra se verifica precio 80, descuento 10% y precio descontado 72; consultar el acceso no los modifica. |
| Unidades y monedas | Precio por docena y descuento normalizados por Odoo; segunda moneda con tipo de cambio de prueba, sin alterar selección ni conversiones. |
| Fechas | Tarifas vencidas, futuras y actuales visibles en el acceso; selección del vendedor respeta la vigencia nativa. Productos archivados no quedan ocultos por un filtro predeterminado del módulo. |
| Permisos | Responsable de Compras puede crear/editar; usuario de Compras de consulta puede leer pero no crear, escribir ni borrar. |
| Compañías | Tarifas compartidas y de la compañía del usuario accesibles; las de otra compañía quedan excluidas. |
| Pantalla | Acceso en Productos, columnas opcionales originales y agrupación por proveedor comprobados. Tarifa creada y editada desde el formulario, con producto visible y seleccionable. |
| Estado final | `miac_v19` iniciado y saludable; correo y crons desactivados. |

### Comparación antes y después

Antes de instalar se crearon tres tarifas ficticias (IDs 93–95), una plantilla con dos variantes
y el pedido de prueba 484. Tras instalar se verificó igualdad de:

- Precio, descuento, mínimo, moneda, unidad, compañía y vigencia de las tres tarifas.
- Proveedor/tarifa seleccionada para cinco unidades: registro 94.
- Precio, descuento e importe del pedido existente: 100, 0 y 575 respectivamente, conservados.

Estos valores son el resultado nativo capturado antes de instalar, no una nueva regla del módulo.
El caso de formulario de compra de las pruebas automáticas verifica por separado la aplicación
de la tarifa específica de 80 con descuento 10%. No se fuerza el recálculo de pedidos existentes.

## Evidencias

Carpeta: `C:\Proyectos FL\DAM\miac_v19`.

- Respaldos: `pricelist-menu19-before-20261011.dump` y `pricelist-menu19-filestore-before-20261011.tar.gz`.
- Resultado final: **`pricelist-menu19-final-20261011.log`**.
- Comparación: `pricelist-menu19-before.json` y `pricelist-menu19-after.json`, idénticos.
- Capturas en `pricelist-menu19-validation`: lista, columnas opcionales y formulario.
- Tarifa ficticia creada/editada desde el navegador: ID 115, código `PRUEBA-UI-19-EDIT`,
  precio 95, descuento 5%, cantidad mínima 2. No se modificaron tarifas reales.

Los logs iniciales registran ajustes de fixtures durante la implementación y no son el resultado final.
Las pruebas automáticas revierten sus datos mediante el framework nativo.
Los registros identificados como `PRUEBA MIAC` se conservan para revisión local.

## Límites de entrega

No se ha modificado el Excel ni creado commits. No se han corregido otros módulos, cambiado
permisos de usuarios reales ni ejecutado conversiones sobre la base del cliente.
Los módulos descargados que aparecieron durante el trabajo se dejaron intactos.

Para la copia migrada de MIAC se deben conservar nombre técnico y XML IDs; no desinstalar el
módulo ni reemplazar la acción por una nueva durante la transición. Tarifas, compañías, permisos
efectivos y preferencias reales se validarán posteriormente en esa copia.

Commit recomendado: `[IMP] #xxxxxx Migra menú de tarifas de proveedor a Odoo 19`.
