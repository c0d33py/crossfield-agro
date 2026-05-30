# Security Rules

## Baseline

- CSRF enforced on all state-changing endpoints (forms + AJAX)
- XSS sanitization — autoescape ON, never `|safe` user-supplied content
- ORM-only DB access — no raw SQL unless reviewed and parameterized
- HTTPS enforced via `SECURE_SSL_REDIRECT = True` in production
- `SECURE_HSTS_SECONDS` >= 31536000 in production
- Secret keys, DB credentials, gateway keys: env vars only — never committed

## Rate Limiting

Required on:
- Login / password reset
- Contact forms
- Checkout submission
- Payment webhook handler (per-IP burst protection — but allow gateway IPs)
- Cart "add" endpoint (prevent abuse)

Use `django-ratelimit` or equivalent. Default: 10/min/IP for sensitive endpoints.

## Commerce Security

- **Payment signature validation** — every webhook must verify HMAC/signature
- **Webhook authentication** — reject unsigned or expired webhooks
- **Order tampering prevention** — server recalculates totals; never trust posted prices
- **Idempotency** — webhook handlers must be idempotent (same event twice = one effect)
- **Admin action logging** — every admin mutation logged to `audit` app
- **Refund authorization** — refunds require staff role + audit entry

## Authentication

- Password hashing: Argon2 preferred, PBKDF2 minimum
- Session cookies: `Secure`, `HttpOnly`, `SameSite=Lax`
- Admin: 2FA required for staff accounts (django-otp)
- API tokens: scoped, rotatable, expire by default

## File Uploads

- Validate MIME type AND extension AND magic bytes
- Store outside web root or behind signed URLs
- Strip EXIF from images
- Max upload size enforced at nginx + Django levels

## Headers (production)

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: <strict per-route>
```

## Forbidden

- ❌ Logging full request bodies on payment endpoints (PII / card data)
- ❌ Storing PAN, CVV, or full card numbers anywhere
- ❌ `DEBUG=True` in production
- ❌ Wildcards in `ALLOWED_HOSTS`
- ❌ Exposing Django admin at `/admin/` in production (move to a secret path)
