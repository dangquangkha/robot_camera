import cv2
import os
import threading
import time
import numpy as np
import winsound
import json
import mysql.connector
from datetime import datetime 
from ultralytics import YOLO
from deepface import DeepFace

# --- 1. CẤU HÌNH KẾT NỐI DATABASE (Phải giống hệt bên Server) ---
# Đây là "chìa khóa" để Robot nói chuyện với Server và App
DB_CONFIG = {
    'host': 'lmag6s0zwmcswp5w.cbetxkdyhwsb.us-east-1.rds.amazonaws.com',
    'user': 'iocpivuiapovtydo',
    'password': 'blqxnptzoye9snv2',
    'database': 'swb77e48ogfk0kvv',
    'port': 3306
}

# --- 2. CẤU HÌNH HỆ THỐNG ROBOT ---
THU_MUC_BAO_DONG = "security_alerts" # Thư mục lưu ảnh bằng chứng trên Mini PC
MODEL_NAME = "Facenet512"
DETECTOR_BACKEND = "ssd" 
NGUONG_NHAN_DIEN = 0.45 
DANGER_ZONE = [100, 100, 600, 500] # Vùng nguy hiểm (x1, y1, x2, y2)
DELAY_BAO_DONG = 10.0 # Cứ 10 giây mới báo động 1 lần để tránh spam

# Biến toàn cục để chia sẻ dữ liệu giữa các luồng
shared_frame = None 
shared_faces = [] 
lock = threading.Lock()
is_running = True
verified_tracks = {} 

# =========================================================================
# PHẦN 1: TẢI DỮ LIỆU TỪ CLOUD (Để nhận diện người nhà)
# =========================================================================
def load_faces_from_cloud():
    print("--- ☁️ ĐANG KẾT NỐI SERVER ĐỂ TẢI DỮ LIỆU KHUÔN MẶT... ---")
    database = {}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Lấy tên và vector khuôn mặt từ bảng 'family_members'
        cursor.execute("SELECT name, embedding FROM family_members")
        rows = cursor.fetchall()
        
        for name, embedding_json in rows:
            if embedding_json:
                # Chuyển chuỗi JSON thành List số thực để tính toán
                database[name] = json.loads(embedding_json)
                print(f"   + Đã nạp: {name}")
                
        conn.close()
        print(f"--- ✅ ĐÃ HỌC XONG {len(database)} NGƯỜI TỪ CLOUD ---")
    except Exception as e:
        print(f"❌ LỖI TẢI DATABASE: {e}")
        print("⚠️ Robot đang chạy chế độ OFFLINE (Chỉ nhận diện được người đã lưu cache cũ nếu có)")
    return database

