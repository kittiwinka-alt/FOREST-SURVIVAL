"""
audio.py — ระบบเสียง (procedural, ไม่ต้องใช้ไฟล์เสียงภายนอก)
"""
import math
import random
import struct
import wave
import io
import pygame


def _build_sound(samples, sr=22050):
    """แปลงลิสต์ตัวเลขเป็น pygame.mixer.Sound"""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(s)))) for s in samples))
    buf.seek(0)
    return pygame.mixer.Sound(buf)


def _gen_sounds():
    """สร้าง sound effects แบบ procedural"""
    sr = 22050

    def sine(f, dur, vol=0.4, env=True):
        n = int(sr * dur)
        out = []
        for i in range(n):
            e = max(0, 1 - (i / n) ** 0.5) if env else 1.0
            out.append(vol * 32767 * math.sin(2 * math.pi * f * i / sr) * e)
        return out

    def noise(dur, vol=0.2):
        rng2 = random.Random(42)
        n = int(sr * dur)
        return [vol * 32767 * rng2.uniform(-1, 1) * (1 - i / n) ** 0.3 for i in range(n)]

    def chord(freqs, dur, vol=0.25):
        n = int(sr * dur)
        return [vol * 32767 / len(freqs) * sum(math.sin(2 * math.pi * f * i / sr) for f in freqs)
                * (1 - (i / n) ** 0.4) for i in range(n)]

    def footstep(surface_type="grass", vol=0.32):
        """เสียงเดินเท้าแบบ realistic"""
        n = int(sr * 0.18)
        buf = [0.0] * n
        rng_fs = random.Random(hash(surface_type) & 0xFFFF)
        heel_len  = int(sr * 0.045)
        heel_freq = {"grass": 120, "dirt": 95, "stone": 180, "wood": 140}.get(surface_type, 110)
        for i in range(min(heel_len, n)):
            env = (1 - i / heel_len) ** 1.8
            buf[i] += 0.55 * math.sin(2 * math.pi * heel_freq * i / sr) * env
            buf[i] += 0.25 * math.sin(2 * math.pi * (heel_freq * 0.5) * i / sr) * env
        toe_start = int(sr * 0.05)
        toe_freq  = {"grass": 380, "dirt": 320, "stone": 600, "wood": 520}.get(surface_type, 360)
        toe_len   = int(sr * 0.03)
        for i in range(toe_len):
            si = toe_start + i
            if si >= n: break
            env = (1 - i / toe_len) ** 2.2
            buf[si] += 0.30 * math.sin(2 * math.pi * toe_freq * i / sr) * env
        tex_vol = {"grass": 0.18, "dirt": 0.14, "stone": 0.08, "wood": 0.12}.get(surface_type, 0.15)
        tex_len = int(sr * 0.12)
        for i in range(min(tex_len, n)):
            buf[i] += tex_vol * rng_fs.uniform(-1, 1) * (1 - i / tex_len) ** 0.6
        if surface_type in ("grass", "dirt"):
            rustle_len = int(sr * 0.10)
            for i in range(min(rustle_len, n)):
                buf[i] += 0.10 * rng_fs.uniform(-1, 1) * math.sin(math.pi * i / rustle_len) ** 0.5
        mx = max(abs(x) for x in buf) or 1.0
        return [x / mx * vol * 32767 for x in buf]

    sounds = {}
    try:
        sounds["step_grass"] = _build_sound(footstep("grass", 0.30), sr)
        sounds["step_dirt"]  = _build_sound(footstep("dirt",  0.28), sr)
        sounds["step_stone"] = _build_sound(footstep("stone", 0.26), sr)
        sounds["step"]       = sounds["step_grass"]
        sounds["hit"]     = _build_sound(noise(0.15, 0.45), sr)
        sounds["swing"]   = _build_sound(
            [0.5 * 32767 * math.sin(2 * math.pi * (800 + i * 8) * i / sr) * (1 - i / int(sr * 0.07))
             for i in range(int(sr * 0.07))], sr)
        sounds["pickup"]  = _build_sound(sine(880, 0.12, 0.35), sr)
        sounds["craft"]   = _build_sound(chord([523, 659, 784], 0.4, 0.3), sr)
        sounds["levelup"] = _build_sound(chord([523, 659, 784, 1047], 0.5, 0.35), sr)
        sounds["death"]   = _build_sound(
            [0.4 * 32767 * math.sin(2 * math.pi * (300 - i * 0.4) * i / sr) * (1 - i / int(sr * 0.8))
             for i in range(int(sr * 0.8))], sr)
        sounds["click"]   = _build_sound(sine(660, 0.06, 0.28), sr)
        sounds["eat"]     = _build_sound(noise(0.1, 0.15), sr)
        sounds["drink"]   = _build_sound(sine(400, 0.18, 0.28), sr)
    except Exception as e:
        print(f"[SFX gen] {e}")
    return sounds


