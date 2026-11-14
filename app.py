#!/usr/bin/env python3
"""H2 Unified Video Studio — minimal local-first dashboard for two licensed H2 packs.
No third-party Python dependencies for the UI. Rendering uses the original toolchain.
Bind only to loopback. Do not expose to the public Internet.
"""
from __future__ import annotations

import hashlib
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

sys.path.insert(0, str((Path(__file__).resolve().parent / 'tools')))
try:
    from common import compute_canonical_visual_hash, compute_canonical_audio_hash, ensure_ffmpeg
except Exception:
    compute_canonical_visual_hash = None
    compute_canonical_audio_hash = None
    ensure_ffmpeg = lambda: None

if ensure_ffmpeg:
    ensure_ffmpeg()

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / 'projects'
WEB = ROOT / 'web'
JOBS_DIR = ROOT / '.studio' / 'jobs'
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS.mkdir(parents=True, exist_ok=True)
ALLOWED_MODES = {'dem': 'Self-Improvement', 'squire': 'Military History'}
PACK_TEMPLATES = {
    'squire': {'scene', 'army', 'close', 'top', 'map', 'plan', 'board', 'xray', 'frame', 'item', 'split', 'title', 'black', 'ai'},
    'dem': {'scene', 'phone', 'clock', 'calendar', 'note', 'face', 'black', 'card', 'cta'},
    'doodle': {'comp', 'host', 'bighead', 'ai', 'map', 'compare', 'scale', 'measure', 'list', 'note', 'counter', 'timeline', 'chart', 'icons', 'title', 'branch', 'endcard'}
}
NAME = re.compile(r'^[a-z0-9][a-z0-9_-]{1,49}$')
JOBS: dict[str, dict] = {}
PROJECT_LOCKS: set[str] = set()
MUTEX = threading.Lock()

sys.path.insert(0, str(ROOT / 'tools'))
from common import compute_source_hash


class ProjectConflictError(Exception):
    def __init__(self, message, project_id, is_recoverable=False, suggested_id=None):
        super().__init__(message)
        self.project_id = project_id
        self.is_recoverable = is_recoverable
        self.suggested_id = suggested_id


def invalidate_by_change(p: Path, change_type: str, old_data=None, new_data=None):
    """Xoa cac file build trung gian co chon loc theo loai thay doi (P0-B):
    - NO_CHANGE: khong xoa gi.
    - AUDIO_ONLY: xoa build/mix.wav, build/mix.m4a, build/preview.mp4.
      TUYET DOI GIU NGUYEN build/video_silent.mp4 va build/visual_hash.txt!
    - VISUAL_CHANGED: xoa ca video_silent.mp4, visual_hash.txt, preview.mp4, mix.wav.
    - INPUT_CHANGED: xoa ca video va audio vi kich ban/giong doc thay doi toan bo timing.
    Luon giu out/*.mp4 va danh dau STALE trong verification_proof.json.
    """
    scope = 'INPUT_CHANGED'
    if change_type == 'story':
        old_story = old_data or {}
        new_story = new_data or {}
        old_vhash = compute_canonical_visual_hash(str(p), story_data=old_story) if compute_canonical_visual_hash else None
        new_vhash = compute_canonical_visual_hash(str(p), story_data=new_story) if compute_canonical_visual_hash else None
        old_ahash = compute_canonical_audio_hash(str(p), story_data=old_story) if compute_canonical_audio_hash else None
        new_ahash = compute_canonical_audio_hash(str(p), story_data=new_story) if compute_canonical_audio_hash else None

        if old_vhash and new_vhash and old_vhash == new_vhash:
            if old_ahash == new_ahash:
                scope = 'NO_CHANGE'
            else:
                scope = 'AUDIO_ONLY'
        else:
            scope = 'VISUAL_CHANGED'
    elif change_type == 'config':
        old_cfg = old_data or {}
        new_cfg = new_data or {}
        vis_keys = ('resolution', 'aspect', 'fps', 'title')
        aud_keys = ('music', 'sfx', 'loudness')
        vis_changed = any(old_cfg.get(k) != new_cfg.get(k) for k in vis_keys)
        aud_changed = any(old_cfg.get(k) != new_cfg.get(k) for k in aud_keys)
        if vis_changed:
            scope = 'VISUAL_CHANGED'
        elif aud_changed:
            scope = 'AUDIO_ONLY'
        else:
            scope = 'NO_CHANGE'
    else:
        scope = 'INPUT_CHANGED'

    if scope == 'NO_CHANGE':
        return

    # Invalidate audio artifacts always on AUDIO_ONLY, VISUAL_CHANGED, or INPUT_CHANGED
    for f in (p / 'build' / 'mix.wav', p / 'build' / 'mix_raw.wav', p / 'build' / 'mix_ln.wav',
              p / 'build' / 'mix.m4a', p / 'build' / 'preview.mp4', p / 'build' / 'preview.partial.mp4',
              p / 'build' / 'preview_audio.wav', p / 'build' / 'audio_hash.txt'):
        if f.exists():
            try: f.unlink()
            except OSError: pass

    # Invalidate visual artifacts ONLY when visual actually changed or input changed
    if scope in ('VISUAL_CHANGED', 'INPUT_CHANGED'):
        for f in (p / 'build' / 'video_silent.mp4', p / 'build' / 'video_silent.partial.mp4',
                  p / 'build' / 'preview_silent.mp4', p / 'build' / 'preview_silent.partial.mp4',
                  p / 'build' / 'visual_hash.txt', p / 'build' / 'preview_visual_hash.txt',
                  p / 'build' / 'preview_manifest.json'):
            if f.exists():
                try: f.unlink()
                except OSError: pass

    # Luon danh dau proof stale khi co bat ky thay doi nao tren project
    proof_file = p / 'build' / 'verification_proof.json'
    if proof_file.exists():
        try:
            data = json.loads(proof_file.read_text('utf-8'))
            data['status'] = 'STALE'
            data['source_hash'] = 'STALE'
            proof_file.write_text(json.dumps(data, indent=2), 'utf-8')
        except Exception:
            try: proof_file.unlink()
            except OSError: pass


