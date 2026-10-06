# Migración de informes MIAC a Odoo 19

Fecha: 5 de octubre de 2026. Rama: `staging_v19`.

## Entrega

Se incorporan `miac_custom_reports` y `account_payment_sale`, ambos en
`19.0.1.0.0`. Conservan autoría, licencia AGPL-3, nombres técnicos y XML IDs
originales. `account_payment_sale` es una adaptación local del código OCA
17.0.1.0.2 del respaldo; no se presenta como una publicación oficial OCA 19.

Fuentes utilizadas exclusivamente:

- `C:\Proyectos FL\DAM\respaldo\addons`.
- `C:\Program Files\Odoo 19.0e.20260105\server`.
- Módulos existentes en este repositorio. No se realizaron consultas ni descargas externas.

## Cambios

### Propagación de referencias y notas

`miac_custom_reports/models/report_sync.py` centraliza la selección de pedidos,
la composición de referencias y notas, y las reglas para actualizar destinos.
Las referencias distintas se separan por comas. Los bloques HTML distintos se
conservan separados, con pedidos ordenados por ID.

Los modelos de ventas, compras, facturas, movimientos y albaranes extienden los
métodos nativos `create`, `write`, `unlink` y de preparación de documentos.
La creación admite lotes. Los cambios y borrados de vínculos actualizan los
destinos anteriores y nuevos; también se contempla cambiar o eliminar líneas
del pedido de origen. Se utiliza `purchase.order.note`.

Se actualizan únicamente facturas en borrador y albaranes abiertos. Un texto
se actualiza si está vacío o coincide con el valor automático anterior.
Los valores expresamente proporcionados en una edición se respetan. Al crear
una factura consolidada, el texto que prepara el flujo nativo desde el primer
pedido puede ampliarse con los restantes pedidos relacionados.

No hay regeneración al leer o imprimir, consultas SQL correctivas, cron nuevo,
ni recalculo masivo de documentos históricos. Se mantienen `client_ref`,
`supplier_ref`, `notes_print`, `partner_bank_id` y `bank_partner_id`.

### Informes

Las cuatro herencias originales se adaptan a los informes nativos de Odoo 19:
ventas, compras, facturas y entregas. Se mantienen direcciones, teléfonos,
referencias, condiciones y lotes. En ventas se muestra `create_uid`, como en
el original. Los widgets de contacto nativos protegen componentes vacíos y
aplican el formato de dirección del idioma correspondiente.

Las columnas fiscales por línea se ocultan sin modificar impuestos, bases o
totales. Ventas conserva `hide_taxes_details=False`: activar esa opción nativa
cambiaría el importe mostrado por línea. Compras utiliza su descuento nativo.
Se ajustan las celdas y los `colspan` de secciones, subsecciones, agrupaciones
y anticipos. Las filas resumidas dejan vacía la serie, evitando asignarles un
lote arbitrario. El subtotal de factura permanece alineado con Importe.

Se conserva el bloque estructural de comunicación de pago, oculto, porque la
vista previa nativa lo hereda. La información bancaria OCA se imprime en su
bloque correspondiente, respetando el enmascaramiento. Las traducciones
originales se conservan y se adapta la etiqueta de dirección fiscal.

### Modos de pago y bancos

`account_payment_sale` depende de `account_payment_mode` en sustitución de
`account_payment_partner`. Propone el modo del contacto según la compañía,
permite seleccionarlo o vaciarlo manualmente y lo traslada a la factura.
Extiende las claves nativas de agrupación con `payment_mode_id`. Conserva
el modo en `sale.report`, incluido en la consulta SQL nativa de análisis.

La selección bancaria del pedido conserva cuentas manuales válidas y limita
las cuentas a la compañía. Se respetan diarios fijos y variables. El
enmascaramiento de cero caracteres no revela accidentalmente la cuenta
completa, tanto en ventas como en facturas.

La selección por mandato SEPA sigue pendiente de la migración bancaria. Si
no existe un mandato válido compatible, el informe no muestra una cuenta
alternativa. Se contempla el código OCA `sepa_direct_debit` y el nativo `sdd`.
No se instala ni sustituye el sistema de mandatos en esta entrega.

## Validación

Entorno aislado: `C:\Proyectos FL\DAM\miac_v19`. Se conserva correo sin salida
y `max_cron_threads=0`. La base principal de ensayo es `miac_v19`; la
instalación desde cero utiliza `miac_reports19_clean`, en el mismo PostgreSQL
aislado, con un proceso Odoo separado. Ninguna contiene una restauración de MIAC.

