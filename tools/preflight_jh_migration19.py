"""Inspect a migration copy with SELECT-only SQL; never modify its data/schema."""
import argparse
import getpass
import json
import os
import pathlib
import psycopg2
from psycopg2 import sql

TABLES = ('sale_order', 'sale_order_line', 'stock_lot', 'partner_agent_rel', 'commission',
          'commission_settlement', 'commission_settlement_line', 'sale_order_line_agent',
          'account_invoice_line_agent', 'product_category_agent_commission',
          'jh_client_sheet', 'jh_client_sheet_manual', 'jh_visit',
          'jh_sales_subscription_advice', 'jh_subscription_renewal_notification')


def inspect(connection):
    result = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_setting('transaction_read_only')")
        result['database'], result['read_only'] = cursor.fetchone()
        if result['read_only'] != 'on':
            raise RuntimeError('Read-only transaction required')
        cursor.execute("SELECT name, state, latest_version FROM ir_module_module WHERE name = ANY(%s) ORDER BY name",
            (['commission', 'account_commission', 'sale_commission', 'commission_oca',
              'account_commission_oca', 'sale_commission_oca', 'sale_purchase_lot',
              'commission_by_category', 'miac_renovation_subscription', 'miac_line_subscription', 'jh_sales_subscription'],))
        result['modules'] = cursor.fetchall()
        counts = {}
        for table in TABLES:
            cursor.execute('SELECT to_regclass(%s)', (table,))
            if cursor.fetchone()[0]:
                cursor.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(table)))
                counts[table] = cursor.fetchone()[0]
        result['counts'] = counts
        cursor.execute("""SELECT table_name, column_name, data_type
            FROM information_schema.columns WHERE table_schema='public'
            AND ((table_name='jh_client_sheet_manual' AND column_name='jh_account_move')
              OR (table_name='jh_visit' AND column_name='commercial_id')
              OR (table_name='sale_order_line' AND column_name IN ('product_uom','product_uom_id','lot_id','main_line_id','discount','technical_price_unit','jh_discount_manual')))
            ORDER BY table_name, column_name""")
        result['columns'] = cursor.fetchall()
        cursor.execute("""SELECT conrelid::regclass::text, conname, confrelid::regclass::text, pg_get_constraintdef(oid)
            FROM pg_constraint WHERE contype='f'
              AND conrelid IN (to_regclass('jh_client_sheet_manual'), to_regclass('jh_visit'))
            ORDER BY conrelid, conname""")
        result['legacy_foreign_keys'] = cursor.fetchall()
        cursor.execute("""SELECT res_model, COUNT(*), SUM(file_size)
            FROM ir_attachment WHERE res_model IN ('jh.client.sheet.manual','jh.visit','sale.order')
            GROUP BY res_model ORDER BY res_model""")
        result['attachments'] = cursor.fetchall()
        cursor.execute("""SELECT company_id, COUNT(*), SUM(amount_untaxed), SUM(amount_total)
            FROM sale_order WHERE subscription_state IS NOT NULL GROUP BY company_id ORDER BY company_id""")
        result['subscription_totals'] = cursor.fetchall()
        cursor.execute("""SELECT module, COUNT(*) FROM ir_model_data
            WHERE module = ANY(%s) GROUP BY module ORDER BY module""",
            (['commission','account_commission','sale_commission','commission_oca','account_commission_oca','sale_commission_oca',
              'jh_sales_subscription','sale_purchase_lot','commission_by_category','miac_renovation_subscription','miac_line_subscription'],))
        result['xmlid_counts'] = cursor.fetchall()
        cursor.execute("""SELECT name, COUNT(*) FROM ir_model_fields
            WHERE model='res.partner' AND name IN ('agent_ids','commission_agent_ids') GROUP BY name""")
        result['partner_agent_fields'] = cursor.fetchall()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='sale_order_line'")
        columns = {row[0] for row in cursor.fetchall()}
        uom = 'product_uom_id' if 'product_uom_id' in columns else 'product_uom'
        extras = [name for name in ('lot_id', 'main_line_id', 'technical_price_unit', 'jh_discount_manual') if name in columns]
        query = sql.SQL("SELECT line.id, line.order_id, line.product_id, line.price_unit, line.discount, line.product_uom_qty, line.{uom}, orders.company_id, orders.currency_id, orders.plan_id, orders.pricelist_id {extras} FROM sale_order_line line JOIN sale_order orders ON orders.id=line.order_id ORDER BY line.id").format(
            uom=sql.Identifier(uom),
            extras=sql.SQL('').join(sql.SQL(', line.{}').format(sql.Identifier(name)) for name in extras))
        cursor.execute(query)
        result['pricing_snapshot_columns'] = [description.name for description in cursor.description]
        result['pricing_snapshot_rows'] = cursor.fetchall()
        if 'partner_agent_rel' in counts:
            cursor.execute('SELECT partner_id, agent_id FROM partner_agent_rel ORDER BY partner_id, agent_id')
            result['partner_agent_pairs'] = cursor.fetchall()

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=5432)
    parser.add_argument('--user', default='openpg')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    password = os.environ.get('JH_PREFLIGHT_PASSWORD') or getpass.getpass('Password (not stored): ')
    connection = psycopg2.connect(host=args.host, port=args.port, dbname=args.database,
        user=args.user, password=password, connect_timeout=10,
        options='-c default_transaction_read_only=on -c statement_timeout=60000')
    try:
        connection.set_session(readonly=True, autocommit=False)
        report = inspect(connection)
        connection.rollback()
    finally:
        connection.close()
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('Read-only preflight saved:', args.output)


if __name__ == '__main__':
    main()
