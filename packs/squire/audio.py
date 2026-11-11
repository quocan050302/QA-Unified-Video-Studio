"""audio.py (pack squire) — SFX + nhac nen rieng cho ngach lich su quan su. Chay boi audio/build_audio.py (tu tim packs/*/audio.py).
SFX (ten dung trong shots.json "sfx": [{"name": ..., "at": ...}]):
  horse_neigh, horse_snort, hooves_walk, hooves_gallop, sword_clash, sword_draw, shield_bash, armor_clank, chainmail,
  arrow_whoosh, arrow_volley, arrow_thunk, javelin_throw, spear_hit, battle_roar, battle_far, war_horn, horn_roman,
  drum_march, drum_hit, thunder, wind_loop, mud_step, musket_shot, cannon, explosion, fire_crackle, splash, bell_toll, coin_drop, page_turn
Nhac (bed): medieval, roman, war, suspense, somber, victory, ancient (+ bed chung: curious, mystery, wonder, sad, dark...)
"""
import os, sys
import numpy as np, soundfile as sf
AUDIO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'audio')
sys.path.insert(0, AUDIO); os.chdir(AUDIO)
from synth import SR, t, norm, lp, hp, bp, reverb, save, impact, whoosh, rng, crowd, sweep_filter, stereo
from music import pad, sub, place, chord_freqs, pluck, kick, CHORDS

D = 'sfx'
def mixp(a, b):
    a = a.mean(1) if a.ndim > 1 else a; b = b.mean(1) if b.ndim > 1 else b
    n = max(len(a), len(b)); return np.pad(a, (0, n - len(a))) + np.pad(b, (0, n - len(b)))
def at(buf, x, s, g=1.0):
    i = max(0, int(s * SR))
    if i >= len(buf): return
    e = min(len(buf), i + len(x)); buf[i:e] += x[:e - i] * g

