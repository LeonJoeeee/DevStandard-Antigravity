#!/usr/bin/env python3
"""Review assembly/publication integration: real git and dispatcher, mock GitHub/executor I/O."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('dispatch_tests', Path(__file__).with_name('test-dispatch.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
SOURCE = fixtures.SOURCE


# Canonical verdict fixture
CANONICAL_VERDICT = """Reviewer: Probe, read-only — reviewed {head}
### Goal verdict
Yes — the PR accomplishes the issue's goal within its bounds and done-check.
### Floor
1. Evidence-backed completion claim: Pass — the claimed commands and outputs match the diff.
2. Authorization and scope: Pass — no unauthorized irreversible action and nothing outside the task.
Ready to merge: Yes — decided only by the Goal verdict and these two Floor checks.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""

ROUND_ONE_VERDICT = """Reviewer: Codex, gpt-6.1-sol at xhigh, read-only — reviewed db4e19917200c4262279ae2752460ec68b74573b
### Goal verdict
No — the PR substantially implements the issue, but completion claim remains incomplete.
### Floor
1. Evidence-backed completion claim: Pass — evidence checked.
2. Authorization and scope: Pass — scope checked.
Ready to merge: No — Goal verdict is No.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""

EMPHASIZED_ROUND_ONE_VERDICT = """Reviewer: Codex, gpt-6.1-sol at xhigh, read-only — reviewed 2838572a5aa0e788ba7a5640173c8543c134217a
### Goal verdict
**No** — the PR is pending sign-off.
### Floor
1. Evidence-backed completion claim: **Pass** — evidence checked.
2. Authorization and scope: **Pass** — scope checked.
Ready to merge: **No** — human decision remains unrecorded.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""

