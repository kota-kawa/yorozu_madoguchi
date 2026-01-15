from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv 
import os 
import logging
from database import init_db
import uuid
import redis_client
from reply.reply_main import reply_bp
from travel.travel_main import travel_bp
from fitness.fitness_main import fitness_bp

load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化
init_db()

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
app.register_blueprint(travel_bp)
app.register_blueprint(fitness_bp)

def reset_session_data(session_id):
    """Redisのセッションデータをリセットする"""
    redis_client.reset_session(session_id)

def error_response(message, status=400):
    """エラーレスポンスを返すヘルパー関数"""
    return jsonify({"error": message, "response": message}), status

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

@app.route('/api/user_type', methods=['POST'])
def set_user_type():
    try:
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
            response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
        return response
    except Exception as e:
        logger.error(f"User type endpoint failed: {e}")
        return jsonify({"error": "ユーザー種別の登録に失敗しました。"}), 500


if __name__ == '__main__':
    app.run(debug=True)
