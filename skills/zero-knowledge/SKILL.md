---
name: zero-knowledge
description: Zero-knowledge principles for software — the server learns nothing. Client-side encryption, proof without revelation, when ZK matters vs when it's theater. Distilled from zerok-container.
version: 1
triggers: zero knowledge, zero-knowledge, ZK, client-side encryption, server learns nothing, private cloud, end-to-end encrypted, privacy architecture
category: Security & privacy
blurb: Zero-knowledge principles — designing so the server learns nothing and you never have to trust software with your data.
example: Explain zero-knowledge like I am smart but new: where does it actually matter?
---
# Zero-Knowledge Principles

You reason about privacy the way `zerok-container` is built, around one
idea: **you should not have to trust software with your data.** If
encryption does not happen on your device, it is not zero-knowledge —
whatever the marketing page says.

This is for informational and educational purposes — not legal advice,
not a privacy certification.

## The core test (one sentence)

**Can the server operator — malicious, curious, or compelled — read
user data?** If yes, the system is not zero-knowledge. Everything else
is implementation detail.

## What zero-knowledge requires

1. **Client-side encryption, always.** Plaintext exists only on the
   user's device. The server receives and stores opaque bytes. (Zerok:
   select file → encrypted locally → blob uploaded → server stores
   unreadable bytes → only the user decrypts.)
2. **Keys never leave the device.** Not in transit, not "temporarily,"
   not for "convenience features." Key derivation happens locally
   (password → KDF → key, all client-side).
3. **Authenticated encryption.** Ciphertext must be tamper-evident —
   encryption without authentication lets an attacker modify data
   silently. (Zerok threat model: blob tampering → mitigated by
   authenticated encryption.)
4. **No trusted third parties in the data path.** No key escrow, no
   recovery backdoor, no admin plaintext view. Each exception is a
   named party you now trust — list them.
5. **Encryption independent of transport.** TLS protects the pipe; ZK
   protects the data. A system that relies on TLS alone trusts the
   server at the end of the pipe.

## When ZK matters vs when it's theater

**ZK matters when:** the server is operated by someone other than the
user (SaaS, cloud storage, hosted services); the data is sensitive
enough that server-side access is itself the threat (health, finance,
legal, personal archives); regulatory or contractual pressure demands
the operator *cannot* read data, not merely *promises not to*.

**ZK is theater when:** the client is a web app served by the same
server (the server ships the JavaScript — it can ship key-stealing
JavaScript tomorrow); the "encrypted" search/indexing requires the
server to see plaintext or searchable tokens; key "backup" uploads the
key to the server under another name; the threat model quietly excludes
the actual adversary (a malicious operator).

**The web-app paradox** deserves emphasis: browser-delivered crypto
moves trust from the server's database to the server's code pipeline.
It is still better than server-side plaintext — but it is not the same
guarantee as a locally installed client. Say which one you're looking
at.

## How to evaluate a ZK claim

- **Follow the key.** Where is it generated? Where is it stored? What
  crosses the network? Draw the key's journey — gaps in your diagram
  are the audit findings.
- **Follow the plaintext.** List every place plaintext exists, however
  briefly (memory, logs, crash dumps, thumbnails, previews). Each is
  a scope boundary.
- **Read the recovery story.** "Forgot password" + "we can't recover
  your data" cannot both be true. The recovery mechanism defines the
  real trust model.
- **Check the metadata.** Zerok's threat model names it honestly:
  traffic analysis and blob-size leakage survive encryption. Sizes,
  timing, and access patterns are data too.

## Rules

- "Zero-knowledge" is a property of the *architecture*, not a feature
  flag. Evaluate the data flow, not the label.
- Distinguish **can't read** (cryptographic guarantee) from **won't
  read** (policy promise). Only the first is ZK.
- Name every trusted component explicitly — including the client
  itself, the OS, and the distribution channel.
- Residual risks are part of the answer, not a footnote.

## Honest limits

- ZK does not protect against a compromised client device, malware,
  or physical access to an unlocked device (zerok states this).
- ZK does not hide *that* you store data, how much, or when you
  access it — only *what* it contains.
- This skill evaluates design claims. It does not replace a
  cryptographic review or a formal security audit.
