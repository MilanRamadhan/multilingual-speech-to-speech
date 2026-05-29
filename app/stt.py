import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WHISPER_CLI = os.path.join(
    BASE_DIR, "..", "models", "whisper.cpp",
    "build", "bin", "Release", "whisper-cli.exe"
)

WHISPER_MODEL = os.path.join(
    BASE_DIR, "..", "models", "whisper.cpp",
    "models", "ggml-large-v3-turbo.bin" 
)

def transcribe_speech_to_text(audio_path: str) -> str:
    print(f"[STT] Transcribing: {audio_path}")

    if not os.path.exists(WHISPER_CLI):
        raise FileNotFoundError(f"whisper-cli.exe tidak ditemukan: {WHISPER_CLI}")
    if not os.path.exists(WHISPER_MODEL):
        raise FileNotFoundError(f"Model tidak ditemukan: {WHISPER_MODEL}")

    prompt_text = "Ya akhi, uridu book flight ila Jeddah al-usbu' al-qadim. Hal bisa bantu ajida afdhal schedule wa rihlatan mubashirah? transport, online."

    result = subprocess.run(
        [WHISPER_CLI, "-m", WHISPER_MODEL, "-f", audio_path,
         "-l", "auto", "--prompt", prompt_text, "--output-txt"],
        capture_output=True, text=True
    )

    # Whisper menyimpan output ke file .txt di samping audio
    txt_path = audio_path + ".txt"
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            transcript = f.read().strip()
        os.remove(txt_path)
        print(f"[STT] Hasil: {transcript}")
        return transcript

    # Fallback dari stdout
    transcript = result.stdout.strip()
    print(f"[STT] Hasil (stdout): {transcript}")

    words = transcript.split()
    if len(words) > 5:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:  # lebih dari 70% kata sama = kemungkinan noise
            return "[Audio tidak jelas, silakan rekam ulang]"
        
    return transcript