# ---------- ngua
def neigh(d=1.5):
    tt = t(d); n = len(tt)
    # cao do rung manh, truot len roi xuong (whinny)
    f0 = 520 + 380 * np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 0.7 - 260 * (tt / d) ** 2
    vib = 1 + 0.08 * np.sin(2 * np.pi * 23 * tt) * (0.4 + tt / d)
    ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
    x = sum(np.sin(k * ph) * a for k, a in [(1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (5, 0.12)])
    x = bp(x, 300, 4200) + bp(rng.standard_normal(n), 1500, 5000) * 0.25
    env = np.minimum(1, tt / 0.06) * np.exp(-((tt - d * 0.35) / (d * 0.55)) ** 2 * 1.4)
    # khit mui cuoi
    sn = bp(rng.standard_normal(int(0.35 * SR)), 300, 2500) * np.exp(-t(0.35) * 9) * 0.6
    out = x * env; out = mixp(out, np.pad(sn, (int(d * 0.85 * SR), 0)))
    return out
def snort():
    x = bp(rng.standard_normal(int(0.5 * SR)), 200, 2200) * np.exp(-t(0.5) * 7); return x + lp(rng.standard_normal(len(x)), 300) * np.exp(-t(0.5) * 10) * 0.5
def hoof():
    x = lp(rng.standard_normal(int(0.09 * SR)), 1600) * np.exp(-t(0.09) * 55); x += np.sin(2 * np.pi * 140 * t(0.09)) * np.exp(-t(0.09) * 40) * 0.8; return x
def hooves(d=4.0, gallop=True):
    buf = np.zeros(int(d * SR)); per = 0.42 if gallop else 0.62; pat = [0, 0.07, 0.15, 0.22] if gallop else [0, 0.31]
    s = 0.0
    while s < d - 0.3:
        for p in pat: at(buf, hoof() * rng.uniform(0.7, 1.0), s + p + rng.uniform(-0.01, 0.01))
        s += per
    return buf
# ---------- kim loai
def metal(d=1.2, fs=(1850, 2730, 3920, 5210, 6880), decay=4.5):
    tt = t(d); x = sum(np.sin(2 * np.pi * f * rng.uniform(0.98, 1.02) * tt + rng.uniform(0, 6)) * np.exp(-tt * decay * (1 + i * 0.3)) / (1 + i * 0.4) for i, f in enumerate(fs))
    return x + hp(rng.standard_normal(len(tt)), 3000) * np.exp(-tt * 40) * 0.6
def clash(): return mixp(metal(1.3), lp(impact(0.4, 220, 90, 0.4, 0.8), 1200) * 0.5)
def draw():
    tt = t(0.8); f = 2500 + 2500 * tt; x = bp(rng.standard_normal(len(tt)), 2500, 9000) * np.sin(np.pi * tt / 0.8) ** 1.5 * 0.6
    return mixp(x, np.pad(metal(0.6, (3100, 4700, 6200), 6) * 0.4, (int(0.65 * SR), 0)))
def bash():
    x = lp(impact(0.6, 150, 60, 0.9, 0.9), 2000); w = bp(rng.standard_normal(int(0.25 * SR)), 300, 2500) * np.exp(-t(0.25) * 18) * 0.7
    return mixp(x, w)
def clank():
    out = np.zeros(int(0.9 * SR))
    for k in range(4): at(out, metal(0.4, (1200 + k * 300, 2600, 3700), 12) * 0.5, k * 0.17 + rng.uniform(0, 0.03))
    return out
def chain():
    out = np.zeros(int(1.0 * SR))
    for k in range(40): at(out, hp(rng.standard_normal(int(0.02 * SR)), 4000) * np.exp(-t(0.02) * 120) * rng.uniform(0.2, 0.6), rng.uniform(0, 0.9))
    return out
# ---------- mui ten, giao
def arrow_whoosh():
    x = whoosh(0.55, 800, 6000, 2.2, bright=0.6); return x.mean(1) if x.ndim > 1 else x
def arrow_thunk():
    x = lp(impact(0.35, 260, 110, 0.5, 1.0), 2500); tw = np.sin(2 * np.pi * 180 * t(0.3)) * np.exp(-t(0.3) * 14) * 0.25 * np.sin(2 * np.pi * 22 * t(0.3))
    return mixp(x, tw)
def volley(d=3.0, n=60):
    buf = np.zeros((int(d * SR), 2))
    for _ in range(n):
        s = rng.uniform(0, d * 0.5); w = stereo(whoosh(rng.uniform(0.35, 0.7), rng.uniform(600, 1200), rng.uniform(4000, 8000), 2.0, bright=0.5)); p = rng.uniform(-0.8, 0.8)
        w = w * np.array([np.sqrt((1 - p) / 2), np.sqrt((1 + p) / 2)]) * rng.uniform(0.2, 0.5); i = int(s * SR); e = min(len(buf), i + len(w)); buf[i:e] += w[:e - i]
    for _ in range(n // 2):
        s = rng.uniform(d * 0.35, d * 0.95); x = stereo(arrow_thunk() * rng.uniform(0.15, 0.4)); i = int(s * SR); e = min(len(buf), i + len(x)); buf[i:e] += x[:e - i]
    return buf
def javelin(): return mixp(whoosh(0.8, 200, 2600, 1.0), np.pad(arrow_thunk() * 0.8, (int(0.7 * SR), 0)))
def spear_hit(): return mixp(bash() * 0.6, metal(0.5, (2100, 3300), 10) * 0.3)
# ---------- dam dong, ken, trong
def roar(d=4.0, far=False):
    x = crowd(d, cheer=False)
    if x.ndim > 1: x = x.mean(1)
    tt = t(len(x) / SR); swell = np.minimum(1, tt / 0.8)
    x = bp(x, 150, 2500 if far else 4500) * swell * 1.4
    if far: x = lp(x, 1200) * 0.7
    return x
def horn(d=3.0, f=110.0, roman=False):
    tt = t(d); env = np.minimum(1, tt / 0.25) * np.minimum(1, (d - tt) / 0.6)
    fr = f * (1 + 0.003 * np.sin(2 * np.pi * 5 * tt))
    if roman: fr = np.where(tt < d * 0.45, f * 1.5, f * 2.0)
    ph = 2 * np.pi * np.cumsum(fr) / SR; x = sum(np.sin(k * ph) * (0.9 ** k) for k in range(1, 12))
    return lp(x, 2600) * env * 0.4
def drum_hit():
    x = lp(impact(0.9, 110, 45, 1.0, 0.25), 900); return x + bp(rng.standard_normal(len(x)), 120, 600) * np.exp(-t(len(x) / SR) * 18) * 0.4
def drum_march(d=6.0, bpm=96):
    buf = np.zeros(int(d * SR)); b = 60 / bpm; k = 0; s = 0.0
    while s < d - 1: at(buf, drum_hit() * (1.0 if k % 4 == 0 else 0.55), s); s += b if k % 4 != 3 else b / 2; k += 1
    return buf
def thunder(d=4.0):
    tt = t(d); x = lp(rng.standard_normal(len(tt)), 300) * np.exp(-tt * 1.1) * 2 + bp(rng.standard_normal(len(tt)), 400, 3000) * np.exp(-tt * 6) * (tt < 0.4)
    return x * np.minimum(1, tt / 0.03)
def wind(d=8.0):
    n = int(d * SR); x = sweep_filter(rng.standard_normal(n), 200, 900, 2.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t(d)))
    f = int(0.5 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f); return x
def mud_step():
    x = lp(rng.standard_normal(int(0.3 * SR)), 900) * np.exp(-t(0.3) * 12); x += np.sin(2 * np.pi * np.cumsum(np.linspace(260, 120, len(x))) / SR) * np.exp(-t(0.3) * 15) * 0.4; return x
def musket():
    x = impact(1.2, 300, 70, 0.9, 1.0)[:int(1.2 * SR)] + hp(rng.standard_normal(int(1.2 * SR)), 1500) * np.exp(-t(1.2) * 25) * 0.8; return x
def cannon(): return lp(impact(3.0, 90, 30, 1.0, 0.6), 1500) * 1.2
def explosion(): return mixp(lp(impact(3.5, 80, 25, 1.0, 0.8), 2000), bp(rng.standard_normal(int(2.5 * SR)), 200, 4000) * np.exp(-t(2.5) * 2.2) * 0.6)
def fire(d=6.0):
    n = int(d * SR); x = lp(rng.standard_normal(n), 800) * 0.15
    for _ in range(int(d * 25)): i = int(rng.uniform(0, d - 0.02) * SR); L = int(0.004 * SR); x[i:i + L] += hp(rng.standard_normal(L), 2000) * rng.uniform(0.2, 0.8)
    return x
def splash(): return mixp(bp(rng.standard_normal(int(0.9 * SR)), 300, 6000) * np.exp(-t(0.9) * 6), lp(impact(0.5, 120, 50, 0.6, 0.2), 500) * 0.5)
def bell():
    tt = t(5.0); return sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * dcy) * a for f, dcy, a in [(196, 0.6, 1.0), (392.5, 0.9, 0.6), (466, 1.1, 0.4), (587, 1.4, 0.3), (980, 2.2, 0.2)])
