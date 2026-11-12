#!/usr/bin/env python3
"""H2 Unified Video Studio — minimal local-first dashboard for two licensed H2 packs.
No third-party Python dependencies for the UI. Rendering uses the original toolchain.
Bind only to loopback. Do not expose to the public Internet.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

if os.name == 'nt' and not shutil.which('ffmpeg'):
    try:
        import winreg
        _extra = []
        for _root, _sub in ((winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
                            (winreg.HKEY_CURRENT_USER, r'Environment')):
            try:
                with winreg.OpenKey(_root, _sub) as _k:
                    _val, _ = winreg.QueryValueEx(_k, 'Path')
                    _extra.extend(os.path.expandvars(p) for p in _val.split(os.pathsep) if p)
            except OSError:
                pass
        _cur = os.environ.get('PATH', '').split(os.pathsep)
        _add = [p for p in _extra if p and p not in _cur]
        if _add:
            os.environ['PATH'] = os.pathsep.join(_add + _cur)
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / 'projects'
WEB = ROOT / 'web'
JOBS_DIR = ROOT / '.studio' / 'jobs'
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS.mkdir(parents=True, exist_ok=True)
ALLOWED_MODES = {'dem': 'Self-Improvement', 'squire': 'Military History'}
PACK_TEMPLATES = {
    'squire': {'scene', 'army', 'close', 'top', 'map', 'plan', 'board', 'xray', 'frame', 'item', 'split', 'title', 'black'},
    'dem': {'scene', 'phone', 'clock', 'calendar', 'note', 'face', 'black', 'card', 'cta', 'stats'},
    'doodle': {'sketch', 'story', 'split', 'map', 'title', 'focus'}
}
NAME = re.compile(r'^[a-z0-9][a-z0-9_-]{1,49}$')
JOBS: dict[str, dict] = {}
MUTEX = threading.Lock()


def invalidate_artifacts(p: Path):
    """Xoa cac file render/mix cu khi kich ban hoac storyboard thay doi."""
    for f in (p / 'build' / 'video_silent.mp4', p / 'build' / 'video_silent.mp4.partial',
              p / 'build' / 'preview.mp4', p / 'build' / 'preview_silent.mp4',
              p / 'build' / 'mix.wav', p / 'build' / 'mix_raw.wav', p / 'build' / 'mix_ln.wav'):
        if f.exists():
            try: f.unlink()
            except OSError: pass
    out_dir = p / 'out'
    if out_dir.is_dir():
        for mp4 in out_dir.glob('*.mp4'):
            try: mp4.unlink()
            except OSError: pass


def project_path(name: str) -> Path:
    if not NAME.fullmatch(name):
        raise ValueError('Project ID must be 2–50 characters: a-z, 0-9, dash, underscore.')
    p = (PROJECTS / name).resolve()
    if not p.is_relative_to(PROJECTS.resolve()):
        raise ValueError('Unsafe project path')
    return p


def load_json(p: Path, default=None):
    if not p.is_file(): return default
    with p.open(encoding='utf-8') as f: return json.load(f)


def put_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    with t.open('w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    t.replace(p)


def available_files(p: Path):
    out = []
    for folder in ('build/sheets', 'build', 'out'):
        q = p / folder
        if q.is_dir():
            for f in q.iterdir():
                if f.is_file() and f.suffix.lower() in {'.jpg', '.png', '.mp4', '.wav'}:
                    out.append({'name': f.name, 'path': f.relative_to(p).as_posix(), 'size': f.stat().st_size})
    return out


def summarize_project(p: Path):
    cfg = load_json(p / 'config.json', {}) or {}
    story = load_json(p / 'story' / 'shots.json', {}) or {}
    shots = story.get('shots', [])
    mode = cfg.get('pack', '')

    known_tpls = PACK_TEMPLATES.get(mode, set())
    custom_shots = set()
    s_dir = p / 'scenes' / 'shots'
    if s_dir.is_dir():
        custom_shots = {f.stem for f in s_dir.glob('*.js')}

    shots_ready = 0
    missing_shots = []
    for s in shots:
        sid = s.get('id', '')
        tpl = s.get('tpl', '')
        if sid in custom_shots or (tpl and tpl in known_tpls):
            shots_ready += 1
        else:
            missing_shots.append(sid)

    visuals_ready = len(shots) > 0 and shots_ready == len(shots)

    if len(shots) == 0:
        if mode == 'squire':
            has_voice = (p / 'timeline' / 'voice.wav').exists() or (p / 'input' / 'voice_source.wav').exists() or (p / 'input' / 'voice_source.mp3').exists()
            stage = 'NEED_SHOTS' if has_voice else 'EMPTY'
        else:
            has_script = (p / 'input' / '01-PHIM.txt').exists()
            stage = 'NEED_SHOTS' if has_script else 'EMPTY'
    elif not visuals_ready:
        stage = 'NEED_VISUALS'
    elif list((p / 'out').glob('*.mp4')):
        stage = 'OUTPUT_VERIFIED'
    elif (p / 'build' / 'video_silent.mp4').exists():
        stage = 'RENDER_DONE'
    else:
        stage = 'VISUALS_READY'

    return {'id': p.name, 'title': cfg.get('title', p.name), 'mode': mode,
            'aspect': cfg.get('aspect', '16:9'), 'resolution': cfg.get('resolution', '1080p'),
            'duration': story.get('duration', cfg.get('duration', 0)),
            'shots': len(shots), 'shots_ready': shots_ready,
            'visuals_ready': visuals_ready, 'missing_shots': missing_shots,
            'stage': stage, 'files': available_files(p)}


def ensure_project(p: Path):
    if not p.is_dir() or not (p / 'config.json').is_file():
        raise ValueError('Project does not exist')
    cfg = load_json(p / 'config.json', {})
    if cfg.get('pack') not in ALLOWED_MODES:
        raise ValueError('Only the two supported studio packs can be used in the dashboard')
    return cfg


def create_project(body):
    name = str(body.get('id', '')).strip().lower()
    mode = str(body.get('mode', ''))
    if mode not in ALLOWED_MODES: raise ValueError('Choose self-improvement or military history')
    p = project_path(name)
    if p.exists(): raise ValueError('Project ID already exists')
    aspect = body.get('aspect', '16:9')
    if aspect not in ('16:9', '9:16'): raise ValueError('Invalid aspect ratio')
    copy_sample = bool(body.get('copy_sample', True))
    if copy_sample:
        sample = PROJECTS / ('selfimprove-mau' if mode == 'dem' else 'squire-mau')
        shutil.copytree(sample, p)
    else:
        for d in ['input', 'anh', 'timeline', 'story', 'scenes/sets', 'scenes/shots', 'build', 'out']:
            (p / d).mkdir(parents=True, exist_ok=True)
        put_json(p / 'story' / 'shots.json', {'duration': 0, 'shots': []})
    cfg = load_json(p / 'config.json', {}) or {}
    title = str(body.get('title', '')).strip()[:140] or name
    cfg.update({'title': title, 'pack': mode, 'aspect': aspect, 'resolution': '1080p',
                'fps': 24, 'lang': 'en', 'captions': (mode == 'squire' and aspect == '9:16')})
    cfg.setdefault('style', 'flat')
    cfg.setdefault('music', {'enabled': True, 'gainDb': -15})
    cfg.setdefault('sfx', {'enabled': True, 'gainDb': -4})
    cfg.setdefault('loudness', -14)
    put_json(p / 'config.json', cfg)
    return summarize_project(p)


def status():
    def exists(cmd): return bool(shutil.which(cmd))
    try:
        import importlib.util
        libs = {p: importlib.util.find_spec(p) is not None for p in ('numpy', 'scipy', 'soundfile')}
    except Exception: libs = {}
    return {'python': sys.version.split()[0], 'node': exists('node'), 'npm': exists('npm'),
            'ffmpeg': exists('ffmpeg'), 'ffprobe': exists('ffprobe'),
            'node_modules': (ROOT / 'node_modules' / 'playwright').exists(),
            'python_libraries': libs,
            'music_ready': len(list((ROOT / 'audio' / 'music').glob('*.wav'))) >= 6,
            'sfx_ready': len(list((ROOT / 'audio' / 'sfx').glob('*.wav'))) >= 30,
            'host': '127.0.0.1'}


def task_commands(action, p: Path):
    proj = str(p)
    node = shutil.which('node') or 'node'
    py = sys.executable
    story = load_json(p / 'story' / 'shots.json', {}) or {}
    shots = story.get('shots', [])

    if action == 'check': return [[node, 'render.mjs', '--project', proj, '--check', '--scale', '0.25']]
    if action in ('sheet', 'preview', 'render'):
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi render.')
        if action == 'sheet': return [[node, 'render.mjs', '--project', proj, '--sheet', '--scale', '0.4']]
        if action == 'preview': return [[node, 'render.mjs', '--project', proj, '--from', '0', '--to', '30', '--scale', '0.5', '--workers', '2']]
        if action == 'render': return [[node, 'render.mjs', '--project', proj, '--workers', '2']]
    if action == 'thumb': return [[node, 'render.mjs', '--project', proj, '--thumb']]
    if action == 'mix':
        if not (p / 'build' / 'video_silent.mp4').exists():
            raise ValueError('Chưa có build/video_silent.mp4. Hãy render video trước khi mix & export.')
        return [[py, 'tools/mix.py', '--project', proj]]
    if action == 'doctor': return [[py, 'tools/doctor.py']]
    if action == 'audio-build': return [[py, 'audio/build_audio.py']]
    if action == 'compile-self':
        if ensure_project(p).get('pack') != 'dem': raise ValueError('Self-Improvement projects only')
        script = p / 'input' / '01-PHIM.txt'
        if not script.exists(): raise ValueError('Save a script before compiling it')
        invalidate_artifacts(p)
        return [[py, 'tools/phim.py', '--project', proj, '--phim', str(script), '--force']]
    if action == 'voice-prepare':
        if ensure_project(p).get('pack') != 'squire': raise ValueError('Squire projects only')
        voice = p / 'input' / 'voice_source.mp3'
        if not voice.exists(): voice = p / 'input' / 'voice_source.wav'
        script = p / 'input' / 'voice_script.txt'
        if not voice.exists() or not script.exists(): raise ValueError('Upload MP3/WAV and save transcript first')
        invalidate_artifacts(p)
        return [[py, 'tools/prep_voice.py', '--project', proj, '--single', str(voice), '--script', str(script)]]
    if action == 'draft-shots':
        cfg = ensure_project(p)
        if cfg.get('pack') != 'squire': raise ValueError('Squire projects only')
        if not (p / 'timeline' / 'lines.json').exists():
            raise ValueError('Run Prepare voice timeline before drafting storyboard shots')
        invalidate_artifacts(p)
        cmd = [py, 'tools/draft_shots.py', '--project', proj, '--force']
        if cfg.get('aspect') == '9:16': cmd.extend(['--min', '0.8', '--max', '2.6'])
        return [cmd]
    if action == 'assign-visuals':
        cfg = ensure_project(p)
        if cfg.get('pack') != 'squire': raise ValueError('Squire projects only')
        if not (p / 'story' / 'shots.json').exists() or not shots:
            raise ValueError('Draft storyboard (shots) before assigning visuals')
        invalidate_artifacts(p)
        return [[py, 'tools/assign_visuals.py', '--project', proj, '--force']]
    raise ValueError('Unknown task')


def verify_task_result(action: str, p: Path, started: float, log_text: str):
    """Confirm an output actually exists; do not equate exit status with a PASS."""
    if action == 'doctor':
        return (not ('[THIEU]' in log_text or 'Chua du' in log_text), 'Missing prerequisites' if '[THIEU]' in log_text else '')
    if action == 'check':
        bad = ('THIEU ' in log_text or 'LOI NAP FILE' in log_text or
               'LOI:' in log_text or 'LOI CANH' in log_text or 'PREFLIGHT' in log_text or
               '[loi trang]' in log_text or '[404 Required]' in log_text or 'Error:' in log_text)
        return (not bad, 'Renderer reported missing shots/assets or errors' if bad else '')
    if action == 'audio-build':
        healthy = status()
        return (healthy['music_ready'] and healthy['sfx_ready'], 'Expected music or sound effects missing')
    expected = {
        'preview': [p / 'build' / 'preview.mp4'],
        'render': [p / 'build' / 'video_silent.mp4'],
        'thumb': [p / 'out' / 'thumbnail.png'],
        'compile-self': [p / 'story' / 'shots.json'],
        'voice-prepare': [p / 'timeline' / 'voice.wav'],
        'draft-shots': [p / 'story' / 'shots.json'],
        'assign-visuals': [p / 'story' / 'shots.json'],
    }
    if action == 'sheet': matches = list((p / 'build' / 'sheets').glob('sheet_*.jpg'))
    elif action == 'mix': matches = list((p / 'out').glob('*.mp4'))
    else: matches = expected.get(action, [])
    if not matches: return False, 'No expected output file was created'
    good = [f for f in matches if f.is_file() and f.stat().st_size > 100 and f.stat().st_mtime >= started - 2]
    if not good: return False, 'Output not created or is empty/stale'

    # Check for fatal indicators in log for render/preview/sheet/thumb
    if action in ('render', 'preview', 'sheet', 'thumb'):
        if any(w in log_text for w in ('PREFLIGHT GATE: BLOCKED', 'THIEU SHOT', 'LOI CANH', 'Error:', 'Fatal:')):
            return False, 'Log indicates renderer preflight or runtime errors'

    if action in ('preview', 'render', 'mix') and shutil.which('ffprobe'):
        for f in good:
            r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
                                '-of', 'default=noprint_wrappers=1', str(f)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            out_str = r.stdout
            dur_m = re.search(r'duration=([\d.]+)', out_str)
            try: duration = float(dur_m.group(1)) if dur_m else 0
            except ValueError: duration = 0
            if r.returncode == 0 and duration > 0:
                if action == 'mix':
                    cfg = load_json(p / 'config.json', {}) or {}
                    if cfg.get('pack') == 'squire' and 'codec_type=audio' not in out_str:
                        return False, 'Mix output missing audio stream for Squire project'
                return True, ''
        return False, 'FFprobe failed to validate rendered video duration'
    return True, ''


def launch_task(action, project_id):
    p = project_path(project_id)
    ensure_project(p)
    cmds = task_commands(action, p)
    with MUTEX:
        if any(j['state'] == 'running' for j in JOBS.values()):
            raise ValueError('Another job is running. Please finish it before starting a new job.')
        jid = uuid.uuid4().hex[:12]
        job = {'id': jid, 'action': action, 'project': project_id, 'state': 'running',
               'started': time.time(), 'exit_code': None, 'log': f'{jid}.log'}
        JOBS[jid] = job
    def worker():
        ret = 0
        log = JOBS_DIR / job['log']
        try:
            with log.open('w', encoding='utf-8') as f:
                for command in cmds:
                    f.write('$ ' + ' '.join(command) + '\n'); f.flush()
                    process = subprocess.Popen(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                                               stdin=subprocess.DEVNULL)
                    ret = process.wait()
                    if ret: break
        except Exception as exc:
            ret = 1
            with log.open('a', encoding='utf-8') as f: f.write('\nERROR: ' + repr(exc) + '\n')
        if ret == 0:
            try:
                result = verify_task_result(action, p, job['started'], log.read_text('utf-8', errors='replace'))
                if not result[0]:
                    ret = 2
                    with log.open('a', encoding='utf-8') as f:
                        f.write('\nVERIFICATION: ' + result[1] + '\n')
            except Exception as exc:
                ret = 2
                with log.open('a', encoding='utf-8') as f:
                    f.write('\nVERIFICATION ERROR: ' + repr(exc) + '\n')
        with MUTEX:
            job['exit_code'] = ret
            job['state'] = ('completed' if ret == 0 else 'needs_setup' if action == 'doctor' and ret == 2 else 'failed')
            job['ended'] = time.time()
    threading.Thread(target=worker, daemon=True).start()
    return {'id': jid}


class Handler(BaseHTTPRequestHandler):
    server_version = 'H2UnifiedLocal/0.1'

    def send(self, status_code, payload, content_type='application/json; charset=utf-8'):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try: self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError): pass

    def error(self, status_code, msg): self.send(status_code, {'error': str(msg)})

    def parse_parts(self):
        return [unquote(x) for x in urlsplit(self.path).path.strip('/').split('/') if x]

    def body(self, max_size=2_000_000):
        length = int(self.headers.get('Content-Length', '0'))
        if length < 0 or length > max_size: raise ValueError('Request body exceeds allowed size')
        return self.rfile.read(length)

    def data(self):
        try: return json.loads(self.body().decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as exc: raise ValueError('Expected valid JSON') from exc

    def do_GET(self):
        parts = self.parse_parts()
        try:
            if not parts or parts == ['index.html']:
                return self.send(200, (WEB / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            if parts == ['api', 'status']:
                return self.send(200, status())
            if parts == ['api', 'projects']:
                return self.send(200, {'projects': [summarize_project(p) for p in sorted(PROJECTS.iterdir())
                                                      if p.is_dir() and (p / 'config.json').exists()]})
            if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                p = project_path(parts[2]); ensure_project(p)
                script = p / 'input' / '01-PHIM.txt'; voice_script = p / 'input' / 'voice_script.txt'
                return self.send(200, {'project': summarize_project(p),
                    'config': load_json(p / 'config.json', {}),
                    'story': load_json(p / 'story' / 'shots.json', {}),
                    'script': script.read_text('utf-8') if script.exists() else '',
                    'voice_script': voice_script.read_text('utf-8') if voice_script.exists() else ''})
            if len(parts) == 3 and parts[:2] == ['api', 'jobs']:
                j = JOBS.get(parts[2]);
                if not j: return self.error(404, 'Job not found')
                log_file = JOBS_DIR / j['log']
                with MUTEX: obj = dict(j)
                obj['log_text'] = log_file.read_text('utf-8', errors='replace')[-28000:] if log_file.exists() else ''
                return self.send(200, obj)
            if len(parts) >= 4 and parts[0] == 'files':
                p = project_path(parts[1]); ensure_project(p)
                rel = Path(*parts[2:]); target = (p / rel).resolve()
                if not target.is_relative_to(p.resolve()) or rel.parts[0] not in ('build', 'out'):
                    return self.error(403, 'File is not public')
                if not target.is_file() or target.suffix.lower() not in ('.jpg', '.png', '.mp4', '.wav'):
                    return self.error(404, 'File not found')
                types = {'.jpg': 'image/jpeg', '.png': 'image/png', '.mp4': 'video/mp4', '.wav': 'audio/wav'}
                return self.send(200, target.read_bytes(), types[target.suffix.lower()])
            self.error(404, 'Unknown endpoint')
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            self.error(400, exc)

    def do_POST(self):
        try:
            origin = self.headers.get('Origin', '')
            if origin and not re.fullmatch(r'http://(?:localhost|127\.0\.0\.1):\d+', origin):
                return self.error(403, 'Only same-machine requests accepted')
            parts = self.parse_parts()
            if parts == ['api', 'projects']:
                return self.send(201, {'project': create_project(self.data())})
            if len(parts) == 4 and parts[:2] == ['api', 'projects']:
                p = project_path(parts[2]); cfg = ensure_project(p); action = parts[3]
                if action == 'task':
                    job = launch_task(self.data().get('action'), parts[2]); return self.send(202, job)
                if action == 'story':
                    data = self.data()
                    if not isinstance(data, dict) or not isinstance(data.get('shots'), list):
                        raise ValueError('Story must be JSON object containing a shots array')
                    if len(data['shots']) > 3000: raise ValueError('Too many shots')
                    put_json(p / 'story' / 'shots.json', data)
                    invalidate_artifacts(p)
                    return self.send(200, {'saved': True})
                if action == 'config':
                    data = self.data()
                    if not isinstance(data, dict): raise ValueError('Config must be object')
                    allowed = ('title','aspect','resolution','fps','captions','accent','music','sfx','loudness')
                    for key in allowed:
                        if key in data: cfg[key] = data[key]
                    cfg['pack'] = ensure_project(p)['pack']
                    if cfg.get('aspect') not in ('16:9','9:16'): raise ValueError('Unsupported aspect')
                    put_json(p / 'config.json', cfg)
                    invalidate_artifacts(p)
                    return self.send(200, {'saved': True})
                if action in ('script', 'voice-script'):
                    data = self.data(); content = data.get('text', '')
                    if not isinstance(content, str) or len(content) > 250_000: raise ValueError('Text too long')
                    file = ('01-PHIM.txt' if action == 'script' else 'voice_script.txt')
                    (p / 'input').mkdir(exist_ok=True)
                    (p / 'input' / file).write_text(content, encoding='utf-8')
                    invalidate_artifacts(p)
                    return self.send(200, {'saved': True})
                if action == 'voice-upload':
                    if cfg['pack'] != 'squire': raise ValueError('Squire projects only')
                    ext = parse_qs(urlsplit(self.path).query).get('ext', [''])[0].lower()
                    if ext not in ('mp3', 'wav'): raise ValueError('Only MP3/WAV accepted')
                    content = self.body(max_size=80_000_000)
                    if not content: raise ValueError('Empty audio file')
                    (p / 'input').mkdir(exist_ok=True)
                    for old in (p / 'input' / 'voice_source.mp3', p / 'input' / 'voice_source.wav'):
                        if old.exists(): old.unlink()
                    (p / 'input' / ('voice_source.' + ext)).write_bytes(content)
                    invalidate_artifacts(p)
                    return self.send(200, {'saved': True, 'bytes': len(content)})
            self.error(404, 'Unknown endpoint')
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            self.error(400, exc)

    def log_message(self, fmt, *args):
        return


def main():
    port = int(os.environ.get('H2_PORT', '7860'))
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'H2 Unified Video Studio: http://127.0.0.1:{port}', flush=True)
    print('Local-only; originals preserved. Press Ctrl+C to stop.', flush=True)
    if '--open' in sys.argv: threading.Timer(0.8, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
