-- Only for the verified migrated website copy; preserve parent/content.
-- Back up the database and all translated view architectures first.
BEGIN;
DO $$
DECLARE
    candidate record;
    candidate_count integer;
BEGIN
    SELECT count(*) INTO candidate_count
      FROM ir_ui_view child JOIN ir_ui_view parent ON parent.id = child.inherit_id
     WHERE child.key = 'theme_buzzy.s_banner'
       AND child.website_id IS NOT NULL
       AND parent.key = 'website.s_banner'
       AND parent.website_id = child.website_id;
    IF candidate_count <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one site-specific Buzzy banner; found %', candidate_count;
    END IF;
    SELECT child.id, child.active, child.arch_db AS child_arch,
           parent.arch_db AS parent_arch INTO candidate
      FROM ir_ui_view child JOIN ir_ui_view parent ON parent.id = child.inherit_id
     WHERE child.key = 'theme_buzzy.s_banner'
       AND child.website_id IS NOT NULL
       AND parent.key = 'website.s_banner'
       AND parent.website_id = child.website_id;
    IF position('//div[hasclass(''row'')]//div[2]' IN candidate.child_arch->>'en_US') = 0
       OR position('theme_buzzy/s_banner.svg' IN candidate.parent_arch->>'en_US') = 0
       OR position('row align-items-center' IN candidate.parent_arch->>'en_US') = 0 THEN
        RAISE EXCEPTION 'Banner architecture differs from reviewed POST-014; aborting';
    END IF;
    UPDATE ir_ui_view SET active = false
     WHERE id = candidate.id AND active;
    RAISE NOTICE 'POST-014: incompatible banner inheritance % disabled; parent preserved', candidate.id;
END $$;
COMMIT;
