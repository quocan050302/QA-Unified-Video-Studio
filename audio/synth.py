"""Procedural SFX + music kit for the What-If channel. 100% generated -> no copyright.
Output: 48 kHz stereo 24-bit WAV."""
import numpy as np, soundfile as sf, os
from scipy import signal

SR = 48000
rng = np.random.default_rng(7)
OUT = os.path.dirname(os.path.abspath(__file__))

def t(d): return np.arange(int(SR * d)) / SR
def norm(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak
def env_adsr(n, a, d, s, r, sus=0.6):
    a, d, r = int(a*SR), int(d*SR), int(r*SR); s_ = max(n - a - d - r, 0)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, sus, d, False), np.full(s_, sus), np.linspace(sus, 0, r)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def lp(x, f, order=2):
    sos = signal.butter(order, f, 'lowpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def hp(x, f, order=2):
    sos = signal.butter(order, f, 'highpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def sweep_filter(x, f0, f1, q=2.0, curve='exp'):
    """time-varying bandpass via block processing"""
    n = len(x); out = np.zeros(n); blk = 256
    zi = None
    for i in range(0, n, blk):
        p = i / n
        f = f0 * (f1 / f0) ** p if curve == 'exp' else f0 + (f1 - f0) * p
        f = np.clip(f, 30, SR/2 - 2000)
        b, a = signal.iirpeak(f, q, fs=SR)
        if zi is None: zi = signal.lfilter_zi(b, a) * 0
        out[i:i+blk], zi = signal.lfilter(b, a, x[i:i+blk], zi=zi)
    return out
_ir_cache = {}
def reverb(x, size=1.8, wet=0.3, damp=4000):
    key = (size, damp)
    if key not in _ir_cache:
        n = int(size * SR); tt = np.arange(n) / SR
        irL = rng.standard_normal(n) * np.exp(-tt * 6.9 / size); irR = rng.standard_normal(n) * np.exp(-tt * 6.9 / size)
        irL, irR = lp(irL, damp), lp(irR, damp)
        _ir_cache[key] = (irL / np.sqrt((irL**2).sum()), irR / np.sqrt((irR**2).sum()))
    irL, irR = _ir_cache[key]
    if x.ndim == 1: x = np.stack([x, x], 1)
    pad = len(irL)
    xp = np.pad(x, ((0, pad), (0, 0)))
    wL = signal.fftconvolve(xp[:, 0], irL)[:len(xp)]; wR = signal.fftconvolve(xp[:, 1], irR)[:len(xp)]
    return xp * (1 - wet) + np.stack([wL, wR], 1) * wet
def pan(x, p):  # p -1..1, can be array
    l = np.sqrt((1 - p) / 2); r = np.sqrt((1 + p) / 2)
    return np.stack([x * l, x * r], 1)
def stereo(x): return np.stack([x, x], 1) if x.ndim == 1 else x
def trim(x, thr=1e-4):
    a = np.max(np.abs(stereo(x)), 1); idx = np.where(a > thr)[0]
    return x[:idx[-1] + int(0.02*SR)] if len(idx) else x
def save(name, x, peak=0.89, rev=None, fade=0.01):
    x = stereo(x)
    if rev: x = reverb(x, *rev)
    x = trim(x)
    f = int(fade * SR); x[-f:] *= np.linspace(1, 0, f)[:, None]
    x = norm(x, peak)
    path = os.path.join(OUT, name + '.wav'); os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, x.astype(np.float32), SR, subtype='PCM_24'); return path

# ---------------- SFX ----------------
def whoosh(d=0.6, f0=300, f1=3500, q=1.2, pan_move=True, bright=1.0):
    n = int(d*SR); x = rng.standard_normal(n)
    x = sweep_filter(x, f0, f1, q) * 0.7 + sweep_filter(rng.standard_normal(n), f0*1.5, f1*1.5, q*1.5) * 0.3 * bright
    e = np.sin(np.linspace(0, np.pi, n)) ** 2.2
    peak = 0.62; e = np.where(np.arange(n) < peak*n, (np.arange(n)/(peak*n))**2.5, np.exp(-(np.arange(n)-peak*n)/(0.12*n)))
    x *= e
    p = np.linspace(-0.7, 0.7, n) if pan_move else np.zeros(n)
    return pan(x, p)

def impact(d=1.6, f_hi=110, f_lo=38, sub=1.0, crack=0.6):
    tt = t(d); n = len(tt)
    f = f_lo + (f_hi - f_lo) * np.exp(-tt * 18)
    body = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt * 3.2) * sub
    nz = rng.standard_normal(n); click = hp(nz, 2000) * np.exp(-tt * 90) * crack
    thump = lp(nz, 300) * np.exp(-tt * 25) * 0.8
    x = np.tanh((body + click + thump) * 1.8)
    return x

