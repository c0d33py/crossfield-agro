# UI / UX Rules

## Design Language

Agro-industrial premium. Conveys: scale, reliability, scientific rigor, trust.

- **Palette**: deep agro-green, charcoal, white, accent gold — no neon, no playful pastels
- **Typography**: one serif for headings (corporate authority), one geometric sans for body
- **Imagery**: high-resolution field/factory/product shots, never stock-photo cliches
- **Whitespace**: generous; B2B buyers scan, they don't browse
- **Iconography**: line icons, consistent stroke weight

## Responsive

- **Mobile-first** — design at 360px, scale up
- Breakpoints: 360, 768, 1024, 1280, 1536
- Touch targets ≥ 44×44px
- Navigation collapses to hamburger below 768px
- Product grids: 1 col mobile → 2 col tablet → 3–4 col desktop

## Interaction Performance

- UI feedback < 100ms (perceived instant)
- Skeleton loaders, not spinners, for content placeholders
- Optimistic UI for cart add/remove
- No layout shift on image load (always reserve dimensions)
- Hover states only where mouse is present (`@media (hover: hover)`)

## Commerce UX

- "Add to Cart" gives immediate visual confirmation + cart badge update
- Cart drawer / mini-cart accessible from every page header
- Checkout: single-page or 3-step max — no surprise steps
- Price always visible with currency + tax inclusivity disclosure
- Shipping cost shown before payment step
- Order confirmation page after success, plus email

## Forms

- Inline validation on blur, not on every keystroke
- Errors near the field, in red, with icon
- Required fields marked with `*`
- Address fields ordered by Pakistani postal convention
- Phone: country-code prefixed, validated server-side
- Disable submit button during submission to prevent double-post

## Accessibility (WCAG 2.1 AA)

- Color contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text
- All interactive elements keyboard-reachable
- Focus indicators visible (don't `outline: none` without replacement)
- `alt` on every meaningful image; `alt=""` on decorative
- ARIA labels where semantic HTML is insufficient
- Form labels associated via `for`/`id`

## Content

- Headings describe content, not marketing fluff
- CTAs are verbs: "Request Quote", "Add to Cart", "Contact Sales"
- Product descriptions: specs first, marketing second
- No autoplay video with sound
- No modal popups within 10s of page load
