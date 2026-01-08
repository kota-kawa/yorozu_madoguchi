from flask import Flask, request, jsonify, session
from flask_cors import CORS
import llama_core
import reservation
from dotenv import load_dotenv
import os
import uuid
import limit_manager

load_dotenv()

app = Flask(__name__)
# Secret key is needed for session management
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

from reply.reply_main import reply_bp

# Blueprintの登録
app.register_blueprint(reply_bp)

# Initialize session
@app.route('/api/init', methods=['POST'])
def init_session():
    session_id = str(uuid.uuid4())
    # Create empty files for the new session
    # We will pass session_id to helper functions to use specific files
    return jsonify({"session_id": session_id, "message": "Session initialized"})

# 予約完了画面 data
@app.route('/api/complete', methods=['GET'])
def complete_data():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    reservation_data = []

    file_path = f'./reservation_plan_{session_id}.csv'
    if not os.path.exists(file_path):
         return jsonify({"reservation_data": []})

    with open(file_path, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        for line in lines:
            row = line.strip().split(',')
            if len(row) == 2 and row[0] and row[1]:
                key = row[0].strip()
                value = row[1].strip()
                if key and value:
                    reservation_data.append(f"{key}：{value}")

    return jsonify({"reservation_data": reservation_data})

# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/travel_send_message', methods=['POST'])
def send_message():
    data = request.json
    session_id = data.get('session_id')
    prompt = data.get('message')

    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    # 利用制限のチェック
    is_allowed, count = limit_manager.check_and_increment_limit()
    if not is_allowed:
        return jsonify({
            'response': f"申し訳ありませんが、本日の利用制限（{limit_manager.MAX_DAILY_LIMIT}回）に達しました。明日またご利用ください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    # 文字数制限のチェック
    if len(prompt) > 3000:
        return jsonify({
            'response': "入力された文字数が3000文字を超えています。短くして再度お試しください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    # Pass session_id to llama_core to use session specific files
    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt, session_id)
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@app.route('/travel_submit_plan', methods=['POST'])
def submit_plan():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
         return jsonify({"error": "Session ID required"}), 400

    compile_result = reservation.complete_plan(session_id)
    return jsonify({'compile': compile_result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
