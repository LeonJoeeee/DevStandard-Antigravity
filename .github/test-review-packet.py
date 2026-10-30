#!/usr/bin/env python3
"""Stateless review assembly/publication integration: real git and dispatcher, mock GitHub/executor I/O."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('dispatch_tests', Path(__file__).with_name('test-dispatch.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
SOURCE = fixtures.SOURCE

sys.path.insert(0, str(SOURCE / 'scripts'))
import review_packet


CANONICAL_APPROVE = """Reviewer: Probe — reviewed {head}
### Verdict
Approve — the PR accomplishes the issue's goal within its bounds and done-check.

### Blocking
None.

### Notes
- Optional follow-up note with no merge block.

Post this verdict whole on the PR before acting on it.
"""

CANONICAL_REQUEST_CHANGES = """Reviewer: Probe — reviewed {head}
### Verdict
Request changes — blocking edge case in scripts/guard.

### Blocking
1. `scripts/guard`: missing empty-tree check on replay (`git diff` line 42).
2. [Needs human decision] Public CLI flag rename affects downstream callers.

### Notes
None.

Post this verdict whole on the PR before acting on it.
"""

LEGACY_VERDICT_TEMPLATE = """Reviewer: Probe, read-only — reviewed {head}
### Goal verdict
{goal} — Checked the claim against the diff.
### Floor
1. Evidence-backed completion claim: {gate1} — Evidence checked.
2. Authorization and scope: {gate2} — Scope checked.
Ready to merge: {ready} — Decided by Goal and gates.
### Notes
None.
Post this verdict whole on the PR before acting on it.
"""


class ContractTest(unittest.TestCase):
    def test_reviewer_contract_is_direct_concise_and_has_clean_slots(self):
        source = (SOURCE / 'reference/reviewer.md').read_text()
        self.assertFalse(source.lstrip().startswith('```'),
                         'reference/reviewer.md must not be wrapped in an outer fence')
        lines = source.splitlines()
        self.assertTrue(40 <= len(lines) <= 150, f'unexpected line count: {len(lines)}')
        self.assertEqual(source.count('{CI_CONFIGURATION_PATHS}'), 1)
        slots = set(review_packet.SLOT.findall(source))
        self.assertEqual(slots, {
            'REVIEWER_IDENTITY',
            'ISSUE_GOAL_STATEMENT',
            'ISSUE_BOUNDS',
            'ISSUE_DONE_CHECK',
            'COMPLETE_PR_DESCRIPTION',
            'REVIEW_BASE_SHA',
            'HEAD_SHA',
            'CI_CONFIGURATION_PATHS',
            'CI_FALLBACK_COMMENT_OR_NONE',
        })
        for heading in ('### Verdict', '### Blocking', '### Notes'):
            self.assertIn(heading, source)


class VerdictParserTest(unittest.TestCase):
    def test_canonical_verdict_shapes_and_defects(self):
        head = 'a' * 40
        approve = CANONICAL_APPROVE.format(head=head)
        self.assertIsNone(review_packet.verdict_shape(approve, head, identity='Probe'))
        parsed_approve = review_packet.parse_verdict(approve, head, identity='Probe')
        self.assertEqual(parsed_approve['verdict'], 'Approve')
        self.assertFalse(parsed_approve['legacy'])

        changes = CANONICAL_REQUEST_CHANGES.format(head=head)
        self.assertIsNone(review_packet.verdict_shape(changes, head, identity='Probe'))
        parsed_changes = review_packet.parse_verdict(changes, head, identity='Probe')
        self.assertEqual(parsed_changes['verdict'], 'Request changes')

        # Emphasis and optional closing line / empty Notes remain admitted
        emphasized = approve.replace('### Verdict\nApprove —', '### **Verdict**\n**Approve** —')
        emphasized = emphasized.replace('Post this verdict whole on the PR before acting on it.\n', '')
        self.assertIsNone(review_packet.verdict_shape(emphasized, head, identity='Probe'))

        # Malformed shapes are rejected
        bad_cases = {
            'approve with blocking item': approve.replace('### Blocking\nNone.', '### Blocking\n1. Broken check.'),
            'request changes with None blocking': changes.replace(
                '1. `scripts/guard`: missing empty-tree check on replay (`git diff` line 42).\n'
                '2. [Needs human decision] Public CLI flag rename affects downstream callers.',
                'None.',
            ),
            'missing Blocking section': approve.replace('### Blocking\nNone.\n\n', ''),
            'missing Notes section': approve.replace('### Notes\n- Optional follow-up note with no merge block.\n\n', ''),
            'ungrounded Approve': approve.replace(
                "Approve — the PR accomplishes the issue's goal within its bounds and done-check.",
                'Approve',
            ),
            'wrong head': CANONICAL_APPROVE.format(head='b' * 40),
            'wrong identity': approve.replace('Reviewer: Probe —', 'Reviewer: Someone Else —'),
        }
        for label, candidate in bad_cases.items():
            with self.subTest(case=label):
                self.assertIsNotNone(review_packet.verdict_shape(candidate, head, identity='Probe'))

    def test_legacy_verdict_rejected_by_default_and_accepted_when_allowed(self):
        head = 'c' * 40
        legacy_ok = LEGACY_VERDICT_TEMPLATE.format(head=head, goal='Yes', gate1='Pass', gate2='Pass', ready='Yes')
        self.assertIsNotNone(review_packet.verdict_shape(legacy_ok, head, allow_legacy=False))
        self.assertIsNone(review_packet.verdict_shape(legacy_ok, head, allow_legacy=True))
        parsed = review_packet.parse_verdict(legacy_ok, head, allow_legacy=True)
        self.assertEqual(parsed['verdict'], 'Approve')
        self.assertTrue(parsed['legacy'])
        self.assertTrue(parsed['legacy_floor_ok'])

        legacy_no = LEGACY_VERDICT_TEMPLATE.format(head=head, goal='No', gate1='Pass', gate2='Pass', ready='No')
        parsed_no = review_packet.parse_verdict(legacy_no, head, allow_legacy=True)
        self.assertTrue(parsed_no['valid'])
        self.assertEqual(parsed_no['verdict'], 'Request changes')
        self.assertTrue(parsed_no['legacy_floor_ok'])

        legacy_gate_fail = LEGACY_VERDICT_TEMPLATE.format(
            head=head, goal='No', gate1='Pass', gate2='Fail', ready='No'
        )
        parsed_fail = review_packet.parse_verdict(legacy_gate_fail, head, allow_legacy=True)
        self.assertTrue(parsed_fail['valid'])
        self.assertEqual(parsed_fail['verdict'], 'Request changes')
        self.assertFalse(parsed_fail['legacy_floor_ok'])


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

        self.d.tool('codex', '''import os,sys
from pathlib import Path
a = sys.argv[1:]
if a[:2] == ['mcp', 'list']:
    sys.stdout.write('[]')
    raise SystemExit(0)
assert a[a.index('-s') + 1] == 'workspace-write'
Path(a[a.index('-o') + 1]).write_bytes(Path(os.environ['VERDICT']).read_bytes())
raise SystemExit(int(os.environ.get('FAKE_EXIT', '0')))
''')

    def write_verdict(self, implementation='codex', decision='Approve', blocking=None, notes='None.', head=None):
        head = head or self.head
        identity = 'Codex, gpt-6.1-sol at high' if implementation == 'codex' else 'Antigravity subagent, inherit'
        if blocking is None:
            blocking = 'None.' if decision == 'Approve' else '1. `result.txt`: missing required validation.'
        text = (f'Reviewer: {identity} — reviewed {head}\n'
                f'### Verdict\n{decision} — Checked the PR against the issue and diff.\n\n'
                f'### Blocking\n{blocking}\n\n'
                f'### Notes\n{notes}\n\n'
                'Post this verdict whole on the PR before acting on it.\n')
        self.verdict.write_text(text)
        return text

    def invoke(self, action, *args):
        implementations = [args[i + 1] for i, arg in enumerate(args) if arg == '--implementation']
        impl = implementations[-1] if implementations else ('agy' if action == 'publish' else 'codex')
        if action == 'start' and impl == 'codex' and '--wait' not in args:
            args = (*args, '--wait')
        cmd = [sys.executable, str(self.script), action, '13', '--project', str(self.project), *args]
        if action in ('assemble', 'start') and '--issue' not in args:
            cmd += ['--issue', '12']
        return subprocess.run(cmd, env=self.env, text=True, capture_output=True)

    def call(self, action, *args, ok=True):
        result = self.invoke(action, *args)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def test_stateless_codex_and_agy_start_and_publish(self):
        # 1. Codex --wait (without --architecture-level): posts exactly one ## Code Review comment
        self.write_verdict('codex', decision='Approve')
        started_codex = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        self.assertEqual(started_codex['round'], 1)
        self.assertEqual(started_codex['outcome'], {'valid': True, 'verdict': 'Approve'})
        comments = json.loads(self.prcomments.read_text())
        self.assertEqual(len(comments), 1)
        self.assertTrue(comments[0]['body'].startswith('## Code Review — round 1\n'))
        self.assertTrue(self.call('status')['accepted'])

        # 2. Antigravity native (agy): posts 0 pre-flight PR comments on start, publishes 1 on publish
        self.prcomments.write_text('[]')
        agy_out = self.root / 'assembly-agy'
        self.write_verdict('agy', decision='Approve')
        started_agy = self.call('start', '--output', str(agy_out), '--implementation', 'agy')
        self.assertEqual(started_agy['run']['status'], 'awaiting-agent-tool')
        self.assertTrue(Path(started_agy['attempt_file']).is_file())
        self.assertEqual(json.loads(self.prcomments.read_text()), [])

        published_agy = self.call('publish', '--output', str(agy_out), '--verdict', str(self.verdict))
        self.assertEqual(published_agy['status'], 'returned')
        self.assertEqual(published_agy['round'], 1)
        self.assertEqual(published_agy['outcome'], {'valid': True, 'verdict': 'Approve'})
        comments = json.loads(self.prcomments.read_text())
        self.assertEqual(len(comments), 1)
        self.assertTrue(comments[0]['body'].startswith('## Code Review — round 1\n'))

    def test_green_head_check_admission(self):
        self.checks.write_text(json.dumps([dict(name='test', bucket='fail', state='FAILURE')]))
        err = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait', ok=False)
        self.assertIn('PR checks red, pending, skipped, or unreported', err)
        self.assertEqual(json.loads(self.prcomments.read_text()), [])

        self.checks.write_text(json.dumps([dict(name='test', bucket='pass', state='SUCCESS')]))
        started = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        self.assertEqual(started['status'], 'returned')

    def test_cli_failure_and_malformed_verdict_post_no_pr_spam_and_fail_is_retired(self):
        # Retired fail subcommand is rejected
        err_fail = self.call('fail', ok=False)
        self.assertIn('invalid choice', err_fail)

        # CLI nonzero exit fails on stderr with 0 PR comments
        self.env['FAKE_EXIT'] = '7'
        err_exit = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait', ok=False)
        self.assertIn('reviewer CLI failed (exit 7)', err_exit)
        self.assertEqual(json.loads(self.prcomments.read_text()), [])

        # Malformed verdict fails on stderr with 0 PR comments
        self.env['FAKE_EXIT'] = '0'
        self.verdict.write_text('Not a valid structured verdict.\n')
        err_shape = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait', ok=False)
        self.assertIn('invalid reviewer verdict', err_shape)
        self.assertEqual(json.loads(self.prcomments.read_text()), [])

        # Subsequent retry starts cleanly at round 1
        self.write_verdict('codex', decision='Approve')
        recovered = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        self.assertEqual(recovered['round'], 1)
        self.assertEqual(len(json.loads(self.prcomments.read_text())), 1)

    def test_two_round_convergence_warning_and_human_authorized_merge_as_is(self):
        # Round 1: Request changes
        self.write_verdict('codex', decision='Request changes')
        r1 = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        self.assertEqual(r1['round'], 1)
        status1 = self.call('status')
        self.assertFalse(status1['accepted'])
        self.assertNotIn('warning', status1)

        # Push fix commit and run Round 2: Request changes again -> triggers 2-round convergence warning
        (self.wt / 'result.txt').write_text('Result v2\n')
        self.d.git('-C', str(self.wt), 'add', 'result.txt')
        self.d.git('-C', str(self.wt), 'commit', '-m', 'fix attempt')
        self.head = self.d.git('rev-parse', self.branch)
        self.d.git('push', 'origin', self.branch)
        self.d.git('update-ref', 'refs/pull/13/head', self.head)
        self.d.git('push', 'origin', 'refs/pull/13/head', '--force')
        pr_data = json.loads(self.prfile.read_text())
        pr_data['headRefOid'] = self.head
        self.prfile.write_text(json.dumps(pr_data))

        self.write_verdict('codex', decision='Request changes', head=self.head)
        r2 = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait',
                       '--reason', 'Addressed round 1 blocker.')
        self.assertEqual(r2['round'], 2)
        status_res = self.invoke('status')
        self.assertEqual(status_res.returncode, 0)
        status2 = json.loads(status_res.stdout)
        self.assertFalse(status2['accepted'])
        self.assertIn('2+ review rounds without convergence; escalate to the human if findings are repeating',
                      status2.get('warning', ''))
        self.assertIn('2+ review rounds without convergence', status_res.stderr)

        # merge-as-is without --human-authorization refuses
        err = self.call('rule', '--decision', 'merge-as-is', '--reason', 'Tried without human auth', ok=False)
        self.assertIn('merge-as-is requires --human-authorization', err)

        # merge-as-is with --human-authorization accepts the head
        ruled = self.call('rule', '--decision', 'merge-as-is',
                          '--reason', 'Human accepted documented scope tradeoff.',
                          '--human-authorization', 'Human approved in session turn 4')
        self.assertEqual(ruled['decision'], 'merge-as-is')
        status3 = self.call('status')
        self.assertTrue(status3['accepted'])

    def test_accepted_head_blocks_rereview_on_notes_without_recovery_ruling(self):
        self.write_verdict('codex', decision='Approve', notes='- Optional style nit.')
        self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        err = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait', ok=False)
        self.assertIn('accepted verdict: Notes do not authorize another round', err)

        # Guard-refusal recovery ruling authorizes re-review when needed
        self.call('rule', '--decision', 'continue', '--reason', 'Guard observed transient mismatch',
                  '--guard-refusal', 'guard refused: required CI checks unmet')
        r2 = self.call('start', '--output', str(self.out), '--implementation', 'codex', '--wait')
        self.assertEqual(r2['round'], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
