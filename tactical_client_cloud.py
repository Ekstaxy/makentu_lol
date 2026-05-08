"""
tactical_client_cloud.py — Central tactical voice client.

5v5 LOL voice system:
  - 4 ally buttons: press to switch audio to that ally, press again to go back to ALL
  - 5 enemy buttons: show countdown when enemy spell info is detected
  - Voice pipeline: Whisper + OpenAI → enemy alerts broadcast via RPi

Usage:
    python tactical_client_cloud.py
"""

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

try:
    import pyaudio
    AUDIO_BACKEND = "pyaudio"
except Exception:
    pyaudio = None
    import sounddevice as sd
    AUDIO_BACKEND = "sounddevice"

# =====================================================================
# ⚙️  Configuration
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "tactical_config.json"

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "server_ip": "172.20.10.2",
        "server_port": 5005,
        "my_role": "MID",
        "my_hero": "蓋倫",
        "allies": ["JG", "TOP", "BOT", "SUP"],
        "enemies": ["安妮", "好運姐", "阿姆姆", "雷歐娜", "墨菲特"],
    }

config = load_config()

RPI_IP = config.get("server_ip", "172.20.10.2")
UDP_PORT = config.get("server_port", 5005)
LOCAL_IPC_PORT = 5006          # Loupedeck plugin → this client
LOCAL_PLUGIN_PORT = 5005       # this client → Loupedeck plugin

MY_ROLE = config.get("my_role", "MID")
MY_HERO = config.get("my_hero", "")
ALLIES = config.get("allies", [])[:4]    # max 4 allies
ENEMIES = config.get("enemies", [])[:5]  # max 5 enemies

ENABLE_MIC = True
ENABLE_SPEAKER = True

CHANNELS = 1
RATE = 16000
CHUNK = 1024

# =====================================================================
# ⚙️  State
# =====================================================================
is_running = True
ptt_active = False
current_target = ""   # "" = broadcast ALL, otherwise a role name like "JG"
audio_buffer = []     # buffered audio chunks for Whisper

# =====================================================================
# ⚙️  Audio setup
# =====================================================================
class SoundDeviceInputAdapter:
    def __init__(self):
        self._stream = sd.RawInputStream(samplerate=RATE, channels=CHANNELS, dtype="int16", blocksize=CHUNK)
        self._stream.start()
    def read(self, frames, exception_on_overflow=False):
        data, _ = self._stream.read(frames)
        return data
    def stop_stream(self): self._stream.stop()
    def close(self): self._stream.close()

class SoundDeviceOutputAdapter:
    def __init__(self):
        self._stream = sd.RawOutputStream(samplerate=RATE, channels=CHANNELS, dtype="int16", blocksize=CHUNK)
        self._stream.start()
    def write(self, data): self._stream.write(data)
    def stop_stream(self): self._stream.stop()
    def close(self): self._stream.close()

stream_in = None
stream_out = None

if AUDIO_BACKEND == "pyaudio":
    FORMAT = pyaudio.paInt16
    p = pyaudio.PyAudio()
    if ENABLE_MIC:
        stream_in = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    if ENABLE_SPEAKER:
        stream_out = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
else:
    p = None
    print("⚠️ PyAudio 載入失敗，改用 sounddevice 後端。")
    if ENABLE_MIC:
        stream_in = SoundDeviceInputAdapter()
    if ENABLE_SPEAKER:
        stream_out = SoundDeviceOutputAdapter()

# =====================================================================
# ⚙️  Network
# =====================================================================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 0))

hello_msg = f"HELLO:{MY_ROLE}".encode("utf-8")
sock.sendto(hello_msg, (RPI_IP, UDP_PORT))
print(f"已向伺服器註冊身分: [{MY_ROLE}] → {RPI_IP}:{UDP_PORT}")

# =====================================================================
# 🔧  Send config to Loupedeck plugin
# =====================================================================
def send_config_to_plugin():
    """Send role + hero assignments to the local Loupedeck plugin on port 5005."""
    psock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        psock.sendto(f"CONFIG:MY_ROLE:{MY_ROLE}".encode("utf-8"), ("127.0.0.1", LOCAL_PLUGIN_PORT))

        for i, role in enumerate(ALLIES[:4], start=1):
            psock.sendto(f"CONFIG:ALLY{i}:{role}".encode("utf-8"), ("127.0.0.1", LOCAL_PLUGIN_PORT))

        for i, hero in enumerate(ENEMIES[:5], start=1):
            psock.sendto(f"CONFIG:ENEMY{i}:{hero}".encode("utf-8"), ("127.0.0.1", LOCAL_PLUGIN_PORT))

        print(f"📤 Config 已發送至 Loupedeck Plugin (port {LOCAL_PLUGIN_PORT})")
    finally:
        psock.close()

