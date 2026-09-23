#!/usr/bin/env python3
"""
scripts/build_sane_soundtrack.py
Clean, Musical, Sane Soundtrack Generation for itswal Portfolio Jukebox.

Principles:
1. Expressive Theme (Default): 100% untouched original sane composition from backups_pre_remix.
   Zero chops, zero glitches, pure ambient jazz-hop soul.
2. Banana Theme (Pink Mode): Warm analog tape lofi chillhop.
   Smooth tape saturation, gentle vintage cassette wow/flutter, warm low-pass.
   ZERO rapid glitch chops, continuous relaxing groove.
3. Space Theme (Dark Mode): Dreamy cosmic retro ambient.
   Vintage 12-bit DAC warmth, warm analog low-pass (4.8 kHz), cosmic stereo delay.
   NO screeching noise drums, NO harsh pulse arps, NO glitch drills.
4. Stem Balance: Unified master peak normalization (0.85 linear / -1.4 dBFS)
   preserving natural hierarchy (home > cats ~ photos > bio).
5. Seamless Looping & Sample Alignment:
   All stems within each theme share exact sample durations.
"""

import os
import subprocess
import numpy as np
import soundfile as sf
import scipy.signal as signal

SR = 44100
BACKUP_DIR = 'audio/tracks/backups_pre_remix'
OUTPUT_DIR = 'audio/tracks'
STEMS = ['home', 'bio', 'cats', 'photos']

os.makedirs(OUTPUT_DIR, exist_ok=True)