def flash_hit(d=2.2):
    """the 'super-reflex' moment: bright shing + impact + reverse air"""
    tt = t(d); n = len(tt)
    # metallic 'shing': many inharmonic partials, fast decay
    parts = rng.uniform(2500, 11000, 14)
    shing = sum(np.sin(2*np.pi*f*tt + rng.uniform(0, 6)) * np.exp(-tt * rng.uniform(6, 14)) for f in parts) / 5
    shing += hp(rng.standard_normal(n), 5000) * np.exp(-tt * 18) * 0.6
    imp = impact(d, 220, 42, sub=1.0, crack=1.0)
    x = shing * 0.5 + imp * 0.9
    # pre-hit: rising tonal sweep (V-shape like reference) + air swell, 0.4 s
    pd = 0.4; tp = t(pd); f = 70 * (650/70) ** ((tp/pd) ** 1.5)
    pre = (np.sin(2*np.pi*np.cumsum(f)/SR) * 0.6 + sweep_filter(rng.standard_normal(len(tp)), 300, 6000, 1.0) * 0.5) * (tp/pd) ** 2.5
    out = np.zeros(len(pre) + n); out[:len(pre)] += pre * 0.7; out[len(pre):] += x
    return out, len(pre) / SR  # return offset of hit point

def slowmo_ring(d=2.5):
    """time-slows 'vwoom': falling pitch + sub + filtered air, stereo widen"""
    tt = t(d)
    f = 220 * np.exp(-tt * 1.4) + 45
    tone = np.sin(2*np.pi*np.cumsum(f)/SR) + 0.5*np.sin(2*np.pi*np.cumsum(f*1.5)/SR)
    tone = lp(tone, 900) * np.exp(-tt * 1.2)
    air = sweep_filter(rng.standard_normal(len(tt)), 4000, 300, 1.5) * np.exp(-tt * 1.5) * 0.6
    x = tone + air
    return np.stack([x, np.roll(x, 600)], 1)

def ding(f=1318.5, d=2.5, bright=1.0):
    tt = t(d)
    ratios = [(1, 1, 1.4), (2.0, 0.35, 2.0), (2.76, 0.5, 2.6), (4.07, 0.3 * bright, 3.5), (5.4, 0.25 * bright, 4.5), (8.93, 0.12 * bright, 7)]
    x = sum(a * np.sin(2*np.pi*f*r*tt) * np.exp(-tt * dec) for r, a, dec in ratios)
    x *= np.minimum(1, tt / 0.002)
    return x

def pop(f=900):
    tt = t(0.12); ff = f * np.exp(-tt * 25) + 200
    return np.sin(2*np.pi*np.cumsum(ff)/SR) * np.exp(-tt * 40)

def ui_click():
    tt = t(0.05); return hp(rng.standard_normal(len(tt)), 3000) * np.exp(-tt * 200) + np.sin(2*np.pi*2400*tt) * np.exp(-tt * 120) * 0.5

def type_key():
    tt = t(0.07); n = len(tt)
    return bp(rng.standard_normal(n), 1500, 6000) * np.exp(-tt * 140) + np.sin(2*np.pi*rng.uniform(180, 260)*tt) * np.exp(-tt*90) * 0.4

