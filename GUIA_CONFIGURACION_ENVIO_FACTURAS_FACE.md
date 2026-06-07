# Guía de configuración: envío de facturas a FACe desde Odoo

Esta guía explica, paso a paso, qué hay que configurar para que las facturas a administraciones públicas se envíen automáticamente a **FACe** (la plataforma oficial del Estado para recibir facturas electrónicas).

Está pensada para **personas de administración, contabilidad o gestión**, no para informáticos.

---

## ¿Qué es FACe y qué hace Odoo?

- **FACe** es la web del Estado donde las empresas envían facturas a organismos públicos (ministerios, consejerías, ayuntamientos, etc.).
- **Odoo** puede preparar la factura en el formato correcto, firmarla con el certificado digital de la empresa y enviarla a FACe **al confirmar la factura**, sin tener que subir archivos a mano en la web.

Para que esto funcione, hay que completar **5 configuraciones**. Si falta alguna, el envío no se realizará o fallará.

---

## Antes de empezar: tenga a mano

- El **certificado digital de la empresa** (el mismo tipo que se usa para trámites electrónicos con Hacienda).
- La **contraseña** de ese certificado.
- Un **correo electrónico** de la empresa donde quieran recibir avisos de FACe (por ejemplo: facturacion@empresa.com).
- Los **datos completos** de cada cliente que sea administración pública (nombre, NIF, dirección, provincia).

---

## Paso 1 — Cargar el certificado digital en Odoo

### ¿Para qué sirve?

Odoo necesita el certificado de la empresa para **firmar** las facturas antes de enviarlas. Sin certificado, no se puede enviar nada a FACe.

### ¿Dónde se hace?

1. Entrar en Odoo.
2. Ir a **Contabilidad**.
3. Abrir **Configuración**.
4. Buscar la sección **AEAT** (Agencia Tributaria).
5. Entrar en **Certificados**.

### ¿Qué hay que hacer?

1. Pulsar **Nuevo** o **Crear**.
2. Poner un nombre fácil de reconocer (por ejemplo: *Certificado empresa 2026*).
3. Elegir la **empresa** que emite las facturas.
4. **Subir el archivo del certificado** (el que entrega la FNMT o el proveedor de certificados; suele ser un archivo con extensión `.pfx` o `.p12`).
5. Escribir la **contraseña** del certificado.
6. Guardar.

### ¿Cómo saber si está bien?

- El certificado aparece en la lista sin mensajes de error.
- Las fechas de validez cubren el periodo en el que va a facturar.
- La empresa seleccionada es la correcta.

> **Importante:** Si la empresa ya tenía certificado configurado para otros trámites con Hacienda en Odoo, puede ser el mismo. Si hay varias empresas en Odoo, cada una necesita el suyo.

---

## Paso 2 — Dar de alta el certificado en la web de FACe

### ¿Para qué sirve?

Configurar el certificado **solo en Odoo no basta**. FACe exige que la empresa esté registrada como emisor y que su certificado esté **aprobado en la plataforma del Estado**.

Este paso se hace **fuera de Odoo**, en la web oficial de FACe.

### ¿Entorno de pruebas o real?

| Situación | Web a utilizar |
|-----------|----------------|
| **Primeras pruebas** (recomendado) | https://se-face.redsara.es |
| **Facturación real** (cuando todo funcione) | https://face.gob.es |

> Empiece siempre en **pruebas**. Las facturas enviadas allí no tienen validez oficial.

### ¿Qué hay que hacer?

1. Entrar en la web de FACe con el **certificado digital**.
2. Buscar la sección de **Integradores** o **Gestión de certificados**.
3. Si es la primera vez, solicitar el **alta como empresa emisora / integrador** (FACe puede pedir un trámite y confirmarlo por correo).
4. Cuando esté aprobado, **subir la parte pública del certificado** (FACe indica cómo hacerlo; normalmente piden el contenido del certificado sin la clave privada).

### ¿Cómo saber si está bien?

- FACe confirma que el certificado está **activo** o **validado**.
- El certificado registrado en FACe es **el mismo** que se subió en Odoo (Paso 1).
- Se está usando el **mismo entorno** en FACe y en Odoo (pruebas con pruebas; real con real).

