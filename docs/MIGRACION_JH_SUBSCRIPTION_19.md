# Migración de suscripciones MIAC a Odoo 19

Rama: `staging_v19`. Referencia: instalación local `19.0+e-20260105`.

## Estado y alcance

Implementación de código preparada; **todavía no es una migración aceptada**.
No se creó, instaló, actualizó ni transformó ninguna base de datos durante este trabajo.
No se ejecutó correo ni ningún cron. No se realizó commit.

| Módulo | Versión | Origen / actuación |
|---|---|---|
| commission_oca | 19.0.2.0.0 | OCA sin modificaciones |
| account_commission_oca | 19.0.1.0.1 | OCA sin modificaciones |
| sale_commission_oca | 19.0.1.0.1 | OCA sin modificaciones |
| sale_purchase_lot | 19.0.1.0.0 | Fuentes de respaldo, adaptadas a 19 |
| commission_by_category | 19.0.1.0.0 | Fuentes de respaldo, adaptadas a 19 |
| miac_renovation_subscription | 19.0.1.0.0 | Fuentes de respaldo, adaptadas a 19 |
| miac_line_subscription | 19.0.1.0.0 | Fuentes de respaldo, adaptadas a 19 |
| jh_sales_subscription | 19.0.1.0.0 | Personalizaciones MIAC adaptadas a 19 |

Commit OCA: `74fcdc06111c6271faf12fb3c2e692da076271c2`.
`OCA_COMMISSION_19.lock.json` registra versiones y SHA-256 de cada archivo oficial.
Las únicas consultas externas fueron las descargas de ese código OCA autorizado.

## Cambios funcionales

- Ventas y compras usan los campos de impuestos y unidad de medida de 19.
- El precio usa la protección nativa `technical_price_unit`; los precios explícitos,
  incluido cero, guardan como referencia el precio de tarifa. `jh_discount_manual`
  conserva los descuentos explícitos, incluido cero. Los cambios automáticos usan
  los helpers nativos, con reglas recurrentes, unidades, compañía y posición fiscal.
- Renovación y upsell conservan el asistente de condiciones. Cada línea hereda su
  lote mediante `parent_line_id`, con remapeo de relaciones entre líneas renovadas.
- La validación de confirmación, cantidades facturables, períodos, estado y agrupación
  de facturas corresponde a Odoo 19. Se retiraron los reintentos y limpiezas SQL de
  renovaciones, la agrupación mínima y la facturación forzada de contratos vencidos.
- Comisiones: selección manual > categoría > agente; los contactos usan
  `commission_agent_ids`. Se conservan modelos, tablas y flags manuales existentes.
  La asignación automática no marca como manual la comisión del agente/categoría.
- Análisis nativo de facturas con extensión `SQL`, sin `_group_by()` antiguo ni
  consultas a `ir_property`. El coste se obtiene con `with_company()` y la unidad
  correspondiente. Se mantienen filtros y exportaciones XLSX/CSV, con las monedas
  de factura y compañía identificadas por separado. La comisión de abonos conserva
  su signo OCA negativo. Se conservan las reglas MIAC de `jh_new_tax`.
- El histórico automático usa `_table_query`: consulta facturas FV/RFV contabilizadas,
  con los signos anteriores, sin DELETE/INSERT al abrir el contacto. La tabla derivada
  antigua queda conservada pero ya no alimenta la consulta. El histórico manual,
  visitas, números de factura y vínculos de adjuntos mantienen sus modelos e IDs.
- Listas, kanban, XPath y envío de correo se adaptan a 19. El envío individual por
  destinatario vive en el modelo abstracto compartido; los campos del formulario,
  en `account.move.send.wizard`.
- Crons por lotes usan el progreso nativo. Las renovaciones anticipadas consideran
  contratos activos y reconocen presupuestos existentes. Los avisos de 60 días se
  registran por destinatario, suscripción y vencimiento para no repetirlos; el correo
  se deja en cola. Los avisos respetan el acceso del destinatario.
- ACL personalizadas limitadas a usuarios internos. Histórico automático por compañía;
  visitas e histórico manual siguen la compañía del contacto, admitiendo contactos
  compartidos. Las exportaciones respetan los permisos nativos y ya no usan sudo.