| Comprobación | Evidencia |
|---|---|
| Python, esquema XML, dependencias y herencias compuestas | `tools/validate_jh_odoo19.py --module miac_custom_reports`: 55 dependencias, 72 archivos Python, 42 XML, 53 vistas del conjunto migrado |
| Instalación desde cero | `reports-clean.log`: instalación de dependencias, `account_payment_sale` y `miac_custom_reports`; 26 casos, sin fallos ni errores |
| Actualización y batería final | `reports-final.log` y `reports-clean-final.log`: 27 casos en cada base, sin fallos ni errores |
| PDF con lotes en albaranes | `reports-pdf-final.log`: caso completo de impresión repetido con `stock.group_lot_on_delivery_slip`, sin fallos ni errores |
| Protección bancaria adicional | `reports-bank-final.log`: selección manual, cuenta ajena, compañías, diarios y ausencia de mandato, sin fallos ni errores |
| Servicio disponible | `miac_v19` reiniciado; `/web/login` responde HTTP 200 en `http://localhost:8079`; PostgreSQL saludable |
| Modos de pago | Cinco casos: propuesta del contacto, cambio manual, anticipos, separación de modos y modo vacío/análisis de ventas |
| Informes y propagación | Trece casos: lotes de creación, consolidación y deduplicación, borrados y cambios de vínculos, textos manuales, documentos cerrados, bancos, compañías, direcciones y QWeb/HTML/PDF |
| Regresión de suscripciones | Nueve casos de `jh_sales_subscription`, repetidos con los informes instalados |

Los tests utilizan fixtures de Odoo 19 y transacciones que revierten los
documentos de prueba. Los PDFs utilizan `allow_pdf_render()`, el mecanismo
nativo que permite al generador consultar estilos y fuentes sin confirmar
los datos de prueba. No se confunde un PDF sin estilos con una validación visual.

Los logs y muestras quedan en `C:\Proyectos FL\DAM\miac_v19`. Las muestras
HTML/PDF se encuentran en `report-validation`; incluyen presupuesto,
proforma, pedido, solicitud/orden de compra, factura, rectificativa, recepción,
entrega, movimientos finalizados, lotes repetidos, agrupaciones, anticipos y
una venta de 75 líneas. Son datos sintéticos, no documentos del cliente.

Se revisaron visualmente 20 PDF, con 25 páginas en total. La venta de 75
líneas ocupa seis páginas. Se verificaron los totales de los casos de venta
y factura: base 180, impuesto 37,80 y total 217,80. En secciones agrupadas
se conserva ese total y se deja vacía la serie. Recepción y entrega
finalizadas imprimen el lote `MIAC-LOT-A` cuando se activa la opción nativa.
`report-validation/pdf-validation.json` contiene el inventario de muestras.

Para imprimir desde el navegador del Docker se configura únicamente en
`miac_v19` el parámetro nativo `report.url=http://127.0.0.1:8069`; el navegador
sigue accediendo por `http://localhost:8079`. Esta dirección interna permite
al generador cargar sus estilos y fuentes. No debe copiarse a otro despliegue
sin revisar su configuración de red. La configuración del ensayo queda
registrada en `reports-runtime-config.log`.

Una consulta de lectura al finalizar las pruebas confirma ambos módulos
instalados en `19.0.1.0.0` y cero pedidos, facturas y albaranes en la base
principal: no se conservaron los documentos sintéticos de los tests.

## Repetición de las pruebas

Estos comandos alteran únicamente la instalación local de ensayo autorizada.
No deben ejecutarse contra una base del cliente.

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' stop web
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' run --rm web --stop-after-init --no-http -u account_payment_sale,miac_custom_reports,jh_sales_subscription --test-enable --test-tags /account_payment_sale,/miac_custom_reports,/jh_sales_subscription
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' start web
```

## Pendientes de aceptación con el cliente

1. Probar una copia de MIAC previamente migrada a 19, conservando SQL y
   filestore de respaldo. No se ha restaurado ni convertido una copia real
   en esta tarea.
2. Comparar importes, referencias, condiciones, contactos y datos bancarios
   con una selección de documentos del origen; validar identidad gráfica,
   idiomas, compañías y permisos de los usuarios reales.
3. Migrar y validar el sistema bancario/mandatos antes de habilitar la selección
   SEPA. No utilizar la cuenta del diario como sustitución de un mandato ausente.
4. Revisar la correspondencia de módulos OCA antiguos con los nuevos sin
   desinstalaciones. Cualquier conversión de datos requiere revisión y
   autorización específica; esta entrega no ejecuta conversiones sobre MIAC.
5. Mantener correo y tareas automáticas desactivados hasta la aceptación
   funcional. El Excel de seguimiento se actualiza cuando se solicite.

La validación técnica local no sustituye la aceptación de datos y procesos
del cliente. No se ha realizado ningún commit, push ni despliegue en producción.

Commit recomendado: `[IMP] #xxxxxx Migra informes MIAC y modos de pago a Odoo 19`
