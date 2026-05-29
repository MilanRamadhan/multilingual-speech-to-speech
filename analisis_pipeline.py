import os, time, jiwer
from app.stt import transcribe_speech_to_text

AUDIO_DIR = "data/corpus/audio/"
results = []

for fname in os.listdir(AUDIO_DIR):
    if fname.endswith(".wav"):
        start = time.time()
        transcript = transcribe_speech_to_text(os.path.join(AUDIO_DIR, fname))
        latency = time.time() - start
        results.append({"file": fname, "transcript": transcript, "latency": latency})
        print(f"[{fname}] → {transcript} ({latency:.2f}s)")

# Simpan log
import json
with open("log/pipeline_results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)