- Se retiraron los cambios destructivos de constraints en `_auto_init()`.

## Archivos de la implementación

- `jh_sales_subscription/models/jh_sale_order_line.py`: precios, descuentos, renovación,
  comisiones, recálculo nativo y envío individual.
- `jh_partner_taxes.py`, `jh_stock_picking.py`, `jh_partner_subscription.py`,
  `jh_sale_subscription.py`: impuestos, inventario y consulta de suscripciones.
- `jh_account_invoice_report.py`, `jh_commission_settlement_line.py`,
  `jh_invoice_report_wizard.py`: informes SQL, costes, impuestos y exportaciones.
- `jh_client_sheet.py`, `jh_client_sheet_manual.py`, `jh_visit.py`: histórico de consulta
  y retirada de cambios destructivos de esquema.
- `jh_sales_subscription.py`: avisos e indicador de emisión por vencimiento.
- `views/`, `reports/`, `data/`, `security/`: listas, kanban, wizard 19, reportes,
  crons desactivados y reglas de acceso.
- Cuatro dependencias personalizadas: modelos, vistas, ACL y manifiestos adaptados.
- `jh_sales_subscription/tests/` y `tools/`: pruebas ORM, validación estática,
  regresiones de helpers y control previo de solo lectura.
- Los cinco manifiestos personalizados se versionaron una sola vez; no existe
  `zue_functional` en ellos. Las versiones y fuentes oficiales OCA se conservaron.

## Preparación obligatoria de los datos: no ejecutada

### 1. Copia y referencia

Respaldar SQL y filestore juntos. Preparar una copia separada y mantenerla aislada del
correo, pagos, conectores y cron. No conectar la instancia 19 a la base 17.
La adaptación del addon no sustituye la migración de toda la base estándar de 17 a 19.

Ejecutar el control previo de **solo lectura** contra el origen y, posteriormente,
contra la copia migrada:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' `
  'tools\preflight_jh_migration19.py' --database NOMBRE_COPIA `
  --output 'C:\ruta\ensayo\preflight_origen.json'
```

Solicita la contraseña sin almacenarla. Puede usar `JH_PREFLIGHT_PASSWORD` temporal.
La conexión fuerza una transacción READ ONLY y ejecuta únicamente SELECT.
Comparar recuentos, sumas por compañía, XML IDs, agentes, tipos legacy y adjuntos.
Registrar además relaciones de lotes/líneas, comisiones por agente y categoría,
liquidaciones y sus totales; verificar los archivos del filestore, no solo sus registros.

### 2. Correspondencia de módulos OCA

| Nombre en 17 | Nombre en 19 | Preservar |
|---|---|---|
| commission | commission_oca | ID de módulo, XML IDs, modelos y tablas de comisiones |
| account_commission | account_commission_oca | Líneas de agente, liquidaciones e históricos |
| sale_commission | sale_commission_oca | Comisiones de venta, agentes y referencias |
| hr_commission | hr_commission_oca | Agentes empleados, liquidaciones y estados históricos |

El mapa común también distingue la absorción `account_payment_partner` →
`account_payment_mode` y la sustitución de interfaz de `account_invoice_line_report`.
Revisión, controles y orden en [MIGRACION_CORRESPONDENCIAS_19.md](MIGRACION_CORRESPONDENCIAS_19.md).
El preflight de JH incorpora el mapa central `MIAC_MODULE_MAPPING_19.json`.

Efectuar la correspondencia de metadatos como parte del proceso de migración de la
copia, antes de cargar los addons 19. **No desinstalar los módulos antiguos.**
Revisar dependencias de módulos, namespaces de `ir.model.data`, claves QWeb, propiedad
registrada de modelos/campos y referencias persistidas en acciones/vistas. Los otros
addons de MIAC que usen nombres OCA antiguos también deben adaptarse antes de cargarse.

