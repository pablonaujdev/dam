-- Run only after hr_commission_oca is installed. Preserve legacy records.
BEGIN;
DO $$
DECLARE view_name text;
BEGIN
    IF NOT EXISTS (SELECT FROM ir_module_module
                   WHERE name='hr_commission_oca' AND state='installed'
                     AND latest_version LIKE '19.%') THEN
        RAISE EXCEPTION 'Install hr_commission_oca 19 before retiring legacy views';
    END IF;
    FOREACH view_name IN ARRAY ARRAY['view_partner_form_agent','view_settlement_form'] LOOP
        IF NOT EXISTS (SELECT FROM ir_model_data d JOIN ir_ui_view v ON v.id=d.res_id
                        WHERE d.module='hr_commission_oca' AND d.name=view_name
                          AND d.model='ir.ui.view' AND v.active) THEN
            RAISE EXCEPTION 'Missing active replacement for %', view_name;
        END IF;
        UPDATE ir_ui_view v SET active=false FROM ir_model_data d
         WHERE d.module='hr_commission' AND d.name=view_name
           AND d.model='ir.ui.view' AND d.res_id=v.id AND v.active;
    END LOOP;
END $$;
COMMIT;
