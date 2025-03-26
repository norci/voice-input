# server.py
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com/"

# 初始化模型（服务启动时加载，后续重复使用）
model = WhisperModel("turbo", device="cuda", compute_type="int8")

app = FastAPI()

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 校验文件类型
    if not file.filename.endswith((".wav", ".mp3", ".ogg", ".m4a")):
        raise HTTPException(400, "Unsupported file format")

    # 将上传的音频保存为临时文件
    with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
        temp_audio.write(await file.read())
        temp_path = temp_audio.name

    try:
        # 使用 faster_whisper 进行识别
        segments, info = model.transcribe(temp_path, beam_size=5,            language="zh",
            initial_prompt="简体中文与英文混合内容，没有其他语言的内容",
)
        full_text = " ".join(segment.text for segment in segments)
        return {
            "language": info.language,
            "text": full_text.strip()
        }
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        os.unlink(temp_path)  # 删除临时文件

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
