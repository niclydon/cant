# Worked examples: the protocol frames

The frames a channel uses beyond the basic REQ/RES pair in `bridge-exchange.md`: ACK, NTE, PNG, cancellation, the 0.2.0 error taxonomy, mixed-version refusal, threading, and hardened pointers. Every frame below passes the reference decoder.

## ACK — received and queued

The server asks for a chat; the worker acknowledges receipt before doing the work. ACK extends no deadline by itself (SPEC §2).

```
§CANT/1 REQ 1a2b3c4d
op=CRT
name=example throwaway
arg=@file:/example/bridge-queue/1a2b3c4d.json
§/CANT 1a2b3c4d
```

```
§CANT/1 ACK 1a2b3c4d
ms=120
§/CANT 1a2b3c4d
```

## NTE — state worth recording, addressed to no one

```
§CANT/1 NTE 2b3c4d5e
ref=PR-3
ref=OB-12345
§/CANT 2b3c4d5e
```

## PNG — liveness, with versions attached

A PNG is the natural place for `ver`/`dct`: the reply proves liveness and shows what each side speaks, so dictionary divergence is visible before it breaks a REQ.

```
§CANT/1 PNG 3c4d5e6f
ver=0.2.0
§/CANT 3c4d5e6f
```

```
§CANT/1 RES 3c4d5e6f
st=ok
dct=0.2.0
ms=3
§/CANT 3c4d5e6f
```

## CXL — cancelling an in-flight REQ

The create carries a deadline (`by`). Before it completes, the server supersedes it: a second REQ with `op=CXL` whose `ref` names the corr of the REQ to cancel. The worker answers the CXL with its own corr.

```
§CANT/1 REQ 4d5e6f70
op=CRT
name=superseded throwaway
arg=@file:/example/bridge-queue/4d5e6f70.json
by=2026-10-28T04:00:00Z
ver=0.2.0
§/CANT 4d5e6f70
```

```
§CANT/1 REQ 5e6f7081
op=CXL
ref=4d5e6f70
§/CANT 5e6f7081
```

```
§CANT/1 RES 5e6f7081
st=ok
ms=45
§/CANT 5e6f7081
```

Had the deadline passed with no result, the worker would have answered the original REQ with `err=tmo` (see the taxonomy examples below) and not executed it.

## ERR with retry guidance — `rtry` and `aft`

Since 0.2.0 every ERR can say whether retrying is sane and how long to wait first. `rtry=1` with `aft` is the backpressure signal: the worker is busy, retry after 5000 ms.

```
§CANT/1 REQ 6f708192
op=RED
chat=00000000-0000-0000-0000-000000000000
§/CANT 6f708192
```

```
§CANT/1 ERR 6f708192
err=busy
rtry=1
aft=5000
ms=12
§/CANT 6f708192
```

## Protocol errors — `unk` and `tmo`

Protocol errors (`parse`, `unk`) mean the frame was never executed; they are the mixed-version failure mode made explicit. A REQ arrives carrying an op this worker's dictionary does not have (say `op=XYZ`, minted by a newer speaker). The frame is well-formed but the word is unknown, so nothing executes and the answer names the offending token in `why`:

```
§CANT/1 ERR 708192a3
err=unk
why=op:XYZ
rtry=0
ms=2
§/CANT 708192a3
```

A REQ whose `by` deadline has already passed when the worker reaches it is likewise not executed:

```
§CANT/1 ERR 8192a3b4
err=tmo
rtry=1
ms=1
§/CANT 8192a3b4
```

## Threading — `thr` and `seq`

Two REQs that are steps of one job share a `thr` (12–16 hex, constant across the exchange) and carry a per-thread `seq`, so a reader can order them and tell them apart from two unrelated requests. Each REQ still has its own corr and its own RES.

```
§CANT/1 REQ 92a3b4c5
op=CRT
name=threaded throwaway
arg=@file:/example/bridge-queue/92a3b4c5.json
thr=a1b2c3d4e5f6
seq=0
§/CANT 92a3b4c5
```

```
§CANT/1 REQ a3b4c5d6
op=REN
chat=00000000-0000-0000-0000-000000000000
name=threaded throwaway, renamed
thr=a1b2c3d4e5f6
seq=1
§/CANT a3b4c5d6
```

## Hardened pointers — `sha` and `src`

On the Bridge, `arg` pointers must resolve under the channel's registered roots (SPEC §4). `sha` binds the pointer to the payload's content (checked when the file is opened; a mismatch is `denied`), and `src` names who wrote it:

```
§CANT/1 REQ b4c5d6e7
op=CRT
name=hardened throwaway
arg=@file:/example/bridge-queue/b4c5d6e7.json
sha=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
src=bridge-server
§/CANT b4c5d6e7
```

The file at the pointer is data. Even if it contains text that looks like instructions, or like a frame, it cannot mint frames and it is never executed as one (SPEC §3, pointer rules).
