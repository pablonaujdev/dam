-- Solo en la copia V19, con respaldo previo y el web detenido.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
DO $miac$
DECLARE column_type text; company_args text; studio_view integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'base'
                   AND latest_version LIKE '19.%' AND state = 'installed') THEN
        RAISE EXCEPTION 'Este ajuste exige la copia migrada V19';
    END IF;
    SELECT data_type INTO column_type FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'res_partner'
      AND column_name = 'not_in_mod347';
    IF column_type = 'boolean' THEN
        LOCK TABLE res_company IN SHARE MODE;
        LOCK TABLE res_partner IN ACCESS EXCLUSIVE MODE;
        SELECT string_agg(format('%L, not_in_mod347', id::text), ', ' ORDER BY id)
          INTO company_args FROM res_company;
        IF company_args IS NULL THEN RAISE EXCEPTION 'No existen companias'; END IF;
        ALTER TABLE res_partner ALTER COLUMN not_in_mod347 DROP DEFAULT;
        EXECUTE format('ALTER TABLE res_partner ALTER COLUMN not_in_mod347 TYPE jsonb
          USING CASE WHEN not_in_mod347 IS NULL THEN NULL
          ELSE jsonb_build_object(%s) END', company_args);
        RAISE NOTICE 'Indicador compartido conservado por cada compania actual';
    ELSIF column_type = 'jsonb' THEN
        RAISE NOTICE 'Indicador ya convertido; no se modifica';
    ELSE
        RAISE EXCEPTION 'Tipo de columna inesperado: %', column_type;
    END IF;
    SELECT v.id INTO studio_view FROM ir_ui_view v JOIN ir_model_data d
      ON d.model = 'ir.ui.view' AND d.res_id = v.id
    WHERE d.module = 'studio_customization'
      AND d.name = 'odoo_studio_res_part_ba3d9bec-174c-46a2-92cf-944a3362972b'
      AND v.model = 'res.partner' AND v.type = 'list' FOR UPDATE OF v;
    IF studio_view IS NULL THEN
        RAISE EXCEPTION 'No existe la vista Studio esperada; revisar antes de continuar';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_model_fields WHERE model = 'res.partner'
                   AND name = 'commission_agent_ids') THEN
        RAISE EXCEPTION 'No existe el campo vigente de agentes';
    END IF;
    UPDATE ir_ui_view v SET arch_db = (
        SELECT jsonb_object_agg(lang, replace(xml, 'name="agent_ids"', 'name="commission_agent_ids"'))
        FROM jsonb_each_text(v.arch_db) AS arch(lang, xml)
    ) WHERE v.id = studio_view AND EXISTS (
        SELECT 1 FROM jsonb_each_text(v.arch_db) AS arch(lang, xml)
        WHERE strpos(xml, 'name="agent_ids"') > 0
    );
END;
$miac$;
COMMIT;