def invalidate_artifacts(p: Path):
    """Backwards compatible alias for full invalidation."""
    invalidate_by_change(p, 'all')


def project_path(name: str) -> Path:
    if not NAME.fullmatch(name):
        raise ValueError('Project ID must be 2–50 characters: a-z, 0-9, dash, underscore.')
    p = (PROJECTS / name).resolve()
    if not p.is_relative_to(PROJECTS.resolve()):
        raise ValueError('Unsafe project path')
    return p


def load_json(p: Path, default=None):
    if not p.is_file(): return default
    try:
        with p.open(encoding='utf-8') as f: return json.load(f)
    except Exception:
        return default


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

    proof = load_json(p / 'build' / 'verification_proof.json', {})
    current_src_hash = compute_source_hash(p)
    out_dir = p / 'out'
    out_mp4s = list(out_dir.glob('*.mp4')) if out_dir.is_dir() else []

    if len(shots) == 0:
        if mode == 'squire':
            has_voice = (p / 'timeline' / 'voice.wav').exists() or (p / 'input' / 'voice_source.wav').exists() or (p / 'input' / 'voice_source.mp3').exists()
            stage = 'NEED_SHOTS' if has_voice else 'EMPTY'
        else:
            has_script = (p / 'input' / '01-PHIM.txt').exists()
            stage = 'NEED_SHOTS' if has_script else 'EMPTY'
    elif not visuals_ready:
        stage = 'NEED_VISUALS'
    elif proof and out_mp4s:
        proof_out_rel = proof.get('output_file')
        proof_out_file = (p / proof_out_rel) if proof_out_rel else None

        if proof.get('status') != 'VERIFIED':
            stage = 'OUTPUT_STALE'
        elif proof.get('source_hash') != current_src_hash:
            stage = 'OUTPUT_STALE'
        elif not proof_out_file or not proof_out_file.is_file():
            stage = 'VERIFICATION_FAILED'
        else:
            try:
                real_out_h = hashlib.sha256()
                with proof_out_file.open('rb') as fp:
                    while chunk := fp.read(65536):
                        real_out_h.update(chunk)
                if real_out_h.hexdigest() == proof.get('output_sha256'):
                    stage = 'OUTPUT_VERIFIED'
                else:
                    stage = 'VERIFICATION_FAILED'
            except Exception:
                stage = 'VERIFICATION_FAILED'
    elif out_mp4s:
        stage = 'OUTPUT_UNVERIFIED'
    elif (p / 'build' / 'video_silent.mp4').exists():
        stage = 'RENDER_DONE'
    else:
        stage = 'VISUALS_READY'

    audio_plan_file = p / 'build' / 'audio_plan.json'
    audio_planned = audio_plan_file.exists() or any(bool(s.get('sfx') or s.get('music')) for s in shots)
    mix_wav = p / 'build' / 'mix.wav'
    audio_mixed = mix_wav.exists()

    audio_status = 'AUDIO_NOT_PLANNED'
    if audio_mixed:
        is_audio_stale = False
        audio_hash_file = p / 'build' / 'audio_hash.txt'
        if audio_hash_file.exists() and compute_canonical_audio_hash:
            try:
                cur_ah = compute_canonical_audio_hash(p, story_data=story, config_data=cfg)
                stored_ah = audio_hash_file.read_text('utf-8').strip()
                if cur_ah != stored_ah:
                    is_audio_stale = True
            except Exception:
                pass
        elif (p / 'story' / 'shots.json').exists() and (p / 'story' / 'shots.json').stat().st_mtime > mix_wav.stat().st_mtime + 2:
            is_audio_stale = True
        audio_status = 'AUDIO_STALE' if is_audio_stale else 'AUDIO_MIXED'
    elif audio_planned:
        audio_status = 'AUDIO_PLANNED'

    hook_diff_file = p / 'build' / 'opening_diff.json'
    hook_rev_file = p / 'build' / 'opening_review.json'
    hook_status = None
    if hook_diff_file.is_file():
        hdata = load_json(hook_diff_file, {}) or {}
        hook_status = hdata.get('status')
    elif hook_rev_file.is_file():
        hdata = load_json(hook_rev_file, {}) or {}
        hook_status = hdata.get('validation', {}).get('editorial_state')

    battle_rev_file = p / 'build' / 'battle_review.json'
    battle_status = 'NOT_APPLICABLE' if mode != 'squire' else 'NOT_PLANNED'
    battle_events_count = 0
    battle_changed_shots = 0
    if battle_rev_file.is_file():
        bdata = load_json(battle_rev_file, {}) or {}
        battle_status = bdata.get('status', 'REVIEWED')
        battle_events_count = bdata.get('events_count', 0)
        battle_changed_shots = bdata.get('changed_shots_count', 0)
    elif story.get('battle_choreo_status'):
        battle_status = story.get('battle_choreo_status')

    return {'id': p.name, 'title': cfg.get('title', p.name), 'mode': mode,
            'aspect': cfg.get('aspect', '16:9'), 'resolution': cfg.get('resolution', '1080p'),
            'duration': story.get('duration', cfg.get('duration', 0)),
            'shots': len(shots), 'shots_ready': shots_ready,
            'visuals_ready': visuals_ready, 'missing_shots': missing_shots,
            'audio_planned': audio_planned, 'audio_mixed': audio_mixed,
            'audio_status': audio_status,
            'hook_status': hook_status,
            'battle_status': battle_status,
            'battle_events_count': battle_events_count,
            'battle_changed_shots': battle_changed_shots,
            'stage': stage, 'files': available_files(p)}


