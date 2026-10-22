#!/usr/bin/env python3
"""Exercise real git and child processes; mock GitHub and executor I/O."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class DispatchTest(unittest.TestCase):
    def assert_role_config(self, args, role):
        import shlex
        import tomllib
        overrides = [args[i + 1] for i, arg in enumerate(args) if arg == '-c']
        parsed = {}
        for override in overrides:
            key, value = override.split('=', 1)
            if key != 'hooks.PreToolUse' and not key.startswith('agents.'):
                continue
            assignment = tomllib.loads('value=' + value)
            self.assertEqual(set(assignment), {'value'})
            parsed[key] = assignment['value']
        self.assertEqual(parsed.get('agents.default_subagent_model'), 'gpt-6.1-sol')
        self.assertEqual(parsed.get('agents.default_subagent_reasoning_effort'), 'high')
        self.assertEqual(parsed['hooks.PreToolUse'], [{
            'matcher': '.*', 'hooks': [{'type': 'command', 'command': shlex.join([
                str(SOURCE / 'hooks/pre-tool-use'), '--role', role]), 'timeout': 30}]}])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dispatch-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.issue = self.root / 'issue.json'
        self.comments = self.root / 'comments.json'
        self.comments.write_text('[]')
        self.issue.write_text(json.dumps(dict(
            number=12, title='A small task', url='https://github.com/o/r/issues/12',
            state='OPEN', body='## Goal\nProduce evidence.\n## Bounds\nOne task only.\n## Done-check\nOutput is captured.'
        )))
        self.env = dict(
            os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
            ISSUE=str(self.issue), COMMENTS=str(self.comments), PR=str(self.root / 'pr.json'),
            TMPDIR=str(self.root), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1'
        )
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        (self.project / '.gitignore').write_text('/.agents/worktrees/\n')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.git('remote', 'add', 'origin', 'https://github.com/o/r.git')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

        self.tool('gh', '''import json,os,sys
from pathlib import Path
a = sys.argv[1:]; c = Path(os.environ['COMMENTS'])
def w(rows):
    t = c.with_name(c.name + '.tmp')
    t.write_text(json.dumps(rows))
    os.replace(t, c)

if a[:2] == ['repo', 'view']:
    print('o/r')
elif a[:1] == ['api']:
    endpoint = a[1]
    if '/issues/comments/' in endpoint:
        rows = json.loads(c.read_text())
        cid = int(endpoint.rsplit('/', 1)[1])
        row = next(r for r in rows if r['id'] == cid)
        if '--input' in a:
            row['body'] = json.loads(Path(a[a.index('--input') + 1]).read_text())['body']
            w(rows)
        print(json.dumps(row))
    elif '/issues/12/comments' in endpoint or '/issues/13/comments' in endpoint:
        assert '--paginate' in a
        rows = json.loads(c.read_text())
        print(json.dumps(rows[:1])); print(json.dumps(rows[1:]))
    elif '/comments' in endpoint:
        print(os.environ.get('REVIEW_COMMENTS', '[]'))
    elif '/compare/' in endpoint:
        print(json.dumps({'behind_by': int(os.environ.get('PR_BEHIND', '0'))}))
    elif '/git/trees/' in endpoint or '/git/blobs/' in endpoint:
        raise SystemExit('policy must be read from the local origin/main ref, not GitHub')
    else:
        print(json.dumps(json.loads(os.environ.get('DEFAULT_CI', '{"default_branch":"main","owner":{"login":"o"},"commit":{"sha":"abc"},"tree":[],"check_runs":[{"name":"test","status":"completed","conclusion":"success"}],"statuses":[]}'))))
elif a[:2] == ['issue', 'view']:
    num = a[2] if len(a) > 2 else '12'
    d = json.loads(Path(os.environ['ISSUE']).read_text())
    d['number'] = int(num)
    d['url'] = f'https://github.com/o/r/issues/{num}'
    d['comments'] = [dict(row, id='IC_fixture_' + str(i + 1), url=f'https://github.com/o/r/issues/{num}#issuecomment-' + str(i + 1))
                     for i, row in enumerate(json.loads(c.read_text()))]
    print(json.dumps(d))
elif a[:2] == ['issue', 'comment']:
    body = Path(a[a.index('--body-file') + 1]).read_text()
    if '```json\\n' in body:
        record = json.loads(body.split('```json\\n')[1].split('\\n```')[0])
        if record.get('kind') == 'run' and (os.environ.get('REJECT_RUN_PUBLICATION')
            or (record.get('status') == 'returned' and os.environ.get('REJECT_COMPLETION_PUBLICATION'))):
            raise SystemExit('fixture publication failed')
    rows = json.loads(c.read_text())
    rows.append({'id': len(rows) + 1, 'body': body})
    w(rows)
    print('https://github.com/o/r/issues/12#issuecomment-' + str(len(rows)))
elif a[:2] == ['pr', 'view']:
    data = json.loads(Path(os.environ['PR']).read_text())
    rows = data if isinstance(data, list) else [data]
    print(json.dumps(next(p for p in rows if p['number'] == int(a[2]))))
elif a[:2] == ['pr', 'list']:
    p = Path(os.environ['PR'])
    rows = json.loads(p.read_text()) if p.exists() else []
    rows = rows if isinstance(rows, list) else [rows]
    if '--head' in a:
        rows = [row for row in rows if row['headRefName'] == a[a.index('--head') + 1]]
    if '--state' in a and a[a.index('--state') + 1] != 'all':
        rows = [row for row in rows if row['state'] == a[a.index('--state') + 1].upper()]
    print(json.dumps(rows))
else:
    raise SystemExit('unexpected gh: ' + repr(a))
''')

        self.tool('codex', '''import json,os,subprocess,sys,time
from pathlib import Path
a = sys.argv[1:]
if a[:2] == ['mcp', 'list']:
    sys.stdout.write(os.environ.get('FAKE_MCP_LIST', '[]'))
    raise SystemExit(int(os.environ.get('FAKE_MCP_EXIT', '0')))
out = Path(a[a.index('-o') + 1])
if os.environ.get('FAKE_COMMITS'):
    wt = Path(a[a.index('-C') + 1])
    for n in range(2):
        (wt / 'result.txt').write_text('worker result ' + str(n))
        for cmd in [('add', 'result.txt'), ('commit', '-m', 'worker step ' + str(n))]:
            subprocess.run(['git', '-C', str(wt), *cmd], check=True)
probe = {}
if os.environ.get('FAKE_REVIEW_WRITE'):
    wt = Path.cwd()
    def git(*args): return subprocess.check_output(['git', *args], text=True).strip()
    probe = dict(cwd=str(wt), head=git('rev-parse', 'HEAD'),
                 git_dir=git('rev-parse', '--absolute-git-dir'),
                 origin=git('remote', 'get-url', 'origin'))
out.write_text(json.dumps({'args': a, 'sid': os.getsid(0), 'pid': os.getpid(), 'ppid': os.getppid(),
                           'stdin': sys.stdin.read(), 'role': os.environ.get('DEVSTANDARD_ROLE'), **probe}))
hold = os.environ.get('FAKE_HOLD'); deadline = time.monotonic() + 20
while hold and not Path(hold).exists() and time.monotonic() < deadline:
    time.sleep(.01)
raise SystemExit(int(os.environ.get('FAKE_EXIT', '0')))
''')

        self.script = SOURCE / 'scripts/dispatch'

    def tool(self, name, body):
        p = self.bin / name
        p.write_text('#!/usr/bin/env python3\n' + body)
        p.chmod(0o755)

    def git(self, *args):
        return subprocess.check_output(
            ['git', '-C', str(self.project), *args],
            env=self.env, stderr=subprocess.DEVNULL, text=True
        ).strip()

    def call(self, *args, issue='12', ok=True, exit_code=0):
        implementation = [args[i + 1] for i, arg in enumerate(args) if arg == '--implementation']
        native = implementation and implementation[-1] == 'agy'
        if '--purpose' in args and not native and '--wait' not in args:
            args = (*args, '--wait')
        r = subprocess.run(
            [sys.executable, str(self.script), str(issue), *args, '--project', str(self.project)],
            env=self.env, text=True, capture_output=True
        )
        if ok:
            self.assertEqual(r.returncode, exit_code, r.stdout + r.stderr)
            return json.loads(r.stdout)
        self.assertNotEqual(r.returncode, 0)
        return r.stderr

    def start(self, *args, exit_code=0):
        named = () if '--implementation' in args else ('--implementation', 'codex')
        return self.call('--purpose', 'worker', '--base', 'origin/main', *named, *args, exit_code=exit_code)

    def lane_records(self):
        return [json.loads(row['body'].split('```json\n')[1].split('\n```')[0])
                for row in json.loads(self.comments.read_text())]

    def hand_made_lane(self, branch='feat/hand-made', dirname='hand-made'):
        wt = self.root / dirname
        self.git('worktree', 'add', '-b', branch, str(wt), 'origin/main')
        return branch, wt

    def assert_returned(self, run):
        self.assertIn('executor_exit', run)

    def finish(self, run):
        self.assert_returned(run)
        return json.loads(Path(run['output']).read_text())

    def review_packet(self, base=None, head=None, convention=None, identity='{REVIEWER_IDENTITY}'):
        import re
        base = base or self.git('rev-parse', 'origin/main')
        head = head or base
        template = re.search(r'\n```\n(.*?)\n```\n',
                             (SOURCE / 'reference/code-review-prompt.md').read_text(), re.S).group(1)
        predicate = re.search(r'<!-- BEGIN IN-REPO-WRITES PREDICATE -->.*?<!-- END IN-REPO-WRITES PREDICATE \(\d+ payload lines\) -->',
                             (SOURCE / 'reference/in-repo-writes.md').read_text(), re.S).group()
        slots = dict(
            ISSUE_GOAL_STATEMENT='Produce evidence.', ISSUE_BOUNDS='One task.',
            ISSUE_DONE_CHECK='Output captured.', ARCHITECTURE_LEVEL_FLAG='NO',
            COMPLETE_PR_DESCRIPTION='Complete report.', REVIEW_BASE_SHA=base, HEAD_SHA=head,
            CONVENTION_BASE_SHA=convention or base, ACCEPTED_SPEC_BLOB_SHA='NONE',
            CI_CONFIGURATION_PATHS='NONE', CI_FALLBACK_COMMENT_OR_NONE='NONE',
            IN_REPO_WRITES_PREDICATE=predicate, REVIEWER_IDENTITY=identity
        )
        packet = self.root / 'review.txt'
        packet.write_text(json.dumps(dict(format='devstandard-review-packet-v1', template=template, slots=slots)))
        return packet

    def test_default_worktree_creation_under_agents_worktrees(self):
        run = self.start('--implementation', 'codex')
        expected_wt = self.project / '.agents/worktrees/12-a-small-task'
        self.assertEqual(run['worktree'], str(expected_wt))
        self.assertEqual(run['branch'], 'task/12-a-small-task')
        self.assertTrue(expected_wt.is_dir())
        self.assertEqual(self.git('-C', str(expected_wt), 'rev-parse', '--abbrev-ref', 'HEAD'), 'task/12-a-small-task')

    def test_codex_worker_lane_creation_and_flags(self):
        run = self.start('--implementation', 'codex')
        data = self.finish(run)
        args = data['args']
        self.assertIn('-s', args)
        self.assertEqual(args[args.index('-s') + 1], 'workspace-write')
        self.assertIn('--add-dir', args)
        self.assert_role_config(args, 'worker')
        brief = Path(run['brief']).read_text()
        self.assertIn('## Worker mechanics', brief)
        self.assertIn('A Codex CLI worker runs inside the OS sandbox', brief)
        self.assertIn('# Task packet', brief)
        self.assertIn('Helpers: your own subagents go through Codex', brief)

    def test_codex_reviewer_disposable_checkout(self):
        self.start('--implementation', 'codex')
        packet = self.review_packet()
        run = self.call('--purpose', 'reviewer', '--implementation', 'codex', '--packet', str(packet))
        data = self.finish(run)
        self.assertEqual(data['role'], 'reviewer')
        self.assertIn('review_checkout', run)
        # Checkout directory is cleaned up upon return
        self.assertFalse(Path(run['review_checkout']).exists())

    def test_agy_native_worker_prepares_agent_spawn(self):
        run = self.call('--purpose', 'worker', '--base', 'origin/main', '--implementation', 'agy')
        self.assertEqual(run['status'], 'awaiting-agent-tool')
        self.assertIn('instruction', run)
        instruction = json.loads(Path(run['instruction']).read_text())
        self.assertEqual(instruction['subagent_type'], 'devstandard:worker')
        self.assertEqual(instruction['model'], 'inherit')
        self.assertIsNone(instruction['effort'])
        self.assertIn('## Worker mechanics', instruction['prompt'])
        self.assertIn('Native Antigravity subagent', instruction['prompt'])
        self.assertIn('# Task packet', instruction['prompt'])
        self.assert_antigravity_helpers(Path(run['brief']).read_text())

    def test_agy_native_reviewer_prepares_agent_spawn(self):
        self.call('--purpose', 'worker', '--base', 'origin/main', '--implementation', 'agy')
        packet = self.review_packet()
        run = self.call('--purpose', 'reviewer', '--implementation', 'agy', '--packet', str(packet))
        self.assertEqual(run['status'], 'awaiting-agent-tool')
        instruction = json.loads(Path(run['instruction']).read_text())
        self.assertEqual(instruction['subagent_type'], 'devstandard:reviewer')
        self.assertEqual(instruction['model'], 'inherit')
        self.assertIsNone(instruction['effort'])
        self.assertIn('Read', instruction['prompt'])
        self.assertIn('brief.txt', instruction['prompt'])
        self.assert_antigravity_helpers(Path(run['brief']).read_text())

    def assert_antigravity_helpers(self, brief):
        packet = brief.split('# Task packet', 1)[1]
        self.assertIn('Helpers:', packet)
        helpers = packet.split('Helpers:', 1)[1]
        self.assertIn('Antigravity', helpers)
        self.assertIn('Its conclusion directly decides a merge or a design', helpers)
        self.assertIn('**The default — everything else**: `inherit`', helpers)
        self.assertIn('`flash`', helpers)

    def test_agy_reviewer_pins_modified_binary_blob(self):
        (self.project / 'image.png').write_bytes(b'\x89PNG\x00\xffold')
        self.git('add', 'image.png')
        self.git('commit', '-m', 'binary base')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        base = self.git('rev-parse', 'HEAD')
        lane = self.start('--implementation', 'agy')
        wt = Path(lane['worktree'])
        (wt / 'image.png').write_bytes(b'\x89PNG\x00\xffnew')
        self.git('-C', str(wt), 'add', 'image.png')
        self.git('-C', str(wt), 'commit', '-m', 'binary change')
        head = self.git('rev-parse', lane['branch'])
        packet = self.review_packet(base=base, head=head)
        run = self.call('--purpose', 'reviewer', '--implementation', 'agy', '--packet', str(packet))
        brief = Path(run['brief']).read_text()
        evidence = json.JSONDecoder().raw_decode(brief.split('## Pinned Git evidence\n', 1)[1])[0]
        blob = next(row for row in evidence if row['command'].endswith(base + ':image.png'))
        self.assertEqual(blob['exit_code'], 0)
        self.assertIn('\ufffdPNG', ''.join(blob['stdout']))
        self.assertIn('old', ''.join(blob['stdout']))

    def test_agy_native_worker_continuation_and_resume(self):
        self.call('--purpose', 'worker', '--base', 'origin/main', '--implementation', 'agy')
        brief = self.root / 'continue.txt'
        brief.write_text('Continuation instructions.')
        continued = self.call('--purpose', 'worker', '--continue', '--implementation', 'agy',
                              '--brief', str(brief), '--resume', 'conv-1234')
        self.assertEqual(continued['status'], 'awaiting-agent-tool')
        instruction = json.loads(Path(continued['instruction']).read_text())
        self.assertEqual(instruction['resume'], 'conv-1234')

    def test_adopt_records_lane_and_checks_validity(self):
        # Adopting main checkout fails
        err = self.call('--adopt', '--branch', 'main', '--worktree', str(self.project), '--base', 'origin/main', ok=False)
        self.assertIn('linked worktree', err)

        branch, wt = self.hand_made_lane()
        lane = self.call('--adopt', '--branch', branch, '--worktree', str(wt), '--base', 'origin/main')
        self.assertEqual(lane['kind'], 'lane')
        self.assertEqual(lane['status'], 'adopted')
        self.assertEqual(lane['branch'], branch)
        self.assertEqual(lane['worktree'], str(wt))

    def test_cleanup_refuses_dirty_worktree(self):
        run = self.start('--implementation', 'codex')
        wt = Path(run['worktree'])
        (wt / 'dirty.txt').write_text('uncommitted')
        head = self.git('rev-parse', run['branch'])
        pr = dict(number=12, state='MERGED', mergedAt='2026-10-21T00:00:00Z',
                  headRefOid=head, headRefName=run['branch'], baseRefName='main',
                  url='https://github.com/o/r/pull/12')
        (self.root / 'pr.json').write_text(json.dumps(pr))

        err = self.call('--cleanup', '--pr', '12', ok=False)
        self.assertIn('dirty worktree', err)

    def test_adopt_refuses_other_checked_out_branch(self):
        branch, wt = self.hand_made_lane()
        self.git('-C', str(wt), 'checkout', '-b', 'other')
        err = self.call('--adopt', '--branch', branch, '--worktree', str(wt),
                        '--base', 'origin/main', ok=False)
        self.assertIn('branch', err)
        self.assertEqual(self.lane_records(), [])

    def test_cleanup_refuses_switched_branch_and_preserves_unpublished_commits(self):
        lane = self.start('--implementation', 'agy')
        wt = Path(lane['worktree'])
        merged = self.git('rev-parse', lane['branch'])
        (wt / 'unpublished.txt').write_text('Keep this commit.')
        self.git('-C', str(wt), 'add', '.')
        self.git('-C', str(wt), 'commit', '-m', 'unpublished')
        unpublished = self.git('rev-parse', lane['branch'])
        self.git('-C', str(wt), 'checkout', '-b', 'other', merged)
        pr = dict(number=12, state='MERGED', mergedAt='2026-10-21T00:00:00Z',
                  headRefOid=merged, headRefName=lane['branch'], baseRefName='main',
                  url='https://github.com/o/r/pull/12')
        (self.root / 'pr.json').write_text(json.dumps(pr))
        for flags in (('--pr', '12'), ('--discard',)):
            with self.subTest(flags=flags):
                err = self.call('--cleanup', *flags, ok=False)
                self.assertIn('branch', err)
                self.assertTrue(wt.is_dir())
                self.assertEqual(self.git('rev-parse', lane['branch']), unpublished)

    def test_cleanup_verifies_merged_pr_and_cleans(self):
        run = self.start('--implementation', 'codex')
        wt = Path(run['worktree'])
        head = self.git('rev-parse', run['branch'])
        pr = dict(number=12, state='MERGED', mergedAt='2026-10-21T00:00:00Z',
                  headRefOid=head, headRefName=run['branch'], baseRefName='main',
                  url='https://github.com/o/r/pull/12')

        # Unmerged refuses
        pr_open = dict(pr, state='OPEN', mergedAt=None)
        (self.root / 'pr.json').write_text(json.dumps(pr_open))
        err = self.call('--cleanup', '--pr', '12', ok=False)
        self.assertIn('merged', err)

        # Merged succeeds
        (self.root / 'pr.json').write_text(json.dumps(pr))
        cleanup = self.call('--cleanup', '--pr', '12')
        self.assertEqual(cleanup['status'], 'cleaned')
        self.assertFalse(wt.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
