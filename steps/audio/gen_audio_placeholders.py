
import numpy as np
import os
from scipy.io import wavfile

def generate_tone(filename, freq=440, duration=5.0):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate a simple sine wave with fade in/out
    note = np.sin(freq * t * 2 * np.pi)
    
    # Apply envelope to avoid clicking
    envelope = np.ones_like(note)
    fade_len = int(sample_rate * 0.1)
    envelope[:fade_len] = np.linspace(0, 1, fade_len)
    envelope[-fade_len:] = np.linspace(1, 0, fade_len)
    
    audio = note * envelope
    
    # Normalize to 16-bit range
    audio = (audio * 32767).astype(np.int16)
    
    # Ensure dir exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Save as WAV (MoviePy accepts WAV for AudioFileClip usually, or we can try to save as mp3 if pydub is here, but WAV is safer for raw writing)
    # The config expects .mp3, but MoviePy might handle .wav renamed or we just save as .wav and users replace.
    # Actually, let's verify if config enforces extension.
    # Config has keys like "guqin.mp3".
    # I will save as .mp3 if possible, but pure python write to mp3 is hard without lame.
    # I'll save as .wav and rename to .mp3? No, that might confuse decoders.
    # I'll save as .wav and update config to use .wav placeholders? 
    # Or just save as .wav and tell user to replace.
    # MoviePy uses ffmpeg, so it might handle wav content in mp3 extension? Usually yes.
    # Let's try saving as wav but named mp3. FFMPEG is robust.
    
    wavfile.write(filename, sample_rate, audio)
    print(f"Generated {filename}")

base_dir = "auto_maker/assets/music"
files = {
    "guqin.mp3": 196.0,   # G3
    "epic.mp3": 110.0,    # A2
    "lullaby.mp3": 261.6, # C4
    "playful.mp3": 392.0, # G4
    "action.mp3": 146.8,  # D3
    "storybook.mp3": 293.7, # D4
    "meditation.mp3": 174.6 # F3 (Calm)
}

for name, freq in files.items():
    generate_tone(os.path.join(base_dir, name), freq)
