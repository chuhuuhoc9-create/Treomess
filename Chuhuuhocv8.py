import multiprocessing
import requests
import os
import re
import json
import time
import random
import gc
import paho.mqtt.client as mqtt
from time import sleep
from datetime import datetime
import psutil
import threading
import sys

# ===== KIỂM TRA KEY TRƯỚC KHI CHẠY =====
def check_key():
    """Kiểm tra key để kích hoạt tool"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🔐 TOOL CẦN KEY ĐỂ KÍCH HOẠT 🔐                   ║
║                                                              ║
║            Tool Messenger - Bản quyền Chử Hữu Học              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    max_attempts = 3
    for attempt in range(max_attempts):
        key = input(f"\n🔑 Nhập key kích hoạt (Lần {attempt + 1}/{max_attempts}): ").strip()
        
        if key == "chuhuuhoc":
            print("\n✅ KÍCH HOẠT THÀNH CÔNG! Chào mừng Chử Hữu Học trở lại!\n")
            time.sleep(1)
            return True
        else:
            print(f"\n❌ Key không hợp lệ! Còn {max_attempts - attempt - 1} lần thử.\n")
            if attempt < max_attempts - 1:
                print("💡 ib zep lao de lay key: 0972487211")
    
    print("\n⚠️ Bạn đã nhập sai key quá 3 lần! Thoát chương trình...")
    return False

# ===== FIX LỖI "timestamp out of range for platform time_t" TRÊN HỆ THỐNG 32-BIT =====
_MAX_TIME_T = 2147483647
_original_time = time.time
def _safe_time():
    t = _original_time()
    return min(float(int(t) % _MAX_TIME_T), float(_MAX_TIME_T))
time.time = _safe_time
# ==================================================================================

# Thêm danh sách User-Agent cho mobile/kiwi/via
UA_KIWI = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.68 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; V2031) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.60 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; CPH2481) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36"
]

UA_VIA = [
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Linux; Android 11; V2109) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/112.0.5615.138 Mobile Safari/537.36 Via/4.9.0",
    "Mozilla/5.0 (Linux; Android 13; TECNO POVA 5) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.5735.134 Mobile Safari/537.36 Via/5.0.1",
    "Mozilla/5.0 (Linux; Android 12; Infinix X6710) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.138 Mobile Safari/537.36 Via/5.2.0",
    "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.6261.112 Mobile Safari/537.36 Via/5.3.1"
]

# Biến toàn cục để quản lý cookies động
global_cookies = []
global_running = True
command_thread = None

class QuocVuMQTT:
    def __init__(self):
        self.mqtt_client = None
        self.connected = False
        
    def connect_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(client_id=f"quocvu_{random.randint(10000,99999)}")
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            
            self.mqtt_client.connect("broker.emqx.io", 1883, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Lỗi kết nối: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("[MQTT] ✓ Kết nối thành công - Treo trụ ổn định")
            client.subscribe("quocvu/messenger/control")
        else:
            print(f"[MQTT] ✗ Kết nối thất bại với mã lỗi: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        print("[MQTT] Mất kết nối, đang thử kết nối lại...")
        time.sleep(5)
        self.connect_mqtt()
    
    def send_heartbeat(self, process_id, status="alive"):
        if self.connected and self.mqtt_client:
            try:
                data = {
                    "process_id": process_id,
                    "status": status,
                    "timestamp": int(time.time()),
                    "ram": psutil.virtual_memory().percent
                }
                self.mqtt_client.publish("quocvu/messenger/heartbeat", json.dumps(data))
            except:
                pass
    
    def disconnect(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def clear():
    print("\n" * 5)

def log_memory_usage():
    mem = psutil.virtual_memory()
    print(f"[RAM] Dung luong RAM: {mem.percent}% - Con lai: {mem.available // (1024 * 1024)} MB")

def banner():
    banner_text = """
╔══════════════════════════════════════════════════════════════╗
║     MESSENGER TREO NGÔN - Chử Hữu Học V8                         ║
║     Tool Treo Trụ Vĩnh Viễn + MQTT + Thêm Cookie             ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner_text)