def coin(): return metal(0.8, (3200, 4870, 6100), 7) * 0.6
def page():
    x = bp(rng.standard_normal(int(0.45 * SR)), 1200, 8000) * np.sin(np.pi * np.linspace(0, 1, int(0.45 * SR))) ** 2 * 0.5; return x

def sting_low():
    x = lp(impact(2.5, 70, 30, 1.0, 0.15), 400); tt = t(len(x) / SR); return x + np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 1.2) * 0.4
def footsteps(n=6):
    out = np.zeros(int((n * 0.5 + 0.5) * SR))
    for k in range(n): at(out, lp(rng.standard_normal(int(0.12 * SR)), 1200) * np.exp(-t(0.12) * 35) * rng.uniform(0.6, 1.0), k * 0.5)
    return out
def door():
    x = lp(rng.standard_normal(int(1.2 * SR)), 900) * np.exp(-t(1.2) * 3) * 0.3; f = np.linspace(300, 180, len(x)); x += np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 * np.exp(-t(1.2) * 2); return mixp(x, np.pad(drum_hit() * 0.5, (int(1.0 * SR), 0)))
def build_sfx():
    S = [('sting_low', sting_low(), 0.85, (2.5, 0.35, 2500)), ('footsteps', footsteps(), 0.6, (0.6, 0.1, 5000)), ('door_open', door(), 0.7, (1.2, 0.2, 4000)),
        ('horse_neigh', neigh(), 0.85, (1.4, 0.2, 5000)), ('horse_snort', snort(), 0.7, None),
        ('hooves_walk', hooves(4.0, False), 0.7, (0.8, 0.12, 5000)), ('hooves_gallop', hooves(4.0, True), 0.8, (0.8, 0.12, 5000)),
        ('sword_clash', clash(), 0.85, (1.2, 0.2, 7000)), ('sword_draw', draw(), 0.7, (0.8, 0.15, 8000)), ('shield_bash', bash(), 0.85, (0.9, 0.15, 4000)),
        ('armor_clank', clank(), 0.6, (0.6, 0.1, 6000)), ('chainmail', chain(), 0.5, None),
        ('arrow_whoosh', arrow_whoosh(), 0.7, None), ('arrow_thunk', arrow_thunk(), 0.75, None), ('arrow_volley', volley(), 0.8, (1.6, 0.2, 6000)),
        ('javelin_throw', javelin(), 0.8, None), ('spear_hit', spear_hit(), 0.8, None),
        ('battle_roar', roar(4.0), 0.7, (2.0, 0.3, 5000)), ('battle_far', roar(5.0, True), 0.6, (2.5, 0.4, 3000)),
        ('war_horn', horn(3.0, 110), 0.75, (3.0, 0.35, 4000)), ('horn_roman', horn(2.6, 196, True), 0.7, (2.5, 0.3, 5000)),
        ('drum_hit', drum_hit(), 0.85, (1.5, 0.2, 3000)), ('drum_march', drum_march(), 0.75, (1.2, 0.2, 3000)),
        ('thunder', thunder(), 0.9, (2.5, 0.3, 2500)), ('wind_loop', wind(), 0.55, None), ('mud_step', mud_step(), 0.7, None),
        ('musket_shot', musket(), 0.9, (1.5, 0.2, 4000)), ('cannon', cannon(), 0.95, (2.5, 0.3, 2500)), ('explosion', explosion(), 0.95, (2.5, 0.3, 3000)),
        ('fire_crackle', fire(), 0.5, None), ('splash', splash(), 0.8, None), ('bell_toll', bell(), 0.7, (3.0, 0.35, 4000)),
        ('coin_drop', coin(), 0.6, None), ('page_turn', page(), 0.5, None),
    ]
    for name, x, pk, rv in S: print(save(f'{D}/{name}', x, pk, rev=rv))

