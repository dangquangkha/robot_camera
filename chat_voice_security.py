import os
import glob
import datetime
import threading
import time
import cv2  # Cần import cv2 để xử lý màu ảnh
import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button, Scrollbar, Canvas, Frame
from PIL import Image, ImageTk
import speech_recognition as sr
import pygame
from openai import OpenAI
from dotenv import load_dotenv

# === IMPORT MODULE ROBOT CỦA BẠN ===
import robot_security_final as robot  # Đảm bảo file robot tên đúng là robot_security_final.py

# ================= CẤU HÌNH =================
 # Điền API Key của bạn
THU_MUC_BAO_DONG = "security_alerts"

load_dotenv()
# 2. Lấy giá trị từ biến môi trường
api_key = os.getenv("OPENAI_API_KEY")
# Kiểm tra xem key có tồn tại không (tùy chọn nhưng nên làm)
if not api_key:
    raise ValueError("Không tìm thấy OPENAI_API_KEY trong file .env")

# 3. Khởi tạo client
client = OpenAI(api_key=api_key)
# ================= HÀM GIỌNG NÓI =================
def speak(text):
    print(f"Bot: {text}")
    try:
        filename = "response_security_integrated.mp3"
        with client.audio.speech.with_streaming_response.create(
            model="tts-1", voice="alloy", input=text
        ) as response:
            response.stream_to_file(filename)

        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
        if os.path.exists(filename): os.remove(filename)
    except Exception as e:
        print(f"❌ Lỗi TTS: {e}")

# ================= LOGIC DATA =================
def get_todays_stats():
    if not os.path.exists(THU_MUC_BAO_DONG): return 0, []
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    all_files = glob.glob(os.path.join(THU_MUC_BAO_DONG, "*.jpg"))
    todays_files = [f for f in all_files if today_str in os.path.basename(f)]
    todays_files.sort(key=os.path.getmtime, reverse=True)
    return len(todays_files), todays_files

