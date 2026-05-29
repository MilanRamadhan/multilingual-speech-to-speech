import gradio as gr
import requests
import tempfile
import os
import re

BACKEND_URL = "http://127.0.0.1:8000/voice-chat"

def chat_with_voice(audio_path):
    if audio_path is None:
        return None, "", "", "[WARN] Belum ada audio. Silakan rekam suara terlebih dahulu."

    try:
        with open(audio_path, "rb") as f:
            response = requests.post(
                BACKEND_URL,
                files={"file": ("audio.wav", f, "audio/wav")},
                timeout=120
            )

        if response.status_code != 200:
            try:
                detail = response.json().get("detail", response.text)
            except:
                detail = response.text
            return None, "", "", f"[ERROR] Backend error: {detail}"

        # Baca log terbaru
        transcript = "—"
        ai_response = "—"
        log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "transcripts.txt")

        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()

            blocks = [b.strip() for b in content.split("====================") if b.strip()]
            if blocks:
                last = blocks[-1]
                
                # Parse NORMALIZED sebagai transcript UI
                t = re.search(r'NORMALIZED:\n(.*?)(?=\nTAGS:|\nRESPONSE:|\nAUDIO:|$)', last, re.DOTALL)
                # Parse RESPONSE (berhenti sebelum AUDIO:)
                r = re.search(r'RESPONSE:\n(.*?)(?=\nAUDIO:|$)', last, re.DOTALL)
                
                if t:
                    transcript = t.group(1).strip()
                if r:
                    ai_response = r.group(1).strip()

        # Simpan audio output
        out_path = tempfile.mktemp(suffix=".wav")
        with open(out_path, "wb") as f:
            f.write(response.content)

        return out_path, transcript, ai_response, "[SUCCESS] Selesai!"

    except requests.exceptions.ConnectionError:
        return None, "", "", "[ERROR] Backend tidak bisa diakses. Pastikan uvicorn sudah berjalan di port 8000."
    except Exception as e:
        return None, "", "", f"[ERROR] Error: {str(e)}"


# ── Custom CSS ────────────────────────────────────────────────────────────────
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

/* ── Root tokens ── */
:root {
    --bg-base:      #080c12;
    --bg-card:      #0d1420;
    --bg-surface:   #111c2d;
    --bg-hover:     #162235;
    --border:       #1e3050;
    --border-glow:  #2d5a9e;
    --accent:       #3b82f6;
    --accent-soft:  #1d4ed8;
    --accent-glow:  rgba(59,130,246,0.25);
    --teal:         #06b6d4;
    --teal-glow:    rgba(6,182,212,0.2);
    --text-primary: #e8f0fe;
    --text-secondary:#8bafd4;
    --text-muted:   #4d6b8a;
    --green:        #10b981;
    --red:          #ef4444;
    --amber:        #f59e0b;
    --font-display: 'Syne', sans-serif;
    --font-mono:    'DM Mono', monospace;
    --radius:       12px;
    --radius-lg:    18px;
}

/* ── Global reset ── */
*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container {
    background: var(--bg-base) !important;
    font-family: var(--font-mono) !important;
    color: var(--text-primary) !important;
    min-height: 100vh;
}

/* Subtle animated grid background */
.gradio-container::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
    z-index: 0;
}

/* ── Wrapper ── */
.main-wrapper {
    position: relative;
    z-index: 1;
    max-width: 1000px;
    margin: 0 auto;
    padding: 0 16px;
}

/* ── Header ── */
.header-block {
    text-align: center;
    padding: 48px 0 32px;
    position: relative;
}

.header-block .logo-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: linear-gradient(135deg, #0d1a2e 0%, #0a1525 100%);
    border: 1.5px solid var(--border-glow);
    box-shadow: 0 0 32px var(--accent-glow), inset 0 0 24px rgba(59,130,246,0.06);
    margin: 0 auto 20px;
    font-size: 28px;
    animation: pulse-ring 3s ease-in-out infinite;
}

