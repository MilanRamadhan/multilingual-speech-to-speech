import os, shutil, tempfile, time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.stt import transcribe_speech_to_text
from app.llm import generate_response
from app.tts import synthesize_speech
from app.utils import normalize_text, detect_languages

app = FastAPI()

@app.post("/voice-chat")
async def voice_chat(file: UploadFile = File(...)):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(await file.read())
            tmp_path = temp_file.name

        # STT
        transcript = transcribe_speech_to_text(tmp_path)
        print("[STT] Hasil:", transcript)

        # NORMALIZATION
        normalized = normalize_text(transcript)
        tags = detect_languages(normalized)
        print("[NORMALIZED]", normalized)
        print("[TAGS]", tags)

        # LLM
        response_text = generate_response(normalized)
        if not response_text:
            response_text = "Maaf, saya tidak dapat merespons saat ini."
        print("[LLM]", response_text)

        # Simpan audio output dengan timestamp agar tidak overwrite
        timestamp = int(time.time())
        # Simpan audio output dengan timestamp
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        TEMP_DIR = os.path.join(BASE_DIR, "..", "temp")
        timestamp = int(time.time())
        os.makedirs(TEMP_DIR, exist_ok=True)
        output_audio_path = os.path.join(TEMP_DIR, f"output_{timestamp}.wav")
        output_audio = synthesize_speech(response_text, output_path=output_audio_path)

        # LOGGING
        LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(os.path.join(LOGS_DIR, "transcripts.txt"), "a", encoding="utf-8") as log:
            log.write("\n====================\n")
            log.write(f"TIMESTAMP: {timestamp}\n")
            log.write(f"TRANSCRIPT:\n{transcript}\n")
            log.write(f"NORMALIZED:\n{normalized}\n")
            log.write(f"TAGS:\n{tags}\n")
            log.write(f"RESPONSE:\n{response_text}\n")
            log.write(f"AUDIO: {output_audio_path}\n")

        return FileResponse(output_audio, media_type="audio/wav")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)