"""
analisis_pipeline.py
====================
Script analisis pipeline end-to-end untuk korpus speech code-switching.
Memproses sample audio dari data/corpus/audio/A dan data/corpus/audio/B,
menjalankan STT → LLM → TTS, lalu menghitung WER, CER, dan latency.

Cara menjalankan:
    python analisis_pipeline.py              # proses 30 file (default)
    python analisis_pipeline.py --all        # proses semua file
    python analisis_pipeline.py --limit 50   # proses 50 file

Output:
    - logs/pipeline_results.json   : hasil lengkap per file
    - logs/pipeline_summary.txt    : ringkasan evaluasi
    - temp/responses/              : file audio TTS per percakapan
"""

import os, sys, json, time, subprocess, re, unicodedata, argparse, hashlib
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from dotenv import load_dotenv

# Load .env untuk API key
load_dotenv()

BASE_DIR  = Path(__file__).parent
APP_DIR   = BASE_DIR / "app"

# ─── GROUND TRUTH ────────────────────────────────────────────────────────────
GROUND_TRUTH = {
    "audio01":  "Aku mau book flight ke Jeddah minggu depan bisa bantu schedule",
    "audio1":   "Aku mau book flight ke Jeddah minggu depan bisa bantu schedule",
    "audio02":  "Aku butuh travel umrah simple tapi include Madinah visit",
    "audio2":   "Aku butuh travel umrah simple tapi include Madinah visit",
    "audio03":  "Can you help aku arrange transport dari Jeddah ke Madinah tomorrow",
    "audio3":   "Can you help aku arrange transport dari Jeddah ke Madinah tomorrow",
    "audio04":  "Explain step by step cara apply visa Saudi dengan benar",
    "audio4":   "Explain step by step cara apply visa Saudi dengan benar",
    "audio05":  "Ya akhi uridu book flight ila Jeddah al usbu al qadim hal bisa bantu ajida afdal schedule wa rihlatan mubashirah",
    "audio5":   "Ya akhi uridu book flight ila Jeddah al usbu al qadim hal bisa bantu ajida afdal schedule wa rihlatan mubashirah",
    "audio06":  "Uridu arrange transport min Jeddah ila Madinah ghadan",
    "audio6":   "Uridu arrange transport min Jeddah ila Madinah ghadan",
    "audio07":  "Book flight ke Jeddah lalu lanjut ke Madinah schedule terbaik kapan",
    "audio7":   "Book flight ke Jeddah lalu lanjut ke Madinah schedule terbaik kapan",
    "audio08":  "Uridu schedule trip min Jeddah ila Makkah bukra sabah",
    "audio8":   "Uridu schedule trip min Jeddah ila Makkah bukra sabah",
    "audio09":  "Mumkin book transport min Makkah ila Madinah untuk besok",
    "audio9":   "Mumkin book transport min Makkah ila Madinah untuk besok",
    "audio10":  "Apa perbedaan umrah dan hajj secara detail dalam Islam",
    "audio11":  "Kenapa fasting di ramadan itu wajib bagi muslim",
    "audio12":  "Bagaimana proses visa Saudi untuk umrah dari Indonesia sekarang",
    "audio13":  "Jelaskan step by step cara booking flight ke Jeddah secara online",
    "audio14":  "How to prepare dokumen umrah dari Indonesia dengan benar",
    "audio15":  "Tolong buat checklist persiapan umrah termasuk barang wajib dibawa",
    "audio16":  "Guide aku cara pilih hotel di Makkah dekat Haram dengan budget terbatas",
    "audio17":  "Menurut kamu belajar bahasa Arab itu susah gak untuk pemula",
    "audio18":  "I feel overwhelmed dengan persiapan umrah ada tips sederhana",
    "audio19":  "Ahyanan saya bingung mulai dari mana untuk umrah",
    "audio20":  "Translate ke English aku mau pergi ke Makkah minggu depan",
    "Audio01":  "Aku mau book flight ke Jeddah minggu depan bisa bantu schedule",
    "Audio02":  "Aku butuh travel umrah simple tapi include Madinah visit",
    "Audio03":  "Can you help aku arrange transport dari Jeddah ke Madinah tomorrow",
    "Audio04":  "Explain step by step cara apply visa Saudi dengan benar",
    "Audio05":  "Ya akhi uridu book flight ila Jeddah al usbu al qadim hal bisa bantu ajida afdal schedule wa rihlatan mubashirah",
    "Audio06":  "Uridu arrange transport min Jeddah ila Madinah ghadan",
}