class QuocVuMessenger:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = self.get_user_id()
        self.fb_dtsg = None
        self.session = requests.Session()
        self.session.headers.update({
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0'
        })
        self.init_params()
        self.user_agents = UA_KIWI + UA_VIA + [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]

    def get_user_id(self):
        match = re.search(r"c_user=(\d+)", self.cookie)
        if not match:
            raise Exception("> Cookies không hợp lệ")
        return match.group(1)

    def init_params(self):
        urls = ['https://mbasic.facebook.com', 'https://www.facebook.com', 'https://m.facebook.com']
        for url in urls:
            try:
                res = self.session.get(url, timeout=10)
                token = re.search(r'name="fb_dtsg" value="(.*?)"', res.text) or re.search(r'"token":"(.*?)"', res.text)
                if token:
                    self.fb_dtsg = token.group(1)
                    return
            except:
                continue
        raise Exception("Không tìm thấy fb_dtsg")

    def refresh_fb_dtsg(self):
        try:
            self.init_params()
            return True
        except Exception:
            return False

    def guitinnhanvobox(self, recipient_id, message):
        timestamp_sec = int(time.time())
        offline_id = str(timestamp_sec) + str(random.randint(100000, 999999))
        data = {
            'fb_dtsg': self.fb_dtsg,
            '__user': self.user_id,
            'body': message,
            'action_type': 'ma-type:user-generated-message',
            'timestamp': timestamp_sec,
            'offline_threading_id': offline_id,
            'message_id': offline_id,
            'thread_fbid': recipient_id,
            'source': 'source:chat:web',
            'client': 'mercury'
        }
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            for attempt in range(3):
                try:
                    response = requests.post('https://www.facebook.com/messaging/send/', 
                                           data=data, headers=headers, timeout=15)
                except Exception:
                    response = None

                if response is not None and response.status_code == 200:
                    response_text = response.text
                    if '"error":' in response_text or '"errors":' in response_text:
                        if attempt < 2:
                            self.refresh_fb_dtsg()
                            data['fb_dtsg'] = self.fb_dtsg
                            continue
                        return False
                    elif 'spam' in response_text.lower() or 'blocked' in response_text.lower():
                        return False
                    elif 'login' in response_text.lower():
                        return False
                    else:
                        return True
                else:
                    if response and response.status_code in [429, 403, 401]:
                        return False
                    elif attempt < 2:
                        self.refresh_fb_dtsg()
                        data['fb_dtsg'] = self.fb_dtsg
                        continue
                    return False
            return False
        except Exception as e:
            return False

# ===== LỆNH THÊM COOKIE TRONG LÚC CHẠY =====
def command_listener(processes_ref, thread_ids, thread_names, delay, message_text, num_processes):
    """Lắng nghe lệnh từ console để thêm cookie mới"""
    global global_cookies, global_running
    
    print("\n" + "="*60)
    print("🔥 CHẾ ĐỘ LỆNH ĐÃ BẬT 🔥")
    print("📝 Nhập lệnh (gõ 'help' để xem danh sách):")
    print("="*60)
    
    while global_running:
        try:
            cmd = input("\n📝 Lệnh > ").strip().lower()
            
            if cmd == 'help':
                print("""
╔══════════════════════════════════════════════════════════╗
║  DANH SÁCH LỆNH                                         ║
╠══════════════════════════════════════════════════════════╣
║  addcookie | ac  - Thêm cookie mới vào process đang chạy ║
║  list | ls        - Xem danh sách cookies hiện tại       ║
║  status | st      - Xem trạng thái các process           ║
║  exit | stop      - Dừng toàn bộ tool                    ║
╚══════════════════════════════════════════════════════════╝
                """)
            
            elif cmd in ['addcookie', 'ac']:
                print("\n[*] THÊM COOKIE MỚI:")
                cookie_input = input("  Cookie string: ").strip()
                if cookie_input:
                    name = input("  Tên hiển thị (mặc định: user): ").strip() or f"user_{len(global_cookies)+1}"
                    
                    # Kiểm tra cookie có hợp lệ không
                    try:
                        test_messenger = QuocVuMessenger(cookie_input)
                        print(f"  ✓ Cookie hợp lệ! User ID: {test_messenger.user_id}")
                        
                        # Thêm vào danh sách global
                        global_cookies.append((cookie_input, name))
                        
                        # Thêm vào process hiện tại (cần restart hoặc tạo process mới)
                        print(f"\n  ✅ Đã thêm cookie: {name}")
                        print("  ⚠️ LƯU Ý: Cookie mới sẽ được áp dụng sau khi khởi động lại tool!")
                        print("  💡 Để dùng ngay, hãy dừng tool (exit) và chạy lại với file cookie đã cập nhật")
                        
                    except Exception as e:
                        print(f"  ❌ Cookie không hợp lệ: {e}")
                else:
                    print("  ❌ Cookie không được để trống!")
            
            elif cmd in ['list', 'ls']:
                print("\n" + "="*50)
                print("📊 DANH SÁCH COOKIE HIỆN TẠI")
                print("="*50)
                for i, (cookie, name) in enumerate(global_cookies):
                    try:
                        c_user = re.search(r"c_user=(\d+)", cookie)
                        user_id = c_user.group(1) if c_user else "Unknown"
                        print(f"  #{i+1}: {name} | c_user={user_id}")
                    except:
                        print(f"  #{i+1}: {name} | {cookie[:50]}...")
                print(f"\n  Tổng số: {len(global_cookies)} cookies")
                print("="*50)
            
            elif cmd in ['status', 'st']:
                print("\n" + "="*50)
                print("📊 TRẠNG THÁI HỆ THỐNG")
                print("="*50)
                mem = psutil.virtual_memory()
                print(f"  RAM sử dụng: {mem.percent}%")
                print(f"  RAM còn lại: {mem.available // (1024 * 1024)} MB")
                print(f"  Số lượng process: {len(processes_ref)}")
                print(f"  Số cookies đang chạy: {len(global_cookies)}")
                print(f"  Delay: {delay}s")
                print(f"  Số boxes: {len(thread_ids)}")
                print("="*50)
            
            elif cmd in ['exit', 'stop']:
                print("\n⚠️ ĐANG DỪNG TOÀN BỘ TOOL...")
                global_running = False
                # Dừng tất cả processes
                for process in processes_ref:
                    if process.is_alive():
                        process.terminate()
                break
            
            else:
                print(f"❌ Lệnh không hợp lệ: {cmd}. Gõ 'help' để xem danh sách.")
                
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n⚠️ Nhận tín hiệu dừng từ bàn phím...")
            global_running = False
            break
        except Exception as e:
            print(f"❌ Lỗi: {e}")

