#!/usr/bin/env python3

##### run with
## CFLAGS="-Wno-error -O2" UV_DEFAULT_INDEX=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple uv run VoiceInput.py
import asyncio
import io
import os
import time
import threading
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
from evdev import InputDevice, categorize, ecodes

# DEVICE_PATH = '/dev/input/by-id/usb-COMPANY_USB_Device-if02-event-kbd'
DEVICE_PATH = "/dev/input/by-id/usb-COMPANY_USB_Device-event-kbd"

import os

# 设置 Hugging Face Hub 的镜像源
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com/"

import logging

logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.INFO)
# 配置区 ===============================================
MODEL_SIZE = "turbo"  # 可选 tiny|base|small|medium|large-v3|turbo
LANGUAGE = "zh"  # 识别语言 zh/en/ja 等
SAMPLE_RATE = int(44100 / 2)  # 必须与输入设备匹配


# =====================================================
class VoiceInput:
    def __init__(self):
        self.is_recording = False
        self.model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="int8")
        print("语音输入...")

    def start_recording(self):
        audio_frames = []
        self.is_recording = True
        print("录音中...")
        temp_file = io.BytesIO()

        def callback(indata, frames, time, status):
            audio_frames.append(indata.copy())

        with sd.InputStream(callback=callback, channels=1, samplerate=SAMPLE_RATE):
            while self.is_recording:
                sd.sleep(100)

        write(temp_file, SAMPLE_RATE, np.concatenate(audio_frames, axis=0))
        temp_file.seek(0)  # Reset the file pointer to the beginning again

        segments, info = self.model.transcribe(
            temp_file,
            language=LANGUAGE,
            initial_prompt="简体中文与英文混合内容，没有其他语言的内容",
        )
        text = "".join(segment.text for segment in segments)
        os.system(f'wtype "{text}"')

    def run(self):
        try:
            # 连接到输入设备
            dev = InputDevice(DEVICE_PATH)
            # print(f"监听设备: {dev.name}")

            # 监听键盘事件
            async def event_loop():
                async for event in dev.async_read_loop():
                    if event.type == ecodes.EV_KEY:  # 仅处理按键事件
                        key_event = categorize(event)

                        # 检测 F4 键按下（KEY_F4）
                        if key_event.keycode == "KEY_F4":
                            if (
                                key_event.keystate == key_event.key_down
                                and self.is_recording == False
                            ):
                                threading.Thread(target=self.start_recording).start()
                            elif key_event.keystate == key_event.key_up:
                                self.is_recording = False

            asyncio.run(event_loop())
        except PermissionError:
            print("权限不足！请确认：")
            print("1. 用户已加入 input 组（需重启生效）")
            print(f"2. 设备 {DEVICE_PATH} 存在且可读")
        except FileNotFoundError:
            print(f"设备 {DEVICE_PATH} 不存在！")
        except Exception as e:
            print(f"错误: {str(e)}")
        finally:
            if "dev" in locals():
                dev.close()


if __name__ == "__main__":
    try:
        VoiceInput().run()
    except Exception as e:
        print(f"错误: {str(e)}")
        print("确保已安装: cudnn, wtype")
