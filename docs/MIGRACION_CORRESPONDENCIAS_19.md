# MIAC: correspondencias de módulos 17 → 19

Revisión del 06/10/2026 en `staging_v19`. Fuentes: respaldo local de addons 17,
instalación local `19.0e.20260105` y addons presentes en este repositorio.
No se hicieron consultas ni descargas externas.

## Resultado y alcance

Se revisaron los **29 addons del repositorio con versión 19.0** y su cadena de
dependencias. No se encontraron dependencias ni referencias explícitas a XML IDs
de los módulos antiguos en su código activo. Esto no clasifica todos los addons
instalados en la base del cliente ni convierte sus datos.

El mapa revisable y reutilizable es [MIAC_MODULE_MAPPING_19.json](MIAC_MODULE_MAPPING_19.json).
El control de fuentes y metadatos de la instalación limpia es
[MIAC_MODULE_MAPPING_19_AUDIT.json](MIAC_MODULE_MAPPING_19_AUDIT.json).

| Origen V17 | Destino V19 | Operación para la copia migrada |
|---|---|---|
| `commission` | `commission_oca` | Renombrado de módulo y namespace; conservar registros y relaciones. |
| `account_commission` | `account_commission_oca` | Renombrado; conservar líneas de agentes, liquidaciones e históricos. |
| `sale_commission` OCA | `sale_commission_oca` | Renombrado OCA; distinguirlo del nuevo módulo nativo con el mismo nombre antiguo. |
| `hr_commission` | `hr_commission_oca` | Renombrado; conservar agentes empleados, selección `salesman` y estados de liquidación. |
| `account_payment_partner` | `account_payment_mode` | Absorción en el módulo que ya existe en V17; no es un renombrado sobre un destino vacío. |
| `account_invoice_line_report` | Vistas nativas de `account` y extensión JH | Sustitución de interfaz con revisión individual de referencias; no fusionar namespaces. |

Los cuatro renombrados y la absorción bancaria conservan los **91 XML IDs
declarados en los archivos de datos XML/CSV del origen**: 43, 30, 7, 2 y 9,
respectivamente. Esta comparación no incluye los XML IDs generados para modelos
y campos, ni garantiza identidad de los registros de una base histórica.
El control SQL compara esos registros y detecta colisiones por modelo/ID.

Los demás addons V19 mantienen su nombre técnico. Para `jh_sales_subscription`
no hay carpeta homónima en el respaldo de addons: su manifiesto V17 está en
el historial Git anterior al commit `27f3d78` (`17.0.0.7.3`). La conservación
de su nombre no depende de una equivalencia inferida por similitud.

`l10n_es_facturae` OCA y `l10n_es_edi_facturae` nativo son componentes distintos:
el primero existe con su nombre original en las fuentes OCA 19 aportadas.
La instalación del segundo no se interpreta como migración del primero.
`account_payment_term_extension` también conserva su nombre; no se confunde
con el antiguo módulo estándar `account_payment_term`.

## Correspondencia de datos: orden y condiciones

1. Trabajar sobre una copia separada de MIAC, con respaldo SQL y filestore.
   Mantener correo y crons desactivados durante el ensayo.
2. Obtener el control previo de esa copia. La instalación limpia tiene todos
   los destinos activos y ningún namespace antiguo; esto **no prueba** la
   conservación de comisiones, empleados ni modos de pago de MIAC.
3. Procesar los renombrados OCA en el motor de migración, antes de cargar los
   addons 19 que esperan esos namespaces. Mantener el ID del módulo original,
   los IDs de vistas/acciones/grupos/campos y las tablas de negocio.
   Revisar `base.module_<nombre>`, dependencias, XML IDs, claves QWeb y referencias
   persistidas. No hacer un reemplazo global de texto ni renombrar modelos
   `commission.*`, que mantienen su nombre.
4. Si existe un registro del módulo destino, incluso solo en el catálogo de
   aplicaciones, revisar su procedencia antes de resolverlo. Si dos namespaces
   contienen el mismo nombre de XML ID con modelo/registro distinto, detener
   ese caso para una correspondencia individual. No desinstalar módulos
   históricos para liberar el nombre. No reinterpretar un `sale_commission`
   nativo 19 como si fuera el antiguo OCA.
5. Absorber `account_payment_partner` conservando el módulo `account_payment_mode`
   existente y sus IDs. Sus nueve XML IDs de interfaz conservan el nombre local
   en el destino. Revisar también XML IDs generados, vistas heredadas externas,
   campos de modos de pago de contactos/facturas/líneas y modos de devolución.
6. Los modos de pago de contactos son dependientes de compañía. En V17 usan
   `ir_property`; en V19 las columnas de `res_partner` son JSONB. Validar esa
   conversión con el motor general 17 → 19 y comparar compañías, valores por
   defecto e IDs de modos. No escribir un modo único en todos los contactos
   ni ejecutar dos veces la conversión.
7. Aplicar una sola vez el cambio `res.partner.agent_ids` → `commission_agent_ids`
   mediante el pre-migrate oficial de `commission_oca/19.0.2.0.0` cuando corresponda.
   La relación sigue siendo `partner_agent_rel(partner_id, agent_id)`; no vaciarla
   ni duplicarla. Comparar recuento y huella de los pares antes/después.
