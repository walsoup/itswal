#!/usr/bin/env python3
"""
scripts/build_remixes.py
High-Fidelity Musical Remix Pipeline for itswal Portfolio Jukebox.

Styles:
1. Space Theme (Dark Mode) -> 8-Bit / Bitcrush / Chiptune Retro Arcade Remix
   - Sample rate decimation + 7-bit quantization (NES/Game Boy DAC grit)
   - 25% pulse-wave tracker arpeggios in key (F Major / D Minor: F, A, C, E, D)
   - Retro 15-bit LFSR noise drum hits (8-bit kick, snare, hi-hat)
   - Spliced glitch/stutter chops and laser decimation sweeps on phrase turnarounds
2. Banana Theme (Pink Mode) -> Spliced Bouncy Future-Funk / Lofi Chops
   - Spliced beat-repeats and 1/8th & 1/16th stutter edits on phrase turnarounds
   - Pitch/tempo bounce, tape flutter/vibrato (modulated delay line + tape sat)
   - Reverse chord swell chops swelling into downbeats, future-funk sidechain bounce
3. Expressive Theme (Default) -> Spliced Breakbeat / Glitch-Hop Chops
   - Spliced bar rearrangements (kick retriggering, jump cuts)
   - 1/16th and 1/32nd beat rolls/stutters on turnaround bars
   - Reverse chops into downbeats
   - 16th-note rhythmic gating (trance-gate / glitch chop)

Continuity & Alignment:
- Identical tempo grid (125.0 BPM, 84672 samples/bar)
- Exact same slice decisions across section stems (home, bio, cats, photos)
- Identical sample duration for all stems within each theme
"""

import os
import sys
import subprocess
import numpy as np
import soundfile as sf
import scipy.signal as signal

SR = 44100
BAR = 84672           # 125.0 BPM at 44.1 kHz (1.92s)
BEAT = 21168          # 1/4 note (0.48s)
EIGHTH = 10584        # 1/8 note (0.24s)
SIXTEENTH = 5292      # 1/16 note (0.12s)
THIRTYSECOND = 2646   # 1/32 note (0.06s)
FADE_SAMPLES = 64     # ~1.45ms click-prevention fade

BACKUP_DIR = 'audio/tracks/backups_pre_remix'
OUTPUT_DIR = 'audio/tracks'
TEMP_DIR = '/tmp/remix_temp'
os.makedirs(TEMP_DIR, exist_ok=True)


def smooth_edges(audio, n_fade=FADE_SAMPLES):
    """Apply micro-cosine fade at beginning and end of slice to avoid clicks."""
    out = audio.copy()
    if len(out) < 2 * n_fade:
        return out
    fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, n_fade)))
    fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, n_fade)))
    out[:n_fade] *= fade_in[:, None]
    out[-n_fade:] *= fade_out[:, None]
    return out


# ─── DSP Helpers ─────────────────────────────────────────────────────────────

