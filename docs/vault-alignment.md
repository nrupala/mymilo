# Vault alignment (MyMilo × KalaBodha)

Converged 2026-10-06: **MyMilo is the resident buddy; KalaBodha is the
vault it keeps secrets in.** This document states the shared zero-trust
pattern — aligned, not invented (maven transfer #7).

## Secret resolution order (implemented in `Settings.api_key_for`)

1. **Environment variable** named by the route's `api_key_env` — always
   wins. This is the default and preferred path.
2. **Vault file fallback**: if the env var is unset and `[vault] path` is
   configured, read the file `<vault-path>/<API_KEY_ENV>` (e.g.
   `vault/MYMILO_CLOUD_API_KEY`). The file holds the raw secret, nothing
   else.
3. **Otherwise**: no key — the route is used without `Authorization`.

## What MyMilo never does

- Never stores secrets in `config/mymilo.toml` (git-tracked example only).
- Never logs secret values — error paths truncate bodies and exclude
  headers (see ARCHITECTURE.md).
- Never sends secrets anywhere except the route's own `base_url` as a
  Bearer token.
- The `vault/` directory is git-ignored. It is the local stand-in; the
  KalaBodha vault is the system of record when it exists.

## Contract for the vault side

When KalaBodha exposes secret provisioning, it satisfies this interface
and MyMilo needs no code change beyond pointing `[vault] path` (file
mode) or adopting the vault's fetch protocol (a later phase):

- One secret per name; names are the `api_key_env` strings.
- Reads are local and synchronous at request time (no caching of secrets
  in MyMilo beyond the request).
