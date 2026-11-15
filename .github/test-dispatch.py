#!/usr/bin/env python3
"""Exercise real git and child processes; mock GitHub and executor I/O."""
import json
import os
from pathlib import Path
import importlib.machinery
import importlib.util
import io
from contextlib import redirect_stdout
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

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
        self.assertEqual(parsed.get('agents.default_subagent_model'), 'gpt-6.1-terra')
        self.assertEqual(parsed.get('agents.default_subagent_reasoning_effort'), 'high')
        self.assertEqual(args[args.index('-m') + 1], 'gpt-6.1-sol')
        self.assertIn('model_reasoning_effort=' + {'worker': 'xhigh', 'reviewer': 'high'}[role], overrides)
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
            number=12, title='A small task', html_url='https://github.com/o/r/issues/12',
            state='open', body='## Goal\nProduce evidence.\n## Bounds\nOne task only.\n## Done-check\nOutput is captured.'
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
from urllib.parse import urlsplit, parse_qs
a = sys.argv[1:]; c = Path(os.environ['COMMENTS'])
if a[:1] != ['api']:
    raise SystemExit('only gh api is supported: ' + repr(a))
def w(rows):
    t = c.with_name(c.name + '.tmp')
    t.write_text(json.dumps(rows))
    os.replace(t, c)

if a[:1] == ['api']:
    endpoint = a[1]
    route = urlsplit(endpoint).path
    query = parse_qs(urlsplit(endpoint).query)
    if '/issues/comments/' in endpoint:
        rows = json.loads(c.read_text())
        cid = int(endpoint.rsplit('/', 1)[1])
        row = next(r for r in rows if r['id'] == cid)
        if '--input' in a:
            row['body'] = json.loads(Path(a[a.index('--input') + 1]).read_text())['body']
            w(rows)
        print(json.dumps(row))
    elif '/issues/12/comments' in endpoint or '/issues/13/comments' in endpoint:
        rows = json.loads(c.read_text())
        if '--input' in a:
            assert a[a.index('--method') + 1] == 'POST'
            body = json.loads(Path(a[a.index('--input') + 1]).read_text())['body']
            if '```json\\n' in body:
                record = json.loads(body.split('```json\\n')[1].split('\\n```')[0])
                if record.get('kind') == 'run' and (os.environ.get('REJECT_RUN_PUBLICATION')
                    or (record.get('status') == 'returned' and os.environ.get('REJECT_COMPLETION_PUBLICATION'))):
                    raise SystemExit('fixture publication failed')
            row = dict(id=len(rows) + 1, body=body,
                       html_url='https://github.com/o/r/issues/12#issuecomment-' + str(len(rows) + 1))
            rows.append(row); w(rows); print(json.dumps(row))
        else:
            assert '--paginate' in a
            print(json.dumps(rows[:1])); print(json.dumps(rows[1:]))
    elif route.startswith('repos/o/r/issues/'):
        num = int(route.rsplit('/', 1)[1])
        d = json.loads(Path(os.environ['ISSUE']).read_text())
        d.update(number=num, html_url=f'https://github.com/o/r/issues/{num}')
        print(json.dumps(d))
    elif route == 'repos/o/r/pulls' or route.startswith('repos/o/r/pulls/'):
        p = Path(os.environ['PR'])
        data = json.loads(p.read_text()) if p.exists() else []
        rows = data if isinstance(data, list) else [data]
        if route == 'repos/o/r/pulls':
            assert '--paginate' in a
            head = query['head'][0].split(':', 1)[1]
            rows = [row for row in rows if row['head']['ref'] == head]
            assert query['state'] == ['all']
            print(json.dumps(rows[:1])); print(json.dumps(rows[1:]))
        else:
            print(json.dumps(next(row for row in rows if row['number'] == int(route.rsplit('/', 1)[1]))))
    elif '/comments' in endpoint:
        print(os.environ.get('REVIEW_COMMENTS', '[]'))
    elif '/compare/' in endpoint:
        print(json.dumps({'behind_by': int(os.environ.get('PR_BEHIND', '0'))}))
    elif '/git/trees/' in endpoint or '/git/blobs/' in endpoint:
        raise SystemExit('policy must be read from the local origin/main ref, not GitHub')
    else:
        print(json.dumps(json.loads(os.environ.get('DEFAULT_CI', '{"default_branch":"main","owner":{"login":"o"},"commit":{"sha":"abc"},"tree":[],"check_runs":[{"name":"test","status":"completed","conclusion":"success"}],"statuses":[]}'))))
else:
    raise SystemExit('unexpected gh: ' + repr(a))
''')

        self.tool('codex', '''import json,os,subprocess,sys,time
from pathlib import Path
a = sys.argv[1:]
if a[:1] == ['mcp'] and os.environ.get('MCP_PROBE'):
    with Path(os.environ['MCP_PROBE']).open('a') as stream:
        stream.write(json.dumps(dict(args=a, cwd=str(Path.cwd()))) + '\\n')
