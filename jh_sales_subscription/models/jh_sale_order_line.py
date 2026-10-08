from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
import logging

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'


    jh_delivery_status = fields.Selection(
        selection=[
            ("draft", "Por confirmar"),
            ("not_required", "No requiere entrega"),
            ("pending", "Pendiente"),
            ("started", "En proceso"),
            ("partial", "Entrega parcial"),
            ("full", "Entrega finalizada"),
            ("delivery_cancelled", "Entrega cancelada"),
            ("cancelled", "Venta cancelada"),
        ],
        string= "Estado entrega material",
        compute="_compute_jh_delivery_status",
        store=True,
        readonly=True,
        index=True,
        help='Resume la entrega de material con el estado nativo de inventario.\nDistingue ventas pendientes, entregas parciales y transferencias canceladas.'
    )

    @api.depends(
        "state",
        "delivery_status",
        "picking_ids",
        "picking_ids.state",
        "order_line.product_id",
        "order_line.product_id.type",
        "order_line.product_uom_qty",
        "order_line.display_type",
    )

    def _compute_jh_delivery_status(self):
        for order in self:
            # Cotiazaciones todavía no confirmadas.
            if order.state in ("draft", "sent"):
                order.jh_delivery_status = 'draft'
                continue

            # Orden de venta cancelada.
            if order.state == "cancel":
                order.jh_delivery_status = 'cancelled'
                continue

            # Líneas que deberían generar movimientos de inventario.
            material_lines = order.order_line.filtered(
                lambda line:
                    not line.display_type
                    and line.product_id
                    and line.product_id.type == "consu"
                    and line.product_uom_qty > 0
            )

            # Venta compuesta únicamente por servicios o suscripciones.
            if not material_lines:
                order.jh_delivery_status = "not_required"
                continue

            # La venta tiene material, pero todas las transferencias
            # fueron canceladas y la orden sigue activa.
            if (
                order.picking_ids
                and all(
                    picking.state == "cancel"
                    for picking in order.picking_ids
                )
            ):
                order.jh_delivery_status = 'delivery_cancelled'
                continue

            # Aprovechamos el estado estándar calculado por sale_stock.
            status_mapping = {
                "pending": "pending",
                "started": "started",
                "partial": "partial",
                "full": "full",
            }

            order.jh_delivery_status = status_mapping.get(
                order.delivery_status,
                "pending",
            )


    def _jh_has_price_confirmation_gap(self):
        self.ensure_one()
        recurring_lines = self.order_line.filtered(
            lambda l: l.recurring_invoice and not l.display_type and not l.is_downpayment and l.product_id
        )
        for line in recurring_lines:
            vals = line._get_pricelist_reprice_vals()
            if not vals:
                continue
            price_differs = 'price_unit' in vals and float_compare(
                line.price_unit or 0.0,
                vals['price_unit'] or 0.0,
                precision_digits=6,
            ) != 0
            discount_differs = 'discount' in vals and float_compare(
                line.discount or 0.0,
                vals['discount'] or 0.0,
                precision_digits=2,
            ) != 0
            if price_differs or discount_differs:
                return True
        return False

    def _jh_open_subscription_price_confirmation(self, subscription_state):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmar actualizacion de precios'),
            'res_model': 'jh.subscription.price.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_subscription_state': subscription_state,
            },
        }

    def _jh_prepare_subscription_order_with_mode(self, subscription_state):
        self.ensure_one()
        lang = self.partner_id.lang or self.env.user.lang
        origin = 'renewal' if subscription_state == '2_renewal' else 'upsell'
        message_body = self._get_order_digest(origin=origin, lang=lang)
        return self._prepare_renew_upsell_order(subscription_state, message_body)

    def _jh_get_lines_to_protect_when_clearing_plan(self, vals):
        if 'plan_id' not in vals or vals.get('plan_id') or 'order_line' in vals:
            return self.env['sale.order.line']

        regular_orders = self.filtered(
            lambda order: (
                order.state in ('draft', 'sent')
                and order.plan_id
                and not order.subscription_id
                and not order.order_line.filtered(lambda line: line.recurring_invoice)
            )
        )
        return regular_orders.order_line.filtered(
            lambda line: (
                not line.display_type
                and not line.is_downpayment
                and line.product_id
            )
        )

    def write(self, vals):
        protected_lines = self._jh_get_lines_to_protect_when_clearing_plan(vals)
        if protected_lines:
            write_vals = dict(vals)
            write_vals.setdefault('subscription_state', False)
            protected_fields = [
                protected_lines._fields['price_unit'],
                protected_lines._fields['discount'],
            ]
            with self.env.protecting(protected_fields, protected_lines):
                return super().write(write_vals)
        return super().write(vals)

    def prepare_renewal_order(self):
        self.ensure_one()
        if not self.env.context.get('skip_renewal_price_confirmation') and self._jh_has_price_confirmation_gap():
            return self._jh_open_subscription_price_confirmation('2_renewal')
        return self._jh_prepare_subscription_order_with_mode('2_renewal')

    def prepare_upsell_order(self):
        self.ensure_one()
        if not self.env.context.get('skip_renewal_price_confirmation') and self._jh_has_price_confirmation_gap():
            return self._jh_open_subscription_price_confirmation('7_upsell')
        return self._jh_prepare_subscription_order_with_mode('7_upsell')

    def _prepare_upsell_renew_order_values(self, subscription_state):
        values = super()._prepare_upsell_renew_order_values(subscription_state)
        originals = {line.id: line for line in self.order_line}
        mode = self.env.context.get('renewal_pricing_mode', 'update_tariff')
        for command in values.get('order_line', []):
            if command[0] != 0:
                continue
            line_vals = command[2]
            original = originals.get(line_vals.get('parent_line_id'))
            if not original or original.display_type:
                continue
            line_vals['lot_id'] = original.lot_id.id
            if mode == 'keep_current':
                line_vals.update(price_unit=original.price_unit, discount=original.discount)
            else:
                line_vals.pop('price_unit', None)
                line_vals.pop('discount', None)
        return values


    @api.onchange('validity_date')
    def _onchange_due_date(self):
        if self.validity_date is False or self.validity_date is None:
            return {
                'warning': {
                    'title': "Falta información",
                    'message': "Por favor, recuerde diligenciar la fecha de Vencimiento"
                }
            }


    @api.constrains('start_date', 'end_date')
    def _jh_check_subscription_dates(self):
        for order in self:
            if (
                order.is_subscription and order.start_date and order.end_date
                and order.end_date < order.start_date
            ):
                raise ValidationError(_(
                    'La fecha de fin de la suscripción no puede ser anterior a su fecha de inicio.'
                ))

    @api.model
    def _cron_recalcular_invoice_status(self, only_pending=False, only_active_subscriptions=False):
        """Recompute native values in batches; never alter invoice quantities or periods."""
        domain = [('invoice_status', '=', 'to invoice')] if only_pending else []
        if only_active_subscriptions:
            domain += [
                ('state', '=', 'sale'), ('is_subscription', '=', True),
                ('subscription_state', 'in', ('3_progress', '4_paused')),
                ('start_date', '!=', False),
                '|', ('end_date', '=', False), ('end_date', '>', fields.Date.today()),
            ]
        scheduled = bool(self.env.context.get('cron_id'))
        parameters = self.env['ir.config_parameter'].sudo()
        scope = '%s.%s' % (int(only_pending), int(only_active_subscriptions))
        key = 'jh_sales_subscription.invoice_status_cursor.%s.%s' % (
            self.env.context.get('cron_id') or 'manual', scope)
        last_id = int(parameters.get_param(key, '0')) if scheduled else 0
        result = {'orders_checked': 0, 'orders_changed': 0, 'lines_changed': 0}
        if scheduled:
            self.env['ir.cron']._commit_progress(remaining=self.search_count(domain + [('id', '>', last_id)]))
        while orders := self.search(domain + [('id', '>', last_id)], order='id', limit=200):
            lines = orders.order_line
            old_orders = {order.id: order.invoice_status for order in orders}
            old_lines = {line.id: line.invoice_status for line in lines}
            self.env.add_to_compute(lines._fields['invoice_status'], lines)
            lines._recompute_recordset(['invoice_status'])
            self.env.add_to_compute(self._fields['invoice_status'], orders)
            orders._recompute_recordset(['invoice_status'])
            result['orders_checked'] += len(orders)
            result['orders_changed'] += sum(old_orders[order.id] != order.invoice_status for order in orders)
            result['lines_changed'] += sum(old_lines[line.id] != line.invoice_status for line in lines)
            last_id = orders[-1].id
            if scheduled:
                parameters.set_param(key, last_id)
                if not self.env['ir.cron']._commit_progress(len(orders)):
                    return result
        if scheduled:
            parameters.set_param(key, 0)
            self.env['ir.cron']._commit_progress(remaining=0)
        return result


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    def _jh_has_posted_invoice_coverage(self, precision):
        """Comprobar la cobertura propia usando el último período nativo de V19."""
        self.ensure_one()
        order = self.order_id
        period_end = self.last_invoiced_date
        if (
            not period_end or not order.start_date or period_end < order.start_date
            or not order.next_invoice_date or period_end >= order.next_invoice_date
            or not float_is_zero(self.qty_to_invoice, precision_digits=precision)
        ):
            return False
        invoice_lines = self.invoice_lines.filtered(
            lambda line: line.move_id.state == 'posted'
            and line.move_id.move_type in ('out_invoice', 'out_refund')
            and line.deferred_start_date and line.deferred_start_date >= order.start_date
            and line.deferred_start_date <= period_end
            and line.deferred_end_date == period_end
        )
        if not invoice_lines.filtered(lambda line: line.move_id.move_type == 'out_invoice'):
            return False
        quantity = sum(
            (1 if line.move_id.move_type == 'out_invoice' else -1)
            * line.product_uom_id._compute_quantity(line.quantity, self.product_uom_id, round=False)
            for line in invoice_lines
        )
        return float_compare(quantity, self.product_uom_qty, precision_digits=precision) >= 0

    @api.depends(
        'state', 'qty_to_invoice', 'qty_invoiced', 'product_uom_qty', 'product_uom_id',
        'recurring_invoice', 'last_invoiced_date', 'price_subtotal', 'product_id.invoice_policy',
        'invoice_lines.move_id.state', 'invoice_lines.move_id.move_type',
        'invoice_lines.quantity', 'invoice_lines.product_uom_id',
        'invoice_lines.deferred_start_date', 'invoice_lines.deferred_end_date',
        'order_id.start_date', 'order_id.end_date', 'order_id.next_invoice_date',
        'order_id.is_subscription', 'order_id.subscription_state', 'order_id.recurring_monthly',
    )
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        if self.env.context.get('skip_line_status_compute'):
            return
        today = fields.Date.today()
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for line in self:
            order = line.order_id
            if (
                line.state != 'sale' or line.invoice_status != 'no'
                or line.display_type or line.is_downpayment or not line.recurring_invoice
                or not order.is_subscription or order.subscription_state != '3_progress'
                or not order.start_date or order.start_date <= today
                or not order.next_invoice_date or order.next_invoice_date < order.start_date
                or (order.end_date and order.end_date <= order.start_date)
            ):
                continue
            if line._jh_has_posted_invoice_coverage(precision):
                line.invoice_status = 'invoiced'
            elif (
                not line._is_postpaid_line()
                and order.next_invoice_date == order.start_date
                and float_compare(line.qty_to_invoice, 0, precision_digits=precision) > 0
                and order.currency_id.compare_amounts(order.recurring_monthly, 0) > 0
                and not order.currency_id.is_zero(line.price_subtotal)
            ):
                # La selección manual nativa admite el primer período futuro prepago.
                line.invoice_status = 'to invoice'


    jh_discount_manual = fields.Boolean(
        string='Descuento negociado', copy=True,
        help='Conserva un descuento introducido expresamente en la linea.\nEvita que los cambios de cantidad o unidad sustituyan las condiciones negociadas.')

    @api.model_create_multi
    def create(self, vals_list):
        values = [dict(vals) for vals in vals_list]
        for vals in values:
            if 'discount' in vals:
                vals.setdefault('jh_discount_manual', True)
        lines = super().create(values)
        for line, vals in zip(lines, values):
            if 'price_unit' in vals and 'technical_price_unit' not in vals:
                expected = line._get_pricelist_reprice_vals()
                if expected:
                    line.with_context(sale_write_from_compute=True).technical_price_unit = expected['price_unit']
        return lines

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty', 'jh_discount_manual')
    def _compute_discount(self):
        automatic = self.filtered(lambda line: not line.jh_discount_manual)
        super(SaleOrderLineInherit, automatic)._compute_discount()
        for line in self - automatic:
            line.discount = line.discount

    @api.onchange('discount')
    def _onchange_jh_discount_manual(self):
        for line in self:
            expected = line._get_pricelist_reprice_vals().get('discount', 0.0)
            if float_compare(line.discount, expected, precision_digits=2):
                line.jh_discount_manual = True

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

    def _prepare_agent_vals(self, agent):
        values = super()._prepare_agent_vals(agent)
        rule = self.product_id.categ_id.commission_ids.filtered(lambda item: item.agent_id == agent)[:1]
        if rule:
            values['commission_id'] = rule.commission_id.id
        values.update(z_commission_manual=False, z_manual_commission_id=False)
        return values

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
        """Use the native 19 helpers, including subscription pricing and tax mapping."""
        self.ensure_one()
        if not self.product_id or self.display_type or self.is_downpayment or not self.order_id.pricelist_id:
            return {}
        line = self.with_company(self.company_id)
        price = line.product_id._get_tax_included_unit_price_from_price(
            line._get_display_price(),
            product_taxes=line.product_id.taxes_id._filter_taxes_by_company(line.company_id),
            fiscal_position=line.order_id.fiscal_position_id,
        )
        discount = 0.0
        if line.env['product.pricelist.item']._is_discount_feature_enabled() and line.pricelist_item_id._show_discount():
            base_price = line._get_pricelist_price_before_discount()
            if base_price:
                value = (base_price - line._get_pricelist_price()) / base_price * 100
                if (value > 0 and base_price > 0) or (value < 0 and base_price < 0):
                    discount = value
        return {'price_unit': price, 'discount': discount}


    def write(self, vals):
        values = dict(vals)
        if 'discount' in values and not all(self.env.is_protected(self._fields['discount'], line) for line in self):
            values.setdefault('jh_discount_manual', True)
        protected = self.env['sale.order.line']
        if 'discount' not in values and any(key in values for key in ('product_uom_qty', 'product_uom_id')) and 'product_id' not in values:
            for line in self.filtered(lambda item: item.product_id and not item.display_type and not item.is_downpayment):
                expected = line._get_pricelist_reprice_vals().get('discount', 0.0)
                if line.jh_discount_manual or float_compare(line.discount, expected, precision_digits=2):
                    protected |= line
        with self.env.protecting([self._fields['discount']], protected):
            return super().write(values)

