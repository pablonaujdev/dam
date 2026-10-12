-- MIAC 17 -> 19. Ejecutar en la copia V17 antes de exportarla a Odoo Upgrade.
-- Solo cambia la propiedad de un XML ID; no elimina campos ni columnas.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $miac$
DECLARE
    field_id integer;
    xmlid_id integer;
    owner text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND state = 'installed'
                   AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Este script exige una base de origen Odoo 17';
    END IF;
    IF (SELECT count(*) FROM ir_module_module
        WHERE name IN ('account_payment_sale', 'sale_subscription')
        AND state = 'installed') <> 2 THEN
        RAISE EXCEPTION 'Deben estar instalados account_payment_sale y sale_subscription';
    END IF;
    SELECT id INTO field_id FROM ir_model_fields
    WHERE model = 'sale.subscription.report' AND name = 'payment_mode_id'
      AND ttype = 'many2one' AND relation = 'account.payment.mode' AND state = 'base'
    FOR UPDATE;
    IF field_id IS NULL THEN
        RAISE EXCEPTION 'No se encuentra el campo esperado; revisar antes de continuar';
    END IF;
    IF (SELECT count(*) FROM ir_model_data
        WHERE model = 'ir.model.fields' AND res_id = field_id) <> 1 THEN
        RAISE EXCEPTION 'El campo debe tener exactamente un XML ID; revisar aliases';
    END IF;
    SELECT id, module INTO xmlid_id, owner FROM ir_model_data
    WHERE model = 'ir.model.fields' AND res_id = field_id
      AND name = 'field_sale_subscription_report__payment_mode_id'
      AND module IN ('sale_subscription', 'account_payment_sale') FOR UPDATE;
    IF xmlid_id IS NULL THEN
        RAISE EXCEPTION 'XML ID inesperado; no se modifica nada';
    END IF;
    IF owner = 'sale_subscription' THEN
        IF EXISTS (SELECT 1 FROM ir_model_data
                   WHERE module = 'account_payment_sale'
                   AND name = 'field_sale_subscription_report__payment_mode_id') THEN
            RAISE EXCEPTION 'El XML ID destino ya existe: revisar colision';
        END IF;
        UPDATE ir_model_data SET module = 'account_payment_sale'
        WHERE id = xmlid_id;
        RAISE NOTICE 'Corregido XML ID %, campo %; no se modifica ir_model_fields', xmlid_id, field_id;
    ELSE
        RAISE NOTICE 'Correccion ya aplicada; no hay cambios';
    END IF;
END;
$miac$;
SELECT f.id AS field_id, f.model, f.name, d.id AS xmlid_id,
       d.module, d.name AS xmlid, d.noupdate
FROM ir_model_fields f JOIN ir_model_data d
ON d.model = 'ir.model.fields' AND d.res_id = f.id
WHERE f.model = 'sale.subscription.report' AND f.name = 'payment_mode_id';
COMMIT;
