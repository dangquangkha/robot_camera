import threading
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from models.elderly_logic import ElderlyBrain

class ElderlyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voice_sys = None
        self.brain = ElderlyBrain()
        self.is_listening = False

    def on_enter(self):
        app = App.get_running_app()
        self.voice_sys = app.voice_sys
        self.update_log("Hệ thống: Con chào ông bà, con đã sẵn sàng tâm sự rồi ạ!", "00FFFF")

    def toggle_voice_chat(self):
        if self.is_listening:
            self.is_listening = False
            self.ids.btn_talk.text = "🎙️ BẮM ĐỂ NÓI CHUYỆN"
            self.ids.btn_talk.background_color = (0, 0.8, 1, 1)
        else:
            self.is_listening = True
            self.ids.btn_talk.text = "🛑 ĐANG NGHE... (BẤM ĐỂ DỪNG)"
            self.ids.btn_talk.background_color = (1, 0, 0, 1)
            threading.Thread(target=self._process_voice, daemon=True).start()

    def _process_voice(self):
        prompt = self.brain.get_prompt()
        while self.is_listening:
            user_text = self.voice_sys.listen()
            if not user_text: continue

            self.update_log(f"Ông/Bà: {user_text}", "FFFFFF")
            
            # AI phản hồi bằng tiếng Việt
            reply = self.voice_sys.ask_gpt(user_text, prompt)
            self.update_log(f"Cháu: {reply}", "00FF00")
            
            self.voice_sys.text_to_speech(reply)

    def update_log(self, text, color="FFFFFF"):
        def _up(dt):
            if 'lbl_elderly_log' in self.ids:
                self.ids.lbl_elderly_log.text += f"[color={color}]{text}[/color]\n"
        Clock.schedule_once(_up)

    def go_back(self):
        self.is_listening = False
        self.manager.current = 'home'
    
    def adjust_font(self, delta):
            """Hàm điều chỉnh kích cỡ chữ cho người già"""
            if 'lbl_elderly_log' in self.ids:
                # 1. Lấy cỡ chữ hiện tại (Kivy trả về dạng số thực)
                current_size = self.ids.lbl_elderly_log.font_size
                
                # 2. Tính toán cỡ mới và giới hạn trong khoảng an toàn (14 - 50)
                new_size = max(14, min(50, current_size + delta))
                
                # 3. Cập nhật lại cho Label
                self.ids.lbl_elderly_log.font_size = new_size
                
                # 4. Lưu lại vào bộ não (nếu bạn muốn đồng bộ với logic)
                self.brain.font_size = new_size
                
                # 5. Thông báo trạng thái
                self.update_log(f"Hệ thống: Đã chỉnh cỡ chữ thành {int(new_size)}", "FFFF00")