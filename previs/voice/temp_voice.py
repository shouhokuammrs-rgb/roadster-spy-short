"""Temp voice (仮の声) for timing: synthesize every line with OpenJTalk and measure its length.
The real voices (ElevenLabs) replace these later; re-run this + shot_length.py with the real files' lengths.
usage: python3 voice/temp_voice.py      (pip install pyopenjtalk; first run downloads the dictionary)
writes voice/lines.json (text, English subtitle, speaker, measured seconds) and out/voice/<id>.wav / .mp3
"""
import json, os, subprocess, numpy as np, pyopenjtalk, wave
H = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(H); OUT = os.path.join(P, "out", "voice"); os.makedirs(OUT, exist_ok=True)
SPEED = 1.0                                     # OpenJTalk の標準。間を含めて 4.8〜6.3 モーラ/秒＝聞き取りやすい話速の帯（320〜360 モーラ/分）に入る
PITCH = {"Vance": -3, "Sho": 0, "Chief": 2}     # 声の区別だけ（半音）
LINES = [  # id, cut, speaker, 日本語, 英語字幕（下書き）
    ("C02",  "C02",  "Vance", "本部。ナイン。囲まれた。あと3発。", "HQ. Nine. Surrounded. Three rounds left."),
    ("C03a", "C03",  "Chief", "ナインから。上の道。あれを使いなさい。", "From Nine. The upper road. Use it."),
    ("C03b", "C03",  "Sho",   "上。", "Up."),
    ("C03c", "C03",  "Sho",   "了解。", "Copy."),
    ("C07",  "C07",  "Sho",   "お迎えに上がりました。", "Your ride is here."),
    ("C10",  "C10",  "Sho",   "掴まっててくださいね。", "Hold on tight."),
    ("C13b", "C13b", "Vance", "しつこいな。", "Persistent."),
    ("C14a", "C14",  "Vance", "橋がないが。", "...No bridge."),
    ("C14b", "C14",  "Sho",   "ええ。", "Yes."),
    ("C18a", "C18",  "Vance", "私のには、射出座席がついていた。", "Mine had an ejector seat."),
    ("C18b", "C18",  "Sho",   "これは、車ごと飛びますよ。", "This one flies, car and all."),
]
res = {}
for lid, cut, spk, ja, en in LINES:
    x, sr = pyopenjtalk.tts(ja, speed=SPEED, half_tone=PITCH[spk]); a = np.abs(x); idx = np.where(a > a.max() * 0.03)[0]
    x = x[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.05 * sr)]          # 前後の無音を落とす
    wav = os.path.join(OUT, f"{lid}.wav")
    with wave.open(wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.clip(x, -32767, 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ac", "1", "-b:a", "48k", os.path.join(OUT, f"{lid}.mp3")], check=True)
    mora = len([p for p in pyopenjtalk.g2p(ja, kana=True) if p not in "、。ャュョァィゥェォ"])
    dur = round(len(x) / sr, 2)
    res[lid] = {"cut": cut, "speaker": spk, "ja": ja, "en": en, "dur": dur, "mora": mora, "cps_en": round(len(en) / max(dur, 0.83), 1)}
    print(f"{lid:5} {spk:6} {dur:4.2f}s {mora:2d} mora {mora/dur:4.1f}/s  EN {res[lid]['cps_en']} cps  {ja}")
json.dump({"engine": f"OpenJTalk speed {SPEED}", "lines": res}, open(os.path.join(H, "lines.json"), "w"), ensure_ascii=False, indent=1)
