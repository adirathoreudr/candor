"""Original soundtrack for the Candor brag video: music and effects written as one piece.

A minor, 92 BPM, 48 kHz stereo. Pad (Am, Fmaj7, C, G) + sub; plucked arpeggio from the reveal;
soft kick and offbeat air from the time-travel scene to the actions scene; everything ducks a little
under the kick. Effects are in key and sit under the music: key ticks while text types, an A/E bell
when an answer lands, airy swells on scene changes, a muted pluck when the reminder pin drops.
Deterministic (fixed seed).  usage: python music.py out.wav
"""
import sys
import wave

import numpy as np

SR, DUR, BPM = 48000, 75.0, 92
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(7)
t = np.arange(N) / SR
L, R = np.zeros(N), np.zeros(N)


def hz(note):   # MIDI note -> Hz
    return 440.0 * 2 ** ((note - 69) / 12)


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.cos((pan + 1) * np.pi / 4)
    R[i:i + len(sig)] += sig * np.sin((pan + 1) * np.pi / 4)


def onepole(x, cutoff):   # gentle low-pass
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):        # fine for short signals only
        acc = (1 - a) * x[k] + a * acc
        y[k] = acc
    return y


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain)
    ai = min(n, int(a * SR))
    e[:ai] = np.linspace(0, sustain, ai)
    ri = min(n, int(r * SR))
    e[n - ri:] *= np.linspace(1, 0, ri)
    return e


# ---------- harmony ----------
CHORDS = [[57, 60, 64, 69], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 67]]   # Am, Fmaj7, C, G (voiced)
ROOTS = [33, 29, 36, 31]
BAR = 4 * BEAT
CHORD_LEN = 2 * BAR


def chord_at(time):
    return int(time // CHORD_LEN) % 4


def section_gain(time):   # arrangement curve
    if time < 7.0: return 0.55
    if time < 14.0: return 0.8
    if time < 68.0: return 1.0
    return max(0.0, 1.0 - (time - 71.5) / 3.5) if time > 71.5 else 0.9


# ---------- pad ----------
n_chords = int(np.ceil(DUR / CHORD_LEN)) + 1
for c in range(n_chords):
    start = c * CHORD_LEN - 0.4
    n = int((CHORD_LEN + 1.6) * SR)
    tt = np.arange(n) / SR
    sig = np.zeros(n)
    for j, note in enumerate(CHORDS[c % 4]):
        f = hz(note)
        for det, ph in ((-0.0035, 0.0), (0.0035, 1.3)):
            ff = f * (1 + det)
            # soft, few-harmonic tone with slow movement
            sig += (np.sin(2 * np.pi * ff * tt + ph) + 0.28 * np.sin(4 * np.pi * ff * tt + ph)
                    + 0.08 * np.sin(6 * np.pi * ff * tt)) * (1 + 0.15 * np.sin(2 * np.pi * 0.17 * tt + j))
    sig *= env(n, 1.1, 1.6) * 0.035 * section_gain(max(0, start + 1))
    add(sig, max(0, start), pan=-0.25)
    add(sig * 0.9, max(0, start + 0.012), pan=0.25)

# ---------- sub ----------
for b in range(int(DUR / BAR) + 1):
    time = b * BAR
    root = ROOTS[chord_at(time)]
    for beat in (0, 2):
        start = time + beat * BEAT
        if start >= DUR - 2.5:
            continue
        n = int(1.2 * SR)
        tt = np.arange(n) / SR
        sig = np.sin(2 * np.pi * hz(root + 12) * tt) * np.exp(-tt * 2.2) * 0.11 * section_gain(start)
        add(sig, start)

# ---------- pluck arpeggio (from the reveal) ----------
PATTERN = [0, 2, 3, 1, 2, 3, 1, 2]
step = BEAT / 2
k = 0
time = 7.35
while time < DUR - 3.0:
    notes = CHORDS[chord_at(time)]
    note = notes[PATTERN[k % 8]] + 12
    n = int(0.9 * SR)
    tt = np.arange(n) / SR
    f = hz(note)
    tone = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 9)
    sig = tone * np.exp(-tt * 5.5) * 0.045 * section_gain(time) * (0.85 + 0.3 * rng.random())
    add(sig, time, pan=0.35 * np.sin(k * 0.9))
    time += step
    k += 1

