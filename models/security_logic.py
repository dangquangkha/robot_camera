import cv2
import os
import threading
import time
import numpy as np
import winsound
import requests
import shutil
import mysql.connector
from datetime import datetime
from ultralytics import YOLO
from deepface import DeepFace
import re
# === CẤU HÌNH TỪ FILE CŨ ===
BASE_URL = "https://khai-security-robot-f5870f032456.herokuapp.com"
GET_FAMILY_LIST_API = f"{BASE_URL}/get_family_list"
GET_FAMILY_IMG_API = f"{BASE_URL}/get_family_image"

DB_CONFIG = {
    'host': 'lmag6s0zwmcswp5w.cbetxkdyhwsb.us-east-1.rds.amazonaws.com',
    'user': 'iocpivuiapovtydo',
    'password': 'blqxnptzoye9snv2',
    'database': 'swb77e48ogfk0kvv',
    'port': 3306
}

THU_MUC_BAO_DONG = "security_alerts"
THU_MUC_DATA_LOCAL = "local_family_data"
MODEL_NAME = "Facenet512"
DETECTOR_BACKEND = "ssd"
NGUONG_NHAN_DIEN = 0.8
DANGER_ZONE = [100, 100, 600, 500]
DELAY_BAO_DONG = 10.0

class SecuritySystem:
    def __init__(self):
        self.is_running = False
        self.shared_frame = None
        self.lock = threading.Lock()
        self.verified_tracks = {}
        self.shared_faces = []
        self.local_db = {}
        self.last_alert_time = 0
        self.model_yolo = None
        
        # Tạo thư mục
        if not os.path.exists(THU_MUC_BAO_DONG): os.makedirs(THU_MUC_BAO_DONG)
        if not os.path.exists(THU_MUC_DATA_LOCAL): os.makedirs(THU_MUC_DATA_LOCAL)

        self.current_camera_index = 0
        self.camera_configs = {
            # Đổi dấu "-" thành ":" để chuẩn hóa
            "CAM_01": {"mac": "1c:4d:89:d8:c0:FB", "ip": "192.168.0.3", "user": "admin", "pass": "L2D1833A"}, 
            "CAM_02": {"mac": "1c:4d:89:d8:c5:be", "ip": "192.168.1.222", "user": "admin", "pass": "L2D1833A"}
        }
        self.camera_urls = [
        "rtsp://admin:L2D1833A@192.168.0.3:554/cam/realmonitor?channel=1&subtype=1",
        "rtsp://admin:L2D1833A@192.168.1.222:554/cam/realmonitor?channel=1&subtype=1" # Camera thứ 2
        ]
        self.cap = None

    def load_resources(self):
        """Hàm này chạy ngầm để load Model AI"""
        print("--- [MODEL] Đang tải tài nguyên AI... ---")
        try:
            # 1. Load DeepFace
            DeepFace.build_model(MODEL_NAME)
            print("--- [MODEL] DeepFace đã sẵn sàng.")

            # 2. Đồng bộ dữ liệu
            self.local_db = self.sync_data_from_server()

            # 3. Load YOLO Pose
            self.model_yolo = YOLO('yolov8n-pose.pt')
            print("--- [MODEL] YOLO Pose đã sẵn sàng.")

        except Exception as e:
            print(f"❌ [MODEL] Lỗi load resources: {e}")

    def sync_data_from_server(self):
        print("--- ⬇️ [DATA] Đang đồng bộ dữ liệu server... ---")
        local_database = {}
        server_filenames = []
        try:
            resp = requests.get(GET_FAMILY_LIST_API, timeout=10)
            if resp.status_code == 200:
                family_list = resp.json()
                for person in family_list:
                    name = person['name']
                    img_filename = person['image_path']
                    server_filenames.append(img_filename)
                    local_img_path = os.path.join(THU_MUC_DATA_LOCAL, img_filename)
                    
                    # Tải ảnh nếu chưa có
                    if not os.path.exists(local_img_path):
                        try:
                            img_resp = requests.get(f"{GET_FAMILY_IMG_API}/{img_filename}", stream=True, timeout=5)
                            if img_resp.status_code == 200:
                                with open(local_img_path, 'wb') as f:
                                    img_resp.raw.decode_content = True
                                    shutil.copyfileobj(img_resp.raw, f)
                        except: continue
                    
                    # Tạo Embedding
                    try:
                        embedding_objs = DeepFace.represent(img_path=local_img_path, model_name=MODEL_NAME, enforce_detection=False)
                        embedding = embedding_objs[0]["embedding"]
                        
                        # Xử lý trùng tên
                        final_name = name
                        count = 1
                        while final_name in local_database:
                            final_name = f"{name}_{count}"
                            count += 1
                        local_database[final_name] = embedding
                    except: pass
            print(f"✅ [DATA] Đã học {len(local_database)} khuôn mặt.")
            return local_database
        except Exception as e:
            print(f"❌ [DATA] Lỗi đồng bộ: {e}")
            return {}

    def start_camera_thread(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.face_recognition_loop, daemon=True).start()
            threading.Thread(target=self.camera_loop, daemon=True).start()

    def stop(self):
        self.is_running = False

    def face_recognition_loop(self):
        """Luồng xử lý nhận diện khuôn mặt (Chạy song song)"""
        while self.is_running:
            if self.shared_frame is None:
                time.sleep(0.1)
                continue
            
            with self.lock:
                process_frame = self.shared_frame.copy()

            try:
                face_objs = DeepFace.extract_faces(img_path=process_frame, detector_backend=DETECTOR_BACKEND, enforce_detection=False, align=True)
                temp_faces = []
                for face in face_objs:
                    if face['confidence'] > 0.5:
                        # So khớp với database
                        target_emb = DeepFace.represent(img_path=process_frame, model_name=MODEL_NAME, detector_backend=DETECTOR_BACKEND, enforce_detection=False, align=True)[0]["embedding"]
                        best_match = "Unknown"
                        min_dist = 100
                        
                        for name, db_emb in self.local_db.items():
                            dist = 1 - (np.dot(target_emb, db_emb) / (np.linalg.norm(target_emb) * np.linalg.norm(db_emb)))
                            if dist < min_dist:
                                min_dist = dist
                                best_match = name
                        
                        display_name = best_match.split('_')[0] if best_match != "Unknown" else "Unknown"
                        final_name = display_name if min_dist < NGUONG_NHAN_DIEN else "Unknown"
                        
                        temp_faces.append({
                            "name": final_name,
                            "box": [face['facial_area']['x'], face['facial_area']['y'], face['facial_area']['w'], face['facial_area']['h']]
                        })
                self.shared_faces = temp_faces
            except: pass
            time.sleep(0.1)

    def switch_camera(self):
        """Hàm này sẽ được gọi khi bấm nút trên giao diện"""
        self.current_camera_index = (self.current_camera_index + 1) % len(self.camera_urls)
        print(f"--- Đang chuyển sang Camera: {self.current_camera_index} ---")
        
        # Giải phóng camera hiện tại để loop nhận diện ra success = False và tự kết nối lại
        if self.cap is not None:
            self.cap.release()
    
    def update_ips_by_mac(self):
        """Quét mạng để tìm IP mới nhất dựa trên địa chỉ MAC đã biết"""
        print("--- 🔍 Đang quét mạng để cập nhật IP theo MAC... ---")

        # Chạy lệnh hệ thống để lấy bảng ARP
        with os.popen('arp -a') as f:
            arp_data = f.read().lower()

        updated = False
        new_urls = []

        # Duyệt qua từng camera trong cấu hình
        for cam_id, info in self.camera_configs.items():
            mac_target = info['mac'].replace(':', '-').lower()
            # Tìm IP tương ứng với MAC trong dữ liệu ARP
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+' + mac_target, arp_data)
            
            if match:
                new_ip = match.group(1)
                if new_ip != info['ip']:
                    print(f"✅ Phát hiện IP mới cho {cam_id}: {new_ip}")
                    info['ip'] = new_ip
                    updated = True
            
            # Xây dựng lại URL RTSP
            url = f"rtsp://{info['user']}:{info['pass']}@{info['ip']}:554/cam/realmonitor?channel=1&subtype=1"
            new_urls.append(url)

        if updated:
            self.camera_urls = new_urls
            print("--- 🔄 Đã cập nhật lại danh sách camera_urls ---")

    # Trong file security_logic.py, thay thế hàm update_camera_ip cũ:

    def update_camera_ip(self, full_ip_input):
        """
        Cập nhật toàn bộ địa chỉ IP mới cho các camera trong danh sách urls.
        """
        # 1. Kiểm tra định dạng IP cơ bản (phải có 3 dấu chấm)
        if not full_ip_input or full_ip_input.count('.') != 3:
            print(f"❌ Địa chỉ IP '{full_ip_input}' không hợp lệ. Vui lòng nhập đầy đủ (vd: 192.168.1.176)")
            return

        print(f"--- 🔄 Đang cập nhật sang IP mới: {full_ip_input} ---")
        
        new_urls = []
        # Lưu ý: Trong logic của bạn, self.system chính là self nếu hàm nằm trong SecuritySystem
        for url in self.camera_urls: 
            try:
                # Tách chuỗi: rtsp://user:pass@OLD_IP:554/path
                prefix, rest = url.split('@')
                ip_and_port, path = rest.split('/', 1)
                old_ip, port = ip_and_port.split(':')
                
                # Ghép lại với IP mới hoàn toàn
                new_url = f"{prefix}@{full_ip_input}:{port}/{path}"
                new_urls.append(new_url)
            except Exception as e:
                print(f"❌ Lỗi xử lý URL {url}: {e}")
                new_urls.append(url)

        # Cập nhật danh sách URL và cấu hình bộ nhớ
        self.camera_urls = new_urls
        
        # Kích hoạt chuyển nguồn để áp dụng ngay
        self.switch_camera()
        print(f"✅ Đã cập nhật xong IP: {full_ip_input}")

    def change_camera_source(self):
        """Ngắt camera hiện tại và chuyển sang nguồn mới"""
        # Thay vì self.system.switch_camera(), hãy dùng:
        self.switch_camera()

    def camera_loop(self):
        """Vòng lặp Camera chính với hỗ trợ đổi nguồn và đầy đủ tính năng vẽ"""
        print("--- [CAMERA] Hệ thống camera đang khởi động... ---")
        
        # Cấu hình FFMPEG để tối ưu RTSP
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000" 

        # Chờ load model YOLO xong mới bắt đầu
        while self.model_yolo is None and self.is_running:
            time.sleep(1)

        while self.is_running:
            # Lấy URL hiện tại theo index (Phải đảm bảo đã khai báo trong __init__)
            rtsp_url = self.camera_urls[self.current_camera_index]
            self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self.cap.isOpened():
                print(f"❌ Không thể mở: {rtsp_url}. Thử lại sau 2s...")
                time.sleep(2)
                continue
            
            print(f"✅ Đã kết nối với Camera {self.current_camera_index}")

            while self.is_running:
                success, img = self.cap.read()
                
                if not success: 
                    print("⚠️ Đang kết nối lại hoặc chuyển camera...")
                    break # Thoát vòng lặp con để vòng lặp cha khởi tạo lại cap

                # --- BẮT ĐẦU XỬ LÝ AI ---
                results = self.model_yolo.track(img, persist=True, verbose=False, classes=[0])
                
                if results and results[0].boxes:
                    keypoints_all = results[0].keypoints.data.cpu().numpy() if results[0].keypoints else []
                    
                    for i, box in enumerate(results[0].boxes):
                        track_id = int(box.id[0]) if box.id is not None else -1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        center = (int((x1+x2)/2), int((y1+y2)/2))

                        person_name = self.verified_tracks.get(track_id, "Dang xac minh...")
                        if track_id not in self.verified_tracks:
                            for face in self.shared_faces:
                                if self.check_overlap([x1, y1, x2, y2], face['box']):
                                    person_name = face['name']
                                    self.verified_tracks[track_id] = person_name
                                    break
                        
                        is_family = (person_name != "Unknown" and person_name != "Dang xac minh...")
                        kpts = keypoints_all[i] if len(keypoints_all) > i else None
                        action_text, action_color = self.analyze_pose_action(kpts, [x1, y1, x2, y2])

                        in_zone = self.check_danger_zone(center, DANGER_ZONE)
                        box_color = (0, 255, 0)
                        info_text = f"ID:{track_id} | {person_name}"

                        if in_zone:
                            if not is_family:
                                box_color = (0, 0, 255)
                                info_text = f"WARNING! {person_name}"
                                threading.Thread(target=winsound.Beep, args=(2000, 200)).start()
                                if time.time() - self.last_alert_time > DELAY_BAO_DONG:
                                    self.trigger_alert(img)
                            else:
                                box_color = (255, 255, 0)

                        # Vẽ khung và thông tin AI
                        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
                        cv2.putText(img, info_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
                        
                        if action_text != "Normal":
                            cv2.putText(img, action_text, (x1, y1-35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, action_color, 3)
                        
                        if kpts is not None:
                            self.draw_skeleton(img, kpts)

                # Vẽ vùng nguy hiểm (Đầy đủ cả khung và chữ)
                cv2.rectangle(img, (DANGER_ZONE[0], DANGER_ZONE[1]), (DANGER_ZONE[2], DANGER_ZONE[3]), (0, 165, 255), 2)
                cv2.putText(img, "DANGER ZONE", (DANGER_ZONE[0], DANGER_ZONE[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

                # Cập nhật frame để hiển thị lên Kivy
                with self.lock:
                    self.shared_frame = img.copy()
                
                time.sleep(0.01)

            # Giải phóng tài nguyên trước khi vòng lặp cha chạy lần tiếp theo
            self.cap.release()

    # --- CÁC HÀM BỔ TRỢ (HELPER) TỪ FILE CŨ ---
    def trigger_alert(self, img):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"alert_{timestamp}.jpg"
        full_path = os.path.join(THU_MUC_BAO_DONG, fname)
        cv2.imwrite(full_path, img)
        self.last_alert_time = time.time()
        threading.Thread(target=self.push_alert_to_cloud, args=(1, fname)).start()
        print(f"🚨 ĐÃ GHI NHẬN CẢNH BÁO: {fname}")

    def push_alert_to_cloud(self, count, fname):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            sql = "INSERT INTO intrusion_logs (count_people, image_path) VALUES (%s, %s)"
            cursor.execute(sql, (count, fname))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Lỗi Cloud: {e}")

    def check_overlap(self, box_body, box_face):
        fx, fy, fw, fh = box_face
        xA = max(box_body[0], fx)
        yA = max(box_body[1], fy)
        xB = min(box_body[2], fx + fw)
        yB = min(box_body[3], fy + fh)
        return (max(0, xB - xA) * max(0, yB - yA)) > 0

    def check_danger_zone(self, center, zone):
        cx, cy = center
        return zone[0] < cx < zone[2] and zone[1] < cy < zone[3]

    def analyze_pose_action(self, keypoints, box):
        # ... (Copy y nguyên logic từ file cũ) ...
        action = "Normal"
        color = (0, 255, 0)
        if keypoints is None or len(keypoints) == 0: return action, color
        
        l_shoulder = keypoints[5][:2]
        l_hip = keypoints[11][:2]
        
        x1, y1, x2, y2 = box
        w = x2 - x1
        h = y2 - y1
        
        # Ngã
        if w > h * 1.2: 
            return "FALL DETECTED!", (0, 0, 255)
        if l_shoulder[1] > 0 and l_hip[1] > 0 and abs(l_shoulder[1] - l_hip[1]) < h * 0.1:
             return "FALL DETECTED!", (0, 0, 255)

        # Giơ tay (Hands Up)
        l_wrist = keypoints[9][:2]
        r_wrist = keypoints[10][:2]
        r_shoulder = keypoints[6][:2]
        
        if (l_wrist[1] > 0 and l_wrist[1] < l_shoulder[1]) or (r_wrist[1] > 0 and r_wrist[1] < r_shoulder[1]):
             return "HANDS UP", (0, 165, 255)
             
        return action, color

    def draw_skeleton(self, img, keypoints):
        # ... (Copy y nguyên logic vẽ xương) ...
        connections = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
        for pt1, pt2 in connections:
            if keypoints[pt1][2] > 0.5 and keypoints[pt2][2] > 0.5:
                cv2.line(img, (int(keypoints[pt1][0]), int(keypoints[pt1][1])), (int(keypoints[pt2][0]), int(keypoints[pt2][1])), (255, 0, 255), 2)

    def get_frame(self):
        with self.lock:
            if self.shared_frame is not None:
                return self.shared_frame.copy()
        return None
    
    def get_alert_stats(self):
        today_str = datetime.now().strftime("%Y%m%d")
        all_files = [os.path.join(THU_MUC_BAO_DONG, f) for f in os.listdir(THU_MUC_BAO_DONG) if f.endswith(".jpg")]
        todays = [f for f in all_files if today_str in f]
        todays.sort(key=os.path.getmtime, reverse=True) # Mới nhất lên đầu
        return len(todays), todays
    
    # Trong file models/security_logic.py

    def upload_new_member(self, name, frame):
        """Lưu ảnh tạm và gửi lên server để đăng ký người nhà"""
        try:
            img_path = "temp_register.jpg"
            cv2.imwrite(img_path, frame)
            
            with open(img_path, "rb") as f:
                # Sử dụng UPLOAD_URL đã định nghĩa ở đầu file
                response = requests.post(f"{BASE_URL}/add_member", 
                                         data={"name": name}, 
                                         files={"image": f}, 
                                         timeout=15)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def fetch_server_logs(self):
        """Lấy danh sách log xâm nhập từ server Heroku"""
        try:
            response = requests.get(f"{BASE_URL}/get_logs", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []