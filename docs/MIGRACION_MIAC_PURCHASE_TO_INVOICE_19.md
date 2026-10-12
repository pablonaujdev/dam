# Migración de miac_purchase_to_invoice a Odoo 19

Fecha: 11 de octubre de 2026 (America/Bogota). Rama: `staging_v19`.

## Resultado

Módulo Avannubo incorporado, instalado y actualizado en `miac_v19`, versión **19.0.1.0.0**.
Se mantienen el menú «Pedidos a Facturar» y su dominio obligatorio. Las seis pruebas propias pasan.
No se modifica el flujo de facturación ni se añaden campos, modelos, permisos o automatizaciones.

Fuentes exclusivas: respaldo `C:\Proyectos FL\DAM\respaldo\addons\miac_purchase_to_invoice`,
Odoo 19 local y repositorio. No se utilizaron búsquedas ni descargas externas.

## Archivos y conservación

| Archivo | Cambio |
|---|---|
| `miac_purchase_to_invoice/__manifest__.py` | Versión 19.0.1.0.0, descripción técnica/funcional y eliminación de claves antiguas vacías. Única dependencia `purchase`; instalación manual. |
| `miac_purchase_to_invoice/views/purchase_order_view.xml` | `tree,form` pasa a `list,form`; conserva acción, menú, dominio y ubicación. |
| `miac_purchase_to_invoice/i18n/es.po` | Metadatos de traducción de Odoo 19; conserva «Pedidos a Facturar». |
| `miac_purchase_to_invoice/tests/` | Seis pruebas del acceso directo y su integración con estados nativos. |

Se conservan autoría Avannubo, licencia AGPL-3, nombre técnico, icono y XML IDs:
`purchase_to_invoice_action` y `menu_purchase_to_invoice`.
El menú permanece bajo `purchase.menu_purchase_root`, secuencia 2.
Se reutilizan las vistas nativas de lista, formulario y búsqueda; no se copian ni heredan vistas.
No se incorporan archivos compilados ni se cambian otros módulos.

## Comportamiento

Dominio obligatorio: `[('invoice_status', '=', 'to invoice')]`.
Es parte de la acción y no un filtro de búsqueda que se pueda quitar.

- Solo aparecen pedidos con el estado nativo «Pendiente de facturar».
- Las políticas por cantidades pedidas o recibidas siguen el flujo nativo.
- Las facturas en borrador cuentan al determinar cantidades facturadas.
- La facturación parcial mantiene el pedido visible mientras exista cantidad pendiente.
- Cancelaciones y rectificativas modifican el estado según las reglas nativas.
- Las cantidades pendientes negativas no se excluyen mediante un filtro adicional.
- Se mantienen permisos de Compras y reglas por compañía.

## Pruebas y revisión de pantalla

| Validación | Resultado |
|---|---|
| Instalación y actualización | Correctas; módulo `installed`, versión 19.0.1.0.0. |
| AST/XML/PO y dependencias | Correctos; grafo de 19 módulos. No hay vistas personalizadas que componer. |
| `miac_purchase_invoice19` | **6/6**, cero fallos y errores en la ejecución de actualización. |
| Acción y menú | Modelo `purchase.order`, modos `list,form`, padre y secuencia conservados, traducción española correcta. |
| Estados y dominio | Presupuestos y cancelados excluidos; pendientes incluidos. Filtros adicionales se intersectan con el dominio. |
| Facturas | Facturación parcial, factura completa en borrador, cancelación y rectificativa verificadas. |
| Recepciones | Dos recepciones parciales reales mediante Inventario y asistentes nativos de entrega parcial; cantidades facturables correctas. La prueba también admite el mecanismo manual nativo cuando Inventario no está instalado. |
| Cantidad pendiente negativa | Sobre-facturación deja cantidad -1 y el pedido sigue incluido conforme al estado nativo. |
| Permisos | Usuario de Compras autorizado; usuario interno sin permiso de Compras rechazado. Pedidos de otra compañía excluidos. |
| Importes | Base, impuestos y total conservados al consultar el dominio y confirmar el pedido de prueba. |
| Navegador | Menú visible, pedido pendiente listado y presupuesto excluido. «Facturas recibidas» devuelve vacío; al quitarlo vuelve el pendiente. |
| Contenedor | `miac_v19` iniciado y saludable; cero crons y cero servidores de correo activos. |

El producto de recepción se prueba como bien consumible. Los servicios usan por defecto la política
de cantidades pedidas de Odoo 19; no se altera esa regla para simular una recepción.

El respaldo previo no contenía pedidos ni líneas de compra persistentes. Por ello no se presenta
como validación de históricos una comparación sobre documentos inexistentes: se verifican importes
y cantidades con fixtures funcionales y queda pendiente el ensayo con datos reales de MIAC.
El respaldo se inspeccionó sin restaurarlo ni ejecutar su SQL.

## Evidencias

Carpeta: `C:\Proyectos FL\DAM\miac_v19`.

- Respaldos: `purchase-to-invoice19-before-20261011.dump` y
  `purchase-to-invoice19-filestore-before-20261011.tar.gz`.
- Instalación: `purchase-to-invoice19-install-20261011.log`; incluye el ajuste inicial del fixture de recepción.
- Resultado final: **`purchase-to-invoice19-update-20261011.log`**, seis pruebas aprobadas.
- Capturas: `purchase-to-invoice19-validation/menu-ui.png` e `incompatible-filter-ui.png`.
- Pedidos ficticios conservados para revisión: `P00482` (ID 482, confirmado pendiente) y
  `P00483` (ID 483, presupuesto excluido), proveedor `PRUEBA MIAC Proveedor a facturar V19`.

Las transacciones de pruebas automáticas se revierten mediante el framework nativo.
No se crearon facturas reales ni se enviaron correos desde la comprobación en pantalla.

## Entrega y límites

No se ha modificado el Excel ni creado commits. No se han ejecutado conversiones o SQL correctivo
sobre el cliente. La inspección de la base se limita a consultas de lectura; las instalaciones y
fixtures usan exclusivamente el ensayo autorizado.

Para trasladar el módulo a la copia migrada, conservar su nombre técnico y ambos XML IDs.
No retirar el módulo ni sustituir la acción por otra durante la transición. Preferencias, accesos
e históricos reales se comprobarán posteriormente en esa copia separada.

Commit recomendado: `[IMP] #xxxxxx Migra acceso de compras a facturar a Odoo 19`.
