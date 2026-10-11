# Declaración responsable Avannubo en Odoo 19

Fecha: 2026-10-11. Rama: `staging_v19`.
Módulo: `avannubo_declaracion_responsable`, versión `19.0.1.0.0`.
Fuente: `C:\Proyectos FL\DAM\respaldo\addons\avannubo_declaracion_responsable`.
Referencia: instalación local Enterprise `19.0+e-20260105`.

## Implementación

- Incorporado el módulo sin `__pycache__` ni archivos compilados.
- Conservados nombre técnico, XML ID de la vista, autoría Avannubo y licencia AGPL-3.
- Nombre visible corregido a **Avannubo Declaración Responsable**.
- Manifest versionado una sola vez, con descripción funcional/técnica y dependencias
  directas de `base`, `base_setup` y `web`. Instalación manual y sin auto-install.
- Vista de `res.config.settings` adaptada a un bloque nativo después de Acerca de,
  con ancho completo para el texto. El XML ID existente no se ha renombrado.
- Firma con URL absoluta y dimensiones proporcionales.
- Extensión del navegador sobre `res_config_edition`, sin el prefijo antiguo `web.`
  ni el atributo antiguo `owl="1"`.
- Conservados literalmente los tres párrafos, la etiqueta del sello y el mensaje
  sobre el plan de facturación. Icono y firma coinciden byte a byte con el respaldo.
- No se añadieron modelos, campos, menús, ACL, automatizaciones ni dependencias Veri*Factu.

Archivos incorporados: `__init__.py`, `__manifest__.py`,
`views/res_config_settings_view.xml`,
`static/src/webclient/res_config_settings_template_view.xml`,
`static/description/icon.png` y `static/src/imgs/firma.png`.

## Validación

En el Docker aislado `miac_v19`:

- Instalación y actualización posterior: correctas, ambos procesos con salida 0.
- Versión instalada comprobada: `19.0.1.0.0`.
- Validador estático: grafo de 4 módulos, 2 Python, 1 XML y 1 vista compuesta.
- Verificados XML ID, dependencias, XPath y conservación literal del contenido.
- Ajustes abierto en el navegador: texto completo, firma cargada y legible,
  un único encabezado de declaración y un único mensaje del plan.
- Conservados edición Enterprise, vencimiento de la base, copyright y enlace de licencia.
- Recursos del navegador compilados y cargados; consola sin errores ni advertencias.
- Conservado el acceso nativo: menú y ACL de Ajustes para `base.group_system`;
  el único registro propio instalado es una vista heredada.
- Docker iniciado y saludable, correo sin servidores activos y `max_cron_threads=0`.
- `git diff --check`: correcto.

Comandos desde `C:\Proyectos FL\DAM\miac_v19`, deteniendo el servicio web durante
la instalación y la actualización:

```powershell
docker compose run --rm --no-deps web -i avannubo_declaracion_responsable --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/declaracion19-install-20261011.log
docker compose run --rm --no-deps web -u avannubo_declaracion_responsable --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/declaracion19-update-20261011.log
docker compose up -d web
```

Evidencias y respaldo previo en la misma carpeta Docker:

- `declaracion19-before-20261011.dump`.
- `declaracion19-before-20261011-filestore.tar.gz`.
- `declaracion19-install-20261011.log` y `declaracion19-update-20261011.log`.
- `declaracion19-ui-20261011.jpg`.

## Límites

La aceptación técnica se ha completado en el ensayo aislado. La revisión del contenido
firmado para entregar al cliente sigue siendo un trabajo separado de esta adaptación.
No se modificaron datos del cliente, el Excel ni los cambios pendientes de JH.
No se crearon commits ni se utilizaron fuentes externas.
