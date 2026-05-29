import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "coqui_tts", "checkpoint_1260000-inference.pth")
CONFIG_PATH = os.path.join(BASE_DIR, "coqui_tts", "config.json")
SPEAKERS_PATH = os.path.join(BASE_DIR, "coqui_tts", "speakers.pth")
TEMP_DIR = os.path.join(BASE_DIR, "..", "temp")
DEFAULT_SPEAKER = "wibowo"

# Karakter yang didukung vocab model
VOCAB = set("abdefhijklmnoprstuwxzŋɔəɛɡɪɲʃʊʒʔˈ ")

try:
    from g2p_id import G2P
    g2p = G2P()
    G2P_AVAILABLE = True
    print("[TTS] G2P loaded")
except Exception as e:
    G2P_AVAILABLE = False
    print(f"[TTS] G2P tidak tersedia: {e}")

WORD_REPLACEMENTS = {
    r'\bflight\b': 'penerbangan',
    r'\bschedule\b': 'jadwal',
    r'\btransport\b': 'transportasi',
    r'\bbook\b': 'pesan',
    r'\bcheck\b': 'cek',
    r'\bsimple\b': 'sederhana',
    r'\binclude\b': 'termasuk',
    r'\bbudget\b': 'anggaran',
    r'\btomorrow\b': 'besok',
    r'\bnext week\b': 'minggu depan',
    r'\btravel\b': 'perjalanan',
    r'\bticket\b': 'tiket',
    r'\bairport\b': 'bandara',
    r'\bpackage\b': 'paket',
    r'\bonline\b': 'daring',
    r'\bsure\b': 'tentu',
    r'\bokay\b': 'baik',
    r'\binfo\b': 'informasi',
    r'\bana\b': 'saya',
    r'\bakhi\b': 'saudaraku',
}

def normalize_to_indonesian(text: str) -> str:
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def fix_missing_chars(text: str) -> str:
    """Ganti karakter yang tidak ada di vocab."""
    # Latin 'g' → IPA 'ɡ'
    text = text.replace('g', 'ɡ')
    # Hapus karakter yang masih tidak ada di vocab
    result = ''.join(c for c in text if c in VOCAB or c in '.,!?;:-')
    return result

def text_to_phoneme(text: str) -> str:
    if G2P_AVAILABLE:
        try:
            phonemes = g2p(text)
            print(f"[TTS] G2P output: {phonemes}")
            return phonemes
        except Exception as e:
            print(f"[TTS] G2P error: {e}")
    return text

def clean_text_for_tts(text: str) -> str:
    text = re.sub(r'[*#_`]', '', text)
    text = normalize_to_indonesian(text)
    text = re.sub(r'[\u0600-\u06FF]', '', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Memperpanjang limit dari 200 ke 1000 agar kalimat dari LLM tidak terpotong
    if len(text) > 1000:
        text = text[:1000].rsplit(' ', 1)[0] + "."
    return text

def synthesize_speech(text: str, output_path: str = None) -> str:
    if output_path is None:
        os.makedirs(TEMP_DIR, exist_ok=True)
        output_path = os.path.join(TEMP_DIR, "output.wav")

    print(f"[TTS] Input: {text}")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Step 1: normalisasi
    cleaned = clean_text_for_tts(text)
    print(f"[TTS] Cleaned: {cleaned}")

    # Step 2: G2P → fonem IPA
    phoneme = text_to_phoneme(cleaned)

    # Step 3: fix karakter missing (g → ɡ)
    phoneme_fixed = fix_missing_chars(phoneme)
    print(f"[TTS] Phoneme fixed: {phoneme_fixed}")

    if not phoneme_fixed or len(phoneme_fixed.strip()) < 3:
        phoneme_fixed = "baik saja mənərti"

    cmd = [
        "tts",
        "--model_path", MODEL_PATH,
        "--config_path", CONFIG_PATH,
        "--speakers_file_path", SPEAKERS_PATH,
        "--speaker_idx", DEFAULT_SPEAKER,
        "--text", phoneme_fixed,
        "--out_path", output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[TTS] Error: {result.stderr[-300:]}")
        fallback_cmd = cmd[:-2] + ["--text", "baik saja mənərti", "--out_path", output_path]
        result2 = subprocess.run(fallback_cmd, capture_output=True, text=True)
        if result2.returncode != 0:
            raise RuntimeError(f"TTS gagal: {result.stderr[-200:]}")

    print(f"[TTS] Saved: {output_path}")
    return output_path