def spam_worker_with_mqtt(process_id, cookies_chunk, thread_ids, thread_names, delay, message_text, total_processes):
    """
    Worker function có tích hợp MQTT để treo trụ
    """
    mqtt_manager = LeTuanAnhMQTT()
    mqtt_manager.connect_mqtt()
    
    try:
        cookie_index = 0
        last_heartbeat = time.time()
        
        while True:
            if not cookies_chunk:
                break
                
            cookie, name = cookies_chunk[cookie_index % len(cookies_chunk)]
            
            try:
                messenger = LeTuanAnhMessenger(cookie)
                
                # Spam vào tất cả boxes
                for thread_id, thread_name in zip(thread_ids, thread_names):
                    sleep(delay)
                    
                    success = messenger.guitinnhanvobox(thread_id, message_text)
                    
                    if success:
                        print(f"[Process {process_id}] ✓ Chử Hữu Học gửi thành công: {name} > {thread_name}")
                    else:
                        print(f"[Process {process_id}] ✗ Gửi thất bại: {name} > {thread_name}")
                    
                    # Gửi heartbeat qua MQTT mỗi 30 giây
                    if time.time() - last_heartbeat > 30:
                        mqtt_manager.send_heartbeat(process_id, "active")
                        last_heartbeat = time.time()
                    
                    gc.collect()
                    
            except Exception as e:
                print(f"[Process {process_id}] Lỗi tài khoản {name}: {str(e)}")
            
            cookie_index += 1
            
            # Log memory và heartbeat định kỳ
            if cookie_index % 10 == 0:
                try:
                    log_memory_usage()
                    mqtt_manager.send_heartbeat(process_id, "alive")
                except:
                    pass
            
            time.sleep(0.5)
            
    except Exception as e:
        print(f"[Process {process_id}] Lỗi trong quá trình treo: {str(e)}")
    finally:
        mqtt_manager.disconnect()