class SaleOrderLineAgentInherit(models.Model):
    _inherit = "sale.order.line.agent"

    commission_id = fields.Many2one(
        comodel_name="commission",
        ondelete="restrict",
        required=True,
        compute="_compute_commission_id",
        store=True,
        readonly=False,
        copy=True,
    )

    z_commission_manual = fields.Boolean(
        string="Manual commission",
        default=False,
        copy=True,
        help="Conserva la comision seleccionada manualmente.\nTiene prioridad sobre la categoria y la comision del agente.",
    )
    z_manual_commission_id = fields.Many2one(
        comodel_name="commission",
        string="Manual commission value",
        copy=True,
        help="Guarda la comision elegida para esta linea.\nSe aplica cuando esta habilitada la comision manual.",
    )

    @api.depends('agent_id', 'agent_id.commission_id', 'z_commission_manual', 'z_manual_commission_id',
                 'object_id.product_id', 'object_id.product_id.categ_id.commission_ids.commission_id',
                 'object_id.product_id.categ_id.commission_ids.agent_id')
    def _compute_commission_id(self):
        super()._compute_commission_id()
        for line in self:
            if line.z_commission_manual and line.z_manual_commission_id:
                line.commission_id = line.z_manual_commission_id
            elif 'commission_ids' in line.object_id.product_id._fields:
                rule = line.object_id.product_id.commission_ids.filtered(lambda item: item.agent_id == line.agent_id)[:1]
                if rule:
                    line.commission_id = rule.commission_id

    @api.model_create_multi
    def create(self, vals_list):
        # Odoo 19: preserve existing manual commission flags.
        for vals in vals_list:
            if "commission_id" in vals:
                if "z_commission_manual" not in vals:
                    vals["z_commission_manual"] = bool(vals.get("commission_id"))
                if "z_manual_commission_id" not in vals and vals.get("commission_id"):
                    vals["z_manual_commission_id"] = vals.get("commission_id")
            elif "agent_id" in vals and "z_commission_manual" not in vals:
                vals["z_commission_manual"] = False
                vals["z_manual_commission_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        # Odoo 19: preserve existing manual commission flags.
        if all(self.env.is_protected(self._fields['commission_id'], record) for record in self):
            return super().write(vals)
        safe_vals = dict(vals)
        if "commission_id" in safe_vals:
            if "z_commission_manual" not in safe_vals:
                safe_vals["z_commission_manual"] = bool(safe_vals.get("commission_id"))
            if "z_manual_commission_id" not in safe_vals and safe_vals.get("commission_id"):
                safe_vals["z_manual_commission_id"] = safe_vals.get("commission_id")
        elif "agent_id" in safe_vals and "commission_id" not in safe_vals:
            safe_vals["z_commission_manual"] = False
            safe_vals["z_manual_commission_id"] = False
        return super().write(safe_vals)


class AccountMoveSendWizardInherit(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        compute='_compute_partner_ids',
        store=True,
        help='Contacto de la factura que se va a enviar.\nDelimita los destinatarios disponibles en el asistente.'
    )

    commercial_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Commercial Partner",
        compute='_compute_partner_ids',
        store=True,
        help='Empresa principal del contacto facturado.\nPermite seleccionar sus contactos de facturacion y entrega.'
    )

    @api.depends('move_id', 'move_id.partner_id')
    def _compute_partner_ids(self):
        for wizard in self:
            move = wizard.move_id
            wizard.partner_id = move.partner_id
            wizard.commercial_partner_id = move.partner_id.commercial_partner_id


class AccountMoveSendInherit(models.AbstractModel):
    _inherit = 'account.move.send'

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