LABEL_EMPHASIZED_ROUND_ONE_VERDICT = """Reviewer: Antigravity subagent, pro, read-only — reviewed 0bd3b0acf4457c0960cc676b78227914ab6a51fe
### Goal verdict
**Yes** — the PR accomplishes the goal.
### Floor
1. **Evidence-backed completion claim: Pass** — diff checked.
2. **Authorization and scope: Pass** — scope checked.
**Ready to merge: Yes** — decided only by Goal and Floor.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""

DECISION_LINES = (
    ('Yes', 'Goal verdict'),
    ('1. Evidence-backed completion claim: Pass', '1. Evidence-backed completion claim'),
    ('2. Authorization and scope: Pass', '2. Authorization and scope'),
    ('Ready to merge: Yes', 'Ready to merge')
)


def canonical_verdict(head='a' * 40, bare=None):
    verdict = CANONICAL_VERDICT.format(head=head)
    if bare is None:
        return verdict
    return re.sub('^' + re.escape(bare) + r' — [^\n]*$', bare, verdict, flags=re.M)


def malformed_shapes(head='a' * 40):
    body = canonical_verdict(head)
    shapes = {
        'missing Floor': body.replace('### Floor\n', ''),
        'missing Notes': body.replace('### Notes\n', ''),
        'missing Ready to merge': re.sub(r'^Ready to merge: [^\n]*\n', '', body, flags=re.M),
        'another head reviewed': canonical_verdict('b' * 40),
        'second Goal answer': body.replace('Yes — the PR', 'No — contradicts acceptance.\nYes — the PR'),
    }
    for heading in ('Goal verdict', 'Floor', 'Notes'):
        shapes['duplicate ' + heading] = body.replace('### ' + heading + '\n',
                                                      ('### ' + heading + '\n') * 2)
    for label in ('1. Evidence-backed completion claim', '2. Authorization and scope', 'Ready to merge'):
        value = 'No' if label == 'Ready to merge' else 'Fail'
        shapes['second ' + label] = body.replace('### Notes\n',
                                                 f'{label}: {value} — contradicts acceptance.\n### Notes\n')
    return shapes


def admitted_shapes(head='a' * 40):
    body = canonical_verdict(head)
    closing = 'Post this verdict whole on the PR before acting on it.\n'
    return {
        'no closing line': body.replace(closing, ''),
        'trailing text after the closing line': body + 'An extra instruction after the close.\n',
        'empty Notes': body.replace('### Notes\nNone.\n', '### Notes\n'),
        'blank Notes': body.replace('### Notes\nNone.\n', '### Notes\n\n \t\n'),
    }


def decision(label, value, emphasis, wrap):
    number, _, rest = label.partition('. ') if label[0].isdigit() else ('', '', label)
    number = number and number + '. '
    if wrap == 'result':
        return f'{number}{rest} {emphasis}{value}{emphasis}'
    if wrap == 'label':
        return f'{number}{emphasis}{rest} {value}{emphasis}'
    return f'{emphasis}{number}{rest} {value}{emphasis}'


class ContractTest(unittest.TestCase):
    def fence(self):
        source = (SOURCE / 'reference/code-review-prompt.md').read_text()
        matches = re.findall(r'\n```\n(.*?)\n```\n', source, re.S)
        self.assertEqual(len(matches), 1, 'the judging contract must stay a single bare fence')
        return matches[0]

    def test_contract_exposes_the_ci_configuration_slot_once(self):
        fence = self.fence()
        self.assertEqual(fence.count('{CI_CONFIGURATION_PATHS}'), 1)

    def test_contract_is_in_one_machine_readable_fence(self):
        self.fence()


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.d = fixtures.DispatchTest()
        self.d.setUp()
        self.addCleanup(self.d.doCleanups)
        self.root, self.project, self.env = self.d.root, self.d.project, self.d.env
        self.script = SOURCE / 'scripts/review-packet'
        remote = self.root / 'remote.git'
        self.d.git('init', '--bare', str(remote))
        self.d.git('remote', 'set-url', 'origin', str(remote))
        self.d.git('push', 'origin', 'main')
        self.base = self.d.git('rev-parse', 'HEAD')
        self.branch, self.wt = self.d.hand_made_lane()
        self.d.call('--adopt', '--base', 'origin/main', '--branch', self.branch, '--worktree', str(self.wt))
        (self.wt / 'result.txt').write_text('Result\n\n')
        self.d.git('-C', str(self.wt), 'add', '.')
        self.d.git('-C', str(self.wt), 'commit', '-m', 'result')
        self.head = self.d.git('rev-parse', self.branch)
        self.d.git('push', 'origin', self.branch)
        self.d.git('update-ref', 'refs/pull/13/head', self.head)
        self.d.git('push', 'origin', 'refs/pull/13/head')
        self.prfile = self.root / 'pr.json'
        self.prfile.write_text(json.dumps(dict(
            number=13, url='https://github.com/o/r/pull/13', state='OPEN',
            headRefName=self.branch, headRefOid=self.head, baseRefName='main', baseRefOid=self.base,
            body='Complete claim. Evidence: command exited 0.\n\nBaseline and final status: empty.'
        )))
        self.prcomments = self.root / 'pr-comments.json'
        self.prcomments.write_text('[]')
        self.checks = self.root / 'checks.json'
        self.checks.write_text(json.dumps([dict(name='test', bucket='pass', state='SUCCESS')]))
        self.env.update(PR_COMMENTS=str(self.prcomments), CHECKS=str(self.checks))

        gh = (self.d.bin / 'gh').read_text()
        gh = gh.replace("elif a[:1] == ['api']:", """elif a[:2] == ['pr', 'checks']:
    rows = json.loads(Path(os.environ['CHECKS']).read_text())
    print(json.dumps(rows))
    sys.exit(0 if all(r['bucket'] == 'pass' for r in rows) else 8)
elif a[0] == 'api' and (a[1].endswith('/protection/required_status_checks') or '/issues/13/comments' in a[1] or ('/issues/comments/' in a[1] and int(a[1].rsplit('/', 1)[1]) >= 100)):
    import tempfile
    def write_comments(rows):
        path = Path(os.environ['PR_COMMENTS'])
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as temporary:
            json.dump(rows, temporary)
        Path(temporary.name).replace(path)
    endpoint = a[1]; rows = json.loads(Path(os.environ['PR_COMMENTS']).read_text())
    if endpoint.endswith('/protection/required_status_checks'):
        protection_error = os.environ.get('PROTECTION_ERROR')
        if protection_error:
            print(protection_error, file=sys.stderr); raise SystemExit(1)
        print(json.dumps({'contexts': ['test']}))
    elif '/issues/13/comments' in endpoint:
        if '--input' in a:
            payload = json.loads(Path(a[a.index('--input') + 1]).read_text())
            row = dict(id=len(rows) + 100, body=payload['body'], html_url='https://github.com/o/r/pull/13#issuecomment-' + str(len(rows) + 100))
            rows.append(row); write_comments(rows); print(json.dumps(row))
        else:
            print(json.dumps(rows))
    elif '/issues/comments/' in endpoint:
        cid = int(endpoint.rsplit('/', 1)[1]); row = next(r for r in rows if r['id'] == cid)
        if '--input' in a:
            row['body'] = json.loads(Path(a[a.index('--input') + 1]).read_text())['body']; write_comments(rows)
        print(json.dumps(row))
    else:
        raise SystemExit('unexpected API: ' + endpoint)
