-- Run with web stopped, after backup. Cancels requests, not module data.
-- Legacy namespaces/data transitions remain explicitly pending in POST-015.
BEGIN;
DO $$
DECLARE target_names text[] := ARRAY['commission','account_commission',
    'hr_commission','account_payment_partner','dam_website_page_porter',
    'sale_product_template_tags'];
BEGIN
    IF (SELECT count(*) FROM ir_module_module WHERE name=ANY(target_names)) <> 6
       OR EXISTS (SELECT FROM ir_module_module WHERE name=ANY(target_names)
                  AND state NOT IN ('installed','to upgrade')) THEN
        RAISE EXCEPTION 'Unexpected legacy module inventory/state; review before applying';
    END IF;
    IF EXISTS (SELECT FROM ir_module_module WHERE state IN ('to install','to upgrade','to remove')
               AND NOT(name=ANY(target_names))) THEN
        RAISE EXCEPTION 'Other pending operations exist; do not clear partial-update marker';
    END IF;
    UPDATE ir_module_module SET state='installed'
     WHERE name=ANY(target_names) AND state='to upgrade';
    DELETE FROM ir_config_parameter WHERE key='base.partially_updated_database';
END $$;
COMMIT;
