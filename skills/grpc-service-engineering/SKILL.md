---
name: grpc-service-engineering
description: Build gRPC services well — protobuf contracts, streaming, deadlines, health, mTLS, breaking-change checks.
version: 1
triggers: grpc, protobuf, rpc service, streaming rpc, mtls
category: Engineering & code
blurb: Build gRPC services well — protobuf contracts, streaming, deadlines, health checks and mTLS.
archetype: knowledge
example: Design a gRPC service contract that won't break clients.
---

# gRPC Service Engineering

Protobuf contracts are forever: field numbers never get reused, breaking changes get caught in CI, and every call carries a deadline.

## When to use
- Service-to-service RPC (Rust/Go-class daemons, agent infra, internal APIs).
- Streaming pipelines (logs, telemetry, long operations).
- Anywhere agents and services need a typed, fast contract.

## Method
1. **Contract first, proto3**: field numbering discipline (**never reuse numbers** — `reserved` them); backward/forward compatibility rules; `buf` lint + breaking-change checks in CI; codegen pinned and generated in CI, not by hand.
2. **API shape**: unary vs server/client/bidi streaming chosen by flow; **deadlines on every call** + cancellation propagation; rich error model (status codes + typed details), metadata kept for transport concerns.
3. **Server hygiene**: `grpc.health.v1` health, reflection only in dev (or authenticated), interceptors for auth/logging/metrics/tracing, keepalive + pool tuning, explicit max message sizes.
4. **Security**: mTLS between services with per-service identities; authorization interceptor or external policy (`policy-as-code`); no plaintext gRPC across hosts; rate limits on public-ish surfaces.
5. **Observability**: trace + request-id propagation, per-method metrics, structured errors logged once.
6. **Testing**: in-process integration tests (bufconn-style), contract tests against real clients, load smoke on hot paths.
7. **Interop & versioning**: gateway/JSON adapters for REST consumers, gRPC-Web where browsers must connect; `v1` package versions; deprecated fields announced then removed on schedule.

## Quality gates
- [ ] Breaking-change check green in CI; reserved fields for removals.
- [ ] Deadlines/cancellation on all calls; health service exposed.
- [ ] mTLS + authz on cross-host paths.
- [ ] Contract tests pass against clients.

## Red lines
- Never reuse proto field numbers; no unbounded streams; no plaintext off-box; no hand-generated stubs.

## Related
`policy-as-code` · `agent-interoperability` · `backend-engineering`.
