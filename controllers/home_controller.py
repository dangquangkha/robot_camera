import threading
import sys
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
# --- ĐÃ SỬA: Thêm Bezier vào dòng import dưới đây ---
from kivy.graphics import Color, Ellipse, Bezier,Triangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.factory import Factory

# --- Lớp Trái Tim 3D (Đã sửa từ Bong Bóng) ---
class Bubble3D(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (200, 200)
        self.original_size = (200, 200)
        self.is_animating = False
        
        with self.canvas:
            # Màu chính (đỏ hoặc đổi tùy bạn)
            self.color_instruction = Color(0.9, 0.1, 0.2, 1)

            # 🔴 Hình tròn chính
            self.circle = Ellipse()

            # ✨ Highlight tạo cảm giác 3D
            Color(1, 1, 1, 0.35)
            self.highlight = Ellipse()

        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        x, y = self.pos
        w, h = self.size

        # 🔴 Luôn là hình tròn (không méo)
        d = min(w, h)
        cx = x + w / 2
        cy = y + h / 2

        self.circle.pos = (
            cx - d / 2,
            cy - d / 2
        )
        self.circle.size = (d, d)

        # ✨ Highlight góc trên trái
        self.highlight.pos = (
            cx - d * 0.25,
            cy + d * 0.15
        )
        self.highlight.size = (
            d * 0.3,
            d * 0.2
        )


    def start_speaking_animation(self):
        if self.is_animating: return
        self.is_animating = True
        self._animate_loop()

    def _animate_loop(self, *args):
        if not self.is_animating:
            # Khi dừng, quay về kích thước gốc
            anim = Animation(size=self.original_size, duration=0.2, t='out_quad')
            anim.start(self)
            return

        # Hiệu ứng nhịp đập trái tim (Thình thịch)
        # Phóng to nhanh
        target_size = (self.original_size[0] * 1.15, self.original_size[1] * 1.15)
        anim = Animation(size=target_size, duration=0.1, t='out_circ')
        
        def on_complete(a, w):
            if self.is_animating:
                # Thu nhỏ lại một chút
                target_size_small = (self.original_size[0] * 0.95, self.original_size[1] * 0.95)
                anim_back = Animation(size=target_size_small, duration=0.15, t='in_out_sine')
                anim_back.bind(on_complete=self._animate_loop) # Lặp lại
                anim_back.start(self)
        
        anim.bind(on_complete=on_complete)
        anim.start(self)

    def stop_speaking_animation(self):
        self.is_animating = False

# Đăng ký class này với Kivy Factory để file .kv nhận diện được
Factory.register('Bubble3D', cls=Bubble3D)

# --- Controller Màn Hình Chính ---
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voice_sys = None
        self.is_listening_loop = False
        self.menu_open = False

    def on_enter(self):
        """Vào màn hình: Đợi 1 frame để UI load xong rồi mới kết nối Logic"""
        Clock.schedule_once(self._finish_init, 0)

    def _finish_init(self, dt):
        app = App.get_running_app()
        
        # 1. KẾT NỐI VỚI BỘ NÃO (QUAN TRỌNG)
        if hasattr(app, 'voice_sys') and app.voice_sys:
            self.voice_sys = app.voice_sys
            self.update_status("Đã kết nối AI. Đang lắng nghe...")
            self.start_home_listening()
        else:
            # Nếu không tìm thấy, báo lỗi ngay lên màn hình
            self.update_status("[LỖI] Không tìm thấy module Voice!")
            print("❌ LỖI: app.voice_sys chưa được khởi tạo trong main.py")
        
        self.close_menu()

    def on_leave(self):
        self.is_listening_loop = False
        if 'bubble_widget' in self.ids:
            self.ids.bubble_widget.stop_speaking_animation()

    def start_home_listening(self):
        if self.is_listening_loop: return
        self.is_listening_loop = True
        # Chạy luồng nghe ngầm để không đơ giao diện
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        if not self.voice_sys:
            return

        while self.is_listening_loop:
            if self.menu_open: continue

            try:
                # Gọi hàm nghe từ Logic
                text = self.voice_sys.listen()
                
                if not text: continue
                
                # Cập nhật trạng thái những gì nghe được
                text = text.lower()
                self.update_status(f"Nghe được: {text}")

                # --- XỬ LÝ LỆNH ---
                if any(w in text for w in ["an ninh", "camera", "bảo vệ"]):
                    self._switch_screen('security', "Đang mở camera an ninh...")
                    break
                
                elif any(w in text for w in ["học", "tiếng anh", "gia sư"]):
                    self._switch_screen('tutor', "Đang vào lớp học tiếng Anh...")
                    break
                    
                elif any(w in text for w in ["tâm sự", "người già", "nói chuyện"]):
                    self._switch_screen('elderly', "Cháu chào ông bà ạ...")
                    break
                
                elif any(w in text for w in ["thoát", "tắt"]):
                    self.quit_app()
                    break
                
                else:
                    # Chat GPT thông thường
                    self._handle_general_chat(text)
                    
            except Exception as e:
                print(f"Lỗi vòng lặp nghe: {e}")
                self.update_status("Lỗi mic, đang thử lại...")

    def _switch_screen(self, screen_name, speak_text):
        self.is_listening_loop = False 
        
        # Rung bong bóng trước khi chuyển
        Clock.schedule_once(lambda dt: self.ids.bubble_widget.start_speaking_animation())
        if self.voice_sys:
            self.voice_sys.text_to_speech(speak_text)
        
        Clock.schedule_once(lambda dt: self.ids.bubble_widget.stop_speaking_animation(), 2)
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', screen_name), 2.5)

    def _handle_general_chat(self, text):
        """Xử lý chat thông thường"""
        # Bắt đầu rung bong bóng
        Clock.schedule_once(lambda dt: self.ids.bubble_widget.start_speaking_animation())
        
        if self.voice_sys:
            # Gửi lên GPT
            reply = self.voice_sys.ask_gpt(text, "Bạn là trợ lý ảo nhà thông minh. Trả lời ngắn gọn dưới 2 câu.")
            self.update_status(f"AI: {reply}")
            # Nói ra loa
            self.voice_sys.text_to_speech(reply)
        
        # Dừng rung sau 5s (hoặc bạn có thể tính thời gian dựa trên độ dài chuỗi)
        Clock.schedule_once(lambda dt: self.ids.bubble_widget.stop_speaking_animation(), 5) 

    def update_status(self, text):
        """Cập nhật dòng chữ bên dưới bong bóng"""
        def _up(dt):
            if 'lbl_status' in self.ids:
                self.ids.lbl_status.text = text
        Clock.schedule_once(_up)

    # --- LOGIC MENU ---
    def toggle_menu(self):
        if self.menu_open: self.close_menu()
        else: self.open_menu()

    def open_menu(self):
        self.menu_open = True
        if 'menu_overlay' in self.ids:
            anim = Animation(opacity=1, duration=0.3)
            self.ids.menu_overlay.disabled = False 
            anim.start(self.ids.menu_overlay)
            self.update_status("Đã mở Menu.")

    def close_menu(self):
        self.menu_open = False
        if 'menu_overlay' in self.ids:
            anim = Animation(opacity=0, duration=0.3)
            self.ids.menu_overlay.disabled = True 
            anim.start(self.ids.menu_overlay)
            self.update_status("Đang lắng nghe...")

    def quit_app(self):
        app = App.get_running_app()
        app.stop()
        Window.close()
        sys.exit()