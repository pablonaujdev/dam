-- REVISION SOLAMENTE. NO EJECUTAR CONVERSIONES SIN AUTORIZACION Y BACKUP.
-- Estos SELECT son los primeros controles; las conversiones estan comentadas.
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND ((table_name = 'jh_client_sheet_manual' AND column_name = 'jh_account_move')
    OR (table_name = 'jh_visit' AND column_name = 'commercial_id'));

SELECT conrelid::regclass AS source_table, conname,
       confrelid::regclass AS target_table, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE contype = 'f'
  AND (conrelid IN (to_regclass('jh_client_sheet_manual'), to_regclass('jh_visit'))
       OR confrelid = to_regclass('jh_client_sheet'));

-- CASO A: SOLO si jh_account_move es un entero y su FK apunta a account_move.
-- Primero revisar SELECT, registros sin destino y significado de name.
-- SELECT old.id, old.jh_account_move AS legacy_invoice_id, move.name AS invoice_number
-- FROM jh_client_sheet_manual old LEFT JOIN account_move move ON move.id = old.jh_account_move;
-- BEGIN;
-- ALTER TABLE jh_client_sheet_manual ADD COLUMN jh_account_move_v19_text varchar;
-- UPDATE jh_client_sheet_manual old SET jh_account_move_v19_text = move.name
-- FROM account_move move WHERE move.id = old.jh_account_move;
-- VALIDACION OBLIGATORIA: no debe haber relacion no nula sin texto ni diferencias de recuentos.
-- SELECT * FROM jh_client_sheet_manual WHERE jh_account_move IS NOT NULL AND jh_account_move_v19_text IS NULL;
-- ALTER TABLE jh_client_sheet_manual RENAME COLUMN jh_account_move TO jh_account_move_legacy_id;
-- ALTER TABLE jh_client_sheet_manual RENAME COLUMN jh_account_move_v19_text TO jh_account_move;
-- La FK original permanece en jh_account_move_legacy_id; no se elimina ni se usa CASCADE.
-- COMMIT solamente tras validacion; en caso contrario ROLLBACK.

-- CASO B: SOLO si commercial_id es entero y su FK apunta a res_users.
-- SELECT visit.id, visit.commercial_id AS legacy_user_id, partner.name AS salesperson
-- FROM jh_visit visit LEFT JOIN res_users users ON users.id = visit.commercial_id
-- LEFT JOIN res_partner partner ON partner.id = users.partner_id;
-- BEGIN;
-- ALTER TABLE jh_visit ADD COLUMN commercial_id_v19_text varchar;
-- UPDATE jh_visit visit SET commercial_id_v19_text = partner.name
-- FROM res_users users JOIN res_partner partner ON partner.id = users.partner_id
-- WHERE users.id = visit.commercial_id;
-- SELECT * FROM jh_visit WHERE commercial_id IS NOT NULL AND commercial_id_v19_text IS NULL;
-- ALTER TABLE jh_visit RENAME COLUMN commercial_id TO commercial_legacy_user_id;
-- ALTER TABLE jh_visit RENAME COLUMN commercial_id_v19_text TO commercial_id;
-- COMMIT solamente tras validacion; en caso contrario ROLLBACK.

-- CASO C: SOLO si commercial_id es entero y su FK apunta a res_partner.
-- SELECT visit.id, visit.commercial_id AS legacy_partner_id, partner.name AS salesperson
-- FROM jh_visit visit LEFT JOIN res_partner partner ON partner.id = visit.commercial_id;
-- BEGIN;
-- ALTER TABLE jh_visit ADD COLUMN commercial_id_v19_text varchar;
-- UPDATE jh_visit visit SET commercial_id_v19_text = partner.name
-- FROM res_partner partner WHERE partner.id = visit.commercial_id;
-- SELECT * FROM jh_visit WHERE commercial_id IS NOT NULL AND commercial_id_v19_text IS NULL;
-- ALTER TABLE jh_visit RENAME COLUMN commercial_id TO commercial_legacy_partner_id;
-- ALTER TABLE jh_visit RENAME COLUMN commercial_id_v19_text TO commercial_id;
-- COMMIT solamente tras validacion; en caso contrario ROLLBACK.
-- No ejecutar el CASO B con ese esquema. Si el destino es otro, preparar una conversion especifica.
-- Conservar IDs de registros, referencias de adjuntos y el filestore en todos los casos.

-- PRECIOS: propuesta conservadora, SOLO en copia 19 con el campo nuevo ya presente,
-- tras revisar el snapshot por ID y antes de abrir pedidos o ejecutar crons.
-- SELECT id, price_unit, discount, technical_price_unit, jh_discount_manual
-- FROM sale_order_line WHERE display_type IS NULL ORDER BY id;
-- UPDATE sale_order_line SET jh_discount_manual = TRUE WHERE display_type IS NULL;
-- No determina que todos fueran manuales: protege las condiciones de origen.
-- La restauracion de price_unit/discount y la referencia technical_price_unit deben
-- generarse por ID desde el snapshot validado; no inferir cero como ausencia de valor.
