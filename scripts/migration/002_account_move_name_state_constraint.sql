-- Preparacion exclusiva de la copia MIAC V17 destinada a Odoo Upgrade.
-- No cambia documentos; retira solo el CHECK OCA que bloquea el upgrade nativo.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $miac$
DECLARE
    definition text;
    constraint_type "char";
    expected_definition text := $definition$CHECK ((((COALESCE(name, ''::character varying))::text <> ALL (ARRAY[('/'::character varying)::text, (''::character varying)::text])) OR ((state)::text <> 'posted'::text)))$definition$;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'base' AND state = 'installed'
                   AND latest_version LIKE '17.%') THEN
        RAISE EXCEPTION 'Este script exige una copia de origen Odoo 17';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ir_module_module
                   WHERE name = 'account_move_name_sequence' AND state = 'installed') THEN
        RAISE EXCEPTION 'No esta instalado el modulo de secuencia esperado';
    END IF;
    IF (SELECT count(*) FROM ir_model_constraint c
        JOIN ir_module_module m ON m.id = c.module
        WHERE c.name = 'account_move_name_state_diagonal'
          AND m.name = 'account_move_name_sequence') <> 1 THEN
        RAISE EXCEPTION 'Propiedad de la restriccion inesperada; revisar manualmente';
    END IF;
    LOCK TABLE account_move IN ACCESS EXCLUSIVE MODE;
    IF EXISTS (SELECT 1 FROM account_move
               WHERE state = 'posted' AND coalesce(name, '') IN ('', '/')) THEN
        RAISE EXCEPTION 'Existen asientos contabilizados sin numero: revisar antes de retirar la restriccion';
    END IF;
    SELECT pg_get_constraintdef(oid), contype INTO definition, constraint_type
    FROM pg_constraint WHERE conrelid = 'account_move'::regclass
      AND conname = 'account_move_name_state_diagonal';
    IF definition IS NULL THEN
        RAISE NOTICE 'Restriccion ya retirada; no hay cambios';
    ELSE
        IF constraint_type <> 'c' OR definition <> expected_definition THEN
            RAISE EXCEPTION 'La definicion no coincide con el CHECK OCA revisado: %', definition;
        END IF;
        ALTER TABLE account_move DROP CONSTRAINT account_move_name_state_diagonal;
        RAISE NOTICE 'Retirado exclusivamente el CHECK OCA; documentos y metadatos del modulo conservados';
    END IF;
END;
$miac$;
SELECT count(*) AS constraint_remaining FROM pg_constraint
WHERE conrelid = 'account_move'::regclass AND conname = 'account_move_name_state_diagonal';
SELECT count(*) AS posted_without_name FROM account_move
WHERE state = 'posted' AND coalesce(name, '') IN ('', '/');
COMMIT;
