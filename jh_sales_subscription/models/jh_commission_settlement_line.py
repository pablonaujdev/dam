from odoo import models, fields, api, _


class ProductProductInherit(models.Model):
    """Heredar product.product para personalizar name_get en contexto de comisiones"""
    _inherit = 'product.product'
    
    def name_get(self):
        """Personalizar name_get para mostrar solo el nombre del producto"""
        # Si estamos en contexto de comisiones, mostrar solo el nombre
        if self.env.context.get('commission_context'):
            return [(record.id, record.name or '') for record in self]
        return super().name_get()


class CommissionSettlementLineInherit(models.Model):
    _inherit = 'commission.settlement.line'

    jh_serial_number = fields.Char(compute='_compute_serial_number',
                                   string='N° de Serie',
                                   store=False)
    jh_total_amount = fields.Float(string='Importe Bruto',
                                   compute='_compute_total_amount'
                                   )
    jh_commission_percent = fields.Float(string='% de Comisión',
                                         compute='_compute_commission_percent',
                                         store=True)
    jh_invoice_id = fields.Many2one(comodel_name='account.move',
                                    string='Factura',
                                    related='invoice_line_id.move_id',
                                    store=True)
    jh_product_id = fields.Many2one(comodel_name='product.product',
                                    string='Producto',
                                    compute='_compute_jh_product_id',
                                    store=True)
    jh_product_name = fields.Char(string='Nombre Producto',
                                   compute='_compute_product_name',
                                   store=True)

    @api.depends('invoice_line_id')
    def _compute_serial_number(self):
        """
        Calcular el número de serie buscando en múltiples ubicaciones:
        1. jh_sale_lot_id directamente en la línea de factura (si existe)
        2. lot_id en la línea de venta
        3. lot_id en los movimientos de stock relacionados
        4. lot_id en los pickings relacionados
        """
        for record in self:
            serial = ''
            invoice_line = record.invoice_line_id

            if not invoice_line:
                record.jh_serial_number = ''
                continue

            # Méodo 1: Buscar directamente en jh_sale_lot_id de la línea de factura
            try:
                if hasattr(invoice_line, 'jh_sale_lot_id') and invoice_line.jh_sale_lot_id:
                    # Puede ser un Many2one o un Char
                    sale_lot_value = invoice_line.jh_sale_lot_id
                    if isinstance(sale_lot_value, models.Model):
                        serial = sale_lot_value.name or str(sale_lot_value) or ''
                    else:
                        serial = str(sale_lot_value).strip()
                    if serial:
                        record.jh_serial_number = serial
                        continue
            except Exception:
                pass

            # Méodo 2: Buscar lot_id directamente en la línea de factura
            try:
                if hasattr(invoice_line, 'lot_id') and invoice_line.lot_id:
                    serial = invoice_line.lot_id.name or ''
                    if serial:
                        record.jh_serial_number = serial
                        continue
            except Exception:
                pass

            # Méodo 3: Buscar la línea de venta vinculada
            sale_line = False
            try:
                # Intentar buscar a través de sale_line_ids (más directo)
                if hasattr(invoice_line, 'sale_line_ids') and invoice_line.sale_line_ids:
                    sale_line = invoice_line.sale_line_ids[0]
                else:
                    # Búsqueda tradicional por invoice_lines
                    sale_line = self.env['sale.order.line'].search([
                        ('invoice_lines', 'in', invoice_line.id)
                    ], limit=1)
            except Exception:
                pass

            if sale_line:
                # Méodo 3a: Buscar lot_id directamente en la línea de venta
                try:
                    if hasattr(sale_line, 'lot_id') and sale_line.lot_id:
                        serial = sale_line.lot_id.name or ''
                        if serial:
                            record.jh_serial_number = serial
                            continue
                except Exception:
                    pass

                # Méodo 3b: Buscar en movimientos de stock vinculados a la línea de venta
                try:
                    # Buscar en stock.move que tenga sale_line_id
                    domain = [('sale_line_id', '=', sale_line.id)]
                    if invoice_line.product_id:
                        domain.append(('product_id', '=', invoice_line.product_id.id))
                    stock_moves = self.env['stock.move'].search(domain)
                    
                    if stock_moves:
                        # Buscar en las líneas de movimiento (stock.move.line)
                        move_lines = stock_moves.mapped('move_line_ids')
                        
                        if move_lines:
                            # Buscar en lot_id de los movimientos
                            lot_names = move_lines.mapped('lot_id.name')
                            serial = ', '.join(filter(None, lot_names))
                            
                            # Si no hay lot_id, buscar en lot_name
                            if not serial:
                                lot_names = move_lines.mapped('lot_name')
                                serial = ', '.join(filter(None, filter(lambda x: x, lot_names)))
                            
                            if serial:
                                record.jh_serial_number = serial
                                continue
                except Exception:
                    pass

                # Méodo 3c: Búsqueda directa en stock.move.line
                try:
                    domain = [('move_id.sale_line_id', '=', sale_line.id)]
                    if invoice_line.product_id:
                        domain.append(('product_id', '=', invoice_line.product_id.id))
                    move_lines_direct = self.env['stock.move.line'].search(domain)
                    
                    if move_lines_direct:
                        lot_names = move_lines_direct.mapped('lot_id.name')
                        serial = ', '.join(filter(None, lot_names))
                        
                        if not serial:
                            lot_names = move_lines_direct.mapped('lot_name')
                            serial = ', '.join(filter(None, filter(lambda x: x, lot_names)))
                        
                        if serial:
                            record.jh_serial_number = serial
                            continue
                except Exception:
                    pass

            # Méodo 4: Buscar en pickings relacionados con la factura/orden de venta
            if not serial and invoice_line.move_id:
                try:
                    # Obtener las órdenes de venta relacionadas
                    sale_orders = invoice_line.move_id.invoice_line_ids.mapped(
                        'sale_line_ids.order_id'
                    )
                    
                    if sale_orders:
                        # Buscar pickings relacionados
                        pickings = self.env['stock.picking'].search([
                            ('sale_id', 'in', sale_orders.ids),
                            ('state', '=', 'done')
                        ])
                        
                        if pickings:
                            # Buscar en las líneas de picking que coincidan con el producto
                            all_move_lines = pickings.mapped('move_line_ids_without_package')
                            if invoice_line.product_id:
                                picking_move_lines = all_move_lines.filtered(
                                    lambda ml: ml.product_id.id == invoice_line.product_id.id
                                )
                            else:
                                picking_move_lines = all_move_lines
                            
                            if picking_move_lines:
                                lot_names = picking_move_lines.mapped('lot_id.name')
                                serial = ', '.join(filter(None, lot_names))
                                
                                if not serial:
                                    lot_names = picking_move_lines.mapped('lot_name')
                                    serial = ', '.join(filter(None, filter(lambda x: x, lot_names)))
                                
                                if serial:
                                    record.jh_serial_number = serial
                                    continue
                except Exception:
                    pass

            record.jh_serial_number = serial

    @api.depends('invoice_line_id.price_unit', 'invoice_line_id.tax_ids', 'invoice_line_id.quantity')
    def _compute_total_amount(self):
        for record in self:
            invoice_line = record.invoice_line_id
            if not invoice_line:
                record.jh_total_amount = 0.0
                continue

            # Usar el precio unitario como base para compute_all
            taxes = invoice_line.tax_ids.compute_all(
                invoice_line.price_unit,
                currency=invoice_line.currency_id,
                quantity=invoice_line.quantity,
                product=invoice_line.product_id,
                partner=invoice_line.move_id.partner_id,
            )

            # Total con impuestos por línea
            record.jh_total_amount = taxes['total_excluded']

    @api.depends('invoice_line_id')
    def _compute_commission_percent(self):
        for record in self:
            percent = 0.0
            invoice_line = record.invoice_line_id

            if not invoice_line:
                record.jh_commission_percent = 0.0
                continue

            # Buscar agentes vinculados a esta línea de factura
            agent_lines = self.env['account.invoice.line.agent'].search([
                ('object_id', '=', invoice_line.id)
            ])

            for agent_line in agent_lines:
                commission = agent_line.commission_id
                if not agent_line.agent_id or not commission:
                    continue

                # Obtener porcentaje
                if commission.fix_qty and commission.fix_qty > 0.0:
                    percent = commission.fix_qty
                elif commission.section_ids:
                    percent = sum(section.percent or 0.0 for section in commission.section_ids)

                # Si hay múltiples agentes, puedes promediar o tomar el primero válido
                if percent > 0.0:
                    break  # si solo quieres el primero válido

            record.jh_commission_percent = percent

    @api.depends('invoice_line_id.product_id')
    def _compute_jh_product_id(self):
        """Calcular el producto desde la línea de factura"""
        for record in self:
            if record.invoice_line_id and record.invoice_line_id.product_id:
                record.jh_product_id = record.invoice_line_id.product_id
            else:
                record.jh_product_id = False

    @api.depends('invoice_line_id.product_id', 'invoice_line_id.product_id.name')
    def _compute_product_name(self):
        for record in self:
            if record.invoice_line_id and record.invoice_line_id.product_id:
                # Obtener solo el nombre del producto, sin información adicional
                product = record.invoice_line_id.product_id
                record.jh_product_name = product.name or ''
            else:
                record.jh_product_name = ''






