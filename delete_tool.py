import requests

# Đổi thành URL Heroku của bạn
SERVER_URL = "https://khai-security-robot-f5870f032456.herokuapp.com" 

def xoa_nguoi(ten):
    url = f"{SERVER_URL}/delete_member"
    payload = {"name": ten}
    
    try:
        response = requests.post(url, json=payload)
        print(response.json())
    except Exception as e:
        print(f"Lỗi: {e}")

# Gọi hàm để xóa tên bị trùng
xoa_nguoi("khai")
