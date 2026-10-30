#!/usr/bin/env python3
"""Exercise DevStandard Antigravity session hooks and hooks.json declarations."""
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = ROOT / 'hooks.json'
SESSION_START = ROOT / 'hooks/session-start'
ORCHESTRATOR = ROOT / 'reference/orchestrator.md'
WORKER = ROOT / 'reference/worker.md'


def load_session_start_module():
    loader = SourceFileLoader('session_start_hook', str(SESSION_START))
    spec = spec_from_loader('session_start_hook', loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class HooksJsonDeclarationTest(unittest.TestCase):
    def test_hooks_json_structure(self):
        self.assertTrue(HOOKS_JSON.is_file(), f"{HOOKS_JSON} must exist")
        data = json.loads(HOOKS_JSON.read_text())

        # Check devstandard-session
        self.assertIn("devstandard-session", data)
        session_hooks = data["devstandard-session"].get("SessionStart", [])
        self.assertTrue(len(session_hooks) > 0)
        self.assertEqual(session_hooks[0]["type"], "command")
        self.assertEqual(session_hooks[0]["command"], "./hooks/session-start")
        self.assertEqual(session_hooks[0]["timeout"], 30)

        pre_invocation_hooks = data["devstandard-session"].get("PreInvocation", [])
        self.assertTrue(len(pre_invocation_hooks) > 0)
        self.assertEqual(pre_invocation_hooks[0]["type"], "command")
        self.assertEqual(pre_invocation_hooks[0]["command"], "./hooks/session-start --pre-invocation")
        self.assertEqual(pre_invocation_hooks[0]["timeout"], 30)

        # Check devstandard-guard
        self.assertIn("devstandard-guard", data)
        guard_hooks = data["devstandard-guard"].get("PreToolUse", [])
        self.assertTrue(len(guard_hooks) > 0)
        self.assertEqual(guard_hooks[0]["matcher"], "run_command")
        sub_hooks = guard_hooks[0].get("hooks", [])
        self.assertTrue(len(sub_hooks) > 0)
        self.assertEqual(sub_hooks[0]["type"], "command")
        self.assertEqual(sub_hooks[0]["command"], "./hooks/pre-tool-use")
        self.assertEqual(sub_hooks[0]["timeout"], 30)


class HookTestCase(unittest.TestCase):
    def setUp(self):
        self.env = {k: v for k, v in os.environ.items() if k != 'DEVSTANDARD_ROLE'}

    def run_hook(self, payload=None, env=None, executable=None, args=()):
        cmd = [str(executable or SESSION_START), *args]
        stdin_data = json.dumps(payload) if payload is not None else ""
        run_env = self.env if env is None else env
        res = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            env=run_env,
            cwd=str(ROOT),
            check=True
        )
        return json.loads(res.stdout)


