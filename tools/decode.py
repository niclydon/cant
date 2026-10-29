#!/usr/bin/env python3
"""Cant reference decoder/validator (static script, not a service).

Reads a Cant frame from a file argument or stdin, validates it against
the v0.2 grammar and dictionary, and prints a plain-English expansion.
This is the audit path for invariant 1: anything said in Cant can be
decoded by anyone holding this repo.

Usage: python3 tools/decode.py frame.txt   (or pipe the frame on stdin,
       or pass - as the file argument to read stdin)
Exit codes: 0 valid, 1 malformed, 2 usage.
"""
import re
import sys
from datetime import datetime

TYPES = {"REQ", "RES", "ERR", "ACK", "NTE", "PNG"}
OPS = {"CRT", "REN", "ARC", "UAR", "DEL", "RED", "REG", "RLY", "SYN", "QRY",
       "CXL"}
ERRS = {"parse", "notfound", "refused", "denied", "busy", "internal",
        "unk", "tmo"}
KEYS = {"op", "chat", "name", "arg", "out", "st", "err", "why", "ms", "cnt",
        "ref", "ver", "dct", "idem", "sha", "src", "by", "rtry", "aft",
        "thr", "seq"}
# Protocol errors mean the frame was never executed (SPEC section 3,
# error taxonomy); every other code is an execution error.
PROTOCOL_ERRS = {"parse", "unk", "tmo"}
# `st` carries `ok`, or an error code on ERR frames (ROSETTA, "Keys you
# will actually use"); the error codes are the SPEC section 3 set.
STS = {"ok"} | ERRS
# Keys that may repeat in one frame (SPEC/ROSETTA: `ref` is repeatable).
# Every other key must occur at most once; a second `op` line in
# particular would smuggle a second operation into one frame.
REPEATABLE = {"ref"}
SUPPORTED_MAJOR = "1"

OPEN = re.compile(r"^§CANT/(\d+) (REQ|RES|ERR|ACK|NTE|PNG) ([0-9a-f]{8})$")
CLOSE = re.compile(r"^§/CANT ([0-9a-f]{8})$")
LINE = re.compile(r"^([a-z]{2,5})=(.*)$")

# Value shapes for the v0.2 keys (SPEC section 3). `ver` is a full
# semver; `dct` is the dictionary version, optionally suffixed with a
# short hex fingerprint of the dictionary as loaded (-<4-16 hex>) so
# two speakers on the same version can still detect divergence.
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
DCT = re.compile(r"^\d+\.\d+\.\d+(-[0-9a-f]{4,16})?$")
CORR8 = re.compile(r"^[0-9a-f]{8}$")
THREAD = re.compile(r"^[0-9a-f]{12,16}$")
SHA = re.compile(r"^[0-9a-f]{8,64}$")
NONNEG_INT = re.compile(r"^\d+$")
RTRY = re.compile(r"^[01]$")


def _is_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


VALUE_CHECKS = {
    "ver": (lambda v: bool(VERSION.match(v)), "not an x.y.z version"),
    "dct": (lambda v: bool(DCT.match(v)),
            "not a dictionary version (x.y.z, optional -<hex> fingerprint)"),
    "idem": (lambda v: bool(CORR8.match(v)), "not a corr (8 lowercase hex)"),
    "thr": (lambda v: bool(THREAD.match(v)), "not a thread id (12-16 hex)"),
    "sha": (lambda v: bool(SHA.match(v)), "not a hex digest (8-64 hex)"),
    "seq": (lambda v: bool(NONNEG_INT.match(v)), "not a non-negative integer"),
    "aft": (lambda v: bool(NONNEG_INT.match(v)), "not a non-negative integer"),
    "rtry": (lambda v: bool(RTRY.match(v)), "not 0 or 1"),
    "by": (_is_timestamp, "not an ISO-8601 timestamp"),
}


def _malformed(message: str) -> int:
    print(f"MALFORMED: {message}")
    return 1


def decode(text: str) -> int:
    """Validate a frame in full, then print its expansion.

    Validation completes before anything is printed, so a malformed
    frame never produces a partial expansion ahead of its error.
    """
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return _malformed("frame needs at least an open and a close line")
    m = OPEN.match(lines[0].strip())
    if not m:
        return _malformed(f"bad open token: {lines[0]!r}")
    version, ftype, corr = m.groups()
    if version != SUPPORTED_MAJOR:
        return _malformed(
            f"unsupported major version {version!r}: "
            f"this decoder speaks Cant {SUPPORTED_MAJOR}")
    c = CLOSE.match(lines[-1].strip())
    if not c:
        return _malformed(f"bad close token: {lines[-1]!r}")
    if c.group(1) != corr:
        return _malformed(f"close corr {c.group(1)} != open corr {corr}")

    # Parse and validate the whole body first.
    body = []  # ordered (key, value) pairs, duplicates preserved
    seen = set()
    for ln in lines[1:-1]:
        lm = LINE.match(ln.strip())
        if not lm:
            return _malformed(f"body line is not key=value: {ln!r}")
        key, value = lm.groups()
        if key not in KEYS:
            return _malformed(f"unregistered key {key!r}")
        if key in seen and key not in REPEATABLE:
            return _malformed(f"duplicate key {key!r}")
        seen.add(key)
        if key == "op" and value not in OPS:
            return _malformed(f"unregistered op {value!r}")
        if key == "err" and value not in ERRS:
            return _malformed(f"unregistered error code {value!r}")
        if key == "st" and value not in STS:
            return _malformed(f"unregistered status {value!r}")
        if key in VALUE_CHECKS:
            check, complaint = VALUE_CHECKS[key]
            if not check(value):
                return _malformed(f"bad {key} value {value!r}: {complaint}")
        body.append((key, value))

    # Per-type mandatory fields, as defined in SPEC section 2.
    present = {key for key, _ in body}
    if ftype == "REQ" and "op" not in present:
        return _malformed("REQ frame carries no op")
    if ftype == "ERR" and "err" not in present:
        return _malformed("ERR frame carries no err (SPEC section 2: err is mandatory)")

    # Fully valid: print the expansion.
    print(f"Cant v{version} {ftype} frame, correlation {corr}")
    for key, value in body:
        note = ""
        if key == "op":
            note = " (registered op)"
        elif key == "ver":
            note = " (speaker's Cant version)"
        elif key == "dct":
            note = " (speaker's dictionary version)"
        elif key == "err":
            kind = "protocol error: frame not executed" \
                if value in PROTOCOL_ERRS else "execution error"
            note = f" ({kind})"
        print(f"  {key} = {value}{note}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    if len(sys.argv) == 2 and sys.argv[1] != "-":
        path = sys.argv[1]
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"ERROR: cannot read frame file {path!r}: {exc.strerror or exc}",
                  file=sys.stderr)
            sys.exit(2)
    else:
        text = sys.stdin.read()
    sys.exit(decode(text))
