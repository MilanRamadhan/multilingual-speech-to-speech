import os, time
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
    "gemini-3.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

def generate_response(text: str) -> str:
    print(f"[LLM] Input: {text}")

    for model in MODELS_TO_TRY:
        try:
            print(f"[LLM] Mencoba model: {model}")
            response = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=800, 
                    temperature=1.0
                ),
                contents=text
            )
            result = response.text.strip()
            print(f"[LLM] Berhasil dengan {model}: {result}")
            return result

        except Exception as e:
            err = str(e)
            if "429" in err:
                print(f"[LLM] {model} quota habis, coba model berikutnya...")
                time.sleep(2)
                continue
            else:
                print(f"[LLM] {model} error: {e}")
                continue

    raise RuntimeError("Semua model gagal. Cek quota API key kamu.")