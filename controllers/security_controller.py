import threading
import cv2
import os
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior

# THÊM CLASS NÀY ĐỂ ẢNH CÓ THỂ CLICK ĐƯỢC
class ClickableImage(ButtonBehavior, KivyImage):
    pass

class SecurityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.security_sys = None
        self.voice_sys = None
        self.update_event = None
        self.is_talking = False

    def on_enter(self):
        app = App.get_running_app()
        self.security_sys = app.security_sys
        self.voice_sys = app.voice_sys
        # Mặc định khi vào màn hình sẽ BẬT camera
        self.start_cam()
        # Bắt đầu stream camera
        if not self.security_sys.is_running:
            self.security_sys.start_camera_thread()
        
        self.update_event = Clock.schedule_interval(self.update_video_feed, 1.0 / 30.0)

    def on_leave(self):
        """Chạy khi THOÁT màn hình (Về Home)"""
        print("Security: Đang thoát... Dọn dẹp tài nguyên.")
        self.stop_cam()
        self.is_talking = False # Ngắt cờ đang nói chuyện
        
        # Ngắt loa nếu AI đang nói dở
        if self.voice_sys and hasattr(self.voice_sys, 'stop_speaking'):
            self.voice_sys.stop_speaking()

        if self.update_event:
            self.update_event.cancel()
    
    # --- [THÊM MỚI] LOGIC BẬT/TẮT CAMERA ---
    def toggle_camera(self):
        """Hàm này được gọi khi nhấn nút"""
        if self.security_sys.is_running:
            self.stop_cam()
        else:
            self.start_cam()
    
    def start_cam(self):
        """Bật camera và cập nhật giao diện nút"""
        if not self.security_sys.is_running:
            self.security_sys.start_camera_thread()
        
        # Tạo lại lịch cập nhật hình ảnh (30 FPS)
        if self.update_event is None:
            self.update_event = Clock.schedule_interval(self.update_video_feed, 1.0 / 30.0)

        # Cập nhật nút bấm thành màu ĐỎ (Trạng thái đang quay)
        if 'btn_cam_toggle' in self.ids:
            self.ids.btn_cam_toggle.text = "TẮT CAMERA"
            self.ids.btn_cam_toggle.background_color = (1, 0, 0, 1)
    
    def stop_cam(self):
        """Tắt camera và cập nhật giao diện nút"""
        self.security_sys.stop() # Gọi lệnh dừng ở Logic
        
        # Hủy lịch cập nhật hình ảnh
        if self.update_event:
            self.update_event.cancel()
            self.update_event = None
        
        # Xóa hình ảnh đang hiện trên màn hình (để đen thui)
        self.ids.img_camera.texture = None

        # Cập nhật nút bấm thành màu XANH (Sẵn sàng bật)
        if 'btn_cam_toggle' in self.ids:
            self.ids.btn_cam_toggle.text = "BẬT CAMERA"
            self.ids.btn_cam_toggle.background_color = (0, 1, 0, 1)
    # ---------------------------------------------

    def update_video_feed(self, dt):
        frame = self.security_sys.get_frame() # Lấy frame gốc từ logic
        if frame is not None:
            # --- TRẠNG THÁI MẶC ĐỊNH (0 ĐỘ) ---
            # Chuyển trực tiếp frame sang tobytes mà không qua flip hay rotate
            buffer = frame.tobytes() 
            
            # Lưu ý: size=(width, height) tương ứng với shape[1] và shape[0]
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
            texture.flip_vertical()
            self.ids.img_camera.texture = texture

    # --- VOICE LOGIC ---
    def start_intercom(self):
        if self.is_talking: return
        threading.Thread(target=self._process_voice_thread).start()

    def _process_voice_thread(self):
        self.is_talking = True
        self.update_chat_log("Đang nghe...", color="FFFF00")
        
        user_text = self.voice_sys.listen()
        if not user_text:
            self.update_chat_log("Không nghe rõ.", color="FF0000")
            self.is_talking = False
            return
        
        self.update_chat_log(f"Bạn: {user_text}")

        # Lấy thống kê an ninh để báo cáo
        count, _ = self.security_sys.get_alert_stats()
        
        system_prompt = f"""
        Bạn là Robot Bảo vệ. Hôm nay phát hiện {count} người lạ/cảnh báo.
        Nhiệm vụ:
        1. Trả lời ngắn gọn.
        2. Nếu người dùng muốn xem lại ảnh/bằng chứng -> thêm dòng chữ [ACTION_SHOW_IMAGES] vào cuối câu trả lời.
        """

        self.update_chat_log("AI đang suy nghĩ...", color="00FFFF")
        full_reply = self.voice_sys.ask_gpt(user_text, system_prompt)
        
        # Xử lý lệnh đặc biệt
        if "[ACTION_SHOW_IMAGES]" in full_reply:
            reply_text = full_reply.replace("[ACTION_SHOW_IMAGES]", "").strip()
            Clock.schedule_once(lambda dt: self.show_gallery()) # Mở gallery trên luồng chính
        else:
            reply_text = full_reply

        self.update_chat_log(f"Bot: {reply_text}", color="00FF00")
        self.voice_sys.text_to_speech(reply_text)
        self.is_talking = False

    def update_chat_log(self, text, color="FFFFFF"):
        def _update(dt):
            if 'lbl_chat_log' in self.ids:
                timestamp = datetime.now().strftime("%H:%M")
                self.ids.lbl_chat_log.text += f"[color={color}][b]{timestamp}[/b]: {text}[/color]\n"
        Clock.schedule_once(_update)

    # --- GALLERY POPUP (Xem ảnh xâm nhập) ---
    def show_gallery(self):
        count, files = self.security_sys.get_alert_stats()
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        if count == 0:
            content.add_widget(Label(text="Hôm nay chưa có cảnh báo nào!", font_size='20sp'))
        else:
            # Grid chứa ảnh
            scroll = ScrollView()
            grid = GridLayout(cols=3, spacing=10, size_hint_y=None)
            grid.bind(minimum_height=grid.setter('height'))
            
            for f_path in files:
                # Mỗi item gồm Ảnh + Tên
                item = BoxLayout(orientation='vertical', size_hint_y=None, height=200)
                
                # --- SỬA ĐỔI: Dùng ClickableImage ---
                img = ClickableImage(source=f_path, allow_stretch=True, keep_ratio=True)
                
                # Gắn sự kiện: Bấm vào thì gọi hàm view_full_image
                # Lưu ý: path=f_path là bắt buộc để Python nhớ đúng file trong vòng lặp
                img.bind(on_release=lambda x, path=f_path: self.view_full_image(path))
                
                item.add_widget(img)
                # ------------------------------------

                item.add_widget(Label(text=os.path.basename(f_path)[6:-4], size_hint_y=0.2, font_size='10sp')) 
                grid.add_widget(item)
                
            scroll.add_widget(grid)
            content.add_widget(scroll)

        # Nút đóng
        btn_close = Button(text="Đóng", size_hint_y=None, height=50, background_color=(1,0,0,1))
        content.add_widget(btn_close)

        popup = Popup(title=f"LỊCH SỬ CẢNH BÁO ({count})", content=content, size_hint=(0.9, 0.9))
        btn_close.bind(on_press=popup.dismiss)
        popup.open()
    
    # --- THÊM HÀM NÀY ĐỂ XEM FULL MÀN HÌNH ---
    def view_full_image(self, img_path):
        # Tạo nội dung cho Popup full màn hình
        content = BoxLayout(orientation='vertical', spacing=5, padding=5)
        
        # Ảnh lớn
        img = KivyImage(source=img_path, allow_stretch=True, keep_ratio=True)
        content.add_widget(img)
        
        # Nút đóng
        btn_close = Button(text="Đóng ảnh", size_hint_y=None, height=50, background_color=(1, 0, 0, 1))
        content.add_widget(btn_close)
        
        # Tạo Popup full màn hình (size_hint=(1, 1))
        # auto_dismiss=True: bấm ra ngoài sẽ tự đóng
        popup = Popup(title="CHI TIẾT ẢNH XÂM NHẬP", content=content, size_hint=(1, 1), auto_dismiss=True)
        
        btn_close.bind(on_press=popup.dismiss)
        popup.open()
    
    def register_member(self):
        """Hàm đăng ký tối ưu cho cảm ứng"""
        name = self.ids.txt_member_name.text.strip()
        
        # Nếu không gõ tên, tự đặt tên theo ID ngẫu nhiên hoặc thời gian
        if not name:
            from datetime import datetime
            name = f"User_{datetime.now().strftime('%H%M%S')}"
            self.update_chat_log(f"Hệ thống: Tự động đặt tên là {name}")

        frame = self.security_sys.get_frame() # Lấy frame từ logic
        if frame is not None:
            # Vô hiệu hóa nút để tránh bấm liên tục (Double tap)
            self.ids.btn_register.disabled = True
            
            def run_upload():
                res = self.security_sys.upload_new_member(name, frame)
                # Sau khi xong thì mở lại nút
                self.ids.btn_register.disabled = False
                if res.get("status") == "success":
                    self.update_chat_log(f"Thành công: Đã thêm {name}", "00FF00")
                else:
                    self.update_chat_log(f"Lỗi: {res.get('message')}", "FF0000")
            
            threading.Thread(target=run_upload, daemon=True).start()
    
    # --- SỬA LẠI HÀM NÀY ---
    def change_camera_source(self):
        # Thay self.logic bằng self.security_sys
        if self.security_sys:
            self.security_sys.switch_camera()
            
            # Cập nhật thông báo lên giao diện
            self.update_chat_log("Hệ thống: Đang chuyển nguồn Camera...", color="ffff00")