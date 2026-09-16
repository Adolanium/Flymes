# Search fixture

This intentionally introduced bug makes a shopping list search case-sensitive.
Fix `visible_items(items, query)` in `app.py` so matching ignores case, preserves
input order, and returns all items for an empty query. Do not change the inputs.
The independent regression checks live outside this editable workspace.