def apply_bitcrush(audio, bits=7, downsample=3, dry_wet=0.85):
    """
    Crunchy NES / Game Boy DAC grit:
    - Zero-order hold sample rate decimation
    - Discrete bit depth quantization
    - Vintage DAC soft saturation
    """
    n = len(audio)
    idx = (np.arange(n) // downsample) * downsample
    held = audio[idx]
    
    steps = 2 ** (bits - 1)
    quant = np.round(held * steps) / steps
    crushed = np.tanh(1.25 * quant)
    return dry_wet * crushed + (1.0 - dry_wet) * audio


def generate_lfsr_noise(num_samples=SR * 5):
    """15-bit Galois LFSR noise generator (authentic Game Boy / NES noise channel)."""
    reg = 0x7FFF
    noise = np.zeros(num_samples, dtype=np.float32)
    for i in range(num_samples):
        if i % 2 == 0:
            feedback = (reg & 1) ^ ((reg >> 1) & 1)
            reg = (reg >> 1) | (feedback << 14)
            val = 1.0 if (reg & 1) else -1.0
        noise[i] = val
    return noise

LFSR_NOISE = generate_lfsr_noise()


def make_chiptune_drums(bar_count, tempo_offset):
    """Synthesize authentic retro chiptune drums (LFSR noise snare/hat, 4-bit tri kick)."""
    total_len = tempo_offset + bar_count * BAR + BAR
    drums = np.zeros((total_len, 2), dtype=np.float32)
    
    # 1. Hat
    hat_len = int(SR * 0.035)
    t_hat = np.arange(hat_len) / SR
    env_hat = np.exp(-t_hat / 0.007)
    sos_hat = signal.butter(2, 4500, btype='highpass', fs=SR, output='sos')
    filt_hat = signal.sosfilt(sos_hat, LFSR_NOISE[:hat_len])
    hat_sound = np.round(filt_hat * 16) / 16 * env_hat * 0.35
    
    # 2. Snare
    snare_len = int(SR * 0.18)
    t_snare = np.arange(snare_len) / SR
    env_snare = np.exp(-t_snare / 0.038)
    f_snare = 220.0 * np.exp(-t_snare / 0.03) + 70.0
    phase_snare = np.cumsum(f_snare) / SR
    tone_snare = np.sign(np.sin(2 * np.pi * phase_snare)) * 0.35
    noise_snare = LFSR_NOISE[:snare_len] * 0.65
    snare_sound = np.round((tone_snare + noise_snare) * 16) / 16 * env_snare * 0.45
    
    # 3. Kick
    kick_len = int(SR * 0.18)
    t_kick = np.arange(kick_len) / SR
    env_kick = np.exp(-t_kick / 0.045)
    f_kick = 140.0 * np.exp(-t_kick / 0.025) + 40.0
    phase_kick = np.cumsum(f_kick) / SR
    tri_kick = 2.0 * np.abs(2.0 * (phase_kick % 1.0) - 1.0) - 1.0
    quant_kick = np.round(tri_kick * 8) / 8
    click_kick = np.zeros(kick_len)
    click_kick[:int(SR*0.004)] = 0.5 * LFSR_NOISE[:int(SR*0.004)]
    kick_sound = (quant_kick + click_kick) * env_kick * 0.55
    
    for b in range(bar_count):
        bar_start = tempo_offset + b * BAR
        # Kick on 1 and 3
        k1 = bar_start
        k2 = bar_start + 2 * BEAT
        drums[k1 : k1 + kick_len, 0] += kick_sound
        drums[k1 : k1 + kick_len, 1] += kick_sound
        drums[k2 : k2 + kick_len, 0] += kick_sound
        drums[k2 : k2 + kick_len, 1] += kick_sound
        
        # Snare on 2 and 4
        s1 = bar_start + BEAT
        s2 = bar_start + 3 * BEAT
        drums[s1 : s1 + snare_len, 0] += snare_sound * 0.95
        drums[s1 : s1 + snare_len, 1] += snare_sound * 1.05
        drums[s2 : s2 + snare_len, 0] += snare_sound * 1.05
        drums[s2 : s2 + snare_len, 1] += snare_sound * 0.95
        
        # Hats on 8th notes
        for h in range(8):
            pos = bar_start + h * EIGHTH
            drums[pos : pos + hat_len, 0] += hat_sound * 0.8
            drums[pos : pos + hat_len, 1] += hat_sound * 1.1
            
    return drums


def make_chiptune_arps(bar_count, tempo_offset, oct_shift=0, duty=0.25):
    """
    Synthesize authentic 25% duty pulse-wave tracker arpeggios in key (F Major / D Minor).
    Chord Progression:
      Bar 0: D minor (D4, F4, A4, C5)
      Bar 1: Bb major (Bb3, D4, F4, A4)
      Bar 2: F major (F3, A3, C4, E4)
      Bar 3: C major (C4, E4, G4, Bb4)
    """
    scale_multiplier = 2.0 ** oct_shift
    chords = [
        [293.66, 349.23, 440.00, 523.25], # Dm
        [233.08, 293.66, 349.23, 440.00], # Bb
        [174.61, 220.00, 261.63, 329.63], # F
        [261.63, 329.63, 392.00, 466.16], # C
    ]
    chords = [[f * scale_multiplier for f in ch] for ch in chords]
    
    total_len = tempo_offset + bar_count * BAR + BAR
    arps = np.zeros((total_len, 2), dtype=np.float32)
    
    sub_note_samples = SIXTEENTH // 3 # 1764 samples (~40ms per arpeggio note)
    
    for b in range(bar_count):
        chord = chords[b % 4]
        bar_start = tempo_offset + b * BAR
        
        for step in range(16): # 16 sixteenth notes
            step_start = bar_start + step * SIXTEENTH
            for sub in range(3):
                freq = chord[(step + sub) % len(chord)]
                note_start = step_start + sub * sub_note_samples
                note_len = sub_note_samples
                
                t = np.arange(note_len) / SR
                phase = (t * freq) % 1.0
                pulse = np.where(phase < duty, 0.7, -0.7)
                env = np.exp(-t / 0.05)
                
                # Pan slight ping-pong
                pan_l = 0.5 + 0.3 * np.sin(step * 0.7)
                pan_r = 1.0 - pan_l
                
                arps[note_start : note_start + note_len, 0] += pulse * env * pan_l * 0.28
                arps[note_start : note_start + note_len, 1] += pulse * env * pan_r * 0.28
                
    return arps


def apply_tape_flutter_and_bounce(audio, flutter_depth_ms=1.4, flutter_rate_hz=4.5):
    """Modulated delay line tape flutter & subtle analog warmth."""
    n = len(audio)
    t = np.arange(n) / SR
    base_delay_samples = int(SR * 0.008) # 8ms base delay
    mod = (flutter_depth_ms / 1000.0 * SR) * (
        np.sin(2 * np.pi * flutter_rate_hz * t) + 
        0.35 * np.sin(2 * np.pi * 0.8 * t)
    )
    delay_samples = base_delay_samples + mod
    
    idx_float = np.arange(n) - delay_samples
    idx_floor = np.floor(idx_float).astype(int)
    idx_floor = np.clip(idx_floor, 0, n - 2)
    frac = (idx_float - idx_floor)[:, None]
    
    delayed = (1.0 - frac) * audio[idx_floor] + frac * audio[idx_floor + 1]
    # Lofi tape saturation: mild cubic saturation with subtle even harmonic warmth
    saturated = np.tanh(1.12 * delayed) + 0.04 * (delayed ** 2)
    return saturated


def apply_sidechain_bounce(bar_audio):
    """Future-funk / French house sidechain pumping groove on beats 1 and 3."""
    out = bar_audio.copy()
    t_beat = (np.arange(BEAT) / SR)
    pump_curve = 1.0 - 0.35 * np.exp(-t_beat / 0.085)
    
    # Apply to beat 1 and beat 3
    out[0 : BEAT] *= pump_curve[:, None]
    out[2 * BEAT : 3 * BEAT] *= pump_curve[:, None]
    return out


# ─── REMIX BUILDERS ──────────────────────────────────────────────────────────

def remix_space_theme():
    """
    Space Theme (Dark Mode) -> 8-Bit / Bitcrush / Chiptune Retro Arcade Remix
    - 7-bit quantization + sample rate decimation
    - Pulse wave arpeggios (Dm/F)
    - LFSR noise drums
    - Glitch/stutter chops on phrase turnarounds (every 4 bars)
    """
    print('--> Building Space Theme Remix (8-Bit / Bitcrush / Chiptune)...')
    stems = ['home', 'bio', 'cats', 'photos']
    raw_tracks = {}
    for s in stems:
        d, sr = sf.read(f'{BACKUP_DIR}/itswal_space_{s}.mp3')
        raw_tracks[s] = d
        
    target_len = 8564480 # common duration for space tracks
    for s in stems:
        if len(raw_tracks[s]) < target_len:
            pad = np.zeros((target_len - len(raw_tracks[s]), 2), dtype=np.float32)
            raw_tracks[s] = np.concatenate([raw_tracks[s], pad], axis=0)
        else:
            raw_tracks[s] = raw_tracks[s][:target_len]
            
    tempo_offset = 13230
    bar_count = (target_len - tempo_offset) // BAR # 100 bars
    
    # 1. Synthesize chiptune musical layers
    drums = make_chiptune_drums(bar_count, tempo_offset)[:target_len]
    lead_arps = make_chiptune_arps(bar_count, tempo_offset, oct_shift=0, duty=0.25)[:target_len]
    high_arps = make_chiptune_arps(bar_count, tempo_offset, oct_shift=1, duty=0.125)[:target_len]
    mellow_arps = make_chiptune_arps(bar_count, tempo_offset, oct_shift=-1, duty=0.5)[:target_len]
    
    processed = {}
    for s in stems:
        # Bitcrush underlying stem (NES/Game Boy 7-bit DAC grit)
        crushed = apply_bitcrush(raw_tracks[s], bits=7, downsample=3, dry_wet=0.82)
        
        # Stem-specific instrumentation
        if s == 'home':
            mix = crushed * 0.70 + drums * 0.55 + lead_arps * 0.45
        elif s == 'bio':
            # Ambient/mellow: quiet crushed backing, gentle mellow arps, no heavy drums
            mix = crushed * 0.75 + mellow_arps * 0.35 + drums * 0.15
        elif s == 'cats':
            # Playful: sparkly high-register arps, lighter drums
            mix = crushed * 0.70 + high_arps * 0.40 + drums * 0.40
        elif s == 'photos':
            # Dreamy space: wide arpeggios, atmospheric crushed pads
            mix = crushed * 0.72 + lead_arps * 0.30 + high_arps * 0.25 + drums * 0.35
            
        processed[s] = mix
        
    # 2. Apply Spliced Glitch / Stutter Chops on Turnarounds (IDENTICALLY to all 4 stems!)
    for b in range(bar_count):
        bar_start = tempo_offset + b * BAR
        
        # Every 4th bar turnaround (bars 3, 7, 11, 15...)
        if b % 4 == 3:
            # Chop 1: Stutter edit on beat 4 (from 3*BEAT to 4*BEAT)
            # Take the 16th-note slice at beat 3.75, repeat 4x with bitcrush ramp
            slice_src_start = bar_start + 3 * BEAT - SIXTEENTH
            slice_src_end = bar_start + 3 * BEAT
            
            dest_start = bar_start + 3 * BEAT
            dest_end = bar_start + 4 * BEAT
            
            for s in stems:
                slice_data = smooth_edges(processed[s][slice_src_start:slice_src_end])
                # 4 repeats of the 16th slice
                stutter_4x = np.tile(slice_data, (4, 1))
                # Glitch ramp: accelerate bitcrush / volume
                ramp = np.linspace(0.8, 1.3, len(stutter_4x))[:, None]
                processed[s][dest_start:dest_end] = smooth_edges(stutter_4x * ramp)
                
        # Every 8th bar turnaround (bars 7, 15, 23...): Laser 32nd-note drill stutter
        if b % 8 == 7:
            slice_src_start = bar_start + 4 * BEAT - THIRTYSECOND * 2
            slice_src_end = bar_start + 4 * BEAT - THIRTYSECOND
            dest_start = bar_start + 4 * BEAT - THIRTYSECOND * 8 # full beat 4
            dest_end = bar_start + 4 * BEAT
            
            for s in stems:
                slice_32 = smooth_edges(processed[s][slice_src_start:slice_src_end])
                stutter_8x = np.tile(slice_32, (8, 1))
                # Bit-decimation dive
                decimated_stutter = apply_bitcrush(stutter_8x, bits=5, downsample=6, dry_wet=0.95)
                processed[s][dest_start:dest_end] = smooth_edges(decimated_stutter * 1.1)

    # 3. Normalize & Export
    for s in stems:
        # Peak normalization to -1.0 dBFS (0.89)
        peak = np.max(np.abs(processed[s]))
        if peak > 0:
            processed[s] = processed[s] * (0.89 / peak)
            
        wav_path = f'{TEMP_DIR}/space_{s}.wav'
        mp3_path = f'{OUTPUT_DIR}/itswal_space_{s}.mp3'
        sf.write(wav_path, processed[s], SR)
        subprocess.run(['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-b:a', '320k', mp3_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f'   -> Rendered {mp3_path} ({len(processed[s])} samples)')


def remix_pink_theme():
    """
    Banana Theme (Pink Mode) -> Spliced Bouncy Future-Funk / Lofi Chops
    - Spliced beat-repeats and stutter edits (1/8th & 1/16th repeats)
    - Pitch/tempo bounce, tape flutter/vibrato, and reverse chord swell chops
    - French-touch syncopated chops & sidechain bounce
    """
    print('--> Building Banana Theme Remix (Spliced Bouncy Future-Funk / Lofi)...')
    stems = ['home', 'bio', 'cats', 'photos']
    raw_tracks = {}
    for s in stems:
        d, sr = sf.read(f'{BACKUP_DIR}/itswal_pink_{s}.mp3')
        raw_tracks[s] = d
        
    target_len = 8564480 # common duration for pink tracks
    for s in stems:
        if len(raw_tracks[s]) < target_len:
            pad = np.zeros((target_len - len(raw_tracks[s]), 2), dtype=np.float32)
            raw_tracks[s] = np.concatenate([raw_tracks[s], pad], axis=0)
        else:
            raw_tracks[s] = raw_tracks[s][:target_len]
            
    tempo_offset = 13232
    bar_count = (target_len - tempo_offset) // BAR # 100 bars
    
    # 1. Apply tape flutter, vibrato, and analog warmth
    fluttered = {}
    for s in stems:
        fluttered[s] = apply_tape_flutter_and_bounce(raw_tracks[s], flutter_depth_ms=1.3, flutter_rate_hz=4.6)
        
    # 2. Spliced Chops & Edits (IDENTICALLY to all 4 stems!)
    for b in range(bar_count):
        bar_start = tempo_offset + b * BAR
        bar_end = bar_start + BAR
        
        # Apply sidechain bounce to bars
        for s in stems:
            bar_slice = fluttered[s][bar_start:bar_end]
            fluttered[s][bar_start:bar_end] = apply_sidechain_bounce(bar_slice)
            
        # Pattern 1: Turnaround bar (every 2nd bar, b % 4 == 1):
        # 1/8th beat repeat on beat 3.5: repeat beat 3 (from 2*BEAT to 2.5*BEAT)
        if b % 4 == 1:
            src_start = bar_start + 2 * BEAT
            src_end = bar_start + 2 * BEAT + EIGHTH
            dst_start = bar_start + 2 * BEAT + EIGHTH
            dst_end = bar_start + 3 * BEAT
            
            for s in stems:
                rep_slice = smooth_edges(fluttered[s][src_start:src_end])
                fluttered[s][dst_start:dst_end] = rep_slice
                
            # Stutter edit on beat 4: 1/16th beat slice repeated 4x
            stut_src_start = bar_start + 3 * BEAT - SIXTEENTH
            stut_src_end = bar_start + 3 * BEAT
            stut_dst_start = bar_start + 3 * BEAT
            stut_dst_end = bar_start + 4 * BEAT
            for s in stems:
                s16 = smooth_edges(fluttered[s][stut_src_start:stut_src_end])
                s16_4x = np.tile(s16, (4, 1))
                # Rising volume ramp
                ramp = np.linspace(0.85, 1.25, len(s16_4x))[:, None]
                fluttered[s][stut_dst_start:stut_dst_end] = smooth_edges(s16_4x * ramp)
                
        # Pattern 2: Major Turnaround bar (every 4th bar, b % 4 == 3):
        # Reverse chord swell chop on Beat 4 leading into next downbeat!
        if b % 4 == 3:
            swell_start = bar_start + 3 * BEAT
            swell_end = bar_start + 4 * BEAT
            for s in stems:
                chord_slice = fluttered[s][swell_start:swell_end]
                rev_chord = np.flip(chord_slice, axis=0)
                # Exponential crescendo swell
                t_swell = np.linspace(0.1, 1.0, len(chord_slice)) ** 2
                fluttered[s][swell_start:swell_end] = smooth_edges(rev_chord * t_swell[:, None] * 1.3)
                
            # Pitch/tempo bounce on downbeat of next bar (b + 1)
            next_bar_start = bar_start + BAR
            if next_bar_start + BEAT < target_len:
                bounce_len = int(SR * 0.12) # 120ms pitch bounce
                for s in stems:
                    downbeat_slice = fluttered[s][next_bar_start : next_bar_start + bounce_len]
                    # Varispeed dip curve: momentary drop of 40 cents snapping back
                    t_b = np.linspace(0, 1, bounce_len)
                    curve = 1.0 - 0.25 * (1.0 - t_b) ** 2
                    fluttered[s][next_bar_start : next_bar_start + bounce_len] = downbeat_slice * curve[:, None]
                    
        # Pattern 3: Future-funk syncopated re-trigger on bar 3 (b % 4 == 2):
        # Re-trigger beat 1 chord stab on beat 2.5!
        if b % 4 == 2:
            stab_src_start = bar_start
            stab_src_end = bar_start + EIGHTH
            stab_dst_start = bar_start + BEAT + EIGHTH
            stab_dst_end = bar_start + 2 * BEAT
            for s in stems:
                stab = smooth_edges(fluttered[s][stab_src_start:stab_src_end])
                fluttered[s][stab_dst_start:stab_dst_end] = stab * 1.15

    # 3. Normalize & Export
    for s in stems:
        peak = np.max(np.abs(fluttered[s]))
        if peak > 0:
            fluttered[s] = fluttered[s] * (0.89 / peak)
            
        wav_path = f'{TEMP_DIR}/pink_{s}.wav'
        mp3_path = f'{OUTPUT_DIR}/itswal_pink_{s}.mp3'
        sf.write(wav_path, fluttered[s], SR)
        subprocess.run(['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-b:a', '320k', mp3_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f'   -> Rendered {mp3_path} ({len(fluttered[s])} samples)')


def remix_expressive_theme():
    """
    Expressive Theme (Default) -> Spliced Breakbeat / Glitch-Hop Chops
    - Spliced bar rearrangements (kick re-triggering, beat shuffling)
    - 1/16th beat rolls/stutters on turnaround bars
    - Reverse chops into downbeats
    - 16th-note rhythmic gating (trance-gate / glitch chop)
    """
    print('--> Building Expressive Theme Remix (Spliced Breakbeat / Glitch-Hop)...')
    stems = ['home', 'bio', 'cats', 'photos']
    raw_tracks = {}
    for s in stems:
        d, sr = sf.read(f'{BACKUP_DIR}/itswal_expressive_{s}.mp3')
        raw_tracks[s] = d
        
    target_len = 8348992 # common duration for expressive tracks (home/bio/cats)
    for s in stems:
        if len(raw_tracks[s]) < target_len:
            pad = np.zeros((target_len - len(raw_tracks[s]), 2), dtype=np.float32)
            raw_tracks[s] = np.concatenate([raw_tracks[s], pad], axis=0)
        else:
            raw_tracks[s] = raw_tracks[s][:target_len]
            
    tempo_offset = 12306
    bar_count = (target_len - tempo_offset) // BAR # 98 bars
    
    # 1. Prepare Rhythmic Gate Envelope
    # 16-step rhythmic pattern: [1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0]
    gate_pat = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0], dtype=float)
    gate_env = np.repeat(gate_pat, SIXTEENTH)
    w = int(SR * 0.002) # 2ms Hann smoothing
    gate_smooth = np.convolve(gate_env, np.hanning(w)/np.sum(np.hanning(w)), mode='same')
    gate_smooth = gate_smooth[:BAR, None]
    
    processed = {s: raw_tracks[s].copy() for s in stems}
    
    # 2. Spliced Breakbeat / Glitch-Hop Chops (IDENTICALLY to all 4 stems!)
    for b in range(bar_count):
        bar_start = tempo_offset + b * BAR
        bar_end = bar_start + BAR
        
        # Sub-pattern 1 (b % 4 == 1): Spliced Bar Rearrangement
        # Breakbeat kick-retrigger: Rearrange beats [1, 2, 1, 4]
        if b % 4 == 1:
            for s in stems:
                b1 = smooth_edges(processed[s][bar_start : bar_start + BEAT])
                b2 = smooth_edges(processed[s][bar_start + BEAT : bar_start + 2 * BEAT])
                b4 = smooth_edges(processed[s][bar_start + 3 * BEAT : bar_start + 4 * BEAT])
                # Assemble: Beat 1, Beat 2, Beat 1 (chopped kick retrigger), Beat 4
                rearranged_bar = np.concatenate([b1, b2, b1, b4], axis=0)
                processed[s][bar_start:bar_end] = rearranged_bar
                
        # Sub-pattern 2 (b % 4 == 2): Rhythmic Gating Bar + Reverse Chop on Beat 4
        if b % 4 == 2:
            for s in stems:
                # Apply 16th-note glitch-hop trance-gate
                gated_bar = processed[s][bar_start:bar_end] * (0.12 + 0.88 * gate_smooth)
                
                # Reverse chop on Beat 4 (leading into next downbeat)
                beat4_slice = gated_bar[3 * BEAT : 4 * BEAT]
                rev_beat4 = np.flip(beat4_slice, axis=0)
                t_rev = np.linspace(0.15, 1.0, len(beat4_slice)) ** 2
                gated_bar[3 * BEAT : 4 * BEAT] = smooth_edges(rev_beat4 * t_rev[:, None] * 1.4)
                
                processed[s][bar_start:bar_end] = gated_bar
                
        # Sub-pattern 3 (b % 4 == 3): Glitch-Hop Turnaround Breakdown & 1/16th Beat Rolls
        if b % 4 == 3:
            for s in stems:
                # Spliced shuffle: Beat 1, Beat 3 (jump cut), Beat 2
                b1 = smooth_edges(processed[s][bar_start : bar_start + BEAT])
                b2 = smooth_edges(processed[s][bar_start + BEAT : bar_start + 2 * BEAT])
                b3 = smooth_edges(processed[s][bar_start + 2 * BEAT : bar_start + 3 * BEAT])
                
                # 1/16th roll on Beat 4: 4 repeats of the 16th slice from beat 3.75
                s16_slice = smooth_edges(processed[s][bar_start + 3 * BEAT - SIXTEENTH : bar_start + 3 * BEAT])
                s16_roll = np.tile(s16_slice, (4, 1))
                ramp = np.linspace(0.8, 1.35, len(s16_roll))[:, None]
                roll_beat4 = smooth_edges(s16_roll * ramp)
                
                # Assemble turnaround bar: [Beat 1, Beat 3, Beat 2, 1/16th Roll Beat 4]
                turnaround_bar = np.concatenate([b1, b3, b2, roll_beat4], axis=0)
                processed[s][bar_start:bar_end] = turnaround_bar

    # 3. Add Breakbeat / Glitch-Hop Punch & Warmth
    for s in stems:
        # Glitch-hop drive / saturation
        sat = np.tanh(1.2 * processed[s])
        mix = 0.85 * sat + 0.15 * processed[s]
        
        # Peak normalization to -1.0 dBFS (0.89)
        peak = np.max(np.abs(mix))
        if peak > 0:
            mix = mix * (0.89 / peak)
            
        wav_path = f'{TEMP_DIR}/expressive_{s}.wav'
        mp3_path = f'{OUTPUT_DIR}/itswal_expressive_{s}.mp3'
        sf.write(wav_path, mix, SR)
        subprocess.run(['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-b:a', '320k', mp3_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f'   -> Rendered {mp3_path} ({len(mix)} samples)')


def main():
    print('====================================================================')
    print('ITSWAL JUKEBOX MUSICAL REMIX PIPELINE')
    print('====================================================================')
    remix_space_theme()
    remix_pink_theme()
    remix_expressive_theme()
    print('\nAll 12 tracks successfully remixed and exported!')


if __name__ == '__main__':
    main()