def _gen_bgm_loop(sr=22050):
    """สร้าง BGM ambient แบบ loopable (~8 วินาที)"""
    dur = 8.0
    n   = int(sr * dur)
    buf = [0.0] * n
    rng3 = random.Random(777)

    # Layer 1 — deep drone
    for i in range(n):
        t = i / sr
        buf[i] += 0.12 * math.sin(2 * math.pi * 55 * t) * (0.7 + 0.3 * math.sin(2 * math.pi * 0.15 * t))
        buf[i] += 0.07 * math.sin(2 * math.pi * 110 * t + 0.8)

    # Layer 2 — melodic arpeggio (pentatonic)
    notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25]
    arp_times = [i * (dur / 16) for i in range(16)]
    for at in arp_times:
        freq = rng3.choice(notes)
        ns   = int(at * sr)
        ne   = min(n, ns + int(sr * 0.55))
        for i in range(ns, ne):
            env = math.sin(math.pi * (i - ns) / (ne - ns))
            buf[i] += 0.08 * math.sin(2 * math.pi * freq * (i - ns) / sr) * env

    # Layer 3 — bird chirps
    chirp_times = sorted(rng3.uniform(0, dur) for _ in range(10))
    for ct in chirp_times:
        f0   = rng3.uniform(1800, 3200)
        cs   = int(ct * sr)
        clen = int(sr * 0.09)
        ce   = min(n, cs + clen)
        for i in range(cs, ce):
            fq  = f0 * (1 + 0.4 * (i - cs) / clen)
            env = math.sin(math.pi * (i - cs) / clen)
            buf[i] += 0.07 * math.sin(2 * math.pi * fq * (i - cs) / sr) * env

    # Layer 4 — soft percussion
    for _ in range(18):
        ts   = int(rng3.uniform(0, dur - 0.15) * sr)
        tlen = int(sr * 0.12)
        for i in range(min(tlen, n - ts)):
            buf[ts + i] += 0.06 * rng3.uniform(-1, 1) * (1 - i / tlen) ** 1.5

    # Normalize + crossfade edges
    mx  = max(abs(x) for x in buf) or 1.0
    buf = [x / mx * 0.45 for x in buf]
    fade = int(sr * 0.3)
    for i in range(fade):
        t2 = i / fade
        buf[i]       = buf[i] * t2
        buf[n - 1 - i] = buf[n - 1 - i] * t2

    samples = [max(-32767, min(32767, int(x * 32767))) for x in buf]
    raw = b"".join(struct.pack("<h", s) for s in samples)
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(raw)
    wav_buf.seek(0)
    return wav_buf


class Audio:
    """จัดการ BGM และ SFX ทั้งหมด"""

    def __init__(self):
        self.sfx_on  = True
        self.bgm_on  = True
        self.sfx_vol = 0.65
        self.bgm_vol = 0.40
        self.on  = True           # alias สำหรับ backward compat
        self.vol = self.sfx_vol
        self.sounds    = {}
        self.bgm_chan  = None
        self.bgm_sound = None

        try:
            pygame.mixer.init(22050, -16, 2, 1024)
            pygame.mixer.set_num_channels(16)
            self.sounds = _gen_sounds()
            self._init_bgm()
        except Exception as e:
            print(f"[Audio init] {e}")

    def _init_bgm(self):
        try:
            wav_buf        = _gen_bgm_loop()
            self.bgm_sound = pygame.mixer.Sound(wav_buf)
            self.bgm_sound.set_volume(self.bgm_vol)
            self.bgm_chan  = pygame.mixer.Channel(0)
            self.bgm_chan.play(self.bgm_sound, loops=-1, fade_ms=1500)
        except Exception as e:
            print(f"[BGM init] {e}")

    def set_bgm_vol(self, v):
        self.bgm_vol = max(0.0, min(1.0, v))
        if self.bgm_sound:
            self.bgm_sound.set_volume(self.bgm_vol if self.bgm_on else 0.0)

    def set_sfx_vol(self, v):
        self.sfx_vol = max(0.0, min(1.0, v))
        self.vol = self.sfx_vol

    def toggle_bgm(self):
        self.bgm_on = not self.bgm_on
        if self.bgm_sound:
            self.bgm_sound.set_volume(self.bgm_vol if self.bgm_on else 0.0)

    def toggle_sfx(self):
        self.sfx_on = not self.sfx_on
        self.on = self.sfx_on

    def play(self, name):
        if not self.sfx_on: return
        s = self.sounds.get(name)
        if s:
            s.set_volume(self.sfx_vol)
            try:
                if not s.get_num_channels():   # เล่นเฉพาะถ้าไม่มีช่องที่กำลังเล่นอยู่
                    s.play()
                elif name in ("swing", "levelup", "craft", "pickup", "click", "death"):
                    s.play()   # เสียง UI เล่นเสมอ
            except: pass
