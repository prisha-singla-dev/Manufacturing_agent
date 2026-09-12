Test case matrix - user-perspective, with expected response_type

#	Persona	Question (as a user would type it)	Expected type	What to check
1	inventory_manager	"Which items are below their min stock level?"	text or table	Already tested - re-verify still correct after prompt change
2	inventory_manager	"How much of [pick a real item name] do we have across all locations?"	table (per-location) or text if 1 location	Numbers match reality, location names are real
3	inventory_manager	"What's moved in and out of stock in the last 30 days for [item]?"	table	Uses inv_transactions, dates are recent given real data
4	inventory_manager	"Which locations have the most stock value?"	chart (bar)	Needs a join/calc across inv_current_stock + inv_items - good stress test
5	procurement_manager	"Which POs are pending receipt?"	table	Full list this time, not "and more"
6	procurement_manager	"Show vendor-wise total PO value"	chart (bar)	Same query as before - should now chart, not wall-of-text
7	procurement_manager	"Which vendors have we paid the most to?"	table or chart	Tests proc_po_payment_tranches
8	procurement_manager	"Are there any PO line items with a quantity mismatch on receipt?"	table	Tests proc_po_line_regularisations - real variance data exists (5 rows)
9	owner	"What's our total procurement spend this year?"	text (single number)	Should NOT come back as a table for one number
10	owner	"Give me a quick health check - any red flags in inventory or procurement?"	text	Open-ended; check it doesn't hallucinate beyond what SQL returned
11	procurement_manager	"Record a new transaction: received 50 units of [item] at [location]"	confirm_write	Tests the write path - check proposal_id is returned, and that nothing actually writes until you hit /confirm-write/{id}

write{id}
- Give me the name of one inventory item and one active location I can use for a test transaction.
 -- You can use the item "PU Flap for AFC Mechanism (Wide - Green)" and the active location "132-1" for a test transaction.

- Record that we received 50 units of PU Flap for AFC Mechanism (Wide - Green) at 132-1. This is a test.
 -- A test transaction to record the receipt of 50 units of 'PU Flap for AFC Mechanism (Wide - Green)' at location '132-1' has been proposed. Please confirm to execute this transaction.