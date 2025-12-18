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

    def camera_loop(self):
        """Vòng lặp Camera chính"""
        print("--- [CAMERA] Đang mở Camera Imou... ---")
        
        # --- CẤU HÌNH CAMERA ---
        imou_pass = "KHAi2692004" 
        
        # ==> HÃY THỬ ĐỔI IP NẾU .228 KHÔNG ĐƯỢC
        imou_ip = "192.168.1.221" # Nếu lỗi, hãy thử đổi thành "192.168.1.108"
        
        rtsp_url = f"rtsp://admin:{imou_pass}@{imou_ip}:554/cam/realmonitor?channel=1&subtype=1"

        # --- [THÊM MỚI] Ép OpenCV dùng TCP để kết nối ổn định hơn ---
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

        cap = cv2.VideoCapture(rtsp_url)
        
        # Kiểm tra ngay lập tức xem có mở được không
        if not cap.isOpened():
            print(f"❌ LỖI NGHIÊM TRỌNG: Không thể mở RTSP URL: {rtsp_url}")
            print("👉 Gợi ý: Kiểm tra lại IP (có thể là .108?) hoặc tắt 'Mã hóa hình ảnh' trên App.")
        else:
            print("✅ Đã kết nối thành công với Camera!")

        # ... (Phần code while loop bên dưới giữ nguyên)
        # ---------------------------------------------

        # Chờ load model xong nếu chưa xong
        while self.model_yolo is None and self.is_running:
            print("Đang chờ Model YOLO...")
            time.sleep(1)

        while self.is_running:
            success, img = cap.read()
            if not success: 
                print("❌ Mất kết nối Camera! Đang thử kết nối lại...")
                time.sleep(2)
                cap = cv2.VideoCapture(rtsp_url) # Thử kết nối lại
                continue
            
            # ... (Phần code xử lý bên dưới giữ nguyên) ...
            
            # --- YOLO TRACKING ---
            results = self.model_yolo.track(img, persist=True, verbose=False, classes=[0])
            
            if results and results[0].boxes:
                keypoints_all = results[0].keypoints.data.cpu().numpy() if results[0].keypoints else []
                
                for i, box in enumerate(results[0].boxes):
                    track_id = int(box.id[0]) if box.id is not None else -1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center = (int((x1+x2)/2), int((y1+y2)/2))
                    
                    # 1. Xác định danh tính
                    person_name = self.verified_tracks.get(track_id, "Dang xac minh...")
                    if track_id not in self.verified_tracks:
                        for face in self.shared_faces:
                            if self.check_overlap([x1, y1, x2, y2], face['box']):
                                person_name = face['name']
                                self.verified_tracks[track_id] = person_name
                                break
                    
                    is_family = (person_name != "Unknown" and person_name != "Dang xac minh...")

                    # 2. Phân tích hành vi (Pose)
                    kpts = keypoints_all[i] if len(keypoints_all) > i else None
                    action_text, action_color = self.analyze_pose_action(kpts, [x1, y1, x2, y2])

                    # 3. Logic Cảnh báo
                    in_zone = self.check_danger_zone(center, DANGER_ZONE)
                    box_color = (0, 255, 0) # Xanh
                    info_text = f"ID:{track_id} | {person_name}"

                    if in_zone:
                        if is_family:
                            box_color = (255, 255, 0) # Vàng
                        else:
                            box_color = (0, 0, 255) # Đỏ
                            info_text = f"WARNING! {person_name}"
                            
                            if action_text == "FALL DETECTED!" or person_name == "Unknown":
                                # Phát tiếng kêu (Chạy luồng riêng để ko lag)
                                threading.Thread(target=winsound.Beep, args=(2000, 200)).start()
                                
                                # Gửi cảnh báo (10s/lần)
                                if time.time() - self.last_alert_time > DELAY_BAO_DONG:
                                    self.trigger_alert(img)

                    # 4. Vẽ lên hình
                    cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
                    cv2.putText(img, info_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
                    if action_text != "Normal":
                        cv2.putText(img, action_text, (x1, y1-35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, action_color, 3)
                    
                    if kpts is not None:
                        self.draw_skeleton(img, kpts)

            # Vẽ vùng nguy hiểm
            cv2.rectangle(img, (DANGER_ZONE[0], DANGER_ZONE[1]), (DANGER_ZONE[2], DANGER_ZONE[3]), (0, 165, 255), 2)
            cv2.putText(img, "DANGER ZONE", (DANGER_ZONE[0], DANGER_ZONE[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            # Cập nhật frame cho View
            with self.lock:
                self.shared_frame = img.copy()
            
            time.sleep(0.01)

        cap.release()

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