# -*- coding: utf-8 -*-
import time
import logging
from psycopg2 import errors
from odoo import models, api, fields
try:
    # Odoo 14+ suele traer esto aquí
    from odoo.tools.misc import split_every as _split_every
except Exception:
    # Fallback simple si no existiera en tu build
    def _split_every(n, seq):
        for i in range(0, len(seq), n):
            yield seq[i:i+n]


_logger = logging.getLogger(__name__)

ADVISORY_KEY_IVA = 0x4A485F495641  # 64-bit
BATCH_SIZE = 400                   # ajusta (100-800)
MAX_RETRIES = 3
TIME_BUDGET_SEC = 50               # ~ <60s por corrida
MAX_BATCHES_PER_RUN = 10           # salvaguarda adicional
CURSOR_PARAM_KEY = 'aml_iva_recalc_last_id'

class AccountInvoiceReportInherit (models.Model):
    _inherit = 'account.invoice.report'


    jh_invoice_date = fields.Date(string='Fecha de Factura', readonly=True)
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', store=False)
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
        return original + ''',
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
        '''

    def _group_by(self):
        original = super()._group_by()
        return original + ''',
            line.jh_commission_settlement_date,
            partner.country_id AS jh_country_id,
            partner.state_id AS jh_state_id,
            line.jh_tax_id,
            line.jh_tax_amount,
            line.jh_new_tax,
            partner.country_id,
            partner.state_id,
            line.jh_cost_unit,
            move.invoice_date,
            move.partner_shipping_id,
            move.payment_mode_id,
            move.invoice_payment_term_id
        '''


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Campo para almacenar el lote/número de serie desde la línea de venta
    jh_sale_lot_id = fields.Many2one(
        'stock.lot',
        string='Lote/Número de Serie',
        help='Lote o número de serie asociado desde la línea de venta'
    )

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

    @api.depends_context('company')
    @api.depends(
        'product_id',
        'product_id.uom_id',
        'product_id.product_tmpl_id',
        'product_uom_id',
        'display_type',
        'company_id',
        'move_id.company_id',
        'move_id.invoice_date',
        'move_id.move_type',
    )
    def _compute_jh_cost_unit(self):
        # Evita escribir 0 mientras levanta el registry
        if not self.env.registry.ready:
            _logger.debug("[COST] Registry no listo; se omite cómputo.")
            return

        cr = self.env.cr
        for l in self:
            try:
                # Log inicial por línea
                _logger.debug(
                    "[COST] START aml=%s move=%s display_type=%s product_id=%s uom_line=%s company(line)=%s company(move)=%s",
                    l.id, l.move_id.id if l.move_id else None, l.display_type,
                    l.product_id.id if l.product_id else None,
                    l.product_uom_id.id if l.product_uom_id else None,
                    l.company_id.id if l.company_id else None,
                    l.move_id.company_id.id if l.move_id and l.move_id.company_id else None,
                )

                # Solo tratar como sección/nota explícitamente
                if getattr(l, 'display_type', False) in ('line_section', 'line_note'):
                    l.jh_cost_unit = 0.0
                    _logger.debug("[COST] aml=%s es sección/nota => costo=0.0", l.id)
                    continue

                # Si aún no hay producto, no forzar 0: permite recomputo posterior
                if not l.product_id:
                    _logger.debug("[COST] aml=%s sin product_id aún; no se escribe costo.", l.id)
                    continue

                # Compañía efectiva
                company = (l.move_id.company_id or l.company_id or self.env.company)
                product = l.product_id.with_context(force_company=company.id).sudo()
                tmpl = product.product_tmpl_id.with_context(force_company=company.id).sudo()

                # 1) Intento por standard_price (variante -> plantilla)
                cost = product.standard_price or tmpl.standard_price or 0.0
                _logger.debug("[COST] aml=%s std_price inicial=%s (company=%s)", l.id, cost, company.id)

                # 2) Fallback duro a ir.property (product.product)
                if not cost:
                    cr.execute("""
                               SELECT value_float
                               FROM ir_property
                               WHERE name = 'standard_price'
                                 AND (type = 'float' OR type IS NULL)
                                 AND res_id = %s
                                 AND (company_id = %s OR company_id IS NULL)
                               ORDER BY company_id NULLS LAST LIMIT 1
                               """, (f'product.product,{product.id}', company.id))
                    row = cr.fetchone()
                    cost = row[0] if row and row[0] is not None else 0.0
                    _logger.debug("[COST] aml=%s ir.property -> product.product => %s", l.id, cost)

                # 3) Fallback ir.property (product.template)
                if not cost:
                    cr.execute("""
                               SELECT value_float
                               FROM ir_property
                               WHERE name = 'standard_price'
                                 AND (type = 'float' OR type IS NULL)
                                 AND res_id = %s
                                 AND (company_id = %s OR company_id IS NULL)
                               ORDER BY company_id NULLS LAST LIMIT 1
                               """, (f'product.template,{tmpl.id}', company.id))
                    row = cr.fetchone()
                    cost = row[0] if row and row[0] is not None else 0.0
                    _logger.debug("[COST] aml=%s ir.property -> product.template => %s", l.id, cost)

                # 4) Si es venta y sigue 0, último precio de compra (Vendor Bill) en la misma compañía
                if (not cost) and l.move_id and l.move_id.move_type in ('out_invoice', 'out_refund'):
                    invoice_date = l.move_id.invoice_date or fields.Date.context_today(self)
                    cr.execute("""
                               SELECT aml.price_unit
                               FROM account_move_line aml
                                        JOIN account_move m ON m.id = aml.move_id
                               WHERE aml.product_id = %s
                                 AND m.company_id = %s
                                 AND m.state = 'posted'
                                 AND m.move_type IN ('in_invoice', 'in_refund')
                                 AND (m.invoice_date IS NULL OR m.invoice_date <= %s)
                               ORDER BY COALESCE(m.invoice_date, m.date) DESC, aml.id DESC LIMIT 1
                               """, (product.id, company.id, invoice_date))
                    row = cr.fetchone()
                    last_cost = float(row[0]) if row and row[0] is not None else 0.0
                    _logger.debug("[COST] aml=%s último costo compra=%s hasta=%s", l.id, last_cost, invoice_date)
                    cost = last_cost or 0.0

                # 5) Conversión de UoM si difiere
                if cost and l.product_uom_id and l.product_uom_id != product.uom_id:
                    prev = cost
                    cost = product.uom_id._compute_price(cost, l.product_uom_id)
                    _logger.debug("[COST] aml=%s UoM convert %s -> %s (from %s to %s)",
                                  l.id, prev, cost, product.uom_id.id, l.product_uom_id.id)

                l.jh_cost_unit = cost or 0.0
                _logger.info("[COST] DONE aml=%s costo=%s", l.id, l.jh_cost_unit)

            except Exception as e:
                # Evitar fijar 0 si no era sección/nota; reportar error
                _logger.warning("[COST] ERROR aml=%s: %s", getattr(l, 'id', None), e)
                if getattr(l, 'display_type', False) in ('line_section', 'line_note'):
                    l.jh_cost_unit = 0.0

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

    def _compute_commission_settlement_date(self):
        for record in self:
            settlement_lines = self.env['commission.settlement.line'].search([
                ('invoice_line_id', '=', record.id),
            ])
            fechas = settlement_lines.mapped('settlement_id.create_date')
            record.jh_commission_settlement_date = fechas and min(fechas).date() or False

    @api.model
    def _cron_recalcular_fecha_liquidacion(self):
        _logger.info("Iniciando acción planificada: recalcular fecha de liquidación de comisión")

        try:
            # Buscar líneas de liquidación
            settlement_lines = self.env['commission.settlement.line'].search([])
            _logger.info(f"Se encontraron {len(settlement_lines)} líneas de liquidación")

            # Extraer IDs de líneas de factura
            invoice_line_ids = settlement_lines.mapped('invoice_line_id').ids
            _logger.info(f"Se encontraron {len(invoice_line_ids)} líneas de factura vinculadas")

            # Buscar líneas contables
            lines = self.env['account.move.line'].browse(invoice_line_ids)
            _logger.info(f"Procesando {len(lines)} líneas contables")

            # Ejecutar cálculo
            for line in lines:
                try:
                    _logger.debug(f"Procesando línea contable ID {line.id}")
                    line._compute_commission_settlement_date()
                    _logger.debug(f"Línea {line.id} actualizada con fecha {line.jh_commission_settlement_date}")
                except Exception as line_error:
                    _logger.warning(f"Error en línea {line.id}: {line_error}")

            _logger.info(" Acción planificada completada correctamente")

        except Exception as e:
            _logger.error(f" Error general en acción planificada de comisión: {e}")


    @api.depends('product_id')
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
                if agent_line.amount and agent_line.amount > 0.0 and percent > 0.0:
                    agent_names.add(agent_line.agent_id.name)
                    commission_amount += agent_line.amount
                    commission_percent = percent  # si hay múltiples, puedes promediar o mostrar el primero

            record.jh_agents = ', '.join(sorted(agent_names))
            record.jh_commission = commission_amount
            record.jh_commission_percent = commission_percent



    @api.model
    def _get_recalc_cursor(self):
        icp = self.env['ir.config_parameter'].sudo()
        val = icp.get_param(CURSOR_PARAM_KEY)
        try:
            return int(val) if val else 0
        except Exception:
            return 0

    @api.model
    def _set_recalc_cursor(self, last_id):
        self.env['ir.config_parameter'].sudo().set_param(CURSOR_PARAM_KEY, str(int(last_id or 0)))

    # ---------------------------
    # Selector por lotes (pendientes)
    # ---------------------------
    @api.model
    def _claim_ids_pending_skip_locked(self, limit, min_id=0):
        """
        Toma IDs pendientes (jh_tax_recalc_done = false or NULL) con impuestos,
        por encima de min_id, con FOR UPDATE SKIP LOCKED.
        """
        sql = """
            SELECT aml.id
              FROM account_move_line aml
         LEFT JOIN account_move_line_account_tax_rel rel
                ON rel.account_move_line_id = aml.id
             WHERE aml.id > %s
               AND (aml.jh_tax_recalc_done IS NOT TRUE)
               AND rel.account_tax_id IS NOT NULL
               AND COALESCE(aml.price_subtotal, aml.balance, 0) <> 0
          ORDER BY aml.id
             FOR UPDATE SKIP LOCKED
             LIMIT %s
        """
        self.env.cr.execute(sql, (min_id, limit))
        return [r[0] for r in self.env.cr.fetchall()]

    # ---------------------------
    # Cron por bloques (cada minuto)
    # ---------------------------
    @api.model
    def cron_recalcular_valor_iva(self):
        start_ts = time.time()

        # Evitar solapamiento
        self.env.cr.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_KEY_IVA,))
        if not self.env.cr.fetchone()[0]:
            _logger.info("Otro worker ya ejecuta cron_recalcular_valor_iva; salgo.")
            return

        last_id = self._get_recalc_cursor()
        total_proc = 0
        batches = 0

        try:
            while True:
                # Presupuestos
                if (time.time() - start_ts) >= TIME_BUDGET_SEC:
                    _logger.info("Presupuesto de tiempo agotado (~%ss). Corto.", TIME_BUDGET_SEC)
                    break
                if batches >= MAX_BATCHES_PER_RUN:
                    _logger.info("Máx. lotes por corrida alcanzado (%s). Corto.", MAX_BATCHES_PER_RUN)
                    break

                # 1) Intento desde el cursor hacia adelante
                ids = self._claim_ids_pending_skip_locked(BATCH_SIZE, min_id=last_id)

                # 2) Si no hay más por encima del cursor, reinicio cursor y pruebo desde el inicio
                if not ids:
                    if last_id != 0:
                        last_id = 0
                        ids = self._claim_ids_pending_skip_locked(BATCH_SIZE, min_id=last_id)
                    # 3) Si tampoco hay desde 0, no quedan pendientes
                    if not ids:
                        _logger.info("No quedan líneas pendientes de recalcular IVA.")
                        break

                # Procesar lote
                batches += 1
                last_id = ids[-1]

                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        with self.env.cr.savepoint():
                            lines = self.with_context(prefetch_fields=False, recompute=False).browse(ids)

                            # Calcula y acumula updates
                            values_tax = []
                            ids_done = []
                            for ln in lines:
                                try:
                                    # calcula tu campo jh_new_tax con tu compute preferido:
                                    ln._compute_new_tax()
                                    values_tax.append((ln.jh_new_tax, ln.id))
                                    ids_done.append(ln.id)
                                except Exception as e:
                                    _logger.warning("Error en línea %s: %s", ln.id, e)

                            if values_tax:
                                # Persistir jh_new_tax en BD (opcional si es store=True ya lo hace, pero acelera)
                                self.env.cr.executemany(
                                    "UPDATE account_move_line SET jh_new_tax = %s WHERE id = %s",
                                    values_tax
                                )

                            # 2b) Actualizar jh_tax_id (evitar ordenar por name por campo JSON)
                            if ids:
                                self.env.cr.execute("""
                                                    WITH ranked AS (SELECT rel.account_move_line_id AS aml_id,
                                                                           t.id                     AS tax_id,
                                                                           ROW_NUMBER()                OVER (
                                                PARTITION BY rel.account_move_line_id
                                                ORDER BY t.sequence NULLS LAST, t.id
                                            ) AS rn
                                                                    FROM account_move_line_account_tax_rel rel
                                                                             JOIN account_tax t
                                                                                  ON t.id = rel.account_tax_id
                                                                    WHERE rel.account_move_line_id = ANY (%s))
                                                    UPDATE account_move_line aml
                                                    SET jh_tax_id = ranked.tax_id FROM ranked
                                                    WHERE aml.id = ranked.aml_id
                                                      AND ranked.rn = 1
                                                    """, (ids,))

                            # 3) Actualizar COSTO (standard_price company-dependent)
                            if ids:
                                self.env.cr.execute("""
                                                    UPDATE account_move_line aml
                                                    SET jh_cost_unit = COALESCE((SELECT ip.value_float
                                                                                 FROM ir_property ip
                                                                                 WHERE ip.name = 'standard_price'
                                                                                   AND ip.type = 'float'
                                                                                   AND ip.res_id = 'product.product,' || aml.product_id
                                                                                ::text
                                                                                    AND
                                                                                (ip.company_id = aml.company_id OR ip.company_id IS NULL)
                                                                                ORDER BY ip.company_id NULLS LAST
                                                                                LIMIT 1 ), 0)
                                                    WHERE aml.id = ANY (%s)
                                                    """, (ids,))

                            if ids_done:
                                # Marcar como hechos
                                self.env.cr.execute(
                                    "UPDATE account_move_line SET jh_tax_recalc_done = TRUE WHERE id = ANY(%s)",
                                    (ids_done,)
                                )

                        self.env.cr.commit()
                        total_proc += len(ids_done)
                        break  # lote OK
                    except (errors.DeadlockDetected, errors.SerializationFailure) as e:
                        _logger.warning(
                            "Deadlock/Serialization %s..%s (intento %s/%s): %s",
                            ids[0], ids[-1], attempt, MAX_RETRIES, e
                        )
                        self.env.cr.rollback()
                        if attempt >= MAX_RETRIES:
                            _logger.error("Desisto del lote %s..%s", ids[0], ids[-1])

            # Guardar cursor
            self._set_recalc_cursor(last_id)
            _logger.info(
                "cron_recalcular_valor_iva: %s líneas marcadas como done en %s lote(s). Último ID=%s",
                total_proc, batches, last_id
            )

        except Exception as e:
            self.env.cr.rollback()
            _logger.error("Error general en cron_recalcular_valor_iva: %s", e)
        finally:
            # Liberar lock
            try:
                self.env.cr.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_KEY_IVA,))
            except Exception:
                pass