# ================= GIAO DIỆN CHÍNH (TÍCH HỢP CAMERA) =================
class SecurityHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TRUNG TÂM AN NINH THÔNG MINH")
        self.root.geometry("1100x700") # Mở rộng giao diện để chứa Camera

        # --- KHUNG TRÁI: CAMERA ---
        self.frame_camera = Frame(root, width=800, height=600, bg="black")
        self.frame_camera.pack(side="left", fill="both", expand=True)
        
        self.lbl_video = Label(self.frame_camera, text="Đang khởi động Camera...", fg="white", bg="black")
        self.lbl_video.pack(fill="both", expand=True)

        # --- KHUNG PHẢI: CHAT & ĐIỀU KHIỂN ---
        self.frame_control = Frame(root, width=300, bg="#f0f0f0")
        self.frame_control.pack(side="right", fill="y")

        # Tiêu đề bên phải
        Label(self.frame_control, text="Trợ Lý Ảo", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=20)

        # Nút Chat
        self.btn_talk = Button(self.frame_control, text="🎙️ BẤM ĐỂ HỎI", command=self.start_listening_thread,
                               font=("Arial", 14, "bold"), bg="#4CAF50", fg="white", height=2)
        self.btn_talk.pack(pady=10, padx=20, fill="x")

        # Nút xem lại ảnh
        self.btn_show = Button(self.frame_control, text="📷 Xem lịch sử ảnh", command=self.show_images_gui,
                               font=("Arial", 12), bg="#008CBA", fg="white")
        self.btn_show.pack(pady=5, padx=20, fill="x")

        self.label_status = Label(self.frame_control, text="Sẵn sàng...", fg="gray", bg="#f0f0f0")
        self.label_status.pack(pady=10)

        self.txt_log = tk.Text(self.frame_control, height=20, width=35, font=("Arial", 10))
        self.txt_log.pack(pady=10, padx=10)

        # --- KHỞI ĐỘNG HỆ THỐNG ROBOT ---
        self.start_robot_thread()
        
        # --- BẮT ĐẦU CẬP NHẬT VIDEO LÊN GUI ---
        self.update_video_feed()
        
        # Xử lý khi tắt app
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, text):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def start_robot_thread(self):
        """Chạy logic camera của file robot trong luồng riêng"""
        self.log("Đang khởi động hệ thống an ninh...")
        # Gọi hàm start_security_system từ file robot
        t = threading.Thread(target=robot.start_security_system, daemon=True)
        t.start()

    def update_video_feed(self):
        """Hàm này chạy liên tục để lấy ảnh từ robot và hiện lên Tkinter"""
        # Truy cập biến shared_frame từ module robot
        frame = None
        with robot.lock:
            if robot.shared_frame is not None:
                frame = robot.shared_frame.copy()
        
        if frame is not None:
            # Resize để vừa khung giao diện
            img_h, img_w = frame.shape[:2]
            # Giới hạn kích thước hiển thị (ví dụ max width 750)
            target_w = 750
            ratio = target_w / img_w
            target_h = int(img_h * ratio)
            
            frame = cv2.resize(frame, (target_w, target_h))
            
            # Chuyển đổi màu từ BGR (OpenCV) sang RGB (Tkinter)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.lbl_video.imgtk = imgtk # Giữ tham chiếu để không bị xóa
            self.lbl_video.configure(image=imgtk, text="")
        
        # Lặp lại hàm này sau 15ms (tương đương ~60fps)
        self.root.after(15, self.update_video_feed)

    def on_closing(self):
        """Dừng robot khi tắt app"""
        robot.is_running = False # Ra lệnh dừng vòng lặp bên file robot
        self.root.destroy()

    # ================= LOGIC VOICE (GIỮ NGUYÊN) =================
    def start_listening_thread(self):
        threading.Thread(target=self.process_voice).start()

    def process_voice(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self.label_status.config(text="Đang nghe...", fg="red")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
                self.label_status.config(text="Đang xử lý...", fg="blue")
                user_text = r.recognize_google(audio, language="vi-VN")
                self.log(f"Bạn: {user_text}")
                self.handle_ai_logic(user_text)
            except Exception as e:
                self.label_status.config(text="Lỗi/Không nghe rõ")
            self.label_status.config(text="Sẵn sàng...", fg="black")

    def handle_ai_logic(self, user_text):
        count, files = get_todays_stats()
        system_prompt = f"""
        Bạn là Robot Bảo Vệ Thông Minh. 
        Trạng thái hiện tại: Đang giám sát camera.
        Dữ liệu hôm nay ({datetime.datetime.now().strftime("%d/%m/%Y")}): {count} người lạ bị phát hiện.
        
        Nhiệm vụ:
        1. Trả lời ngắn gọn.
        2. Nếu người dùng muốn xem lại ảnh/bằng chứng -> thêm [ACTION_SHOW_IMAGES].
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}]
            )
            reply = response.choices[0].message.content
            if "[ACTION_SHOW_IMAGES]" in reply:
                clean_reply = reply.replace("[ACTION_SHOW_IMAGES]", "")
                self.log(f"AI: {clean_reply}")
                self.root.after(0, self.show_images_gui)
                speak(clean_reply)
            else:
                self.log(f"AI: {reply}")
                speak(reply)
        except:
            speak("Lỗi kết nối AI.")

    def show_images_gui(self):
        count, files = get_todays_stats()
        
        # Tạo cửa sổ mới (Toplevel)
        top = Toplevel(self.root)
        top.title(f"Lịch sử xâm nhập ({count} trường hợp)")
        top.geometry("900x600")
        
        # 1. Tiêu đề hiển thị số lượng
        lbl_info = Label(top, text=f"HÔM NAY PHÁT HIỆN: {count} LẦN XÂM NHẬP", 
                         font=("Arial", 14, "bold"), fg="red", pady=10)
        lbl_info.pack()

        if count == 0:
            Label(top, text="An toàn, chưa có hình ảnh nào.", font=("Arial", 12)).pack(pady=20)
            speak("Hệ thống an toàn, chưa có hình ảnh cảnh báo nào.")
            return

        # 2. Tạo vùng cuộn (Scrollable Canvas)
        frame_container = Frame(top)
        frame_container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = Canvas(frame_container)
        scrollbar = Scrollbar(frame_container, orient="vertical", command=canvas.yview)
        
        # Frame chứa danh sách ảnh nằm trong Canvas
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 3. Load và hiển thị ảnh dạng lưới (Grid)
        row_idx = 0
        col_idx = 0
        max_col = 3  # Mỗi dòng 3 ảnh
        
        # List giữ tham chiếu ảnh để không bị garbage collection xóa mất
        self.photo_refs = [] 

# ... (Phần bên trên giữ nguyên) ...

        for file_path in files:
            try:
                file_name = os.path.basename(file_path).replace("alert_", "").replace(".jpg", "")
                
                # Tạo khung
                frame_item = Frame(scrollable_frame, bd=2, relief="groove", padx=5, pady=5)
                frame_item.grid(row=row_idx, column=col_idx, padx=10, pady=10)
                
                # Load ảnh thumbnail (ảnh nhỏ)
                img_pil = Image.open(file_path)
                img_pil = img_pil.resize((250, 180)) 
                img_tk = ImageTk.PhotoImage(img_pil)
                self.photo_refs.append(img_tk) 
                
                # --- ĐOẠN QUAN TRỌNG ĐÃ ĐƯỢC CẬP NHẬT ---
                # Tạo Label chứa ảnh, thêm cursor="hand2" để hiện bàn tay
                lbl_img = Label(frame_item, image=img_tk, cursor="hand2")
                lbl_img.pack()
                
                # Gán sự kiện Click chuột trái (<Button-1>)
                # Lưu ý: dùng lambda e, p=file_path để truyền đúng đường dẫn của ảnh đó
                lbl_img.bind("<Button-1>", lambda e, p=file_path: self.view_full_image(p))
                # ----------------------------------------

                # Hiển thị thời gian
                Label(frame_item, text=f"Thời gian:\n{file_name}", font=("Arial", 9), fg="blue").pack()
                
                col_idx += 1
                if col_idx >= max_col:
                    col_idx = 0
                    row_idx += 1
            except Exception as e:
                print(f"Lỗi load ảnh {file_path}: {e}")

        speak(f"Đã tìm thấy {count} hình ảnh xâm nhập ngày hôm nay.")

    def view_full_image(self, img_path):
        """Hàm mở cửa sổ mới để xem ảnh kích thước thật"""
        try:
            # Tạo cửa sổ popup
            top_full = Toplevel(self.root)
            top_full.title("Chi tiết hình ảnh xâm nhập")
            
            # Load ảnh gốc
            img_pil = Image.open(img_path)
            
            # (Tùy chọn) Resize nếu ảnh quá to so với màn hình laptop
            # Ví dụ: Giới hạn chiều rộng tối đa 1000px
            if img_pil.width > 1000:
                ratio = 1000 / img_pil.width
                new_h = int(img_pil.height * ratio)
                img_pil = img_pil.resize((1000, new_h))
            
            img_tk = ImageTk.PhotoImage(img_pil)
            
            # Hiển thị ảnh
            lbl_full = Label(top_full, image=img_tk)
            lbl_full.image = img_tk # Quan trọng: Giữ tham chiếu để không mất ảnh
            lbl_full.pack(padx=10, pady=10)
            
            # Nút đóng
            Button(top_full, text="Đóng", command=top_full.destroy, 
                   bg="red", fg="white", font=("Arial", 12)).pack(pady=5)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở ảnh: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SecurityHubApp(root)
    root.mainloop()