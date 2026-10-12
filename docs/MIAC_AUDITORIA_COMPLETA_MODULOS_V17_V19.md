# MIAC — Auditoría completa de módulos V17 frente al ensayo V19

> **Actualización posterior a la auditoría, 12/10/2026:** las 15 fuentes OCA
> que faltaban ya se incorporaron y validaron en el repositorio. La tabla y los
> recuentos siguientes conservan la fotografía anterior de diagnóstico.
> La actualización de esos módulos en la base migrada sigue pendiente.
> Detalle de la incorporación en `MIAC_INCIDENCIAS_POST_MIGRACION_19.md`.

Fecha de corte: 12/10/2026, después de POST-010. Diagnóstico de solo lectura.

## Qué explica los errores aparecidos

El control del Excel y de los módulos preparados no cubría todos los addons
instalados en la base real. Que el inventario del proyecto estuviera completo
no demostraba que el inventario de V17 estuviera completo en V19. Los módulos
que aparecieron al abrir formularios ya existían en V17; no son funciones nuevas
instaladas por el cliente después del mapeo.

La restauración conserva filas de `ir_module_module` y vistas de addons que
no están en el addons_path. Odoo puede arrancar omitiendo esos addons. Por ello
un registro `installed` no acredita que su Python o sus campos estén cargados;
una vista puede seguir pidiendo un campo ausente al navegador.

## Fuentes y método

- V17: `miac17-db`, base `miac`, todos los módulos con `state='installed'`.
- V19: `miac_v19_migrada_db`, base `miac_v19_migrada`, todos los estados.
- Fuentes: respaldo V17, repositorio y addons_path efectivo del Docker V19:
  núcleo comunitario, Enterprise local y repositorio, en ese orden.
- Importación efectiva: nombres de paquetes en `sys.modules` después de cargar
  el registro en una sesión Odoo nueva. Se contrasta cada destino con su estado
  y versión de BD. Importación y esquema no equivalen a aceptación funcional.
- Todos los módulos, incluidas dependencias e integraciones técnicas; no solo
  aquellos marcados como aplicaciones en el menú Apps.
- Clasificación por manifiestos/cabeceras de las fuentes de origen y autoría;
  los manifiestos nativos sin autor explícito no se tratan como personalizados.
  Studio es metadato de BD y el tema Buzzy se muestra como caso separado.
- Renombres acordados: commission/account_commission/sale_commission/hr_commission
  a sus nombres `_oca`, y account_payment_partner a account_payment_mode.
  La cobertura de código del destino no declara completada la fusión de datos.
- `account_invoice_line_report` se compara con el addon OCA homónimo instalado;
  la antigua propuesta de sustituirlo solo por `account` quedó superada.

No se han instalado módulos, modificado bases, convertido datos, cambiado Excel
ni creado commits para esta auditoría. Se encendió únicamente PostgreSQL V17
para leerlo y se vuelve a su estado detenido al terminar.

## Resumen que concilia todas las filas de origen

| Clasificación de los 317 módulos V17 | Entradas de origen |
|---|---:|
| Estándar Odoo con mismo nombre y destino importado/instalado | 226 |
| Estándar Odoo sin el mismo nombre: revisar fusión/cambio oficial | 13 |
| OCA/personalizados con equivalente V19 disponible, instalado e importado | 58 |
| OCA sin fuente en el entorno V19 | 15 |
| Fuente V19 disponible, destino sin instalar: hr_commission_oca | 1 |
| Excluido expresamente: DAM Website Page Porter | 1 |
| Sustitución estándar acordada: sale_product_template_tags | 1 |
| Studio: metadatos, sin carpeta requerida | 1 |
| Tema Buzzy cargado, compatibilidad pendiente de probar | 1 |
| **Total instalado en V17** | **317** |

Hay **239 entradas estándar** y **78 entradas OCA/personalizadas/Studio/tema**.
Las cifras son entradas del origen: account_payment_partner y account_payment_mode
comparten un destino, así que no son 58 destinos diferentes.

La base V19 tiene **347 filas installed**; **22 no tienen paquete importado**,
entre ellas Studio, que no requiere paquete, antiguos namespaces y los addons
que faltan. Los restantes **325** tienen paquete importado. El runtime importó
329 paquetes en total, incluidos cuatro que no constan installed; por eso no
se utiliza ese total de imports como número de aplicaciones instaladas.

## Faltan 15 fuentes OCA en el entorno actual

Los quince nombres se encontraron en ramas oficiales **19.0**. Su ausencia es
local; no se afirma que haya que portar manualmente su código V17. Se necesita
incorporarlos, preparar su actualización de datos, instalarlos/actualizarlos y
verificarlos funcionalmente, con respaldos del ensayo.