def ensure_project(p: Path):
    if not p.is_dir() or not (p / 'config.json').is_file():
        raise ValueError('Project does not exist')
    cfg = load_json(p / 'config.json', {})
    if cfg.get('pack') not in ALLOWED_MODES:
        raise ValueError('Only the two supported studio packs can be used in the dashboard')
    return cfg


def scan_projects():
    valid = []
    recoverable = []
    for p in sorted(PROJECTS.iterdir()):
        if not p.is_dir() or p.name.startswith('.'):
            continue
        cfg_file = p / 'config.json'
        if cfg_file.is_file():
            cfg = load_json(cfg_file, {})
            if isinstance(cfg, dict) and cfg.get('pack') in ALLOWED_MODES:
                try:
                    valid.append(summarize_project(p))
                    continue
                except Exception:
                    pass

        has_voice = (p / 'timeline' / 'voice.wav').exists() or (p / 'input' / 'voice_source.wav').exists() or (p / 'input' / 'voice_source.mp3').exists() or (p / 'input' / 'voice_script.txt').exists()
        has_script = (p / 'input' / '01-PHIM.txt').exists()
        has_story = (p / 'story' / 'shots.json').exists()
        pack_hint = 'squire' if has_voice else ('dem' if has_script else 'squire')

        file_count = 0
        try:
            for sub in p.rglob('*'):
                if sub.is_file():
                    file_count += 1
        except Exception:
            pass

        recoverable.append({
            'id': p.name,
            'title': p.name.replace('_', ' ').replace('-', ' ').title(),
            'pack_hint': pack_hint,
            'has_voice': has_voice,
            'has_script': has_script,
            'has_story': has_story,
            'file_count': file_count,
            'status': 'RECOVERABLE' if file_count > 0 else 'EMPTY_ORPHAN'
        })
    return valid, recoverable


