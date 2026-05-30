# Code Style Rules

## Python / Django Standards

- Strict PEP8 compliance
- Black formatter required (line length: 100)
- isort for imports (profile: black)
- Flake8 validation
- Type hints encouraged on service-layer and selector functions

## Architecture Rules

### Mandatory Layers

- **Views** → thin controllers only; no business logic, no ORM filters
- **Business logic** → `services/` (write paths, transactions, side effects)
- **Query logic** → `selectors/` (read paths with prefetch/select_related)
- **Validation** → `validators.py` (business rules and input shape)

Views may NOT:
- Call `.objects.filter()` directly for non-trivial queries
- Mutate the database without going through a service
- Contain pricing, tax, or order-state logic

## Commerce Rules (CRITICAL)

- Cart is temporary state only — never source of truth for an order
- Orders are immutable after creation (append-only state transitions)
- Payments must be async-confirmed via webhook — never on redirect alone
- Never trust frontend price — always recalculate server-side
- Always recalculate totals server-side from current product snapshots

## Naming Conventions

- Models: `PascalCase` (e.g. `OrderItem`)
- Files / modules: `snake_case` (e.g. `payment_service.py`)
- URLs: `kebab-case` (e.g. `/checkout/payment-confirmation/`)
- DB tables: implicit Django default (`app_modelname`) — don't override unless required
- Migrations: never edit applied migrations; squash if needed

## Imports

- Absolute imports only (`from apps.orders.services import create_order`)
- No wildcard imports
- Group: stdlib → third-party → Django → local

## Docstrings & Comments

- Public service functions: short docstring describing inputs/outputs and side effects
- Inline comments: only when the WHY is non-obvious
- Never narrate WHAT the code does — naming should carry that