| Módulo que falta | Versión oficial encontrada | Repositorio/fuente exacta |
|---|---|---|
| `account_banking_mandate` | `19.0.1.0.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_mandate) |
| `account_banking_pain_base` | `19.0.1.1.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_pain_base) |
| `account_banking_sepa_credit_transfer` | `19.0.1.0.0` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_sepa_credit_transfer) |
| `account_banking_sepa_direct_debit` | `19.0.1.1.1` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_banking_sepa_direct_debit) |
| `account_financial_report` | `19.0.0.0.26` | [OCA/account-financial-reporting](https://github.com/OCA/account-financial-reporting/tree/0078bc03f234d1caa8b9f40324678ce9dbed2a72/account_financial_report) |
| `account_move_name_sequence` | `19.0.1.0.3` | [OCA/account-financial-tools](https://github.com/OCA/account-financial-tools/tree/ddcabb93373382148826f97bf9935424d03ddea5/account_move_name_sequence) |
| `account_payment_order` | `19.0.1.0.7` | [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64/account_payment_order) |
| `account_statement_base` | `19.0.1.0.1` | [OCA/account-reconcile](https://github.com/OCA/account-reconcile/tree/5402de2e9bb8e2cdd271d28c8d33a24eae3725c4/account_statement_base) |
| `account_statement_import_base` | `19.0.1.0.0` | [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import/tree/65316c38d7a5586456bc751d8939b84f1cf0bc2e/account_statement_import_base) |
| `account_statement_import_file` | `19.0.1.0.0` | [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import/tree/65316c38d7a5586456bc751d8939b84f1cf0bc2e/account_statement_import_file) |
| `l10n_es_account_statement_import_n43` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_account_statement_import_n43) |
| `l10n_es_aeat_mod111` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod111) |
| `l10n_es_aeat_mod123` | `19.0.1.0.0` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod123) |
| `l10n_es_aeat_mod349` | `19.0.1.1.2` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_aeat_mod349) |
| `l10n_es_toponyms` | `19.0.1.0.1` | [OCA/l10n-spain](https://github.com/OCA/l10n-spain/tree/f04d5c17e2e4929ba466bfd73e2628991bef4d4f/l10n_es_toponyms) |

Las dependencias directas de estos quince manifests se encontraron entre los
addons ya disponibles o entre los propios quince pendientes. No aparece otro
nombre adicional sin fuente por ese nivel de análisis. Para los destinos que
ya están disponibles, se comprobó también su cierre recursivo de dependencias:
ninguna fuente ausente. La instalación puede revelar necesidades de datos,
librerías, vistas o funcionalidades que ese control estático no prueba.

Prioridad técnica: banca/mandatos/órdenes de pago y extractos; informes financieros
y numeración; localizaciones fiscales y toponimia. No desinstalarlos para hacer
que desaparezcan sus vistas y menús. `account_move_name_sequence` merece prueba
especial: en el ensayo previo se retiró su antiguo CHECK para permitir el
upgrade; su versión V19 debe validarse con numeración y contabilización reales.

## Una fuente preparada pero sin instalar

`hr_commission` de V17 corresponde a `hr_commission_oca` **19.0.1.0.0** disponible
en el repositorio. Su destino consta **uninstalled**. El registro antiguo sigue
installed, pero no se importa. Se necesita completar su correspondencia,
actualización y conservación de agentes empleados/tipos de comisión antes de
aceptar esa funcionalidad. No se instala desde esta auditoría.

## Correspondencias que no se dan por cerradas

Los destinos de commission, account_commission y sale_commission se importan,
pero sobreviven namespaces antiguos de comisiones. `account_payment_partner`
permanece en estado `to upgrade`, aunque account_payment_mode ya está instalado.
Esto no se resuelve con una descarga: requiere revisar colisiones, XML IDs,
menús/vistas, permisos y datos. Las actuaciones acotadas POST-009/010 retiraron
una vista duplicada y migraron la referencia Studio de agentes; no constituyen
una fusión general de módulos o de grupos.

Casos ya acordados:
- `dam_website_page_porter`: excluido por el usuario; fuente residual V17,
  sin cargar en V19. Preparar su transición solo si se aprueba utilizarlo.
- `sale_product_template_tags`: sustitución funcional estándar prevista;
  conservar/verificar etiquetas, filtros y referencias antes de retirar restos.
- `studio_customization`: XML IDs, vistas y campos en BD; no necesita un addon
  descargado. POST-007/010 demuestran que sus referencias sí deben comprobarse.
- `theme_buzzy`: fuente disponible y paquete cargado, manifest `1.0.0` sin serie
  Odoo. No inferir compatibilidad V19 por ese número; probar el sitio y snippets.

## Trece nombres estándar que no coinciden

No se cuentan como addons OCA faltantes. El servicio oficial puede fusionar,
renombrar o retirar módulos estándar entre 17 y 19. La auditoría detecta la
no coincidencia; no inventa destinos ni certifica pérdida de función. Revisar
las funciones correspondientes en el ensayo y las decisiones oficiales:

- `account_auto_transfer`
- `account_disallowed_expenses`
- `account_payment_term`
- `account_reports_tax_reminder`
- `documents_spreadsheet_account`
- `documents_spreadsheet_crm`
- `sale_async_emails`
- `sale_product_configurator`
- `spreadsheet_dashboard_purchase`
- `stock_account_enterprise`
- `web_editor`
- `website_form_project`
- `website_sale_product_configurator`

## Base documental de cierre y próxima revisión

No volver a declarar «todos» usando únicamente filas del presupuesto. La
siguiente aceptación debe conciliar las **317 filas de origen** con fuente,
estado, versión, importación, correspondencia y pruebas funcionales. Los
pendientes de los quince módulos y HR deben reducirse explícitamente; los
casos de sustitución/exclusión deben conservar una decisión revisada.

Evidencias completas, fuera del repositorio:
`C:\Proyectos FL\DAM\miac_v19_migrada\logs`:
`module_inventory_compare_final.json`, `runtime_inventory.json`,
`runtime_inventory.log`, `missing_modules_oca19_sources.json`.

## Inventario completo de los 317 módulos instalados en V17

«Fuente» corresponde al addons_path efectivo V19, no solo a la carpeta del repo.
«Importado» indica paquete presente en el runtime inspeccionado; Studio es la
excepción dinámica documentada. «Estado BD» es el del destino tras correspondencia.

| Origen V17 | Clasificación | Versión V17 | Destino V19 | Estado BD / versión | Fuente | Importado | Conclusión |
|---|---|---|---|---|---|---|---|
| `account` | Odoo estándar | `17.0.1.2` | `account` | installed / `19.0.1.4` | `1.4` | sí | ESTANDAR CARGADO |
| `account_accountant` | Odoo estándar | `17.0.1.1` | `account_accountant` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `account_asset` | Odoo estándar | `17.0.1.0` | `account_asset` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `account_auto_transfer` | Odoo estándar | `17.0.1.0` | `account_auto_transfer` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `account_banking_mandate` | OCA | `17.0.1.0.3` | `account_banking_mandate` | installed / `17.0.1.0.3` | `ausente` | no | FALTA FUENTE V19 |
| `account_banking_pain_base` | OCA | `17.0.1.0.0` | `account_banking_pain_base` | installed / `17.0.1.0.0` | `ausente` | no | FALTA FUENTE V19 |
| `account_banking_sepa_credit_transfer` | OCA | `17.0.1.0.3` | `account_banking_sepa_credit_transfer` | installed / `17.0.1.0.3` | `ausente` | no | FALTA FUENTE V19 |
| `account_banking_sepa_direct_debit` | OCA | `17.0.1.2.2` | `account_banking_sepa_direct_debit` | installed / `17.0.1.2.2` | `ausente` | no | FALTA FUENTE V19 |
| `account_bank_statement_import` | Odoo estándar | `17.0.1.0` | `account_bank_statement_import` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_bank_statement_import_camt` | Odoo estándar | `17.0.1.0` | `account_bank_statement_import_camt` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `account_bank_statement_import_csv` | Odoo estándar | `17.0.1.0` | `account_bank_statement_import_csv` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_bank_statement_import_ofx` | Odoo estándar | `17.0.1.0` | `account_bank_statement_import_ofx` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_base_import` | Odoo estándar | `17.0.1.0` | `account_base_import` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `account_commission` | OCA | `17.0.1.0.0` | `account_commission_oca` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_disallowed_expenses` | Odoo estándar | `17.0.1.0` | `account_disallowed_expenses` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `account_due_list` | OCA | `17.0.1.0.0` | `account_due_list` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_due_list_payment_mode` | OCA | `17.0.1.0.0` | `account_due_list_payment_mode` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_edi_ubl_cii` | Odoo estándar | `17.0.1.0` | `account_edi_ubl_cii` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_financial_report` | OCA | `17.0.1.2.2` | `account_financial_report` | installed / `17.0.1.2.2` | `ausente` | no | FALTA FUENTE V19 |
| `account_fiscal_position_autodetect_optional_vies` | OCA | `17.0.1.0.0` | `account_fiscal_position_autodetect_optional_vies` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_fiscal_position_partner_type` | OCA | `17.0.1.0.0` | `account_fiscal_position_partner_type` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_followup` | Odoo estándar | `17.0.1.1` | `account_followup` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `account_invoice_extract` | Odoo estándar | `17.0.1.0` | `account_invoice_extract` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_invoice_extract_purchase` | Odoo estándar | `17.0.1.0` | `account_invoice_extract_purchase` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_invoice_line_report` | OCA | `17.0.1.0.0` | `account_invoice_line_report` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_move_name_sequence` | OCA | `17.0.1.0.5` | `account_move_name_sequence` | installed / `17.0.1.0.5` | `ausente` | no | FALTA FUENTE V19 |
| `account_online_synchronization` | Odoo estándar | `17.0.1.0` | `account_online_synchronization` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `account_payment` | Odoo estándar | `17.0.2.0` | `account_payment` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `account_payment_mode` | OCA | `17.0.1.0.2` | `account_payment_mode` | installed / `19.0.1.1.0` | `19.0.1.1.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_order` | OCA | `17.0.1.4.4` | `account_payment_order` | installed / `17.0.1.4.4` | `ausente` | no | FALTA FUENTE V19 |
| `account_payment_partner` | OCA | `17.0.1.0.3` | `account_payment_mode` | installed / `19.0.1.1.0` | `19.0.1.1.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_purchase` | OCA | `17.0.1.2.1` | `account_payment_purchase` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_purchase_stock` | OCA | `17.0.1.0.0` | `account_payment_purchase_stock` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_return` | OCA | `17.0.1.1.0` | `account_payment_return` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_sale` | OCA | `17.0.1.0.2` | `account_payment_sale` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_payment_term` | Odoo estándar | `17.0.1.0` | `account_payment_term` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `account_payment_term_extension` | OCA | `17.0.1.0.2` | `account_payment_term_extension` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `account_qr_code_sepa` | Odoo estándar | `17.0.0.1` | `account_qr_code_sepa` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `account_reports` | Odoo estándar | `17.0.1.0` | `account_reports` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `account_reports_tax_reminder` | Odoo estándar | `17.0.1.0` | `account_reports_tax_reminder` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `account_statement_base` | OCA | `17.0.1.0.1` | `account_statement_base` | installed / `17.0.1.0.1` | `ausente` | no | FALTA FUENTE V19 |
| `account_statement_import_base` | OCA | `17.0.1.0.0` | `account_statement_import_base` | installed / `17.0.1.0.0` | `ausente` | no | FALTA FUENTE V19 |
| `account_statement_import_file` | OCA | `17.0.1.0.0` | `account_statement_import_file` | installed / `17.0.1.0.0` | `ausente` | no | FALTA FUENTE V19 |
| `account_tax_balance` | OCA | `17.0.1.0.0` | `account_tax_balance` | installed / `19.0.1.0.3` | `19.0.1.0.3` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `analytic` | Odoo estándar | `17.0.1.1` | `analytic` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `analytic_enterprise` | Odoo estándar | `17.0.0.1` | `analytic_enterprise` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `appointment` | Odoo estándar | `17.0.1.3` | `appointment` | installed / `19.0.1.3` | `1.3` | sí | ESTANDAR CARGADO |
| `appointment_account_payment` | Odoo estándar | `17.0.1.0` | `appointment_account_payment` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `appointment_crm` | Odoo estándar | `17.0.1.0` | `appointment_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `appointment_hr` | Odoo estándar | `17.0.1.0` | `appointment_hr` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `appointment_sms` | Odoo estándar | `17.0.1.0` | `appointment_sms` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `attachment_indexation` | Odoo estándar | `17.0.2.1` | `attachment_indexation` | installed / `19.0.2.1` | `2.1` | sí | ESTANDAR CARGADO |
| `auth_signup` | Odoo estándar | `17.0.1.0` | `auth_signup` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `auth_totp` | Odoo estándar | `17.0.1.0` | `auth_totp` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `auth_totp_mail` | Odoo estándar | `17.0.1.0` | `auth_totp_mail` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `auth_totp_portal` | Odoo estándar | `17.0.1.0` | `auth_totp_portal` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `avannubo_declaracion_responsable` | Personalizado/externo | `17.0.17.0` | `avannubo_declaracion_responsable` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `barcodes` | Odoo estándar | `17.0.2.0` | `barcodes` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `barcodes_gs1_nomenclature` | Odoo estándar | `17.0.1.0` | `barcodes_gs1_nomenclature` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `base` | Odoo estándar | `17.0.1.3` | `base` | installed / `19.0.1.3` | `1.3` | sí | ESTANDAR CARGADO |
| `base_address_extended` | Odoo estándar | `17.0.1.1` | `base_address_extended` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `base_automation` | Odoo estándar | `17.0.1.0` | `base_automation` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `base_bank_from_iban` | OCA | `17.0.1.0.1` | `base_bank_from_iban` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `base_geolocalize` | Odoo estándar | `17.0.2.1` | `base_geolocalize` | installed / `19.0.2.1` | `2.1` | sí | ESTANDAR CARGADO |
| `base_iban` | Odoo estándar | `17.0.1.0` | `base_iban` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `base_import` | Odoo estándar | `17.0.2.0` | `base_import` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `base_import_module` | Odoo estándar | `17.0.1.0` | `base_import_module` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `base_install_request` | Odoo estándar | `17.0.1.0` | `base_install_request` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `base_iso3166` | OCA | `17.0.1.0.1` | `base_iso3166` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `base_location` | OCA | `17.0.1.0.0` | `base_location` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `base_location_geonames_import` | OCA | `17.0.1.0.0` | `base_location_geonames_import` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `base_setup` | Odoo estándar | `17.0.1.0` | `base_setup` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `base_sparse_field` | Odoo estándar | `17.0.1.0` | `base_sparse_field` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `base_vat` | Odoo estándar | `17.0.1.0` | `base_vat` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `board` | Odoo estándar | `17.0.1.0` | `board` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `bus` | Odoo estándar | `17.0.1.0` | `bus` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `calendar` | Odoo estándar | `17.0.1.1` | `calendar` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `calendar_sms` | Odoo estándar | `17.0.1.1` | `calendar_sms` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `commission` | OCA | `17.0.1.1.0` | `commission_oca` | installed / `19.0.2.0.0` | `19.0.2.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `commission_by_category` | Personalizado/externo | `17.0.17.0` | `commission_by_category` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `component` | OCA | `17.0.1.0.0` | `component` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `component_event` | OCA | `17.0.1.0.0` | `component_event` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `contacts` | Odoo estándar | `17.0.1.0` | `contacts` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `contacts_enterprise` | Odoo estándar | `17.0.1.0` | `contacts_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `crm` | Odoo estándar | `17.0.1.8` | `crm` | installed / `19.0.1.9` | `1.9` | sí | ESTANDAR CARGADO |
| `crm_enterprise` | Odoo estándar | `17.0.1.0` | `crm_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `crm_iap_enrich` | Odoo estándar | `17.0.1.1` | `crm_iap_enrich` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `crm_iap_mine` | Odoo estándar | `17.0.1.2` | `crm_iap_mine` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `crm_sms` | Odoo estándar | `17.0.1.1` | `crm_sms` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `currency_rate_live` | Odoo estándar | `17.0.1.0` | `currency_rate_live` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `dam_website_page_porter` | Personalizado/externo | `17.0.1.0.2` | `dam_website_page_porter` | installed / `17.0.1.0.2` | `17.0.1.0.2` | no | Excluido del alcance; V17 residual en BD |
| `date_range` | OCA | `17.0.1.2.0` | `date_range` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `date_range_account` | OCA | `17.0.1.0.0` | `date_range_account` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `delivery` | Odoo estándar | `17.0.1.0` | `delivery` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `delivery_stock_picking_batch` | Odoo estándar | `17.0.1.0` | `delivery_stock_picking_batch` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `delivery_ups` | Odoo estándar | `17.0.1.0` | `delivery_ups` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `digest` | Odoo estándar | `17.0.1.1` | `digest` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `digest_enterprise` | Odoo estándar | `17.0.1.0` | `digest_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents` | Odoo estándar | `17.0.1.3` | `documents` | installed / `19.0.1.4` | `1.4` | sí | ESTANDAR CARGADO |
| `documents_account` | Odoo estándar | `17.0.1.0` | `documents_account` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_hr` | Odoo estándar | `17.0.1.0` | `documents_hr` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_hr_holidays` | Odoo estándar | `17.0.1.0` | `documents_hr_holidays` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_product` | Odoo estándar | `17.0.1.0` | `documents_product` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_project` | Odoo estándar | `17.0.1.0` | `documents_project` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_project_sale` | Odoo estándar | `17.0.1.0` | `documents_project_sale` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_spreadsheet` | Odoo estándar | `17.0.1.0` | `documents_spreadsheet` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `documents_spreadsheet_account` | Odoo estándar | `17.0.1.0` | `documents_spreadsheet_account` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `documents_spreadsheet_crm` | Odoo estándar | `17.0.1.0` | `documents_spreadsheet_crm` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `error_line_wiz` | Personalizado/externo | `17.0.17.0` | `error_line_wiz` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `gamification` | Odoo estándar | `17.0.1.0` | `gamification` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `gamification_sale_crm` | Odoo estándar | `17.0.1.0` | `gamification_sale_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `google_gmail` | Odoo estándar | `17.0.1.2` | `google_gmail` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `google_recaptcha` | Odoo estándar | `17.0.1.0` | `google_recaptcha` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr` | Odoo estándar | `17.0.1.1` | `hr` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `hr_attendance` | Odoo estándar | `17.0.2.0` | `hr_attendance` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `hr_attendance_gantt` | Odoo estándar | `17.0.1.0` | `hr_attendance_gantt` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_commission` | OCA | `17.0.1.0.0` | `hr_commission_oca` | uninstalled / `` | `19.0.1.0.0` | no | FUENTE DISPONIBLE, FALTA INSTALAR |
| `hr_gamification` | Odoo estándar | `17.0.1.0` | `hr_gamification` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_gantt` | Odoo estándar | `17.0.1.0` | `hr_gantt` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_holidays` | Odoo estándar | `17.0.1.6` | `hr_holidays` | installed / `19.0.1.6` | `1.6` | sí | ESTANDAR CARGADO |
| `hr_holidays_attendance` | Odoo estándar | `17.0.1.0` | `hr_holidays_attendance` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_holidays_gantt` | Odoo estándar | `17.0.1.0` | `hr_holidays_gantt` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_hourly_cost` | Odoo estándar | `17.0.1.0` | `hr_hourly_cost` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_mobile` | Odoo estándar | `17.0.1.0` | `hr_mobile` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_org_chart` | Odoo estándar | `17.0.1.0` | `hr_org_chart` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_skills` | Odoo estándar | `17.0.1.0` | `hr_skills` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `hr_skills_slides` | Odoo estándar | `17.0.1.0` | `hr_skills_slides` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `http_routing` | Odoo estándar | `17.0.1.0` | `http_routing` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `iap` | Odoo estándar | `17.0.1.1` | `iap` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `iap_crm` | Odoo estándar | `17.0.1.0` | `iap_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `iap_extract` | Odoo estándar | `17.0.1.0` | `iap_extract` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `iap_mail` | Odoo estándar | `17.0.1.0` | `iap_mail` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `import_initial_account_move` | Personalizado/externo | `17.0.17.0` | `import_initial_account_move` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `jh_sales_subscription` | Personalizado/externo | `17.0.0.8.0` | `jh_sales_subscription` | installed / `19.0.1.1.1` | `19.0.1.1.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `knowledge` | Odoo estándar | `17.0.1.0` | `knowledge` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `l10n_es` | Odoo estándar | `17.0.5.2` | `l10n_es` | installed / `19.0.5.4` | `5.4` | sí | ESTANDAR CARGADO |
| `l10n_es_account_statement_import_n43` | OCA | `17.0.1.0.1` | `l10n_es_account_statement_import_n43` | installed / `17.0.1.0.1` | `ausente` | no | FALTA FUENTE V19 |
| `l10n_es_aeat` | OCA | `17.0.2.0.1` | `l10n_es_aeat` | installed / `19.0.1.2.8` | `19.0.1.2.8` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_aeat_mod111` | OCA | `17.0.1.0.0` | `l10n_es_aeat_mod111` | installed / `17.0.1.0.0` | `ausente` | no | FALTA FUENTE V19 |
| `l10n_es_aeat_mod123` | OCA | `17.0.1.1.0` | `l10n_es_aeat_mod123` | installed / `17.0.1.1.0` | `ausente` | no | FALTA FUENTE V19 |
| `l10n_es_aeat_mod303` | OCA | `17.0.1.5.1` | `l10n_es_aeat_mod303` | installed / `19.0.1.0.2` | `19.0.1.0.2` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_aeat_mod347` | OCA | `17.0.1.0.1` | `l10n_es_aeat_mod347` | installed / `19.0.1.0.3` | `19.0.1.0.3` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_aeat_mod349` | OCA | `17.0.1.0.2` | `l10n_es_aeat_mod349` | installed / `17.0.1.0.2` | `ausente` | no | FALTA FUENTE V19 |
| `l10n_es_aeat_mod390` | OCA | `17.0.1.2.0` | `l10n_es_aeat_mod390` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_edi_verifactu` | Odoo estándar | `17.0.1.0` | `l10n_es_edi_verifactu` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `l10n_es_facturae` | OCA | `17.0.1.0.0` | `l10n_es_facturae` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_mis_report` | OCA | `17.0.1.0.0` | `l10n_es_mis_report` | installed / `19.0.1.1.0` | `19.0.1.1.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_partner` | OCA | `17.0.1.0.0` | `l10n_es_partner` | installed / `19.0.1.0.3` | `19.0.1.0.3` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `l10n_es_reports` | Odoo estándar | `17.0.4.1` | `l10n_es_reports` | installed / `19.0.4.3` | `4.3` | sí | ESTANDAR CARGADO |
| `l10n_es_toponyms` | OCA | `17.0.1.0.0` | `l10n_es_toponyms` | installed / `17.0.1.0.0` | `ausente` | no | FALTA FUENTE V19 |
| `l10n_eu_oss` | Odoo estándar | `17.0.1.0` | `l10n_eu_oss` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `l10n_eu_oss_reports` | Odoo estándar | `17.0.1.0` | `l10n_eu_oss_reports` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `link_tracker` | Odoo estándar | `17.0.1.1` | `link_tracker` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `mail` | Odoo estándar | `17.0.1.15` | `mail` | installed / `19.0.1.19` | `1.19` | sí | ESTANDAR CARGADO |
| `mail_bot` | Odoo estándar | `17.0.1.2` | `mail_bot` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `mail_bot_hr` | Odoo estándar | `17.0.1.0` | `mail_bot_hr` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mail_enterprise` | Odoo estándar | `17.0.1.0` | `mail_enterprise` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `mail_mobile` | Odoo estándar | `17.0.1.1` | `mail_mobile` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `miac_custom_reports` | Personalizado/externo | `17.0.17.0` | `miac_custom_reports` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_line_subscription` | Personalizado/externo | `17.0.17.0` | `miac_line_subscription` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_picking_always_return` | Personalizado/externo | `17.0.17.0` | `miac_picking_always_return` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_purchase_pricelist_menu` | Personalizado/externo | `17.0.17.0` | `miac_purchase_pricelist_menu` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_purchase_to_invoice` | Personalizado/externo | `17.0.17.0` | `miac_purchase_to_invoice` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_quantity_commission` | Personalizado/externo | `17.0.17.0` | `miac_quantity_commission` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_renovation_subscription` | Personalizado/externo | `17.0.17.0` | `miac_renovation_subscription` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `miac_sale_purchase_notification` | Personalizado/externo | `17.0.17.0` | `miac_sale_purchase_notification` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `microsoft_outlook` | Odoo estándar | `17.0.1.1` | `microsoft_outlook` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `mis_builder` | OCA | `17.0.1.0.0` | `mis_builder` | installed / `19.0.1.2.1` | `19.0.1.2.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `mrp` | Odoo estándar | `17.0.2.0` | `mrp` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `mrp_account` | Odoo estándar | `17.0.1.0` | `mrp_account` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_accountant` | Odoo estándar | `17.0.1.0` | `mrp_accountant` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_account_enterprise` | Odoo estándar | `17.0.1.0` | `mrp_account_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_product_expiry` | Odoo estándar | `17.0.1.0` | `mrp_product_expiry` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_repair` | Odoo estándar | `17.0.1.0` | `mrp_repair` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_workorder` | Odoo estándar | `17.0.1.0` | `mrp_workorder` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_workorder_expiry` | Odoo estándar | `17.0.1.0` | `mrp_workorder_expiry` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `mrp_workorder_hr_account` | Odoo estándar | `17.0.1.0` | `mrp_workorder_hr_account` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `onboarding` | Odoo estándar | `17.0.1.2` | `onboarding` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `partner_autocomplete` | Odoo estándar | `17.0.1.1` | `partner_autocomplete` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `partner_manual_rank` | OCA | `17.0.1.0.0` | `partner_manual_rank` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `payment` | Odoo estándar | `17.0.2.0` | `payment` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `payment_stripe` | Odoo estándar | `17.0.2.0` | `payment_stripe` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `phone_validation` | Odoo estándar | `17.0.2.1` | `phone_validation` | installed / `19.0.2.1` | `2.1` | sí | ESTANDAR CARGADO |
| `portal` | Odoo estándar | `17.0.1.0` | `portal` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `portal_rating` | Odoo estándar | `17.0.1.0` | `portal_rating` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `privacy_lookup` | Odoo estándar | `17.0.1.0` | `privacy_lookup` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `product` | Odoo estándar | `17.0.1.2` | `product` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `product_expiry` | Odoo estándar | `17.0.1.0` | `product_expiry` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `product_margin` | Odoo estándar | `17.0.1.0` | `product_margin` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `project` | Odoo estándar | `17.0.1.3` | `project` | installed / `19.0.1.4` | `1.4` | sí | ESTANDAR CARGADO |
| `project_account` | Odoo estándar | `17.0.1.0` | `project_account` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `project_account_asset` | Odoo estándar | `17.0.1.0` | `project_account_asset` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_enterprise` | Odoo estándar | `17.0.1.0` | `project_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_enterprise_hr` | Odoo estándar | `17.0.1.0` | `project_enterprise_hr` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_holidays` | Odoo estándar | `17.0.1.0` | `project_holidays` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_mrp` | Odoo estándar | `17.0.1.0` | `project_mrp` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_purchase` | Odoo estándar | `17.0.1.0` | `project_purchase` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_sale_subscription` | Odoo estándar | `17.0.1.0` | `project_sale_subscription` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `project_sms` | Odoo estándar | `17.0.1.0` | `project_sms` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `project_todo` | Odoo estándar | `17.0.1.0` | `project_todo` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `purchase` | Odoo estándar | `17.0.1.2` | `purchase` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `purchase_mrp` | Odoo estándar | `17.0.1.0` | `purchase_mrp` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `purchase_no_group_supplier` | Personalizado/externo | `17.0.17.0` | `purchase_no_group_supplier` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `purchase_stock` | Odoo estándar | `17.0.1.2` | `purchase_stock` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `quality` | Odoo estándar | `17.0.1.0` | `quality` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `queue_job` | OCA | `17.0.1.5.3` | `queue_job` | installed / `19.0.2.1.6` | `19.0.2.1.6` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `rating` | Odoo estándar | `17.0.1.1` | `rating` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `repair` | Odoo estándar | `17.0.1.0` | `repair` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `report_qweb_parameter` | OCA | `17.0.1.0.1` | `report_qweb_parameter` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `report_xlsx` | OCA | `17.0.1.0.1` | `report_xlsx` | installed / `19.0.1.0.2` | `19.0.1.0.2` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `report_xml` | OCA | `17.0.1.0.0` | `report_xml` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `resource` | Odoo estándar | `17.0.1.1` | `resource` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `sale` | Odoo estándar | `17.0.1.2` | `sale` | installed / `19.0.1.2` | `1.2` | sí | ESTANDAR CARGADO |
| `sale_account_accountant` | Odoo estándar | `17.0.1.0` | `sale_account_accountant` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_async_emails` | Odoo estándar | `17.0.1.0` | `sale_async_emails` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `sale_commission` | OCA | `17.0.1.0.0` | `sale_commission_oca` | installed / `19.0.1.0.1` | `19.0.1.0.1` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `sale_commission_salesman` | OCA | `17.0.1.0.1` | `sale_commission_salesman` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `sale_crm` | Odoo estándar | `17.0.1.0` | `sale_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_management` | Odoo estándar | `17.0.1.0` | `sale_management` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_mrp` | Odoo estándar | `17.0.1.0` | `sale_mrp` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_order_type` | OCA | `17.0.1.0.2` | `sale_order_type` | installed / `19.0.1.6.0` | `19.0.1.6.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `sale_pdf_quote_builder` | Odoo estándar | `17.0.1.0` | `sale_pdf_quote_builder` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `sale_product_configurator` | Odoo estándar | `17.0.1.0` | `sale_product_configurator` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `sale_product_template_tags` | OCA | `17.0.1.0.0` | `sale_product_template_tags` | installed / `17.0.1.0.0` | `ausente` | no | Sustitucion estandar prevista; transicion de metadatos pendiente |
| `sale_project` | Odoo estándar | `17.0.1.0` | `sale_project` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `sale_project_stock` | Odoo estándar | `17.0.1.0` | `sale_project_stock` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_purchase` | Odoo estándar | `17.0.1.0` | `sale_purchase` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_purchase_lot` | Personalizado/externo | `17.0.17.0` | `sale_purchase_lot` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `sale_purchase_stock` | Odoo estándar | `17.0.1.0` | `sale_purchase_stock` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_service` | Odoo estándar | `17.0.1.0` | `sale_service` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `sale_sms` | Odoo estándar | `17.0.1.0` | `sale_sms` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sales_team` | Odoo estándar | `17.0.1.1` | `sales_team` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `sale_stock` | Odoo estándar | `17.0.1.0` | `sale_stock` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sale_subscription` | Odoo estándar | `17.0.1.1` | `sale_subscription` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `sale_subscription_start_date` | Personalizado/externo | `17.0.17.0` | `sale_subscription_start_date` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `sale_subscription_stock` | Odoo estándar | `17.0.1.0` | `sale_subscription_stock` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `sms` | Odoo estándar | `17.0.3.0` | `sms` | installed / `19.0.3.0` | `3.0` | sí | ESTANDAR CARGADO |
| `snailmail` | Odoo estándar | `17.0.0.4` | `snailmail` | installed / `19.0.0.4` | `0.4` | sí | ESTANDAR CARGADO |
| `snailmail_account` | Odoo estándar | `17.0.0.1` | `snailmail_account` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `snailmail_account_followup` | Odoo estándar | `17.0.1.0` | `snailmail_account_followup` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `social_media` | Odoo estándar | `17.0.0.1` | `social_media` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `spreadsheet` | Odoo estándar | `17.0.1.0` | `spreadsheet` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_account` | Odoo estándar | `17.0.1.0` | `spreadsheet_account` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_account` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_account` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_account_accountant` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_account_accountant` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_crm` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_documents` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_documents` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_edition` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_edition` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_mrp_account` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_mrp_account` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_purchase` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_purchase` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `spreadsheet_dashboard_purchase_stock` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_purchase_stock` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_sale` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_sale` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_sale_subscription` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_sale_subscription` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_stock` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_stock` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_stock_account` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_stock_account` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_website_sale` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_website_sale` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_dashboard_website_sale_slides` | Odoo estándar | `17.0.1.0` | `spreadsheet_dashboard_website_sale_slides` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `spreadsheet_edition` | Odoo estándar | `17.0.1.0` | `spreadsheet_edition` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock` | Odoo estándar | `17.0.1.1` | `stock` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `stock_account` | Odoo estándar | `17.0.1.1` | `stock_account` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `stock_accountant` | Odoo estándar | `17.0.1.0` | `stock_accountant` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_account_enterprise` | Odoo estándar | `17.0.1.0` | `stock_account_enterprise` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `stock_barcode` | Odoo estándar | `17.0.1.0` | `stock_barcode` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_barcode_mrp` | Odoo estándar | `17.0.1.0` | `stock_barcode_mrp` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_barcode_picking_batch` | Odoo estándar | `17.0.1.0` | `stock_barcode_picking_batch` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_barcode_product_expiry` | Odoo estándar | `17.0.1.0` | `stock_barcode_product_expiry` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_delivery` | Odoo estándar | `17.0.1.0` | `stock_delivery` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_enterprise` | Odoo estándar | `17.0.1.0` | `stock_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_picking_batch` | Odoo estándar | `17.0.1.0` | `stock_picking_batch` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `stock_picking_imgs` | Personalizado/externo | `17.0.17.0` | `stock_picking_imgs` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `stock_sms` | Odoo estándar | `17.0.1.0` | `stock_sms` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `studio_customization` | Personalizado/externo | `` | `studio_customization` | installed / `19.0.1.0` | `ausente` | no | Studio: metadatos en BD, no requiere carpeta de addon |
| `subscription_date_lines` | Personalizado/externo | `17.0.17.0` | `subscription_date_lines` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `theme_buzzy` | Personalizado/externo | `17.0.1.0.0` | `theme_buzzy` | installed / `19.0.1.0.0` | `1.0.0` | sí | Tema cargado; version sin serie, compatibilidad web pendiente |
| `uom` | Odoo estándar | `17.0.1.0` | `uom` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `utm` | Odoo estándar | `17.0.1.1` | `utm` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `voip` | Odoo estándar | `17.0.2.0` | `voip` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `voip_crm` | Odoo estándar | `17.0.1.0` | `voip_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web` | Odoo estándar | `17.0.1.0` | `web` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_cohort` | Odoo estándar | `17.0.1.0` | `web_cohort` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `web_editor` | Odoo estándar | `17.0.1.0` | `web_editor` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `web_enterprise` | Odoo estándar | `17.0.1.0` | `web_enterprise` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_gantt` | Odoo estándar | `17.0.2.0` | `web_gantt` | installed / `19.0.2.0` | `2.0` | sí | ESTANDAR CARGADO |
| `web_grid` | Odoo estándar | `17.0.0.1` | `web_grid` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `web_hierarchy` | Odoo estándar | `17.0.1.0` | `web_hierarchy` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_map` | Odoo estándar | `17.0.1.0` | `web_map` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_mobile` | Odoo estándar | `17.0.1.0` | `web_mobile` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website` | Odoo estándar | `17.0.1.0` | `website` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_appointment` | Odoo estándar | `17.0.1.0` | `website_appointment` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_appointment_account_payment` | Odoo estándar | `17.0.1.0` | `website_appointment_account_payment` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_appointment_crm` | Odoo estándar | `17.0.1.0` | `website_appointment_crm` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_appointment_sale` | Odoo estándar | `17.0.1.0` | `website_appointment_sale` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_crm` | Odoo estándar | `17.0.2.1` | `website_crm` | installed / `19.0.2.1` | `2.1` | sí | ESTANDAR CARGADO |
| `website_crm_sms` | Odoo estándar | `17.0.1.0` | `website_crm_sms` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_documents` | Odoo estándar | `17.0.1.0` | `website_documents` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_enterprise` | Odoo estándar | `17.0.1.0` | `website_enterprise` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `website_form_project` | Odoo estándar | `17.0.1.0` | `website_form_project` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `website_knowledge` | Odoo estándar | `17.0.1.0` | `website_knowledge` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_links` | Odoo estándar | `17.0.1.0` | `website_links` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_mail` | Odoo estándar | `17.0.0.1` | `website_mail` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `website_partner` | Odoo estándar | `17.0.0.1` | `website_partner` | installed / `19.0.0.1` | `0.1` | sí | ESTANDAR CARGADO |
| `website_payment` | Odoo estándar | `17.0.1.0` | `website_payment` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_profile` | Odoo estándar | `17.0.1.0` | `website_profile` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_sale` | Odoo estándar | `17.0.1.1` | `website_sale` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |
| `website_sale_dashboard` | Odoo estándar | `17.0.1.0` | `website_sale_dashboard` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_sale_product_configurator` | Odoo estándar | `17.0.1.0` | `website_sale_product_configurator` | ausente / `` | `ausente` | no | ESTANDAR: REVISAR CAMBIO DE NOMBRE/FUSION |
| `website_sale_slides` | Odoo estándar | `17.0.1.0` | `website_sale_slides` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_sale_stock` | Odoo estándar | `17.0.1.0` | `website_sale_stock` | installed / `19.0.1.0` | `sin serie` | sí | ESTANDAR CARGADO |
| `website_sale_subscription` | Odoo estándar | `17.0.1.0` | `website_sale_subscription` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_slides` | Odoo estándar | `17.0.2.7` | `website_slides` | installed / `19.0.2.7` | `2.7` | sí | ESTANDAR CARGADO |
| `website_sms` | Odoo estándar | `17.0.1.0` | `website_sms` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `website_studio` | Odoo estándar | `17.0.1.0` | `website_studio` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_studio` | Odoo estándar | `17.0.1.0` | `web_studio` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_tour` | Odoo estándar | `17.0.0.1` | `web_tour` | installed / `19.0.1.0` | `1.0` | sí | ESTANDAR CARGADO |
| `web_tree_many2one_clickable` | OCA | `17.0.1.0.0` | `web_tree_many2one_clickable` | installed / `19.0.1.0.0` | `19.0.1.0.0` | sí | FUENTE V19, INSTALADO Y CARGADO |
| `web_unsplash` | Odoo estándar | `17.0.1.1` | `web_unsplash` | installed / `19.0.1.1` | `1.1` | sí | ESTANDAR CARGADO |

## Revalidación después de incorporar las fuentes OCA

12/10/2026: se volvió a consultar la base V17 en directo; sus **317 módulos
instalados** coinciden con la auditoría completa anterior. Se contrastaron sus
destinos con las carpetas actuales y los estados/versiones reales de V19:

- **Cero fuentes V19 ausentes** entre los addons de origen que se conservarán.
- Cierre recursivo de **130 módulos/dependencias**, sin fuentes ausentes.
- Los 15 módulos recién incorporados continúan con versión V17 en la base:
  requieren actualización; la copia de archivos no ejecutó sus migraciones.
- `hr_commission_oca` está disponible en el repo, versión `19.0.1.0.0`, pero
  sigue `uninstalled`: requiere instalación y correspondencia con HR antiguo.
- Permanecen revisiones de namespaces, sustituciones/exclusiones y tema web,
  detalladas en la auditoría. No se convierten en descargas nuevas por este control.
- No se carga un registro nuevo con estos addons sin actualizar primero el
  esquema: incorporar código y tener filas installed no prueba funcionamiento.
- No se instaló/actualizó ningún addon ni se modificaron datos o Excel. PostgreSQL
  V17 se volvió a detener después de la lectura, conservando su estado inicial.

Evidencia: `C:\Proyectos FL\DAM\miac_v19_migrada\logs\inventory_after_oca_download.json`.
