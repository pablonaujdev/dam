from odoo import models, api, fields
from odoo.tools import SQL
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountInvoiceReportInherit (models.Model):
    _inherit = 'account.invoice.report'


    jh_invoice_date = fields.Date(string='Fecha de Factura', readonly=True)
    jh_commission = fields.Float(string='Importe Comisión', readonly=True)
    jh_commission_percent = fields.Float(string='% Comisión', readonly=True)
    jh_agents = fields.Char(string='Agentes', readonly=True)
    jh_margin_percent = fields.Float(string='% Margen', compute='_compute_margin_percent', store=False)
    jh_commission_settlement_date = fields.Date(string='Fecha Liquidación Comisión', readonly=True)
    jh_country_id = fields.Many2one('res.country', string='País', readonly=True)
    jh_state_id = fields.Many2one('res.country.state', string='Provincia', readonly=True)
    jh_tax_id = fields.Many2one('account.tax', string='Impuesto principal')
    jh_tax_amount = fields.Float(string='Valor IVA', readonly=True)
    jh_new_tax = fields.Float(string='Valor IVA', readonly=True)
    jh_cost = fields.Float(string='Costo', readonly=True)
    jh_partner_shipping_id = fields.Many2one('res.partner', string='Dirección De Entrega', readonly=True)
    jh_serial_number = fields.Char(string='N° de Serie', readonly=True)
    jh_payment_mode_id = fields.Many2one('account.payment.mode', string='Forma de Pago', readonly=True, related='move_id.payment_mode_id', store=False)
    jh_payment_term_id = fields.Many2one('account.payment.term', string='Condiciones de Pago', readonly=True, related='move_id.invoice_payment_term_id', store=False)



    @api.depends('price_margin', 'price_total')
    def _compute_margin_percent(self):
        for record in self:
            if record.price_total:
                record.jh_margin_percent = (record.price_margin / record.price_total) * 100
            else:
                record.jh_margin_percent = 0.0

    def _select(self):
        original = super()._select()
        return SQL("%s" + ''',
            move.invoice_date AS jh_invoice_date,
            line.jh_commission,
            line.jh_commission_percent,
            line.jh_agents,
            line.jh_commission_settlement_date,
            partner.country_id AS jh_country_id,
            partner.state_id AS jh_state_id,
            line.jh_tax_id,
            line.jh_tax_amount,
            line.jh_new_tax,
            line.jh_cost_unit AS jh_cost,
            move.partner_shipping_id as jh_partner_shipping_id,
            move.payment_mode_id AS jh_payment_mode_id,
            move.invoice_payment_term_id AS jh_payment_term_id,
            COALESCE(
                (SELECT lot.name FROM stock_lot lot WHERE lot.id = line.jh_sale_lot_id LIMIT 1),
                (SELECT lot.name
                 FROM sale_order_line sol
                 JOIN sale_order_line_invoice_rel solir ON solir.order_line_id = sol.id
                 LEFT JOIN stock_lot lot ON lot.id = sol.lot_id
                 WHERE solir.invoice_line_id = line.id
                 LIMIT 1),
                (SELECT lot.name
                 FROM stock_move_line sml
                 JOIN stock_move sm ON sm.id = sml.move_id
                 JOIN stock_lot lot ON lot.id = sml.lot_id
                 WHERE sm.sale_line_id IN (
                     SELECT sol.id FROM sale_order_line sol
                     JOIN sale_order_line_invoice_rel solir ON solir.order_line_id = sol.id
                     WHERE solir.invoice_line_id = line.id
                 )
                 AND sm.product_id = line.product_id
                 AND sml.lot_id IS NOT NULL
                 LIMIT 1)
            ) AS jh_serial_number
        ''', original)



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Campo para almacenar el lote/número de serie desde la línea de venta
    jh_sale_lot_id = fields.Many2one(
        'stock.lot',
        string='Lote/Número de Serie',
        help='Lote o número de serie asociado desde la línea de venta',
        domain="[('product_id', '=', product_id)]"
    )

    def _jh_is_syncable_invoice_line(self):
        self.ensure_one()
        return (
            self.display_type in (False, 'product')
            and self.move_id.is_sale_document(include_receipts=True)
        )

    def _jh_validate_lot_sync(self):
        for line in self:
            if not line._jh_is_syncable_invoice_line():
                continue
            if line.move_id.state != 'draft':
                raise UserError('Solo se puede corregir el lote o numero de serie en facturas en borrador.')
            if len(line.sale_line_ids) > 1:
                raise UserError(
                    'La linea de factura esta vinculada a varias lineas de venta. '
                    'No se puede sincronizar automáticamente el lote o numero de serie.'
                )

    def _jh_sync_lot_to_sale_line(self):
        for line in self:
            if not line._jh_is_syncable_invoice_line():
                continue
            sale_line = line.sale_line_ids[:1]
            if sale_line:
                sale_line.with_context(skip_invoice_lot_sync=True).write({
                    'lot_id': line.jh_sale_lot_id.id or False,
                })

    def write(self, vals):
        sync_lot = 'jh_sale_lot_id' in vals and not self.env.context.get('skip_invoice_lot_sync')
        if sync_lot:
            self._jh_validate_lot_sync()
        res = super().write(vals)
        if sync_lot:
            self._jh_sync_lot_to_sale_line()
        return res

    jh_agents = fields.Char(string='Agentes',
                            compute='_compute_jh_agents_commission',
                            store=True)
    jh_commission = fields.Float(string='Importe de Comisión',
                                 compute='_compute_jh_agents_commission',
                                 store=True )
    jh_commission_percent = fields.Float(string='% de Comisión',
                                         compute='_compute_jh_agents_commission',
                                         store=True )
    jh_commission_settlement_date = fields.Date(string='Fecha de Liquidación Comisión',
                                                compute='_compute_commission_settlement_date',
                                                store=True)

    jh_tax_id = fields.Many2one('account.tax', string='Impuesto principal', compute='_compute_tax_id', store=True)

    jh_tax_amount = fields.Float(string='Valor IVA', compute='_compute_tax_amount', store=True)
    jh_new_tax = fields.Float(string='Valor IVA', compute='_compute_new_tax', store=True)
    jh_tax_recalc_done = fields.Boolean(string='IVA Recalculado (jh_new_tax)', default=False, index=True)
    jh_cost_unit = fields.Monetary(
        string='Costo unitario (standard_price)',
        currency_field='company_currency_id',
        compute='_compute_jh_cost_unit',
        store=True,
        compute_sudo=True,  # <— IMPORTANTE
    )

    @api.depends('product_id', 'product_id.standard_price', 'product_uom_id', 'company_id', 'display_type')
    def _compute_jh_cost_unit(self):
        for line in self:
            cost = 0.0
            if line.product_id and line.display_type in (False, 'product'):
                product = line.product_id.with_company(line.company_id)
                cost = product.uom_id._compute_price(product.standard_price, line.product_uom_id or product.uom_id)
            line.jh_cost_unit = cost

    @api.depends('price_unit', 'quantity', 'discount', 'tax_ids', 'currency_id', 'move_id.move_type')
    def _compute_tax_amount(self):
        for line in self:
            result = line.tax_ids.compute_all(
                line.price_unit * (1 - line.discount / 100),
                currency=line.currency_id, quantity=line.quantity,
                product=line.product_id, partner=line.partner_id,
                is_refund=line.move_id.move_type in ('out_refund', 'in_refund'),
            )
            amount = result['total_included'] - result['total_excluded']
            line.jh_tax_amount = -amount if line.move_id.move_type in ('out_refund', 'in_refund') else amount

    @api.depends('price_subtotal', 'tax_ids', 'move_id.move_type')
    def _compute_new_tax(self):
        for line in self:
            try:
                base = abs(line.price_subtotal or line.balance or 0.0)
                if not line.tax_ids or base == 0.0:
                    line.jh_new_tax = 0.0
                    continue

                names = {(t.name or '').strip() for t in line.tax_ids}
                is_refund = line.move_id.move_type in ('out_refund', 'in_refund')

                # --- Reglas simples por nombre (sin regex, sin norm) ---
                # 1) Reino Unido: dejar 0 sí o sí
                if '21% R.Unido 600' in names or '21% R.Unido 6000' in names:
                    line.jh_new_tax = 0.0
                    continue

                # 2) 21% 600 serv => base * 21% (tomado del importe del propio impuesto)
                if '21% 600 serv' in names:
                    pct = 0.0
                    for t in line.tax_ids:
                        if (t.name or '').strip() == '21% 600 serv':
                            pct = (t.amount or 0.0)
                            break
                    amount = base * (pct / 100.0)
                    amount = -abs(amount) if is_refund else abs(amount)
                    line.jh_new_tax = round(amount, 2)
                    continue

                # 3) 4% S => base * 4% (desde importe del impuesto)
                if '4% S' in names:
                    pct = 0.0
                    for t in line.tax_ids:
                        if (t.name or '').strip() == '4% S':
                            pct = (t.amount or 0.0)
                            break
                    amount = base * (pct / 100.0)
                    amount = -abs(amount) if is_refund else abs(amount)
                    line.jh_new_tax = round(amount, 2)
                    continue

                # 4) 4% G => base * 4%
                if '4% G' in names:
                    pct = 0.0
                    for t in line.tax_ids:
                        if (t.name or '').strip() == '4% G':
                            pct = (t.amount or 0.0)
                            break
                    amount = base * (pct / 100.0)
                    amount = -abs(amount) if is_refund else abs(amount)
                    line.jh_new_tax = round(amount, 2)
                    continue

                # 5) 10% S => base * 10%
                if '10% S' in names:
                    pct = 0.0
                    for t in line.tax_ids:
                        if (t.name or '').strip() == '10% S':
                            pct = (t.amount or 0.0)
                            break
                    amount = base * (pct / 100.0)
                    amount = -abs(amount) if is_refund else abs(amount)
                    line.jh_new_tax = round(amount, 2)
                    continue
                # --- Fin reglas por nombre ---

                # --- Lógica original (fallback) ---
                iva_total = 0.0
                for tax in line.tax_ids.filtered(lambda t: t.active):
                    if tax.amount_type == 'group' and tax.children_tax_ids:
                        children = tax.children_tax_ids
                        has_minus_base = any(
                            (c.amount_type == 'percent' and round((c.amount or 0.0), 6) == -100.0)
                            for c in children
                        )
                        positive_percent = sum(
                            (c.amount or 0.0) for c in children
                            if c.amount_type == 'percent' and (c.amount or 0.0) > 0.0
                        )
                        if has_minus_base and positive_percent:
                            # DUA: SOLO el IVA (no base+IVA)
                            iva_total = base * (positive_percent / 100.0)
                            break

                        for c in children:
                            if c.amount_type == 'percent' and (c.amount or 0.0):
                                if c.price_include or c.include_base_amount:
                                    comp = base - (base / (1.0 + (c.amount / 100.0)))
                                else:
                                    comp = base * (c.amount / 100.0)
                                iva_total += comp
                            elif c.amount_type == 'fixed' and (c.amount or 0.0):
                                iva_total += c.amount
                    else:
                        if tax.amount_type == 'percent' and (tax.amount or 0.0):
                            if tax.price_include or tax.include_base_amount:
                                comp = base - (base / (1.0 + (tax.amount / 100.0)))
                            else:
                                comp = base * (tax.amount / 100.0)
                            iva_total += comp
                        elif tax.amount_type == 'fixed' and (tax.amount or 0.0):
                            iva_total += tax.amount

                amount = abs(iva_total)
                if is_refund:
                    amount = -amount
                line.jh_new_tax = round(amount, 2)

            except Exception as e:
                _logger.warning("Compute IVA falló en línea %s: %s", line.id, e)
                line.jh_new_tax = 0.0

    @api.depends('tax_ids', 'tax_ids.active', 'tax_ids.sequence', 'tax_ids.name', 'tax_ids.children_tax_ids', 'tax_ids.children_tax_ids.active',
                 'tax_ids.children_tax_ids.sequence','tax_ids.children_tax_ids.name',)
    def _compute_tax_id(self):
        for line in self:
            if not line.tax_ids:
                line.jh_tax_id = False
                continue

            tax = sorted(
                line.tax_ids,
                key=lambda t: (t.sequence or 0, (t.name or '').lower(), t.id)
            )[:1]
            line.jh_tax_id = tax[0].id if tax else False

    @api.depends('agent_ids.settlement_line_ids.settlement_id.create_date')
    def _compute_commission_settlement_date(self):
        for record in self:
            settlement_lines = self.env['commission.settlement.line'].search([
                ('invoice_line_id', '=', record.id),
            ])
            fechas = settlement_lines.mapped('settlement_id.create_date')
            record.jh_commission_settlement_date = fechas and min(fechas).date() or False

    @api.model
    def _cron_recalcular_fecha_liquidacion(self):
        domain = [('agent_ids', '!=', False)]
        scheduled = bool(self.env.context.get('cron_id'))
        parameters = self.env['ir.config_parameter'].sudo()
        key = 'jh_sales_subscription.settlement_date_cursor'
        last_id = int(parameters.get_param(key, '0')) if scheduled else 0
        processed = 0
        if scheduled:
            self.env['ir.cron']._commit_progress(remaining=self.search_count(domain + [('id', '>', last_id)]))
        while lines := self.search(domain + [('id', '>', last_id)], order='id', limit=400):
            lines._compute_commission_settlement_date()
            processed += len(lines)
            last_id = lines[-1].id
            if scheduled:
                parameters.set_param(key, last_id)
                if not self.env['ir.cron']._commit_progress(len(lines)):
                    return processed
        if scheduled:
            parameters.set_param(key, 0)
            self.env['ir.cron']._commit_progress(remaining=0)
        return processed


    @api.depends('product_id', 'agent_ids.amount', 'agent_ids.agent_id.name', 'agent_ids.commission_id')
    def _compute_jh_agents_commission(self):
        for record in self:
            agent_names = set()
            commission_amount = 0.0
            commission_percent = 0.0

            if not record.product_id:
                record.jh_agents = ''
                record.jh_commission = 0.0
                record.jh_commission_percent = 0.0
                continue

            # Buscar agentes vinculados a esta línea
            agent_lines = self.env['account.invoice.line.agent'].search([
                ('object_id', '=', record.id)
            ])

            for agent_line in agent_lines:
                commission = agent_line.commission_id
                if not agent_line.agent_id or not commission:
                    continue

                # Obtener porcentaje
                percent = 0.0
                if commission.fix_qty and commission.fix_qty > 0.0:
                    percent = commission.fix_qty
                elif commission.section_ids:
                    percent = sum(section.percent or 0.0 for section in commission.section_ids)

                # Validar que el monto sea positivo y el porcentaje válido
                if agent_line.amount and percent > 0.0:
                    agent_names.add(agent_line.agent_id.name)
                    commission_amount += agent_line.amount
                    commission_percent = percent  # si hay múltiples, puedes promediar o mostrar el primero

            record.jh_agents = ', '.join(sorted(agent_names))
            record.jh_commission = commission_amount
            record.jh_commission_percent = commission_percent





    # ---------------------------
    # Selector por lotes (pendientes)
    # ---------------------------

    # ---------------------------
    # Cron por bloques (cada minuto)
    # ---------------------------
    @api.model
    def cron_recalcular_valor_iva(self):
        domain = [('display_type', '=', 'product'), ('jh_tax_recalc_done', '=', False)]
        cron = self.env['ir.cron']
        if self.env.context.get('cron_id'):
            cron._commit_progress(remaining=self.search_count(domain))
        processed = 0
        while lines := self.search(domain, order='id', limit=400):
            for field_name in ('jh_new_tax', 'jh_tax_id', 'jh_tax_amount', 'jh_cost_unit'):
                self.env.add_to_compute(self._fields[field_name], lines)
            lines._recompute_recordset(['jh_new_tax', 'jh_tax_id', 'jh_tax_amount', 'jh_cost_unit'])
            lines.write({'jh_tax_recalc_done': True})
            processed += len(lines)
            if self.env.context.get('cron_id') and not cron._commit_progress(len(lines)):
                break
        return processed