def recover_project(name: str, pack: str = None, title: str = None, aspect: str = '16:9'):
    p = project_path(name)
    if not p.is_dir():
        raise ValueError(f'Thư mục dự án "{name}" không tồn tại trên đĩa.')

    cfg_file = p / 'config.json'
    cfg = load_json(cfg_file, {}) or {}

    if not pack:
        if cfg.get('pack') in ALLOWED_MODES:
            pack = cfg['pack']
        elif (p / 'timeline' / 'voice.wav').exists() or (p / 'input' / 'voice_source.wav').exists() or (p / 'input' / 'voice_source.mp3').exists() or (p / 'input' / 'voice_script.txt').exists():
            pack = 'squire'
        elif (p / 'input' / '01-PHIM.txt').exists():
            pack = 'dem'
        else:
            pack = 'squire'

    if pack not in ALLOWED_MODES:
        raise ValueError('Invalid studio pack for recovery')

    if aspect not in ('16:9', '9:16'):
        aspect = cfg.get('aspect', '16:9')

    if not title:
        title = cfg.get('title') or name.replace('_', ' ').replace('-', ' ').title()

    cfg.update({
        'title': title,
        'pack': pack,
        'aspect': aspect,
        'resolution': cfg.get('resolution', '1080p'),
        'fps': cfg.get('fps', 24),
        'lang': cfg.get('lang', 'en'),
        'captions': cfg.get('captions', (pack == 'squire' and aspect == '9:16'))
    })
    cfg.setdefault('style', 'flat')
    cfg.setdefault('music', {'enabled': True, 'gainDb': -15})
    cfg.setdefault('sfx', {'enabled': True, 'gainDb': -4})
    cfg.setdefault('loudness', -14)

    for d in ['input', 'anh', 'timeline', 'story', 'scenes/sets', 'scenes/shots', 'build', 'out']:
        (p / d).mkdir(parents=True, exist_ok=True)

    put_json(cfg_file, cfg)

    story_file = p / 'story' / 'shots.json'
    if not story_file.is_file():
        put_json(story_file, {'duration': 0, 'shots': []})

    return summarize_project(p)


def create_project(body):
    name = str(body.get('id', '')).strip().lower()
    mode = str(body.get('mode', ''))
    if mode not in ALLOWED_MODES: raise ValueError('Choose self-improvement or military history')
    p = project_path(name)
    if p.exists():
        is_rec = not (p / 'config.json').is_file()
        counter = 2
        suggested_id = f"{name}_{counter}"
        while (PROJECTS / suggested_id).exists():
            counter += 1
            suggested_id = f"{name}_{counter}"
        raise ProjectConflictError(
            f'Thư mục dự án "{name}" đã tồn tại trên đĩa.',
            project_id=name,
            is_recoverable=is_rec,
            suggested_id=suggested_id
        )
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
    if ensure_ffmpeg:
        ensure_ffmpeg()
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