> **Ayuda oficial del Estado:** https://administracionelectronica.gob.es/PAe/FACE/altaintegrador

---

## Paso 3 — Configurar los datos de la empresa en Odoo

### ¿Para qué sirve?

Indica a Odoo **cómo generar la factura electrónica** y **a qué correo** FACe enviará los avisos cuando la factura sea recibida, rechazada, etc.

### ¿Dónde se hace?

1. Ir a **Ajustes** (engranaje).
2. Entrar en **Empresas** o **Compañías**.
3. Abrir la ficha de **su empresa**.
4. Buscar la pestaña **Facturae** o **Factura electrónica**.

### ¿Qué hay que rellenar?

| Campo | Qué poner |
|-------|-----------|
| **Versión Facturae** | Dejar **3.2.2** (es la habitual; si ya aparece ese valor, no cambiarlo). |
| **Correo FACe** / **Email FACe** | Un correo real de la empresa donde quieran recibir avisos de FACe (ejemplo: oficina@empresa.com). |

### ¿Cómo saber si está bien?

- El correo es de alguien que **lee el buzón** con regularidad.
- El NIF, la dirección y los datos fiscales de la empresa en Odoo son **correctos** (aparecerán en la factura electrónica).

> **Aclaración:** Este correo es para que **FACe avise a su empresa** del estado del envío. No es el correo del cliente (la administración pública).

---

## Paso 4 — Indicar a Odoo si está en pruebas o en producción

### ¿Para qué sirve?

FACe tiene **dos entornos separados**: uno para **probar** y otro para **facturación real**. Odoo debe conectarse al entorno correcto.

Este ajuste lo suele hacer **alguien con acceso técnico** o el administrador de Odoo. Si usted no ve el menú descrito abajo, pídaselo a su proveedor informático.

### ¿Dónde se hace?

1. Activar el **modo administrador avanzado** (si no lo tiene, pídalo a informática).
2. Ir a **Ajustes → Técnico → Parámetros del sistema**.
3. Buscar un parámetro relacionado con **FACe** o **face.ws**.

### ¿Qué valor debe tener?

| Situación | Dirección que debe configurarse |
|-----------|----------------------------------|
| **Pruebas** (recomendado al inicio) | `https://se-face-webservice.redsara.es/facturasspp2?wsdl` |
| **Producción** (facturación real) | `https://webservice.face.gob.es/facturasspp2?wsdl` |

### ¿Cómo saber si está bien?

- Para las **primeras pruebas**, la dirección debe ser la de **redsara** (pruebas).
- Cuando todo funcione y el certificado esté dado de alta en **face.gob.es**, se cambia a la dirección de **producción**.

> **Importante:** No mezcle entornos. Si prueba en redsara, el certificado y la configuración de FACe también deben ser de **pruebas**.

---

## Paso 5 — Configurar cada cliente que sea administración pública

### ¿Para qué sirve?

Odoo **solo envía a FACe** las facturas de clientes marcados correctamente. Si un organismo público no está bien configurado, la factura se crea en Odoo pero **no se envía** a FACe.

### ¿Dónde se hace?

1. Ir a **Contactos**.
2. Abrir la ficha del **organismo público** (ministerio, consejería, ayuntamiento, etc.).

### ¿Qué hay que activar y rellenar?

| Dato | Qué hacer |
|------|-----------|
| **Factura electrónica / Facturae** | **Activar** (marcar como sí). |
| **Forma de envío / Método de envío** | Elegir **FACe**. |
| **NIF / CIF** | Obligatorio. Debe ser el del organismo. |
| **País** | España. |
| **Provincia** | Obligatoria. |
| **Dirección completa** | Calle, código postal y ciudad. |

Repita esto para **cada** administración a la que facture por FACe.

### ¿Cómo saber si está bien?

- El contacto tiene **Factura electrónica = Sí** y **envío = FACe**.
- No faltan NIF, provincia ni dirección.
- Al confirmar una factura de ese cliente, Odoo debe intentar el envío (su informático puede comprobar que aparece el registro de envío).

### Facturas antiguas

