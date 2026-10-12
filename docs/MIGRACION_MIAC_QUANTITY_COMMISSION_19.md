# Migración de miac_quantity_commission a Odoo 19

Fecha: 11 de octubre de 2026 (America/Bogota). Rama: `staging_v19`.

## Resultado

Implementado, instalado y actualizado en el Docker aislado `miac_v19`, versión **19.0.1.0.0**.
Siete pruebas propias aprobadas; seis pruebas OCA de liquidaciones aprobadas; JH pasa nueve de diez.
La regresión JH pendiente es la duplicidad conocida de filtros del análisis de facturas, ajena a este módulo.
La comprobación de históricos reales de MIAC sigue pendiente en una copia migrada separada.

## Implementación

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons\miac_quantity_commission`,
instalación local `C:\Program Files\Odoo 19.0e.20260105` y repositorio actual.
El módulo es personalizado de Avannubo; no se han realizado búsquedas ni descargas externas.

| Archivo | Adaptación |
|---|---|
| `miac_quantity_commission/__manifest__.py` | Versión 19.0.1.0.0, descripción técnica/funcional, dependencias `account`, `commission_oca`, `account_commission_oca`. Instalación manual. |
| `miac_quantity_commission/models/commission_settlement_line.py` | Conserva clase, modelo y `invoiced_quantity`: Float relacionado con `invoice_line_id.quantity`, almacenado, readonly y ayuda de dos líneas. Sin overrides ni cálculos nuevos. |
| `miac_quantity_commission/views/commission_settlement_line_view.xml` | Herencia `account_commission_oca.view_settlement_form`, XPath `list`, prioridad 50 y columna después de `invoice_line_id`. |
| `miac_quantity_commission/i18n/es.po` | Conserva «Cantidad Facturada» y actualiza ayuda y metadatos de traducción. |
| `miac_quantity_commission/tests/` | Siete pruebas funcionales, de composición, acceso y renderizado del informe OCA. |

Se conserva el XML ID `commission_settlement_invoiced_quantity_view_form_inherit`, autoría Avannubo,
licencia AGPL-3, nombre técnico e icono (hash idéntico al respaldo). No se incorporan archivos compilados.

La columna conserva su condición `parent.settlement_type != 'sale_invoice'` y el grupo
`account.group_account_invoice`. No se añaden permisos, dependencias de JH, columnas en otras vistas
ni herencias de informes. El PDF OCA 19 ya muestra la cantidad de la factura.

## Semántica y precisión

- La cantidad es la del documento de origen, sin invertir signos en rectificativas.
- Se hereda la precisión nativa de `account.move.line.quantity` mediante el campo relacionado.
- En el ensayo, «Unidad de producto» tiene dos decimales: una entrada 2.375 se conserva como 2.38
  en la factura y la columna muestra ese mismo valor. No se introduce una precisión diferente.
- Sin origen, la cantidad es cero. Cada agente recibe la cantidad completa de la misma línea;
  no se reparte ni se suma en una cantidad comercial distinta.
- Cambios de cantidad y vínculo siguen el related almacenado. No se crea una copia histórica independiente.
- Se respetan las restricciones OCA de líneas liquidadas. La prueba de cambio de cantidad cancela primero
  la liquidación mediante el método nativo; no desactiva validaciones.

## Validación ejecutada

| Comprobación | Resultado |
|---|---|
| Instalación y actualización | Correctas; estado `installed`, versión 19.0.1.0.0. |
| `miac_quantity19` | **7/7**, cero fallos y errores en ejecución final. |
| OCA `TestAccountCommission` | **6/6** seleccionadas: liquidaciones negativas, negativas agrupadas en factura, factura única, múltiples facturas, liquidación única y borrado de factura de liquidación. |
| `jh_migration19` | **9/10**; solo falla la unicidad de filtros de precio del análisis de facturas. |
| Cantidades | Enteras, decimales, cero, negativas, actualización de origen y ausencia de origen. Se verifica persistencia después de vaciar caché. |
| Rectificativas y varios agentes | Cantidades originales conservadas; comisiones e importes sin cambios. |
| Vista y permisos | Columna única, posición posterior al origen, prioridad 50 y traducción española. Usuario de comisiones sin grupo de facturación no recibe la columna en su formulario. |
| HTML/PDF | Una única columna de cantidad OCA; se comparan valores y totales antes/después del renderizado. PDF de una página generado y revisado visualmente. |
| Pantalla | Factura con cantidades 3.00 y 2.38: comisiones 30.00 y 23.80; rectificativa con las mismas cantidades y comisiones -30.00 y -23.80. |
| Contenedor | Iniciado y saludable; cero crons y cero servidores de correo activos. |

La validación estática compuso una vista en un grafo de 20 módulos: Python, XML, dependencias y XML IDs correctos.
El verificador existente de archivos OCA detectó cambios de finales de línea LF/CRLF en 97 archivos.
Se comprobó que **todos** coinciden con sus hashes fijados al normalizar CRLF a LF; no hay diferencias
de contenido. La validación completa se ejecutó normalizando únicamente en memoria, sin editar el
verificador, los módulos OCA ni su lock.

### Pendientes ajenos a la adaptación

La prueba `TestJhMigration19.test_legacy_price_filters_use_native_invoice_analysis` encuentra dos filtros
`without_price` y dos `with_price`: JH y `account_invoice_line_report` los añaden sobre la misma vista.
Este módulo no hereda el análisis de facturas. No se han cambiado esos módulos ni se ha omitido la prueba.

En el PDF existente de liquidaciones, las columnas adicionales JH producen una tabla muy ancha y la
columna final queda ajustada al borde derecho. La cantidad OCA es visible, aparece una sola vez y sus
valores coinciden. El ajuste de anchura del informe queda para un trabajo independiente, porque el
alcance aprobado exige conservar el PDF y no modificar otros módulos.

## Evidencias y estado del ensayo

Respaldos previos:

- `C:\Proyectos FL\DAM\miac_v19\quantity-commission19-before-20261011.dump`.
- `C:\Proyectos FL\DAM\miac_v19\quantity-commission19-filestore-before-20261011.tar.gz`.

Logs:

- `quantity-commission19-install-20261011.log`: instalación y primeras pruebas; registra ajustes de fixtures.
- `quantity-commission19-final-20261011.log`: pruebas OCA y JH; también registra un assert propio posteriormente corregido.
- **`quantity-commission19-acceptance-final-20261011.log`**: resultado definitivo de las siete pruebas propias, todas aprobadas.

Todos están en `C:\Proyectos FL\DAM\miac_v19`.
HTML, PDF y capturas están en `C:\Proyectos FL\DAM\miac_v19\quantity-commission19-validation`.

Los documentos ficticios usados en pantalla son liquidaciones 103/104 y factura/rectificativa 883/884,
con nombres y referencias `PRUEBA MIAC`. Tras verificar la pantalla, se cancelaron **solo estos documentos**
mediante métodos nativos para no dejarlos pendientes de facturación o selección por futuras pruebas.
Se conservaron sus registros y cantidades; las capturas documentan el estado anterior a esa cancelación.
Las pruebas automáticas revierten sus propios datos mediante el framework nativo.

## Conservación y entrega

Se conserva el mismo campo/columna `commission_settlement_line.invoiced_quantity` para la continuidad
de datos. No se han ejecutado conversiones, SQL correctivo, scripts de relleno ni recálculos propios sobre
la base del cliente. La instalación del related almacenado usa el mecanismo ORM normal en el ensayo.

Antes de actualizar la copia real de MIAC, deberá estar resuelta la correspondencia de módulos OCA
antiguos con los nuevos. No se debe desinstalar este módulo para trasladar sus datos.

Quedan pendientes el ensayo con históricos reales y la incidencia de filtros JH/OCA para cerrar la
aceptación conjunta. No se ha modificado el Excel, creado commits ni corregido otros módulos.

Commit recomendado: `[IMP] #xxxxxx Migra cantidad facturada en comisiones a Odoo 19`.
