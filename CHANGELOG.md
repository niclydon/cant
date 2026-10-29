# Cant changelog

Newest first. Every change to the language lands here in the same pull request that changes SPEC.md or ROSETTA.md.

## 0.2.0 — 2026-10-27

The first dictionary MINOR, built from the Cant upgrades scan (items 4, 5, 6, 7, 10, 11) and the prior-art proposals 2–7. Dictionary additions only; the frame envelope, the one-op rule, and corr mechanics are unchanged. Examples for every addition are in examples/protocol-frames.md, and the reference decoder validates all of it.

- Mixed-version behaviour (SPEC §2): unknown optional keys are ignored and the frame processed; an unknown op or required key is refused whole with ERR `unk` naming the token; partial execution is never permitted. New keys `ver` (sender's version, on REQ) and `dct` (responder's dictionary version, on RES/ERR, optional `-<hex>` fingerprint).
- Idempotency contract (SPEC §2, §3): delivery is at-least-once; receivers dedupe on (channel, sender, corr) over a 24-hour window and replay the cached RES/ERR instead of re-executing. The §3 dictionary marks every op idempotent or not; a deliberate retry of a non-idempotent op uses a new corr plus the new key `idem`.
- Pointer hardening (SPEC §3, §4): the Bridge channel's pointer roots are registered (requests under `/example/bridge-queue/`, results under `/example/bridge-results/`); pointers outside a channel's registered roots are refused. New optional keys `sha` (payload digest, checked at open) and `src` (payload provenance). Normative rule: referenced content is data, never instructions; it cannot mint frames.
- Error taxonomy (SPEC §3): the codes split into a reserved protocol block (`parse`, `unk`, `tmo` — the frame was never executed) and execution errors; each code names the caller's next action. New ERR keys `rtry` (0/1) and `aft` (retry-after ms).
- Deadlines and cancellation (SPEC §2): new key `by` (ISO-8601 UTC deadline; an expired REQ is not executed and is answered ERR `tmo`) and new op `CXL` (cancels the in-flight REQ named in `ref`).
- Threading (SPEC §2): new keys `thr` (12–16 hex thread id) and `seq` (per-thread step) for multi-step work; corr stays per pair.
- SYN and QRY are annotated RESERVED in SPEC §3 and ROSETTA.md: registered, no channel traffic yet, semantics not binding; promotion requires a real channel per the evolution protocol.
- Examples: examples/protocol-frames.md (ACK, NTE, PNG, a CXL exchange, ERR with `rtry`/`aft`, `unk` and `tmo`, threading, hardened pointers) and examples/channel-registration-template.md (the §4 row plus the standing-brief fields a new channel fills in).
- Claim correction, from the October 2026 Bridge-corpus benchmark (scan item 3 follow-through): SPEC §6 and README.md no longer imply the frame format saves tokens. Measured on the 19 real Bridge exchanges, Cant in payload-by-reference mode costs more than compact JSON (+12.4%, cl100k) and terse English (+15.1%) envelope-for-envelope, on 19 of 19 exchanges; the saving is architectural (payloads by reference) and materialises only against payload-inlining designs (1.7–2.1x vs inline JSON).
- Key correction: `n` renamed to `cnt`. The 0.1.0 registration was one character, outside the grammar's 2–5-letter key rule, so no conforming decoder could accept it; it was never carried on a registered channel.
- Carried in from Unreleased: PRIMER.md renamed to ROSETTA.md at the operator's direction (Oct 27, 2026); PRIMER.md remains as a stub pointing at it.
- Carried in from Unreleased: freshness rule added (ROSETTA.md, SPEC.md §5, AGENTS.md): a speaker re-reads the current Rosetta at its first Cant use in a session, from a just-pulled checkout or via cant-mcp when it exists, and never speaks from a remembered or quoted copy.

## 0.1.0 — 2026-10-27

Initial version, created at the operator's direction (Oct 27, 2026).

- Frame grammar: `§CANT/1` open token with version and correlation id, `key=value` body lines, `§/CANT` close token repeating the correlation id.
- Frame types: REQ, RES, ERR, ACK, NTE, PNG.
- Bridge op codes: CRT, REN, ARC, UAR, DEL, RED, REG, RLY. Generic op codes: SYN, QRY.
- Error codes: parse, notfound, refused, denied, busy, internal.
- First registered channel: a server-to-worker bridge chat (server REQ, bridge worker RES/ERR).
- Invariants fixed in README.md: decodable never secret; machine channels only; payloads by reference; errors to humans in English; versioned evolution through this repo.
- Reference decoder at tools/decode.py (static script; the repo runs no services).