if a[:2] == ['mcp', 'list']:
    sys.stdout.write(os.environ.get('FAKE_MCP_LIST', '[]'))
    raise SystemExit(int(os.environ.get('FAKE_MCP_EXIT', '0')))
if a[:2] == ['mcp', 'get']:
    assert a[3] == '--json'
    overrides = a[4:]
    assert len(overrides) % 2 == 0 and overrides
    names = []
    for flag, setting in zip(overrides[::2], overrides[1::2]):
        assert flag == '-c'
        assert setting.startswith('mcp_servers.')
        assert setting.endswith('.default_tools_approval_mode="approve"')
        names.append(setting.split('.')[1])
    assert a[2] in names
    rejected = set(json.loads(os.environ.get('FAKE_MCP_REJECT', '[]')))
    if rejected.intersection(names):
        raise SystemExit('invalid transport')
    print('{}')
    raise SystemExit(0)
out = Path(a[a.index('-o') + 1])
if os.environ.get('FAKE_COMMITS'):
    wt = Path(a[a.index('-C') + 1])
    for n in range(2):
        (wt / 'result.txt').write_text('worker result ' + str(n))
        for cmd in [('add', 'result.txt'), ('commit', '-m', 'worker step ' + str(n))]:
            subprocess.run(['git', '-C', str(wt), *cmd], check=True)
probe = {}
if os.environ.get('FAKE_AGENT_DOCS'):
    probe = dict(agent_docs={name: Path(name).read_bytes().hex()
                            for name in ('AGENTS.md', 'GEMINI.md') if Path(name).is_file()},
                 status=subprocess.check_output(['git', 'status', '--porcelain', '-uall'], text=True))
if os.environ.get('FAKE_REVIEW_WRITE'):
    wt = Path.cwd()
    def git(*args): return subprocess.check_output(['git', *args], text=True).strip()
    probe = dict(cwd=str(wt), head=git('rev-parse', 'HEAD'),
                 git_dir=git('rev-parse', '--absolute-git-dir'),
                 origin=git('remote', 'get-url', 'origin'))
