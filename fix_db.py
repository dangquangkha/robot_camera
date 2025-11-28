import mysql.connector

# Thông tin Database của bạn (Tôi đã điền sẵn từ file bạn gửi)
DB_CONFIG = {
    'host': 'lmag6s0zwmcswp5w.cbetxkdyhwsb.us-east-1.rds.amazonaws.com',
    'user': 'iocpivuiapovtydo',
    'password': 'blqxnptzoye9snv2',
    'database': 'swb77e48ogfk0kvv',
    'port': 3306
}

def fix_database():
    print("⏳ Đang kết nối JawsDB để sửa lỗi...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Cách 1: Xóa bảng cũ đi tạo lại (Nhanh nhất, nhưng mất dữ liệu lịch sử cũ)
        print("1. Đang xóa bảng cũ 'intrusion_logs'...")
        cursor.execute("DROP TABLE IF EXISTS intrusion_logs")
        
        print("2. Đang tạo lại bảng mới với cấu trúc đúng...")
        # Tạo lại bảng với đầy đủ cột image_path
        cursor.execute("""
            CREATE TABLE intrusion_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                count_people INT,
                image_path VARCHAR(255)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ THÀNH CÔNG! Database đã có cột 'image_path'.")
        print("👉 Bây giờ bạn có thể chạy lại robot_security_final.py")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    fix_database()