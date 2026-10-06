This module extends the functionality of sale_commission_oca to allow you to
auto-populate salesmen as commission agents without setting explicitly
them on the customer.

**IMPORTANT**: The salesman will be only populated if no other
commission agent is set via other method, to assure that there's no
overlapping commissions.

Local migration to Odoo 19 from the OCA 17 source included in the MIAC backup.
The preparation hook is shared by OCA and MIAC/JH, without depending on JH.
Changing the salesman preserves existing agents; use **Regenerate agents** on
editable documents to apply the new salesman. Commission-free products, sections,
notes, purchase documents and journal entries do not receive the salesman fallback.
