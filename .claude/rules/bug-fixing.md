# Bug Fixing Protocol

## Step 1: Identify Layer

Locate the bug in one of these layers before touching code:

- **UI** — template, JS, CSS
- **API** — serializer, view, URL routing
- **Service** — business logic, transactions
- **DB** — schema, migration, query plan
- **Payment** — gateway integration, webhook handling

## Step 2: Reproduce

- Reproduce on staging — never debug on production
- Capture full request/response logs
- Trace the request lifecycle (middleware → view → service → DB)
- Save the reproduction recipe (URL, payload, user state) before fixing

## Step 3: Root Cause Fix

- Fix the logic, not the symptom
- Never patch views directly for business bugs — fix in the service layer
- Add a regression test that fails before the fix and passes after
- If the root cause spans layers, document the contract being violated

## Step 4: Validate Commerce Impact

Before merging any fix that touches `cart`, `checkout`, `orders`, `payments`,
`shipping`, or `invoices`, verify:

- **Cart integrity** — totals, item snapshots, expiry behavior
- **Order consistency** — state transitions remain append-only
- **Payment correctness** — webhook idempotency still holds
- **Inventory consistency** — no double-decrement, no negative stock

## Forbidden Quick-Fixes

- ❌ Catching and silencing exceptions to "make the error go away"
- ❌ Adding `if/else` in templates to hide broken data
- ❌ Editing migrations that have already shipped
- ❌ Marking a payment as paid without a verified webhook
- ❌ Mutating an existing order row instead of inserting a state-change record
