import socket
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# 🌟 身份字典：用來對應 "位置代號" -> (IP, Port)
# 例如: {'MID': ('192.168.1.100', 5005), 'JG': ('192.168.1.101', 5005)}
clients = {}
addr_to_role = {} # 反向查詢字典

# 🌟 紀錄上次印出訊息的時間以避免終端機洗頻
last_print_time = {}

print(f"🚀 RPi 戰術語音路由器已啟動 (Port: {UDP_PORT})")
print("等待各節點連線...")

while True:
    try:
        data, addr = sock.recvfrom(8192)

        # 1. 處理註冊封包 (例如收到 b'HELLO:MID')
        if data.startswith(b'HELLO:'):
            role = data.split(b':')[1].decode('utf-8').strip()
            clients[role] = addr
            addr_to_role[addr] = role
            print(f"👋 {role} 已連線! 來自: {addr}")
            print(f"   目前線上名單: {list(clients.keys())}")
            continue

        # 確保寄件者有註冊過
        if addr not in addr_to_role:
            continue

        sender_role = addr_to_role[addr]

        # 2. 🌟 處理 CMD: 命令封包 (UTF-8 text, not audio)
        try:
            text_preview = data[:4].decode('utf-8')
        except UnicodeDecodeError:
            text_preview = ""

        if text_preview == "CMD:":
            # Command packet — broadcast to ALL clients (including sender for self-display)
            cmd_text = data.decode('utf-8')
            now = time.time()
            print_key = f"CMD:{sender_role}"
            if print_key not in last_print_time or (now - last_print_time[print_key] > 1.0):
                print(f"📨 [{sender_role}] 發送指令: {cmd_text[:80]}...")
                last_print_time[print_key] = now

            # Broadcast command to ALL registered clients
            for role, client_addr in clients.items():
                sock.sendto(data, client_addr)
            continue

        # 3. 解析語音封包標頭 (前 4 Bytes 是目標)
        target_role = data[:4].decode('utf-8').strip()
        audio_payload = data[4:]

        # 4. 抽換標頭：把標頭改成「發信者的名字」，長度強制補齊 4 Bytes
        sender_header = sender_role.ljust(4, ' ').encode('utf-8')
        forward_data = sender_header + audio_payload

        # 5. 【核心路由邏輯】
        now = time.time()
        print_key = f"{sender_role}->{target_role}"

        if print_key not in last_print_time or (now - last_print_time[print_key] > 1.0):
            if target_role == 'ALL':
                print(f"📡 {sender_role} 正在全頻廣播...")
            else:
                print(f"🤫 {sender_role} 正在密語給 {target_role.strip()}...")
            last_print_time[print_key] = now

        if target_role == 'ALL':
            # 廣播：發給線上所有人 (自己除外)
            for role, client_addr in clients.items():
                if client_addr != addr:
                    sock.sendto(forward_data, client_addr)

        elif target_role in clients:
            # 密語：只發給指定的單一目標
            target_addr = clients[target_role]
            sock.sendto(forward_data, target_addr)

    except Exception as e:
        pass # 實戰中為保持效能，底層錯誤直接 pass