# ─── KONFIGURASI ─────────────────────────────────────────────────────────────
WHISPER_CLI   = BASE_DIR / "models" / "whisper.cpp" / "build" / "bin" / "Release" / "whisper-cli.exe"
WHISPER_MODEL = BASE_DIR / "models" / "whisper.cpp" / "models" / "ggml-large-v3-turbo.bin"

# ─── WER & CER ───────────────────────────────────────────────────────────────
def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def edit_distance(a, b):
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            dp[j] = prev[j-1] if a[i-1] == b[j-1] else 1 + min(prev[j], dp[j-1], prev[j-1])
    return dp[n]

def compute_wer(ref, hyp):
    r = normalize_text(ref).split()
    h = normalize_text(hyp).split()
    if not r: return 0.0
    return round(edit_distance(r, h) / len(r), 4)

def compute_cer(ref, hyp):
    r = list(normalize_text(ref).replace(" ", ""))
    h = list(normalize_text(hyp).replace(" ", ""))
    if not r: return 0.0
    return round(edit_distance(r, h) / len(r), 4)

# ─── DETEKSI BAHASA ───────────────────────────────────────────────────────────
ARABIC_RE  = re.compile(r'[\u0600-\u06FF]')
EN_WORDS   = {"flight","book","schedule","transport","help","arrange","explain",
              "step","apply","prepare","guide","include","visit","simple","how",
              "translate","feel","overwhelmed","tips","fasting","check","can","you"}
ID_WORDS   = {"aku","mau","ke","bisa","bantu","saya","untuk","dari","yang","ini",
              "dengan","dan","atau","tapi","juga","cara","proses","tolong","kenapa",
              "bagaimana","jelaskan","menurut","apa","perbedaan","butuh"}

def detect_lang(text):
    words = set(text.lower().split())
    has_ar = bool(ARABIC_RE.search(text))
    has_en = bool(words & EN_WORDS)
    has_id = bool(words & ID_WORDS)
    langs = []
    if has_id: langs.append("ID")
    if has_en: langs.append("EN")
    if has_ar: langs.append("AR")
    return "+".join(langs) if langs else "ID"

# ─── STT ─────────────────────────────────────────────────────────────────────
def run_stt(audio_path):
    t0 = time.time()
    result = subprocess.run(
        [str(WHISPER_CLI), "-m", str(WHISPER_MODEL), "-f", str(audio_path),
         "-l", "auto", "--output-txt"],
        capture_output=True, text=True
    )
    latency = round(time.time() - t0, 2)
    txt_path = str(audio_path) + ".txt"
    if Path(txt_path).exists():
        transcript = Path(txt_path).read_text(encoding="utf-8").strip()
        os.remove(txt_path)
        return transcript, latency
    return result.stdout.strip(), latency

# ─── LLM CACHE ───────────────────────────────────────────────────────────────
# Cache menyimpan {transcript_normalized: response}
# Sehingga transcript yang sama/mirip tidak perlu panggil API lagi
_llm_cache = {}   # key: normalized transcript → value: response string

