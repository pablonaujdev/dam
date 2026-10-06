"""Real PostgreSQL concurrency test. Execute through Odoo shell in the clean test DB only.

Creates dedicated ORM fixtures, commits two concurrent test transactions, then
removes its own draft moves, wizards, accounts and journal. Never targets MIAC.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from io import BytesIO
import json
import threading
import time
import uuid

import openpyxl
from odoo import api, Command


def run_initial_import_concurrency(environment):
    if environment.cr.dbname != 'miac_import19_clean':
        raise RuntimeError('This test is restricted to miac_import19_clean.')
    registry, uid = environment.registry, environment.uid
    company_id = environment.company.id
    context = {'allowed_company_ids': [company_id], 'tracking_disable': True,
               'mail_create_nosubscribe': True, 'mail_create_nolog': True}
    token = uuid.uuid4().hex[:10]
    source = 'CONCURRENT-' + token
    account_ids, journal_id = [], None
    executor = ThreadPoolExecutor(max_workers=1)
    result = {}
    try:
        with registry.cursor() as cr:
            fixture_env = api.Environment(cr, uid, context)
            accounts = fixture_env['account.account'].create([
                {'name': 'Import concurrency debit ' + token, 'code': 'ICD' + token,
                 'account_type': 'expense', 'company_ids': [Command.set([company_id])]},
                {'name': 'Import concurrency credit ' + token, 'code': 'ICC' + token,
                 'account_type': 'income', 'company_ids': [Command.set([company_id])]},
            ])
            journal = fixture_env['account.journal'].create({
                'name': 'Import concurrency ' + token, 'type': 'general',
                'code': 'I' + token[:4], 'company_id': company_id,
            })
            account_ids, journal_id = accounts.ids, journal.id
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(['ASIENTO', 'FECHA', 'DEBIT', 'CREDIT', 'Empresa', 'CUENTA', 'DESCRIPCION'])
            sheet.append([source, date(2026, 2, 1), 100, 0, None, accounts[0].code, 'Debit'])
            sheet.append([source, date(2026, 2, 1), 0, 100, None, accounts[1].code, 'Credit'])
            buffer = BytesIO()
            workbook.save(buffer)
            workbook.close()
            values = {'upload_file': base64.b64encode(buffer.getvalue()), 'file_name': 'concurrent.xlsx',
                      'date': date(2026, 1, 1), 'journal_id': journal_id}
            cr.commit()

        ready = threading.Event()
        backend = {}

        def second_import():
            with registry.cursor() as cr:
                second_env = api.Environment(cr, uid, context)
                cr.execute('SELECT pg_backend_pid()')
                backend['pid'] = cr.fetchone()[0]
                wizard = second_env['import.initial.account.move.wiz'].create(values)
                ready.set()
                action = wizard.import_xls_file()
                errors = []
                if action['res_model'] == 'error.log.wiz':
                    errors = second_env['error.log.wiz'].browse(action['res_id']).error_line_ids.mapped('error')
                cr.commit()
                return action['res_model'], errors

        with registry.cursor() as first_cr:
            first_env = api.Environment(first_cr, uid, context)
            action = first_env['import.initial.account.move.wiz'].create(values).import_xls_file()
            assert action['res_model'] == 'account.move', action
            future = executor.submit(second_import)
            assert ready.wait(timeout=10), 'Second transaction did not start.'
            blocked = False
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    with registry.cursor() as observer:
                        observer.execute('SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s', (backend['pid'],))
                        row = observer.fetchone()
                        blocked = bool(row and row[0] == 'Lock')
                    if blocked:
                        break
                    time.sleep(0.05)
            finally:
                # Release the unique-index wait even if the observation fails.
                first_cr.commit()
            second_model, errors = future.result(timeout=20)
            assert blocked, 'The second transaction did not reach the unique-index lock.'
            assert second_model == 'error.log.wiz' and errors, (second_model, errors)
            assert any('concurrent' in message or 'already exists' in message for message in errors), errors
        with registry.cursor() as cr:
            check_env = api.Environment(cr, uid, context)
            count = check_env['account.move'].search_count([('import_initial_asiento', '=', source)])
            assert count == 1, count
        result = {'concurrent_imports': 2, 'created_entries': 1, 'second_import_rejected': True,
                  'unique_index_lock_observed': True}
    finally:
        executor.shutdown(wait=True)
        if journal_id:
            with registry.cursor() as cr:
                cleanup_env = api.Environment(cr, uid, context)
                cleanup_env['account.move'].search([('journal_id', '=', journal_id)]).unlink()
                cleanup_env['import.initial.account.move.wiz'].search([('journal_id', '=', journal_id)]).unlink()
                cleanup_env['error.log.wiz'].search([('error_line_ids.error', 'ilike', source)]).unlink()
                cleanup_env['account.journal'].browse(journal_id).unlink()
                cleanup_env['account.account'].browse(account_ids).unlink()
                cr.commit()
        with registry.cursor() as cr:
            check_env = api.Environment(cr, uid, context)
            assert not check_env['account.move'].search_count([('import_initial_asiento', '=', source)])
        result['test_entries_remaining'] = 0
    print(json.dumps(result, ensure_ascii=False))


run_initial_import_concurrency(env)
