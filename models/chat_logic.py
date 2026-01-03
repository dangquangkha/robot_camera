import os
import time  # <--- Cần import time
import pygame
import speech_recognition as sr
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
import io  # <--- THƯ VIỆN QUAN TRỌNG ĐỂ DÙNG RAM
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
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
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

    def stop_speaking(self):
        """Hàm ngắt lời AI ngay lập tức (Dùng khi người dùng bấm nút hoặc ngắt lời)"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

    def text_to_speech(self, text):
        """Chuyển văn bản thành giọng nói dùng RAM (BytesIO)"""
        try:
            # 1. Ngắt âm thanh cũ nếu đang phát dở
            self.stop_speaking()

            # 2. Gọi API OpenAI (Không dùng stream_to_file nữa)
            # Chúng ta lấy raw content (dữ liệu nhị phân) trực tiếp
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3"
            )

            # 3. Tạo luồng dữ liệu trong RAM (Memory Buffer)
            # io.BytesIO hoạt động y hệt một file, nhưng nằm trên RAM
            byte_stream = io.BytesIO(response.content)

            # 4. Load trực tiếp từ RAM vào Pygame
            pygame.mixer.music.load(byte_stream)
            pygame.mixer.music.play()

            # 5. Chờ phát xong
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(30)

            # Lưu ý: Khi hàm này kết thúc, biến byte_stream sẽ tự được giải phóng khỏi RAM
            # Không cần lệnh xóa file hay os.remove

        except Exception as e:
            print(f"Lỗi TTS: {e}")