def treo_ngon_multiprocessing(cookies, thread_ids, thread_names, delay, message_text, num_processes=3):
    """
    Hàm treo ngôn chính sử dụng multiprocessing + MQTT
    """
    global global_cookies, global_running
    
    # Lưu cookies vào biến global để quản lý
    global_cookies = cookies.copy()
    
    try:
        cookies_per_process = len(cookies) // num_processes
        remaining_cookies = len(cookies) % num_processes
        
        processes = []
        
        start_idx = 0
        for i in range(num_processes):
            chunk_size = cookies_per_process + (1 if i < remaining_cookies else 0)
            end_idx = start_idx + chunk_size
            
            chunk = cookies[start_idx:end_idx]
            
            if chunk:
                process = multiprocessing.Process(
                    target=spam_worker_with_mqtt,
                    args=(i+1, chunk, thread_ids, thread_names, delay, message_text, num_processes)
                )
                processes.append(process)
            
            start_idx = end_idx
        
        # Hiển thị thông tin phân phối
        print(f"\n┌─────────────────────────────────────────────┐")
        print(f"│ ⚡ TREO NGÔN MQTT - Chử Hữu Học V8             │")
        print(f"├─────────────────────────────────────────────┤")
        for i, chunk in enumerate([cookies[i::num_processes] for i in range(num_processes)]):
            if chunk:
                print(f"│ Process {i+1}: {len(chunk):>2} cookies              │")
        print(f"│ Delay: {delay}s                               │")
        print(f"│ Boxes: {len(thread_ids):>2}                                 │")
        print(f"└─────────────────────────────────────────────┘\n")
        
        # Bắt đầu các processes
        for process in processes:
            process.start()
            print(f"[MAIN] Đã khởi động Process {process.pid}")
        
        print("[MQTT] ✓ Đã kích hoạt chế độ treo trụ vĩnh viễn")
        print("[CMD]  ✓ Chế độ lệnh đã bật - Gõ 'help' để xem danh sách\n")
        
        # Khởi động thread lắng nghe lệnh
        cmd_thread = threading.Thread(
            target=command_listener,
            args=(processes, thread_ids, thread_names, delay, message_text, num_processes),
            daemon=True
        )
        cmd_thread.start()
        
        # Đợi tất cả processes hoàn thành (hoặc Ctrl+C để dừng)
        try:
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            print("\n[MAIN] Đang dừng tất cả processes...")
            global_running = False
            for process in processes:
                process.terminate()
                process.join()
            print("[MAIN] Đã dừng treo ngôn")
            
    except Exception as e:
        print(f"[MAIN] Lỗi trong multiprocessing: {str(e)}")

def main():
    try:
        # Kiểm tra key trước khi chạy
        if not check_key():
            return
        
        clear()
        banner()
        
        # Nhập file cookies
        cookie_file = input("[ - ] Nhập file cookies: ").strip()
        if not cookie_file:
            raise Exception("> Chua nhap file cookies.")
        
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_lines = f.readlines()
            
            cookies = []
            count = 1
            for line in cookie_lines:
                cookie = line.strip()
                if cookie:
                    cookies.append((cookie, f"user{count}"))
                    count += 1
                    
            if not cookies:
                raise Exception("> File cookies trống.")
                
        except Exception as e:
            raise Exception(f"> Lỗi đọc file cookies: {str(e)}")
        
        # Nhập file nội dung
        print("[ - ] Nhập File nội dung ( enter để kết thúc )")
        files = []
        count = 1
        while True:
            fname = input(f"> File {count} : ")
            if fname.strip() == "":
                break
            files.append(fname.strip())
            count += 1
        
        if not files:
            raise Exception("> Chưa nhập file nào.")
        
        # Nhập delay
        delay = float(input("[ - ] Nhập Delay (giây): ").strip())
        
        # Auto set processes
        num_processes = min(3, max(2, len(cookies) // 2))
        print(f"[ * ] Tự động sử dụng {num_processes} processes")
        
        # Gộp nội dung các file
        messages = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if content:
                        messages.append(content)
            except Exception as e:
                print(f"> Loi file {f}: {e}")
        
        if not messages:
            raise Exception("> Không có nội dung tin nhắn.")
        full_message = "\n".join(messages)
        
        # Kiểm tra cookies
        valid_cookies = []
        print("\n[ * ] Đang kiểm tra cookies...")
        for cookie, name in cookies:
            try:
                messenger = QuocVuMessenger(cookie)
                valid_cookies.append((cookie, name))
                print(f"> {name} ✓ lấy fb_dtsg thành công (ID: {messenger.user_id})")
                time.sleep(0.5)
            except Exception as e:
                print(f"> {name} ✗ lỗi: {e}")
        
        if not valid_cookies:
            raise Exception("> Không có cookie nào hợp lệ")
        
        # Nhập ID box
        print("\n[ - ] Nhập ID Box ( enter để kết thúc )")
        box_ids = []
        count = 1
        while True:
            box_id_input = input(f"> ID Box {count} : ")
            if box_id_input.strip() == "":
                break
            box_ids.append(box_id_input.strip())
            count += 1
        
        if not box_ids:
            raise Exception("> Chưa nhập ID box nào")
        
        thread_names = [f"Box_{i+1}" for i in range(len(box_ids))]
        
        print(f"\n[ * ] Tổng hợp: {len(valid_cookies)} cookies hợp lệ, {len(box_ids)} boxes")
        print(f"[ * ] Delay: {delay}s, Nội dung: {len(full_message)} ký tự")
        
        # Bắt đầu treo ngôn với MQTT
        treo_ngon_multiprocessing(valid_cookies, box_ids, thread_names, delay, full_message, num_processes)
        
    except Exception as e:
        print(f"> Loi : {e}")
        input("\nNhấn Enter để thoát...")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
