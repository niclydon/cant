# Template: registering a new Cant channel

Registration is a pull request against this repo (SPEC §5). Copy the row, fill every field, and add the standing-brief block below it to the same PR. A channel that is not in SPEC §4 is not a Cant channel.

## The SPEC §4 row

| Channel | Purpose | Speakers | Ops |
|---|---|---|---|
| `<channel name> (<chat or channel id>)` | `<what traffic this channel carries, in one line>` | `<who posts REQ> (REQ), <who answers> (RES/ERR)` | `<op codes this channel uses, space-separated>` |

## Standing-brief fields the PR fills in

- **Channel**: name and id, and where it lives (which surface hosts the chat).
- **Purpose**: the traffic, and the class of work it belongs to. One line.
- **Speakers**: every agent or service that may post frames, and the direction each speaks (REQ, RES/ERR, NTE only, PNG).
- **Ops used**: the op codes from the dictionary. A channel registers only the ops it actually speaks; an op a channel needs that is not in the dictionary is a separate dictionary proposal in the same PR, with its own worked example.
- **Pointer roots**: the registered roots every `@file:` pointer in this channel must resolve under, one root per direction if requests and results live in different places (e.g. Bridge requests under one directory, results under another). Pointers outside the registered roots are refused.
- **Operator-read?**: must be no. Any channel the operator reads is permanently excluded, by invariant 2.
- **Idempotency window**: 24h unless the channel states otherwise in its row (SPEC §3); state it if different.
- **Escalation**: how a stuck or refused op in this channel reaches a human (an English post in a named operator channel — never a Cant frame).

## First traffic

The registration PR is not complete until the channel has carried one real exchange and the PR links it. A liveness check with versions attached is the smallest honest first traffic:

```
§CANT/1 PNG c5d6e7f8
ver=0.2.0
§/CANT c5d6e7f8
```