@keyframes pulse-ring {
    0%, 100% { box-shadow: 0 0 24px var(--accent-glow), inset 0 0 24px rgba(59,130,246,0.06); }
    50%       { box-shadow: 0 0 48px rgba(59,130,246,0.4), inset 0 0 24px rgba(59,130,246,0.1); }
}

.header-block h1 {
    font-family: var(--font-display) !important;
    font-size: clamp(22px, 4vw, 34px) !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    background: linear-gradient(135deg, #e8f0fe 0%, #93c5fd 50%, #06b6d4 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    margin: 0 0 10px !important;
    line-height: 1.2 !important;
}

.header-block .subtitle {
    font-family: var(--font-mono) !important;
    font-size: 13px !important;
    color: var(--text-muted) !important;
    font-weight: 400;
    letter-spacing: 0.5px;
}

.header-block .lang-badges {
    display: flex;
    gap: 8px;
    justify-content: center;
    margin-top: 14px;
    flex-wrap: wrap;
}

.header-block .badge {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid var(--border-glow);
    color: var(--accent);
    background: rgba(59,130,246,0.08);
    letter-spacing: 0.8px;
}

/* ── Section labels ── */
.section-label {
    font-family: var(--font-display) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    margin: 0 0 10px !important;
}

/* ── Cards ── */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 24px;
    transition: border-color 0.3s, box-shadow 0.3s;
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-glow), transparent);
    opacity: 0.6;
}

.card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 0 24px rgba(59,130,246,0.07);
}

/* ── Gradio component overrides ── */

/* Labels */
label, .svelte-1gfkn6j {
    font-family: var(--font-mono) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    letter-spacing: 0.3px !important;
}

/* Textboxes */
textarea, .scroll-hide {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
    font-size: 13px !important;
    padding: 14px 16px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    resize: none !important;
}

textarea:focus {
    border-color: var(--border-glow) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
    outline: none !important;
}

textarea::placeholder {
    color: var(--text-muted) !important;
    font-style: italic;
}

/* Audio component wrapper */
.waveform-container, audio-player {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}

/* Gradio audio / waveform */
.gr-audio, [data-testid="audio"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}

/* ── Submit button ── */
#submit-btn {
    width: 100% !important;
    padding: 16px 28px !important;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-soft) 100%) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-display) !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: #fff !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 20px rgba(59,130,246,0.35) !important;
    position: relative !important;
    overflow: hidden !important;
}

#submit-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 50%);
}

#submit-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(59,130,246,0.5) !important;
}

#submit-btn:active {
    transform: translateY(0) !important;
}

/* ── Status box ── */
#status-box textarea {
    font-size: 12px !important;
    padding: 10px 14px !important;
    background: var(--bg-surface) !important;
    border-radius: 8px !important;
    min-height: unset !important;
}

/* Status color states via content matching */
#status-box textarea[value*="[SUCCESS]"] {
    border-color: var(--green) !important;
    color: var(--green) !important;
}

#status-box textarea[value*="[ERROR]"] {
    border-color: var(--red) !important;
    color: var(--red) !important;
}

#status-box textarea[value*="[WARN]"] {
    border-color: var(--amber) !important;
    color: var(--amber) !important;
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-glow) 30%, var(--teal) 50%, var(--border-glow) 70%, transparent);
    opacity: 0.4;
    margin: 28px 0;
}

/* ── Panel titles ── */
.panel-title {
    font-family: var(--font-display) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: var(--text-secondary) !important;
    margin-bottom: 16px !important;
    display: flex;
    align-items: center;
    gap: 8px;
}

.panel-title::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 14px;
    border-radius: 2px;
    background: linear-gradient(180deg, var(--accent), var(--teal));
}

.title-badge {
    font-family: var(--font-display);
    font-size: 9px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--teal));
    color: #fff;
    padding: 2px 6px;
    border-radius: 4px;
    letter-spacing: 1px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }

/* ── Footer ── */
.footer-note {
    text-align: center;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    padding: 24px 0 32px;
    letter-spacing: 0.3px;
}

.footer-note span {
    color: var(--border-glow);
}

/* ── Gradio block container cleanup ── */
.block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

.gap { gap: 16px !important; }

