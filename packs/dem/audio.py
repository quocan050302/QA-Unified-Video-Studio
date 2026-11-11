"""audio.py (pack dem) — nhac nen va SFX rieng cho phim ngan khong loi doc. Chay boi audio/build_audio.py (tu tim packs/*/audio.py).
Nhac (ten dung trong shots.json "music": bed):
  sad      piano cham + pad tram (mo dau, sa nga)
  dark     drone thap + nhip tim + chuong xa (day, cam do thang)
  rise     piano rai not + nhip + trong nhe, manh dan (dung len, tap luyen)
  resolve  hop am truong am, piano (ket, the cuoi)
  hope     pad sang + chuong nhe (khoanh khac that, buoc ngoat)
SFX: alarm_beep, alarm_long, glass_shatter, rain_loop, notif_msg, msg_sent, punch_bag, boom_deep, tempt_swell, tempt_whisper,
     clock_tick, footsteps, door_open, breath_in, sting_low, page_flip
"""
import os, sys
import numpy as np, soundfile as sf
AUDIO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'audio')
sys.path.insert(0, AUDIO); os.chdir(AUDIO)
from synth import SR, t, norm, lp, hp, bp, reverb, save, ding, impact, whoosh, heartbeat, riser, rng
from music import render, piano, pad, sub, place, chord_freqs, pluck, kick, hat, CHORDS

CHORDS.update({'Cm': ('C', [0, 3, 7]), 'Ab': ('G#', [0, 4, 7]), 'Eb': ('D#', [0, 4, 7]), 'Bbs': ('A#', [0, 4, 7]), 'Am9': ('A', [0, 3, 7, 10, 14]), 'Fadd9': ('F', [0, 4, 7, 14])})

def mixp(a, b):
    n = max(len(a), len(b)); return np.pad(a, (0, n - len(a))) + np.pad(b, (0, n - len(b)))

def drone_bed(name, root_hz, d=72.0, beat_bpm=None, bells=True):
    n = int(d * SR); tt = np.arange(n) / SR; x = np.zeros(n)
    for k, a in ((1, 1.0), (1.5, 0.35), (2, 0.5), (3, 0.18)):
        f = root_hz * k; ph = rng.uniform(0, 6)
        x += a * (2 * ((f * (1 + 0.002 * np.sin(2 * np.pi * 0.07 * tt)) * tt + ph) % 1) - 1)
    x = hp(lp(x, 900, 2), 70) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * tt))
    buf = np.stack([x, np.roll(x, 900)], 1) * 0.25
    if beat_bpm:
        hb = heartbeat(beat_bpm, int(d * beat_bpm / 60) - 1)
        L = min(len(hb), n); hb = hp(hb, 45); buf[:L] += np.stack([hb[:L], hb[:L]], 1) * 0.35
    if bells:
        for s in np.arange(4, d - 4, 6.0): place(buf, ding(root_hz * 8 * rng.choice([1, 1.2, 1.5]), 4.0, 0.3), s, 0.12, p=rng.uniform(-0.6, 0.6))
    buf = reverb(buf, 3.5, 0.4, 3000)[:n]
    f = int(2 * SR); buf[:f] *= np.linspace(0, 1, f)[:, None]; buf[-f:] *= np.linspace(1, 0, f)[:, None]
    buf = norm(buf, 0.7); p = os.path.join(AUDIO, 'music', name + '.wav'); sf.write(p, buf.astype(np.float32), SR, subtype='PCM_24'); print(p)