class SessionStartDeliveryTest(HookTestCase):
    def test_normal_stdin_returns_preamble_and_exact_orchestrator(self):
        payload = {"conversationId": "test", "workspacePaths": ["/tmp"]}
        output = self.run_hook(payload)
        self.assertIn("injectSteps", output)
        self.assertEqual(len(output["injectSteps"]), 1)
        step = output["injectSteps"][0]
        self.assertIn("systemMessage", step)
        msg = step["systemMessage"]["systemMessage"]

        orchestrator_content = ORCHESTRATOR.read_text(encoding='utf-8')
        head = (
            f"DevStandard operating context: reference/orchestrator.md\n"
            f"Plugin root: {ROOT}\n"
            "Complete artifact below: follow it before acting or replying. Resolve references from this root; load them only at their triggers.\n\n"
        )
        self.assertTrue(msg.startswith(head))
        body = msg[len(head):]
        self.assertEqual(body, orchestrator_content)
        self.assertEqual(body.encode('utf-8'), ORCHESTRATOR.read_bytes())

    def test_open_stdin_pipe_returns_without_eof(self):
        for data, suppressed in ((b'', False), (b'{"agent_type":"worker"}', True)):
            with self.subTest(data=data):
                # A file also lets a full role page exceed the OS pipe buffer.
                with tempfile.TemporaryFile() as stdout:
                    proc = subprocess.Popen([str(SESSION_START)], stdin=subprocess.PIPE,
                                            stdout=stdout, stderr=subprocess.PIPE,
                                            env=self.env, cwd=str(ROOT))
                    try:
                        if data:
                            proc.stdin.write(data)
                            proc.stdin.flush()
                        # Keep stdin open throughout the wait; communicate() would close it.
                        proc.wait(timeout=5)
                        self.assertEqual(proc.returncode, 0, proc.stderr.read().decode())
                        stdout.seek(0)
                        output = json.loads(stdout.read())
                        if suppressed:
                            self.assertEqual(output, {})
                        else:
                            self.assertIn('injectSteps', output)
                    finally:
                        if proc.poll() is None:
                            proc.kill()
                        proc.communicate()

    def test_devstandard_role_worker_and_reviewer_suppress_output(self):
        for role in ('worker', 'reviewer'):
            with self.subTest(role=role):
                env = dict(self.env, DEVSTANDARD_ROLE=role)
                output = self.run_hook({"conversationId": "test"}, env=env)
                self.assertEqual(output, {})

    def test_agent_type_worker_and_reviewer_suppress_output(self):
        for agent_type in ('worker', 'devstandard:worker', 'reviewer', 'devstandard:reviewer'):
            with self.subTest(agent_type=agent_type):
                output = self.run_hook({"conversationId": "test", "agent_type": agent_type})
                self.assertEqual(output, {})

    def test_parent_conversation_suppresses_output(self):
        self.assertEqual(self.run_hook({"parentConversationId": "parent"}), {})
        self.assertIn("injectSteps", self.run_hook({"parentConversationId": ""}))

    def test_empty_stdin_and_non_matching_agent_type_delivers(self):
        for payload in ({}, {"conversationId": "test", "agent_type": "orchestrator"}, {"agent_type": None}):
            with self.subTest(payload=payload):
                output = self.run_hook(payload)
                self.assertIn("injectSteps", output)

    def test_native_subagents_detected_via_brain_registry_suppress_output(self):
        with tempfile.TemporaryDirectory(prefix="devstandard-brain-") as tmpdir:
            brain_dir = Path(tmpdir) / "brain"
            parent_dir = brain_dir / "parent-conv-123"
            subagents_dir = parent_dir / ".system_generated" / "subagents"
            subagents_dir.mkdir(parents=True)

            subagents = {
                "worker-subagent": {"typeName": "self", "role": "Issue 4 worker"},
                "reviewer-subagent": {"typeName": "self", "role": "Issue 4 reviewer"},
                "research-subagent": {"typeName": "research", "role": "Codebase Researcher"},
                "untyped-subagent": {"typeName": "self", "role": "General Helper"},
            }

            for conv_id, descriptor in subagents.items():
                record = {
                    "conversationId": conv_id,
                    "subagentDescriptor": descriptor,
                    "state": "SUBAGENT_STATE_ALIVE",
                }
                (subagents_dir / f"{conv_id}.json").write_text(json.dumps(record))

            for conv_id in subagents:
                with self.subTest(subagent=conv_id, route="artifactDirectoryPath"):
                    payload = {
                        "conversationId": conv_id,
                        "artifactDirectoryPath": str(brain_dir / conv_id),
                    }
                    output = self.run_hook(payload)
                    self.assertEqual(output, {})

                with self.subTest(subagent=conv_id, route="transcriptPath"):
                    payload = {
                        "conversationId": conv_id,
                        "transcriptPath": str(brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"),
                    }
                    output = self.run_hook(payload)
                    self.assertEqual(output, {})

            orchestrator_payload = {
                "conversationId": "parent-conv-123",
                "artifactDirectoryPath": str(brain_dir / "parent-conv-123"),
            }
            output = self.run_hook(orchestrator_payload)
            self.assertIn("injectSteps", output)

    def test_missing_orchestrator_emits_stop_warning(self):
        with tempfile.TemporaryDirectory(prefix="devstandard-test-") as tmpdir:
            tmproot = Path(tmpdir)
            (tmproot / "hooks").mkdir()
            shutil.copy2(SESSION_START, tmproot / "hooks/session-start")
            # orchestrator.md does not exist in tmproot / reference
            cmd = [str(tmproot / "hooks/session-start")]
            res = subprocess.run(
                cmd,
                input=json.dumps({"conversationId": "test"}),
                capture_output=True,
                text=True,
                env=self.env,
                cwd=str(tmproot),
                check=True
            )
            output = json.loads(res.stdout)
            self.assertIn("injectSteps", output)
            msg = output["injectSteps"][0]["systemMessage"]["systemMessage"]
            self.assertIn(f"Stop before acting: DevStandard cannot read {tmproot / 'reference/orchestrator.md'}", msg)
            self.assertIn("Report the missing role context to the caller.", msg)


class PreInvocationDeliveryTest(HookTestCase):
    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory(prefix="devstandard-pre-invocation-")
        self.addCleanup(self.scratch.cleanup)
        self.transcript = Path(self.scratch.name) / "transcript.jsonl"
        head = (
            f"DevStandard operating context: reference/orchestrator.md\n"
            f"Plugin root: {ROOT}\n"
            "Complete artifact below: follow it before acting or replying. Resolve references from this root; load them only at their triggers.\n\n"
        )
        self.context = head + ORCHESTRATOR.read_text(encoding='utf-8')
        self.context_step = {"type": "SYSTEM_MESSAGE", "content": self.context}
        self.expected = {"injectSteps": [{"systemMessage": {"systemMessage": self.context}}]}

        worker_head = (
            f"DevStandard operating context: reference/worker.md\n"
            f"Plugin root: {ROOT}\n"
            "Complete artifact below: follow it before acting or replying. Resolve references from this root; recover your dynamic # Task packet (Issue, Branch, Worktree, Bounds, Done-check) from the issue's devstandard-dispatch-v1 receipt or your local transcript if omitted from the compaction summary.\n\n"
        )
        self.worker_context = worker_head + WORKER.read_text(encoding='utf-8')
        self.worker_context_step = {"type": "SYSTEM_MESSAGE", "content": self.worker_context}
        self.worker_expected = {"injectSteps": [{"systemMessage": {"systemMessage": self.worker_context}}]}

    def write_steps(self, *steps):
        self.transcript.write_text("\n".join(json.dumps(step) for step in steps) + "\n")

    def invoke(self, **kwargs):
        return self.run_hook({"transcriptPath": str(self.transcript)},
                             args=("--pre-invocation",), **kwargs)

    def test_missing_invalid_or_unreadable_transcript_is_noop(self):
        for payload in ({}, {"transcriptPath": None}, {"transcriptPath": ""},
                        {"transcriptPath": 42}, {"transcriptPath": []},
                        {"transcriptPath": str(self.transcript)},
                        {"transcriptPath": self.scratch.name},
                        {"transcriptPath": "bad\u0000path"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})
        self.transcript.write_bytes(b'\xff\n')
        self.assertEqual(self.invoke(), {})

    def test_without_checkpoint_is_noop(self):
        for steps in ((), (self.context_step,),
                      ({"type": "USER_MESSAGE", "content": "CHECKPOINT"},)):
            with self.subTest(steps=steps):
                self.write_steps(*steps)
                self.assertEqual(self.invoke(), {})

    def test_checkpoint_after_startup_reinjects_exact_context(self):
        self.write_steps(self.context_step, {"type": "CHECKPOINT"})
        self.assertEqual(self.invoke(), self.expected)

    def test_checkpoint_without_prior_context_reinjects(self):
        self.write_steps({"type": "CHECKPOINT"})
        self.assertEqual(self.invoke(), self.expected)

    def test_reinjected_context_prevents_duplicates_until_next_checkpoint(self):
        self.write_steps(self.context_step, {"type": "CHECKPOINT"}, self.context_step)
        self.assertEqual(self.invoke(), {})
        with self.transcript.open('a') as transcript:
            transcript.write(json.dumps({"type": "USER_MESSAGE", "content": "next turn"}) + "\n")
        self.assertEqual(self.invoke(), {})
        with self.transcript.open('a') as transcript:
            transcript.write(json.dumps({"type": "CHECKPOINT"}) + "\n")
        self.assertEqual(self.invoke(), self.expected)

    def test_only_marked_system_messages_count_as_context(self):
        for step in ({"type": "SYSTEM_MESSAGE", "content": "Unrelated host instructions"},
                     {"type": "SYSTEM_MESSAGE", "content": self.worker_context},
                     {"type": "USER_MESSAGE", "content": self.context},
                     {"type": "SYSTEM_MESSAGE"},
                     {"type": "SYSTEM_MESSAGE", "content": None},
                     {"type": "SYSTEM_MESSAGE", "content": [self.context]}):
            with self.subTest(step=step):
                self.write_steps(self.context_step, {"type": "CHECKPOINT"}, step)
                self.assertEqual(self.invoke(), self.expected)

    def test_blank_malformed_and_non_object_records_are_ignored(self):
        self.write_steps(self.context_step)
        with self.transcript.open('a') as transcript:
            transcript.write('\nnot json\nnull\n[]\n42\n{"type":"CHECKPOINT"}\n{"unfinished":\n')
        self.assertEqual(self.invoke(), self.expected)
        with self.transcript.open('a') as transcript:
            transcript.write(json.dumps(self.context_step) + '\nnot json\n')
        self.assertEqual(self.invoke(), {})

    def test_event_fields_select_pre_invocation_even_when_zero(self):
        for field in ("invocationNum", "initialNumSteps"):
            for value in (0, 1):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.run_hook({field: value}), {})
                    self.write_steps(self.context_step, {"type": "CHECKPOINT"})
                    self.assertEqual(self.run_hook({field: value, "transcriptPath": str(self.transcript)}),
                                     self.expected)
                    self.write_steps(self.context_step, {"type": "CHECKPOINT"}, self.context_step)
                    self.assertEqual(self.run_hook({field: value, "transcriptPath": str(self.transcript)}), {})

    def test_role_agent_type_and_parent_suppress_after_checkpoint(self):
        self.write_steps({"type": "CHECKPOINT"})
        for role in ("worker", "reviewer"):
            with self.subTest(role=role):
                env = dict(self.env, DEVSTANDARD_ROLE=role)
                self.assertEqual(self.invoke(env=env), {})
                self.assertEqual(
                    self.run_hook({"transcriptPath": str(self.transcript), "agent_type": "worker"},
                                  env=env, args=("--pre-invocation",)),
                    {},
                )
        for fields in ({"agent_type": "reviewer"}, {"agent_type": "devstandard:reviewer"},
                       {"parentConversationId": "parent"}):
            with self.subTest(suppressed_fields=fields):
                self.assertEqual(self.run_hook({"transcriptPath": str(self.transcript), **fields},
                                               args=("--pre-invocation",)), {})

        for agent_type in ("worker", "devstandard:worker"):
            for extra in ({}, {"parentConversationId": "parent"}):
                with self.subTest(worker_agent_type=agent_type, extra=extra):
                    payload = {"transcriptPath": str(self.transcript), "agent_type": agent_type, **extra}
                    self.write_steps({"type": "USER_MESSAGE", "content": "working"})
                    self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})
                    self.write_steps({"type": "CHECKPOINT"}, self.context_step)
                    self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), self.worker_expected)
                    self.write_steps({"type": "CHECKPOINT"}, self.worker_context_step)
                    self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})
                    with self.transcript.open('a') as transcript:
                        transcript.write('{"type":"CHECKPOINT"}\n')
                    self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), self.worker_expected)

    def test_brain_registry_suppresses_all_subagents_after_checkpoint(self):
        brain = Path(self.scratch.name) / "brain"
        registry = brain / "parent" / ".system_generated/subagents"
        registry.mkdir(parents=True)
        suppressed_subagents = {
            "reviewer": {"subagentDescriptor": {"typeName": "self", "role": "Issue 15 reviewer"}},
            "worker-reviewer": {"subagentDescriptor": {"typeName": "self", "role": "Issue 15 worker reviewer"}},
            "research": {"subagentDescriptor": {"typeName": "research", "role": "Codebase Researcher"}},
            "worker-research": {"subagentDescriptor": {"typeName": "research", "role": "Worker Researcher"}},
            "helper": {"subagentDescriptor": {"typeName": "self", "role": "General Helper"}},
            "nodesc": {},
        }
        for conv_id, record_extra in suppressed_subagents.items():
            (registry / f"{conv_id}.json").write_text(json.dumps({
                "conversationId": conv_id,
                "state": "SUBAGENT_STATE_ALIVE",
                **record_extra,
            }))
            transcript = brain / conv_id / ".system_generated/logs/transcript.jsonl"
            transcript.parent.mkdir(parents=True)
            transcript.write_text('{"type":"CHECKPOINT"}\n')
            for route in ("artifactDirectoryPath", "transcriptPath"):
                for extra in ({}, {"parentConversationId": "parent"}):
                    with self.subTest(suppressed=conv_id, route=route, extra=extra):
                        payload = {"conversationId": conv_id,
                                   "transcriptPath": str(transcript if route == "transcriptPath" else self.transcript),
                                   **extra}
                        if route == "artifactDirectoryPath":
                            self.write_steps({"type": "CHECKPOINT"})
                            payload[route] = str(brain / conv_id)
                        self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})

        worker_subagents = {
            "worker": {"typeName": "self", "role": "Issue 15 worker"},
            "typed-worker": {"typeName": "devstandard:worker", "role": "Issue 15"},
        }
        for conv_id, descriptor in worker_subagents.items():
            (registry / f"{conv_id}.json").write_text(json.dumps({
                "conversationId": conv_id,
                "subagentDescriptor": descriptor,
                "state": "SUBAGENT_STATE_ALIVE",
            }))
            transcript = brain / conv_id / ".system_generated/logs/transcript.jsonl"
            transcript.parent.mkdir(parents=True)
            for route in ("artifactDirectoryPath", "transcriptPath"):
                for extra in ({}, {"parentConversationId": "parent"}):
                    with self.subTest(worker=conv_id, route=route, extra=extra):
                        target_transcript = transcript if route == "transcriptPath" else self.transcript
                        payload = {"conversationId": conv_id,
                                   "transcriptPath": str(target_transcript),
                                   **extra}
                        if route == "artifactDirectoryPath":
                            payload[route] = str(brain / conv_id)

                        target_transcript.write_text('{"type":"USER_MESSAGE","content":"initial"}\n')
                        self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})

                        target_transcript.write_text('{"type":"CHECKPOINT"}\n')
                        self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), self.worker_expected)
                        self.assertEqual(self.run_hook({**payload, "invocationNum": 1}), self.worker_expected)
                        self.assertEqual(
                            self.run_hook(payload, env=dict(self.env, DEVSTANDARD_ROLE="worker"),
                                          args=("--pre-invocation",)),
                            {},
                        )

                        with target_transcript.open('a') as handle:
                            handle.write(json.dumps(self.worker_context_step) + '\n')
                        self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), {})

                        with target_transcript.open('a') as handle:
                            handle.write('{"type":"CHECKPOINT"}\n')
                        self.assertEqual(self.run_hook(payload, args=("--pre-invocation",)), self.worker_expected)

    def test_missing_page_warns_once_per_checkpoint(self):
        plugin = Path(self.scratch.name) / "plugin"
        (plugin / "hooks").mkdir(parents=True)
        executable = plugin / "hooks/session-start"
        shutil.copy2(SESSION_START, executable)
        warning = (f"Stop before acting: DevStandard cannot read {plugin / 'reference/orchestrator.md'}. "
                   "Report the missing role context to the caller.")
        self.write_steps({"type": "CHECKPOINT"})
        self.assertEqual(self.invoke(executable=executable),
                         {"injectSteps": [{"systemMessage": {"systemMessage": warning}}]})
        with self.transcript.open('a') as transcript:
            transcript.write(json.dumps({"type": "SYSTEM_MESSAGE", "content": warning}) + '\n')
        self.assertEqual(self.invoke(executable=executable), {})
        with self.transcript.open('a') as transcript:
            transcript.write('{"type":"CHECKPOINT"}\n')
        self.assertEqual(self.invoke(executable=executable),
                         {"injectSteps": [{"systemMessage": {"systemMessage": warning}}]})

        # Present orchestrator.md while worker.md is missing: native worker warns naming worker.md
        shutil.copytree(ROOT / "scripts", plugin / "scripts")
        (plugin / "reference").mkdir(parents=True)
        shutil.copy2(ORCHESTRATOR, plugin / "reference/orchestrator.md")
        brain = Path(self.scratch.name) / "missing-worker-brain"
        registry = brain / "parent" / ".system_generated/subagents"
        registry.mkdir(parents=True)
        (registry / "worker-1.json").write_text(json.dumps({
            "conversationId": "worker-1",
            "subagentDescriptor": {"typeName": "self", "role": "Issue 37 worker"},
            "state": "SUBAGENT_STATE_ALIVE",
        }))
        worker_warning = (f"Stop before acting: DevStandard cannot read {plugin / 'reference/worker.md'}. "
                          "Report the missing role context to the caller.")
        for payload in (
            {"transcriptPath": str(self.transcript), "agent_type": "worker"},
            {"conversationId": "worker-1", "artifactDirectoryPath": str(brain / "worker-1"),
             "transcriptPath": str(self.transcript), "parentConversationId": "parent"},
        ):
            with self.subTest(missing_worker_payload=payload):
                self.write_steps({"type": "CHECKPOINT"})
                self.assertEqual(
                    self.run_hook(payload, executable=executable, args=("--pre-invocation",)),
                    {"injectSteps": [{"systemMessage": {"systemMessage": worker_warning}}]},
                )
                with self.transcript.open('a') as transcript:
                    transcript.write(json.dumps({"type": "SYSTEM_MESSAGE", "content": worker_warning}) + '\n')
                self.assertEqual(self.run_hook(payload, executable=executable, args=("--pre-invocation",)), {})
                with self.transcript.open('a') as transcript:
                    transcript.write('{"type":"CHECKPOINT"}\n')
                self.assertEqual(
                    self.run_hook(payload, executable=executable, args=("--pre-invocation",)),
                    {"injectSteps": [{"systemMessage": {"systemMessage": worker_warning}}]},
                )

    def test_multi_chunk_reverse_tail_transcript_scan(self):
        # Build > 250 KB padding with multi-byte UTF-8 characters so lines cross 64 KB chunk boundaries
        utf8_turn = json.dumps({
            "type": "USER_MESSAGE",
            "content": ("turn — → 中文 " * 310),
        }) + "\n"
        chunk_spanning_padding = utf8_turn * 60  # > 250 KB (> 4 x 64 KB chunks)
        self.assertGreater(len(chunk_spanning_padding.encode('utf-8')), 250_000)

        # 1. Multi-chunk transcript without CHECKPOINT -> {}
        self.transcript.write_text(chunk_spanning_padding, encoding='utf-8')
        self.assertEqual(self.invoke(), {})

        # 2. CHECKPOINT followed by > 150 KB of turns/malformed records -> restores across multiple chunks
        tail_padding = (utf8_turn * 38) + "\nnot-json\n[]\n42\n"
        self.assertGreater(len(tail_padding.encode('utf-8')), 150_000)
        self.transcript.write_text(
            chunk_spanning_padding + '{"type":"CHECKPOINT"}\n' + tail_padding,
            encoding='utf-8',
        )
        self.assertEqual(self.invoke(), self.expected)
        self.assertEqual(
            self.run_hook({"transcriptPath": str(self.transcript), "agent_type": "worker"},
                          args=("--pre-invocation",)),
            self.worker_expected,
        )

        # 3. Context SYSTEM_MESSAGE placed across a 64 KB boundary after CHECKPOINT suppresses duplicates
        prefix_to_boundary = "x" * (65536 - 200)
        boundary_line = json.dumps({"type": "USER_MESSAGE", "content": prefix_to_boundary}) + "\n"
        self.transcript.write_text(
            '{"type":"CHECKPOINT"}\n'
            + boundary_line
            + json.dumps(self.context_step) + "\n"
            + tail_padding,
            encoding='utf-8',
        )
        self.assertEqual(self.invoke(), {})

        self.transcript.write_text(
            '{"type":"CHECKPOINT"}\n'
            + boundary_line
            + json.dumps(self.worker_context_step) + "\n"
            + tail_padding,
            encoding='utf-8',
        )
        self.assertEqual(
            self.run_hook({"transcriptPath": str(self.transcript), "agent_type": "worker"},
                          args=("--pre-invocation",)),
            {},
        )

        # 4. Reverse-tail early stop: invalid bytes in chunk 0 are never read when tail chunk decides
        mod = load_session_start_module()
        early_stop_path = Path(self.scratch.name) / "early-stop.jsonl"
        early_stop_path.write_bytes(
            b'\xff\n'
            + tail_padding.encode('utf-8')
            + b'{"type":"CHECKPOINT"}\n'
        )
        self.assertTrue(mod.needs_context({"transcriptPath": str(early_stop_path)}))
        with early_stop_path.open('ab') as handle:
            handle.write((json.dumps(self.context_step) + '\n').encode('utf-8'))
        self.assertFalse(mod.needs_context({"transcriptPath": str(early_stop_path)}))

        # 5. Exact 3-byte UTF-8 character and CHECKPOINT JSON line split across a chunk boundary
        split_utf8_path = Path(self.scratch.name) / "split-utf8.jsonl"
        # Place 3-byte em-dash b'\xe2\x80\x94' straddling the final 65536-byte boundary
        tail_after_emdash = b'"}\n' + (b'{"type":"USER_MESSAGE","content":"' + b'a' * 990 + b'"}\n') * 63
        pad_len = 65536 - len(tail_after_emdash) - 2  # leaves 2 trailing bytes of em-dash inside final chunk
        self.assertGreater(pad_len, 0)
        split_utf8_path.write_bytes(
            b'{"type":"CHECKPOINT"}\n'
            + b'{"type":"USER_MESSAGE","content":"\xe2\x80\x94'
            + (b'b' * pad_len)
            + tail_after_emdash
        )
        # Verify the final 65536-byte chunk starts mid-codepoint (0x80) so naive chunk decoding would fail
        raw_bytes = split_utf8_path.read_bytes()
        self.assertEqual(raw_bytes[-65536], 0x80)
        self.assertTrue(mod.needs_context({"transcriptPath": str(split_utf8_path)}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