def task_commands(action, p: Path, params: dict = None):
    params = params or {}
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
        if action == 'preview':
            from_sec = str(params.get('from', 0))
            to_sec = str(params.get('to', 30))
            scale = str(params.get('scale', '0.5'))
            return [[node, 'render.mjs', '--project', proj, '--from', from_sec, '--to', to_sec, '--scale', scale]]
        if action == 'render': return [[node, 'render.mjs', '--project', proj]]
    if action == 'thumb': return [[node, 'render.mjs', '--project', proj, '--thumb']]
    if action == 'review-opening':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi review opening.')
        dur = float(story.get('duration', 30.0))
        op_to = str(min(30.0, dur) if dur > 0 else 30.0)
        return [
            [py, 'tools/plan_hook.py', '--project', proj, '--review'],
            [node, 'render.mjs', '--project', proj, '--from', '0', '--to', op_to, '--scale', '0.5'],
            [py, 'tools/mix.py', '--project', proj, '--preview', '--from-sec', '0', '--to-sec', op_to]
        ]
    if action == 'enhance-opening':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi enhance opening.')
        return [[py, 'tools/plan_hook.py', '--project', proj, '--apply-hook']]
    if action == 'review-battle':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi review battle.')
        if ensure_project(p).get('pack') != 'squire':
            raise ValueError('Battle Choreography chỉ hỗ trợ pack Squire.')
        return [[py, 'tools/battle_choreo.py', '--project', proj, '--review']]
    if action == 'apply-battle':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi apply battle.')
        if ensure_project(p).get('pack') != 'squire':
            raise ValueError('Battle Choreography chỉ hỗ trợ pack Squire.')
        return [[py, 'tools/battle_choreo.py', '--project', proj, '--apply']]
    if action == 'preview-battle':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi preview battle.')
        if ensure_project(p).get('pack') != 'squire':
            raise ValueError('Battle Choreography chỉ hỗ trợ pack Squire.')
        dur = float(story.get('duration', 30.0))
        op_to = str(min(30.0, dur) if dur > 0 else 30.0)
        return [
            [node, 'render.mjs', '--project', proj, '--from', '0', '--to', op_to, '--scale', '0.5'],
            [py, 'tools/mix.py', '--project', proj, '--preview', '--from-sec', '0', '--to-sec', op_to]
        ]
    if action == 'validate-battle':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi validate battle.')
        return [[py, 'tools/battle_choreo.py', '--project', proj, '--validate-only']]
    if action == 'plan-audio':
        return [[py, 'tools/plan_audio.py', '--project', proj]]
    if action == 'upgrade-generated-audio':
        return [[py, 'tools/plan_audio.py', '--project', proj, '--upgrade-generated']]
    if action == 'preview-audio':
        if not shots:
            raise ValueError('Chưa có storyboard (0 shots). Vui lòng chuẩn bị kịch bản/visuals trước khi render.')
        from_sec = str(params.get('from', 0))
        to_sec = str(params.get('to', 30))
        scale = str(params.get('scale', '0.5'))
        return [
            [node, 'render.mjs', '--project', proj, '--from', from_sec, '--to', to_sec, '--scale', scale],
            [py, 'tools/mix.py', '--project', proj, '--preview', '--from-sec', from_sec, '--to-sec', to_sec]
        ]
    if action == 'mix':
        silent_file = p / 'build' / 'video_silent.mp4'
        if not silent_file.exists():
            raise ValueError('Chưa có build/video_silent.mp4. Hãy render video trước khi mix & export.')
        shots_file = p / 'story' / 'shots.json'
        cfg_file = p / 'config.json'
        hash_file = p / 'build' / 'visual_hash.txt'
        silent_mtime = silent_file.stat().st_mtime
        
        visual_matches = False
        if hash_file.exists() and shots_file.exists() and compute_canonical_visual_hash:
            try:
                current_vhash = compute_canonical_visual_hash(p)
                stored_vhash = hash_file.read_text(encoding="utf-8").strip()
                visual_matches = (current_vhash == stored_vhash)
            except Exception:
                pass

        if not visual_matches:
            if (shots_file.exists() and shots_file.stat().st_mtime > silent_mtime + 2) or \
               (cfg_file.exists() and cfg_file.stat().st_mtime > silent_mtime + 2):
                raise ValueError('STALE_OUTPUT: build/video_silent.mp4 cũ hơn storyboard hoặc config hiện tại. Vui lòng render video lại trước khi mix & export.')
        return [[py, 'tools/mix.py', '--project', proj]]
    if action == 'doctor': return [[py, 'tools/doctor.py']]
    if action == 'audio-build': return [[py, 'audio/build_audio.py']]
    if action in ('compile-self', 'compile-self-force'):
        if ensure_project(p).get('pack') != 'dem': raise ValueError('Self-Improvement projects only')
        script = p / 'input' / '01-PHIM.txt'
        if not script.exists(): raise ValueError('Save a script before compiling it')
        cmd = [py, 'tools/phim.py', '--project', proj, '--phim', str(script)]
        if action == 'compile-self-force': cmd.append('--force')
        return [cmd]
    if action == 'voice-prepare':
        if ensure_project(p).get('pack') != 'squire': raise ValueError('Squire projects only')
        voice = p / 'input' / 'voice_source.mp3'
        if not voice.exists(): voice = p / 'input' / 'voice_source.wav'
        script = p / 'input' / 'voice_script.txt'
        if not voice.exists() or not script.exists(): raise ValueError('Upload MP3/WAV and save transcript first')
        return [[py, 'tools/prep_voice.py', '--project', proj, '--single', str(voice), '--script', str(script)]]
    if action in ('draft-shots', 'draft-shots-force'):
        cfg = ensure_project(p)
        if cfg.get('pack') != 'squire': raise ValueError('Squire projects only')
        if not (p / 'timeline' / 'lines.json').exists():
            raise ValueError('Run Prepare voice timeline before drafting storyboard shots')
        cmd = [py, 'tools/draft_shots.py', '--project', proj]
        if action == 'draft-shots-force': cmd.append('--force')
        if cfg.get('aspect') == '9:16': cmd.extend(['--min', '0.8', '--max', '2.6'])
        return [cmd]
    if action in ('assign-visuals', 'assign-visuals-force'):
        cfg = ensure_project(p)
        if cfg.get('pack') != 'squire': raise ValueError('Squire projects only')
        if not (p / 'story' / 'shots.json').exists() or not shots:
            raise ValueError('Draft storyboard (shots) before assigning visuals')
        cmd = [py, 'tools/assign_visuals.py', '--project', proj]
        if action == 'assign-visuals-force': cmd.append('--force')
        return [cmd]
    if action in ('upgrade-visuals', 'upgrade-visuals-force'):
        cfg = ensure_project(p)
        if cfg.get('pack') != 'squire': raise ValueError('Squire projects only')
        if not (p / 'story' / 'shots.json').exists() or not shots:
            raise ValueError('Draft storyboard (shots) before upgrading visuals')
        cmd = [py, 'tools/assign_visuals.py', '--project', proj, '--upgrade-generated']
        if action == 'upgrade-visuals-force': cmd.append('--force')
        return [cmd]
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
    if action in ('plan-audio', 'upgrade-generated-audio'):
        plan_file = p / 'build' / 'audio_plan.json'
        shots_file = p / 'story' / 'shots.json'
        if not shots_file.is_file() or not plan_file.is_file():
            return False, 'Audio plan or shots.json was not created'
        try:
            plan_data = load_json(plan_file, {})
            if not isinstance(plan_data, dict):
                return False, 'Invalid audio_plan.json schema'
            status_val = plan_data.get('status', '')
            if status_val not in ('AUDIO_PLAN_PASS', 'NO_CHANGE', 'AUDIO_PLANNED'):
                return False, f'Audio planner reported non-pass status: {status_val}'
            planned_at = float(plan_data.get('planned_at', 0))
            if planned_at > 0 and planned_at < started - 2:
                return False, f'audio_plan.json is stale (planned_at: {planned_at} < started: {started})'
            return True, ''
        except Exception as exc:
            return False, f'Failed to parse audio_plan.json: {exc}'

    if action == 'review-opening':
        rev_file = p / 'build' / 'opening_review.json'
        prev_file = p / 'build' / 'preview.mp4'
        if not rev_file.is_file() or rev_file.stat().st_mtime < started - 2:
            return False, 'build/opening_review.json was not created or is stale'
        if not prev_file.is_file() or prev_file.stat().st_size < 1000 or prev_file.stat().st_mtime < started - 2:
            return False, 'build/preview.mp4 for opening was not created or is empty/stale'
        if shutil.which('ffprobe'):
            r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
                                '-of', 'default=noprint_wrappers=1', str(prev_file)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if r.returncode != 0 or 'codec_type=video' not in r.stdout:
                return False, 'Preview output missing video stream'
            dur_m = re.search(r'duration=([\d.]+)', r.stdout)
            dur_val = float(dur_m.group(1)) if dur_m else 0
            if dur_val <= 0:
                return False, 'Preview video has invalid zero duration'
        return True, ''

    if action == 'enhance-opening':
        rev_file = p / 'build' / 'opening_review.json'
        diff_file = p / 'build' / 'opening_diff.json'
        shots_file = p / 'story' / 'shots.json'
        if not rev_file.is_file() and not diff_file.is_file():
            return False, 'Opening review or diff metadata was not generated'
        diff_data = load_json(diff_file, {}) or {}
        status_val = diff_data.get('status', '')
        if status_val == 'ENHANCED':
            if diff_data.get('changed_shots_count', 0) <= 0:
                return False, 'Enhance reported status ENHANCED but changed_shots_count is 0'
            if shots_file.is_file() and shots_file.stat().st_mtime < started - 2:
                return False, 'shots.json was not updated with compiled hook parameters'
            return True, ''
        elif status_val in ('NO_RENDERABLE_CHANGE', 'MANUAL_PROTECTED', 'HOOK_QA_PASS'):
            return True, ''
        return False, f'Opening enhance reported unrecognized status: {status_val}'

    if action == 'preview-audio':
        prev_file = p / 'build' / 'preview.mp4'
        if not prev_file.is_file() or prev_file.stat().st_size < 1000 or prev_file.stat().st_mtime < started - 2:
            return False, 'build/preview.mp4 with audio was not created or is empty/stale'
        if shutil.which('ffprobe'):
            r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
                                '-of', 'default=noprint_wrappers=1', str(prev_file)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if r.returncode != 0 or 'codec_type=audio' not in r.stdout or 'codec_type=video' not in r.stdout:
                return False, 'Preview output missing video or audio stream'
            dur_m = re.search(r'duration=([\d.]+)', r.stdout)
            dur_val = float(dur_m.group(1)) if dur_m else 0
            if dur_val <= 0:
                return False, 'Preview video has invalid zero duration'
        return True, ''

    if action == 'review-battle':
        rev_file = p / 'build' / 'battle_review.json'
        if not rev_file.is_file() or rev_file.stat().st_mtime < started - 2:
            return False, 'build/battle_review.json was not created or is stale'
        rev_data = load_json(rev_file, {}) or {}
        if rev_data.get('status') not in ('REVIEWED', 'NOT_APPLICABLE', 'NOT_BATTLE'):
            return False, f"Battle review reported unexpected status: {rev_data.get('status')}"
        return True, ''

    if action == 'apply-battle':
        diff_file = p / 'build' / 'battle_diff.json'
        rev_file = p / 'build' / 'battle_review.json'
        shots_file = p / 'story' / 'shots.json'
        if not diff_file.is_file() and not rev_file.is_file():
            return False, 'Battle diff or review metadata was not generated'
        diff_data = load_json(diff_file, {}) or {}
        status_val = diff_data.get('status', '')
        if status_val in ('APPLIED', 'NOT_BATTLE', 'NO_CHANGE', 'MANUAL_PROTECTED', 'VALIDATED'):
            if status_val == 'APPLIED' and shots_file.is_file() and shots_file.stat().st_mtime < started - 2:
                return False, 'shots.json was not updated with compiled battle choreography'
            return True, ''
        return False, f'Battle apply reported unrecognized status: {status_val}'

    if action == 'preview-battle':
        prev_file = p / 'build' / 'preview.mp4'
        if not prev_file.is_file() or prev_file.stat().st_size < 1000 or prev_file.stat().st_mtime < started - 2:
            return False, 'build/preview.mp4 for battle opening was not created or is empty/stale'
        if shutil.which('ffprobe'):
            r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type',
                                '-of', 'default=noprint_wrappers=1', str(prev_file)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if r.returncode != 0 or 'codec_type=video' not in r.stdout:
                return False, 'Preview output missing video stream'
            dur_m = re.search(r'duration=([\d.]+)', r.stdout)
            dur_val = float(dur_m.group(1)) if dur_m else 0
            if dur_val <= 0:
                return False, 'Preview video has invalid zero duration'
        return True, ''

    if action == 'validate-battle':
        rev_file = p / 'build' / 'battle_review.json'
        if not rev_file.is_file() or rev_file.stat().st_mtime < started - 2:
            return False, 'build/battle_review.json was not created or is stale'
        rev_data = load_json(rev_file, {}) or {}
        if not rev_data.get('causality_valid', False):
            return False, f"Battle validation failed causality checks: {rev_data.get('causality_issues')}"
        return True, ''

    expected = {
        'preview': [p / 'build' / 'preview.mp4'],
        'render': [p / 'build' / 'video_silent.mp4'],
        'thumb': [p / 'out' / 'thumbnail.png'],
        'compile-self': [p / 'story' / 'shots.json'],
        'voice-prepare': [p / 'timeline' / 'voice.wav'],
        'draft-shots': [p / 'story' / 'shots.json'],
        'assign-visuals': [p / 'story' / 'shots.json'],
        'upgrade-visuals': [p / 'story' / 'shots.json'],
    }
    if action == 'sheet':
        matches = list((p / 'build' / 'sheets').glob('sheet_*.jpg'))
    elif action == 'mix':
        cfg = load_json(p / 'config.json', {}) or {}
        title = re.sub(r'[\\/:*?"<>|]', '', cfg.get('title', 'video')).strip() or 'video'
        exact_mp4 = p / 'out' / f'{title}.mp4'
        if exact_mp4.is_file():
            matches = [exact_mp4]
        else:
            matches = list((p / 'out').glob('*.mp4'))
    else:
        matches = expected.get(action, [])
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
                    report_file = p / 'build' / 'audio_mix_report.json'
                    if not report_file.exists():
                        return False, 'Missing build/audio_mix_report.json'
                    try:
                        rep = load_json(report_file, {})
                        if rep.get('status') != 'AUDIO_MIX_PASS':
                            return False, f'Audio mix report status is not pass: {rep.get("status")}'
                    except Exception:
                        pass
                return True, ''
        return False, 'FFprobe failed to validate rendered video duration'
    return True, ''


