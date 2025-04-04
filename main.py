from flask import Flask, request
import openai
import os
import requests

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
PAGE_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Session lưu trạng thái câu trả lời theo từng khách
user_sessions = {}

# ===== Trả lời AI dựa theo flow =====
def generate_reply(prompt):
    system_prompt = """
    Bạn là trợ lý AI của phòng gym FITZONE – nơi tập luyện 1:1 cho người bận rộn. 
    Mục tiêu là tư vấn thân thiện, ngắn gọn, chuyên nghiệp và đặt đúng câu hỏi để hiểu khách.

    Khi người dùng chưa trả lời đủ 4 câu hỏi sau, hãy lần lượt hỏi:
    1. Mục tiêu của bạn khi đến với gym là gì?
    2. Bạn từng tập với HLV cá nhân chưa?
    3. Bạn muốn tập khoảng mấy buổi/tuần?
    4. Bạn có muốn để lại số Zalo để bên mình tư vấn chi tiết?

    Sau khi có đủ, hãy nói: “Cảm ơn bạn! Mình sẽ gửi thông tin cho HLV liên hệ hỗ trợ.”
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']


# ===== GỬI TIN NHẮN VỀ MESSENGER =====
def send_message(sender_id, message):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": sender_id},
        "message": {"text": message}
    }
    requests.post(url, headers=headers, json=data)


# ===== TÍNH ĐIỂM TIỀM NĂNG DỰA TRÊN CÂU TRẢ LỜI =====
def score_lead(responses):
    score = 0
    if "giảm mỡ" in responses.get("q1", "").lower(): score += 20
    if "tập với hlv" in responses.get("q2", "").lower(): score += 20
    if "2" in responses.get("q3", "") or "3" in responses.get("q3", ""): score += 30
    if "zalo" in responses.get("q4", "").lower() or "sdt" in responses.get("q4", "").lower(): score += 30
    return score


# ===== FLASK ROUTE =====
@app.route("/")
def home():
    return "✅ AI Lead Bot FITZONE online!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()
        if data.get("object") == "page":
            for entry in data["entry"]:
                for msg_event in entry["messaging"]:
                    sender_id = msg_event["sender"]["id"]
                    if "message" in msg_event and "text" in msg_event["message"]:
                        msg = msg_event["message"]["text"]

                        # Khởi tạo session nếu chưa có
                        if sender_id not in user_sessions:
                            user_sessions[sender_id] = {"q1": "", "q2": "", "q3": "", "q4": ""}

                        session = user_sessions[sender_id]

                        # Gán câu trả lời theo thứ tự
                        for q in ["q1", "q2", "q3", "q4"]:
                            if session[q] == "":
                                session[q] = msg
                                break

                        # Nếu đã có đủ câu trả lời
                        if all(session.values()):
                            score = score_lead(session)
                            if score >= 70:
                                send_message(sender_id, "🎯 Bạn rất phù hợp với dịch vụ của FITZONE! Vui lòng để lại Zalo hoặc số điện thoại nhé 📲")
                                # TODO: Gửi email nội bộ nếu cần
                            else:
                                send_message(sender_id, "Cảm ơn bạn đã chia sẻ! Nếu cần tư vấn thêm, hãy để lại Zalo nhé.")

                            # Xóa session sau khi xử lý
                            user_sessions.pop(sender_id)

                        else:
                            # Nếu chưa đủ câu, hỏi tiếp bằng GPT
                            ai_reply = generate_reply(msg)
                            send_message(sender_id, ai_reply)

        return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
