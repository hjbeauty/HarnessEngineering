"""Course-owned deterministic probes. No model calls, network calls, or secret reads.

Run as the image's hermes user. create writes disposable markers and initializes
only /workspace Git metadata; verify never recreates missing markers.
"""
import argparse
import errno
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(mode, workspace=Path('/workspace'), inputs=Path('/inputs'), state=Path('/opt/data')):
    evidence = workspace / 'evidence' / 'lesson02'
    results = []

    def check(label, ok, detail=''):
        results.append({'check': label, 'passed': bool(ok), 'detail': detail})
        print(('PASS' if ok else 'FAIL') + ' ' + label + (': ' + detail if detail else ''))

    def read_exact(path, expected, label):
        try:
            actual = path.read_text(encoding='utf-8').strip()
            check(label, actual == expected, 'expected marker found' if actual == expected else 'marker differs')
        except OSError as exc:
            check(label, False, type(exc).__name__)

    check('linux_runtime', platform.system() == 'Linux', platform.system())
    check('non_root_user', hasattr(os, 'geteuid') and os.geteuid() != 0)
    read_exact(evidence / 'host_marker.txt', 'created-on-windows', 'windows_file_visible')
    read_exact(inputs / 'input_marker.txt', 'provided-by-course', 'input_file_readable')

    # The only attempted input write targets a disposable probe, not course data.
    probe = inputs / 'lesson02_write_probe.tmp'
    if probe.exists():
        check('input_write_blocked', False, 'probe already exists; inspect the read-only mount')
    else:
        try:
            with probe.open('x', encoding='utf-8') as file:
                file.write('disposable course probe\n')
        except OSError as exc:
            check('input_write_blocked', exc.errno == errno.EROFS,
                  'read-only filesystem' if exc.errno == errno.EROFS else f'unexpected errno {exc.errno}')
        else:
            check('input_write_blocked', False, 'input mount is writable; disposable probe retained as evidence')

    markers = [(evidence / 'container_marker.txt', 'created-in-container', 'workspace_marker'),
               (state / 'lesson02_state_marker.txt', 'saved-in-hermes-volume', 'state_volume_marker')]
    for path, value, label in markers:
        if mode == 'create' and not path.exists():
            try:
                with path.open('x', encoding='utf-8') as file:
                    file.write(value + '\n')
            except OSError as exc:
                check(label + '_create', False, type(exc).__name__)
        read_exact(path, value, label)

    def git(*args):
        return subprocess.run(['git', '-c', f'safe.directory={workspace}', '-C', str(workspace), *args],
                              capture_output=True, text=True, timeout=15)

    try:
        if mode == 'create':
            init = git('init')
            check('git_init', init.returncode == 0)
            for key, default in [('user.name', 'student'), ('user.email', 'student@example.com')]:
                previous = git('config', '--local', '--get', key)
                if previous.returncode == 1:
                    saved = git('config', '--local', key, default)
                    check('git_set_' + key, saved.returncode == 0)
            ignore = workspace / '.gitignore'
            text = ignore.read_text(encoding='utf-8-sig') if ignore.exists() else ''
            missing = [x for x in ['.env', '.env.*', '*.key', '__pycache__/', 'evidence/'] if x not in text.splitlines()]
            if missing:
                with ignore.open('a', encoding='utf-8') as file:
                    file.write(('' if not text or text.endswith('\n') else '\n') + '\n'.join(missing) + '\n')
        for key in ['user.name', 'user.email']:
            value = git('config', '--local', '--get', key)
            check('git_' + key, value.returncode == 0 and bool(value.stdout.strip()), 'configured' if value.stdout.strip() else 'missing')
    except (OSError, subprocess.SubprocessError) as exc:
        check('git_ready', False, type(exc).__name__)

    passed = all(row['passed'] for row in results)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'mode': mode,
              'scope': 'environment probes only; no Hermes/model inference was invoked by this script',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'passed': passed, 'results': results}
    try:
        evidence.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        report_path = evidence / f'probe-{mode}-{stamp}.json'
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print('REPORT ' + str(report_path))
    except OSError as exc:
        passed = False
        print('FAIL evidence_write: ' + type(exc).__name__)
    print('ENVIRONMENT_PASS' if passed else 'ENVIRONMENT_FAIL')
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['create', 'verify'])
    sys.exit(run(parser.parse_args().mode))
