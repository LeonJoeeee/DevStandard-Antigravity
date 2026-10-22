#!/usr/bin/env python3
"""Hard-edge probes: PreToolUse format decisions, git replay proof, acceptance and merge guard."""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hard_edges
import review_packet

HOOK = ROOT / 'hooks/pre-tool-use'
GUARD = ROOT / 'scripts/guard'


class AntigravityPreToolUseFormatTest(unittest.TestCase):
    def run_hook(self, role, tool, args, agent_type=None):
        payload = {'toolCall': {'name': tool, 'args': args}}
        if agent_type:
            payload['agent_type'] = agent_type
        res = subprocess.run(
            [sys.executable, str(HOOK), '--role', role],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(ROOT)
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_worker_refusals_and_admissions(self):
        # Worker refuses forbidden operations
        for cmd in ('git merge main', 'git push origin main', 'git push origin master'):
            with self.subTest(cmd=cmd):
                out = self.run_hook('worker', 'run_command', {'CommandLine': cmd})
                self.assertEqual(out.get('decision'), 'deny')
                self.assertTrue(out.get('reason'))

        # Worker admits allowed operations
        for cmd in (
            'git push origin task/1-test',
            'git status',
            'git merge-base main HEAD',
            'git commit -m "merge"',
            "cat <<EOF\nmerge\nEOF"
        ):
            with self.subTest(cmd=cmd):
                out = self.run_hook('worker', 'run_command', {'CommandLine': cmd})
                self.assertEqual(out.get('decision'), 'allow')

        # Worker admits non-shell tools
        for tool in ('write_file', 'edit_file'):
            with self.subTest(tool=tool):
                out = self.run_hook('worker', tool, {'Path': '/tmp/test.txt', 'Content': 'git merge main'})
                self.assertEqual(out.get('decision'), 'allow')

    def test_orchestrator_refusals_and_admissions(self):
        # Refuses raw gh pr merge
        out = self.run_hook('orchestrator', 'run_command', {'CommandLine': 'gh pr merge 1'})
        self.assertEqual(out.get('decision'), 'deny')

        # Admits guard merge, git merge, and issue description carrying gh pr merge
        for cmd in (
            'scripts/guard merge --repo o/r --pr 1',
            'git merge origin/main',
            'gh issue create --body "gh pr merge"'
        ):
            with self.subTest(cmd=cmd):
                out = self.run_hook('orchestrator', 'run_command', {'CommandLine': cmd})
                self.assertEqual(out.get('decision'), 'allow')

    def test_reviewer_refusals_and_admissions(self):
        # Refuses write gh api calls
        for cmd in (
            'gh api -X POST repos/o/r/issues',
            'gh api --method PUT repos/o/r/issues',
            'gh api -f body=x repos/o/r/issues',
            'gh api -F body=x repos/o/r/issues',
            'gh api --field body=x repos/o/r/issues',
            'gh api --input file repos/o/r/issues'
        ):
            with self.subTest(cmd=cmd):
                out = self.run_hook('reviewer', 'run_command', {'CommandLine': cmd})
                self.assertEqual(out.get('decision'), 'deny')

        # Admits read-only gh api and git diff
        for cmd in ('gh api repos/o/r/pulls/1', 'git diff origin/main'):
            with self.subTest(cmd=cmd):
                out = self.run_hook('reviewer', 'run_command', {'CommandLine': cmd})
                self.assertEqual(out.get('decision'), 'allow')

    def test_native_subagent_brain_registry_role_detection(self):
        with tempfile.TemporaryDirectory(prefix="devstandard-pretool-brain-") as tmpdir:
            brain_dir = Path(tmpdir) / "brain"
            parent_dir = brain_dir / "parent-conv-456"
            subagents_dir = parent_dir / ".system_generated" / "subagents"
            subagents_dir.mkdir(parents=True)

            (subagents_dir / "worker-conv.json").write_text(json.dumps({
                "conversationId": "worker-conv",
                "subagentDescriptor": {"typeName": "self", "role": "Issue 4 worker"}
            }))
            (subagents_dir / "reviewer-conv.json").write_text(json.dumps({
                "conversationId": "reviewer-conv",
                "subagentDescriptor": {"typeName": "self", "role": "Issue 4 reviewer"}
            }))
            (subagents_dir / "research-conv.json").write_text(json.dumps({
                "conversationId": "research-conv",
                "subagentDescriptor": {"typeName": "research", "role": "Codebase Researcher"}
            }))

            # 1. Native worker subagent: denies git merge main and git push origin main, allows git status
            for forbidden in ('git merge main', 'git push origin main'):
                with self.subTest(worker_cmd=forbidden):
                    payload = {
                        'conversationId': 'worker-conv',
                        'artifactDirectoryPath': str(brain_dir / 'worker-conv'),
                        'toolCall': {'name': 'run_command', 'args': {'CommandLine': forbidden}}
                    }
                    res = subprocess.run(
                        [sys.executable, str(HOOK), '--role', 'orchestrator'],
                        input=json.dumps(payload),
                        text=True, capture_output=True, cwd=str(ROOT)
                    )
                    self.assertEqual(res.returncode, 0, res.stderr)
                    out = json.loads(res.stdout)
                    self.assertEqual(out.get('decision'), 'deny')
                    self.assertIn('worker role refuses', out.get('reason', ''))

            # Worker admits git status via transcriptPath
            payload = {
                'conversationId': 'worker-conv',
                'transcriptPath': str(brain_dir / 'worker-conv' / '.system_generated' / 'logs' / 'transcript.jsonl'),
                'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'git status'}}
            }
            res = subprocess.run(
                [sys.executable, str(HOOK), '--role', 'orchestrator'],
                input=json.dumps(payload),
                text=True, capture_output=True, cwd=str(ROOT)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out.get('decision'), 'allow')

            # 2. Native reviewer subagent: denies gh api -X POST, allows gh api read
            payload = {
                'conversationId': 'reviewer-conv',
                'artifactDirectoryPath': str(brain_dir / 'reviewer-conv'),
                'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'gh api -X POST repos/o/r/issues'}}
            }
            res = subprocess.run(
                [sys.executable, str(HOOK), '--role', 'orchestrator'],
                input=json.dumps(payload),
                text=True, capture_output=True, cwd=str(ROOT)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out.get('decision'), 'deny')
            self.assertIn('reviewer role refuses', out.get('reason', ''))

            payload = {
                'conversationId': 'reviewer-conv',
                'artifactDirectoryPath': str(brain_dir / 'reviewer-conv'),
                'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'gh api repos/o/r/pulls/1'}}
            }
            res = subprocess.run(
                [sys.executable, str(HOOK), '--role', 'orchestrator'],
                input=json.dumps(payload),
                text=True, capture_output=True, cwd=str(ROOT)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out.get('decision'), 'allow')

            # 3. Native research subagent keeps orchestrator role (git merge origin/main allowed)
            payload = {
                'conversationId': 'research-conv',
                'artifactDirectoryPath': str(brain_dir / 'research-conv'),
                'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'git merge origin/main'}}
            }
            res = subprocess.run(
                [sys.executable, str(HOOK), '--role', 'orchestrator'],
                input=json.dumps(payload),
                text=True, capture_output=True, cwd=str(ROOT)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out.get('decision'), 'allow')

            # 4. Parent orchestrator keeps orchestrator role (git merge origin/main allowed)
            payload = {
                'conversationId': 'parent-conv-456',
                'artifactDirectoryPath': str(brain_dir / 'parent-conv-456'),
                'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'git merge origin/main'}}
            }
            res = subprocess.run(
                [sys.executable, str(HOOK), '--role', 'orchestrator'],
                input=json.dumps(payload),
                text=True, capture_output=True, cwd=str(ROOT)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out.get('decision'), 'allow')


class CodexPreToolUseFormatTest(unittest.TestCase):
    def run_hook(self, role, tool, field, cmd):
        payload = {'tool_name': tool, 'tool_input': {field: cmd}}
        res = subprocess.run(
            [sys.executable, str(HOOK), '--role', role],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(ROOT)
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_codex_format_decisions(self):
        for tool, field in (('Bash', 'command'), ('exec_command', 'cmd')):
            with self.subTest(tool=tool, field=field):
                # Worker denial
                denied = self.run_hook('worker', tool, field, 'git push origin main')
                self.assertEqual(denied.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
                self.assertTrue(denied['hookSpecificOutput'].get('permissionDecisionReason'))

                # Worker admit
                admitted = self.run_hook('worker', tool, field, 'git status')
                self.assertEqual(admitted, {})

                # Orchestrator denial
                orch_denied = self.run_hook('orchestrator', tool, field, 'gh pr merge 1')
                self.assertEqual(orch_denied.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

                # Orchestrator admit
                orch_admitted = self.run_hook('orchestrator', tool, field, 'git merge origin/main')
                self.assertEqual(orch_admitted, {})

                # Reviewer denial
                rev_denied = self.run_hook('reviewer', tool, field, 'gh api -X POST /test')
                self.assertEqual(rev_denied.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

                # Reviewer admit
                rev_admitted = self.run_hook('reviewer', tool, field, 'git diff')
                self.assertEqual(rev_admitted, {})


class FailOpenBehaviorTest(unittest.TestCase):
    def test_malformed_json_and_invalid_inputs_fail_open(self):
        # Malformed JSON
        res = subprocess.run(
            [sys.executable, str(HOOK), '--role', 'worker'],
            input="not valid json",
            text=True,
            capture_output=True,
            cwd=str(ROOT)
        )
        self.assertEqual(res.returncode, 0)
        self.assertEqual(json.loads(res.stdout), {})
        self.assertIn('devstandard role hook admitted this call without deciding', res.stderr)

        # Invalid toolCall / tool_input types
        for bad in (
            '{}',
            '{"toolCall": 123}',
            '{"toolCall": {"name": 123}}',
            '{"toolCall": {"name": "run_command", "args": "invalid"}}',
            '{"tool_name": 123}',
            '{"tool_name": "Bash", "tool_input": "invalid"}'
        ):
            with self.subTest(bad=bad):
                r = subprocess.run(
                    [sys.executable, str(HOOK), '--role', 'worker'],
                    input=bad,
                    text=True,
                    capture_output=True,
                    cwd=str(ROOT)
                )
                self.assertEqual(r.returncode, 0)
                self.assertEqual(json.loads(r.stdout), {})


class HelperSettingsAndConfigTest(unittest.TestCase):
    def test_helper_settings(self):
        rows = hard_edges.helper_settings(ROOT)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][1:], ('gpt-6-astra', 'max', 'inherit'))
        self.assertEqual(rows[1][1:], ('gpt-6.1-sol', 'high', 'inherit'))
        self.assertEqual(rows[2][1:], ('gpt-6-luna', 'max', 'flash'))

    def test_judgment_subagent_setting(self):
        self.assertEqual(hard_edges.judgment_subagent_setting(ROOT), ('gpt-6.1-sol', 'high'))

    def test_codex_helper_line(self):
        line = hard_edges.codex_helper_line(ROOT)
        self.assertTrue(line.startswith('Helpers:'))
        self.assertIn('gpt-6-astra', line)
        self.assertIn('gpt-6.1-sol', line)
        self.assertIn('gpt-6-luna', line)

    def test_codex_hook_config(self):
        config = hard_edges.codex_hook_config(ROOT, 'worker')
        self.assertIn('hooks.PreToolUse=[{matcher=".*",hooks=[{type="command",command="', config)
        self.assertIn('--role worker', config)
        self.assertIn('agents.default_subagent_model="gpt-6.1-sol"', config)
        self.assertIn('agents.default_subagent_reasoning_effort="high"', config)


class RebaseProofAndManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hard-edge-rebase-')
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k != 'DEVSTANDARD_ROLE'}
        self.env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Probe')
        self.git('config', 'user.email', 'probe@example.invalid')
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.0'}, indent=2) + '\n')
        self.git('add', 'plugin.json')
        self.git('commit', '-m', 'initial')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.project), *args], env=self.env, text=True).strip()

    def test_manifests_constant(self):
        self.assertEqual(hard_edges.MANIFESTS, ('plugin.json',))

    def test_version_only_and_manifest_bump(self):
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.1'}, indent=2) + '\n')
        self.git('add', 'plugin.json')
        self.git('commit', '-m', 'bump version')
        head = self.git('rev-parse', 'HEAD')

        self.assertTrue(hard_edges.version_only(self.project, self.base, head))
        self.assertEqual(hard_edges.manifest_bump(self.project, self.base, head, 'plugin.json'), ['1.0.0', '1.0.1'])

    def test_compare_rebase_passes_with_identical_change_and_version_bump(self):
        # Create topic with code edit and version bump
        self.git('checkout', '-b', 'topic')
        (self.project / 'code.txt').write_text('feature\n')
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.1'}, indent=2) + '\n')
        self.git('add', '.')
        self.git('commit', '-m', 'topic work')
        old_head = self.git('rev-parse', 'HEAD')

        # Advance main
        self.git('checkout', 'main')
        (self.project / 'unrelated.txt').write_text('unrelated\n')
        self.git('add', '.')
        self.git('commit', '-m', 'main advances')
        new_base = self.git('rev-parse', 'HEAD')

        # Rebase topic on main
        self.git('checkout', 'topic')
        self.git('rebase', 'main')
        new_head = self.git('rev-parse', 'HEAD')

        result = hard_edges.compare_rebase(self.project, self.base, old_head, new_base, new_head)
        self.assertEqual(result['comparison'], 'pass')
        self.assertIsNone(result['version_bump'])

    def test_compare_rebase_with_bump_past_merged_bump(self):
        # Topic work carrying 1.0.1 bump
        self.git('checkout', '-b', 'bump-topic')
        (self.project / 'code.txt').write_text('feature\n')
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.1'}, indent=2) + '\n')
        self.git('add', '.')
        self.git('commit', '-m', 'topic work')
        old_head = self.git('rev-parse', 'HEAD')

        # Main merges another PR carrying 1.0.1
        self.git('checkout', 'main')
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.1'}, indent=2) + '\n')
        self.git('add', '.')
        self.git('commit', '-m', 'another PR merges 1.0.1')
        new_base = self.git('rev-parse', 'HEAD')

        # Topic rebases and bumps to 1.0.2 to advance past merged bump
        self.git('checkout', 'bump-topic')
        self.git('rebase', 'main')
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.2'}, indent=2) + '\n')
        self.git('add', 'plugin.json')
        self.git('commit', '--amend', '--no-edit')
        new_head = self.git('rev-parse', 'HEAD')

        result = hard_edges.compare_rebase(self.project, self.base, old_head, new_base, new_head)
        self.assertEqual(result['comparison'], 'pass')
        self.assertEqual(result['version_bump'], ['1.0.1', '1.0.2'])