8. Comparar comisiones, categorías, líneas de agentes, empleados `salesman`,
   liquidaciones, estados e importes. Complementar los recuentos del control
   previo con el ensayo funcional descrito en la migración de JH.

La instalación local de Odoo y el Docker limpio no contienen actualmente
`openupgradelib` ni `odoo.upgrade.util`. La preparación del entorno de migración
de datos sigue pendiente. No se añadió un hook improvisado ni se ejecutaron
conversiones de módulos/campos sobre una copia del cliente.

## Sustitución de `account_invoice_line_report`

El addon V17 declara cuatro registros de interfaz del **mismo modelo nativo
`account.invoice.report`**. No introduce otro modelo ni una tabla de facturas.
Por eso sus cuatro XML IDs no se renombrarán indiscriminadamente a `account`.

| Registro antiguo | Tratamiento revisado |
|---|---|
| `view_invoice_report_tree_info` | Usar `account.account_invoice_report_view_tree`, extendida por JH. |
| `view_account_invoice_report_search` | Usar `account.view_account_invoice_report_search`, extendida por JH con los filtros originales. |
| `action_account_invoice_line_report` | Revisar enlaces y filtros guardados por ID. El flujo de cliente utiliza la acción nativa `account.action_account_invoice_report_all`, con acceso a lista, pivot y gráfico. |
| `menu_action_account_invoice_line_report` | Revisar favoritos, permisos y referencias; el menú nativo `account.menu_action_account_invoice_report_all` mantiene el acceso al análisis. |

La acción nativa conserva sus filtros iniciales de período y cliente, distintos
del contexto vacío del antiguo addon. Validar su uso con el cliente; no cambiar
de forma masiva contextos, filtros de proveedor ni acciones históricas.
Las vistas antiguas necesitan revisión de `tree` → `list` y de sus herencias
antes de habilitarlas en la copia. No eliminar sus registros sin analizar
las referencias que reciban de otros módulos todavía pendientes.

### Ajuste aplicado al código de JH

- Recuperados `without_price` / `with_price`, con las mismas condiciones
  sobre `price_average`; mostrados como **Sin precio** y **Con precio**.
- Habilitada la lista de líneas en la acción nativa de análisis de facturas.
  Se extiende el flujo existente; no se añade otro botón, menú ni acción.
- Manifest de JH: **19.0.1.0.1**, un único incremento FIX para esta revisión,
  con descripción funcional actualizada. Versiones OCA oficiales conservadas.
- Nueva regresión comprueba la vista combinada y aplica sus dominios a una
  factura con línea a precio cero y línea con precio. Comprueba exclusión y
  cobertura de ambas selecciones, además del acceso a lista.

## Control previo reproducible: solo lectura

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\preflight_module_mapping19.py --output docs\MIAC_MODULE_MAPPING_19_AUDIT.json

# Añadir una base local con --database NOMBRE --host HOST --port PUERTO.
# El script solicita la contraseña y no la guarda.
# Para ejecutar dentro de Docker sin el respaldo de Windows, usar --database-only.

& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\test_module_mapping19.py
```

`preflight_module_mapping19.py` fuerza READ ONLY y ejecuta solamente SELECT.
Identifica módulos de origen/destino, colisiones de XML IDs, dependencias activas
antiguas, claves de vistas, propietarios de campos, almacenamiento bancario por
compañía y recuentos/huella de relaciones de comisiones. No ofrece opción de
aplicar conversiones. `preflight_jh_migration19.py` incorpora el mismo control,
evitando mantener dos listas diferentes de correspondencias.

Los estados de una instalación limpia indican explícitamente que **no prueban
una migración de datos**. Una colisión o un destino ya presente exige revisión,
sin resolverlo automáticamente. El artefacto JSON no contiene credenciales.

## Validaciones y pendientes

- Auditoría de los 29 addons V19: sin referencias antiguas detectadas ni
  dependencias ausentes en las fuentes locales.
- Control de la base limpia `miac_v19`: READ ONLY, sin colisiones ni namespaces
  antiguos; relación de agentes y tablas de comisiones/modos de pago vacías.
- Diez pruebas unitarias del control previo aprobadas, incluidas colisiones,
  destino existente, nombre nativo ambiguo y rechazo de transacción de escritura.
- Sintaxis, XML IDs y composición estática de las vistas de JH, HR commissions
  y posiciones fiscales contra Odoo local 19.
- Actualización de JH a `19.0.1.0.1` y **10 pruebas ORM aprobadas** en `miac_v19`,
  incluidas las nueve regresiones originales y la nueva de precio/lista;
  cero fallos y cero errores. Log local:
  `C:\Proyectos FL\DAM\miac_v19\module-mapping-tests-20261006.log`.
- Seis pruebas de helpers de JH aprobadas; el preflight integrado se ejecutó
  con READ ONLY. Servicio web restablecido, HTTP 200 y contenedores saludables.
- No se aplicaron renombrados, absorciones ni conversiones de campos históricos
  en este ensayo. La actualización de JH solo cargó el ajuste de interfaz y tests.
- Ensayo sobre datos reales y aceptación de históricos: pendiente de una copia
  MIAC migrada. El contenedor V17 detenido no se inició ni se modificó.

Commit recomendado: `[FIX] #xxxxxx Ajusta correspondencias y filtros MIAC para V19`
