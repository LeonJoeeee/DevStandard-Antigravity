"""Current-contract review packet assembly and verdict validation (stdlib only)."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'devstandard-review-packet-v1'
SLOT = re.compile(r'\{([A-Z_][A-Z_0-9]*)\}')
SHA = re.compile(r'(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})')


def require(condition, message):
    if not condition:
        raise ValueError(message)


CANONICAL_HEADING = re.compile(
    r'^ {0,3}###[ \t]+[*_]{0,2}(Verdict|Blocking|Notes)[*_]{0,2}[ \t]*(?:#+[ \t]*)?\r?$', re.M
)
VERDICT_PLAIN = re.compile(r'^[ \t]*[*_]{0,2}(Approve|Request changes)[*_]{0,2}(?=[\W_]|$)', re.M)
VERDICT_GROUNDED = re.compile(
    r'^[ \t]*[*_]{0,2}(Approve|Request changes)[*_]{0,2}[ \t]+—[ \t]+(\S[^\n]*)$', re.M
)

# Legacy verdict patterns kept strictly for allow_legacy=True historical PR comment readers.
LEGACY_DECISION = re.compile(
    r'^[*_]{0,2}(?:([12])\. [*_]{0,2}(Evidence-backed completion claim|Authorization and scope)'
    r'|(Ready to merge)): [*_]{0,2}(Yes|No|Pass|Fail)[*_]{0,2}(?=[\W_]|$)', re.M
)
LEGACY_GATES = ('1. Evidence-backed completion claim', '2. Authorization and scope')
LEGACY_LABELS = ('Goal verdict', *LEGACY_GATES, 'Ready to merge')
LEGACY_GOAL_HEADING = re.compile(r'^ {0,3}###[ \t]+[*_]{0,2}Goal verdict[*_]{0,2}[ \t]*(?:#+[ \t]*)?\r?\n', re.M)
LEGACY_GOAL_ANSWER = re.compile(
    r'(^### Goal verdict\n)(?:[ \t]*\r?\n)*[ \t]*[*_]{0,2}(Yes|No)[*_]{0,2}(?=[\W_]|$)', re.M
)


def _normalize_common(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return re.sub(r' — reviewed\s+([0-9a-fA-F]{40,64})', r' — reviewed \1', text)


def _legacy_decision_line(label, grounds=False):
    tail = r' — .+' if grounds else (r'(?=[\W_]|$)' if label == 'Goal verdict' else r'\b')
    if label == 'Goal verdict':
        return r'^### Goal verdict\n(Yes|No)' + tail
    if label == 'Ready to merge':
        return r'^Ready to merge: (Yes|No)' + tail
    return '^' + re.escape(label) + r': (Pass|Fail)' + tail


def _normalize_legacy(text):
    text = _normalize_common(text)
    stripped = LEGACY_DECISION.sub(
        lambda m: (f'{m[1]}. {m[2]}' if m[1] else m[3]) + f': {m[4]}', text
    )
    return LEGACY_GOAL_ANSWER.sub(r'\1\2', LEGACY_GOAL_HEADING.sub('### Goal verdict\n', stripped))


def _parse_legacy(text):
    text = _normalize_legacy(text)
    missing = [
        label for label in LEGACY_LABELS
        if re.findall(_legacy_decision_line(label), text, re.M)[:1]
        != re.findall(_legacy_decision_line(label, grounds=True), text, re.M)[:1]
    ]
    if missing:
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='decision lines stating no grounds: ' + ', '.join(missing))
    headings = list(re.finditer(r'^### (Goal verdict|Floor|Notes)\b[^\n]*$', text, re.M))
    if [m[0] for m in headings] != ['### Goal verdict', '### Floor', '### Notes']:
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='duplicate, missing, or out-of-order verdict section')
    goal_section = text[headings[0].end():headings[1].start()]
    answers = re.findall(r'^[ \t]*[*_]{0,2}(Yes|No)[*_]{0,2}[ \t]+—(?:[ \t]|$)', goal_section, re.M)
    if len(answers) != 1:
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='duplicate or missing Goal decision')
    matches = [list(re.finditer(_legacy_decision_line(label, grounds=True), text, re.M))
               for label in LEGACY_LABELS]
    if any(len(found) != 1 for found in matches):
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='duplicate or missing grounded decision line')
    if any(len(re.findall(_legacy_decision_line(label), text, re.M)) != 1 for label in LEGACY_LABELS):
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='duplicate or missing decision line')
    goal, gate1, gate2, ready = [found[0] for found in matches]
    if not (goal.start() == headings[0].start() < goal.end() <= headings[1].start()
            < gate1.start() < gate2.start() < ready.start() < headings[2].start()):
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='decision lines outside their ordered Goal/Floor sections')
    approved = (goal[1], gate1[1], gate2[1]) == ('Yes', 'Pass', 'Pass')
    if ready[1] != ('Yes' if approved else 'No'):
        return dict(valid=False, verdict=None, legacy=True, legacy_floor_ok=False,
                    reason='readiness contradicts Goal/Floor')
    return dict(
        valid=True,
        verdict='Approve' if approved else 'Request changes',
        legacy=True,
        legacy_floor_ok=(gate1[1] == 'Pass' and gate2[1] == 'Pass'),
        reason=None,
    )


def parse_verdict(text, head, identity=None, allow_legacy=False):
    """Validate and extract the structured decision from a whole reviewer return."""
    normalized = _normalize_common(text)
    reviewer = re.escape(identity) if identity is not None else r'[^\n]+'
    if not re.match(r'Reviewer: ' + reviewer + ' — reviewed ' + re.escape(head) + r'\n', normalized):
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='latest verdict does not review the exact accepted head and reviewer')

    canonical = CANONICAL_HEADING.sub(r'### \1', normalized)
    headings = list(re.finditer(r'^### (Verdict|Blocking|Notes)\b[^\n]*$', canonical, re.M))
    if (allow_legacy and not any(m[1] in ('Verdict', 'Blocking') for m in headings)
            and re.search(r'^ {0,3}###[ \t]+[*_]{0,2}Goal verdict\b', normalized, re.M)):
        return _parse_legacy(normalized)

    if [m[0] for m in headings] != ['### Verdict', '### Blocking', '### Notes']:
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='duplicate, missing, or out-of-order verdict section')

    verdict_section = canonical[headings[0].end():headings[1].start()]
    plain = VERDICT_PLAIN.findall(verdict_section)
    grounded = VERDICT_GROUNDED.findall(verdict_section)
    if plain and not grounded:
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='decision line stating no grounds: Verdict')
    if len(plain) != 1 or len(grounded) != 1:
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='duplicate or missing Verdict decision')
    first_nonblank = next((line for line in verdict_section.splitlines() if line.strip()), '')
    if not VERDICT_GROUNDED.match(first_nonblank):
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='Verdict section must open with Approve or Request changes and grounds')

    decision = grounded[0][0]
    blocking_section = canonical[headings[1].end():headings[2].start()]
    cleaned_blocking = re.sub(r'^[\s*_`]+|[\s*_`]+$', '', blocking_section)
    blocking_is_none = cleaned_blocking in ('', 'None', 'None.')
    if decision == 'Approve' and not blocking_is_none:
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='Approve verdict must not list items under Blocking')
    if decision == 'Request changes' and blocking_is_none:
        return dict(valid=False, verdict=None, legacy=False, legacy_floor_ok=False,
                    reason='Request changes verdict must state blocking items under Blocking')

    return dict(valid=True, verdict=decision, legacy=False, legacy_floor_ok=True, reason=None)


def verdict_shape(text, head, identity=None, allow_legacy=False):
    """Return None when `text` is a valid whole verdict for `head` (and `identity`), else defect string."""
    return parse_verdict(text, head, identity=identity, allow_legacy=allow_legacy)['reason']


def comment_review(body, next_round):
    """Extract `(round_number, verdict_text, warning)` from a plain review comment."""
    heading, _, verdict = body.partition('\n')
    canonical = re.fullmatch(r'## Code Review — round ([0-9]+)\r?', heading)
    if canonical:
        number = int(canonical[1])
        warning = (f'review heading has nonpositive round {number}; reconcile history'
                   if number < 1 else None)
        return number, verdict.lstrip('\n'), warning
    legacy = re.fullmatch(r'## [Mm]erge check 1 — round ([0-9]+)\r?', heading)
    number = int(legacy[1]) if legacy else next_round
    warning = None
    if not legacy:
        warning = f'legacy review heading has no readable round; inferred round {number}'
    elif heading != f'## Merge check 1 — round {number}' or number < 1:
        warning = f'legacy review heading is noncanonical for recorded round {number}; reconcile history'
    return number, verdict.lstrip('\n'), warning


legacy_review = comment_review


def latest_ruling(rulings):
    """Keep a recorded human disposition when a later ruling omits its authorization.

    Callers supply only rulings for the latest returned round and head. A later ordinary ruling
    cannot turn that human disposition into permission to reuse the failed lane.
    """
    if not rulings:
        return None
    human = next((r['decision'] for r in reversed(rulings) if r.get('human_authorization')), None)
    return dict(rulings[-1], human_disposition=human) if human else rulings[-1]


def recovery_ruling(ruling, head):
    """A trusted continuation ruling must carry recovery evidence for this accepted head.

    The ruling publisher verifies a base advance or records the orchestrator's guard-refusal
    attestation. Consumers use that same durable decision; they never infer recovery from Notes.
    """
    if not ruling or ruling.get('decision') != 'continue' or ruling.get('head') != head:
        return False
    recovery = ruling.get('recovery')
    if not isinstance(recovery, dict) or recovery.get('head') != head:
        return False
    if recovery.get('kind') == 'behind-base':
        base = recovery.get('base')
        return isinstance(base, str) and bool(SHA.fullmatch(base)) and base != head
    if recovery.get('kind') == 'guard-refusal':
        reason = recovery.get('reason')
        return isinstance(reason, str) and bool(reason.strip())
    return False


def pinned_git(project, env=None):
    """Read-only git reader returning raw bytes; env is pinned by sanitizing callers."""
    def git(*args):
        result = subprocess.run(['git', '-C', str(project), *args], capture_output=True, env=env)
        require(result.returncode == 0, 'cannot read pinned diff: ' + result.stderr.decode(errors='replace'))
        return result.stdout
    return git


# CI configuration is what a CI run reads as its own definition: the workflow files, plus the gate
# commands those workflows invoke. Stated once here; the packet's flag line is computed from it.
CI_CONFIGURATION = re.compile(r'\.github/(?:workflows/.+|[^/]+\.py)')


def ci_configuration_paths(project, base, head, env=None):
    """Sorted CI-configuration paths the pinned name-status diff touches; a run the diff configured."""
    require(SHA.fullmatch(base) and SHA.fullmatch(head), 'the pinned diff form needs full base and head SHAs')
    raw = pinned_git(project, env)('diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                                   '--name-status', '-z', base, head)
    # --no-renames leaves every record one status and one path, so the paths are the odd fields.
    paths = set(field.decode() for field in raw.rstrip(b'\0').split(b'\0')[1::2])
    return sorted(path for path in paths if CI_CONFIGURATION.fullmatch(path))


def issue_contract(body):
    # Locate headings on a masked copy, then take values from the original text.
    # Fenced commands and nested headings are part of the issue's contract, not delimiters.
    masked = re.sub(r'<!--.*?-->', lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), body, flags=re.S)
    headings, offset, fence = [], 0, None
    for line in masked.splitlines(keepends=True):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif fence is None:
            heading = re.match(r'^(#{1,6})\s+([^\n]+?)\s*#*\s*$', line)
            if heading:
                headings.append((offset, offset + len(line), len(heading[1]), heading[2].lower()))
        offset += len(line)
    fields = {}
    for i, (_, begin, level, name) in enumerate(headings):
        if name not in ('goal', 'bounds', 'done-check'):
            continue
        require(name not in fields, f'duplicate {name} section')
        end = next((h[0] for h in headings[i + 1:] if h[2] <= level), len(body))
        value = body[begin:end].strip()
        require(value and not SLOT.fullmatch(value) and value not in ('TODO', 'TBD', '{field}'),
                f'missing or unresolved placeholder in {name}')
        fields[name] = value
    require(set(fields) == {'goal', 'bounds', 'done-check'}, 'missing issue goal, bounds, or done-check')
    return fields


def template():
    """Read the direct reviewer prompt contract (`reference/reviewer.md`)."""
    text = (ROOT / 'reference/reviewer.md').read_text()
    require(text.strip() and not text.lstrip().startswith('```'),
            'reference/reviewer.md must be a direct prompt without an outer fence')
    return text


UNPINNED = 'NOT PINNED'
# Named in the packet's own integrity report, so the reviewer reads what assembly pinned beside
# what it could not.
REPORTED_PINS = ('REVIEW_BASE_SHA', 'HEAD_SHA', 'CI_CONFIGURATION_PATHS', 'CI_FALLBACK_COMMENT_OR_NONE')


def validate(packet, identity=None):
    """Validate packet against current `reference/reviewer.md` and return filled slot dictionary."""
    source = template()
    require(packet.get('template') == source, 'stale reviewer contract; assemble again')
    slots = dict(packet.get('slots', {}))
    if identity:
        slots['REVIEWER_IDENTITY'] = identity
    for key in set(SLOT.findall(source)):
        slots[key] = slots[key] if isinstance(slots.get(key), str) else UNPINNED
    return slots


def integrity(packet, slots):
    """Every packet-integrity gap assembly could not close, in the order a reader checks them."""
    gaps = list(packet.get('integrity_gaps') or [])
    if packet.get('format') != FORMAT:
        gaps.append(f'format: the packet declares {packet.get("format")!r}, not {FORMAT}')
    source = template()
    for key in sorted(set(SLOT.findall(source))):
        value = slots.get(key, UNPINNED)
        if value == UNPINNED:
            gaps.append(f'{key}: the contract names this slot and assembly did not fill it')
        elif not value.strip():
            gaps.append(f'{key}: filled with empty text')
        # Quoted evidence is opaque: only an entire slot still equal to a marker is unfilled.
        elif SLOT.fullmatch(value.strip()) or value.strip() in ('TODO', 'TBD', '{field}'):
            gaps.append(f'{key}: unresolved placeholder {value.strip()}')
        elif key in ('REVIEW_BASE_SHA', 'HEAD_SHA') and not SHA.fullmatch(value):
            gaps.append(f'{key}: {value} is not a full SHA')
    return gaps


def integrity_report(packet, slots):
    """The `## Packet integrity` section reporting pinned values and any gaps."""
    def summary(value):
        first = (value.strip().splitlines() or [''])[0]
        return first[:200] + (' …' if len(first) > 200 or first != value.strip() else '')

    pinned = [f'- {key}: {summary(slots.get(key, UNPINNED))}' for key in REPORTED_PINS]
    gaps = integrity(packet, slots) or ['NONE']
    return ('## Packet integrity (assembly report)\n'
            'Pinned:\n' + '\n'.join(pinned) + '\nCould not pin:\n'
            + '\n'.join('- ' + gap for gap in gaps) + '\n')


def render(packet, identity=None):
    slots = validate(packet, identity)
    result = SLOT.sub(lambda match: slots[match[1]], packet['template'])
    result += '\n\n' + integrity_report(packet, slots)
    if packet.get('issue_body') is not None:
        result += '\n\n## Complete issue body (quoted evidence)\n' + packet['issue_body']
    if packet.get('rebase_result') is not None:
        result += ('\n\n## Rebase comparison result (evidence only; full review still applies)\n'
                   + json.dumps(packet['rebase_result'], indent=2) + '\n')
    for prior in packet.get('prior_verdicts', []):
        result += '\n\n## Prior returned verdict (historical evidence, verbatim)\n' + prior
    return result


def decode(text):
    if text.lstrip().startswith('{'):
        return json.loads(text)
    return None
