from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
import llama_core
import reservation
from dotenv import load_dotenv 
import os 
from pathlib import Path
import limit_manager
from reply.reply_main import reply_bp
import logging

load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# 環境変数からオリジンを取得し、Flask-CORS用にリスト化
raw_origins = os.getenv("ALLOWED_ORIGINS", FRONTEND_ORIGIN).split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins if origin.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:5173"]

# リダイレクト先は許可されたオリジンの最初、またはデフォルト
FRONTEND_REDIRECT = ALLOWED_ORIGINS[0]

app = Flask(__name__)
# CORSの設定
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)


def reset_session_files():
    try:
        for filename in ("chat_history.txt", "decision.txt"):
            file_path = BASE_DIR / filename
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write("")
    except Exception as e:
        logger.error(f"Failed to reset session files: {e}")


def load_reservation_data():
    reservation_data = []
    file_path = BASE_DIR / "reservation_plan.csv"
    if not file_path.exists():
        return reservation_data

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
            for line in lines:
                row = line.strip().split(',')
                if len(row) == 2 and row[0] and row[1]:
                    key = row[0].strip()
                    value = row[1].strip()
                    if key and value:
                        reservation_data.append(f"{key}：{value}")
    except Exception as e:
        logger.error(f"Failed to load reservation data: {e}")
        return ["予約データの読み込みに失敗しました。"]

    return reservation_data


def error_response(message, status=400):
    return jsonify({
        'error': True,
        'response': message,
        'current_plan': "",
        'yes_no_phrase': "",
        'remaining_text': ""
    }), status


# Blueprintの登録
app.register_blueprint(reply_bp)

# ホームのチャット画面（React フロントエンドに切り替え）
@app.route('/')
def home():
    reset_session_files()
    return redirect(FRONTEND_REDIRECT)


@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        reset_session_files()
        return jsonify({"status": "reset"})
    except Exception as e:
        logger.error(f"Reset endpoint failed: {e}")
        return jsonify({"error": "Reset failed"}), 500


# 予約完了画面
@app.route('/complete')
def complete():
    try:
        reservation_data = load_reservation_data()
        accepts_json = request.accept_mimetypes.get('application/json', 0)
        accepts_html = request.accept_mimetypes.get('text/html', 0)
        if accepts_json >= accepts_html:
            return jsonify({"reservation_data": reservation_data})

        # 結果を表示
        for item in reservation_data:
            print(item)
        return render_template('complete.html', reservation_data = reservation_data)
    except Exception as e:
        logger.error(f"Complete endpoint failed: {e}")
        return "サーバー内部エラーが発生しました。", 500


# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/travel_send_message', methods=['POST'])
def send_message():
    try:
        # 利用制限のチェック
        # プロキシ経由の場合も考慮してIPアドレスを取得
        if request.headers.getlist("X-Forwarded-For"):
            user_ip = request.headers.getlist("X-Forwarded-For")[0]
        else:
            user_ip = request.remote_addr

        is_allowed, count = limit_manager.check_and_increment_limit(user_ip)
        if not is_allowed:
            return error_response(
                f"申し訳ありませんが、本日の利用制限（{limit_manager.MAX_DAILY_LIMIT}回）に達しました。明日またご利用ください。",
                status=429
            )

        data = request.get_json(silent=True)
        if data is None:
            return error_response("リクエストの形式が正しくありません（JSONを送信してください）。", status=400)

        prompt = data.get('message', '')

        if not prompt:
            return error_response("メッセージを入力してください。", status=400)

        # 文字数制限のチェック
        if len(prompt) > 3000:
            return error_response("入力された文字数が3000文字を超えています。短くして再度お試しください。", status=400)

        response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt)
        return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)


@app.route('/travel_submit_plan', methods=['POST'])
def submit_plan():
    try:
        result = reservation.complete_plan()
        return jsonify({'compile': result})
    except Exception as e:
        logger.error(f"Error in submit_plan: {e}", exc_info=True)
        return jsonify({'error': 'プランの保存に失敗しました。'}), 500

if __name__ == '__main__':
    app.run(debug=True)
