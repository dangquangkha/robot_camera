import threading
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from models.tutor_logic import TutorBrain  # <--- Import file mới

class TutorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voice_sys = None
        self.brain = TutorBrain() # Khởi tạo bộ não phân loại level
        self.is_listening = False

    def on_enter(self):
        app = App.get_running_app()
        self.voice_sys = app.voice_sys
        self.update_log("System: Chọn cấp độ để bắt đầu...", "00FFFF")

    def select_level(self, level):
        """Hàm này được gọi khi bấm nút chọn Level"""
        msg = self.brain.set_level(level)
        self.update_log(f"System: {msg}", "00FF00")
        
        # AI tự động chào hỏi theo level mới
        greeting_prompt = f"{self.brain.get_prompt()} Say hello to the student and ask a simple question."
        threading.Thread(target=self._ai_speak_greeting, args=(greeting_prompt,)).start()

    def _ai_speak_greeting(self, prompt):
        """AI chủ động nói xin chào"""
        reply = self.voice_sys.ask_gpt("Hello", prompt)
        self.update_log(f"Tutor ({self.brain.current_level}): {reply}", "FFFF00")
        self.voice_sys.text_to_speech(reply)

    def start_voice_chat(self):
        """Bấm nút 'Nói'"""
        if self.is_listening: return
        threading.Thread(target=self._process_voice).start()

    def _process_voice(self):
        self.is_listening = True
        self.update_log("Mic: Đang nghe...", "AAAAAA")
        
        user_text = self.voice_sys.listen()
        if not user_text:
            self.update_log("Mic: Không nghe rõ.", "FF0000")
            self.is_listening = False
            return

        self.update_log(f"You: {user_text}", "FFFFFF")

        # --- ĐIỂM QUAN TRỌNG NHẤT ---
        # Lấy prompt cấu hình A1-C2 từ TutorBrain nạp vào OpenAI
        system_prompt = self.brain.get_prompt() 
        
        reply = self.voice_sys.ask_gpt(user_text, system_prompt)
        
        self.update_log(f"Tutor: {reply}", "00FF00")
        self.voice_sys.text_to_speech(reply)
        self.is_listening = False

    def update_log(self, text, color="FFFFFF"):
        # Cập nhật giao diện an toàn từ luồng phụ
        def _up(dt):
            if 'lbl_tutor_log' in self.ids:
                self.ids.lbl_tutor_log.text += f"[color={color}]{text}[/color]\n"
        Clock.schedule_once(_up)

    def go_back(self):
        self.manager.current = 'home'