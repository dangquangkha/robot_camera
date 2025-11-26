import cv2
import os
import threading
import time
import winsound
import numpy as np
from deepface import DeepFace

# --- CẤU HÌNH TỐI ƯU ---
THU_MUC_ANH = "family_images"
MODEL_NAME = "Facenet512" 

# THAY ĐỔI 1: Dùng 'ssd' để bắt mặt xa tốt hơn 'opencv' rất nhiều
# Nếu máy khỏe, hãy đổi thành "retinaface" (cần cài thêm: pip install retina-face)
DETECTOR_BACKEND = "ssd" 

# THAY ĐỔI 2: Nới lỏng ngưỡng (0.4 - 0.45 là ổn cho camera thường)
NGUONG_NHAN_DIEN = 0.42

# Biến toàn cục
global_frame = None
global_face_name = ""
global_face_loc = None
is_running = True
lock = threading.Lock()

def load_database():
    """Đọc ảnh và chuyển thành Vector số"""
    database = {}
    print("Dang nap du lieu khuon mat...")
    
    if not os.path.exists(THU_MUC_ANH):
        os.makedirs(THU_MUC_ANH)
        return {}

    for file_name in os.listdir(THU_MUC_ANH):
        if file_name.lower().endswith(('.jpg', '.png', '.jpeg')):
            path = os.path.join(THU_MUC_ANH, file_name)
            try:
                # align=True giúp xoay thẳng mặt, học chuẩn xác hơn
                embeddings = DeepFace.represent(img_path=path, 
                                              model_name=MODEL_NAME, 
                                              detector_backend=DETECTOR_BACKEND, 
                                              enforce_detection=False,
                                              align=True) 
                if embeddings:
                    name = os.path.splitext(file_name)[0]
                    database[name] = embeddings[0]["embedding"]
                    print(f"Da hoc: {name}")
            except Exception as e:
                print(f"Loi file {file_name}: {e}")
    
    print(f"--- Hoan tat! Da hoc {len(database)} nguoi ---")
    return database

def ai_worker(database):
    global global_frame, global_face_name, global_face_loc
    
    while is_running:
        if global_frame is not None:
            with lock:
                small_frame = global_frame.copy()
            
            try:
                # THAY ĐỔI 3: Bật align=True để nhận diện chính xác hơn
                face_objs = DeepFace.extract_faces(img_path=small_frame, 
                                                 detector_backend=DETECTOR_BACKEND, 
                                                 enforce_detection=False, 
                                                 align=True)
                
                detected_name = "KHONG CO NGUOI"
                current_loc = None

                # Lọc khuôn mặt có độ tin cậy > 0.5
                if len(face_objs) > 0 and face_objs[0]['confidence'] > 0.5:
                    face_area = face_objs[0]['facial_area']
                    current_loc = (face_area['x'], face_area['y'], face_area['w'], face_area['h'])
                    
                    # Tính vector (cũng phải bật align=True)
                    target_embedding = DeepFace.represent(img_path=small_frame, 
                                                        model_name=MODEL_NAME, 
                                                        detector_backend=DETECTOR_BACKEND, 
                                                        enforce_detection=False,
                                                        align=True)[0]["embedding"]
                    
                    min_dist = 100
                    best_match = "NGUOI LA"
                    
                    for name, db_embedding in database.items():
                        a = np.array(target_embedding)
                        b = np.array(db_embedding)
                        dist = 1 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
                        
                        if dist < min_dist:
                            min_dist = dist
                            best_match = name
                    
                    # So sánh với ngưỡng
                    if min_dist < NGUONG_NHAN_DIEN:
                        detected_name = best_match
                        # In ra khoảng cách để debug (xem nó giống bao nhiêu %)
                        print(f"Nhan dien: {best_match} - Do sai lech: {min_dist:.2f}")
                    else:
                        detected_name = "NGUOI LA"
                        print(f"Nguoi la - Do sai lech: {min_dist:.2f}")
                        threading.Thread(target=winsound.Beep, args=(1000, 200)).start()
                
                global_face_name = detected_name
                global_face_loc = current_loc

            except Exception as e:
                pass
            
            time.sleep(0.05) # Giảm thời gian nghỉ chút để phản hồi nhanh hơn
        else:
            time.sleep(0.1)

def main():
    global global_frame, is_running
    db = load_database()
    
    ai_thread = threading.Thread(target=ai_worker, args=(db,))
    ai_thread.start()

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    print("Camera dang chay... Nhan 'q' de thoat")

    while True:
        ret, frame = cap.read()
        if not ret: break

        with lock:
            global_frame = frame.copy()

        if global_face_loc:
            x, y, w, h = global_face_loc
            color = (0, 255, 0)
            label = global_face_name
            
            if global_face_name == "NGUOI LA":
                color = (0, 0, 255)
            elif global_face_name == "KHONG CO NGUOI":
                color = (255, 0, 0)

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        cv2.imshow("DeepFace Security Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            is_running = False
            break

    cap.release()
    cv2.destroyAllWindows()
    ai_thread.join()

if __name__ == "__main__":
    main()