def riser(d=4.0, f0=120, f1=1400):
    tt = t(d); n = len(tt); p = tt / d
    f = f0 * (f1/f0) ** (p**1.6)
    tone = sum(np.sin(2*np.pi*np.cumsum(f*k)/SR + k) / k for k in (1, 1.005, 2.01, 3))
    nz = sweep_filter(rng.standard_normal(n), 300, 9000, 1.2)
    e = p ** 2.2
    x = (lp(tone, 4000) * 0.5 + nz * 0.8) * e
    return np.stack([x, np.roll(x, 400)], 1)

def downer(d=2.5):
    tt = t(d); f = 600 * np.exp(-tt * 2.2) + 30
    x = np.tanh(2 * np.sin(2*np.pi*np.cumsum(f)/SR)) * np.exp(-tt * 1.4)
    return lp(x, 1500)

def heartbeat(bpm=70, beats=4):
    one = lp(impact(0.35, 70, 40, 1, 0), 400)
    gap = int(60 / bpm * SR); out = np.zeros(gap * beats + len(one))
    for b in range(beats):
        s = b * gap; out[s:s+len(one)] += one; s2 = s + int(0.18*SR); out[s2:s2+len(one)] += one * 0.6
    return out

def glitch(d=0.5):
    n = int(d*SR); x = np.zeros(n); i = 0
    while i < n:
        L = int(rng.uniform(0.01, 0.05) * SR)
        kind = rng.integers(3); tt = np.arange(L) / SR
        seg = [np.sign(np.sin(2*np.pi*rng.uniform(200, 2000)*tt)), rng.standard_normal(L), np.zeros(L)][kind]
        x[i:i+L] = seg[:max(0, min(L, n-i))]; i += L
    return hp(x, 300) * 0.6

def tick():
    tt = t(0.06); return np.sin(2*np.pi*3200*tt) * np.exp(-tt*150) + hp(rng.standard_normal(len(tt)), 4000)*np.exp(-tt*300)*0.4

def cash():
    a = ding(2093, 1.2) * 0.6; b = ding(2637, 1.2) * 0.6
    out = np.zeros(int(1.4*SR)); out[:len(a)] += a; s = int(0.09*SR); out[s:s+len(b)] += b[:len(out)-s]
    return out

def thud_soft():
    return lp(impact(0.6, 90, 50, 0.8, 0.1), 600)

def crowd(d=6.0, cheer=True):
    n = int(d*SR); tt = t(d)
    x = sum(bp(rng.standard_normal(n), lo, lo*2.2) * (0.5 + 0.5*np.sin(2*np.pi*rng.uniform(0.2, 1.2)*tt + rng.uniform(0, 6))) for lo in (250, 500, 900, 1700))
    e = np.minimum(1, tt/0.8) * np.minimum(1, (d-tt)/1.5) if cheer else np.ones(n)
    return np.stack([x*e, np.roll(x, 2000)*e], 1)

def terminal_blip(f=2400):
    tt = t(0.045); return np.sign(np.sin(2*np.pi*f*tt)) * 0.3 * np.exp(-tt * 60) * np.minimum(1, tt/0.002)

def terminal_typing(chars=24, cps=14):
    out = np.zeros(int((chars / cps + 0.3) * SR))
    for k in range(chars):
        b = lp(terminal_blip(rng.choice([2200, 2400, 2600])), 6000); s = int(k / cps * SR); out[s:s+len(b)] += b[:len(out)-s]
    return out

def phone_ring(rings=2):
    tt = t(1.0); burst = (np.sin(2*np.pi*1400*tt) + np.sin(2*np.pi*1750*tt)) * (np.sin(2*np.pi*20*tt) > 0) * 0.4
    burst *= np.minimum(1, tt/0.01) * np.minimum(1, (1.0-tt)/0.01)
    out = np.zeros(int(rings * 3.0 * SR))
    for r in range(rings): s = int(r * 3.0 * SR); out[s:s+len(burst)] += burst
    return bp(out, 300, 3400, 2)

