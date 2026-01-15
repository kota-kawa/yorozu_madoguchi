from flask import Flask, request, jsonify, redirect, make_response
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
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://chat.project-kk.com")

# 環境変数からオリジンを取得し、Flask-CORS用にリスト化
# 本番ドメインとローカル開発環境の両方を許可リストに含める
raw_origins = os.getenv("ALLOWED_ORIGINS", FRONTEND_ORIGIN).split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins if origin.strip()]
if "https://chat.project-kk.com" not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append("https://chat.project-kk.com")
if "http://localhost:5173" not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append("http://localhost:5173")

app = Flask(__name__)
# CORSの設定
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)
app.register_blueprint(reply_bp)

def reset_session_data(session_id):
    """Redisのセッションデータをリセットする"""
    redis_client.reset_session(session_id)

def error_response(message, status=400):
    """エラーレスポンスを返すヘルパー関数"""
    return jsonify({"error": message}), status

def load_reservation_data():
    """データベースから最新の予約プランを読み込む"""
    db = SessionLocal()
    try:
        # 最新の予約プランを取得
        plan = db.query(ReservationPlan).order_by(ReservationPlan.id.desc()).first()
        if plan:
            return [{
                "id": plan.id,
                "destinations": plan.destinations,
                "departure": plan.departure,
                "hotel": plan.hotel,
                "airlines": plan.airlines,
                "railway": plan.railway,
                "taxi": plan.taxi,
                "start_date": plan.start_date,
                "end_date": plan.end_date
            }]
        return []
    finally:
        db.close()

def resolve_frontend_url(path=""):
    host = request.headers.get('Host', '')
    if 'chat.project-kk.com' in host:
        base_url = "https://chat.project-kk.com"
    elif 'localhost' in host or '127.0.0.1' in host:
        base_url = "http://localhost:5173"
    else:
        base_url = FRONTEND_ORIGIN

    if path and not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"

# ホームのチャット画面（React フロントエンドに切り替え）
@app.route('/')
def home():
    session_id = str(uuid.uuid4())
    # セッションデータを初期化
    reset_session_data(session_id)
    
    redirect_url = resolve_frontend_url()
    response = make_response(redirect(redirect_url))
    # CookieにセッションIDを設定
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
        return redirect(resolve_frontend_url('/complete'))
    except Exception as e:
        logger.error(f"Complete endpoint failed: {e}")
        return "サーバー内部エラーが発生しました。", 500


@app.route('/fitness')
def fitness_home():
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url('/fitness')
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
    return response


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


@app.route('/fitness_send_message', methods=['POST'])
def fitness_send_message():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

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

        if len(prompt) > 3000:
            return error_response("入力された文字数が3000文字を超えています。短くして再度お試しください。", status=400)

        response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(
            session_id,
            prompt,
            mode="fitness",
        )
        return jsonify({
            'response': response,
            'current_plan': current_plan,
            'yes_no_phrase': yes_no_phrase,
            'remaining_text': remaining_text
        })
    except Exception as e:
        logger.error(f"Error in fitness_send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)

if __name__ == '__main__':
    app.run(debug=True)
