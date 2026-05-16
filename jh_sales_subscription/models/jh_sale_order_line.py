from odoo import models, api, fields, _
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_compare, float_round
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInvInherit(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        # Consolidación activada: agrupar SOLO por (company, currency, partner_invoice)
        if self.advance_payment_method == 'delivered' and getattr(self, 'consolidated_billing', False):
            moves = self.env['account.move']
            groups = defaultdict(lambda: self.env['sale.order'])

            # Construimos los grupos explícitamente
            for o in self.sale_order_ids:
                partner_inv = o.partner_invoice_id or o.partner_id  # fallback seguro
                key = (o.company_id.id, o.currency_id.id, partner_inv.id)
                groups[key] |= o

            # Por cada grupo, dejamos que Odoo consolide internamente esas SO
            for so_group in groups.values():
                # Usar contexto force_minimal_grouping para evitar errores de comparación
                # cuando hay campos None (como subscription_id) en las claves de agrupación
                moves |= so_group.with_context(force_minimal_grouping=True)._create_invoices(grouped=False, final=True)

            return self.sale_order_ids.action_view_invoice(moves)

        # Flujo normal intacto
        return super().create_invoices()


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    INVOICE_STATUS = [
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ]

    invoice_status = fields.Selection(
        selection=INVOICE_STATUS,
        string="Invoice Status",
        compute='_compute_invoice_status',
        store=True)


    def _get_invoice_grouping_keys(self):
        if self.env.context.get('force_minimal_grouping'):
            # SOLO estas llaves:
            return ['company_id', 'currency_id', 'partner_invoice_id']
        return super()._get_invoice_grouping_keys()

    def _prepare_upsell_renew_order_values(self, subscription_state):
        """
        Sobrescribe el méodo para:
        1. Actualizar el precio al precio actual del producto (usando la tarifa vigente)
        2. Heredar el lote/número de serie de la suscripción original
        """
        values = super()._prepare_upsell_renew_order_values(subscription_state)

        for entry in values.get('order_line', []):
            product_id = entry[2].get('product_id')
            if not product_id:
                continue
            
            # Buscar la línea original correspondiente
            original_line = self.order_line.filtered(lambda l: l.product_id.id == product_id)
            
            if original_line:
                original_line = original_line[0]  # Tomar la primera si hay varias
                
                # 1. Heredar el lot_id si existe en la línea original
                if original_line.lot_id:
                    entry[2]['lot_id'] = original_line.lot_id.id
                    _logger.info(f"[RENOVACIÓN] Heredando lote {original_line.lot_id.name} para producto {product_id}")
                
                # 2. Forzar recálculo del precio eliminando price_unit y discount
                # Esto permite que el sistema aplique automáticamente la tarifa vigente
                # cuando se cree la nueva línea de orden
                if 'price_unit' in entry[2]:
                    del entry[2]['price_unit']
                    _logger.info(f"[RENOVACIÓN] Eliminando price_unit para recalcular precio actual del producto {product_id}")
                
                if 'discount' in entry[2]:
                    del entry[2]['discount']
                    _logger.info(f"[RENOVACIÓN] Eliminando discount para recalcular descuento según tarifa del producto {product_id}")

        return values

    def action_confirm(self):
        """
        Sobrescribe action_confirm para manejar el caso de renovaciones de suscripciones
        que tienen referencias incorrectas que impiden la confirmación.
        
        El error "No puede renovar una suscripción que ya se renovó" ocurre cuando
        la suscripción tiene una referencia a otra orden de renovación que bloquea
        la confirmación de la orden actual.
        """
        # Limpiar referencias problemáticas ANTES de intentar confirmar
        for order in self:
            # Si es una orden de renovación de suscripción
            if order.is_subscription and order.subscription_id:
                subscription = order.subscription_id
                _logger.info(f"[RENOVACIÓN] Intentando confirmar orden {order.name}, suscripción: {subscription.id}")
                _logger.info(f"[RENOVACIÓN] Estado de la orden: {order.state}, subscription_state: {getattr(order, 'subscription_state', 'N/A')}")
                
                # IMPORTANTE: Limpiar renewal_order_id SIEMPRE si es diferente a la orden actual
                # Esto es necesario porque Odoo valida que una suscripción solo pueda tener una renovación
                if hasattr(subscription, 'renewal_order_id') and subscription.renewal_order_id:
                    renewal_order = subscription.renewal_order_id
                    _logger.info(f"[RENOVACIÓN] Suscripción tiene renewal_order_id: {renewal_order.name} (estado: {renewal_order.state}, id: {renewal_order.id})")
                    _logger.info(f"[RENOVACIÓN] Orden actual: {order.name} (id: {order.id})")
                    
                    # Si la orden de renovación referenciada es diferente a la actual, limpiarla SIEMPRE
                    if renewal_order.id != order.id:
                        _logger.warning(f"[RENOVACIÓN] La suscripción referencia a otra orden ({renewal_order.name}). Limpiando referencia...")
                        # Obtener el nombre correcto de la tabla
                        subscription_table = subscription._table if hasattr(subscription, '_table') else 'sale_order'
                        _logger.info(f"[RENOVACIÓN] Usando tabla: {subscription_table}")
                        
                        # Verificar si la columna existe en la tabla antes de actualizar
                        self.env.cr.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = %s AND column_name = 'renewal_order_id'
                        """, (subscription_table,))
                        column_exists = self.env.cr.fetchone() is not None
                        
                        if column_exists:
                            # Usar SQL directo inmediatamente para evitar cualquier validación
                            self.env.cr.execute(
                                f"UPDATE {subscription_table} SET renewal_order_id = NULL WHERE id = %s",
                                (subscription.id,)
                            )
                            _logger.info(f"[RENOVACIÓN] Columna renewal_order_id actualizada en BD")
                        else:
                            _logger.warning(f"[RENOVACIÓN] La columna renewal_order_id no existe en la tabla {subscription_table}")
                        
                        # Invalidar y refrescar el cache completo
                        self.env.registry.clear_cache()
                        # Solo invalidar si el campo existe en el modelo
                        if 'renewal_order_id' in subscription._fields:
                            subscription.invalidate_recordset(['renewal_order_id'])
                        # Volver a leer la suscripción para obtener el valor actualizado
                        subscription = self.env['sale.order'].browse(subscription.id)
                        
                        # Verificar que se limpió correctamente (solo si la columna existe)
                        if column_exists:
                            self.env.cr.execute(
                                f"SELECT renewal_order_id FROM {subscription_table} WHERE id = %s",
                                (subscription.id,)
                            )
                            result = self.env.cr.fetchone()
                            renewal_id_db = result[0] if result else None
                            _logger.info(f"[RENOVACIÓN] Referencia limpiada. Verificación en BD: renewal_order_id = {renewal_id_db}")
                        else:
                            # Si no existe la columna, intentar limpiar usando el méodo write si el campo existe como atributo
                            try:
                                subscription.write({'renewal_order_id': False})
                                _logger.info(f"[RENOVACIÓN] Referencia limpiada usando write()")
                            except Exception as e:
                                _logger.warning(f"[RENOVACIÓN] No se pudo limpiar renewal_order_id: {e}")
                    else:
                        _logger.info(f"[RENOVACIÓN] La suscripción ya referencia a esta orden, está correcto")
                
                # También verificar si hay otras órdenes de renovación relacionadas
                # que puedan estar causando conflictos (verificar en order_ids si existe)
                if hasattr(subscription, 'order_ids'):
                    related_orders = subscription.order_ids.filtered(
                        lambda o: o.is_subscription and o.id != order.id
                    )
                    
                    # Buscar órdenes de renovación pendientes que puedan causar conflicto
                    related_renewal_orders = related_orders.filtered(
                        lambda o: o.state in ('draft', 'cancel') 
                        and hasattr(o, 'subscription_state') 
                        and o.subscription_state in ('3_renewal', '4_renewed', '5_renewed')
                    )
                    
                    if related_renewal_orders:
                        _logger.info(f"[RENOVACIÓN] Encontradas {len(related_renewal_orders)} órdenes de renovación relacionadas en estado draft/cancel")
                    
                    # Si hay órdenes de renovación canceladas, limpiar sus estados
                    for old_renewal in related_renewal_orders:
                        if old_renewal.state == 'cancel' and hasattr(old_renewal, 'subscription_state'):
                            _logger.info(f"[RENOVACIÓN] Limpiando subscription_state de orden cancelada: {old_renewal.name}")
                            old_renewal.write({'subscription_state': False})
        
        # Forzar guardado de todos los cambios antes de confirmar
        self.env.flush_all()
        
        # Invalidar caché de suscripciones después de la limpieza
        # Solo si el campo existe en el modelo
        for order in self:
            if order.is_subscription and order.subscription_id:
                subscription = order.subscription_id
                if 'renewal_order_id' in subscription._fields:
                    subscription.invalidate_recordset(['renewal_order_id'])
                else:
                    # Si el campo no existe, solo limpiar el caché general
                    self.env.registry.clear_cache()
        
        # Intentar confirmar con contexto que puede ayudar a evitar validaciones
        try:
            return super(SaleOrderInherit, self.with_context(skip_renewal_check=True)).action_confirm()
        except Exception as e:
            error_msg = str(e)
            # Si el error es el de renovación ya realizada, intentar una última vez
            # limpiando todas las referencias de forma más agresiva
            if "renovó" in error_msg or "renewed" in error_msg.lower() or "already renewed" in error_msg.lower():
                _logger.error(f"[RENOVACIÓN] Error persistente al confirmar: {error_msg}. Limpieza final agresiva...")
                
                # Limpieza final más agresiva usando SQL directo
                orders_to_retry = self.browse([])
                for order in self:
                    # Verificar si la orden todavía necesita confirmación
                    order.invalidate_recordset(['state'])
                    order_state = order.state
                    if order_state != 'draft':
                        _logger.info(f"[RENOVACIÓN] Orden {order.name} ya está en estado '{order_state}', no necesita confirmación")
                        continue
                    
                    if order.is_subscription and order.subscription_id:
                        subscription = order.subscription_id
                        # Buscar el nombre de la tabla de suscripciones
                        subscription_table = subscription._table if hasattr(subscription, '_table') else 'sale_order'
                        
                        if hasattr(subscription, 'renewal_order_id') and subscription.renewal_order_id:
                            if subscription.renewal_order_id.id != order.id:
                                _logger.warning(f"[RENOVACIÓN] Limpieza final SQL: eliminando referencia renewal_order_id de suscripción {subscription.id}")
                                
                                # Verificar si la columna existe en la tabla
                                self.env.cr.execute("""
                                    SELECT column_name 
                                    FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = 'renewal_order_id'
                                """, (subscription_table,))
                                column_exists = self.env.cr.fetchone() is not None
                                
                                if column_exists:
                                    # Usar SQL directo para evitar validaciones de Odoo
                                    self.env.cr.execute(
                                        f"UPDATE {subscription_table} SET renewal_order_id = NULL WHERE id = %s",
                                        (subscription.id,)
                                    )
                                    _logger.info(f"[RENOVACIÓN] Columna renewal_order_id actualizada en BD")
                                else:
                                    _logger.warning(f"[RENOVACIÓN] La columna renewal_order_id no existe en la tabla {subscription_table}")
                                
                                # Invalidar el cache solo si el campo existe
                                if 'renewal_order_id' in subscription._fields:
                                    subscription.invalidate_recordset(['renewal_order_id'])
                                else:
                                    self.env.registry.clear_cache()
                                
                                # Volver a leer la suscripción
                                subscription = self.env['sale.order'].browse(subscription.id)
                                
                                # Verificar resultado
                                if hasattr(subscription, 'renewal_order_id'):
                                    _logger.info(f"[RENOVACIÓN] Referencia limpiada. renewal_order_id ahora es: {subscription.renewal_order_id}")
                                else:
                                    _logger.info(f"[RENOVACIÓN] Referencia limpiada (campo no existe en modelo)")
                        
                        # También buscar si hay otras órdenes relacionadas que puedan estar bloqueando
                        # Buscar todas las órdenes de renovación de esta suscripción
                        related_renewal_orders = self.env['sale.order'].search([
                            ('subscription_id', '=', subscription.id),
                            ('is_subscription', '=', True),
                            ('id', '!=', order.id),
                            ('state', 'in', ('draft', 'sent')),
                            ('subscription_state', 'in', ('3_renewal', '4_renewed', '5_renewed'))
                        ])
                        
                        if related_renewal_orders:
                            _logger.warning(f"[RENOVACIÓN] Encontradas {len(related_renewal_orders)} órdenes de renovación relacionadas: {related_renewal_orders.mapped('name')}")
                            # Limpiar el subscription_state de órdenes en borrador que puedan causar conflicto
                            for rel_order in related_renewal_orders:
                                if rel_order.state == 'draft':
                                    _logger.info(f"[RENOVACIÓN] Limpiando subscription_state de orden relacionada: {rel_order.name}")
                                    rel_order.write({'subscription_state': False})
                    
                    orders_to_retry |= order
                
                # Si hay órdenes para reintentar, hacerlo
                if orders_to_retry:
                    _logger.info(f"[RENOVACIÓN] Reintentando confirmar órdenes: {orders_to_retry.mapped('name')}")
                    # Forzar flush e invalidar antes de reintentar
                    self.env.flush_all()
                    for order in orders_to_retry:
                        order.invalidate_recordset(['state', 'subscription_state'])
                        if order.subscription_id:
                            subscription = order.subscription_id
                            if 'renewal_order_id' in subscription._fields:
                                subscription.invalidate_recordset(['renewal_order_id'])
                            else:
                                self.env.registry.clear_cache()
                    
                    try:
                        return super(SaleOrderInherit, orders_to_retry).action_confirm()
                    except Exception as retry_error:
                        error_msg2 = str(retry_error)
                        # Si el error es que ya no necesita confirmación, considerarlo éxito
                        if "no se encuentran en un estado que necesite confirmación" in error_msg2 or "not in a state requiring confirmation" in error_msg2.lower():
                            _logger.info(f"[RENOVACIÓN] Las órdenes ya están confirmadas: {error_msg2}")
                            # Verificar el estado y devolver las órdenes confirmadas
                            return orders_to_retry
                        # Si es otro error, propagarlo
                        raise
                else:
                    # No hay órdenes para reintentar (todas ya están confirmadas)
                    _logger.info(f"[RENOVACIÓN] No hay órdenes pendientes de confirmación")
                    return self
            # Si es otro error, propagarlo
            raise

    @api.onchange('validity_date')
    def _onchange_due_date(self):
        if self.validity_date is False or self.validity_date is None:
            return {
                'warning': {
                    'title': "Falta información",
                    'message': "Por favor, recuerde diligenciar la fecha de Vencimiento"
                }
            }

    def create_invoices(self):
        moves = self.env['account.move']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        if self.advance_payment_method == 'delivered':
            for order in self.sale_order_ids:
                order._compute_invoice_status()

                # IMPORTANTE: Forzar que qty_to_invoice siempre use cantidades entregadas
                # independientemente de la política de facturación del producto
                for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                    # Calcular cantidad a facturar basándose SIEMPRE en cantidades entregadas
                    qty_delivered = line.qty_delivered or 0.0
                    qty_invoiced = line.qty_invoiced or 0.0
                    qty_to_invoice_delivered = qty_delivered - qty_invoiced
                    
                    # Actualizar qty_to_invoice solo si hay cantidad pendiente de facturar
                    if float_compare(qty_to_invoice_delivered, 0.0, precision_digits=precision) > 0:
                        line.qty_to_invoice = qty_to_invoice_delivered
                        _logger.info(f"[FACTURACIÓN] Línea {line.id} - Producto: {line.product_id.name} - "
                                   f"Entregado: {qty_delivered}, Facturado: {qty_invoiced}, "
                                   f"A facturar: {qty_to_invoice_delivered}")
                    else:
                        line.qty_to_invoice = 0.0

                # Verificar si es recurrente y tiene fecha válida
                if order.is_subscription and order.next_invoice_date:
                    invoice_lines = order.order_line.filtered(
                        lambda l: not l.display_type and float_compare(l.qty_to_invoice, 0.0, precision_digits=precision) > 0
                    )
                    if invoice_lines:
                        moves |= order._create_invoices(final=True, date=order.next_invoice_date)
                        continue

                # Facturación normal si no es recurrente
                invoice_lines = order.order_line.filtered(
                    lambda l: not l.display_type and float_compare(l.qty_to_invoice, 0.0, precision_digits=precision) > 0
                )
                if invoice_lines:
                    moves |= order._create_invoices(final=True)

            return self.sale_order_ids.action_view_invoice(moves)

        return super().create_invoices()


    @api.depends('state', 'order_line.product_id', 'subscription_state')
    def _compute_invoice_status(self):
        today = fields.Date.today()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for order in self.filtered(lambda o: not o.name.startswith('SO') and o.subscription_state != '5_renewed'):
            # Excluir órdenes canceladas o suscripciones churn
            if order.state not in ('sale', 'done') or order.subscription_state == '6_churn':
                order.invoice_status = 'no'
                continue

            # Filtrar solo líneas con producto real
            lineas_facturables = order.order_line.filtered(lambda l: l.product_id)

            if not lineas_facturables:
                order.invoice_status = 'no'
                continue

            # Si no hay facturas asociadas
            if not order.invoice_ids:
                order.invoice_status = 'to invoice'
                continue

            # Obtener productos de la orden
            producto_ids = lineas_facturables.mapped('product_id')
            fecha_inicio = order.date_order.date()
            fecha_limite = fecha_inicio + relativedelta(years=1)

            # Buscar facturas posteadas del cliente en el rango
            facturas_cliente = self.env['account.move'].search([
                ('partner_id', '=', order.partner_id.id),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('invoice_date', '>=', fecha_inicio),
                ('invoice_date', '<=', fecha_limite)
            ])

            # Extraer productos facturados
            productos_facturados = set()
            for factura in facturas_cliente:
                for linea in factura.invoice_line_ids:
                    if linea.product_id:
                        productos_facturados.add(linea.product_id.id)

            # Validar si todos los productos de la orden están facturados
            if set(producto_ids.ids).issubset(productos_facturados):
                order.invoice_status = 'invoiced'
                continue

            # Validación por suscripción activa
            if order.is_subscription and order.next_invoice_date and order.start_date:
                if today >= order.start_date and today >= order.next_invoice_date:
                    facturas_actuales = order.invoice_ids.filtered(
                        lambda i: i.state == 'posted' and i.invoice_date >= order.next_invoice_date
                    )
                    if not facturas_actuales:
                        order.invoice_status = 'to invoice'
                        continue

            # Validación por monto total facturado
            total_facturado = sum(order.invoice_ids.filtered(lambda i: i.state == 'posted').mapped('amount_total'))
            if float_compare(total_facturado, order.amount_total, precision_digits=2) >= 0:
                order.invoice_status = 'invoiced'
                continue

            # Si hay productos no facturados, marcar como 'to invoice'
            productos_pendientes = producto_ids.filtered(lambda p: p.id not in productos_facturados)
            if productos_pendientes:
                order.invoice_status = 'to invoice'
                continue

            # Si nada aplica, marcar como no facturable
            order.invoice_status = 'no'


    def _was_product_already_invoiced(self):
        self.ensure_one()
        producto_ids = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_downpayment
        ).mapped('product_id')

        if not producto_ids:
            return False
        fecha_inicio = self.date_order.date()
        fecha_limite = fecha_inicio + relativedelta(years=1)

        facturas_cliente = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_limite)])

        for factura in facturas_cliente:
            for linea in factura.invoice_line_ids:
                if linea.product_id in producto_ids and float_compare(linea.quantity, 1.0, precision_digits=2) >= 0:
                    if float_compare(linea.price_unit, linea.product_id.lst_price, precision_digits=2) >= 0:
                        return True
        return False

class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Sobrescribe el méodo para incluir el lot_id en la línea de factura
        como jh_sale_lot_id para que pueda ser utilizado en reportes y comisiones
        """
        res = super()._prepare_invoice_line(**optional_values)
        
        # Si esta línea tiene un lot_id, agregarlo a los valores de la línea de factura
        if self.lot_id:
            res['jh_sale_lot_id'] = self.lot_id.id
        
        return res

    @api.depends("order_id.partner_id")
    def _compute_agent_ids(self):
        """
        Sobrescribe el méodo original para que SIEMPRE herede los agentes
        del contacto, independientemente del settlement_type (manual o sale_invoice).
        """
        self.agent_ids = False  # for resetting previous agents
        for record in self:
            if record.order_id.partner_id and not record.commission_free:
                # No pasar settlement_type para que no se filtre y se incluyan todos los agentes
                record.agent_ids = record._prepare_agents_vals_partner(
                    record.order_id.partner_id, settlement_type=None
                )

    @api.onchange('product_id')
    def _onchange_product_subscription_lot(self):
        if self.product_id and self.product_id.recurring_invoice:
            if not self.lot_id:
                return {
                    'warning': {
                        'title': "Falta información",
                        'message': "Este producto es una suscripción. Por favor recuerde diligenciar el campo Lote Num Serie."
                    }
                }

    def _get_pricelist_reprice_vals(self):
        self.ensure_one()
        if self.display_type or self.is_downpayment:
            return {}

        order = self.order_id
        product = self.product_id
        if not order or not order.pricelist_id or not product:
            return {}

        pricelist = order.pricelist_id
        uom = self.product_uom or product.uom_id
        qty = self.product_uom_qty or 1.0
        date = fields.Date.to_date(order.date_order) if order.date_order else fields.Date.context_today(self)

        # Precio final según la tarifa (ya con reglas aplicadas)
        price, rule_id = pricelist._get_product_price_rule(
            product=product,
            quantity=qty,
            uom=uom,
            date=date,
            partner=order.partner_id,
        )

        vals = {}

        # 1) with_discount = "Descuento incluido en el precio"
        #    -> solo mostramos el precio final, sin % de descuento
        if pricelist.discount_policy == 'with_discount':
            vals['price_unit'] = price
            vals['discount'] = 0.0
            return vals

        # 2) without_discount = "Mostrar precio público + % descuento"
        #    -> price_unit = precio público, discount = % para llegar a 'price'
        public_price_company_cur = product.uom_id._compute_price(product.lst_price, uom)
        public_price_in_order_cur = order.company_id.currency_id._convert(
            public_price_company_cur,
            order.currency_id,
            order.company_id,
            date,
        )

        if float_compare(public_price_in_order_cur, 0.0, precision_digits=6) <= 0:
            # No hay precio público válido: usamos directamente el precio de la tarifa
            vals['price_unit'] = price
            vals['discount'] = 0.0
        else:
            disc = 100.0 * (1.0 - (price / public_price_in_order_cur))
            disc = float_round(min(max(disc, 0.0), 100.0), precision_digits=2)
            vals['price_unit'] = public_price_in_order_cur
            vals['discount'] = disc

        return vals

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_apply_pricelist(self):
        """
        Aplica la tarifa solo cuando se cambia el producto, UOM o cantidad.
        NO sobrescribe valores manuales de precio_unit o discount.
        
        La lógica preserva valores manuales:
        - Si el precio fue modificado manualmente, se mantiene
        - Si el descuento fue modificado manualmente, se mantiene
        - Solo aplica tarifa a campos que están en valores por defecto
        """
        for line in self:
            if line.is_downpayment or line.display_type:
                continue
            if not line.product_id:
                continue
            
            # Obtener valores actuales
            current_price = line.price_unit or 0.0
            current_discount = line.discount or 0.0
            default_price = line.product_id.list_price or 0.0
            
            # Verificar si los valores actuales son los por defecto
            is_default_price = float_compare(current_price, 0.0, precision_digits=6) == 0 or \
                              (default_price > 0 and float_compare(current_price, default_price, precision_digits=6) == 0)
            is_default_discount = float_compare(current_discount, 0.0, precision_digits=2) == 0
            
            # Solo aplicar tarifa si al menos uno de los valores es por defecto
            # Pero actualizar solo los campos que son por defecto
            if is_default_price or is_default_discount:
                vals = line._get_pricelist_reprice_vals()
                if vals:
                    update_vals = {}
                    # Solo actualizar precio si es por defecto
                    if 'price_unit' in vals and is_default_price:
                        update_vals['price_unit'] = vals['price_unit']
                    # Solo actualizar descuento si es por defecto
                    if 'discount' in vals and is_default_discount:
                        update_vals['discount'] = vals['discount']
                    # Solo actualizar si hay algo que actualizar
                    if update_vals:
                        line.update(update_vals)

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Solo aplicar tarifa si no se proporcionaron valores manuales de precio o descuento
        if not rec.is_downpayment and not rec.display_type and rec.order_id.pricelist_id and rec.product_id:
            # Si ya se proporcionaron precio_unit o discount en vals, no recalcular
            has_manual_price = 'price_unit' in vals and vals.get('price_unit', 0) != 0
            has_manual_discount = 'discount' in vals and vals.get('discount', 0) != 0
            
            if not has_manual_price and not has_manual_discount:
                vals2 = rec._get_pricelist_reprice_vals()
                if vals2:
                    rec.write(vals2)
        return rec

    def write(self, vals):
        # Evitar recursión: si ya estamos en modo skip, no hacer nada más
        if self.env.context.get('skip_pricelist_recalc', False):
            return super().write(vals)
        
        # Detectar si se están modificando manualmente precio o descuento
        is_manual_price_change = 'price_unit' in vals
        is_manual_discount_change = 'discount' in vals
        
        res = super().write(vals)
        
        # Solo recalcular precios si se cambia producto, UOM o cantidad
        # Y NO si el usuario está modificando manualmente precio_unit o discount
        if any(k in vals for k in ('product_id', 'product_uom', 'product_uom_qty')):
            # No recalcular si se están modificando manualmente precio o descuento
            if not is_manual_price_change and not is_manual_discount_change:
                for line in self:
                    if line.is_downpayment or line.display_type:
                        continue
                    if line.order_id.pricelist_id and line.product_id:
                        vals2 = line._get_pricelist_reprice_vals()
                        if vals2:
                            # Solo actualizar si los valores actuales son los por defecto
                            update_vals = {}
                            current_price = line.price_unit
                            current_discount = line.discount
                            
                            # Calcular precio por defecto del producto
                            default_price = line.product_id.list_price
                            
                            # Solo actualizar precio si es 0 o es el valor por defecto del producto
                            if 'price_unit' in vals2:
                                if float_compare(current_price, 0.0, precision_digits=6) == 0 or \
                                   (default_price > 0 and float_compare(current_price, default_price, precision_digits=6) == 0):
                                    update_vals['price_unit'] = vals2['price_unit']
                            
                            # Solo actualizar descuento si es 0
                            if 'discount' in vals2:
                                if float_compare(current_discount, 0.0, precision_digits=2) == 0:
                                    update_vals['discount'] = vals2['discount']
                            
                            if update_vals:
                                # Usar write con contexto skip para evitar recursión
                                line.with_context(skip_pricelist_recalc=True).write(update_vals)
        return res

class AccountMoveSendInherit(models.TransientModel):
    _inherit = 'account.move.send'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        compute='_compute_partner_ids',
        store=True
    )

    commercial_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Commercial Partner",
        compute='_compute_partner_ids',
        store=True
    )

    @api.depends('move_ids')
    def _compute_partner_ids(self):
        for wizard in self:
            move = wizard.move_ids[:1]
            wizard.partner_id = move.partner_id
            wizard.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        partner_ids = kwargs.get('partner_ids', []) or []
        if len(partner_ids) <= 1:
            return super()._send_mail(move, mail_template, **kwargs)

        result = None
        for partner_id in partner_ids:
            new_kwargs = dict(kwargs, partner_ids=[partner_id])
            result = super()._send_mail(move, mail_template, **new_kwargs)
        return result

