#!/usr/bin/uv run
# server.py
import os
import time
import tempfile
import threading
import uvicorn
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com/"


class ModelManager:
    def __init__(self):
        self.model: Optional[WhisperModel] = None
        self.last_used: float = 0
        self.lock = threading.Lock()

        # 启动后台线程检查模型使用情况
        self.check_thread = threading.Thread(target=self._check_usage, daemon=True)
        self.check_thread.start()

    def get_model(self) -> WhisperModel:
        with self.lock:
            if self.model is None:
                self.model = WhisperModel("turbo", device="cuda", compute_type="int8")
            self.last_used = time.time()
            return self.model

    def _check_usage(self):
        while True:
            time.sleep(60)
            with self.lock:
                if self.model is not None and time.time() - self.last_used > 60:
                    del self.model
                    self.model = None


model_manager = ModelManager()
app = FastAPI()


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        segments, info = model_manager.get_model().transcribe(
            file.file,
            beam_size=5,
            language="zh",
            initial_prompt="简体中文与英文混合内容，没有其他语言的内容",
        )
        full_text = " ".join(segment.text for segment in segments).strip()
        return {"text": "" if full_text == "null" else full_text, "error": ""}
    except Exception as e:
        return {"text": "", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
