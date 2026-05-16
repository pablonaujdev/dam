# Novedad: envío de factura por correo a múltiples destinatarios

## Descripción del problema

Al imprimir/enviar una factura por correo electrónico desde Odoo (**Imprimir / Enviar factura** o **Send & Print**), si en el campo **Destinatarios** se seleccionaban **varios contactos** (por ejemplo, el cliente de la factura más dos direcciones de correo adicionales), **solo uno de los destinatarios recibía el correo** en la práctica. Concretamente, el comportamiento observado era que **únicamente el último destinatario de la lista** recibía el mensaje con la factura adjunta; el resto no recibía ningún correo.

### Síntomas

- El usuario selecciona **varios destinatarios** en el wizard de “Imprimir / Enviar factura”.
- Se confirma el envío sin errores.
- **Solo uno de los destinatarios** (en los casos reportados, el último de la lista) recibe el correo con la factura en PDF.
- Los demás destinatarios **no reciben** el correo, aunque figuren correctamente en el campo Destinatarios.

---

## Causa técnica del error

El comportamiento se debía a cómo el módulo estándar de **Facturación (account)** agrupa los destinatarios al generar los correos de notificación:

1. **Destinatarios “adicionales” en un solo grupo**  
   Los contactos que el usuario añade manualmente en “Destinatarios” (distintos del partner principal de la factura) se trataban en Odoo como un **único grupo** de notificación llamado `additional_intended_recipient`.

2. **Un solo `mail.mail` para todos los adicionales**  
   Para ese grupo se creaba **una sola** ficha de correo saliente (`mail.mail`) con **varios** destinatarios asociados (`recipient_ids`: por ejemplo, 2 o 3 IDs de contacto).

3. **Envío efectivo solo a uno**  
   En el flujo de envío, cuando un mismo `mail.mail` tiene más de un destinatario, el sistema debería enviar un correo por cada uno. En la práctica, en este flujo **solo se estaba enviando un correo** (al que se percibía como “el último” de la lista), por lo que el resto de destinatarios adicionales no recibía el mensaje.

Por tanto, la novedad no estaba en la selección de destinatarios en el wizard (ahí los 3 destinatarios se guardaban y transmitían bien), sino en la **forma en que se generaban y enviaban los correos** a partir de ese grupo único de “destinatarios adicionales”.

---

## Solución implementada

La corrección se ha implementado en el módulo **jh_sales_subscription** (personalización MIAC - DAM), heredando el comportamiento del modelo `account.move` (facturas):

- **Antes:** Un solo grupo para todos los destinatarios adicionales → un solo `mail.mail` con varios `recipient_ids` → en la práctica solo un envío.
- **Ahora:** Se define **un grupo de notificación por cada destinatario adicional**. Así, cada uno de esos contactos tiene su propia ficha de correo (`mail.mail`) con **un único** destinatario, y el sistema envía **un correo por cada uno**.

### Cambio técnico (resumen)

- **Archivo:** `jh_sales_subscription/models/jh_account_move.py`
- **Méodo:** Sobrescritura de `_notify_get_recipients_groups` para facturas (`account.move`).
- **Lógica:** En lugar de insertar un único grupo `additional_intended_recipient` para todos los contactos añadidos manualmente, se elimina ese grupo y se insertan **tantos grupos como destinatarios adicionales** haya (uno por cada ID de partner), manteniendo el mismo enlace a la factura y permisos de acceso. Cada grupo genera su propio `mail.mail` con un solo destinatario, garantizando que cada uno reciba su correo.

Con esto se mantiene la funcionalidad estándar (incluido el enlace a la factura para cada destinatario) y se corrige el envío a múltiples destinatarios.

---

## Cómo comprobar que está solucionado

1. Abrir una **factura de cliente** confirmada.
2. Pulsar **Imprimir / Enviar factura** (o **Send & Print**).
3. En el asistente, elegir plantilla de correo si aplica y en el campo **Destinatarios** añadir **varios contactos** con email válido (por ejemplo: cliente de la factura + 2 contactos más).
4. Pulsar **Enviar e imprimir**.
5. **Comprobación:** Cada uno de los destinatarios seleccionados debe recibir **un correo** con la factura en PDF. Si todos reciben el correo, la novedad queda resuelta.

---

## Resumen para el cliente

**Problema:** Al enviar la factura por correo a varios destinatarios, solo uno recibía el correo.  
**Causa:** El sistema generaba un único correo para todos los destinatarios “adicionales” y en la práctica solo se enviaba a uno.  
**Solución:** Se ha ajustado la lógica en el módulo jh_sales_subscription para que se genere y envíe **un correo por cada destinatario** seleccionado, de modo que todos reciban la factura por email.  
**Verificación:** Enviar una factura a 2 o 3 destinatarios y confirmar que todos reciben el correo con el PDF adjunto.
