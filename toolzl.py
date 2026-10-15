import threading
import time
import sys
from zlapi import ZaloAPI, ThreadType, Message, Mention, MultiMsgStyle, MessageStyle

def custom_print(text):
    print(text)
    sys.stdout.flush()

def create_main_banner():
    banner = """

TOOL ZALO TREO NGÔN 
👑 Admin: Quốc Vũ
ℹ️ Phiên bản: v1.1
📲 Copyright: Anh Em Quốc Vũ 
⏰ Thời gian: {}
🔄 Cập nhật lần cuối: 5/2/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
✅ Sài Tool Quốc Vũ Vui Vẻ 📌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(time.strftime('%I:%M %p, %d/%m/%Y'))
    return banner

def create_instructions():
    instructions = """🔹 HƯỚNG DẪN SỬ DỤNG TOOL TREO NGÔN🔹

1️⃣ Nhập số lượng tài khoản Zalo muốn chạy
2️⃣ Nhập IMEI, Cookie cho từng tài khoản
3️⃣ Nhập tên file .txt chứa nội dung spam
4️⃣ Nhập delay giữa các tin nhắn (giây)
5️⃣ Chọn có bật thời gian tự hủy tin nhắn (TTL) hay không (Y/N)
6️⃣ Chọn nhóm (VD: 1,3)
7️⃣ Chọn có gửi tin nhắn kèm màu đỏ hay không (Y/N)


