"""Procedural cinematic underscore beds (royalty-free, generated). Loopable, 48k stereo."""
import numpy as np, soundfile as sf, os
from synth import SR, lp, hp, bp, reverb, norm, rng, ding, impact
OUT = os.path.dirname(os.path.abspath(__file__))

NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def hz(name, octv): return 440.0 * 2 ** ((NOTE[name] + 12 * (octv + 1) - 69) / 12)
CHORDS = {  # root, intervals
    'Am': ('A', [0, 3, 7]), 'F': ('F', [0, 4, 7]), 'C': ('C', [0, 4, 7]), 'G': ('G', [0, 4, 7]), 'Dm': ('D', [0, 3, 7]),
    'E': ('E', [0, 4, 7]), 'Em': ('E', [0, 3, 7]), 'Bb': ('A#', [0, 4, 7]), 'Fmaj7': ('F', [0, 4, 7, 11]), 'Am7': ('A', [0, 3, 7, 10]),
    'Dsus': ('D', [0, 5, 7]), 'Cadd9': ('C', [0, 4, 7, 14]), 'Gsus': ('G', [0, 5, 7]),
}
def chord_freqs(ch, octv=3):
    r, iv = CHORDS[ch]; f0 = hz(r, octv); return [f0 * 2 ** (i / 12) for i in iv]

def pad(freqs, d, cutoff=1400, det=0.004):
    tt = np.arange(int(d * SR)) / SR; x = np.zeros_like(tt)
    for f in freqs:
        for dd in (-det, 0, det):
            ph = rng.uniform(0, 6.28)
            saw = 2 * ((f * (1 + dd) * tt + ph / 6.28) % 1) - 1
            x += saw
    x = lp(x, cutoff, 2) / (len(freqs) * 3)
    a = int(min(1.2, d / 3) * SR); r = int(min(1.5, d / 3) * SR)
    e = np.ones_like(tt); e[:a] = np.linspace(0, 1, a); e[-r:] = np.linspace(1, 0, r)
    return x * e

def pluck(f, d=1.6, bright=0.5):
    tt = np.arange(int(d * SR)) / SR
    x = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * tt) * np.exp(-tt * (2.5 + k * 1.8 * (1.2 - bright))) for k in range(6))
    return x * np.minimum(1, tt / 0.004)

def piano(f, d=3.0, vel=0.8):
    tt = np.arange(int(d * SR)) / SR
    x = sum((0.55 ** k) * np.sin(2 * np.pi * f * (k + 1) * (1 + 0.0004 * k * k) * tt) * np.exp(-tt * (0.9 + 0.9 * k)) for k in range(8))
    x += 0.15 * hp(rng.standard_normal(len(tt)), 2000) * np.exp(-tt * 60)
    return x * vel * np.minimum(1, tt / 0.003)

def sub(f, d):
    tt = np.arange(int(d * SR)) / SR; e = np.minimum(1, tt / 0.05) * np.minimum(1, (d - tt) / 0.2)
    return np.sin(2 * np.pi * f * tt) * e

def kick():
    return lp(impact(0.5, 150, 45, 1.0, 0.15), 800)
def hat():
    tt = np.arange(int(0.08 * SR)) / SR; return hp(rng.standard_normal(len(tt)), 7000) * np.exp(-tt * 70)
def tick_perc():
    tt = np.arange(int(0.05 * SR)) / SR; return bp(rng.standard_normal(len(tt)), 2500, 5000) * np.exp(-tt * 120)

def place(buf, x, start, gain=1.0, p=0.0):
    s = int(start * SR)
    if s >= len(buf): return
    if x.ndim == 1:
        l, r = np.sqrt((1 - p) / 2), np.sqrt((1 + p) / 2); x = np.stack([x * l, x * r], 1)
    e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s] * gain

