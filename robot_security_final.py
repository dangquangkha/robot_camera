import cv2
import os
import threading
import time
import numpy as np
import winsound
from datetime import datetime 
from ultralytics import YOLO
from deepface import DeepFace

# --- CẤU HÌNH HỆ THỐNG ---
THU_MUC_ANH = "family_images"
THU_MUC_BAO_DONG = "security_alerts" # Thư mục lưu ảnh xâm nhập
MODEL_NAME = "Facenet512"
DETECTOR_BACKEND = "ssd" 
NGUONG_NHAN_DIEN = 0.45 
DANGER_ZONE = [100, 100, 600, 500] 
DELAY_CHUP_ANH = 3.0 # Thời gian chờ giữa các lần chụp (giây)

# Biến toàn cục
shared_frame = None 
shared_faces = [] 
lock = threading.Lock()
is_running = True
verified_tracks = {} 

def load_database():
    print("--- ĐANG NẠP DỮ LIỆU GIA ĐÌNH ---")
    database = {}
    if not os.path.exists(THU_MUC_ANH):
        os.makedirs(THU_MUC_ANH)
        return {}
    for file_name in os.listdir(THU_MUC_ANH):
        if file_name.lower().endswith(('.jpg', '.png', '.jpeg')):
            path = os.path.join(THU_MUC_ANH, file_name)
            try:
                embeddings = DeepFace.represent(img_path=path, model_name=MODEL_NAME, 
                                              detector_backend=DETECTOR_BACKEND, enforce_detection=False, align=True)
                if embeddings:
                    name = os.path.splitext(file_name)[0]
                    database[name] = embeddings[0]["embedding"]
                    print(f"Đã học: {name}")
            except: pass
    print(f"--- Đã học xong {len(database)} người ---")
    return database

def check_overlap(box_body, box_face):
    """Kiểm tra xem khuôn mặt nhận diện được có thuộc về người đang đi không"""
    fx, fy, fw, fh = box_face
    xA = max(box_body[0], fx)
    yA = max(box_body[1], fy)
    xB = min(box_body[2], fx + fw)
    yB = min(box_body[3], fy + fh)
    return (max(0, xB - xA) * max(0, yB - yA)) > 0

def check_danger_zone(center_point, zone):
    cx, cy = center_point
    x1, y1, x2, y2 = zone
    return x1 < cx < x2 and y1 < cy < y2

def face_recognition_thread(database):
    """Luồng chạy ngầm chuyên để nhận diện khuôn mặt (DeepFace)"""
    global shared_frame, shared_faces, is_running
    print("--- 🧠 AI Thread (Face ID) đang chạy... ---")
    while is_running:
        if shared_frame is None: 
            time.sleep(0.1)
            continue
        
        with lock:
            processing_frame = shared_frame.copy()

        try:
            face_objs = DeepFace.extract_faces(img_path=processing_frame, 
                                             detector_backend=DETECTOR_BACKEND, 
                                             enforce_detection=False, align=True)
            temp_faces = []
            
            for face in face_objs:
                if face['confidence'] > 0.5:
                    face_area = face['facial_area']
                    target_embedding = DeepFace.represent(img_path=processing_frame, 
                                                        model_name=MODEL_NAME, 
                                                        detector_backend=DETECTOR_BACKEND, 
                                                        enforce_detection=False, align=True)[0]["embedding"]
                    best_match = "Unknown"
                    min_dist = 100
                    for name, db_embedding in database.items():
                        a, b = np.array(target_embedding), np.array(db_embedding)
                        dist = 1 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
                        if dist < min_dist:
                            min_dist = dist
                            best_match = name
                    
                    final_name = best_match if min_dist < NGUONG_NHAN_DIEN else "Unknown"
                    temp_faces.append({
                        "name": final_name,
                        "box": [face_area['x'], face_area['y'], face_area['w'], face_area['h']]
                    })
            shared_faces = temp_faces
            
        except: 
            pass # Không thấy mặt thì bỏ qua
        
        time.sleep(0.1) # Nghỉ một chút để giảm tải CPU

def main():
    global shared_frame, is_running, verified_tracks

    db = load_database()
    threading.Thread(target=face_recognition_thread, args=(db,), daemon=True).start()
    
    # Tạo thư mục lưu ảnh báo động
    if not os.path.exists(THU_MUC_BAO_DONG):
        os.makedirs(THU_MUC_BAO_DONG)

    model = YOLO('yolov8n.pt')
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)
    
    last_capture_time = 0 # Biến đếm thời gian chụp ảnh

    print("HỆ THỐNG ĐANG CHẠY...")

    while True:
        success, img = cap.read()
        if not success: break

        with lock:
            shared_frame = img.copy()

        results = model.track(img, persist=True, verbose=False, classes=[0])
        current_frame_ids = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                if box.id is not None:
                    track_id = int(box.id[0])
                    current_frame_ids.append(track_id)
                else:
                    track_id = -1

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x, center_y = int((x1+x2)/2), int((y1+y2)/2)

                person_name = "Dang xac minh..."
                is_family = False

                if track_id in verified_tracks:
                    person_name = verified_tracks[track_id]
                    is_family = True
                else:
                    for face_data in shared_faces:
                        if check_overlap([x1, y1, x2, y2], face_data['box']):
                            detected_name = face_data['name']
                            if detected_name != "Unknown":
                                verified_tracks[track_id] = detected_name
                                person_name = detected_name
                                is_family = True
                                print(f"Da xac nhan: ID {track_id} la {person_name}")
                            break
                
                # --- XỬ LÝ CẢNH BÁO & CHỤP ẢNH ---
                in_zone = check_danger_zone((center_x, center_y), DANGER_ZONE)
                box_color = (0, 255, 0) 

                if in_zone:
                    if is_family:
                        box_color = (255, 255, 0) 
                        status_text = f"OK: {person_name}"
                    else:
                        box_color = (0, 0, 255) 
                        status_text = "CANH BAO: XAM NHAP"
                        threading.Thread(target=winsound.Beep, args=(1500, 50)).start()
                        
                        # Logic chụp ảnh
                        current_time = time.time()
                        if current_time - last_capture_time > DELAY_CHUP_ANH:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{THU_MUC_BAO_DONG}/alert_{timestamp}.jpg"
                            cv2.imwrite(filename, img)
                            print(f"!!! DA CHUP ANH XAM NHAP: {filename}")
                            cv2.putText(img, "DA CHUP ANH!", (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                            last_capture_time = current_time

                else:
                    status_text = person_name

                cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(img, status_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

        active_ids = list(verified_tracks.keys())
        for old_id in active_ids:
            if old_id not in current_frame_ids:
                del verified_tracks[old_id]

        so_nguoi = len(current_frame_ids)
        cv2.rectangle(img, (10, 10), (250, 60), (0, 0, 0), -1)
        cv2.putText(img, f'So nguoi: {so_nguoi}', (20, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.rectangle(img, (DANGER_ZONE[0], DANGER_ZONE[1]), (DANGER_ZONE[2], DANGER_ZONE[3]), (0, 165, 255), 2)
        
        cv2.imshow("Smart Security Camera", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            is_running = False
            break

    cap.release()
    cv2.destroyAllWindows()
    print("--- Đã tắt Camera ---")

if __name__ == "__main__":
    main()