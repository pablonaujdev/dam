-- Ensayo V19: retirar solo la vista V17 duplicada, conservando todos sus registros.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
DO $miac$
DECLARE old_view integer; new_view integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Este ajuste exige la copia migrada V19';
    END IF;
    SELECT v.id INTO old_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'commission' AND d.name = 'view_partner_form_agent'
      AND v.model = 'res.partner' FOR UPDATE OF v;
    SELECT v.id INTO new_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'commission_oca' AND d.name = 'view_partner_form_agent'
      AND v.model = 'res.partner' AND v.active
      AND v.arch_db::text LIKE '%commission_agent_ids%';
    IF old_view IS NULL OR new_view IS NULL OR old_view = new_view THEN
        RAISE EXCEPTION 'No existe el par de vistas V17/V19 esperado; no se modifica nada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids') THEN
        RAISE EXCEPTION 'No existe el campo actual de agentes';
    END IF;
    IF EXISTS (SELECT 1 FROM ir_ui_view WHERE id = old_view AND active) THEN
        UPDATE ir_ui_view SET active = false WHERE id = old_view;
        RAISE NOTICE 'Vista V17 % retirada; vista V19 % conservada', old_view, new_view;
    ELSE
        RAISE NOTICE 'La vista V17 ya esta inactiva; no hay cambios';
    END IF;
END;
$miac$;
COMMIT;
