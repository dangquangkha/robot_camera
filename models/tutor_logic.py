class TutorBrain:
    def __init__(self):
        # Định nghĩa quy tắc cho từng cấp độ
        self.levels = {
            "A1": {
                "desc": "Beginner (Sơ cấp)",
                "prompt": "You are an English tutor for an A1 Beginner student. "
                          "Strictly use ONLY the 500 most common English words. "
                          "Use short, simple sentences (Subject + Verb + Object). "
                          "Speak slowly and clearly text style. "
                          "Correct basic grammar errors politely."
            },
            "A2": {
                "desc": "Elementary (Sơ trung cấp)",
                "prompt": "You are an English tutor for an A2 Elementary student. "
                          "Use basic vocabulary related to daily life, shopping, geography. "
                          "You can use past tense and future tense. "
                          "Keep sentences under 15 words."
            },
            "B1": {
                "desc": "Intermediate (Trung cấp)",
                "prompt": "You are an English tutor for a B1 Intermediate student. "
                          "Discuss topics like work, school, and leisure. "
                          "Use distinct sentence structures. "
                          "Encourage the user to express opinions."
            },
            "B2": {
                "desc": "Upper Intermediate (Trên trung cấp)",
                "prompt": "You are an English tutor for a B2 student. "
                          "Engage in fluent and spontaneous conversation. "
                          "Use idiomatic expressions and phrasal verbs appropriately. "
                          "Correct nuanced mistakes."
            },
            "C1": {
                "desc": "Advanced (Cao cấp)",
                "prompt": "You are an English tutor for a C1 Advanced student. "
                          "Use sophisticated vocabulary and complex grammar structures. "
                          "Discuss abstract ideas and professional topics deeply."
            },
            "C2": {
                "desc": "Mastery (Thành thạo)",
                "prompt": "Act as a highly educated native speaker talking to a C2 Mastery student. "
                          "Use literary, archaic, or highly technical vocabulary where fitting. "
                          "Analyze subtle meanings and cultural references."
            }
        }
        self.current_level = "A1" # Mặc định

    def set_level(self, level_code):
        if level_code in self.levels:
            self.current_level = level_code
            return f"Đã chuyển sang trình độ: {self.levels[level_code]['desc']}"
        return "Lỗi cấp độ"

    def get_prompt(self):
        """Lấy câu lệnh cấu hình cho AI dựa trên level hiện tại"""
        return self.levels[self.current_level]['prompt']