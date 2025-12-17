from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.core.window import Window
import sys

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        """Khi vào màn hình chính"""
        # Bạn có thể thêm logic kiểm tra kết nối mạng hoặc load thông báo ở đây
        pass

    def navigate_to(self, screen_name):
        """Hàm điều hướng chung"""
        self.manager.current = screen_name
        self.manager.transition.direction = 'left'

    def quit_app(self):
        """Thoát ứng dụng an toàn"""
        app = App.get_running_app()
        app.stop()
        Window.close()
        sys.exit()