class CommitChecksTest(unittest.TestCase):
    def test_commit_checks_evaluation(self):
        # All green passes
        with patch.object(hard_edges, 'api', return_value={'check_runs': [
            {'name': 'test', 'status': 'completed', 'conclusion': 'success'},
            {'name': 'lint', 'status': 'completed', 'conclusion': 'success'}
        ]}):
            runs = hard_edges.commit_checks('o/r', 'a' * 40, required=['test'])
            self.assertEqual(runs['test'], 'success')

        # Failed check raises Refusal
        with patch.object(hard_edges, 'api', return_value={'check_runs': [
            {'name': 'test', 'status': 'completed', 'conclusion': 'failure'}
        ]}):
            with self.assertRaises(hard_edges.Refusal):
                hard_edges.commit_checks('o/r', 'a' * 40, required=['test'])

        # Missing required check raises Refusal
        with patch.object(hard_edges, 'api', return_value={'check_runs': [
            {'name': 'other', 'status': 'completed', 'conclusion': 'success'}
        ]}):
            with self.assertRaises(hard_edges.Refusal):
                hard_edges.commit_checks('o/r', 'a' * 40, required=['test'])


class AcceptanceTest(unittest.TestCase):
    def verdict(self, head='a' * 40, goal='Yes', floor1='Pass', floor2='Pass'):
        ready = 'Yes' if (goal, floor1, floor2) == ('Yes', 'Pass', 'Pass') else 'No'
        return f"""## Merge check 1 — round 1
Reviewer: Probe, read-only — reviewed {head}
### Goal verdict
{goal} — Checked against the diff.
### Floor
1. Evidence-backed completion claim: {floor1} — Checked.
2. Authorization and scope: {floor2} — Checked.
Ready to merge: {ready} — Goal and Floor.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""

    def test_acceptance_accepts_clean_verdict(self):
        row = {'id': 1, 'body': self.verdict('a' * 40), 'author_association': 'OWNER'}
        accepted = hard_edges.acceptance([row], 'a' * 40)
        self.assertEqual(accepted['id'], 1)

    def test_acceptance_refuses_stale_head_and_floor_failure(self):
        # Stale head
        row_stale = {'id': 1, 'body': self.verdict('b' * 40), 'author_association': 'OWNER'}
        with self.assertRaises(hard_edges.Refusal):
            hard_edges.acceptance([row_stale], 'a' * 40)

        # Floor fail
        row_floor_fail = {'id': 1, 'body': self.verdict('a' * 40, floor1='Fail'), 'author_association': 'OWNER'}
        with self.assertRaises(hard_edges.Refusal):
            hard_edges.acceptance([row_floor_fail], 'a' * 40)

        # Goal No without allow_goal_no
        row_goal_no = {'id': 1, 'body': self.verdict('a' * 40, goal='No'), 'author_association': 'OWNER'}
        with self.assertRaises(hard_edges.Refusal):
            hard_edges.acceptance([row_goal_no], 'a' * 40)
        # Goal No allowed
        self.assertEqual(hard_edges.acceptance([row_goal_no], 'a' * 40, allow_goal_no=True)['id'], 1)


class MergeCheckTest(unittest.TestCase):
    def test_merge_check_preserves_antigravity_and_codex_session_trailers(self):
        head = 'a' * 40
        base = 'b' * 40
        project = Path('/tmp')

        message = (
            "feat: implement feature\n\n"
            "Antigravity-Session: https://gemini.google.com/session/12345\n"
            "Codex-Session: https://chatgpt.com/session/67890\n"
            "Co-authored-by: Worker <worker@example.com>\n"
        )

        pr = {
            'title': 'feat: my pr',
            'head': {'sha': head, 'repo': {'full_name': 'o/r'}},
            'base': {'ref': 'main', 'repo': {'full_name': 'o/r'}},
            'body': 'Closes #12'
        }

        verdict_body = AcceptanceTest().verdict(head)
        comments = [{'id': 100, 'body': verdict_body, 'author_association': 'OWNER'}]

        called_merge = []

        def mock_api(endpoint, *args, **kwargs):
            if endpoint == 'repos/o/r':
                return {'default_branch': 'main'}
            if endpoint == 'repos/o/r/branches/main':
                return {'commit': {'sha': base}}
            if endpoint == 'repos/o/r/pulls/13':
                return pr
            if endpoint == 'repos/o/r/issues/13/comments?per_page=100':
                return comments
            if endpoint == 'repos/o/r/commits/' + head + '/check-runs?per_page=100':
                return {'check_runs': [{'name': f'merged-result / {base} / {head}', 'status': 'completed', 'conclusion': 'success'}]}
            if '/status?' in endpoint:
                return {'statuses': []}
            if endpoint.endswith('/merge'):
                called_merge.append((endpoint, args))
                return {'merged': True}
            raise ValueError('unexpected API call: ' + endpoint)

        def mock_run(*args, **kwargs):
            if 'log' in args:
                return message
            if 'merge-base' in args:
                return ''
            return ''

        with patch.object(hard_edges, 'project_repo', return_value='o/r'), \
             patch.object(hard_edges, 'api', side_effect=mock_api), \
             patch.object(hard_edges, 'run', side_effect=mock_run), \
             patch.object(hard_edges, 'version_only', return_value=False):
            result = hard_edges.merge_check(project, 'o/r', 13, execute=True)
            self.assertEqual(result['merge'], 'pass')
            self.assertTrue(called_merge)
            args = called_merge[0][1]
            commit_msg_arg = next(arg for arg in args if isinstance(arg, str) and arg.startswith('commit_message='))
            self.assertIn('Antigravity-Session: https://gemini.google.com/session/12345', commit_msg_arg)
            self.assertIn('Codex-Session: https://chatgpt.com/session/67890', commit_msg_arg)
            self.assertIn('Co-authored-by: Worker <worker@example.com>', commit_msg_arg)


class ProtectionCheckTest(unittest.TestCase):
    def test_plan_limit_reports_unavailable_gate(self):
        plan_limit = hard_edges.Refusal(
            'gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)'
        )
        with patch.object(hard_edges, 'api', side_effect=plan_limit):
            result = hard_edges.protection_check('o/r', 'main', ['test'])
            self.assertEqual(result['protection'], "unavailable on this repository's plan")

    def test_protected_branch_with_required_checks(self):
        def mock_api(endpoint, *args):
            if endpoint.endswith('/protection'):
                return {
                    'required_status_checks': {'strict': True, 'contexts': ['test']},
                    'enforce_admins': {'enabled': True},
                    'allow_force_pushes': {'enabled': False},
                    'allow_deletions': {'enabled': False}
                }
            if 'rules' in endpoint:
                return []
            raise ValueError(endpoint)

        with patch.object(hard_edges, 'api', side_effect=mock_api):
            result = hard_edges.protection_check('o/r', 'main', ['test'])
            self.assertEqual(result['protection'], 'pass')


if __name__ == '__main__':
    unittest.main(verbosity=2)
