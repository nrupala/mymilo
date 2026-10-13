---
name: authentication-authorization
description: Do auth properly — passkeys/MFA, sound sessions and tokens, least-privilege authorization, lifecycle.
version: 1
triggers: authentication, authorization, passkeys, mfa, sessions, tokens, login security
category: Security & privacy
blurb: Do sign-in properly — passkeys and MFA, sound sessions, and least-privilege access.
archetype: knowledge
example: Review the auth design for my app before I ship it.
---

# Authentication & Authorization

Prove identity once, check permission every time. AuthN without authZ is a doorman who never checks the guest list.

## When to use
- Adding login, sessions, tokens, or permissions to anything.
- Reviewing SSO/OIDC integrations and API auth.
- Designing account lifecycle (provision → review → revoke).

## Method
1. **Humans — strong first**: passkeys/WebAuthn preferred; MFA enforced for admin and sensitive ops; passwords (when unavoidable) long not complex, hashed with Argon2id (or bcrypt cost-tuned).
2. **Sessions**: secure, HttpOnly, SameSite cookies; rotate on login/privilege change; expire sensibly; server-side revocation list works.
3. **OAuth2/OIDC done right**: authorization code + PKCE; exact redirect allowlists; validate `iss/aud/exp`; no implicit flow; refresh tokens rotated (sender-constrained where possible).
4. **Tokens for services**: short-lived, scoped, audience-bound; JIT issuance over long-lived keys; rotate + revoke paths tested.
5. **Authorization server-side, always**: per-endpoint permission checks; RBAC roles for coarse, ABAC/policies (OPA-style) for fine; deny by default; never trust the UI.
6. **Lifecycle**: provisioning reviewed; deprovisioning is a checklist (tokens revoked, keys rotated); access reviews on schedule for admin surfaces.
7. **Anti-abuse**: rate-limit login + token endpoints; lockout policies balanced (no user-lockout DoS); alert on anomalies (new geo, spikes).
8. **Audit**: authN events (success/fail), authZ denials, permission changes — logged with actor + context.

## Quality gates
- [ ] Admin surfaces require MFA/passkey; no shared accounts.
- [ ] Every endpoint performs a server-side authorization check.
- [ ] Token lifetimes + scopes documented; revocation tested.
- [ ] Deprovisioning runbook exists and was exercised once.

## Red lines
- No hand-rolled crypto or auth protocols; no client-side-only authorization; no long-lived unrevocable credentials.

## Related
`secrets-management` · `zero-trust-architecture` · `backend-engineering`.
