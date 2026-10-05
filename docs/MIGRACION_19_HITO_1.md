# Odoo 19 - Validacion del hito 1 (05/10/2026)

Rama revisada: `staging`. Alcance: `mis_builder`, `l10n_es_facturae` y
`l10n_es_aeat_mod390`. `jh_sales_subscription` queda pendiente y fuera de esta revision.

**Resultado: codigo preparado con todas sus dependencias de modulos; hito funcional
pendiente de instalacion y pruebas sobre una copia migrada de MIAC.**

Los tres modulos principales son versiones OCA 19.0 y coinciden byte a byte con las
carpetas aportadas por el usuario. Se incorporaron 11 dependencias OCA adicionales;
no se detecto necesidad de portar manualmente el codigo de estos tres modulos en
las comprobaciones estaticas. Esto no acredita la migracion de datos ni la
compatibilidad de las personalizaciones de otros modulos de MIAC.

## Dependencias incorporadas

| Modulo | Version | Procedencia |
| --- | --- | --- |
| `report_xlsx` | `19.0.1.0.2` | OCA/reporting-engine |
| `date_range` | `19.0.1.0.0` | OCA/server-ux |
| `account_payment_mode` | `19.0.1.1.0` | OCA/bank-payment |
| `l10n_es_partner` | `19.0.1.0.3` | download-l10n-spain |
| `base_bank_from_iban` | `19.0.1.0.1` | OCA/community-data-files |
| `base_iso3166` | `19.0.1.0.0` | OCA/community-data-files |
| `report_xml` | `19.0.1.0.1` | OCA/reporting-engine |
| `report_qweb_parameter` | `19.0.1.0.0` | OCA/reporting-engine |
| `l10n_es_aeat` | `19.0.1.2.8` | download-l10n-spain |
| `account_tax_balance` | `19.0.1.0.3` | OCA/account-financial-reporting |
| `l10n_es_aeat_mod303` | `19.0.1.0.2` | download-l10n-spain |

Las dependencias estandar se resuelven desde Odoo 19; no se copiaron al repositorio.
La cadena completa comprende 14 modulos OCA y 24 modulos estandar.

- MIS Builder: `report_xlsx` y `date_range`, ademas de `account` y `board`.
- Facturae: `account_payment_mode`, `l10n_es_partner`, `base_iso3166`, `report_xml`,
  `report_qweb_parameter` y `l10n_es_aeat`, ademas de `l10n_es` y `base_vat`.
- Modelo 390: `l10n_es_aeat_mod303` -> `l10n_es_aeat` -> `account_tax_balance`.
- `l10n_es_partner` requiere a su vez `base_bank_from_iban`.

## Comprobaciones realizadas

Referencia local: Odoo `19.0+e-20260105`, Python 3.12.3.

- Manifiestos 19.0 instalables y grafo completo de dependencias.
- Sintaxis de 212 archivos Python: sin errores.
- XML bien formado en 79 archivos: sin errores.
- 77 XML declarados en data/demo: validos frente al esquema de importacion de Odoo 19.
- Archivos data/demo y assets declarados: presentes.
- Los tres modulos aportados y las dependencias copiadas conservan el codigo OCA.
- Los manifiestos conservaron las versiones oficiales; no hubo ajustes de codigo
  Python/XML ni incrementos de version locales.

MIS Builder conserva una entrada heredada `qweb` hacia un archivo antiguo. El
widget actual esta declarado mediante `web.assets_backend` y sus archivos existen;
queda pendiente comprobar su carga y funcionamiento desde el navegador.

## Dependencias Python del entorno de destino

Se incorpora `requirements.txt` con las librerias declaradas por los manifiestos.
Instalarlas usando el Python del servidor/imagen Odoo 19 de destino:

```text
python -m pip install -r requirements.txt
```

La revision del Python de la instalacion local detecto dos bloqueos:

| Libreria | Requisito | Estado local |
| --- | --- | --- |
| Unidecode | `unidecode` | No instalada |
| schwifty | `schwifty==2024.4.0` | Instalada 2026.3.0; no cumple la version exacta |

Odoo 19 comprueba las restricciones de version declaradas en los manifiestos:
`schwifty` debe cumplir la version exigida por `base_bank_from_iban`. Instalar las
librerias en el entorno de destino y verificar alli; estos resultados locales no
prueban el estado del servidor de staging. No se instalaron ni sustituyeron
librerias globales en el PC durante esta revision.

## Condiciones para cerrar los tres componentes del hito

1. Preparar el entorno Odoo 19 y su `addons_path` para incluir este repositorio;
   instalar las librerias y resolver cualquier conflicto del entorno.
2. Instalar los tres modulos con sus dependencias en una base de ensayo y revisar
   registro, permisos, carga de vistas y assets. Esa instalacion valida carga
   limpia; despues se debe comprobar la copia de MIAC migrada desde 17.
3. MIS Builder: conservar informes, estilos, KPI y periodos; comparar saldos con
   MIAC y comprobar visualizacion, exportacion XLSX y PDF.
4. Facturae: conservar modos de pago, datos bancarios y contactos; generar XML de
   facturas y rectificativas representativas, comprobar esquema e importes y
   validar firma/certificado cuando se utilice.
5. AEAT 303/390: conservar configuraciones y mapas fiscales; comparar casillas y
   totales con el origen para un periodo cerrado y comprobar fichero de exportacion.
6. Obtener aceptacion funcional. El primer hito completo requiere ademas terminar
   y validar `jh_sales_subscription`, excluido expresamente de este trabajo.

La disponibilidad de codigo 19.0 no sustituye el proceso de upgrade ni garantiza
que datos/configuraciones de version 17 se preserven automaticamente. La presencia
de scripts de mantenimiento de 19.0 (por ejemplo en `l10n_es_partner`) tampoco
acredita una migracion completa de 17 a 19.

No se instalaron modulos, no se crearon ni migraron bases y no se modificaron datos.
El repositorio conserva otros modulos 17.0 ajenos a este alcance; no deben
considerarse ya migrados por esta incorporacion.

## Trazabilidad de las fuentes descargadas

Los repositorios externos fueron descargados de la rama OCA `19.0`, fijando el
commit para conservar una referencia reproducible. Solo se copiaron las carpetas
de modulos necesarias. Las descargas de l10n-spain y mis-builder aportadas por el
usuario se utilizaron directamente.

- [OCA/reporting-engine](https://github.com/OCA/reporting-engine/tree/b9e8c6cdd2d106614eddaf81bd78f487ae35db45): `b9e8c6cdd2d106614eddaf81bd78f487ae35db45`.
- [OCA/server-ux](https://github.com/OCA/server-ux/tree/f2485eef1437b7fd57e3d44a61537420bbf1b281): `f2485eef1437b7fd57e3d44a61537420bbf1b281`.
- [OCA/bank-payment](https://github.com/OCA/bank-payment/tree/fdd5d4040b235a4c688b2aec30611d57dd246b64): `fdd5d4040b235a4c688b2aec30611d57dd246b64`.
- [OCA/account-financial-reporting](https://github.com/OCA/account-financial-reporting/tree/b26d1233d3d24536e51dddef416939a6cbf9a1fc): `b26d1233d3d24536e51dddef416939a6cbf9a1fc`.
- [OCA/community-data-files](https://github.com/OCA/community-data-files/tree/6866ed6392b1c278a0ad44e3f9dbc11294d756dc): `6866ed6392b1c278a0ad44e3f9dbc11294d756dc`.