# ---------- nhac nen: nhe, kieu ke chuyen lich su (nam duoi giong ~15 dB)
CHORDS.update({'Dm7': ('D', [0, 3, 7, 10]), 'Csus': ('C', [0, 5, 7]), 'Gm': ('G', [0, 3, 7]), 'Bbmaj7': ('A#', [0, 4, 7, 11]), 'A': ('A', [0, 4, 7]), 'Fm': ('F', [0, 3, 7]), 'Db': ('C#', [0, 4, 7]), 'D': ('D', [0, 4, 7]), 'B': ('B', [0, 4, 7])})
def frame_drum():
    x = lp(rng.standard_normal(int(0.35 * SR)), 500) * np.exp(-t(0.35) * 14) + np.sin(2 * np.pi * 90 * t(0.35)) * np.exp(-t(0.35) * 12) * 0.8; return x
def lute(f, d=1.6): return lp(pluck(f, d, 0.55), 3500)
def bed(name, prog, bpm, loops, kind):
    beat = 60 / bpm; bar = beat * 4; total = len(prog) * loops * bar
    buf = np.zeros((int((total + 5) * SR), 2))
    for i, ch in enumerate(prog * loops):
        t0 = i * bar; fr = chord_freqs(ch, 3)
        place(buf, pad(fr, bar + 1.2, 1100 if kind != 'war' else 700), t0, 0.32 if kind in ('somber', 'mystery_old') else 0.22)
        place(buf, sub(fr[0] / 2, bar), t0, 0.12)
        if kind in ('medieval', 'triumph_old'):
            pat = [0, 2, 1, 2, 0, 2, 1, 3]
            for k in range(8): n = [fr[0] * 2, fr[1] * 2, fr[2] * 2, fr[0] * 4][pat[k] % 4]; place(buf, lute(n), t0 + k * beat / 2, 0.22, p=0.3 * np.sin(k))
        if kind in ('roman', 'war', 'triumph_old', 'medieval'):
            for k in range(4):
                if kind == 'medieval' and k % 2: continue
                place(buf, frame_drum(), t0 + k * beat, 0.35 if k == 0 else 0.2, p=-0.2)
        if kind == 'roman':
            for k, f in enumerate([fr[0] * 2, fr[2] * 2]): place(buf, lp(horn(bar * 0.45, f), 1800) * 0.6, t0 + k * bar / 2, 0.22, p=0.2)
        if kind == 'war':
            for k in range(8): place(buf, drum_hit() * 0.5, t0 + k * beat / 2, 0.25 if k % 2 == 0 else 0.12)
        if kind == 'tension':
            for k in range(16): place(buf, lp(pluck(fr[0], 0.2, 0.1), 700), t0 + k * beat / 4, 0.18 if k % 4 == 0 else 0.08)
        if kind in ('somber', 'mystery_old'):
            place(buf, lute(fr[2] * 2, 3.0), t0 + beat, 0.15, p=0.4); place(buf, lute(fr[1] * 4, 3.0), t0 + beat * 3, 0.1, p=-0.4)
    buf = reverb(buf, 3.2, 0.38, 4500)[:int((total + 3) * SR)]
    f = int(1.0 * SR); buf[:f] *= np.linspace(0, 1, f)[:, None]; g = int(3 * SR); buf[-g:] *= np.linspace(1, 0, g)[:, None]
    buf = norm(buf, 0.7); p = os.path.join(AUDIO, 'music', name + '.wav'); os.makedirs(os.path.dirname(p), exist_ok=True); sf.write(p, buf.astype(np.float32), SR, subtype='PCM_24'); print(p)
def build_music():
    bed('bed_medieval_Dm_84bpm', ['Dm', 'C', 'Bb', 'C'], 84, 6, 'medieval')
    bed('bed_roman_Am_80bpm', ['Am', 'G', 'F', 'E'], 80, 6, 'roman')
    bed('bed_war_Dm_100bpm', ['Dm', 'Bb', 'Gm', 'A'], 100, 8, 'war')
    bed('bed_suspense_Em_90bpm', ['Em', 'C', 'Em', 'B' if 'B' in CHORDS else 'G'], 90, 7, 'tension')
    bed('bed_somber_Am_62bpm', ['Am', 'F', 'Dm', 'E'], 62, 4, 'somber')
    bed('bed_victory_D_92bpm', ['D' if 'D' in CHORDS else 'Dsus', 'G', 'A', 'D' if 'D' in CHORDS else 'Dsus'], 92, 6, 'triumph_old')
    bed('bed_ancient_Dm_70bpm', ['Dm', 'Bbmaj7', 'Gm', 'A'], 70, 5, 'mystery_old')

if __name__ == '__main__':
    build_sfx(); build_music()