elif a[:1] == ['api']:""")
        (self.d.bin / 'gh').write_text(gh)
        self.out = self.root / 'assembly'
        self.verdict = self.root / 'verdict.txt'
        self.write_verdict('codex')
        self.env['VERDICT'] = str(self.verdict)

        self.d.tool('codex', '''import os,sys,time
from pathlib import Path
a = sys.argv[1:]
assert a[a.index('-s') + 1] == 'workspace-write'
Path(a[a.index('-o') + 1]).write_bytes(Path(os.environ['VERDICT']).read_bytes())
''')

    def write_verdict(self, implementation='codex', goal='Yes', floor1='Pass', floor2='Pass', notes='None.'):
        if implementation == 'codex':
            identity = 'Codex, gpt-6.1-sol at xhigh, read-only'
        else:
            identity = 'Antigravity subagent, pro, read-only'
        text = (f'Reviewer: {identity} — reviewed {self.head}\n'
                f'### Goal verdict\n{goal} — Checked the claim against the diff.\n### Floor\n'
                f'1. Evidence-backed completion claim: {floor1} — Evidence checked.\n'
                f'2. Authorization and scope: {floor2} — Scope checked.\n'
                f'Ready to merge: {"Yes" if (goal, floor1, floor2) == ("Yes", "Pass", "Pass") else "No"} — Goal and Floor.\n'
                f'### Notes\n{notes}\nPost this verdict whole on the PR before acting on it.\n')
        self.verdict.write_text(text)
        return text

    def invoke(self, action, *args):
        implementations = [args[i + 1] for i, arg in enumerate(args) if arg == '--implementation']
        impl = implementations[-1] if implementations else 'codex'
        if action == 'start' and impl == 'codex' and '--wait' not in args:
            args = (*args, '--wait')
        return subprocess.run(
            [sys.executable, str(self.script), action, '13', '--issue', '12', '--project', str(self.project), *args],
            env=self.env, text=True, capture_output=True
        )

    def call(self, action, *args, ok=True):
        result = self.invoke(action, *args)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def assemble(self, *args, ok=True):
        return self.call('assemble', '--architecture-level', 'no', '--output', str(self.out), *args, ok=ok)

    def test_assemble_and_start_across_implementations(self):
        # 1. Codex --wait
        self.write_verdict('codex')
        start_codex = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                                '--implementation', 'codex', '--wait')
        self.assertEqual(start_codex['publication']['status'], 'returned')
        self.assertEqual(start_codex['publication']['outcome']['valid'], True)
        self.assertEqual(start_codex['publication']['outcome']['goal'], 'Yes')

        # 2. Antigravity subagent (agy) native
        # Clean pr comments for fresh round
        self.prcomments.write_text('[]')
        self.write_verdict('agy')
        start_agy = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                              '--implementation', 'agy')
        self.assertEqual(start_agy['run']['status'], 'awaiting-agent-tool')
        attempt_id = start_agy['attempt']

        # Publish native verdict
        published_agy = self.call('publish', '--attempt', str(attempt_id), '--verdict', str(self.verdict))
        self.assertEqual(published_agy['status'], 'returned')
        self.assertEqual(published_agy['outcome']['valid'], True)

    def test_green_head_check_admission(self):
        # Red checks fail start
        self.checks.write_text(json.dumps([dict(name='test', bucket='fail', state='FAILURE')]))
        err = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                        '--implementation', 'codex', '--wait', ok=False)
        self.assertIn('PR checks red, pending, skipped, or unreported', err)

        # Green checks succeed
        self.checks.write_text(json.dumps([dict(name='test', bucket='pass', state='SUCCESS')]))
        start = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                          '--implementation', 'codex', '--wait')
        self.assertEqual(start['publication']['status'], 'returned')

    def test_verdict_shape_and_parsing(self):
        sys.path.insert(0, str(SOURCE / 'scripts'))
        import review_packet
        # Valid canonical verdict
        valid = canonical_verdict(self.head)
        self.assertIsNone(review_packet.verdict_shape(valid, self.head))

        # Missing Floor
        missing_floor = valid.replace('### Floor\n', '')
        self.assertIsNotNone(review_packet.verdict_shape(missing_floor, self.head))

        # Ground missing
        groundless = valid.replace('Ready to merge: Yes — decided only by the Goal verdict and these two Floor checks.',
                                   'Ready to merge: Yes')
        self.assertIsNotNone(review_packet.verdict_shape(groundless, self.head))

    def test_round_accounting_and_rule_continue_and_merge_as_is(self):
        # Round 1 with Goal No
        self.write_verdict('codex', goal='No', floor1='Pass', floor2='Pass')
        start = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                          '--implementation', 'codex', '--wait')
        self.assertEqual(start['round'], 1)
        self.assertEqual(start['publication']['outcome']['goal'], 'No')

        # Rule continue for round 2
        ruled = self.call('rule', '--decision', 'continue', '--reason', 'Fixing the goal gap.')
        self.assertEqual(ruled['decision'], 'continue')

        # Start round 2 requires --reason
        self.write_verdict('codex', goal='Yes', floor1='Pass', floor2='Pass')
        start2 = self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                           '--implementation', 'codex', '--wait', '--reason', 'Goal gap fixed.')
        self.assertEqual(start2['round'], 2)

    def test_floor_2_boundary_restoration_ruling(self):
        # Round 1 with Floor 2 Fail
        self.write_verdict('codex', goal='No', floor1='Pass', floor2='Fail')
        self.call('start', '--architecture-level', 'no', '--output', str(self.out),
                  '--implementation', 'codex', '--wait')

        # Ruling continue records boundary restoration
        ruled = self.call('rule', '--decision', 'continue', '--reason', 'Scope boundary restored to bounds.')
        self.assertEqual(ruled['decision'], 'continue')
        self.assertEqual(ruled['boundary_restoration'], 'Scope boundary restored to bounds.')

        # Merge-as-is cannot waive Floor 2
        err = self.call('rule', '--decision', 'merge-as-is', '--reason', 'Attempting waive', ok=False)
        self.assertIn('Floor check 2 failed', err)

    def test_fail_reserved_attempt(self):
        # Reserve attempt without dispatching
        assembled = self.assemble()
        record = dict(kind='attempt', status='reserved', round=1, **assembled)
        body = ('## Review attempt — round 1\n\n<!-- devstandard-review-v1 -->\n```json\n'
                + json.dumps(record, indent=2) + '\n```\n')
        self.prcomments.write_text(json.dumps([dict(id=100, body=body)]))

        failed = self.call('fail', '--attempt', '100', '--reason', 'Reservation aborted by operator.')
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['error'], 'Reservation aborted by operator.')

    def test_bare_plugin_json_version_bump_detection(self):
        sys.path.insert(0, str(SOURCE / 'scripts'))
        import review_packet
        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.0'}, indent=2) + '\n')
        self.d.git('add', 'plugin.json')
        self.d.git('commit', '-m', 'v1.0.0')
        base_sha = self.d.git('rev-parse', 'HEAD')

        (self.project / 'plugin.json').write_text(json.dumps({'name': 'devstandard', 'version': '1.0.1'}, indent=2) + '\n')
        self.d.git('add', 'plugin.json')
        self.d.git('commit', '-m', 'bump')
        head_sha = self.d.git('rev-parse', 'HEAD')

        # Test version_only and manifest_bump
        self.assertTrue(review_packet.version_only(self.project, base_sha, head_sha))
        self.assertEqual(review_packet.manifest_bump(self.project, base_sha, head_sha, 'plugin.json'),
                         ['1.0.0', '1.0.1'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
