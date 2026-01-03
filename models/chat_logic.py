import os
import time  # <--- Cần import time
import pygame
import speech_recognition as sr
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
# 1. Load biến môi trường từ file .env
load_dotenv()

# 2. Lấy giá trị từ biến môi trường
api_key = os.getenv("OPENAI_API_KEY")
# Kiểm tra xem key có tồn tại không (tùy chọn nhưng nên làm)
if not api_key:
    raise ValueError("Không tìm thấy OPENAI_API_KEY trong file .env")

# 3. Khởi tạo client
client = OpenAI(api_key=api_key)

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
# --- [SỬA ĐỔI 1] Cấu hình Pygame Mixer chuẩn hơn ---
        # frequency=24000 khớp với chuẩn model tts-1 của OpenAI để tránh bị méo/mất tiếng
        # buffer=4096 giúp giảm độ trễ và tránh ngắt quãng
        try:
            pygame.mixer.init(frequency=24000, buffer=4096)
        except:
            pygame.mixer.init() # Fallback nếu lỗi

    def listen(self):
        """Lắng nghe giọng nói và chuyển thành văn bản"""
        with sr.Microphone() as source:
            print("AI: Đang nghe...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                # Nghe tối đa 5 giây
                audio = self.recognizer.listen(source, timeout=55, phrase_time_limit=150)
                text = self.recognizer.recognize_google(audio, language="vi-VN")
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except Exception as e:
                print(f"Lỗi mic: {e}")
                return None

    def ask_gpt(self, user_text, system_context="Bạn là trợ lý ảo."):
        """Gửi text lên OpenAI và nhận câu trả lời"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Hoặc gpt-3.5-turbo cho rẻ
                messages=[
                    {"role": "system", "content": system_context},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
                max_tokens=200  # token ≠ từ, nhưng giúp hạn chế lan man

            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Lỗi kết nối AI: {e}"

    def text_to_speech(self, text):
        """Chuyển văn bản thành giọng nói (OpenAI TTS)"""
        try:
            filename = "response_voice.mp3"
            # --- SỬA ĐOẠN NÀY ---
            # Luôn dừng và giải phóng file cũ trước khi làm bất cứ gì
            # 1. Dừng âm thanh cũ và giải phóng file
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
            # 2. Xóa file cũ để đảm bảo không bị cache
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except PermissionError:
                    print("Không thể xóa file cũ, đang dùng tên tạm...")
                    filename = f"response_{int(time.time())}.mp3"

            # 3. Gọi API OpenAI và lưu file
            with client.audio.speech.with_streaming_response.create(
                model="tts-1", 
                voice="alloy", 
                input=text,
                response_format="mp3"
            ) as response:
                response.stream_to_file(filename)
            
            time.sleep(0.2)  # Đợi file được ghi xong
            # Phát âm thanh
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # Giữ chương trình không chạy tiếp cho đến khi nói xong
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(30) # Tăng tick lên 30 để check mượt hơn
            
            # --- [SỬA ĐỔI 3] Đợi thêm 1 chút sau khi get_busy trả về False ---
            # Vì đôi khi Pygame báo xong nhưng loa vẫn còn dư âm
            time.sleep(0.2) 
                
        except Exception as e:
            print(f"Lỗi TTS: {e}")