import mysql.connector

# Cấu hình Database y hệt như trong file robot của bạn
DB_CONFIG = {
    'host': 'lmag6s0zwmcswp5w.cbetxkdyhwsb.us-east-1.rds.amazonaws.com',
    'user': 'iocpivuiapovtydo',
    'password': 'blqxnptzoye9snv2',
    'database': 'swb77e48ogfk0kvv',
    'port': 3306
}

def fix_database():
    print("⏳ Đang kết nối tới Database trên Cloud...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. Xóa bảng cũ (Bảng gây lỗi)
        print("🗑️  Đang xóa bảng 'family_members' cũ (sai cấu trúc)...")
        cursor.execute("DROP TABLE IF EXISTS family_members")
        
        # 2. Tạo lại bảng mới (Đúng cấu trúc chứa ảnh)
        print("🔨 Đang tạo lại bảng 'family_members' mới...")
        cursor.execute("""
            CREATE TABLE family_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                image_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ THÀNH CÔNG! Database đã được sửa chữa.")
        print("👉 Bây giờ bạn hãy dùng App Mobile để đăng ký lại khuôn mặt người nhà nhé.")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    fix_database()