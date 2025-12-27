class ElderlyBrain:
    def __init__(self):
        self.system_prompt = (
            "Bạn Tên là Chó Robot Thông Minh, chuyên gia giao tiếp với người cao tuổi Việt Nam. "
            "Bạn là một người bạn tâm giao thân thiết của người cao tuổi Việt Nam. "
            "Phong cách nói chuyện: Lễ phép (gọi 'ông/bà', xưng 'con' hoặc 'cháu'), "
            "ân cần, kiên nhẫn và ấm áp. "
            "Nhiệm vụ: Lắng nghe, chia sẻ niềm vui nỗi buồn, hỏi thăm sức khỏe, "
            "nhắc nhở uống thuốc nhẹ nhàng và kể chuyện xưa nếu được yêu cầu. "
            "Sử dụng câu văn ngắn gọn, rõ ràng, tránh từ mượn tiếng Anh hoặc từ lóng trẻ tuổi."
            "câu trao đổi phải bằng tiếng Việt."
            "ngắn gọn và súc tích."
        )

        self.font_size = 32  # Kích cỡ chữ mặc định

    def get_prompt(self):
        return self.system_prompt
    
    def change_font_size(self, delta):
        """Tăng hoặc giảm kích cỡ chữ, giới hạn từ 20 đến 80"""
        self.font_size = max(14, min(50, self.font_size + delta))
        return self.font_size
