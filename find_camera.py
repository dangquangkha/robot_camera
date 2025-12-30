import os
import re

def get_arp_table():
    print("--- Đang quét danh sách thiết bị trong mạng (ARP Table) ---")
    # Chạy lệnh arp -a của hệ thống
    with os.popen('arp -a') as f:
        data = f.read()

    # Tìm tất cả các đoạn có định dạng IP và MAC
    # Ví dụ: 192.168.1.176      a1-b2-c3-d4-e5-f6
    devices = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+([a-fA-F0-9:-]{17})', data)
    
    print(f"{'Địa chỉ IP':<20} | {'Địa chỉ MAC':<20}")
    print("-" * 45)
    
    camera_found = []
    for ip, mac in devices:
        # Lọc bỏ các địa chỉ broadcast hoặc multicast thông dụng
        if not ip.endswith('.255') and not ip.startswith('224'):
            print(f"{ip:<20} | {mac:<20}")
            camera_found.append((ip, mac))
    
    return camera_found

if __name__ == "__main__":
    found = get_arp_table()
    print(f"\nTìm thấy {len(found)} thiết bị đang hoạt động.")
    print("Mẹo: Hãy rút thử 1 camera ra rồi chạy lại để biết MAC nào biến mất!")