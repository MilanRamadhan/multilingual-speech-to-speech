import os
import re
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """Kamu adalah asisten percakapan yang memahami input code-switching (Indonesia, Inggris, Arab).

LANGSUNG berikan jawaban substansial dalam Bahasa Indonesia MURNI yang natural. Jangan gunakan bahasa Inggris/Arab dalam merespons.
Dilarang keras memakai markdown formatting (seperti *, **, #, atau bullet point). Gunakan teks paragraf biasa.
Jawaban harus langsung ke intinya (maksimal 3 kalimat pendek) dan JANGAN menulis ulang, mengonfirmasi, atau menyebutkan bahwa kamu sedang mengikuti aturan/checklist. Fokus saja pada jawaban.

Contoh:
Input: "Can you help aku arrange transport dari Jeddah ke Madinah tomorrow?"
Output: "Tentu bisa, saya bantu carikan transportasi dari Jeddah ke Madinah untuk besok."

Input: "Aku mau book flight ke Jeddah minggu depan"
Output: "Baik, saya bantu carikan penerbangan ke Jeddah untuk minggu depan."
"""

MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    # gemini-2.0-flash-lite dihapus — daily quota habis
]

# Kata kunci yang menandakan model bocor meta/thinking
META_KEYWORDS = [
    'markdown', 'sentence', 'checklist', 'code-switching',
    'very natural', 'pure natural', 'indonesian?', 'yes ("',
    'no (', '**final', 'final answer', 'sentences check',
    'output:', 'input:', '(sentence', 'rule', 'constraint'
]


def _clean_response(text: str) -> str:
    """
    Buang baris yang mengandung meta-instruksi/thinking Gemini.
    Ambil maksimal 3 kalimat pertama yang bersih.
    """
    lines = text.split('\n')
    clean_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        # Buang baris yang mengandung meta keyword
        if any(k in low for k in META_KEYWORDS):
            continue
        # Buang baris yang dimulai dengan numbering/bullet sisa
        if re.match(r'^[\d]+\.\s', stripped) or stripped.startswith('*'):
            continue
        clean_lines.append(stripped)

    if not clean_lines:
        return ""

    # Gabung dan ambil max 3 kalimat
    full_text = ' '.join(clean_lines)
    # Split by sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    result = ' '.join(sentences[:3]).strip()
    return result


def generate_response(text: str) -> str:
    print(f"[LLM] Input: {text}")

    last_error = None

    for model in MODELS_TO_TRY:
        try:
            print(f"[LLM] Mencoba model: {model}")
            response = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=200,
                    temperature=0.4
                ),
                contents=text
            )

            raw = response.text.strip()
            result = _clean_response(raw)

            if not result:
                print(f"[LLM] {model} response kosong setelah cleaning, raw: {raw[:100]}")
                last_error = "Response kosong setelah cleaning"
                continue

            print(f"[LLM] Berhasil dengan {model}: {result}")
            return result

        except Exception as e:
            err = str(e)
            last_error = err

            if "429" in err:
                # Coba baca retryDelay dari error message
                delay_match = re.search(r'retryDelay.*?(\d+)s', err)
                wait = int(delay_match.group(1)) + 2 if delay_match else 15

                # Kalau daily quota habis (limit: 0), skip model ini selamanya
                if 'limit: 0' in err:
                    print(f"[LLM] {model} daily quota habis, skip permanen.")
                    continue

                print(f"[LLM] {model} rate limit — tunggu {wait} detik...")
                time.sleep(wait)
                continue
            elif "quota" in err.lower():
                print(f"[LLM] {model} quota habis, coba model berikutnya...")
                time.sleep(5)
                continue
            else:
                print(f"[LLM] {model} error: {e}")
                continue

    raise RuntimeError(f"Semua model gagal. Error terakhir: {last_error}")