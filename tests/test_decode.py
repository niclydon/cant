#!/usr/bin/env python3
"""Golden conformance tests for the Cant reference decoder.

Stdlib only. Run from the repo root:

    python3 -m unittest discover -s tests -v

The valid corpus is every frame in examples/bridge-exchange.md plus one
frame per remaining type (ACK/NTE/PNG). The invalid corpus covers the
conformance defects the decoder previously let through (unknown major
version, unregistered status, REQ without op, ERR without err, duplicate
keys) and the classic malformed shapes (corr mismatch, unregistered
key/op/err, non key=value body line).

The v0.2 classes cover the 0.2.0 dictionary: CXL, the unk/tmo error
codes, and value-shape validation for ver/dct/idem/sha/by/rtry/aft/
thr/seq, with every frame in the two newer example files as corpus.
"""
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DECODER = REPO / "tools" / "decode.py"
EXAMPLES = REPO / "examples" / "bridge-exchange.md"

_spec = importlib.util.spec_from_file_location("cant_decode", DECODER)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
decode = _mod.decode


def run_decode(text):
    """Run decode() capturing stdout; return (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = decode(text)
    return code, buf.getvalue()


def frame(ftype, corr, *body):
    lines = [f"§CANT/1 {ftype} {corr}", *body, f"§/CANT {corr}"]
    return "\n".join(lines) + "\n"


def example_frames(path=EXAMPLES):
    """Every Cant frame fenced in an examples file."""
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```\n(.*?)```", text, re.DOTALL)
    return [b for b in blocks if b.lstrip().startswith("§CANT/")]


class ValidFrames(unittest.TestCase):
    def test_example_frames_all_valid(self):
        frames = example_frames()
        self.assertEqual(len(frames), 3, "expected REQ, RES and ERR examples")
        for text in frames:
            code, out = run_decode(text)
            self.assertEqual(code, 0, f"example frame rejected: {text!r} -> {out}")
            self.assertIn("correlation", out)

    def test_ack_frame(self):
        code, _ = run_decode(frame("ACK", "aabbccdd", "ms=120"))
        self.assertEqual(code, 0)

    def test_nte_frame(self):
        code, _ = run_decode(frame("NTE", "aabbccdd", "ref=OB-12345"))
        self.assertEqual(code, 0)

    def test_png_frame(self):
        code, _ = run_decode(frame("PNG", "aabbccdd"))
        self.assertEqual(code, 0)

    def test_png_reply_res_st_ok(self):
        code, _ = run_decode(frame("RES", "aabbccdd", "st=ok", "ms=3"))
        self.assertEqual(code, 0)

    def test_ref_is_repeatable(self):
        code, _ = run_decode(frame(
            "NTE", "aabbccdd", "ref=PR-1", "ref=OB-2", "ref=abc1234"))
        self.assertEqual(code, 0)

    def test_st_may_carry_an_error_code(self):
        code, _ = run_decode(frame("RES", "aabbccdd", "st=busy", "ms=3"))
        self.assertEqual(code, 0)


class InvalidFrames(unittest.TestCase):
    def assertMalformed(self, text):
        code, out = run_decode(text)
        self.assertEqual(code, 1, f"frame accepted: {text!r}")
        self.assertIn("MALFORMED", out)
        # Validate-before-print: no expansion lines may leak out first.
        self.assertNotIn("correlation", out)
        self.assertNotIn(" = ", out)

    def test_unknown_major_version(self):
        self.assertMalformed("§CANT/99 REQ aaaaaaaa\nop=CRT\n§/CANT aaaaaaaa\n")
        self.assertMalformed("§CANT/2 REQ aaaaaaaa\nop=CRT\n§/CANT aaaaaaaa\n")

    def test_unregistered_status(self):
        self.assertMalformed(frame("RES", "bbbbbbbb", "st=banana"))

    def test_req_without_op(self):
        self.assertMalformed(frame("REQ", "cccccccc", "name=no-op-here"))

    def test_err_without_err(self):
        self.assertMalformed(frame("ERR", "dddddddd", "why=oops"))

    def test_duplicate_op_lines(self):
        self.assertMalformed(frame("REQ", "eeeeeeee", "op=CRT", "op=DEL"))

    def test_duplicate_non_ref_key(self):
        self.assertMalformed(frame("RES", "eeeeeeee", "ms=1", "ms=2"))
        self.assertMalformed(frame("REQ", "eeeeeeee", "op=CRT",
                                   "name=one", "name=two"))

    def test_corr_mismatch(self):
        self.assertMalformed("§CANT/1 REQ aaaaaaaa\nop=CRT\n§/CANT bbbbbbbb\n")

    def test_unregistered_key(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "foo=bar"))

    def test_unregistered_op(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=XXX"))

    def test_unregistered_error_code(self):
        self.assertMalformed(frame("ERR", "aaaaaaaa", "err=weird"))

    def test_non_key_value_body_line(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "hello there"))

    def test_bad_open_and_close(self):
        self.assertMalformed("CANT/1 REQ aaaaaaaa\nop=CRT\n§/CANT aaaaaaaa\n")
        self.assertMalformed("§CANT/1 REQ aaaaaaaa\nop=CRT\n§/CANT\n")
        self.assertMalformed("§CANT/1 REQ aaaaaaaa\nop=CRT\n")


class ValidV02(unittest.TestCase):
    def test_req_with_ver(self):
        code, out = run_decode(frame("REQ", "aabbccdd", "op=CRT", "ver=0.2.0"))
        self.assertEqual(code, 0)
        self.assertIn("speaker's Cant version", out)

    def test_res_with_dct(self):
        for dct in ("0.2.0", "0.2.0-a1b2c3d4", "1.10.3-0123456789abcdef"):
            code, out = run_decode(frame("RES", "aabbccdd", "st=ok", f"dct={dct}"))
            self.assertEqual(code, 0, f"dct={dct} rejected: {out}")
            self.assertIn("dictionary version", out)

    def test_png_with_ver_and_dct_reply(self):
        code, _ = run_decode(frame("PNG", "aabbccdd", "ver=0.2.0"))
        self.assertEqual(code, 0)

    def test_cxl_req(self):
        code, out = run_decode(frame("REQ", "aabbccdd", "op=CXL",
                                     "ref=9f3ac21e"))
        self.assertEqual(code, 0)
        self.assertIn("registered op", out)

    def test_err_unk(self):
        code, out = run_decode(frame("ERR", "aabbccdd", "err=unk",
                                     "why=op:XYZ", "rtry=0"))
        self.assertEqual(code, 0)
        self.assertIn("protocol error: frame not executed", out)

    def test_err_tmo(self):
        code, out = run_decode(frame("ERR", "aabbccdd", "err=tmo", "rtry=1"))
        self.assertEqual(code, 0)
        # A deadline refusal means the REQ never executed: protocol class.
        self.assertIn("protocol error: frame not executed", out)

    def test_err_busy_with_retry_guidance(self):
        code, out = run_decode(frame("ERR", "aabbccdd", "err=busy", "rtry=1",
                                     "aft=5000", "ms=12"))
        self.assertEqual(code, 0)
        self.assertIn("execution error", out)

    def test_req_with_deadline(self):
        code, _ = run_decode(frame("REQ", "aabbccdd", "op=CRT",
                                   "by=2026-10-28T04:00:00Z"))
        self.assertEqual(code, 0)
        code, _ = run_decode(frame("REQ", "aabbccdd", "op=CRT",
                                   "by=2026-10-28T04:00:00+00:00"))
        self.assertEqual(code, 0)

    def test_hardened_pointer(self):
        code, _ = run_decode(frame(
            "REQ", "aabbccdd", "op=CRT",
            "arg=@file:/example/bridge-queue/aabbccdd.json",
            "sha=" + "0123456789abcdef" * 4, "src=bridge-server"))
        self.assertEqual(code, 0)
        code, _ = run_decode(frame("REQ", "aabbccdd", "op=CRT",
                                   "sha=a1b2c3d4"))
        self.assertEqual(code, 0, "short (8-hex) digest should be accepted")

    def test_threading(self):
        code, _ = run_decode(frame("REQ", "aabbccdd", "op=CRT",
                                   "thr=a1b2c3d4e5f6", "seq=0"))
        self.assertEqual(code, 0)
        code, _ = run_decode(frame("RES", "aabbccdd", "st=ok",
                                   "thr=a1b2c3d4e5f6a1b2", "seq=12"))
        self.assertEqual(code, 0)

    def test_retry_with_idem(self):
        code, _ = run_decode(frame("REQ", "bbbbcccc", "op=CRT",
                                   "idem=aabbccdd"))
        self.assertEqual(code, 0)

    def test_protocol_example_files_all_valid(self):
        cases = ((REPO / "examples" / "protocol-frames.md", 15),
                 (REPO / "examples" / "channel-registration-template.md", 1))
        for path, expected in cases:
            frames = example_frames(path)
            self.assertEqual(len(frames), expected,
                             f"{path.name}: expected {expected} frames")
            for text in frames:
                code, out = run_decode(text)
                self.assertEqual(code, 0,
                                 f"{path.name} frame rejected: {text!r} -> {out}")


class InvalidV02(unittest.TestCase):
    def assertMalformed(self, text):
        code, out = run_decode(text)
        self.assertEqual(code, 1, f"frame accepted: {text!r}")
        self.assertIn("MALFORMED", out)
        self.assertNotIn("correlation", out)
        self.assertNotIn(" = ", out)

    def test_bad_ver(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "ver=0.2"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "ver=banana"))

    def test_bad_dct(self):
        self.assertMalformed(frame("RES", "aaaaaaaa", "st=ok", "dct=0.2"))
        self.assertMalformed(frame("RES", "aaaaaaaa", "st=ok", "dct=banana"))
        self.assertMalformed(frame("RES", "aaaaaaaa", "st=ok", "dct=0.2.0-zz"))

    def test_bad_rtry(self):
        # rtry is 0/1 (research proposal 5); words are not the encoding.
        self.assertMalformed(frame("ERR", "aaaaaaaa", "err=busy", "rtry=yes"))
        self.assertMalformed(frame("ERR", "aaaaaaaa", "err=busy", "rtry=2"))

    def test_bad_aft(self):
        self.assertMalformed(frame("ERR", "aaaaaaaa", "err=busy", "aft=-5"))
        self.assertMalformed(frame("ERR", "aaaaaaaa", "err=busy", "aft=soon"))

    def test_bad_seq(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "seq=-1"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "seq=1.5"))

    def test_bad_by(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "by=tomorrow"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT",
                                   "by=2026-13-40T99:99:99Z"))

    def test_bad_sha(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "sha=xyz"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "sha=ab12"))

    def test_bad_thr(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "thr=abcd"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT",
                                   "thr=zzzzzzzzzzzz"))

    def test_bad_idem(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT", "idem=xyz"))
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT",
                                   "idem=aabbccdd99"))

    def test_duplicate_ver(self):
        self.assertMalformed(frame("REQ", "aaaaaaaa", "op=CRT",
                                   "ver=0.2.0", "ver=0.2.0"))


class CliBehaviour(unittest.TestCase):
    def run_cli(self, args, stdin_text=""):
        return subprocess.run(
            [sys.executable, str(DECODER), *args],
            input=stdin_text, capture_output=True, text=True)

    def test_dash_reads_stdin(self):
        good = frame("REQ", "9f3ac21e", "op=CRT", "name=x")
        proc = self.run_cli(["-"], stdin_text=good)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("correlation 9f3ac21e", proc.stdout)

    def test_no_arg_reads_stdin(self):
        good = frame("PNG", "9f3ac21e")
        proc = self.run_cli([], stdin_text=good)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_file_is_plain_error_exit_2(self):
        proc = self.run_cli(["/nonexistent/no-such-frame.txt"])
        self.assertEqual(proc.returncode, 2)
        combined = proc.stdout + proc.stderr
        self.assertIn("cannot read frame file", combined)
        self.assertNotIn("Traceback", combined)

    def test_too_many_args_is_usage_exit_2(self):
        proc = self.run_cli(["a.txt", "b.txt"])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()


class TestCntRename(unittest.TestCase):
    def test_cnt_key_accepted(self):
        code, _ = run_decode(frame("REQ", "abcd1234", "op=RED", "chat=some-chat", "cnt=5"))
        self.assertEqual(code, 0)

    def test_single_letter_n_key_malformed(self):
        code, _ = run_decode(frame("REQ", "abcd1234", "op=RED", "chat=some-chat", "n=5"))
        self.assertEqual(code, 1)