out.write_text(json.dumps({'args': a, 'sid': os.getsid(0), 'pid': os.getpid(), 'ppid': os.getppid(),
                           'stdin': sys.stdin.read(), 'role': os.environ.get('DEVSTANDARD_ROLE'),
                           'path': os.environ['PATH'], **probe}))
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

    def ignore(self, *patterns):
        with (self.project / '.gitignore').open('a') as stream:
            stream.write(''.join(pattern + '\n' for pattern in patterns))
        self.git('add', '.gitignore')
        self.git('commit', '-m', 'ignore local inputs')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

    def dispatch_module(self):
        loader = importlib.machinery.SourceFileLoader('dispatch_agent_docs', str(self.script))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(SOURCE / 'scripts'), *sys.path]):
            loader.exec_module(module)
        return module

    def agent_doc_lane(self):
        self.ignore('/AGENTS.md', '/GEMINI.md', '/cache/', '/nested/')
        for name in ('AGENTS.md', 'GEMINI.md'):
            (self.project / name).write_bytes(b'## Core need\r\nKeep canonical context.\x00\n')
        return self.start('--implementation', 'agy')

    def merged_pr(self, lane, head=None):
        head = head or self.git('rev-parse', lane['branch'])
        pr = dict(number=12, state='closed', merged_at='2026-10-21T00:00:00Z',
                  head=dict(sha=head, ref=lane['branch']), base=dict(ref='main', sha=head),
                  html_url='https://github.com/o/r/pull/12')
        (self.root / 'pr.json').write_text(json.dumps(pr))
        return pr

    def assert_returned(self, run):
        self.assertIn('executor_exit', run)

    def finish(self, run):
        self.assert_returned(run)
        return json.loads(Path(run['output']).read_text())

    def review_packet(self, base=None, head=None, identity='{REVIEWER_IDENTITY}'):
        base = base or self.git('rev-parse', 'origin/main')
        head = head or base
        template = (SOURCE / 'reference/reviewer.md').read_text()
        slots = dict(
            REVIEWER_IDENTITY=identity,
            ISSUE_GOAL_STATEMENT='Produce evidence.',
            ISSUE_BOUNDS='One task.',
            ISSUE_DONE_CHECK='Output captured.',
            COMPLETE_PR_DESCRIPTION='Complete report.',
            REVIEW_BASE_SHA=base,
            HEAD_SHA=head,
            CI_CONFIGURATION_PATHS='NONE',
            CI_FALLBACK_COMMENT_OR_NONE='NONE',
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

    def test_worker_syncs_ignored_root_agent_docs_before_launch_with_clean_status(self):
        self.ignore('/AGENTS.md', '/GEMINI.md')
        contents = b'## Core need\r\nLocal context.\x00\n'
        for name in ('AGENTS.md', 'GEMINI.md'):
            (self.project / name).write_bytes(contents)
        self.env['FAKE_AGENT_DOCS'] = '1'
        run = self.start()
        self.assertEqual(self.finish(run)['agent_docs'],
                         {'AGENTS.md': contents.hex(), 'GEMINI.md': contents.hex()})
        self.assertEqual(self.finish(run)['status'], '')
        self.assertEqual(self.git('-C', run['worktree'], 'status', '--porcelain', '-uall'), '')

    def test_worker_sync_skips_tracked_and_unignored_source_docs(self):
        (self.project / 'AGENTS.md').write_text('Tracked baseline.')
        self.git('add', 'AGENTS.md')
        self.git('commit', '-m', 'tracked context')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        (self.project / 'AGENTS.md').write_text('Uncommitted tracked change.')
        (self.project / 'GEMINI.md').write_text('Unignored local context.')
        run = self.start('--implementation', 'agy')
        wt = Path(run['worktree'])
        self.assertEqual((wt / 'AGENTS.md').read_text(), 'Tracked baseline.')
        self.assertFalse((wt / 'GEMINI.md').exists())
        self.assertEqual(self.git('-C', str(wt), 'status', '--porcelain', '-uall'), '')

    def test_worker_sync_skips_source_symlinks_and_directories(self):
        self.ignore('/AGENTS.md', '/GEMINI.md')
        source = self.root / 'context.txt'
        source.write_text('Context behind a symlink.')
        (self.project / 'AGENTS.md').symlink_to(source)
        (self.project / 'GEMINI.md').mkdir()
        run = self.start('--implementation', 'agy')
        for name in ('AGENTS.md', 'GEMINI.md'):
            self.assertFalse(os.path.lexists(Path(run['worktree']) / name))

    def test_sync_preserves_existing_symlink_tracked_and_unignored_destinations(self):
        self.ignore('/AGENTS.md')
        (self.project / 'AGENTS.md').write_text('Canonical context.')
        module = self.dispatch_module()
        for kind in ('file', 'directory', 'symlink', 'broken-symlink', 'tracked-missing', 'unignored'):
            with self.subTest(destination=kind):
                _, wt = self.hand_made_lane(branch=f'feat/{kind}', dirname=kind)
                dest = wt / 'AGENTS.md'
                if kind == 'file':
                    dest.write_text('Keep this local context.')
                elif kind == 'directory':
                    dest.mkdir()
                elif kind in ('symlink', 'broken-symlink'):
                    dest.symlink_to(self.project / ('AGENTS.md' if kind == 'symlink' else 'missing'))
                elif kind == 'tracked-missing':
                    dest.write_text('Tracked context.')
                    self.git('-C', str(wt), 'add', '-f', 'AGENTS.md')
                    dest.unlink()
                else:
                    (wt / '.gitignore').write_text('/.agents/worktrees/\n')
                with patch.dict(os.environ, self.env):
                    module.sync_root_agent_docs(self.project, wt)
                if kind == 'file':
                    self.assertEqual(dest.read_text(), 'Keep this local context.')
                elif kind == 'directory':
                    self.assertTrue(dest.is_dir())
                elif kind in ('symlink', 'broken-symlink'):
                    self.assertTrue(dest.is_symlink())
                else:
                    self.assertFalse(os.path.lexists(dest))

    def test_reviewer_syncs_canonical_project_docs_into_disposable_clone(self):
        lane = self.agent_doc_lane()
        (Path(lane['worktree']) / 'AGENTS.md').write_text('Stale lane context.')
        self.env['FAKE_AGENT_DOCS'] = '1'
        run = self.call('--purpose', 'reviewer', '--packet', str(self.review_packet()))
        data = self.finish(run)
        contents = b'## Core need\r\nKeep canonical context.\x00\n'.hex()
        self.assertEqual(data['agent_docs'], {'AGENTS.md': contents, 'GEMINI.md': contents})
        self.assertEqual(data['status'], '')
        self.assertFalse(Path(run['review_checkout']).exists())

    def test_reviewer_sync_skips_destination_without_ignore_rule(self):
        # info/exclude is local to the source repository and is not cloned.
        exclude = Path(self.git('rev-parse', '--git-path', 'info/exclude'))
        if not exclude.is_absolute():
            exclude = self.project / exclude
        with exclude.open('a') as stream:
            stream.write('/AGENTS.md\n')
        (self.project / 'AGENTS.md').write_text('Source-only ignored context.')
        self.start('--implementation', 'agy')
        self.env['FAKE_AGENT_DOCS'] = '1'
        run = self.call('--purpose', 'reviewer', '--packet', str(self.review_packet()))
        self.assertEqual(self.finish(run)['agent_docs'], {})
        self.assertEqual(self.finish(run)['status'], '')

    def test_codex_worker_lane_creation_and_flags(self):
        # Also verify omitting --implementation defaults CLI flag selection to codex.
        run = self.call('--purpose', 'worker', '--base', 'origin/main')
        self.assertEqual(run['implementation'], 'codex')
        data = self.finish(run)
        args = data['args']
        self.assertIn('-s', args)
        self.assertEqual(args[args.index('-s') + 1], 'workspace-write')
        self.assertIn('--add-dir', args)
        self.assertNotIn('--ephemeral', args)
        self.assert_role_config(args, 'worker')
        brief = Path(run['brief']).read_text()
        self.assertNotIn('## Worker mechanics', brief)
        self.assertIn('Environment: OS-sandboxed Codex CLI rooted at Worktree', brief)
        self.assertIn('# Task packet', brief)
        self.assert_helpers(brief, 'codex')

    def test_codex_reviewer_disposable_checkout(self):
        self.start('--implementation', 'codex')
        packet = self.review_packet()
        run = self.call('--purpose', 'reviewer', '--implementation', 'codex', '--packet', str(packet))
        data = self.finish(run)
        self.assertEqual(data['role'], 'reviewer')
        self.assertIn('--ephemeral', data['args'])
        self.assert_role_config(data['args'], 'reviewer')
        self.assertIn('Reviewer identity: Codex, gpt-6.1-sol at high.', data['stdin'])
        self.assertIn('Environment: disposable CLI clone; return the whole verdict in CLI output', data['stdin'])
        self.assert_helpers(Path(run['brief']).read_text(), 'codex')
        self.assertIn('review_checkout', run)
        # Checkout directory is cleaned up upon return
        self.assertFalse(Path(run['review_checkout']).exists())

    def test_mcp_admission_batches_valid_overrides_in_worker_cwd(self):
        probe = self.root / 'mcp.jsonl'
        self.env.update(MCP_PROBE=str(probe), FAKE_MCP_LIST=json.dumps([
            dict(name='zulu_2'), dict(name='alpha-tool'), dict(name='alpha-tool'),
            dict(name='disabled', enabled=False), dict(name='not.dotted'),
        ]))
        run = self.start()
        calls = [json.loads(line) for line in probe.read_text().splitlines()]
        self.assertEqual(calls, [
            dict(args=['mcp', 'list', '--json'], cwd=run['worktree']),
            dict(args=['mcp', 'get', 'alpha-tool', '--json',
                       '-c', 'mcp_servers.alpha-tool.default_tools_approval_mode="approve"',
                       '-c', 'mcp_servers.zulu_2.default_tools_approval_mode="approve"'],
                 cwd=run['worktree']),
        ])
        self.assertEqual(run['mcp_servers'], ['alpha-tool', 'zulu_2'])
        self.assertIn('MCP servers a dotted -c override cannot address, left unadmitted: not.dotted.',
                      run['notice'])
        args = self.finish(run)['args']
        self.assertIn('mcp_servers.alpha-tool.default_tools_approval_mode="approve"', args)
        self.assertIn('mcp_servers.zulu_2.default_tools_approval_mode="approve"', args)
        self.assertNotIn('mcp_servers.disabled.default_tools_approval_mode="approve"', args)
        self.assertNotIn('mcp_servers.not.dotted.default_tools_approval_mode="approve"', args)

    def test_mcp_admission_isolates_rejected_plugin_and_project_overrides(self):
        probe = self.root / 'mcp.jsonl'
        self.env.update(MCP_PROBE=str(probe), FAKE_MCP_LIST=json.dumps([
            dict(name='cua_repl'), dict(name='local_tool'), dict(name='untrusted'),
            dict(name='not.dotted'),
        ]), FAKE_MCP_REJECT='["cua_repl", "untrusted"]')
        run = self.start()
        calls = [json.loads(line) for line in probe.read_text().splitlines()]
        self.assertEqual(len(calls), 5)  # list, rejected batch, three individual gets
        self.assertTrue(all(call['cwd'] == run['worktree'] for call in calls))
        self.assertEqual(calls[1]['args'], ['mcp', 'get', 'cua_repl', '--json',
            '-c', 'mcp_servers.cua_repl.default_tools_approval_mode="approve"',
            '-c', 'mcp_servers.local_tool.default_tools_approval_mode="approve"',
            '-c', 'mcp_servers.untrusted.default_tools_approval_mode="approve"'])
        for call, name in zip(calls[2:], ['cua_repl', 'local_tool', 'untrusted']):
            self.assertEqual(call['args'], ['mcp', 'get', name, '--json', '-c',
                f'mcp_servers.{name}.default_tools_approval_mode="approve"'])
        self.assertEqual(run['mcp_servers'], ['local_tool'])
        self.assertIn('left unadmitted: cua_repl, not.dotted, untrusted.', run['notice'])
        args = self.finish(run)['args']
        self.assertIn('mcp_servers.local_tool.default_tools_approval_mode="approve"', args)
        for name in ('cua_repl', 'untrusted', 'not.dotted'):
            self.assertNotIn(f'mcp_servers.{name}.default_tools_approval_mode="approve"', args)
        self.assertEqual(self.lane_records()[-1]['notice'], run['notice'])

    def test_mcp_enumeration_failures_and_unaddressable_names_do_not_block_dispatch(self):
        for listing, exit_code, notice in [
            ('[]', '1', 'could not be enumerated'),
            ('not json', '0', 'could not be enumerated'),
            ('{}', '0', 'could not be enumerated'),
            ('[{"name":"not.dotted"}]', '0', 'left unadmitted: not.dotted.'),
            ('[]', '0', None),
        ]:
            with self.subTest(listing=listing, exit_code=exit_code):
                probe = self.root / 'mcp.jsonl'
                probe.write_text('')
                self.env.update(MCP_PROBE=str(probe), FAKE_MCP_LIST=listing, FAKE_MCP_EXIT=exit_code)
                run = self.start()
                self.assertEqual(run['mcp_servers'], [])
                self.assertEqual(len(probe.read_text().splitlines()), 1)
                if notice:
                    self.assertIn(notice, run['notice'])
                else:
                    self.assertNotIn('notice', run)

    def test_reviewer_mcp_admission_uses_scratch_before_clone_exists(self):
        self.start('--implementation', 'agy')
        probe = self.root / 'mcp.jsonl'
        self.env.update(MCP_PROBE=str(probe), FAKE_MCP_LIST='[{"name":"review_tool"}]')
        run = self.call('--purpose', 'reviewer', '--implementation', 'codex',
                        '--packet', str(self.review_packet()))
        calls = [json.loads(line) for line in probe.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call['cwd'] == str(Path(run['brief']).parent) for call in calls))
        self.assertEqual(run['mcp_servers'], ['review_tool'])

    def assert_verbatim_spawn_notice(self, text):
        for token in ('spawn["type_name"]', 'spawn["role"]', 'spawn["model"]', 'spawn["prompt"]',
                      'verbatim', 'invoke_subagent', 'send_message', 'file pointer', 'rename'):
            self.assertIn(token, text)

    def test_agy_native_worker_prepares_agent_spawn(self):
        help_out = subprocess.check_output(
            [sys.executable, str(self.script), '--help'], env=self.env, text=True
        )
        self.assert_verbatim_spawn_notice(help_out)

        run = self.call('--purpose', 'worker', '--base', 'origin/main', '--implementation', 'agy')
        self.assertEqual(run['status'], 'awaiting-agent-tool')
        self.assertIn('instruction', run)
        self.assert_verbatim_spawn_notice(run['notice'])
        instruction = json.loads(Path(run['instruction']).read_text())
        self.assertEqual(instruction['subagent_type'], 'devstandard:worker')
        self.assertEqual(instruction['type_name'], 'self')
        self.assertEqual(instruction['role'], 'Issue 12 worker')
        self.assertEqual(instruction['model'], 'inherit')
        self.assertIsNone(instruction['effort'])
        self.assertNotIn('## Worker mechanics', instruction['prompt'])
        self.assertIn('Environment: native Antigravity subagent; validate Worktree and Branch before acting',
                      instruction['prompt'])
        self.assertIn('# Task packet', instruction['prompt'])
        brief_path = Path(run['brief'])
        self.assertEqual(instruction['prompt'], brief_path.read_text())
        self.assertFalse((brief_path.parent / 'evidence.json').exists())
        self.assert_helpers(brief_path.read_text(), 'agy')

    def test_agy_native_reviewer_prepares_agent_spawn(self):
        self.call('--purpose', 'worker', '--base', 'origin/main', '--implementation', 'agy')
        rows = json.loads(self.comments.read_text())
        rows.append(dict(id=99, body='Human refinement.', user=dict(login='alice'),
                         created_at='2026-11-15T00:00:00Z'))
        self.comments.write_text(json.dumps(rows))
        packet = self.review_packet()
        run = self.call('--purpose', 'reviewer', '--implementation', 'agy', '--packet', str(packet))
        self.assertEqual(run['status'], 'awaiting-agent-tool')
        self.assert_verbatim_spawn_notice(run['notice'])
        instruction = json.loads(Path(run['instruction']).read_text())
        self.assertEqual(instruction['subagent_type'], 'devstandard:reviewer')
        self.assertEqual(instruction['type_name'], 'self')
        self.assertEqual(instruction['role'], 'Issue 12 reviewer')
        self.assertEqual(instruction['model'], 'inherit')
        self.assertIsNone(instruction['effort'])

        scratch = Path(run['brief']).parent
        evidence_path = scratch / 'evidence.json'
        self.assertTrue(evidence_path.is_file())
        evidence_rows = json.loads(evidence_path.read_text())
        self.assertEqual(len(evidence_rows), 3)

        prompt = instruction['prompt']
        self.assertNotIn('brief.txt', prompt)
        self.assertIn('# Reviewer', prompt)
        self.assertIn('## Packet integrity (assembly report)', prompt)
        self.assertIn('Reviewer: Antigravity subagent, inherit — reviewed ', prompt)
        self.assertIn('# Task packet', prompt)
        self.assertIn('----- BEGIN ISSUE BODY -----', prompt)
        self.assertIn('Human refinement.', prompt)
        self.assertIn('Reviewer identity: Antigravity subagent, inherit.', prompt)
        self.assertIn('Environment: native Antigravity subagent; never modify main or lane worktrees', prompt)
        self.assert_helpers(prompt, 'agy')
        self.assertLess(prompt.index('# Reviewer'), prompt.index('# Task packet'))
        self.assertLess(prompt.index('# Task packet'), prompt.index('Helpers:'))
        self.assertLess(prompt.index('Helpers:'), prompt.index('## Pinned Git evidence'))
        pinned_tail = prompt.split('## Pinned Git evidence\n', 1)[1]
        self.assertIn(str(evidence_path), pinned_tail)
        self.assertIn('read_file', pinned_tail)
        self.assertIn('in full', pinned_tail.lower())
        self.assertIn('whole verdict', pinned_tail.lower())

        brief = Path(run['brief']).read_text()
        self.assertEqual(
            prompt.split('\n\n## Pinned Git evidence\n', 1)[0],
            brief.split('\n\n## Pinned Git evidence\n', 1)[0],
        )
        self.assertIn('Reviewer identity: Antigravity subagent, inherit.', brief)
        self.assertIn('Environment: native Antigravity subagent; never modify main or lane worktrees', brief)
        self.assert_helpers(brief, 'agy')
        self.assertLess(brief.index('# Task packet'), brief.index('## Pinned Git evidence'))
        self.assertLess(brief.index('Helpers:'), brief.index('## Pinned Git evidence'))
        archived_evidence = json.loads(brief.split('\n\n## Pinned Git evidence\n', 1)[1])
        self.assertEqual(evidence_rows, archived_evidence)

    def assert_helpers(self, brief, implementation):
        packet = brief.split('# Task packet', 1)[1]
        self.assertIn('Helpers:', packet)
        tail = packet.split('Helpers:', 1)[1]
        helpers = tail.splitlines()[0]
        native = {'codex': ('Codex', '`gpt-6-astra` at `max`',
                            '`gpt-6.1-sol` at `high`',
                            '`gpt-6.1-terra` at `high`'),
                  'agy': ('Antigravity', '`inherit`', '`inherit`', '`flash`')}[implementation]
        preamble, rows_part = helpers.split(' — ', 1)
        self.assertIn(native[0] + "'s native subagent tool", preamble)
        self.assertIn('scripts/dispatch', preamble)
        self.assertIn('scripts/review-packet', preamble)
        self.assertTrue(preamble.endswith('`scripts/review-packet`'), preamble)
        self.assertIn('unless explicitly specified', preamble)
        self.assertIn("pass the project's core need and how the helper's task serves it", preamble)
        if implementation == 'agy':
            self.assertIn('`TypeName="self"`', preamble)
            self.assertIn('never `TypeName="research"`', preamble)
            self.assertIn('read-only prompt boundary', preamble)
        else:
            self.assertNotIn('TypeName=', preamble)
        rows = rows_part.split('; ')
        self.assertEqual(len(rows), 3)
        self.assertIn('Its conclusion directly decides a merge or a design', rows[0])
        self.assertTrue(rows[0].endswith(': ' + native[1]), rows[0])
        self.assertIn('Research, reconnaissance, and information synthesis', rows[1])
        self.assertTrue(rows[1].endswith(': ' + native[2]), rows[1])
        self.assertEqual(rows[2], '**The default — everything else**: ' + native[3] + '.')

    def test_agy_reviewer_pins_diff_evidence_without_blob_dumps(self):
        (self.project / 'image.png').write_bytes(b'\x89PNG\x00\xffold')
        self.git('add', 'image.png')
        self.git('commit', '-m', 'binary base')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        base = self.git('rev-parse', 'HEAD')
        lane = self.start('--implementation', 'agy')
        wt = Path(lane['worktree'])
        (wt / 'image.png').write_bytes(b'\x89PNG\x00\xffnew')
        (wt / 'note.txt').write_text('hello\n')
        self.git('-C', str(wt), 'add', 'image.png', 'note.txt')
        self.git('-C', str(wt), 'commit', '-m', 'binary and text change')
        head = self.git('rev-parse', lane['branch'])
        packet = self.review_packet(base=base, head=head)
        run = self.call('--purpose', 'reviewer', '--implementation', 'agy', '--packet', str(packet))
        scratch = Path(run['brief']).parent
        evidence = json.loads((scratch / 'evidence.json').read_text())
        brief = Path(run['brief']).read_text()
        archived = json.JSONDecoder().raw_decode(brief.split('## Pinned Git evidence\n', 1)[1])[0]
        self.assertEqual(evidence, archived)
        instruction = json.loads(Path(run['instruction']).read_text())
        self.assertNotIn('+hello', instruction['prompt'])
        self.assertIn(str(scratch / 'evidence.json'), instruction['prompt'])
        self.assertEqual(len(evidence), 3)
        self.assertTrue(all(row['exit_code'] == 0 for row in evidence))
        self.assertIn('--name-status', evidence[0]['command'])
        self.assertIn('image.png', ''.join(evidence[0]['stdout']))
        self.assertIn('--stat', evidence[1]['command'])
        self.assertIn('+hello', ''.join(evidence[2]['stdout']))

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
        pr = dict(number=12, state='closed', merged_at='2026-10-21T00:00:00Z',
                  head=dict(sha=head, ref=run['branch']), base=dict(ref='main', sha=head),
                  html_url='https://github.com/o/r/pull/12')
        (self.root / 'pr.json').write_text(json.dumps(pr))

        err = self.call('--cleanup', '--pr', '12', ok=False)
        self.assertIn('dirty worktree', err)

    def test_cleanup_removes_identical_ignored_root_agent_docs_after_merged_checks(self):
        lane = self.agent_doc_lane()
        wt = Path(lane['worktree'])
        self.merged_pr(lane)
        cleanup = self.call('--cleanup', '--pr', '12')
        self.assertEqual(cleanup['status'], 'cleaned')
        self.assertFalse(wt.exists())
        self.assertNotIn(lane['branch'], self.git('branch', '--format=%(refname:short)').splitlines())
        self.assertTrue((self.project / 'AGENTS.md').is_file())

    def test_cleanup_refuses_changed_missing_or_symlink_root_agent_docs(self):
        lane = self.agent_doc_lane()
        wt = Path(lane['worktree'])
        source, dest = self.project / 'AGENTS.md', wt / 'AGENTS.md'
        contents = source.read_bytes()
        for kind in ('changed', 'missing-source', 'source-symlink', 'lane-symlink'):
            with self.subTest(artifact=kind):
                source.write_bytes(contents)
                dest.write_bytes(contents)
                if kind == 'changed':
                    dest.write_bytes(contents.replace(b'\r\n', b'\n'))
                elif kind == 'missing-source':
                    source.unlink()
                elif kind == 'source-symlink':
                    source.unlink()
                    source.symlink_to(dest)
                else:
                    dest.unlink()
                    dest.symlink_to(source)
                err = self.call('--cleanup', '--discard', ok=False)
                self.assertIn('ignored artifacts remain; inventory and remove or retain them first', err)
                self.assertTrue(wt.is_dir())
                self.assertTrue(os.path.lexists(dest))
                if kind == 'changed':
                    self.assertEqual(dest.read_bytes(), contents.replace(b'\r\n', b'\n'))
                source.unlink(missing_ok=True)
                dest.unlink()

    def test_cleanup_refuses_other_ignored_artifacts_without_unlinking_docs(self):
        lane = self.agent_doc_lane()
        wt = Path(lane['worktree'])
        for rel in ('cache/result.txt', 'nested/AGENTS.md'):
            with self.subTest(artifact=rel):
                artifact = wt / rel
                artifact.parent.mkdir()
                artifact.write_text('Preserve this ignored artifact.')
                err = self.call('--cleanup', '--discard', ok=False)
                self.assertIn('ignored artifacts remain; inventory and remove or retain them first', err)
                self.assertEqual((wt / 'AGENTS.md').read_bytes(), (self.project / 'AGENTS.md').read_bytes())
                self.assertEqual(artifact.read_text(), 'Preserve this ignored artifact.')
                artifact.unlink()
                artifact.parent.rmdir()

    def test_cleanup_preserves_identical_docs_when_later_head_check_fails(self):
        lane = self.agent_doc_lane()
        wt = Path(lane['worktree'])
        self.merged_pr(lane)
        (wt / 'unpublished.txt').write_text('Preserve this commit.')
        self.git('-C', str(wt), 'add', 'unpublished.txt')
        self.git('-C', str(wt), 'commit', '-m', 'unpublished work')
        head = self.git('rev-parse', lane['branch'])
        err = self.call('--cleanup', '--pr', '12', ok=False)
        self.assertIn('lane head differs from merged PR', err)
        self.assertEqual(self.git('rev-parse', lane['branch']), head)
        for name in ('AGENTS.md', 'GEMINI.md'):
            self.assertEqual((wt / name).read_bytes(), (self.project / name).read_bytes())

    def test_adopt_refuses_other_checked_out_branch(self):
        branch, wt = self.hand_made_lane()
        self.git('-C', str(wt), 'checkout', '-b', 'other')
        err = self.call('--adopt', '--branch', branch, '--worktree', str(wt),
                        '--base', 'origin/main', ok=False)
        self.assertIn('branch', err)
        self.assertEqual(self.lane_records(), [])

    def test_adopt_existing_lane_refuses_other_checked_out_branch(self):
        branch, wt = self.hand_made_lane()
        flags = ('--branch', branch, '--worktree', str(wt), '--base', 'origin/main')
        lane = self.call('--adopt', *flags)
        readopted = self.call('--adopt')
        self.assertEqual(readopted['status'], 'adopted')
        self.assertEqual(readopted['lane_id'], lane['lane_id'])
        comments = self.comments.read_text()

        self.git('-C', str(wt), 'checkout', '-b', 'other')
        for lane_flags in ((), flags):
            with self.subTest(flags=lane_flags):
                err = self.call('--adopt', *lane_flags, ok=False)
                self.assertIn('checked-out branch', err)
                self.assertEqual(self.comments.read_text(), comments)
                self.assertEqual(self.git('-C', str(wt), 'branch', '--show-current'), 'other')

    def test_cleanup_refuses_switched_branch_and_preserves_unpublished_commits(self):
        lane = self.start('--implementation', 'agy')
        wt = Path(lane['worktree'])
        merged = self.git('rev-parse', lane['branch'])
        (wt / 'unpublished.txt').write_text('Keep this commit.')
        self.git('-C', str(wt), 'add', '.')
        self.git('-C', str(wt), 'commit', '-m', 'unpublished')
        unpublished = self.git('rev-parse', lane['branch'])
        self.git('-C', str(wt), 'checkout', '-b', 'other', merged)
        pr = dict(number=12, state='closed', merged_at='2026-10-21T00:00:00Z',
                  head=dict(sha=merged, ref=lane['branch']), base=dict(ref='main', sha=merged),
                  html_url='https://github.com/o/r/pull/12')
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
        pr = dict(number=12, state='closed', merged_at='2026-10-21T00:00:00Z',
                  head=dict(sha=head, ref=run['branch']), base=dict(ref='main', sha=head),
                  html_url='https://github.com/o/r/pull/12')

        # Unmerged refuses
        pr_open = dict(pr, state='open', merged_at=None)
        (self.root / 'pr.json').write_text(json.dumps(pr_open))
        err = self.call('--cleanup', '--pr', '12', ok=False)
        self.assertIn('merged', err)

        # Merged succeeds
        (self.root / 'pr.json').write_text(json.dumps(pr))
        cleanup = self.call('--cleanup', '--pr', '12')
        self.assertEqual(cleanup['status'], 'cleaned')
        self.assertEqual(cleanup.get('pr'), pr['html_url'])
        self.assertEqual(self.lane_records()[-1].get('pr'), pr['html_url'])
        self.assertFalse(wt.exists())

    def test_codex_fallback_is_resolved_and_inherited_by_child(self):
        user = self.root / 'user'
        fallback = user / '.npm-global/bin'
        fallback.mkdir(parents=True)
        (self.bin / 'codex').rename(fallback / 'codex')
        for tool, target in [('python3', sys.executable), ('git', shutil.which('git'))]:
            (self.bin / tool).symlink_to(target)
        loader = importlib.machinery.SourceFileLoader('dispatch_path_probe', str(self.script))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(SOURCE / 'scripts'), *sys.path]):
            loader.exec_module(module)
        argv = [str(self.script), '12', '--project', str(self.project), '--purpose', 'worker',
                '--base', 'origin/main', '--implementation', 'codex', '--wait']
        output = io.StringIO()
        with patch.object(Path, 'home', return_value=user), \
             patch.dict(os.environ, dict(self.env, PATH=str(self.bin)), clear=True), \
             patch.object(tempfile, 'tempdir', None), \
             patch.object(sys, 'argv', argv), redirect_stdout(output):
            self.assertEqual(module.main(), 0)
        run = json.loads(output.getvalue())
        self.assertEqual(Path(run['brief']).parent.parent, self.root)
        child = self.finish(run)
        self.assertEqual(child['path'].split(os.pathsep)[:2], [str(self.bin), str(fallback)])

    def test_continuation_lists_rest_prs_and_normalizes_closed_states(self):
        lane = self.start('--implementation', 'agy')
        head = self.git('rev-parse', lane['branch'])
        for state, merged, label in [('closed', None, 'CLOSED'),
                                     ('closed', '2026-10-21T00:00:00Z', 'MERGED'),
                                     ('open', None, None)]:
            with self.subTest(state=state, merged_at=merged):
                pr = dict(number=13, state=state, merged_at=merged,
                          html_url='https://github.com/o/r/pull/13', body='',
                          head=dict(ref=lane['branch'], sha=head), base=dict(ref='main', sha=head))
                (self.root / 'pr.json').write_text(json.dumps([pr]))
                resumed = self.start('--implementation', 'agy')
                if label:
                    self.assertIn('#13 ' + label, resumed['pr_note'])
                else:
                    brief = Path(resumed['brief']).read_text()
                    self.assertIn('PR: https://github.com/o/r/pull/13', brief)

    def test_rest_issue_with_no_body_renders_empty_body(self):
        issue = json.loads(self.issue.read_text())
        issue['body'] = None
        self.issue.write_text(json.dumps(issue))
        lane = self.start('--implementation', 'agy')
        brief = Path(lane['brief']).read_text()
        self.assertIn('----- BEGIN ISSUE BODY -----\n\n----- END ISSUE BODY -----', brief)


if __name__ == '__main__':
    unittest.main(verbosity=2)
