from kivy.config import Config
# 1. Cấu hình bàn phím ảo cho màn hình cảm ứng
Config.set('kivy', 'keyboard_mode', 'systemanddock')
from kivy.app import App
# Import Models
import threading
from kivy.lang import Builder
from kivy.core.window import Window

from models.security_logic import SecuritySystem
from models.chat_logic import VoiceAssistant

# Import Controllers
# (Import này cần thiết để file .kv nhận diện được các class Screen)
from controllers.home_controller import HomeScreen
from controllers.security_controller import SecurityScreen
from controllers.tutor_controller import TutorScreen


class AiHomeApp(App):
    def build(self):
        # 1. Khởi tạo Models
        self.security_sys = SecuritySystem()
        self.voice_sys = VoiceAssistant()
        
        # 2. Load DeepFace/YOLO ngầm (tránh đơ lúc khởi động)
        threading.Thread(target=self.security_sys.load_resources, daemon=True).start()
        
        # 3. QUAN TRỌNG: Load giao diện và TRẢ VỀ (Return) nó
        # File layout.kv chứa ScreenManager là widget gốc
        return Builder.load_file('views/layout.kv')

    def on_stop(self):
        self.security_sys.stop()

if __name__ == '__main__':
    Window.fullscreen = 'auto' 
    AiHomeApp().run()