# MIAC — Devoluciones de albaranes en Odoo 19

## Resultado

Implementado en `staging_v19`, versión **19.0.1.0.0**, con dependencia exclusiva
de `stock`. Instalación y actualización correctas en el Docker aislado `miac_v19`.
Se utilizaron únicamente el respaldo Avannubo, Odoo 19 local y el repositorio.

El 11 de octubre de 2026 pasaron **45 casos funcionales**:

| Suite | Casos |
|---|---:|
| `picking_return19`, pruebas nuevas | 16 |
| `stock:TestReturnPicking`, devoluciones nativas | 7 |
| `subscription_activation19`, activación de suscripciones | 12 |
| `jh_migration19`, regresiones JH | 10 |

Las siete pruebas nativas se repitieron además después de cargar todas las
extensiones MIAC, mediante `TestNativeReturnAfterMiac`. Esto asegura que lotes,
series, unidades y cambios se prueban también con los overrides instalados.
**52 ejecuciones aprobadas entre ambas corridas, sin fallos ni errores.**

## Comportamiento y cambios respecto a V17

| Estado del origen | Botón y devolución |
|---|---|
| Borrador (`draft`) | Oculto y bloqueado |
| Confirmado (`confirmed`) | Permitido |
| En espera (`waiting`) | Permitido |
| Preparado (`assigned`) | Permitido |
| Realizado (`done`) | Permitido |
| Cancelado (`cancel`) | Oculto y bloqueado |

La regla se aplica a entregas, recepciones y transferencias internas. Se conserva
el botón y el asistente de Odoo; no se añaden acciones ni permisos paralelos.

- Se elimina el cálculo de V17 que escribe temporalmente el estado como realizado.
- `_can_return()` llama a `super()` y amplía los estados permitidos.
- `_create_return()` vuelve a comprobar acceso y elegibilidad antes de copiar
  movimientos. Un asistente abierto no permite devolver un origen cancelado.
- Las cantidades comienzan en **cero**, como en Odoo 19. «Devolver todo» utiliza
  la cantidad nativa disponible, no la demanda del movimiento. En un pendiente
  sin cantidades reservadas puede quedar en cero y requerir captura manual.
- Crear la devolución no completa ni valida el origen ni la devolución. Odoo
  conserva sus reglas de confirmación, reservas y movimientos encadenados.
- Las ubicaciones, operación de retorno, unidades, lotes, series, vínculos con
  ventas/compras y exclusiones de movimientos cancelados/inventario siguen
  íntegramente el flujo nativo. «Devolver para cambio» conserva su funcionamiento.

Una devolución solicitada antes de completar el origen no acredita una entrega
o recepción realizada. Su validación posterior sigue siendo una decisión
operativa y aplicará las reglas normales de existencias de Odoo.

## Acceso y conservación

Se comprueba explícitamente el permiso de lectura del albarán antes de evaluar
su devolución. Durante las pruebas se detectó que el compute almacenado nativo
del asistente eleva permisos; el campo existente `product_return_moves` conserva
su estructura y cálculo, pero utiliza **`compute_sudo=False`**. No se crean
campos: se ajusta ese atributo y su ayuda para respetar el usuario y la compañía.

Las pruebas verifican el rechazo de un usuario de otra compañía incluso después
de leer el origen con administrador. Un usuario de Inventario autorizado puede
crear la devolución sin elevación de permisos.

Se conservan nombre técnico, autoría Avannubo, licencia AGPL-3, icono y XML ID
`stock_picking_view_form_inherit_always_return`. No hay conversiones ni cambios
automáticos de históricos. El código pendiente de `miac_sale_purchase_notification`
y su documentación mantuvieron su huella SHA-256 inicial sin modificaciones.

## Archivos y validación

Archivos incorporados/adaptados:

- `__manifest__.py`: versión, descripción y dependencia `stock`.
- `models/stock_picking.py`: acceso y extensión de `_can_return()`.
- `wizards/stock_picking_return.py`: validación antes de crear y compute sin sudo.
- `views/stock_picking_view.xml`: visibilidad del botón nativo.
- `i18n/es.po`: error de estado y ayuda del campo existente.
- `tests/`: 16 casos propios y repetición de las 7 pruebas nativas con MIAC.
- Inicializadores e icono; sin archivos compilados.

Validación estática:

```powershell
& 'C:\Program Files\Odoo 19.0e.20260105\python\python.exe' tools\validate_jh_odoo19.py --module miac_picking_always_return
```

Resultado: 18 módulos en el grafo de dependencias, Python/XML válidos y vista
heredada compuesta contra Odoo 19 local.

Instalación inicial mediante `-i miac_picking_always_return`. Corrida final:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' run --rm -T web -d miac_v19 -u miac_picking_always_return,stock,sale_subscription_start_date,jh_sales_subscription --test-enable --test-tags picking_return19,picking_native_return19,/stock:TestReturnPicking,subscription_activation19,jh_migration19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/picking-return19-final-tests-20261011.log
```

La ejecución registrada en ese log aprobó 45 pruebas. Tras habilitar el mecanismo
nativo `allow_inherited_tests_method` para descubrir los métodos heredados de
la clase de regresión, se ejecutaron las siete pruebas adicionales:

```powershell
docker compose -f 'C:\Proyectos FL\DAM\miac_v19\compose.yaml' run --rm -T web -d miac_v19 -u miac_picking_always_return --test-enable --test-tags picking_native_return19 --stop-after-init --no-http --max-cron-threads=0 --logfile=/var/lib/odoo/picking-return19-native-integration-tests-20261011.log
```

Ambos logs están conservados en `C:\Proyectos FL\DAM\miac_v19`.

Las pruebas propias comprueban apertura y descarte sin escrituras del origen,
estados y visibilidad, asistente obsoleto, cantidades cero, retorno total con
reservas, parciales/repetidos, unidades distintas, movimientos excluidos,
compañías y usuarios, vínculos con ventas/compras y fechas de suscripción
intactas al completar una devolución de cliente. Las pruebas nativas cubren
también lotes, series, paquetes y cambios.

## Respaldo, entorno y pendientes

Respaldos previos de base y filestore:

- `C:\Proyectos FL\DAM\miac_v19\picking-return19-before-20261011.dump`
- `C:\Proyectos FL\DAM\miac_v19\picking-return19-filestore-before-20261011.tar.gz`

Las pruebas automáticas se revierten. Para la revisión del navegador se preparan
tres albaranes ficticios con origen `MIAC-RETURN19-UI`: borrador, confirmado y
cancelado, y un producto «PRUEBA MIAC devolución V19». No se validan esos
albaranes ni se crean existencias; quedan disponibles únicamente en el ensayo.

Se verificó en pantalla el botón visible en el confirmado, oculto en borrador y
cancelado, y el asistente con cantidades en cero y sus tres opciones nativas.
Se descartó sin crear devoluciones. Albaranes: `WH/OUT/00006` (361),
`WH/OUT/00007` (362) y `WH/OUT/00008` (363). Capturas:

- `C:\Proyectos FL\DAM\miac_v19\picking-return19-button-20261011.png`
- `C:\Proyectos FL\DAM\miac_v19\picking-return19-wizard-20261011.png`

Correo bloqueado en `127.0.0.1:1`, sin servidores de correo activos, tareas
desactivadas y `max_cron_threads=0`. Odoo y PostgreSQL quedan iniciados y saludables.

La comprobación con documentos reales corresponde a una copia migrada de MIAC
separada. No se modificó el Excel, no se crearon commits y no se ejecutaron
conversiones ni SQL de escritura sobre la base del cliente.