def launch_task(action, project_id, params: dict = None):
    p = project_path(project_id)
    ensure_project(p)
    cmds = task_commands(action, p, params=params)
    with MUTEX:
        if project_id in PROJECT_LOCKS:
            raise ValueError(f'Project "{project_id}" is currently running another task. Please wait.')
        if any(j['state'] == 'running' for j in JOBS.values()):
            raise ValueError('Another job is running. Please finish it before starting a new job.')
        PROJECT_LOCKS.add(project_id)
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
            PROJECT_LOCKS.discard(project_id)
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
                valid, rec = scan_projects()
                return self.send(200, {'projects': valid, 'recoverable': rec})
            if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                p = project_path(parts[2]); ensure_project(p)
                script = p / 'input' / '01-PHIM.txt'; voice_script = p / 'input' / 'voice_script.txt'
                return self.send(200, {'project': summarize_project(p),
                    'config': load_json(p / 'config.json', {}),
                    'story': load_json(p / 'story' / 'shots.json', {}),
                    'script': script.read_text('utf-8') if script.exists() else '',
                    'voice_script': voice_script.read_text('utf-8') if voice_script.exists() else '',
                    'battle_review': load_json(p / 'build' / 'battle_review.json', None),
                    'battle_diff': load_json(p / 'build' / 'battle_diff.json', None)})
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
                mime = types[target.suffix.lower()]
                size = target.stat().st_size
                range_header = self.headers.get('Range')
                if range_header and range_header.startswith('bytes=') and target.suffix.lower() in ('.mp4', '.wav'):
                    try:
                        rng = range_header[6:].split('-')
                        start = int(rng[0]) if rng[0] else 0
                        end = int(rng[1]) if len(rng) > 1 and rng[1] else size - 1
                        if start >= size or end >= size or start > end:
                            self.send_response(416)
                            self.send_header('Content-Range', f'bytes */{size}')
                            self.end_headers()
                            return
                        content_len = end - start + 1
                        self.send_response(206)
                        self.send_header('Content-Type', mime)
                        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                        self.send_header('Content-Length', str(content_len))
                        self.send_header('Accept-Ranges', 'bytes')
                        self.end_headers()
                        with target.open('rb') as f:
                            f.seek(start)
                            rem = content_len
                            while rem > 0:
                                chunk = f.read(min(65536, rem))
                                if not chunk: break
                                self.wfile.write(chunk)
                                rem -= len(chunk)
                        return
                    except (ValueError, OSError):
                        pass

                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(size))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                with target.open('rb') as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk: break
                        self.wfile.write(chunk)
                return
            self.error(404, 'Unknown endpoint')
        except ProjectConflictError as exc:
            self.send(409, {
                'error': str(exc),
                'conflict': True,
                'project_id': exc.project_id,
                'is_recoverable': exc.is_recoverable,
                'suggested_id': exc.suggested_id
            })
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
            if parts == ['api', 'projects', 'recover']:
                d = self.data()
                proj = recover_project(d.get('id', ''), pack=d.get('pack'), title=d.get('title'), aspect=d.get('aspect', '16:9'))
                return self.send(200, {'project': proj, 'recovered': True})
            if len(parts) == 4 and parts[:2] == ['api', 'projects']:
                p = project_path(parts[2]); cfg = ensure_project(p); action = parts[3]
                if action == 'task':
                    data = self.data()
                    job = launch_task(data.get('action'), parts[2], params=data)
                    return self.send(202, job)
                if action == 'story':
                    data = self.data()
                    if not isinstance(data, dict) or not isinstance(data.get('shots'), list):
                        raise ValueError('Story must be JSON object containing a shots array')
                    if len(data['shots']) > 3000: raise ValueError('Too many shots')
                    old_story = load_json(p / 'story' / 'shots.json', {})
                    put_json(p / 'story' / 'shots.json', data)
                    invalidate_by_change(p, 'story', old_data=old_story, new_data=data)
                    return self.send(200, {'saved': True})
                if action == 'config':
                    data = self.data()
                    if not isinstance(data, dict): raise ValueError('Config must be object')
                    old_cfg = dict(cfg)
                    allowed = ('title','aspect','resolution','fps','captions','accent','music','sfx','loudness')
                    for key in allowed:
                        if key in data: cfg[key] = data[key]
                    cfg['pack'] = ensure_project(p)['pack']
                    if cfg.get('aspect') not in ('16:9','9:16'): raise ValueError('Unsupported aspect')
                    if cfg.get('resolution') not in ('720p', '1080p', '1440p', '2160p'): raise ValueError('Unsupported resolution')
                    put_json(p / 'config.json', cfg)
                    invalidate_by_change(p, 'config', old_data=old_cfg, new_data=cfg)
                    return self.send(200, {'saved': True})
                if action in ('script', 'voice-script'):
                    data = self.data(); content = data.get('text', '')
                    if not isinstance(content, str) or len(content) > 250_000: raise ValueError('Text too long')
                    file = ('01-PHIM.txt' if action == 'script' else 'voice_script.txt')
                    (p / 'input').mkdir(exist_ok=True)
                    (p / 'input' / file).write_text(content, encoding='utf-8')
                    invalidate_by_change(p, 'script')
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
                    invalidate_by_change(p, 'voice-upload')
                    return self.send(200, {'saved': True, 'bytes': len(content)})
            self.error(404, 'Unknown endpoint')
        except ProjectConflictError as exc:
            self.send(409, {
                'error': str(exc),
                'conflict': True,
                'project_id': exc.project_id,
                'is_recoverable': exc.is_recoverable,
                'suggested_id': exc.suggested_id
            })
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
