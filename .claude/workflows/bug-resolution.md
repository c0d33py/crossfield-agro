# Bug Resolution Workflow

Use this in tandem with `rules/bug-fixing.md`.

## 1. Triage

- Severity:
  - **P0** — payment failure, data loss, security breach, site down
  - **P1** — broken commerce flow, broken auth, broken admin
  - **P2** — broken non-critical feature
  - **P3** — cosmetic, edge case
- Confirm reporter, environment (prod/staging), timestamp, affected user count

## 2. Reproduce

- Reproduce in staging with the reported recipe
- Capture:
  - Request URL, method, headers, body
  - Response status, body
  - Server log excerpt
  - DB state snapshot (relevant rows)
  - User session state
- If you cannot reproduce, treat as a data-issue bug and inspect production DB read-only

## 3. Isolate Layer

Per `rules/bug-fixing.md`: UI / API / Service / DB / Payment.

## 4. Write Failing Test

Before writing the fix, write the test that exposes the bug. The test should:
- Fail on `main`
- Pass after the fix
- Live in the appropriate `tests/` subfolder

## 5. Fix Root Cause

- Fix in the layer that owns the bug — not the layer where it surfaced
- If the fix spans layers, the deeper layer is usually the right one
- Never silence the symptom (try/except pass, template if/else hide)

## 6. Commerce Bugs — Extra Validation

For any bug in `cart`, `checkout`, `orders`, `payments`, `shipping`, `invoices`:

- [ ] Cart totals still recompute correctly
- [ ] Order events still append-only
- [ ] Webhook handler still idempotent
- [ ] No path leads to an order marked paid without a webhook
- [ ] No path leads to negative stock or double-decrement
- [ ] Existing in-flight orders unaffected (test with fixture data)

## 7. Backport / Hotfix

- P0/P1: cherry-pick to release branch, deploy out-of-band
- P2/P3: queue for next scheduled release

## 8. Postmortem (P0/P1 only)

- Root cause (what)
- Trigger (why now)
- Detection (how we found out)
- Resolution (what we did)
- Prevention (what changes — code, test, monitoring, process)
- File in `docs/postmortems/` with date

## 9. Close the Loop

- Notify reporter with resolution
- Add monitoring/alert if the bug class could recur silently
- Update `.claude/` rules if the bug exposed a missing guardrail
