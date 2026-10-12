-- POST-012: solo en la copia V19, con respaldo y web detenido.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
DO $miac$
DECLARE field_id integer; current_related text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Esta correccion exige la copia V19';
    END IF;
    SELECT f.id, f.related INTO field_id, current_related
    FROM ir_model_fields f JOIN ir_model_data d
      ON d.model = 'ir.model.fields' AND d.res_id = f.id
    WHERE f.model = 'account.move' AND f.name = 'x_studio_agente'
      AND f.state = 'manual' AND f.ttype = 'char' AND f.store
      AND d.module = 'studio_customization'
      AND d.name = 'nuevo_campo_relacion_2776226f-a343-4393-b096-4d0ac094f523'
    FOR UPDATE OF f;
    IF field_id IS NULL THEN RAISE EXCEPTION 'No existe el campo Studio esperado'; END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids' AND ttype = 'many2many') THEN
        RAISE EXCEPTION 'No existe el campo actual de agentes';
    END IF;
    IF current_related = 'partner_id.agent_ids.name' THEN
        UPDATE ir_model_fields SET related = 'partner_id.commission_agent_ids.name'
        WHERE id = field_id;
    ELSIF current_related = 'partner_id.commission_agent_ids.name' THEN
        RAISE NOTICE 'La relacion ya esta corregida';
    ELSE
        RAISE EXCEPTION 'Relacion inesperada: %', current_related;
    END IF;
END;
$miac$;
COMMIT;
