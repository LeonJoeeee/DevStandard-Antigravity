#!/usr/bin/env python3
"""Exercise DevStandard Antigravity session hooks and hooks.json declarations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = ROOT / 'hooks.json'
SESSION_START = ROOT / 'hooks/session-start'
ORCHESTRATOR = ROOT / 'reference/orchestrator.md'


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


class SessionStartDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.env = {k: v for k, v in os.environ.items() if k != 'DEVSTANDARD_ROLE'}

    def run_hook(self, payload=None, env=None, executable=None):
        cmd = [str(executable or SESSION_START)]
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

    def test_empty_stdin_and_non_matching_agent_type_delivers(self):
        for payload in ({}, {"conversationId": "test", "agent_type": "orchestrator"}, {"agent_type": None}):
            with self.subTest(payload=payload):
                output = self.run_hook(payload)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