def sad_piano(name, prog, bpm, loops, notes_per_bar=4, oct_=4, drone=True):
    beat = 60 / bpm; bar = beat * 4; total = len(prog) * loops * bar
    buf = np.zeros((int((total + 5) * SR), 2))
    for i, ch in enumerate(prog * loops):
        t0 = i * bar; fr = chord_freqs(ch, 3)
        place(buf, hp(pad(fr, bar + 1.5, 1400), 160), t0, 0.16)
        mel = [fr[0] * 2, fr[2] * 2, fr[1] * 4, fr[2] * 2]
        for k in range(notes_per_bar): place(buf, piano(mel[k % 4] * 2, 3.5, 0.55 if k else 0.7), t0 + k * bar / notes_per_bar, 0.42, p=-0.25 + 0.16 * k)
        place(buf, piano(fr[0], 4.0, 0.5), t0, 0.22)
    buf = reverb(buf, 3.8, 0.42, 4200)[:int((total + 3) * SR)]
    f = int(1.0 * SR); buf[:f] *= np.linspace(0, 1, f)[:, None]; g = int(3 * SR); buf[-g:] *= np.linspace(1, 0, g)[:, None]
    buf = norm(buf, 0.7); p = os.path.join(AUDIO, 'music', name + '.wav'); sf.write(p, buf.astype(np.float32), SR, subtype='PCM_24'); print(p)

def build_music():
    sad_piano('bed_sad_Am_64bpm', ['Am', 'F', 'C', 'G'], 64, 5)
    drone_bed('bed_dark_E_drone', 41.2, 72, beat_bpm=62)
    render('bed_rise_Am_96bpm', ['Am', 'F', 'C', 'G'], 96, 1, 8, ('pad', 'sub', 'arp', 'piano', 'drums'), pad_cut=1800, rev=(2.6, 0.32, 5000))
    sad_piano('bed_resolve_C_70bpm', ['C', 'G', 'Am', 'F'], 70, 4, notes_per_bar=3)
    render('bed_hope_F_76bpm', ['Fadd9', 'C', 'Am9', 'G'], 76, 1, 5, ('pad', 'bell', 'sub'), pad_cut=2400, rev=(4.0, 0.45, 6000))

# ---------------- SFX
def alarm(beeps=4, f=2900):
    one = np.sin(2 * np.pi * f * t(0.11)) * 0.5; one = np.sign(one) * 0.3 + one * 0.5; out = np.zeros(int(SR * (beeps * 0.5 + 0.2)))
    for b in range(beeps):
        for k in range(2): s = int((b * 0.5 + k * 0.15) * SR); out[s:s + len(one)] += one
    return bp(out, 800, 7000)
def shatter(d=1.6):
    n = int(d * SR); tt = t(d); x = hp(rng.standard_normal(n), 2500) * np.exp(-tt * 5)
    for _ in range(40): s = int(rng.uniform(0, 0.9) * SR); L = int(0.05 * SR); x[s:s + L] += np.sin(2 * np.pi * rng.uniform(2500, 7000) * t(0.05)) * np.exp(-t(0.05) * 60)[:len(x[s:s + L])] * 0.6
    return mixp(x, lp(impact(0.6, 140, 50, 0.7, 0.5), 900) * 0.6)
def rain_loop(d=8.0):
    n = int(d * SR); x = bp(rng.standard_normal(n), 400, 9000) * 0.3
    for _ in range(int(d * 60)): s = int(rng.uniform(0, d - 0.05) * SR); L = int(0.01 * SR); x[s:s + L] += hp(rng.standard_normal(L), 3000) * rng.uniform(0.1, 0.5)
    f = int(0.3 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f); return np.stack([x, np.roll(x, 3000)], 1)
def notif():
    a = np.sin(2 * np.pi * 1320 * t(0.09)) * np.exp(-t(0.09) * 30); b = np.sin(2 * np.pi * 1760 * t(0.16)) * np.exp(-t(0.16) * 22)
    out = np.zeros(int(0.3 * SR)); out[:len(a)] += a; s = int(0.08 * SR); out[s:s + len(b)] += b; return out
def sent():
    tt = t(0.25); f = 600 + 1800 * tt / 0.25; return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 12) * 0.6 + hp(rng.standard_normal(len(tt)), 3000) * np.exp(-tt * 25) * 0.15
