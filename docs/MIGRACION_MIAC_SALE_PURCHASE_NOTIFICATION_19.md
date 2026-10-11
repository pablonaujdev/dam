# MIAC — Avisos de compras de licencias en Odoo 19

## Resultado técnico

Migración implementada en `staging_v19`, versión `19.0.1.0.0`.
Instalación y actualización completadas en la base aislada `miac_v19`.
El 11 de octubre de 2026 se ejecutaron **56 pruebas, con 0 fallos y 0 errores**:

| Suite | Pruebas |
|---|---:|
| Avisos de licencias (`license_notification19`) | 20 |
| Odoo 19 `sale_purchase:TestSalePurchase` | 9 |
| Separación de compras (`no_group_purchase19`) | 17 |
| Regresiones de JH (`jh_migration19`) | 10 |

Fuentes utilizadas: respaldo Avannubo, instalación local de Odoo 19 y repositorio.
Sin búsquedas, descargas externas, commits ni cambios en el Excel de seguimiento.

## Comportamiento

- Se compara `purchase_line_ids` por venta antes y después de la confirmación nativa.
- Si existen líneas nuevas de productos recurrentes, se genera un aviso por venta.
- Reutilizar una compra en borrador con una nueva línea también genera el aviso.
- Las líneas anteriores, las reconfirmaciones sin líneas nuevas y los cambios
  posteriores de cantidades no generan avisos adicionales.
- Solo se consideran los vínculos originales `purchase_line_ids`. Una compra
  relacionada exclusivamente mediante referencias de inventario queda fuera.
- En confirmaciones múltiples, cada venta utiliza el destinatario de su compañía.
- La lectura elevada se limita a los vínculos de compra de líneas de ventas
  accesibles. No se elevan permisos de ventas, compañías ni contactos.
- Un destinatario ausente, un correo vacío, inválido o múltiple, o una plantilla
  ausente generan una nota interna y conservan la venta y sus compras.
- Los errores de acceso al destinatario, renderizado o creación del correo se
  revierten mediante un savepoint del intento de aviso. Se registra el detalle
  en el log y una nota interna; no se revierte la confirmación ni sus compras.
- Un aviso fallido no impide procesar el aviso de la siguiente venta del lote.
- Las notas internas no notifican a seguidores ni envían correos.

## Plantilla y configuración

Se conservan el campo `res.company.notify_purchase_license_id`, el XML ID de su
vista y `email_template_sale_purchase_license`, con `noupdate="1"`.
El campo se muestra junto al correo en el formulario nativo de compañía.
Se verificó en el navegador, en español, su ubicación y el selector nativo de
contactos, sin guardar cambios en la configuración. Evidencia:
`C:\Proyectos FL\DAM\miac_v19\license-notification19-company-form-20261011.png`.

La plantilla distribuida usa `{{ ... }}`, saluda al destinatario configurado y
selecciona su idioma. Conserva el asunto, el mensaje de compra de licencias y la
firma del comercial, con traducción española.

En tiempo de ejecución se sustituye la lista de destinatarios por el único
contacto configurado y se vacían `email_to` y `email_cc`, también cuando una
plantilla personalizada propone otros destinatarios. `force_send=False` utiliza
la cola nativa; no se ejecuta SMTP en la confirmación.

**Plantillas existentes:** la actualización no reescribe sus textos, idioma,
saludo ni expresiones antiguas. La prueba con `${...}` demuestra que el
destinatario de envío se corrige mediante `email_values`; no constituye una
conversión automática de todas las expresiones o contenido personalizado.
Su revisión y adaptación en la copia real de MIAC sigue pendiente.

## Archivos incorporados y adaptados

- `__manifest__.py`: versión, descripción, autoría/licencia y dependencias
  directas `sale_purchase`, `sale_subscription` y `mail`.
- `models/res_company.py`: etiqueta y ayuda de dos líneas del campo conservado.
- `models/sale_order.py`: detección por venta, cola, permisos y gestión de errores.
- `views/res_company_view.xml`: XPath compatible con el formulario de Odoo 19.
- `datas/sale_purchase_email_template.xml`: plantilla QWeb y destinatario/idioma.
- `i18n/es.po`: traducción del campo, ayuda, mensajes y plantilla.
- `tests/`: 20 pruebas funcionales sobre los flujos descritos.
- Inicializadores e icono originales; se excluyeron archivos compilados.

No se añaden campos de control, modelos, crons, permisos ni dependencias MIAC.

## Evidencia reproducible

Validación estática:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py --module miac_sale_purchase_notification
```

Resultado: 37 módulos en el grafo de dependencias; Python/XML válidos y vista
heredada compuesta correctamente contra las fuentes locales de Odoo 19.

Instalación inicial: `-i miac_sale_purchase_notification`.
Actualización y ejecución final:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' run --rm -T web -d miac_v19 -u miac_sale_purchase_notification,sale_purchase,purchase_no_group_supplier,jh_sales_subscription --test-enable --test-tags license_notification19,/sale_purchase:TestSalePurchase,no_group_purchase19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/license-notification19-final-tests-20261011.log
```

Log final conservado en:
`C:\Proyectos FL\DAM\miac_v19\license-notification19-final-tests-20261011.log`.

Las pruebas incluyen destinatarios por compañía, vendedor sin acceso a Compras,
contacto restringido, compras nuevas y reutilizadas, reconfirmación, aumento de
cantidades que crea compras posteriores, correo parcial revertido, plantilla
ausente o defectuosa, texto personalizado, saludo/idioma español y firma.
Un mock de `ir.mail_server.send_email` falla si se intenta SMTP durante estas
pruebas propias. Los correos generados se verifican en estado `outgoing`.

## Respaldo y entorno

Antes de instalar se respaldaron base y filestore:

- `C:\Proyectos FL\DAM\miac_v19\notification19-before-20261011.dump`
- `C:\Proyectos FL\DAM\miac_v19\notification19-filestore-before-20261011.tar.gz`

Se desactivaron mediante ORM las 39 tareas que seguían marcadas activas en el
ensayo, además de mantener `max_cron_threads=0`. Al finalizar: 0 tareas activas,
0 servidores de correo activos y SMTP restringido a `127.0.0.1:1`.
El módulo figura instalado con versión `19.0.1.0.0`; los contenedores de Odoo y
PostgreSQL quedan iniciados y saludables.

Las pruebas se revierten automáticamente. No se han enviado correos reales ni
ejecutado conversiones sobre una base del cliente.

## Pendiente de aceptación con datos reales

Validar los destinatarios, su acceso y las plantillas personalizadas existentes
en una copia migrada de MIAC. La aceptación de esa copia es independiente de
estas pruebas técnicas sobre la instalación aislada. No habilitar correo ni
tareas automáticas antes de su aceptación funcional.