def _normalize_for_cache(text: str) -> str:
    """Normalisasi transcript untuk key cache: lowercase, strip, hapus tanda baca."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def _find_in_cache(transcript: str, threshold: float = 0.82) -> str | None:
    """
    Cari response di cache berdasarkan similarity.
    Kalau ada transcript yang mirip >= threshold, pakai responsenya.
    Exact match dicek duluan (lebih cepat).
    """
    key = _normalize_for_cache(transcript)

    # 1. Exact match
    if key in _llm_cache:
        return _llm_cache[key]

    # 2. Fuzzy match
    for cached_key, cached_resp in _llm_cache.items():
        ratio = SequenceMatcher(None, key, cached_key).ratio()
        if ratio >= threshold:
            return cached_resp

    return None

def _store_in_cache(transcript: str, response: str):
    key = _normalize_for_cache(transcript)
    _llm_cache[key] = response

def _clean_llm_output(raw: str) -> str:
    """
    Bersihkan output Gemini dari:
    - Baris meta/thinking (markdown, drafting, concept, dll)
    - Bullet/numbering
    - Baris kosong
    Lalu ambil maksimal 3 kalimat pertama yang lengkap.
    """
    META_KW = [
        'markdown', 'drafting', 'concept:', 'sentences check',
        'or other markups', 'pure natural', 'final answer',
        'note:', 'remember:', 'important:', 'disclaimer:',
        'thinking:', '**output', '**response', 'here is',
        'here\'s', 'as an ai', 'i cannot', 'i am unable'
    ]

    clean_lines = []
    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        # Buang baris meta/thinking
        if any(k in low for k in META_KW):
            continue
        # Buang bullet/numbering sisa
        if re.match(r'^[\d]+[.)]\s|^\*{1,2}[^*]|^-\s', s):
            continue
        # Buang baris yang seluruhnya huruf besar (kemungkinan header)
        if s.isupper() and len(s) > 3:
            continue
        clean_lines.append(s)

    if not clean_lines:
        return ""

    # Gabung semua baris bersih jadi satu paragraf
    full_text = ' '.join(clean_lines)

    # Ambil maksimal 3 kalimat yang selesai (diakhiri . ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    # Filter kalimat yang terlalu pendek (< 5 kata) — kemungkinan terpotong
    good = [s for s in sentences if len(s.split()) >= 4]

    if not good:
        # Kalau tidak ada kalimat lengkap, ambil semua saja
        return full_text[:300].strip()

    result = ' '.join(good[:3]).strip()
    return result

# ─── LLM ─────────────────────────────────────────────────────────────────────
def run_llm(transcript: str):
    # ── CEK CACHE DULU — hemat quota API ──
    cached = _find_in_cache(transcript)
    if cached:
        print(f"  [LLM] Cache hit ✓ — tidak panggil API")
        return cached, 0.0

    try:
        from google import genai
        from google.genai import types
        import os as _os

        api_key = _os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "[LLM ERROR: GEMINI_API_KEY tidak ditemukan di .env]", 0.0

        client = genai.Client(api_key=api_key)

        SYSTEM_PROMPT = (
            "Kamu adalah asisten customer service umrah yang ramah dan informatif. "
            "Kamu memahami pertanyaan dalam Bahasa Indonesia, Inggris, Arab, "
            "maupun campuran ketiganya (code-switching). "
            "Berikan jawaban LANGSUNG dalam Bahasa Indonesia yang natural dan lengkap. "
            "Maksimal 2-3 kalimat yang selesai sempurna. "
            "Jangan gunakan simbol markdown (*, **, #, bullet, nomor). "
            "Jangan tulis ulang pertanyaan atau jelaskan bahwa kamu AI."
        )

        # Model list — hanya yang masih punya quota
        # gemini-2.5-flash: 500 RPD free tier, 10 RPM
        # gemini-2.0-flash: skip jika sudah habis quota
        MODELS = ["gemini-2.5-flash"]

        t0 = time.time()

        for model in MODELS:
            try:
                print(f"  [LLM] Memanggil {model}...")
                response = client.models.generate_content(
                    model=model,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=800,
                        temperature=0.3,
                    ),
                    contents=transcript
                )

                raw = response.text.strip() if response.text else ""
                if not raw:
                    print(f"  [LLM] {model} response kosong, skip.")
                    continue

                result = _clean_llm_output(raw)
                if not result:
                    print(f"  [LLM] {model} output kosong setelah cleaning.")
                    print(f"  [LLM] Raw: {raw[:100]}")
                    continue

                # Simpan ke cache
                _store_in_cache(transcript, result)
                return result, round(time.time() - t0, 2)

            except Exception as e:
                err = str(e)

                if "429" in err:
                    # Baca retry delay dari response Gemini
                    delay_match = re.search(r'retryDelay["\s:]+(\d+)s', err)
                    wait = int(delay_match.group(1)) + 3 if delay_match else 20

                    # Kalau daily quota habis (limit: 0), skip model ini
                    if 'limit: 0' in err:
                        print(f"  [LLM] {model} daily quota habis — skip.")
                        continue

                    print(f"  [LLM] {model} rate limit — tunggu {wait}s...")
                    time.sleep(wait)
                    # Coba lagi model yang sama setelah tunggu
                    try:
                        print(f"  [LLM] Retry {model}...")
                        response = client.models.generate_content(
                            model=model,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                max_output_tokens=800,
                                temperature=0.3,
                            ),
                            contents=transcript
                        )
                        raw = response.text.strip() if response.text else ""
                        result = _clean_llm_output(raw)
                        if result:
                            _store_in_cache(transcript, result)
                            return result, round(time.time() - t0, 2)
                    except Exception as e2:
                        print(f"  [LLM] Retry gagal: {e2}")
                    continue

                else:
                    print(f"  [LLM] {model} error: {err[:120]}")
                    continue

        return "[LLM ERROR: semua model gagal]", 0.0

    except Exception as e:
        return f"[LLM ERROR: {e}]", 0.0


# ─── TTS ─────────────────────────────────────────────────────────────────────
def run_tts(text, output_path):
    try:
        sys.path.insert(0, str(APP_DIR))
        if "tts" in sys.modules:
            del sys.modules["tts"]
        import tts as tts_mod
        t0 = time.time()
        tts_mod.synthesize_speech(text, output_path=str(output_path))
        return True, round(time.time() - t0, 2)
    except Exception as e:
        return False, 0.0

# ─── GROUND TRUTH LOOKUP ─────────────────────────────────────────────────────
def get_gt(filename):
    name = Path(filename).stem.lower()
    # Urutkan key dari yang terpanjang agar audio10-audio20 dicek lebih dulu dari audio1
    for key in sorted(GROUND_TRUTH.keys(), key=len, reverse=True):
        if key.lower() in name:
            return GROUND_TRUTH[key]
    return ""

# ─── PROSES SATU FILE ────────────────────────────────────────────────────────
def process_one(audio_path, output_dir, idx, total):
    fname = Path(audio_path).name
    stem  = Path(audio_path).stem
    gt    = get_gt(fname)

    print(f"\n[{idx}/{total}] {fname}")
    rec = {
        "file": fname, "folder": Path(audio_path).parent.name,
        "ground_truth": gt,
        "stt_transcript": "", "stt_wer": None, "stt_cer": None, "stt_latency": 0,
        "lang_mix": "",
        "llm_response": "", "llm_latency": 0,
        "tts_success": False, "tts_output": "", "tts_latency": 0,
        "total_latency": 0, "error": None
    }
    t_total = time.time()

    try:
        # ── STT ──
        transcript, stt_lat = run_stt(audio_path)
        rec["stt_transcript"] = transcript
        rec["stt_latency"]    = stt_lat
        rec["lang_mix"]       = detect_lang(transcript)
        if gt:
            rec["stt_wer"] = compute_wer(gt, transcript)
            rec["stt_cer"] = compute_cer(gt, transcript)
        print(f"  STT ({stt_lat:.1f}s) WER={rec['stt_wer']} CER={rec['stt_cer']} [{rec['lang_mix']}]")
        print(f"  → {transcript[:80]}")

        # ── LLM — dengan cache, hemat quota ──
        llm_resp, llm_lat = run_llm(transcript)
        rec["llm_response"] = llm_resp
        rec["llm_latency"]  = llm_lat
        print(f"  LLM ({llm_lat:.1f}s) → {llm_resp[:80]}")

        # Jeda hanya jika benar-benar memanggil API (bukan cache)
        if llm_lat > 0:
            time.sleep(8)

        # ── TTS ──
        tts_out = Path(output_dir) / f"response_{stem}.wav"
        ok, tts_lat = run_tts(llm_resp, tts_out)
        rec["tts_success"] = ok
        rec["tts_output"]  = str(tts_out) if ok else ""
        rec["tts_latency"] = tts_lat
        print(f"  TTS ({tts_lat:.1f}s) {'✓' if ok else '✗'}")

    except Exception as e:
        rec["error"] = str(e)
        print(f"  ERROR: {e}")

    rec["total_latency"] = round(time.time() - t_total, 2)
    return rec

# ─── SAVE ────────────────────────────────────────────────────────────────────
def save_results(results, log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    json_path = log_dir / "pipeline_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total    = len(results)
    suc      = sum(1 for r in results if not r["error"])
    tts_ok   = sum(1 for r in results if r["tts_success"])
    wer_l    = [r["stt_wer"] for r in results if r["stt_wer"] is not None]
    cer_l    = [r["stt_cer"] for r in results if r["stt_cer"] is not None]
    lat_l    = [r["total_latency"] for r in results]
    stt_l    = [r["stt_latency"] for r in results if r["stt_latency"] > 0]
    llm_l    = [r["llm_latency"] for r in results if r["llm_latency"] > 0]
    tts_l    = [r["tts_latency"] for r in results if r["tts_latency"] > 0]
    cache_hits = sum(1 for r in results if r["llm_latency"] == 0.0 and not str(r["llm_response"]).startswith("[LLM ERROR"))

    avg = lambda l: round(sum(l)/len(l), 4) if l else 0
    mn  = lambda l: round(min(l), 4) if l else 0
    mx  = lambda l: round(max(l), 4) if l else 0

    lang_cnt = {}
    for r in results:
        lm = r.get("lang_mix", "?")
        lang_cnt[lm] = lang_cnt.get(lm, 0) + 1

    lines = [
        "="*65,
        "  RINGKASAN ANALISIS PIPELINE CS-NLP",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "="*65, "",
        "STATISTIK UMUM",
        f"  Total file diproses : {total}",
        f"  Pipeline sukses     : {suc} ({round(suc/total*100,1)}%)" if total else "",
        f"  TTS berhasil        : {tts_ok} ({round(tts_ok/total*100,1)}%)" if total else "",
        f"  File dengan GT      : {len(wer_l)}",
        f"  LLM cache hits      : {cache_hits} dari {total} (hemat {cache_hits} API call)",
        "",
        "DISTRIBUSI BAHASA (Code-Switching)",
    ]
    for lang, cnt in sorted(lang_cnt.items(), key=lambda x: -x[1]):
        lines.append(f"  {lang:<12}: {cnt} file ({round(cnt/total*100,1)}%)")

    lines += [
        "", "EVALUASI STT — Whisper small",
        f"  WER rata-rata  : {avg(wer_l)}",
        f"  WER min/max    : {mn(wer_l)} / {mx(wer_l)}",
        f"  CER rata-rata  : {avg(cer_l)}",
        f"  CER min/max    : {mn(cer_l)} / {mx(cer_l)}",
        f"  Latency rata2  : {avg(stt_l)}s",
        "", "EVALUASI LLM — Gemini",
        f"  Latency rata2  : {avg(llm_l)}s  (hanya API call, cache=0.0s)",
        f"  Latency min/max: {mn(llm_l)}s / {mx(llm_l)}s",
        "", "EVALUASI TTS — Coqui VITS + G2P-ID",
        f"  Latency rata2  : {avg(tts_l)}s",
        "", "LATENCY END-TO-END",
        f"  Rata-rata      : {avg(lat_l)}s",
        f"  Min / Max      : {mn(lat_l)}s / {mx(lat_l)}s",
        "", "DETAIL PER FILE",
        f"  {'File':<32} {'WER':<7} {'CER':<7} {'Lang':<10} {'Latency'}",
        "-"*65,
    ]
    for r in results:
        wer = str(r["stt_wer"]) if r["stt_wer"] is not None else "N/A"
        cer = str(r["stt_cer"]) if r["stt_cer"] is not None else "N/A"
        err = " ✗" if r["error"] else " ✓"
        cache_tag = " [cache]" if r["llm_latency"] == 0.0 and not str(r["llm_response"]).startswith("[LLM") else ""
        lines.append(
            f"  {r['file']:<32} {wer:<7} {cer:<7} {r['lang_mix']:<10} {r['total_latency']:.1f}s{err}{cache_tag}"
        )

    lines += ["", "="*65]
    summary = "\n".join(lines)

    summary_path = log_dir / "pipeline_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print("\n" + summary)
    print(f"\n✓ JSON  : {json_path}")
    print(f"✓ Summary: {summary_path}")

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",   action="store_true", help="Proses semua file")
    parser.add_argument("--limit", type=int, default=30, help="Batas jumlah file (default: 30)")
    args = parser.parse_args()

    print("="*65)
    print("  ANALISIS PIPELINE — Code-Switching Speech-to-Speech NLP")
    print("="*65)

    print("\n[1] Mengumpulkan file audio corpus...")
    audio_dir = BASE_DIR / "data" / "corpus" / "audio"
    files = []
    for sub in ["A", "B"]:
        folder = audio_dir / sub
        if folder.exists():
            wavs = sorted(folder.glob("*.wav"))
            files.extend(wavs)
            print(f"  Folder {sub}: {len(wavs)} file")
        else:
            print(f"  ⚠ Folder {sub} tidak ada")

    if not files:
        print("\n✗ Tidak ada file audio ditemukan!")
        sys.exit(1)

    total_available = len(files)
    if not args.all:
        limit = args.limit
        files_a = [f for f in files if f.parent.name == "A"]
        files_b = [f for f in files if f.parent.name == "B"]
        ratio = limit / total_available
        n_a = min(len(files_a), max(1, round(len(files_a) * ratio)))
        n_b = min(len(files_b), max(1, limit - n_a))
        sampled = files_a[:n_a] + files_b[:n_b]
        files = sampled[:limit]
        print(f"\n  Sampling {len(files)}/{total_available} file (dari A: {n_a}, dari B: {n_b})")
        print(f"  Gunakan --all untuk proses semua, atau --limit N untuk jumlah berbeda")
    else:
        print(f"\n  Memproses SEMUA {total_available} file")

    out_dir = BASE_DIR / "temp" / "responses"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[2] Pipeline dimulai... ({len(files)} file)")
    print(f"    Cache aktif — transcript mirip tidak akan panggil API ulang")
    print("-"*65)

    results = []
    for i, fp in enumerate(files, 1):
        rec = process_one(str(fp), out_dir, i, len(files))
        results.append(rec)

    print(f"\n[3] Menyimpan hasil...")
    print(f"    Total cache hits: {sum(1 for r in results if r['llm_latency']==0.0 and not str(r['llm_response']).startswith('[LLM'))}/{len(results)}")
    save_results(results, BASE_DIR / "logs")
    print("\n✓ SELESAI!")

if __name__ == "__main__":
    main()