def boom(): return lp(impact(3.0, 70, 28, 1.0, 0.2), 300)
def swell(d=2.2):
    tt = t(d); n = len(tt); x = bp(rng.standard_normal(n), 200, 1800) * (tt / d) ** 2.5
    tone = np.sin(2 * np.pi * 55 * tt) * 0.5 + np.sin(2 * np.pi * 58.3 * tt) * 0.4
    return (x + tone * (tt / d) ** 2) * np.minimum(1, (d - tt) / 0.05)
def whisper(d=1.3):
    tt = t(d); n = len(tt); env = np.abs(np.sin(np.pi * tt / d)) ** 1.5 * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * tt))
    return bp(rng.standard_normal(n), 1800, 6500) * env * 0.6
def clock_tick(d=4.0):
    out = np.zeros(int(d * SR))
    for k in range(int(d)): s = int(k * SR); c = hp(rng.standard_normal(int(0.02 * SR)), 2500) * np.exp(-t(0.02) * 300) * (1 if k % 2 else 0.7); out[s:s + len(c)] += c
    return out
def footsteps(n=6, gap=0.48):
    out = np.zeros(int((n * gap + 0.3) * SR))
    for k in range(n): s = int(k * gap * SR); st = lp(impact(0.18, 160, 80, 0.4, 0.4), 1800) * rng.uniform(0.7, 1); out[s:s + len(st)] += st[:len(out) - s]
    return out
def door():
    tt = t(1.1); f = 300 + 200 * np.sin(2 * np.pi * 1.3 * tt); x = bp(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3, 400, 3000) * np.exp(-tt * 2)
    return mixp(x, lp(impact(0.4, 90, 50, 0.5, 0.2), 500) * 0.5)
def breath(): tt = t(0.9); return bp(rng.standard_normal(len(tt)), 500, 3000) * np.sin(np.pi * tt / 0.9) ** 2 * 0.5
def sting():
    tt = t(3.0); x = sum(np.sin(2 * np.pi * f * tt) for f in (55, 58.27, 82.4)) * np.exp(-tt * 0.9)
    return mixp(lp(x, 600), lp(impact(1.2, 80, 35, 1.0, 0.3), 400) * 0.6)
def page():
    tt = t(0.4); return bp(rng.standard_normal(len(tt)), 1500, 8000) * np.exp(-((tt - 0.15) / 0.07) ** 2) * 0.6

def build_sfx():
    D = 'sfx'; P = []
    P.append(save(f'{D}/alarm_beep', alarm(4), 0.7)); P.append(save(f'{D}/alarm_long', alarm(10), 0.7))
    P.append(save(f'{D}/glass_shatter', shatter(), 0.85, rev=(1.4, 0.2, 7000)))
    P.append(save(f'{D}/rain_loop', rain_loop(), 0.5))
    P.append(save(f'{D}/notif_msg', notif(), 0.6)); P.append(save(f'{D}/msg_sent', sent(), 0.55))
    P.append(save(f'{D}/punch_bag', lp(impact(0.45, 110, 55, 0.9, 0.3), 1200), 0.9))
    P.append(save(f'{D}/boom_deep', boom(), 0.95, rev=(2.5, 0.3, 1500)))
    P.append(save(f'{D}/tempt_swell', swell(), 0.8, rev=(2.0, 0.35, 3000)))
    P.append(save(f'{D}/tempt_whisper', whisper(), 0.55, rev=(1.6, 0.4, 6000)))
    P.append(save(f'{D}/clock_tick', clock_tick(), 0.5)); P.append(save(f'{D}/footsteps', footsteps(), 0.7))
    P.append(save(f'{D}/door_open', door(), 0.6, rev=(1.0, 0.2, 4000))); P.append(save(f'{D}/breath_in', breath(), 0.5))
    P.append(save(f'{D}/sting_low', sting(), 0.9, rev=(3.0, 0.35, 2000))); P.append(save(f'{D}/page_flip', page(), 0.5))
    return P

if __name__ == '__main__':
    for p in build_sfx(): print(p)
    build_music()