Si la factura **ya estaba confirmada** antes de configurar FACe en el contacto, puede hacer falta un **envío manual** desde la propia factura (botón relacionado con Facturae / FACe). Consulte con su administrador de Odoo.

---

## Cómo hacer la primera prueba

Cuando estén completos los 5 pasos anteriores:

1. Crear una **factura de cliente** normal en Odoo.
2. Elegir un contacto que ya tenga **Facturae + FACe** configurado.
3. Rellenar las líneas de la factura con normalidad.
4. **Confirmar** la factura.

### ¿Qué debería ocurrir?

- Odoo prepara y envía la factura a FACe.
- En la factura debería aparecer un **estado de envío** (por ejemplo, indicando que fue recibida correctamente).
- Debería guardarse un **número de registro** de FACe.

### Si algo falla

| Problema | Posible causa |
|----------|----------------|
| La factura se confirma pero no se envía | El cliente no tiene **FACe** marcado como forma de envío. |
| Error de certificado | Certificado no cargado en Odoo, caducado o no dado de alta en la web de FACe. |
| Error de conexión | Odoo apunta al entorno incorrecto (pruebas vs producción). |
| Error de datos | Faltan NIF, provincia o dirección en el cliente o en la empresa. |

En caso de error, anote el **mensaje que muestra Odoo** y compártalo con su administrador o proveedor de Odoo.

---

## Resumen: checklist para marcar

Marque cada casilla cuando esté hecho:

```
PASO 1 — Certificado en Odoo
[ ] Certificado de la empresa subido en Contabilidad → AEAT → Certificados
[ ] Contraseña correcta y certificado vigente

PASO 2 — Certificado en la web FACe
[ ] Alta como emisor completada en la web de FACe
[ ] Certificado aprobado en FACe (entorno de pruebas al inicio)

PASO 3 — Datos de la empresa
[ ] Versión Facturae: 3.2.2
[ ] Correo FACe rellenado

PASO 4 — Entorno de conexión (informática)
[ ] Odoo conectado al entorno de PRUEBAS para las primeras pruebas
[ ] Cambio a PRODUCCIÓN solo cuando todo esté validado

PASO 5 — Clientes (administraciones públicas)
[ ] Factura electrónica activada
[ ] Forma de envío: FACe
[ ] NIF, provincia y dirección completos

PRUEBA
[ ] Factura de prueba confirmada
[ ] Envío recibido correctamente por FACe
```

---

## Datos que conviene pedir a cada administración pública

Para configurar bien el contacto en Odoo, solicite al cliente público:

- Nombre oficial del organismo
- NIF / CIF
- Dirección fiscal completa
- Provincia
- Confirmación de que reciben facturas por **FACe**
- Cualquier código administrativo que exijan (si lo conocen)

---

## Preguntas frecuentes

**¿Tengo que entrar en la web de FACe cada vez que emito una factura?**  
No. Una vez configurado todo, Odoo envía al confirmar la factura. FACe es solo para el registro inicial del certificado y, si hace falta, consultas puntuales.

**¿Puedo probar sin afectar a facturación real?**  
Sí. Use el entorno de **pruebas** (redsara) hasta que su informático y usted validen que todo funciona.

**¿El correo FACe lo recibe el cliente público?**  
No. Es el correo donde **FACe avisa a su empresa** sobre el estado del envío.

**¿Qué pasa si cambio de certificado?**  
Debe actualizarlo en Odoo (Paso 1) **y** volver a registrarlo en la web de FACe (Paso 2).

**¿Necesito configurar algo por cada factura?**  
No. Solo hay que configurar bien **una vez** la empresa, el certificado y cada **contacto** administración pública. Después, cada factura confirmada a ese contacto se enviará sola (si el sistema está bien configurado).

---

## Contacto de soporte

Si tras seguir esta guía el envío no funciona, facilite a su soporte técnico:

- Captura del **mensaje de error** en Odoo
- Nombre del **cliente** (administración) de la factura de prueba
- Confirmación de si están en entorno de **pruebas** o **producción**
- Fecha de caducidad del **certificado digital**

---

*Documento preparado para la configuración del envío automático de facturas a FACe desde Odoo.*
