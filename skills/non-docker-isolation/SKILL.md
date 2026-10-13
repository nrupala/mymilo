---
name: non-docker-isolation
description: Isolate services and untrusted code without Docker — systemd hardening, sandboxes, WASM, least privilege.
version: 1
triggers: isolation without docker, systemd sandbox, run untrusted code, sandboxing
category: Security & privacy
blurb: Isolate services and untrusted code without Docker — systemd hardening, sandboxes, least privilege.
archetype: knowledge
example: How do I sandbox an untrusted script without containers?
---

# Non-Docker Isolation

House rule: **no Docker in application code**; Podman only as a last resort for stateful infra; systemd services on owned machines are the default. Isolation still matters — do it with the OS, not a daemon.

## When to use
- Deploying a service or tool that should run contained.
- Executing untrusted or semi-trusted code (plugins, user scripts, parsers).
- Hardening existing services running as root or with broad access.

## Method
1. **Least-privilege accounts**: one service, one non-login system user; no cross-service file access.
2. **systemd hardening** (Linux default): `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, `DynamicUser`, `CapabilityBoundingSet=`, `SystemCallFilter=@system-service`, `RestrictAddressFamilies`, `ReadWritePaths=` only what's needed.
3. **Sandbox tools**: `bubblewrap`/`nsjail`/`firejail` for one-off execution; namespaces for filesystem/network separation; `chroot` only with care (classic escape history).
4. **MAC profiles**: AppArmor/SELinux confinement for anything exposed; audit denials, don't blanket-disable.
5. **Resource limits**: cgroups v2 (CPU/mem/IO), `ulimit`, timeouts, restart limits — a runaway should kill itself, not the host.
6. **WASM/WASI** for untrusted plugin logic; microVMs (Firecracker-class) when kernel isolation is the requirement.
7. **Windows equivalents**: dedicated low-privilege accounts, AppContainer, Windows Sandbox for risky tooling, Job Objects for limits.
8. **Egress + monitoring**: restrict outbound; log exec/spawn events; a kill switch per service.

## Quality gates
- [ ] Services run non-root with minimal capabilities and filesystem scope.
- [ ] Resource limits set; runaway behavior tested.
- [ ] Escape/abuse cases exercised (sandbox actually blocks).
- [ ] Egress restricted where the service doesn't need the world.

## Red lines
- No root services "for convenience"; no host-wide mounts; never disable the sandbox to make something run — fix the permission design.

## Related
`observability-ops` · `secure-build-pattern` · `zero-trust-architecture`.