"""
    return instructions

def read_file_content(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if content:
                custom_print(f"✅ Đọc file thành công: {len(content)} ký tự")
            return content
    except Exception as e:
        custom_print(f"❌ Lỗi đọc file {filename}: {e}")
        return ""

def parse_selection(input_str, max_index):
    try:
        numbers = [int(i.strip()) for i in input_str.split(',')]
        return [n for n in numbers if 1 <= n <= max_index]
    except:
        custom_print("❌ Định dạng không hợp lệ!")
        return []

class Bot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies, mode="treongon", 
                 delay_min=0, message_text="", ttl=None, use_color=False):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.mode = mode
        self.delay_min = delay_min
        self.message_text = message_text
        self.ttl = ttl
        self.use_color = use_color
        self.running = True
        self.threads = []
        self.message_counts = {}

    def start_spam(self, thread_id, thread_type, ttl=None):
        if not self.message_text:
            custom_print("❌ Nội dung spam rỗng!")
            return
        
        self.message_counts[thread_id] = 0
        
        
        thread = threading.Thread(
            target=self.spam_messages_treongon,
            args=(thread_id, thread_type, ttl),
            daemon=True
        )
        self.threads.append(thread)
        thread.start()
        custom_print(f"✅ Đã khởi động thread Spam Cho Nhóm {thread_id}")

    def spam_messages_treongon(self, thread_id, thread_type, ttl=None):
        custom_print(f"🚀Quốc Vũ Bắt Đầu Spam Vào Nhóm {thread_id}")
        
        while self.running:
            mention = Mention("-1", length=len(self.message_text), offset=0)
            try:
                custom_print(f"Quốc Vũ  Đang Spam Tới Nhóm {thread_id}...")
                self.setTyping(thread_id, thread_type)
                time.sleep(4)
                
                if self.use_color:
                    style = MultiMsgStyle([
                        MessageStyle(
                            offset=0,
                            length=1000,
                            style="color",
                            color="#db342e",
                            auto_format=False,
                        ),
                        MessageStyle(
                            offset=0,
                            length=900,
                            style="font",
                            size="15",
                            auto_format=False
                        ),
                    ])
                    if ttl is not None:
                        self.send(
                            Message(text=self.message_text, mention=mention, style=style), 
                            thread_id=thread_id, 
                            thread_type=thread_type, 
                            ttl=ttl
                        )
                    else:
                        self.send(
                            Message(text=self.message_text, mention=mention, style=style), 
                            thread_id=thread_id, 
                            thread_type=thread_type
                        )
                else:
                    if ttl is not None:
                        self.send(
                            Message(text=self.message_text, mention=mention), 
                            thread_id=thread_id, 
                            thread_type=thread_type, 
                            ttl=ttl
                        )
                    else:
                        self.send(
                            Message(text=self.message_text, mention=mention), 
                            thread_id=thread_id, 
                            thread_type=thread_type
                        )
                
                self.message_counts[thread_id] += 1
                custom_print(f"✅ [{time.strftime('%H:%M:%S')}] Nhóm {thread_id} | Đã gửi: {self.message_counts[thread_id]} tin nhắn")
                
            except Exception as e:
                custom_print(f"❌ Quốc Vũ Lỗi Spam Nhóm {thread_id}: {e}")
            
            time.sleep(self.delay_min)

    def stop(self):
        self.running = False
        custom_print("🛑 Đang dừng tất cả threads...")

    def onMessage(self, *args, **kwargs):
        pass

    def onEvent(self, *args, **kwargs):
        pass

    def onAdminMessage(self, *args, **kwargs):
        pass

    def fetch_groups(self):
        try:
            custom_print("📋 Quốc Vũ Đang Lấy Danh Sách Nhóm...")
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = self.fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({
                    'id': group_id,
                    'name': group_name
                })
            custom_print(f"✅ Tìm thấy {len(group_list)} nhóm")
            return type('GroupObj', (), {
                'groups': [type('GroupItem', (), {'grid': g['id'], 'name': g['name']})() 
                          for g in group_list]
            })()
        except Exception as e:
            custom_print(f"❌ Quốc Vũ Không Thể Lấy Danh Sách Nhóm: {e}")
            return None

def start_multiple_accounts():
    print(create_main_banner())
    print(create_instructions())
    
    try:
        num_accounts = int(input("💠 Nhập số lượng tài khoản Zalo muốn chạy: "))
    except ValueError:
        custom_print("❌ Nhập sai, phải là số nguyên!")
        return
    
    all_bots = []
    
    for i in range(num_accounts):
        print(f"\n{'='*60}")
        print(f"📱 NHẬP THÔNG TIN CHO TÀI KHOẢN {i+1}/{num_accounts}")
        print(f"{'='*60}")
        
        try:
            imei = input("📱 Nhập IMEI của Zalo: ").strip()
            cookie_str = input("🍪 Nhập Cookie: ").strip()
            
            try:
                session_cookies = eval(cookie_str)
                if not isinstance(session_cookies, dict):
                    custom_print("❌ Cookie phải là dictionary!")
                    continue
            except:
                custom_print("❌ Cookie không hợp lệ, dùng dạng {'key': 'value'}!")
                continue
            
            custom_print("> Loading.")
            bot = Bot('api_key', 'secret_key', imei, session_cookies, mode="treongon")
            groups = bot.fetch_groups()
            
            if not groups or not hasattr(groups, 'groups') or not groups.groups:
                custom_print("❌ Không lấy được nhóm nào!")
                continue
            
            print(f"\n📋 DANH SÁCH NHÓM (Tổng: {len(groups.groups)}):")
            print("=" * 60)
            for idx, group in enumerate(groups.groups, 1):
                print(f"   {idx}. {group.name}")
            print("=" * 60)
            
            raw = input("🔸 Nhập số thứ tự nhóm muốn chạy (VD: 1,3,5): ").strip()
            selected = parse_selection(raw, len(groups.groups))
            if not selected:
                custom_print("❌ Không chọn nhóm nào!")
                continue
            
            selected_ids = [groups.groups[i - 1].grid for i in selected]
            custom_print(f"✅ Đã chọn {len(selected_ids)} nhóm")
            
            file_txt = input("📂 Nhập tên file .txt chứa nội dung spam: ").strip()
            message_text = read_file_content(file_txt)
            if not message_text:
                custom_print("❌ File rỗng hoặc không đọc được!")
                continue
            
            while True:
                try:
                    delay = float(input("⏳ Nhập delay giữa các lần gửi (giây): "))
                    if delay < 0:
                        custom_print("❌ Delay phải không âm!")
                        continue
                    break
                except ValueError:
                    custom_print("❌ Delay phải là số!")
            
            ttl = None
            while True:
                ttl_choice = input("⏰ Bật thời gian tự hủy tin nhắn (TTL)? (Y/N): ").lower()
                if ttl_choice in ['y', 'n']:
                    break
                custom_print("❌ Vui lòng nhập Y hoặc N!")
            
            if ttl_choice == 'y':
                while True:
                    try:
                        ttl_seconds = float(input("⏰ Nhập thời gian tự hủy (giây): "))
                        if ttl_seconds <= 0:
                            custom_print("❌ Thời gian TTL phải lớn hơn 0!")
                            continue
                        ttl = int(ttl_seconds * 1000)
                        break
                    except ValueError:
                        custom_print("❌ Thời gian TTL phải là số!")
            
            while True:
                color_choice = input("🎨 Gửi tin nhắn kèm màu đỏ? (Y/N): ").lower()
                if color_choice in ['y', 'n']:
                    break
                custom_print("❌ Vui lòng nhập Y hoặc N!")
            
            use_color = color_choice == 'y'
            
            
            bot.message_text = message_text
            bot.delay_min = delay
            bot.ttl = ttl
            bot.use_color = use_color
            
            
            for group_id in selected_ids:
                bot.start_spam(group_id, ThreadType.GROUP, ttl=ttl)
            
            all_bots.append(bot)
            custom_print(f"\n✅ Tài khoản {i+1} đã khởi động thành công!\n")
            
        except Exception as e:
            custom_print(f"❌ Lỗi nhập liệu tài khoản {i+1}: {e}")
            continue
    
    if not all_bots:
        custom_print("❌ Không có bot nào được khởi động!")
        return
    
    
    try:
        while True:
            time.sleep(60)
            total_messages = sum(sum(bot.message_counts.values()) for bot in all_bots)
            custom_print(f"⏰ [{time.strftime('%H:%M:%S')}] Quốc Vũ Đã Spam!| Tổng: {total_messages} tin nhắn")
    except KeyboardInterrupt:
        custom_print("\n\n🛑 Đang dừng tất cả bot...")
        for bot in all_bots:
            bot.stop()
        time.sleep(2)
        custom_print("👋 Đã dừng! Cảm ơn bạn đã sử dụng tool của Lê Quốc Vũ !")

if __name__ == "__main__":
    start_multiple_accounts()