/**
 * canonical_hash.js — Node.js implementation of the V8 canonical visual & audio hashing spec.
 * Produces byte-for-byte identical JSON serialization and SHA256 hashes as tools/common.py.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const NON_VISUAL_ARG_KEYS = new Set([
  'sfx', 'music', 'audio_gain', 'voice_gain', 'notes', 'cue', 'cues',
  'audio_plan', 'audio_report', 'comment', 'audio'
]);

export function canonicalJsonSerialize(obj) {
  if (obj === null || obj === undefined) {
    return 'null';
  }
  if (typeof obj === 'boolean') {
    return obj ? 'true' : 'false';
  }
  if (typeof obj === 'number') {
    const r = Math.round(obj * 10000) / 10000;
    if (r === 0) return '0';
    return JSON.stringify(r);
  }
  if (typeof obj === 'string') {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalJsonSerialize).join(',') + ']';
  }
  if (typeof obj === 'object') {
    const keys = Object.keys(obj).sort();
    const items = [];
    for (const k of keys) {
      const v = obj[k];
      if (v !== undefined && v !== null) {
        items.push(JSON.stringify(String(k)) + ':' + canonicalJsonSerialize(v));
      }
    }
    return '{' + items.join(',') + '}';
  }
  return JSON.stringify(obj);
}

export function filterVisualArgs(args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) {
    return args;
  }
  const res = {};
  for (const [k, v] of Object.entries(args)) {
    if (NON_VISUAL_ARG_KEYS.has(k)) continue;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      res[k] = filterVisualArgs(v);
    } else if (Array.isArray(v)) {
      res[k] = v.map(item => (item && typeof item === 'object' && !Array.isArray(item)) ? filterVisualArgs(item) : item);
    } else {
      res[k] = v;
    }
  }
  return res;
}

export function getCanonicalVisualManifest(projDir, storyData = null, configData = null) {
  const p = path.resolve(projDir);
  let cfg = configData;
  if (!cfg) {
    const cfgPath = path.join(p, 'config.json');
    cfg = fs.existsSync(cfgPath) ? JSON.parse(fs.readFileSync(cfgPath, 'utf8')) : {};
  }
  let story = storyData;
  if (!story) {
    const storyPath = path.join(p, 'story', 'shots.json');
    story = fs.existsSync(storyPath) ? JSON.parse(fs.readFileSync(storyPath, 'utf8')) : {};
  }

  const manifest = {
    manifest_version: 'v8_visual_v1',
    config: {
      pack: String(cfg.pack || 'squire'),
      aspect: String(cfg.aspect || '16:9'),
      resolution: String(cfg.resolution || '1080p'),
      fps: parseInt(cfg.fps || 24, 10),
      style: String(cfg.style || 'flat'),
    },
    shots: [],
    visual_assets: {}
  };

  for (const s of (story.shots || [])) {
    const startNum = Math.round(Number(s.start || 0) * 10000) / 10000;
    const endNum = Math.round(Number(s.end || 0) * 10000) / 10000;
    manifest.shots.push({
      id: String(s.id || ''),
      start: startNum,
      end: endNum,
      tpl: String(s.tpl || 'scene'),
      scene: s.scene ? String(s.scene) : null,
      args: filterVisualArgs(s.args || {})
    });
  }

  // Collect scenes and anh assets
  const scenesDir = path.join(p, 'scenes');
  if (fs.existsSync(scenesDir)) {
    function walk(dir) {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(full);
        } else if (entry.isFile() && entry.name.endsWith('.js')) {
          const rel = path.relative(p, full).replace(/\\/g, '/');
          try {
            const buf = fs.readFileSync(full);
            manifest.visual_assets[rel] = crypto.createHash('sha256').update(buf).digest('hex').slice(0, 16);
          } catch {}
        }
      }
    }
    try { walk(scenesDir); } catch {}
  }

  const anhDir = path.join(p, 'anh');
  if (fs.existsSync(anhDir)) {
    try {
      for (const f of fs.readdirSync(anhDir)) {
        const ext = path.extname(f).toLowerCase();
        if (['.png', '.jpg', '.jpeg', '.webp'].includes(ext)) {
          const full = path.join(anhDir, f);
          const rel = path.relative(p, full).replace(/\\/g, '/');
          try {
            const buf = fs.readFileSync(full);
            manifest.visual_assets[rel] = crypto.createHash('sha256').update(buf).digest('hex').slice(0, 16);
          } catch {}
        }
      }
    } catch {}
  }

  return manifest;
}

export function computeCanonicalVisualHash(projDir, storyData = null, configData = null) {
  const manifest = getCanonicalVisualManifest(projDir, storyData, configData);
  const serialized = canonicalJsonSerialize(manifest);
  return crypto.createHash('sha256').update(Buffer.from(serialized, 'utf8')).digest('hex');
}

export function getCanonicalAudioManifest(projDir, storyData = null, configData = null) {
  const p = path.resolve(projDir);
  let cfg = configData;
  if (!cfg) {
    const cfgPath = path.join(p, 'config.json');
    cfg = fs.existsSync(cfgPath) ? JSON.parse(fs.readFileSync(cfgPath, 'utf8')) : {};
  }
  let story = storyData;
  if (!story) {
    const storyPath = path.join(p, 'story', 'shots.json');
    story = fs.existsSync(storyPath) ? JSON.parse(fs.readFileSync(storyPath, 'utf8')) : {};
  }

  const voiceFile = path.join(p, 'timeline', 'voice.wav');
  let voiceSha = '';
  if (fs.existsSync(voiceFile)) {
    try {
      voiceSha = crypto.createHash('sha256').update(fs.readFileSync(voiceFile)).digest('hex');
    } catch {}
  }

  const manifest = {
    manifest_version: 'v8_audio_v1',
    voice_sha256: voiceSha,
    config: {
      music: cfg.music || { enabled: true, gainDb: -15 },
      sfx: cfg.sfx || { enabled: true, gainDb: -4 },
      loudness: Number(cfg.loudness !== undefined ? cfg.loudness : -14),
    },
    shots_audio: [],
    story_sfx: story.sfx || [],
    story_music: story.music || []
  };

  for (const s of (story.shots || [])) {
    manifest.shots_audio.push({
      id: String(s.id || ''),
      sfx: s.sfx || [],
      music: s.music || null
    });
  }

  return manifest;
}

export function computeCanonicalAudioHash(projDir, storyData = null, configData = null) {
  const manifest = getCanonicalAudioManifest(projDir, storyData, configData);
  const serialized = canonicalJsonSerialize(manifest);
  return crypto.createHash('sha256').update(Buffer.from(serialized, 'utf8')).digest('hex');
}

// CLI test runner if invoked directly
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'))) {
  const proj = process.argv[2] || '.';
  console.log('Visual Hash:', computeCanonicalVisualHash(proj));
  console.log('Audio Hash: ', computeCanonicalAudioHash(proj));
}