# =====================================================================
# 🎙️  IPC listener — receives PTT commands from Loupedeck plugin
# =====================================================================
def ipc_listener():
    ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ipc_sock.bind(("127.0.0.1", LOCAL_IPC_PORT))
    ipc_sock.settimeout(1.0)
    print(f"🔌 IPC 伺服器已啟動 (Port: {LOCAL_IPC_PORT})，等待 Logi Console 指令...")

    global ptt_active, current_target, audio_buffer

    while is_running:
        try:
            data, _ = ipc_sock.recvfrom(1024)
            msg = data.decode("utf-8").strip()

            if msg == "PTT_START":
                ptt_active = True
                audio_buffer = []
                target_display = current_target if current_target else "ALL"
                print(f"\n🎤 [目標: {target_display}] 🟢 開始錄音...")

            elif msg == "PTT_STOP":
                ptt_active = False
                print("🔇 [停止發話] 🔴 按鈕已放開！")
                if audio_buffer:
                    buf_copy = list(audio_buffer)
                    audio_buffer = []
                    threading.Thread(target=voice_analysis_pipeline, args=(buf_copy,), daemon=True).start()

            elif msg == "PTT_ALL_TOGGLE":
                current_target = ""
                print("📡 [廣播模式] 語音發送給所有人")

            elif msg.startswith("PTT_ALLY") and msg.endswith("_TOGGLE"):
                # PTT_ALLY3_TOGGLE → slot 3
                try:
                    slot = int(msg.replace("PTT_ALLY", "").replace("_TOGGLE", ""))
                    if 1 <= slot <= len(ALLIES):
                        role = ALLIES[slot - 1]
                        if current_target == role:
                            current_target = ""
                            print(f"📡 [{role}] 取消密語 → 廣播模式 (ALL)")
                        else:
                            current_target = role
                            print(f"🤫 [{role}] 切換密語 → 語音只發給 {role}")
                except ValueError:
                    pass

            # Legacy PTT_JG_START / PTT_ALL_START support
            elif msg == "PTT_ALL_START":
                ptt_active = True
                current_target = ""
                audio_buffer = []
                print("\n🎤 [全頻廣播] 🟢 開始！")
            elif msg.startswith("PTT_") and msg.endswith("_START"):
                role = msg.replace("PTT_", "").replace("_START", "")
                ptt_active = True
                current_target = role
                audio_buffer = []
                print(f"\n🤫 [密語: {role}] 🟢 開始！")
            else:
                print(f"❓ 未知指令: {msg}")

        except socket.timeout:
            continue
        except Exception as e:
            if is_running:
                print(f"IPC 錯誤: {e}")

    ipc_sock.close()

# =====================================================================
# 📡  Audio receiver
# =====================================================================
def receive_and_play():
    if not stream_out:
        return
    print("📡 監聽戰術頻道中...")
    while is_running:
        try:
            data, addr = sock.recvfrom(8192)
            if len(data) <= 4:
                continue

            # Check for CMD: packets forwarded by RPi
            try:
                preview = data[:4].decode("utf-8")
            except UnicodeDecodeError:
                preview = ""

            if preview == "CMD:":
                handle_incoming_command(data)
                continue

            # Normal audio
            audio_data = data[4:]
            stream_out.write(audio_data)
        except Exception:
            pass

def handle_incoming_command(data):
    """Forward CMD: packets to local Loupedeck plugin."""
    try:
        cmd_text = data.decode("utf-8")
        print(f"📥 收到指令: {cmd_text[:80]}...")
        fwd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            fwd.sendto(data, ("127.0.0.1", LOCAL_PLUGIN_PORT))
        finally:
            fwd.close()
    except Exception as e:
        print(f"指令處理錯誤: {e}")

# =====================================================================
# 🚀  Audio sender
# =====================================================================
def record_and_send():
    if not stream_in:
        return
    print("🚀 麥克風就緒 (使用 Logi Console 控制 PTT)")

    while is_running:
        try:
            audio_data = stream_in.read(CHUNK, exception_on_overflow=False)

            if not ptt_active:
                continue

            audio_buffer.append(audio_data)

            # Single target routing
            target = current_target if current_target else "ALL"
            header = target.ljust(4)[:4].encode("utf-8")
            sock.sendto(header + audio_data, (RPI_IP, UDP_PORT))

        except Exception as e:
            if is_running:
                print(f"發送錯誤: {e}")

# =====================================================================
# 🧠  Voice analysis pipeline
# =====================================================================
_whisper_model = None

def _ensure_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("正在載入 Whisper 語音模型 (可能需要幾秒鐘)...")
        import whisper
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def voice_analysis_pipeline(buffer_chunks):
    """Transcribe → analyze → broadcast enemy alerts."""
    try:
        audio_np = np.frombuffer(b"".join(buffer_chunks), dtype=np.int16).astype(np.float32) / 32768.0

        if len(audio_np) < RATE * 0.5:
            print("⚠️ 錄音太短，跳過分析。")
            return

        model = _ensure_whisper()
        print("🧠 Whisper 辨識中...")
        result = model.transcribe(audio_np, language="zh", fp16=False)
        text = result["text"].replace(" ", "").strip()

        if not text:
            print("⚠️ Whisper 沒有辨識到有效文字。")
            return

        print(f"[Whisper 聽到]：{text}")

        payload = _analyze_voice(text)
        print(f"[結構化 JSON]：{json.dumps(payload, ensure_ascii=False, indent=2)}")

        _route_payload(payload)

    except Exception as e:
        print(f"語音分析錯誤: {e}")


