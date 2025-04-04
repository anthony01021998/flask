from flask import Flask, request
import os
import requests
from openai import OpenAI

app = Flask(__name__)

# Load API key từ biến môi trường
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# 👉 Prompt hướng dẫn AI về FitZone
def generate_reply(prompt):
    system_prompt = """
    Bạn là một trợ lý AI thân thiện, chuyên tư vấn về Private Gym FITZONE – nơi chuyên huấn luyện cá nhân 1:1 cho khách hàng cao cấp, tập trung vào hiệu quả, riêng tư và an toàn.

    Thông tin cơ bản về FITZONE:
    - ✅ Dịch vụ: Huấn luyện cá nhân (Personal Training), Meal plan cá nhân, kiểm tra InBody, và phục hồi chức năng.
    - 💪 Đối tượng: Doanh nhân bận rộn, dân văn phòng, người muốn giảm mỡ – tăng cơ.
    - 📍 Địa điểm: TP. HCM – hoạt động theo mô hình appointment only.
    - 💼 Gói tập phổ biến: Gói 24 buổi, 36 buổi, 48 buổi. Tập 2–3 buổi/tuần.
    - 🧠 Huấn luyện viên: Được đào tạo chuyên sâu về phục hồi, dinh dưỡng và kỹ thuật.

    Trả lời mọi câu hỏi ngắn gọn, rõ ràng và gợi ý hành động cụ thể nếu cần (ví dụ: 'bạn có thể để lại số điện thoại để được tư vấn chi tiết hơn').
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

# Gửi tin nhắn về Messenger
def send_message(sender_id, message):
    PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": sender_id},
        "message": {"text": message}
    }
    requests.post(url, headers=headers, json=data)

@app.route('/')
def home():
    return "Private Gym AI Chatbot is running"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == os.getenv("VERIFY_TOKEN"):
            return challenge, 200
        return "Verification token mismatch", 403

    if request.method == 'POST':
        data = request.get_json()
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    if "message" in messaging_event:
                        user_message = messaging_event["message"].get("text")
                        if user_message:
                            ai_reply = generate_reply(user_message)
                            send_message(sender_id, ai_reply)
        return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
