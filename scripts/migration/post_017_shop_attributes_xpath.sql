-- Reviewed site-specific migration correction. Back up first, stop web.
BEGIN;
DO $$
DECLARE
    target_id integer;
    matching_count integer;
    old_selector text := '//div[contains(@t-attf-class, ''products_attributes_filters'')]';
    new_selector text := '//div[hasclass(''products_attributes_filters'') or contains(@t-attf-class, ''products_attributes_filters'')]';
BEGIN
    SELECT count(*),min(c.id) INTO matching_count,target_id
      FROM ir_ui_view c JOIN ir_ui_view p ON p.id=c.inherit_id
     WHERE c.key='website_sale.products_attributes' AND c.website_id=1
       AND p.key='website_sale.products' AND p.website_id=c.website_id;
    IF matching_count <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one reviewed site attributes inheritance';
    END IF;
    IF EXISTS (SELECT FROM ir_ui_view c,LATERAL jsonb_each_text(c.arch_db) a
                WHERE c.id=target_id AND position(old_selector IN a.value)=0
                  AND position(new_selector IN a.value)=0) THEN
        RAISE EXCEPTION 'Unexpected translated architecture; review before applying';
    END IF;
    UPDATE ir_ui_view c
       SET arch_db=(SELECT jsonb_object_agg(a.key,replace(a.value,old_selector,new_selector))
                    FROM jsonb_each_text(c.arch_db) a)
     WHERE c.id=target_id AND EXISTS
           (SELECT FROM jsonb_each_text(c.arch_db) a WHERE position(old_selector IN a.value)>0);
END $$;
COMMIT;