def render(name, prog, bpm, bars_per_chord=1, loops=4, layers=(), oct_pad=3, pad_cut=1400, rev=(3.0, 0.35, 5000)):
    beat = 60 / bpm; bar = beat * 4; chord_d = bar * bars_per_chord
    seq = prog * loops; total = len(seq) * chord_d
    buf = np.zeros((int((total + 4) * SR), 2))
    for i, ch in enumerate(seq):
        t0 = i * chord_d; fr = chord_freqs(ch, oct_pad)
        if 'pad' in layers: place(buf, pad(fr, chord_d + 1.0, pad_cut), t0, 0.55)
        if 'sub' in layers: place(buf, sub(fr[0] / 2, chord_d), t0, 0.18)
        if 'arp' in layers:
            notes = [f * 2 for f in fr] + [fr[0] * 4]; step = beat / 2
            for k in range(int(chord_d / step)):
                n = notes[[0, 1, 2, 3, 2, 1][k % 6] % len(notes)]
                place(buf, pluck(n, 1.4, 0.4), t0 + k * step, 0.22 * (0.85 if k % 2 else 1), p=0.4 * np.sin(k))
        if 'piano' in layers:
            for k, f in enumerate([fr[0] * 2, fr[1] * 2, fr[2] * 2, fr[1] * 4]):
                place(buf, piano(f, 3.5, 0.6), t0 + k * beat * (bars_per_chord), 0.3, p=-0.2 + 0.15 * k)
        if 'bell' in layers and i % 2 == 0:
            place(buf, ding(fr[2] * 4, 3.0, 0.4), t0, 0.08, p=0.5)
        if 'pulse' in layers:
            for k in range(int(chord_d / (beat / 2))):
                place(buf, lp(pluck(fr[0], 0.25, 0.1), 600), t0 + k * beat / 2, 0.25)
        if 'ticks' in layers:
            for k in range(int(chord_d / (beat / 4))):
                place(buf, tick_perc(), t0 + k * beat / 4, 0.12 if k % 4 else 0.22, p=0.3)
        if 'drums' in layers:
            for k in range(int(chord_d / beat)):
                if k % 2 == 0: place(buf, kick(), t0 + k * beat, 0.6)
                place(buf, hat(), t0 + k * beat + beat / 2, 0.1, p=0.2)
    buf = reverb(buf, *rev)
    buf = buf[:int((total + 3) * SR)]
    # loop-friendly: fade in 1s, fade out 3s
    f = int(1.0 * SR); buf[:f] *= np.linspace(0, 1, f)[:, None]; g = int(3 * SR); buf[-g:] *= np.linspace(1, 0, g)[:, None]
    buf = norm(buf, 0.7)
    path = os.path.join(OUT, 'music', name + '.wav'); os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, buf.astype(np.float32), SR, subtype='PCM_24'); print(path, round(len(buf) / SR, 1), 's')

if __name__ == '__main__':
    render('bed_wonder_Am_96bpm', ['Am7', 'Fmaj7', 'Cadd9', 'Gsus'], 96, 1, 6, ('pad', 'sub', 'arp', 'bell'))
    render('bed_curious_Dm_110bpm', ['Dm', 'Bb', 'F', 'C'], 110, 1, 8, ('pad', 'sub', 'pulse', 'arp'), pad_cut=1100)
    render('bed_tension_Am_120bpm', ['Am', 'Am', 'F', 'E'], 120, 1, 8, ('pad', 'sub', 'pulse', 'ticks'), oct_pad=2, pad_cut=800)
    render('bed_emotional_F_70bpm', ['F', 'C', 'Dm', 'Bb'], 70, 1, 4, ('pad', 'piano', 'sub'), pad_cut=1000, rev=(3.5, 0.4, 4500))
    render('bed_triumph_C_100bpm', ['C', 'G', 'Am', 'F'], 100, 1, 6, ('pad', 'sub', 'arp', 'drums', 'bell'), pad_cut=2200)
    render('bed_mystery_Em_80bpm', ['Em', 'Em', 'C', 'Dsus'], 80, 2, 3, ('pad', 'sub', 'bell'), oct_pad=2, pad_cut=700, rev=(4.0, 0.45, 3000))