def phone_vibrate(d=1.2):
    tt = t(d); return lp(np.sign(np.sin(2*np.pi*150*tt)), 400) * 0.5 * ((tt % 0.6) < 0.4)

def build_sfx():
    D = 'sfx'; paths = []
    paths.append(save(f'{D}/terminal_blip', terminal_blip(), 0.5))
    paths.append(save(f'{D}/terminal_typing_24chars', terminal_typing(), 0.5))
    paths.append(save(f'{D}/phone_ring', phone_ring(), 0.6, rev=(0.6, 0.1, 6000)))
    paths.append(save(f'{D}/phone_vibrate', phone_vibrate(), 0.7))
    for i, (d, f0, f1, q) in enumerate([(0.45, 400, 5000, 1.3), (0.7, 250, 3000, 1.0), (1.0, 180, 2400, 0.9), (0.35, 900, 7000, 1.6)]):
        paths.append(save(f'{D}/whoosh_{["fast","mid","long","tiny"][i]}', whoosh(d, f0, f1, q), 0.8))
    paths.append(save(f'{D}/whoosh_reverse', whoosh(0.8, 300, 4000, 1.1)[::-1], 0.8))
    paths.append(save(f'{D}/impact_heavy', impact(2.0, 120, 36, 1.0, 0.7), 0.95, rev=(1.5, 0.18, 3000)))
    paths.append(save(f'{D}/impact_light', impact(0.8, 160, 60, 0.6, 0.5), 0.85))
    paths.append(save(f'{D}/impact_punch', impact(0.5, 200, 70, 0.8, 1.0), 0.9))
    fh, off = flash_hit(); paths.append(save(f'{D}/flash_hit_hitAt{int(off*1000)}ms', fh, 0.95, rev=(2.2, 0.25, 6000)))
    paths.append(save(f'{D}/slowmo_ring', slowmo_ring(), 0.85, rev=(2.5, 0.3, 3000)))
    paths.append(save(f'{D}/ding_high', ding(1318.5), 0.75, rev=(1.6, 0.2, 7000)))
    paths.append(save(f'{D}/ding_soft', ding(880, 2.2, 0.5), 0.7, rev=(1.8, 0.25, 5000)))
    paths.append(save(f'{D}/ting_idea', ding(2093, 1.5), 0.6, rev=(1.2, 0.2, 9000)))
    paths.append(save(f'{D}/cash_register', cash(), 0.7, rev=(1.0, 0.15, 8000)))
    paths.append(save(f'{D}/pop', pop(), 0.8)); paths.append(save(f'{D}/pop_low', pop(500), 0.8))
    paths.append(save(f'{D}/ui_click', ui_click(), 0.6)); paths.append(save(f'{D}/type_key', type_key(), 0.6))
    paths.append(save(f'{D}/tick', tick(), 0.6))
    paths.append(save(f'{D}/riser_4s', riser(4.0), 0.85, rev=(1.5, 0.2, 6000)))
    paths.append(save(f'{D}/riser_2s', riser(2.0, 200, 2000), 0.85, rev=(1.2, 0.2, 6000)))
    paths.append(save(f'{D}/downer', downer(), 0.85, rev=(1.8, 0.25, 2500)))
    paths.append(save(f'{D}/heartbeat', heartbeat(), 0.9))
    paths.append(save(f'{D}/glitch', glitch(), 0.7))
    paths.append(save(f'{D}/thud_soft', thud_soft(), 0.8))
    paths.append(save(f'{D}/crowd_cheer', crowd(6), 0.6, rev=(2.5, 0.35, 4000)))
    # typing sequence 2s
    seq = np.zeros(int(2.2*SR))
    for k in range(18):
        s = max(0, int((k*0.11 + rng.uniform(-0.02, 0.02)) * SR)) + 200; kk = type_key(); e = min(len(seq), s+len(kk)); seq[s:e] += kk[:e-s]
    paths.append(save(f'{D}/typing_2s', seq, 0.6))
    return paths

if __name__ == '__main__':
    for p in build_sfx(): print(p)
