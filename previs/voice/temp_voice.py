"""Temp voice (仮の声) for timing: synthesize every line (English, Piper TTS) and measure its length. 10/19 台詞は英語音声に。
The real voices (ElevenLabs) replace these later; re-run this + shot_length.py with the real files' lengths.
usage: python3 voice/temp_voice.py      (pip install piper-tts; python3 -m piper.download_voices en_GB-alan-medium en_US-ryan-medium en_US-lessac-medium into PIPER_DIR)
writes voice/lines.json (text, English subtitle, speaker, measured seconds) and out/voice/<id>.wav / .mp3
"""
import json, os, subprocess, numpy as np, pyopenjtalk, wave
H = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(H); OUT = os.path.join(P, "out", "voice"); os.makedirs(OUT, exist_ok=True)
SPEED = 1.0                                     # OpenJTalk の標準。間を含めて 4.8〜6.3 モーラ/秒＝聞き取りやすい話速の帯（320〜360 モーラ/分）に入る
PITCH = {"Vance": -3, "Sho": 0, "Chief": 2}     # 声の区別だけ（半音）
LINES = [  # id, cut, speaker, 日本語（元の台本・意味の確認用）, 英語（話す台詞＝字幕）
    ("C02",  "C02",  "Vance", "本部。ダブルオーセブン。囲まれた。あと3発。", "HQ. Double-O-Seven. Surrounded. Three rounds left."),
    ("C03a", "C03",  "Chief", "ダブルオーセブンから。上の道。あれを使いなさい。", "Double-O-Seven. The upper road. Use the car."),
    ("C03b", "C03",  "Sho",   "上。", "Up there."),
    ("C03c", "C03",  "Sho",   "了解。", "On it."),
    ("C07",  "C07",  "Sho",   "お迎えに上がりました。", "Your ride, sir."),
    ("C10",  "C10",  "Sho",   "掴まっててくださいね。", "Hold on tight."),
    ("C13b", "C13b", "Vance", "しつこいな。", "Persistent."),
    ("C14a", "C14",  "Vance", "橋がないが。", "...The bridge is out."),
    ("C14b", "C14",  "Sho",   "ええ。", "Yes."),
    ("C18a", "C18",  "Vance", "私のには、射出座席がついていた。", "Mine had an ejector seat."),
    ("C18b", "C18",  "Sho",   "これは、車ごと飛びますよ。", "This one ejects the whole car."),
]
res = {}
from piper import PiperVoice, SynthesisConfig
VDIR = os.environ.get("PIPER_DIR", "/tmp/claude-0/-home-claude/0ef688ce-adfa-58a3-b26b-48034528405c/scratchpad/piper")
VOICES = {"Vance": "en_GB-alan-medium", "Sho": "en_US-ryan-medium", "Chief": "en_US-lessac-medium"}   # 10/19 本人「音声は英語で構わない」
PACE = {"Vance": 1.0, "Sho": 1.35, "Chief": 1.1}   # length_scale：落ち着いた話し方（約 150 語/分）に揃える。ryan はそのままだと 250 語/分と速い
_v = {}
for lid, cut, spk, ja, en in LINES:
    if spk not in _v: _v[spk] = PiperVoice.load(os.path.join(VDIR, VOICES[spk] + ".onnx"))
    v = _v[spk]; chunks = list(v.synthesize(en, syn_config=SynthesisConfig(length_scale=PACE[spk]))); sr = chunks[0].sample_rate
    x = np.concatenate([c.audio_float_array for c in chunks]) * 32767; a = np.abs(x); idx = np.where(a > a.max() * 0.03)[0]
    x = x[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.05 * sr)]
    wav = os.path.join(OUT, f"{lid}.wav")
    with wave.open(wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.clip(x, -32767, 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ac", "1", "-b:a", "48k", os.path.join(OUT, f"{lid}.mp3")], check=True)
    dur = round(len(x) / sr, 2); words = len(en.replace("...", "").split())
    res[lid] = {"cut": cut, "speaker": spk, "ja": ja, "en": en, "dur": dur, "words": words, "cps_en": round(len(en) / max(dur, 0.83), 1)}
    print(f"{lid:5} {spk:6} {dur:4.2f}s {words:2d} words {words/dur*60:4.0f} wpm  {res[lid]['cps_en']} cps  {en}")
json.dump({"engine": "Piper (en_GB-alan / en_US-ryan / en_US-lessac medium)", "lang": "en", "lines": res}, open(os.path.join(H, "lines.json"), "w"), ensure_ascii=False, indent=1)
