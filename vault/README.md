# vault/

This directory holds secrets (API keys, tokens). It is git-ignored by design:
nothing in here ever lands in version control.

Conventions:
- Prefer environment variables (e.g. `MYMILO_CLOUD_API_KEY`) over files.
- If a file is unavoidable, keep it here with `0600` permissions and reference
  it from the environment, never from `config/`.
- `config/mymilo.toml` names the *variable* (`api_key_env`); the *value* lives
  here or in the process environment.

Nothing read from this directory is ever logged.
