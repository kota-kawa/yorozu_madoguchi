from flask import Flask, render_template, request, jsonify
import llama_core
import reservation
from dotenv import load_dotenv 
import os 
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = Flask(__name__)


def reset_session_files():
    for filename in ("chat_history.txt", "decision.txt"):
        file_path = BASE_DIR / filename
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("")


def load_reservation_data():
    reservation_data = []
    file_path = BASE_DIR / "reservation_plan.csv"
    if not file_path.exists():
        return reservation_data

    with open(file_path, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        for line in lines:
            row = line.strip().split(',')
            if len(row) == 2 and row[0] and row[1]:
                key = row[0].strip()
                value = row[1].strip()
                if key and value:
                    reservation_data.append(f"{key}：{value}")
    return reservation_data


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_ORIGIN
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

from reply.reply_main import reply_bp

# Blueprintの登録
app.register_blueprint(reply_bp)

# ホームのチャット画面（React フロントエンドに切り替え）
@app.route('/')
def home():
    reset_session_files()
    return jsonify({
        "message": "フロントエンドはReactに移行しました。frontend/ ディレクトリで npm run dev を実行してください。",
        "frontend": FRONTEND_ORIGIN
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    reset_session_files()
    return jsonify({"status": "reset"})


# 予約完了画面
@app.route('/complete')
def complete():
    reservation_data = load_reservation_data()
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify({"reservation_data": reservation_data})

    # 結果を表示
    for item in reservation_data:
        print(item)
    return render_template('complete.html', reservation_data = reservation_data)

import limit_manager

# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/travel_send_message', methods=['POST'])
def send_message():
    # 利用制限のチェック
    is_allowed, count = limit_manager.check_and_increment_limit()
    if not is_allowed:
        return jsonify({
            'response': f"申し訳ありませんが、本日の利用制限（{limit_manager.MAX_DAILY_LIMIT}回）に達しました。明日またご利用ください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    prompt = (request.json or {}).get('message', '')

    if not prompt:
        return jsonify({
            'response': "メッセージを入力してください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        }), 400

    # 文字数制限のチェック
    if len(prompt) > 3000:
        return jsonify({
            'response': "入力された文字数が3000文字を超えています。短くして再度お試しください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt)
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@app.route('/travel_submit_plan', methods=['POST'])
def submit_plan():
    compile = reservation.complete_plan()
    return jsonify({'compile': compile})

if __name__ == '__main__':
    app.run(debug=True)
