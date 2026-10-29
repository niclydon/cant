# Cant

> Public export of the Cant language specification, generated from a private working repository. The grammar, dictionary, examples, and decoder here are complete and usable as published; deployment-specific details (real channel registrations, hosts, and filesystem paths) are replaced with worked examples.

Cant is a wire dialect for a personal multi-agent system: a terse, framed, mechanically decodable message format for agent-to-agent traffic in channels no human needs to read.

It exists because agent channels fill up with English prose written for nobody. Two agents exchanging a request and a result do not need sentences; they need a frame, an op code, and a pointer to the payload. Cant is that frame — not because the frame is cheaper than a sentence (measured on the real Bridge corpus in October 2026, it is not: +12.4% per exchange against compact JSON and +15.1% against terse English, on 19 of 19 exchanges), but because the frame is rigid, mechanically checkable, and keeps payloads out of the message entirely, which is where the real cost lives: against designs that inline their payloads, by-reference traffic is 1.7–2.1x cheaper on the same corpus. It was designed for a server-to-worker bridge channel first (a server waking a worker chat and getting a one-line result back) and is open to any agent that works a machine channel.

## Invariants (these do not evolve)

1. **Decodable, never secret.** Every Cant message can be expanded to plain English using only this repo (ROSETTA.md, SPEC.md, tools/decode.py). Cant is compression, not concealment. Anything an agent would not say in English in front of the operator, it does not say in Cant either.
2. **Machine channels only.** Cant is spoken only in channels registered in SPEC.md as machine channels. Any channel the operator reads (main chat, Verify, Ledger, purpose chats) stays English, always.
3. **Payloads by reference.** Bulk data travels through governed files and stores, never inline in a frame. A frame carries pointers.
4. **Errors to humans are English.** A frame that fails to parse gets an English reply naming the frame. Machines may be terse with each other; they are never terse at the operator.
5. **Versioned in the open (to the estate).** Every frame carries its version. Changes land here as pull requests with a CHANGELOG.md entry, under the evolution protocol in SPEC.md. The Rosetta in this repo is the only source of truth; no agent speaks a private extension.

## Layout

- `AGENTS.md` — the entry file for any agent arriving in this repo: orientation, rules, read order. `CLAUDE.md` points at it for Claude-family tools.
- `ROSETTA.md` — the one file an agent reads to start speaking. Start there.
- `SPEC.md` — the formal grammar, the dictionary, the channel registry, the evolution protocol.
- `CHANGELOG.md` — every change to the language, newest first.
- `examples/` — worked exchanges, annotated frame by frame.
- `tools/decode.py` — a static reference decoder/validator (a script, not a service; this repo runs no compute).

## Status

Version 0.2.0. First registered channel: a server-to-worker bridge chat. Spoken by: the bridge server (wake frames) and the bridge worker (result frames). Adoption by other agents is by reading ROSETTA.md and registering the channel in SPEC.md via pull request.