Si ya existe algún módulo destino, detener la operación y revisar colisiones de IDs.
Especialmente: `sale_commission` de Enterprise 19 es un módulo diferente. No interpretar
el antiguo módulo OCA como si fuera ese módulo nativo, ni mezclar automáticamente sus datos.
El proceso de renombrado debe conservar los IDs internos, no instalar otra copia de
las mismas tablas/modelos ni crear nuevos XML IDs para sustituir los existentes.

El pre-migrate oficial `commission_oca/migrations/19.0.2.0.0/pre-migrate.py` renombra
`res.partner.agent_ids` a `commission_agent_ids` mediante `openupgradelib`. Validar que
esa librería esté disponible en el entorno de migración. La relación `partner_agent_rel`
conserva `partner_id` y `agent_id`; comparar sus pares antes/después. No copiar ni vaciar
la relación para cambiar el nombre del campo. Evitar ejecutar dos veces el renombrado
si el proceso general ya lo efectuó.

### 3. Precios y descuentos existentes

Guardar una referencia por ID de línea de `price_unit`, `discount`, unidad, cantidad,
moneda, plan, tarifa y lote antes de actualizar. El campo nuevo `jh_discount_manual`
no puede inferir retrospectivamente qué descuentos eran negociados.

Propuesta conservadora para revisar: marcar los descuentos de las líneas existentes
como protegidos y mantener su `technical_price_unit` coherente con la tarifa 19,
restaurando precios/descuentos desde la referencia si el proceso estándar los recomputa.
Hacerlo dentro de la migración de la copia, antes de permitir edición o ejecutar crons.
Esto incluye precios/descuentos cero. No se entregan flags históricos como ya convertidos.

### 4. Campos legacy y selección del histórico

El control previo indica si `jh_client_sheet_manual.jh_account_move` o
`jh_visit.commercial_id` todavía son enteros con una FK. Si ya son texto, no convertir.
Si siguen siendo relaciones, revisar el destino exacto antes de convertir:

- FK a `account_move`: conservar el ID legacy y trasladar el **número de factura**
  (`account_move.name`) al campo de texto, sin convertir simplemente el entero a cadena.
- FK comercial a `res_users`: conservar el ID legacy y trasladar el nombre de su contacto.
- FK comercial a `res_partner`: conservar el ID legacy y trasladar el nombre del contacto.
- Cualquier otro destino: definir su significado con el control previo; no asumirlo.

`JH_LEGACY_CONVERSION_REVIEW.sql` contiene SELECT de diagnóstico y ejemplos de conversión
comentados. Solo se pueden concretar y ejecutar después de revisar la FK y autorizar
esa transformación. Conservan la columna antigua y su constraint; no usan CASCADE.

El histórico automático nuevo identifica filas con `account_move_line.id`. Antes del
cambio, comprobar si existen referencias externas a los IDs de `jh_client_sheet`.
En ese caso preparar una correspondencia específica; conservar su tabla antigua para
verificar la selección FV/RFV y los signos. No borrar la tabla ni el histórico manual.

## Validaciones ejecutadas

- Grafo cerrado: 53 módulos, con fuentes locales disponibles para todas las dependencias.
- Sintaxis de 53 archivos Python personalizados, incluidos los tests preparados.
- Validación RelaxNG de los 34 XML declarados en los cinco módulos personalizados.
- Composición estática de 44 vistas y 1 plantilla QWeb con el motor local de herencias.
- Referencias XML y ACL contra los XML IDs de las fuentes del grafo.
- Importación de los ocho addons con el Python local de Odoo 19, sin registro/base de datos.
- Integridad byte a byte de los tres addons OCA contra el commit fijado.
- Seis pruebas de helpers reales: dos opciones de renovación, identidad de lotes y precio
  cero, correo individual, composición SQL y consulta/signos del histórico.
- `git diff --check`.