<<<<<<< Updated upstream
=======
# =========================================================================
# PHẦN 2: ĐẨY BÁO ĐỘNG LÊN CLOUD (Để App Mobile nhận được)
# =========================================================================
def push_alert_to_cloud(count_people, image_filename):
    """
    Khi thấy người lạ, hàm này sẽ chạy ngầm để ghi vào Database.
    App Mobile sẽ đọc bảng 'intrusion_logs' và hiện cảnh báo đỏ.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Ghi vào bảng nhật ký
        sql = "INSERT INTO intrusion_logs (count_people, image_path) VALUES (%s, %s)"
        cursor.execute(sql, (count_people, image_filename))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"☁️ 🚨 ĐÃ GỬI CẢNH BÁO LÊN CLOUD: Có {count_people} người lạ!")
    except Exception as e:
        print(f"❌ Lỗi gửi báo động: {e}")

# =========================================================================
# PHẦN 3: CÁC HÀM XỬ LÝ AI & LOGIC
# =========================================================================

>>>>>>> Stashed changes
def check_overlap(box_body, box_face):
    """Kiểm tra xem khuôn mặt nhận diện được có thuộc về người đang đi không"""
    fx, fy, fw, fh = box_face
    xA = max(box_body[0], fx)
    yA = max(box_body[1], fy)
    xB = min(box_body[2], fx + fw)
    yB = min(box_body[3], fy + fh)
    return (max(0, xB - xA) * max(0, yB - yA)) > 0

def check_danger_zone(center, zone):
    """Kiểm tra người có đứng trong vùng nguy hiểm không"""
    cx, cy = center
    return zone[0] < cx < zone[2] and zone[1] < cy < zone[3]

def face_recognition_thread(database):
    """Luồng chạy ngầm chuyên để nhận diện khuôn mặt (DeepFace)"""
    global shared_frame, shared_faces, is_running
    print("--- 🧠 AI Thread (Face ID) đang chạy... ---")
    while is_running:
        if shared_frame is None: 
            time.sleep(0.1)
            continue
        
        # Lấy 1 khung hình ra để xử lý
        with lock: processing_frame = shared_frame.copy()
        
        try:
            # Tìm tất cả khuôn mặt trong hình
            face_objs = DeepFace.extract_faces(img_path=processing_frame, detector_backend=DETECTOR_BACKEND, enforce_detection=False, align=True)
            temp_faces = []
            
            for face in face_objs:
                if face['confidence'] > 0.5:
                    # Tính vector đặc trưng của mặt vừa tìm thấy
                    target_emb = DeepFace.represent(img_path=processing_frame, model_name=MODEL_NAME, detector_backend=DETECTOR_BACKEND, enforce_detection=False, align=True)[0]["embedding"]
                    
                    best_match = "Unknown"
                    min_dist = 100
                    
                    # So sánh với database người nhà
                    for name, db_emb in database.items():
                        # Tính khoảng cách Cosine (Càng nhỏ càng giống)
                        dist = 1 - (np.dot(target_emb, db_emb) / (np.linalg.norm(target_emb) * np.linalg.norm(db_emb)))
                        if dist < min_dist: 
                            min_dist = dist
                            best_match = name
                    
                    # Nếu giống > mức ngưỡng thì là người nhà, không thì là Unknown
                    final_name = best_match if min_dist < NGUONG_NHAN_DIEN else "Unknown"
                    
                    temp_faces.append({
                        "name": final_name, 
                        "box": [face['facial_area']['x'], face['facial_area']['y'], face['facial_area']['w'], face['facial_area']['h']]
                    })
            
            # Cập nhật kết quả cho luồng chính vẽ lên màn hình
            shared_faces = temp_faces
            
        except: 
            pass # Không thấy mặt thì bỏ qua
        
        time.sleep(0.1) # Nghỉ một chút để giảm tải CPU

def main():
    global shared_frame, is_running, verified_tracks
    
    # BƯỚC 1: Tải dữ liệu từ Cloud trước khi mở Camera
    db = load_faces_from_cloud()
    
    # BƯỚC 2: Khởi động luồng nhận diện khuôn mặt
    threading.Thread(target=face_recognition_thread, args=(db,), daemon=True).start()
    
    # Tạo thư mục lưu ảnh báo động nếu chưa có
    if not os.path.exists(THU_MUC_BAO_DONG): os.makedirs(THU_MUC_BAO_DONG)
    
    # Khởi tạo mô hình YOLO để theo dõi người (Body Tracking)
    model = YOLO('yolov8n.pt')
    cap = cv2.VideoCapture(0)
    
    # Đặt độ phân giải camera (tùy chọn)
    cap.set(3, 1280)
    cap.set(4, 720)
    
    last_alert_time = 0 

    print("--- 📷 CAMERA AN NINH ĐANG HOẠT ĐỘNG ---")
    print("--- Nhấn 'q' để thoát ---")

    while True:
        success, img = cap.read()
        if not success: break
        
        # Chia sẻ khung hình cho luồng nhận diện
        with lock: shared_frame = img.copy()
        
        # Dùng YOLO để phát hiện người (class 0 = person)
        results = model.track(img, persist=True, verbose=False, classes=[0])
        current_frame_ids = []

        if results and results[0].boxes:
            for box in results[0].boxes:
                # Lấy ID theo dõi của người này
                track_id = int(box.id[0]) if box.id is not None else -1
                current_frame_ids.append(track_id)
                
                # Lấy tọa độ
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center = (int((x1+x2)/2), int((y1+y2)/2))
                
                # Logic xác định tên:
                # 1. Kiểm tra xem ID này đã được nhận diện chưa
                person_name = verified_tracks.get(track_id, "Dang xac minh...")
                is_family = (person_name != "Unknown" and person_name != "Dang xac minh...")
                
                # 2. Nếu chưa biết là ai, thử khớp với kết quả từ luồng DeepFace
                if track_id not in verified_tracks:
                    for face in shared_faces:
                        if check_overlap([x1, y1, x2, y2], face['box']):
                            person_name = face['name']
                            verified_tracks[track_id] = person_name # Gán tên cho ID này
                            is_family = (person_name != "Unknown")
                            break

                # Logic vẽ và cảnh báo
                in_zone = check_danger_zone(center, DANGER_ZONE)
                color = (0, 255, 0) # Màu xanh (An toàn)
                
                if in_zone:
                    if is_family:
                        color = (255, 255, 0) # Màu vàng (Người nhà)
                        text = f"NGUOI NHA: {person_name}"
                    else:
                        color = (0, 0, 255) # Màu đỏ (Nguy hiểm)
                        text = "CANH BAO! XAM NHAP"
                        
                        # Chỉ báo động khi chắc chắn là Unknown
                        if person_name == "Unknown":
                            # Phát âm thanh tại chỗ
                            threading.Thread(target=winsound.Beep, args=(2000, 200)).start()
                            
                            # Gửi cảnh báo lên Cloud (có độ trễ để không spam)
                            if time.time() - last_alert_time > DELAY_BAO_DONG:
                                # 1. Chụp ảnh
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                fname = f"alert_{timestamp}.jpg"
                                full_path = os.path.join(THU_MUC_BAO_DONG, fname)
                                cv2.imwrite(full_path, img)
                                
                                # 2. Đẩy lên Cloud
                                threading.Thread(target=push_alert_to_cloud, args=(1, fname)).start()
                                
                                last_alert_time = time.time()
                else:
                    text = person_name

                # Vẽ khung chữ nhật và tên
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Vẽ vùng nguy hiểm
        cv2.rectangle(img, (DANGER_ZONE[0], DANGER_ZONE[1]), (DANGER_ZONE[2], DANGER_ZONE[3]), (0, 165, 255), 2)
        cv2.putText(img, "VUNG NGUY HIEM", (DANGER_ZONE[0], DANGER_ZONE[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        cv2.imshow("Robot Security Camera", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            is_running = False
            break

    cap.release()
    cv2.destroyAllWindows()
    print("--- Đã tắt Camera ---")

if __name__ == "__main__":
    main()