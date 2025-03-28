#!/usr/bin/uv run
# server.py
import os
import tempfile
import uvicorn

from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com/"

# 初始化模型（服务启动时加载，后续重复使用）
model = WhisperModel("turbo", device="cuda", compute_type="int8")

app = FastAPI()

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 将上传的音频保存为临时文件
    with tempfile.SpooledTemporaryFile() as temp_audio:
        temp_audio.write(await file.read())
        temp_audio.seek(0)
        try:
            # 使用 faster_whisper 进行识别
            segments, info = model.transcribe(temp_audio,
                                          beam_size=5,
                                          language="zh",
                                          initial_prompt="简体中文与英文混合内容，没有其他语言的内容",
                                          )
            full_text = " ".join(segment.text for segment in segments).strip()
            return {
                "text": "" if full_text == "null" else full_text,
                "error": ""
            }
        except Exception as e:
            return {"text": "","error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