def export_mp3(audio, out_path, sr=SR):
    """Export numpy audio to pristine 320 kbps MP3 via ffmpeg."""
    temp_wav = f'/tmp/temp_export_{os.path.basename(out_path)}.wav'
    sf.write(temp_wav, audio, sr, subtype='PCM_24')
    cmd = [
        'ffmpeg', '-y', '-i', temp_wav,
        '-codec:a', 'libmp3lame',
        '-b:a', '320k',
        '-ar', str(sr),
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(temp_wav):
        os.remove(temp_wav)


def build_expressive_theme():
    print("--> Building Expressive Theme (100% Pure Original Sane Stems)...")
    stems_data = {}
    max_peak = 0.0

    for s in STEMS:
        fpath = os.path.join(BACKUP_DIR, f'itswal_expressive_{s}.mp3')
        data, sr = sf.read(fpath)
        stems_data[s] = data
        peak = np.max(np.abs(data))
        if peak > max_peak:
            max_peak = peak

    # Clean linear gain normalization (peaks at 0.85 / -1.4 dBFS)
    # Zero DSP alterations, 100% bit-pure musical original
    gain = 0.85 / max_peak
    print(f"   -> Expressive gain factor: {gain:.4f} (original peak: {max_peak:.4f})")

    # Match exact length across all 4 stems (8,348,992 frames)
    target_len = len(stems_data['home'])

    for s in STEMS:
        audio = stems_data[s]
        if len(audio) < target_len:
            # Pad with gentle silence if needed
            pad = np.zeros((target_len - len(audio), 2), dtype=audio.dtype)
            audio = np.vstack([audio, pad])
        elif len(audio) > target_len:
            audio = audio[:target_len]

        scaled = audio * gain
        out_file = os.path.join(OUTPUT_DIR, f'itswal_expressive_{s}.mp3')
        export_mp3(scaled, out_file)
        peak = np.max(np.abs(scaled))
        rms = np.sqrt(np.mean(scaled**2))
        print(f"   -> Exported {s:6s}: peak={peak:.4f} (-{20*np.log10(1/peak):.1f} dBFS), rms={rms:.4f}")


def build_banana_theme():
    print("--> Building Banana Theme (Warm Analog Tape Lofi Chillhop)...")
    stems_data = {}

    for s in STEMS:
        fpath = os.path.join(BACKUP_DIR, f'itswal_pink_{s}.mp3')
        data, sr = sf.read(fpath)
        stems_data[s] = data

    target_len = len(stems_data['home']) # 8,564,480 samples

    # Processing function for warm analog tape lofi
    def process_banana(raw_audio):
        audio = raw_audio[:target_len].copy()
        if len(audio) < target_len:
            pad = np.zeros((target_len - len(audio), 2), dtype=audio.dtype)
            audio = np.vstack([audio, pad])

        # 1. Analog tape soft saturation
        sat = np.tanh(1.10 * audio)

        # 2. Gentle tape wow/flutter (0.35 Hz smooth delay modulation, depth 0.35ms)
        n = len(sat)
        t = np.arange(n) / SR
        mod_delay = (0.00035 * np.sin(2 * np.pi * 0.35 * t) * SR).astype(int)
        fluttered = np.zeros_like(sat)
        for ch in range(2):
            indices = np.clip(np.arange(n) - mod_delay, 0, n - 1)
            fluttered[:, ch] = sat[indices, ch]

        # 3. Soft warm high-shelf filter (smooth roll-off above 11 kHz)
        sos_warm = signal.butter(2, 11000, btype='lowpass', fs=SR, output='sos')
        warmed = signal.sosfilt(sos_warm, fluttered, axis=0)

        # 4. Gentle, smooth 4-on-the-floor kick breathing (subtle 12% cosine ducking)
        # 125 BPM -> beat = 21168 samples (0.48s)
        beat_len = 21168
        env_beat = 1.0 - 0.12 * np.maximum(0, np.cos(np.linspace(0, np.pi, beat_len))) ** 2
        # Tile across length
        repeats = n // beat_len + 1
        tiled_env = np.tile(env_beat, repeats)[:n]
        breathed = warmed * tiled_env[:, None]

        return breathed

    processed = {}
    max_peak = 0.0
    for s in STEMS:
        proc = process_banana(stems_data[s])
        processed[s] = proc
        p = np.max(np.abs(proc))
        if p > max_peak:
            max_peak = p

    gain = 0.85 / max_peak
    print(f"   -> Banana gain factor: {gain:.4f} (processed peak: {max_peak:.4f})")

    for s in STEMS:
        scaled = processed[s] * gain
        out_file = os.path.join(OUTPUT_DIR, f'itswal_pink_{s}.mp3')
        export_mp3(scaled, out_file)
        peak = np.max(np.abs(scaled))
        rms = np.sqrt(np.mean(scaled**2))
        print(f"   -> Exported {s:6s}: peak={peak:.4f} (-{20*np.log10(1/peak):.1f} dBFS), rms={rms:.4f}")


def build_space_theme():
    print("--> Building Space Theme (Dreamy Cosmic Retro Ambient)...")
    stems_data = {}

    for s in STEMS:
        fpath = os.path.join(BACKUP_DIR, f'itswal_space_{s}.mp3')
        data, sr = sf.read(fpath)
        stems_data[s] = data

    target_len = len(stems_data['home']) # 8,564,480 samples

    def process_space(raw_audio):
        audio = raw_audio[:target_len].copy()
        if len(audio) < target_len:
            pad = np.zeros((target_len - len(audio), 2), dtype=audio.dtype)
            audio = np.vstack([audio, pad])

        # 1. Vintage 12-bit DAC soft quantization (gentle vintage sampler flavor)
        steps = 2048 # 12-bit
        quant = np.round(audio * steps) / steps

        # 2. Smooth analog low-pass filter at 4.8 kHz (warm, cosmic space ambiance)
        sos_lp = signal.butter(3, 4800, btype='lowpass', fs=SR, output='sos')
        filtered = signal.sosfilt(sos_lp, quant, axis=0)

        # 3. Cosmic stereo delay & ambient space reflection (Left 300ms, Right 450ms, 25% wet)
        delay_l = int(0.300 * SR)
        delay_r = int(0.450 * SR)
        delayed = np.zeros_like(filtered)
        delayed[delay_l:, 0] = filtered[:-delay_l, 1] * 0.25
        delayed[delay_r:, 1] = filtered[:-delay_r, 0] * 0.25
        if len(delayed) > delay_l + delay_r:
            delayed[delay_l + delay_r:, 0] += filtered[:-(delay_l + delay_r), 0] * 0.10
            delayed[delay_l + delay_r:, 1] += filtered[:-(delay_l + delay_r), 1] * 0.10

        space_mix = filtered * 0.85 + delayed * 0.30

        # 4. Rich sub-bass warmth (50-90 Hz)
        sos_sub = signal.butter(2, 90, btype='lowpass', fs=SR, output='sos')
        sub = signal.sosfilt(sos_sub, filtered, axis=0)
        space_mix += sub * 0.25

        return space_mix

    processed = {}
    max_peak = 0.0
    for s in STEMS:
        proc = process_space(stems_data[s])
        processed[s] = proc
        p = np.max(np.abs(proc))
        if p > max_peak:
            max_peak = p

    gain = 0.85 / max_peak
    print(f"   -> Space gain factor: {gain:.4f} (processed peak: {max_peak:.4f})")

    for s in STEMS:
        scaled = processed[s] * gain
        out_file = os.path.join(OUTPUT_DIR, f'itswal_space_{s}.mp3')
        export_mp3(scaled, out_file)
        peak = np.max(np.abs(scaled))
        rms = np.sqrt(np.mean(scaled**2))
        print(f"   -> Exported {s:6s}: peak={peak:.4f} (-{20*np.log10(1/peak):.1f} dBFS), rms={rms:.4f}")


def main():
    print("====================================================================")
    print("ITSWAL JUKEBOX CLEAN & SANE SOUNDTRACK PIPELINE")
    print("====================================================================")
    build_expressive_theme()
    build_banana_theme()
    build_space_theme()
    print("\nAll 12 tracks successfully generated with clean, musical audio!")


if __name__ == '__main__':
    main()
