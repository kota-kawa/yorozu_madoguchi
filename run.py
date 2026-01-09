from flask import Flask, render_template, request, jsonify, redirect, make_response
from flask_cors import CORS
import llama_core
import reservation
from dotenv import load_dotenv 
import os 
from pathlib import Path
import limit_manager
from reply.reply_main import reply_bp
import logging
from database import init_db, SessionLocal
from models import ReservationPlan
import uuid
import redis_client

load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化
init_db()

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


def reset_session_data(session_id):
    try:
        redis_client.reset_session(session_id)
    except Exception as e:
        logger.error(f"Failed to reset session data for {session_id}: {e}")


def load_reservation_data():
    reservation_data = []
    db = SessionLocal()
    try:
        plan = db.query(ReservationPlan).first()
        if plan:
            # 表示順序やラベルは既存CSVに合わせて定義
            fields = [
                ('目的地', plan.destinations),
                ('出発地', plan.departure),
                ('ホテル', plan.hotel),
                ('航空会社', plan.airlines),
                ('鉄道会社', plan.railway),
                ('タクシー会社', plan.taxi),
                ('滞在開始日', plan.start_date),
                ('滞在終了日', plan.end_date)
            ]
            for key, value in fields:
                if value: # 値が存在する場合のみ追加
                    reservation_data.append(f"{key}：{value}")
    except Exception as e:
        logger.error(f"Failed to load reservation data: {e}")
        return ["予約データの読み込みに失敗しました。"]
    finally:
        db.close()

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
    session_id = str(uuid.uuid4())
    # セッションデータを初期化
    reset_session_data(session_id)
    
    response = make_response(redirect(FRONTEND_REDIRECT))
    # CookieにセッションIDを設定 (有効期限やSameSite設定は環境に合わせて調整)
    # ローカル開発(HTTP)とクロスオリジンを考慮して設定
    response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
    return response


@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            # セッションIDがない場合は新規作成して返す（実質リセットと同じ）
            session_id = str(uuid.uuid4())
        
        reset_session_data(session_id)
        
        response = make_response(jsonify({"status": "reset"}))
        if not request.cookies.get('session_id'):
             response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
             
        return response
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

        # 結果をログ出力
        for item in reservation_data:
            logger.info(f"Reservation Data: {item}")
        return render_template('complete.html', reservation_data = reservation_data)
    except Exception as e:
        logger.error(f"Complete endpoint failed: {e}")
        return "サーバー内部エラーが発生しました。", 500


# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/travel_send_message', methods=['POST'])
def send_message():
    try:
        # セッションIDの取得
        session_id = request.cookies.get('session_id')
        if not session_id:
            # セッションIDがない場合の処理（エラーにするか、一時的なIDで処理するか）
            # ここではエラーメッセージを返しつつ、クッキーセットを促すのが理想だが
            # 簡易的にエラーとする
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        # 利用制限のチェック
        is_allowed, count = limit_manager.check_and_increment_limit()
        if not is_allowed:
            return error_response(
                f"本日の利用制限（{limit_manager.MAX_DAILY_LIMIT}回）に達しました。明日またご利用ください。",
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

        response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(session_id, prompt)
        return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)


@app.route('/travel_submit_plan', methods=['POST'])
def submit_plan():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
             return jsonify({'error': 'セッションが無効です。'}), 400
             
        result = reservation.complete_plan(session_id)
        return jsonify({'compile': result})
    except Exception as e:
        logger.error(f"Error in submit_plan: {e}", exc_info=True)
        return jsonify({'error': 'プランの保存に失敗しました。'}), 500

if __name__ == '__main__':
    app.run(debug=True)