def _analyze_voice(raw_text):
    """Call OpenAI to produce structured JSON."""
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            print("[警告] 無 OPENAI_API_KEY，使用原始文字。")
            return {"kind": "chat", "target": "", "lol_slang_line": raw_text}

        client = OpenAI(api_key=api_key)

        hero_list = "\n".join(f"    {i+1}. {h}" for i, h in enumerate(ENEMIES))

        prompt = f"""你是台灣《英雄聯盟》(LOL) 高端玩家與通訊分類器。請根據「使用者語音轉寫」產出**一個** JSON 物件。

【輸出規則】
1. 只輸出 JSON，不要 markdown、不要說明。
2. 必須包含鍵：kind, target, lol_slang_line。
3. 欄位：
   - kind：chat | status_report
   - target：英雄名稱（例如「安妮」）；若無明確目標填空字串
   - lol_slang_line：台服極簡術語一行
4. 當提到某個敵方英雄的技能/召喚師技能狀態時，kind = status_report。
5. 敵方英雄名單：
{hero_list}

使用者語音轉寫：「{raw_text}」"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.2,
            timeout=12,
        )
        raw = (response.choices[0].message.content or "").strip()

        # Extract JSON
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
        if fence:
            raw = fence.group(1).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])

        return {"kind": "chat", "target": "", "lol_slang_line": raw_text}

    except Exception as e:
        print(f"[AI 分析失敗] {e}")
        return {"kind": "chat", "target": "", "lol_slang_line": raw_text}


def _route_payload(payload):
    """Route analyzed payload: enemy alert → broadcast via RPi + local console."""
    kind = payload.get("kind", "").lower()
    target = payload.get("target", "")
    slang = payload.get("lol_slang_line", "")

    if kind == "status_report" and target:
        alert_json = json.dumps({
            "which character": target,
            "which skill": _infer_skill(slang),
            "lol_slang_line": slang,
        }, ensure_ascii=False)

        cmd_bytes = f"CMD:ENEMY_ALERT:{alert_json}".encode("utf-8")

        # Send to RPi for broadcast to all PCs
        sock.sendto(cmd_bytes, (RPI_IP, UDP_PORT))
        print(f"📤 Enemy alert → RPi: {target}")

        # Also trigger own console immediately
        local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            local.sendto(cmd_bytes, ("127.0.0.1", LOCAL_PLUGIN_PORT))
        finally:
            local.close()

    elif kind == "chat" and slang:
        try:
            import keyboard
            keyboard.send("enter")
            time.sleep(0.3)
            keyboard.write(slang, delay=0.05)
            time.sleep(0.2)
            keyboard.send("enter")
            print(f"💬 已發送遊戲內訊息: {slang}")
        except Exception as e:
            print(f"遊戲訊息發送失敗: {e}")


def _infer_skill(slang_line):
    s = slang_line.lower()
    if "沒閃" in slang_line or "no flash" in s:
        return "flash"
    if "沒大" in slang_line or "no r" in s:
        return "ultimate"
    if "沒傳" in slang_line or "沒tp" in s or "no tp" in s:
        return "teleport"
    if "沒治" in slang_line:
        return "heal"
    if "沒淨化" in slang_line:
        return "cleanse"
    return "unknown"


# =====================================================================
# 🏁  Main
# =====================================================================
print(f"\n🌐 連接至 RPi 路由器 ({RPI_IP}:{UDP_PORT})")
print(f"🎮 我: {MY_ROLE} ({MY_HERO})")
print(f"🤝 隊友: {', '.join(ALLIES)}")
print(f"⚔️  敵方: {', '.join(ENEMIES)}")

send_config_to_plugin()

# Pre-load Whisper in background
def _preload():
    _ensure_whisper()
    print("✅ Whisper 模型載入完畢！")
threading.Thread(target=_preload, daemon=True).start()

# Start threads
threading.Thread(target=ipc_listener, daemon=True).start()
threading.Thread(target=receive_and_play, daemon=True).start()
threading.Thread(target=record_and_send, daemon=True).start()

try:
    print("\n✅ 系統已啟動！")
    print("┌─────────────────────────────────────────┐")
    print("│  Creative Console 3×3 配置:              │")
    print("│  [Ally1] [Ally2] [Ally3]                 │")
    print("│  [Ally4] [Enemy1][Enemy2]                │")
    print("│  [Enemy3][Enemy4][Enemy5]                │")
    print("│                                          │")
    print("│  按盟友按鈕 → 切換密語/廣播              │")
    print("│  說敵方資訊 → 自動觸發倒數計時           │")
    print("└─────────────────────────────────────────┘")
    while is_running:
        time.sleep(1.0)
except KeyboardInterrupt:
    is_running = False

if stream_in:
    stream_in.stop_stream()
    stream_in.close()
if stream_out:
    stream_out.stop_stream()
    stream_out.close()
if p:
    p.terminate()
sock.close()
print("系統已安全關閉。")