Comandos reproducibles sin base:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\test_jh_source_helpers.py
```

Las comprobaciones estáticas anteriores se complementaron con el ensayo Docker indicado
a continuación. Ninguna de ellas acredita aún la conservación de los datos reales de MIAC.

### Ensayo limpio autorizado: Docker miac_v19 (2026-10-05)

- Compose: `C:\Proyectos FL\DAM\miac_v19\compose.yaml`; base nueva `miac_v19`.
- Código Enterprise local `19.0+e-20260105` y este checkout montados en solo lectura.
- Instalación limpia de `jh_sales_subscription` y sus dependencias: correcta; 123 módulos
  contando las integraciones estándar instaladas automáticamente.
- Actualización de `jh_sales_subscription` y `miac_renovation_subscription`: correcta.
- Nueve pruebas ORM: **0 fallos y 0 errores**, log `tests-final.log` en la carpeta Docker.
- Corregida la escritura del precio técnico usando el contexto nativo que evita que Odoo
  descarte ese valor; precios negociados y precio cero conservados al cambiar cantidad.
- El cron de renovación recorre las compañías autorizadas del usuario ejecutor.
- Fixtures ajustados con categoría explícita y factura previa a confirmar una renovación.
- Base sin datos de MIAC, pedidos ni facturas persistentes tras las pruebas.
- Correo bloqueado y tareas automáticas deshabilitadas durante el ensayo.

Las versiones personalizadas permanecen en `19.0.1.0.0`: las correcciones completan
la misma migración y no constituyen un incremento independiente.

## Ensayo pendiente y criterios de aceptación

Preparadas nueve pruebas ORM en `jh_sales_subscription/tests/test_migration19.py`,
con fixtures y patrones de los tests locales de `sale_subscription` 19:
precios y confirmación/factura; cero explícito; productos repetidos/lotes; tarifa y segunda
renovación; manual/categoría/agente y factura; recálculo nativo; avisos/renovaciones sin
duplicados; consulta SQL/exportaciones; conservación de histórico manual y adjunto.

1. Base limpia aislada autorizada, preparada y validada en Docker `miac_v19`.
   Los otros entornos Docker y servicios Windows no fueron reconfigurados.
2. Instalar con solo las rutas de addons estándar 19 y este checkout. No cargar otros
   módulos 17 que aún estén en el repositorio. Usar una carpeta de datos aislada.
3. Mantener `max_cron_threads=0`, sin HTTP durante instalación y pruebas, correo bloqueado
   y ningún SMTP real. Los cuatro crons personalizados se declaran inactivos en instalación
   limpia. En una copia ya instalada, `noupdate=1` puede conservar su valor activo: desactivarlos
   explícitamente como paso autorizado del ensayo, incluyendo los crons nativos de suscripciones.
4. Instalar y actualizar `jh_sales_subscription`; ejecutar `--test-enable` con
   `--test-tags /jh_sales_subscription` y `--stop-after-init`. Revisar log y resultado completo.
5. Repetir actualización sobre la copia de MIAC migrada a 19 con SQL y filestore preservados.
6. UAT: ambas opciones de renovación/upsell, unidades y tarifas, confirmación duplicada,
   contratos activos/vencidos/cerrados/renovados, facturación parcial, abonos y consolidación;
   agentes/liquidaciones/históricos; contactos de entrega; vistas y permisos por compañía;
   correo individual; crons repetidos; selección y signos FV/RFV; XLSX/CSV e informes PDF.
7. Comparar importes, IVA, comisiones, costes y márgenes con el origen por compañía y moneda.
   Los importes nativos del análisis y las comisiones/IVA de factura pueden tener distintas
   bases monetarias; validar con un caso multimoneda y no sumar monedas diferentes.
8. Revisar cómo se representan varias series en una sola línea de material: el modelo
   histórico `lot_id` permite una única serie por línea; no ampliar silenciosamente su estructura.
9. Verificar que avisos de 60 días y anticipación por meses funcionan conjuntamente según la
   configuración actual: un contrato con presupuesto de renovación ya vinculado queda excluido
   del aviso, conservando la selección original.
10. Habilitar correo/crons solo tras aceptación. Si falla el ensayo, restaurar SQL y filestore
    del mismo respaldo y documentar el caso antes de reintentar.

La creación e instalación de la base limpia se ejecutaron con autorización expresa del usuario.
No se ejecutaron transformaciones sobre datos de MIAC; las conversiones y actualizaciones
de una copia migrada del cliente siguen sujetas a autorización específica.
