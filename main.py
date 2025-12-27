from kivy.config import Config
# 1. Cấu hình bàn phím ảo cho màn hình cảm ứng
Config.set('kivy', 'keyboard_mode', 'systemanddock')
import sys
import os # <--- THÊM MODULE NÀY ĐỂ XỬ LÝ ĐƯỜNG DẪN

# --- Fix DPI cho Windows ---
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1) 
    except: pass

Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'fullscreen', 'auto')

from kivy.app import App
import threading
from kivy.lang import Builder
from kivy.core.window import Window

# --- IMPORT MODELS ---
# Nếu file logic ở cùng cấp
from models.security_logic import SecuritySystem
from models.chat_logic import VoiceAssistant

# --- IMPORT CONTROLLERS ---
# Dựa trên file bạn gửi, các file controller nằm cùng cấp main.py
# Nên xóa 'controllers.' đi để tránh lỗi ModuleNotFoundError
try:
    from controllers.home_controller import HomeScreen
    from controllers.security_controller import SecurityScreen
    from controllers.tutor_controller import TutorScreen
    from controllers.elderly_controller import ElderlyScreen
except ImportError:
    # Fallback: Nếu bạn thực sự để trong thư mục controllers/
    from controllers.home_controller import HomeScreen
    from controllers.security_controller import SecurityScreen
    from controllers.tutor_controller import TutorScreen
    from controllers.elderly_controller import ElderlyScreen

class AiHomeApp(App):
    def build(self):
        # 1. Khởi tạo Models
        self.security_sys = SecuritySystem()
        self.voice_sys = VoiceAssistant()
        
        # 2. Load DeepFace/YOLO ngầm
        threading.Thread(target=self.security_sys.load_resources, daemon=True).start()
        
        # 3. SỬA LỖI ĐƯỜNG DẪN KV (QUAN TRỌNG)
        # Lấy đường dẫn thư mục chứa file main.py hiện tại
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Thử tìm file layout.kv ở cùng thư mục
        kv_path = os.path.join(current_dir, 'layout.kv')
        
        # Nếu không thấy, thử tìm trong thư mục views/ (phòng trường hợp bạn để trong views)
        if not os.path.exists(kv_path):
            kv_path = os.path.join(current_dir, 'views', 'layout.kv')
            
        if not os.path.exists(kv_path):
            print(f"❌ LỖI NGHIÊM TRỌNG: Không tìm thấy file layout.kv tại: {kv_path}")
            print("👉 Vui lòng kiểm tra file layout.kv có nằm cùng thư mục với main.py không.")
            return None # Tránh crash xấu, chỉ thoát app
            
        return Builder.load_file(kv_path) 

    def on_stop(self):
        if hasattr(self, 'security_sys'):
            self.security_sys.stop()

if __name__ == '__main__':
    AiHomeApp().run()