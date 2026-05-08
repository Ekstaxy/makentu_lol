import socket
import threading

try:
    import pyaudio
    AUDIO_BACKEND = "pyaudio"
except Exception:
    pyaudio = None
    import sounddevice as sd
    AUDIO_BACKEND = "sounddevice"

# ================= 戰術參數設定區 =================
RPI_IP = "172.20.10.2"
UDP_PORT = 5005
LOCAL_IPC_PORT = 5006 # 🌟 新增：讓 Logi Console 通訊用的本機 Port

# 🌟 設定你的身分 (如果是另一台電腦，請改成 'JG', 'ADC' 等)
MY_ROLE = "ADC"  

ENABLE_MIC = True
ENABLE_SPEAKER = True # 為了測試密語，兩邊最好都打開喇叭
# ==================================================

# 🌟 新增：存放 Logi Console 送來的按鍵狀態
ipc_state = {"target": None}

CHANNELS = 1
RATE = 16000
CHUNK = 1024

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 0))

# 🌟 傳送註冊封包給 RPi
hello_msg = f"HELLO:{MY_ROLE}".encode('utf-8')
sock.sendto(hello_msg, (RPI_IP, UDP_PORT))
print(f"已向伺服器註冊身分: [{MY_ROLE}]")

stream_in = None
stream_out = None


class SoundDeviceInputAdapter:
    def __init__(self):
        self._stream = sd.RawInputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK,
        )
        self._stream.start()

    def read(self, frames, exception_on_overflow=False):
        data, _overflowed = self._stream.read(frames)
        return data

    def stop_stream(self):
        self._stream.stop()

    def close(self):
        self._stream.close()


class SoundDeviceOutputAdapter:
    def __init__(self):
        self._stream = sd.RawOutputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK,
        )
        self._stream.start()

    def write(self, data):
        self._stream.write(data)

    def stop_stream(self):
        self._stream.stop()

    def close(self):
        self._stream.close()


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

is_running = True

# --- 執行緒 0：接收 Logi Console 的指令 ---
def ipc_listener():
    ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ipc_sock.bind(("127.0.0.1", LOCAL_IPC_PORT))
    print(f"🔌 IPC 伺服器已啟動 (Port: {LOCAL_IPC_PORT})，等待 Logi Console 指令...")
    while is_running:
        try:
            ipc_sock.settimeout(1.0)
            data, _ = ipc_sock.recvfrom(1024)
            msg = data.decode('utf-8').strip()
            
            # 解析 Logi 送來的指令
            if msg == "PTT_ALL_START":
                ipc_state["target"] = "ALL "
                print("\n🎤 [全頻廣播] 🟢 按鈕已按下！發送語音給所有人...")
            elif msg == "PTT_JG_START":
                ipc_state["target"] = "JG  "
                print("\n🤫 [指定密語] 🟢 按鈕已按下！發送語音給 JG...")
            elif msg == "PTT_STOP":
                ipc_state["target"] = None
                print("\n🔇 [停止發話] 🔴 按鈕已放開！")
        except socket.timeout:
            continue
        except Exception as e:
            if is_running: print(f"IPC 錯誤: {e}")
    ipc_sock.close()

# --- 執行緒 1：負責聽 ---
def receive_and_play():
    if not stream_out: return
    print("📡 監聽戰術頻道中...")
    while is_running:
        try:
            data, addr = sock.recvfrom(8192)
            if len(data) > 4:
                # 🌟 拆解封包：前 4 Bytes 是誰發出的
                sender = data[:4].decode('utf-8').strip()
                audio_data = data[4:]
                
                # 這裡可以加上 print(f"[{sender}] 正在講話...") 但為了避免洗頻先註解掉
                stream_out.write(audio_data)
        except:
            pass

# --- 執行緒 2：負責講 (按鍵判斷路由) ---
def record_and_send():
    if not stream_in: return
    print("🚀 實時傳送語音中... (請使用 Logi Console 控制 PTT)")
    
    while is_running:
        try:
            # 隨時讀取麥克風，保持資料流暢通 (避免 buffer 塞爆)
            audio_data = stream_in.read(CHUNK, exception_on_overflow=False)
            
            # 🌟 路由邏輯判斷 (完全依賴 Logi IPC 訊號)
            target = ipc_state["target"]

            # 如果有按下按鈕，才把封包加上標頭射出去！
            if target:
                payload = target.encode('utf-8') + audio_data
                sock.sendto(payload, (RPI_IP, UDP_PORT))
                
        except Exception as e:
            if is_running: print(f"發送錯誤: {e}")

print(f"\n🌐 正在連接至 RPi 路由器 ({RPI_IP})...")
ipc_thread = threading.Thread(target=ipc_listener)
recv_thread = threading.Thread(target=receive_and_play)
send_thread = threading.Thread(target=record_and_send)

ipc_thread.start()
recv_thread.start()
send_thread.start()

try:
    while is_running:
        recv_thread.join(timeout=1.0)
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