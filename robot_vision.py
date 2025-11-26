import cv2
from ultralytics import YOLO
import math

# --- CẤU HÌNH ---
# Tải mô hình YOLOv8 loại 'nano' (nhẹ nhất, chạy nhanh trên CPU)
# Lần đầu chạy sẽ tự động tải file yolov8n.pt về
model = YOLO('yolov8n.pt')

# Danh sách class (COCO dataset), chúng ta chỉ quan tâm class 'person'
classNames = model.names

# Khởi tạo Camera (0 là webcam mặc định, hoặc thay bằng link RTSP của Camera IP)
cap = cv2.VideoCapture(0)
cap.set(3, 1280) # Chiều rộng
cap.set(4, 720)  # Chiều cao

# Định nghĩa khu vực nguy hiểm/cảnh báo (Ví dụ: Một hình chữ nhật)
# [x1, y1, x2, y2]
danger_zone = [100, 100, 500, 500] 

def check_danger_zone(center_point, zone):
    cx, cy = center_point
    x1, y1, x2, y2 = zone
    # Kiểm tra xem điểm tâm có nằm trong hình chữ nhật không
    if x1 < cx < x2 and y1 < cy < y2:
        return True
    return False

print("Robot Vision đang khởi động...")

while True:
    success, img = cap.read()
    if not success:
        break

    # 1. NHẬN DIỆN QUA YOLO
    # stream=True giúp xử lý luồng video mượt hơn
    results = model(img, stream=True, verbose=False)

    # Biến đếm số người
    people_count = 0
    alert_triggered = False

    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Lấy tên class
            cls = int(box.cls[0])
            currentClass = classNames[cls]

            # CHỈ XỬ LÝ NẾU LÀ "PERSON" (NGƯỜI) và độ tin cậy > 50%
            conf = math.ceil((box.conf[0] * 100)) / 100
            if currentClass == "person" and conf > 0.5:
                people_count += 1

                # Lấy tọa độ khung bao (Bounding Box)
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Tính tâm của người (để xác định vị trí đứng)
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                # Kiểm tra xem có vào vùng nguy hiểm không
                is_in_danger = check_danger_zone((center_x, center_y), danger_zone)
                
                # --- VẼ LÊN HÌNH ---
                color = (0, 255, 0) # Màu xanh (An toàn)
                if is_in_danger:
                    color = (0, 0, 255) # Màu đỏ (Cảnh báo)
                    alert_triggered = True
                    cv2.putText(img, "CANH BAO XAM NHAP!", (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Vẽ khung bao quanh người
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
                # Vẽ điểm tâm
                cv2.circle(img, (center_x, center_y), 5, (255, 0, 255), cv2.FILLED)

    # 2. HIỂN THỊ GIAO DIỆN ROBOT
    # Vẽ vùng nguy hiểm lên màn hình để dễ quan sát
    dz_x1, dz_y1, dz_x2, dz_y2 = danger_zone
    cv2.rectangle(img, (dz_x1, dz_y1), (dz_x2, dz_y2), (0, 255, 255), 2)
    cv2.putText(img, "Khu Vuc Canh Bao", (dz_x1, dz_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Hiển thị thông tin thống kê
    cv2.rectangle(img, (0, 0), (300, 80), (0, 0, 0), -1) # Nền đen cho chữ
    cv2.putText(img, f'So luong nguoi: {people_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if alert_triggered:
        cv2.putText(img, "TRANG THAI: NGUY HIEM", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        cv2.putText(img, "TRANG THAI: AN TOAN", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Hiển thị cửa sổ
    cv2.imshow("Robot Gia Dinh - Giam Sat", img)

    # Nhấn phím 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()