# ---------- kick and air (time travel to actions) ----------
kick_env = np.zeros(N)
time = 14.0
while time < 67.6:
    n = int(0.45 * SR)
    tt = np.arange(n) / SR
    f = 46 + 70 * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) * np.exp(-tt * 9) * 0.17
    add(sig, time)
    i = int(time * SR)
    d = min(N - i, int(0.3 * SR))
    kick_env[i:i + d] = np.maximum(kick_env[i:i + d], np.exp(-np.arange(d) / SR * 12))
    hat_t = time + BEAT / 2
    hn = int(0.05 * SR)
    noise = rng.standard_normal(hn)
    noise = noise - onepole(noise, 6000)          # high-pass by subtraction
    add(noise * np.exp(-np.arange(hn) / SR * 70) * 0.012, hat_t, pan=0.3)
    time += BEAT

duck = 1 - 0.28 * kick_env                        # music leans back under the kick
L *= duck
R *= duck

# ---------- effects ----------
def bell(start, notes=(81, 88), gain=0.05):
    for note in notes:
        f = hz(note)
        n = int(2.4 * SR)
        tt = np.arange(n) / SR
        sig = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.6) + 0.25 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 6)
               + 0.1 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 11))
        add(sig * gain, start, pan=0.15 if note % 2 else -0.15)


def swell(start, dur=1.0, gain=0.03):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    noise = onepole(noise, 2200) - onepole(noise, 400)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    add(noise * shape * gain, start - dur * 0.6, pan=-0.2)
    add(noise[::-1] * shape * gain, start - dur * 0.6, pan=0.2)


def ticks(start, count, cps, gain=0.010):
    for c in range(count):
        n = int(0.012 * SR)
        noise = rng.standard_normal(n)
        noise = noise - onepole(noise, 3000)
        add(noise * np.exp(-np.arange(n) / SR * 400) * gain * (0.7 + 0.6 * rng.random()), start + c / cps,
            pan=rng.uniform(-0.2, 0.2))


def pluck(start, note=69, gain=0.07):
    n = int(1.2 * SR)
    tt = np.arange(n) / SR
    f = hz(note)
    add((np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 12)) * np.exp(-tt * 4) * gain, start)


ticks(0.25, 19, 15)                          # "When is the launch?"
for s in (7.0, 14.0, 32.0, 44.0, 57.0, 68.0):
    swell(s)
bell(7.5, (69, 76, 81), 0.04)               # wordmark
for s in (16.7, 22.8, 28.4):                 # answers land as the playhead stops
    bell(s)
ticks(32.45, 32, 26)                         # "Did John agree to cut dark mode?"
bell(36.8, (76, 81))
for s in (45.1, 47.5, 49.9):
    bell(s, (81,), 0.03)
ticks(57.6, 61, 30)                          # the reminder command
pluck(60.7, 69, 0.08)                        # pin drops at 8:00
ticks(63.6, 32, 28)                          # the delete command
pluck(64.9, 57, 0.06)                        # confirm
bell(68.3, (69, 76, 81, 88), 0.03)          # proof
bell(71.8, (57, 64, 69), 0.04)              # wordmark again

# ---------- reverb (convolution with decaying stereo noise) and master ----------
ir_n = int(2.3 * SR)
decay = np.exp(-np.arange(ir_n) / SR * 2.8)
irL, irR = rng.standard_normal(ir_n) * decay, rng.standard_normal(ir_n) * decay
irL[:int(0.02 * SR)] = 0
irR[:int(0.02 * SR)] = 0
size = 1 << int(np.ceil(np.log2(N + ir_n)))
def conv(x, ir):
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:N]
wetL, wetR = conv(L, irL), conv(R, irR)
wet_gain = 0.22 / max(np.abs(wetL).max(), np.abs(wetR).max(), 1e-9) * max(np.abs(L).max(), 1e-9)
L, R = L + wetL * wet_gain, R + wetR * wet_gain

fade = np.ones(N)
fade[:int(0.25 * SR)] = np.linspace(0, 1, int(0.25 * SR))
fade[-int(2.0 * SR):] *= np.linspace(1, 0, int(2.0 * SR))
L, R = L * fade, R * fade
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(1.3 * L / peak) / np.tanh(1.3), np.tanh(1.3 * R / peak) / np.tanh(1.3)   # soft ceiling
pcm = (np.stack([L, R], axis=1) * 0.89 * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], f"{DUR:.0f}s")
