from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv 
import os 
import logging
from database import init_db
import uuid
import redis_client
import security
from werkzeug.exceptions import RequestEntityTooLarge
from reply.reply_main import reply_bp
from travel.travel_main import travel_bp
from fitness.fitness_main import fitness_bp

load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化
init_db()

ALLOWED_ORIGINS = security.get_allowed_origins()

app = Flask(__name__)
# 最大リクエストサイズを制限
try:
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "262144"))
except ValueError:
    app.config["MAX_CONTENT_LENGTH"] = 262144
# CORSの設定
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)
app.register_blueprint(reply_bp)
app.register_blueprint(travel_bp)
app.register_blueprint(fitness_bp)

def reset_session_data(session_id):
    """Redisのセッションデータをリセットする"""
    redis_client.reset_session(session_id)

def error_response(message, status=400):
    """エラーレスポンスを返すヘルパー関数"""
    return jsonify({"error": message, "response": message}), status

@app.after_request
def apply_security_headers(response):
    return security.apply_security_headers(response)

@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error):
    return error_response("リクエストサイズが大きすぎます。", status=413)

@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            # セッションIDがない場合は新規作成して返す（実質リセットと同じ）
            session_id = str(uuid.uuid4())
        
        reset_session_data(session_id)
        
        response = make_response(jsonify({"status": "reset"}))
        if not request.cookies.get('session_id'):
             response.set_cookie('session_id', session_id, **security.cookie_settings(request))
             
        return response
    except Exception as e:
        logger.error(f"Reset endpoint failed: {e}")
        return jsonify({"error": "Reset failed"}), 500

@app.route('/api/user_type', methods=['POST'])
def set_user_type():
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        data = request.get_json(silent=True) or {}
        user_type = data.get('user_type', '').strip().lower()

        if user_type not in ['normal', 'premium']:
            return error_response("ユーザー種別が正しくありません。", status=400)

        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            reset_session_data(session_id)

        redis_client.save_user_type(session_id, user_type)

        response = make_response(jsonify({"user_type": user_type}))
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, **security.cookie_settings(request))
        return response
    except Exception as e:
        logger.error(f"User type endpoint failed: {e}")
        return jsonify({"error": "ユーザー種別の登録に失敗しました。"}), 500


if __name__ == '__main__':
    app.run(debug=True)