/* Row gap */
.gr-form, .form { background: transparent !important; }

footer { display: none !important; }

/* Gradio upload / mic area */
.upload-container, [data-testid="audio"] > div {
    background: var(--bg-surface) !important;
    border-color: var(--border) !important;
    border-radius: var(--radius) !important;
}

/* Input section highlight */
#input-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 24px;
    position: relative;
    overflow: hidden;
}
#input-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--teal));
    opacity: 0.7;
}

/* Output section */
#output-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 24px;
    position: relative;
    overflow: hidden;
}
#output-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--teal), var(--accent));
    opacity: 0.5;
}
"""

# ── HTML decorations ──────────────────────────────────────────────────────────
header_html = """
<div class="header-block">
  <div class="logo-ring"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent-soft)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg></div>
  <h1>Voice Chatbot CS-NLP</h1>
  <p class="subtitle">Code-Switching Natural Language Processing · Speech Interface</p>
  <div class="lang-badges">
    <span class="badge">ID - Bahasa Indonesia</span>
    <span class="badge">EN - English</span>
    <span class="badge">AR - Arabic</span>
    <span class="badge">CS - Code-Switching</span>
  </div>
</div>
"""

input_title_html  = '<p class="panel-title"><span class="title-badge">IN</span> AUDIO INPUT</p>'
output_title_html = '<p class="panel-title"><span class="title-badge">OUT</span> SYSTEM OUTPUT</p>'

footer_html = """
<div class="footer-note">
  Rekam · Submit · Dengar &nbsp;|&nbsp; <span>CS-NLP Voice Interface v1.0</span>
</div>
"""


# ── Build UI ──────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Voice Chatbot CS-NLP",
    css=custom_css,
    theme=gr.themes.Base(
        primary_hue=gr.themes.colors.blue,
        neutral_hue=gr.themes.colors.slate,
        font=[gr.themes.GoogleFont("DM Mono"), "monospace"],
    )
) as demo:

    gr.HTML(header_html)

    with gr.Row(equal_height=False):
        # ── LEFT: Input ──────────────────────────────────────────────────────
        with gr.Column(scale=1, elem_id="input-panel"):
            gr.HTML(input_title_html)

            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Rekam atau upload file audio"
            )

            selected_file_box = gr.Textbox(
                label="File Terpilih",
                interactive=False,
                lines=1,
                placeholder="Belum ada file yang dipilih...",
                elem_id="selected-file-box"
            )

            submit_btn = gr.Button(
                "PROSES AUDIO",
                variant="primary",
                size="lg",
                elem_id="submit-btn"
            )

            status_box = gr.Textbox(
                label="Status",
                interactive=False,
                lines=1,
                placeholder="Menunggu input…",
                elem_id="status-box"
            )

        # ── RIGHT: Output ────────────────────────────────────────────────────
        with gr.Column(scale=1, elem_id="output-panel"):
            gr.HTML(output_title_html)

            transcript_box = gr.Textbox(
                label="Transkripsi — Speech to Text",
                interactive=False,
                lines=3,
                placeholder="Hasil transkripsi suara akan muncul di sini…"
            )

            response_box = gr.Textbox(
                label="Respons AI — Large Language Model",
                interactive=False,
                lines=4,
                placeholder="Jawaban dari AI akan muncul di sini…"
            )

            audio_output = gr.Audio(
                label="Respons Suara — Text to Speech",
                type="filepath"
            )

    gr.HTML(footer_html)

    # ── Wire up ──────────────────────────────────────────────────────────────
    def update_selected_file(audio_path):
        if audio_path:
            # Mengambil nama file dari path temporary Gradio
            return f"File terdeteksi: {os.path.basename(audio_path)}"
        return "Belum ada file yang dipilih..."

    audio_input.change(
        fn=update_selected_file,
        inputs=[audio_input],
        outputs=[selected_file_box]
    )
    
    submit_btn.click(
        fn=chat_with_voice,
        inputs=[audio_input],
        outputs=[audio_output, transcript_box, response_box, status_box]
    )

if __name__ == "__main__":
    demo.launch(server_port=7860)