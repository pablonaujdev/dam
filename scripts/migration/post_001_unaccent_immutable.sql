-- Solo en el PostgreSQL del nuevo ensayo V19, antes de restaurar los indices.
-- Mismo ajuste aplicado por odoo/service/db.py al preparar una base Odoo.
\set ON_ERROR_STOP on
BEGIN;
DO $guard$
BEGIN
    IF to_regprocedure('public.unaccent(text)') IS NULL THEN
        RAISE EXCEPTION 'No existe la extension unaccent esperada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc
                   WHERE oid = 'public.unaccent(text)'::regprocedure
                     AND provolatile IN ('s', 'i')) THEN
        RAISE EXCEPTION 'Funcion unaccent inesperada: revisar antes de continuar';
    END IF;
END;
$guard$;
ALTER FUNCTION public.unaccent(text) IMMUTABLE;
SELECT proname, provolatile FROM pg_proc
WHERE oid = 'public.unaccent(text)'::regprocedure;
COMMIT;
