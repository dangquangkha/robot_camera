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
        if self.is_listening: 
            # Nếu đang nghe mà bấm lại thì coi như lệnh Dừng
            self.is_listening = False
            self.update_log("System: Đã tắt chế độ nghe liên tục.", "FF0000")
            return
            
        threading.Thread(target=self._process_voice, daemon=True).start()

    def _process_voice(self):
        self.is_listening = True
        self.update_log("Mic: Đang nghe liên tục (Bấm lại nút Nói để dừng)...", "00FFFF")
        
        system_prompt = self.brain.get_prompt() 

        while self.is_listening:
            user_text = self.voice_sys.listen()
            
            if not user_text:
                continue # Nếu không nghe thấy gì, quay lại nghe tiếp

            self.update_log(f"You: {user_text}", "FFFFFF")

            # Kiểm tra từ khóa dừng lại
            stop_keywords = ["dừng lại", "stop", "kết thúc", "hẹn gặp lại"]
            if any(word in user_text.lower() for word in stop_keywords):
                self.update_log("System: Tạm biệt!", "FF0000")
                self.voice_sys.text_to_speech("Goodbye! See you later.")
                self.is_listening = False
                break

            # AI trả lời
            reply = self.voice_sys.ask_gpt(user_text, system_prompt)
            self.update_log(f"Tutor: {reply}", "00FF00")
            
            # Phát âm thanh (Lưu ý: hàm text_to_speech trong chat_logic.py của bạn đang block luồng 
            # cho đến khi nói xong, điều này vô tình giúp AI không nghe đúng giọng của chính nó)
            self.voice_sys.text_to_speech(reply)
            
            # Sau khi nói xong, tự động quay lại đầu vòng lặp để nghe tiếp

    def update_log(self, text, color="FFFFFF"):
        # Cập nhật giao diện an toàn từ luồng phụ
        def _up(dt):
            if 'lbl_tutor_log' in self.ids:
                self.ids.lbl_tutor_log.text += f"[color={color}]{text}[/color]\n"
        Clock.schedule_once(_up)

    def go_back(self):
        self.manager.current = 'home'