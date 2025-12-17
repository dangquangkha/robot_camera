import mysql.connector

# Cấu hình Database
DB_CONFIG = {
    'host': 'lmag6s0zwmcswp5w.cbetxkdyhwsb.us-east-1.rds.amazonaws.com',
    'user': 'iocpivuiapovtydo',
    'password': 'blqxnptzoye9snv2',
    'database': 'swb77e48ogfk0kvv',
    'port': 3306
}

def clear_zombie_data():
    print("⏳ Đang kết nối Database...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. Xóa lịch sử báo động (Vì ảnh báo động cũ đã mất)
        print("🗑️  Đang xóa lịch sử báo động cũ...")
        cursor.execute("TRUNCATE TABLE intrusion_logs")

        # 2. Xóa danh sách người nhà (Vì ảnh khuôn mặt đăng ký cũ cũng đã mất)
        # Lưu ý: Bạn sẽ cần đăng ký lại khuôn mặt trên App sau khi chạy lệnh này.
        print("🗑️  Đang xóa dữ liệu khuôn mặt cũ (để đăng ký lại)...")
        cursor.execute("TRUNCATE TABLE family_members")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ ĐÃ LÀM SẠCH DATABASE!")
        print("👉 Bây giờ App Mobile sẽ không còn báo lỗi 404 nữa.")
        print("👉 Hãy mở App và đăng ký lại khuôn mặt mới.")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    clear_zombie_data()