from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
from dotenv import load_dotenv 
import os 
import logging
from typing import Tuple, Union
from database import init_db
import uuid
import redis_client
import security
from werkzeug.exceptions import RequestEntityTooLarge
from reply.reply_main import reply_bp
from travel.travel_main import travel_bp
from fitness.fitness_main import fitness_bp
from job.job_main import job_bp
from study.study_main import study_bp

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化
# アプリケーション起動時にデータベーステーブルを作成・確認します
init_db()

# 許可されたオリジンを取得（CORS設定用）
ALLOWED_ORIGINS = security.get_allowed_origins()

app = Flask(__name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]
# 最大リクエストサイズを制限
# デフォルトで256KBに制限し、巨大なペイロードによるDoS攻撃を防ぎます
try:
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "262144"))
except ValueError:
    app.config["MAX_CONTENT_LENGTH"] = 262144
# CORSの設定
# 特定のオリジンからのリクエストのみを許可し、クレデンシャル情報の送受信を有効にします
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)

# 各機能のBlueprintを登録
app.register_blueprint(reply_bp)
app.register_blueprint(travel_bp)
app.register_blueprint(fitness_bp)
app.register_blueprint(job_bp)
app.register_blueprint(study_bp)

def reset_session_data(session_id: str) -> None:
    """
    Redisのセッションデータをリセットする
    
    指定されたセッションIDに関連するチャット履歴や一時データを削除・初期化します。
    """
    redis_client.reset_session(session_id)

def error_response(message: str, status: int = 400) -> Tuple[Response, int]:
    """
    エラーレスポンスを返すヘルパー関数
    
    一貫した形式でJSONエラーメッセージを生成します。
    """
    return jsonify({"error": message, "response": message}), status

@app.after_request
def apply_security_headers(response: Response) -> Response:
    """
    すべてのレスポンスにセキュリティヘッダーを付与する
    
    X-Content-Type-Options, X-Frame-Options などのヘッダーを設定し、
    ブラウザベースの攻撃（クリックジャッキングなど）を軽減します。
    """
    return security.apply_security_headers(response)

@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error: RequestEntityTooLarge) -> Tuple[Response, int]:
    """
    リクエストサイズ超過エラーのハンドリング
    """
    return error_response("リクエストサイズが大きすぎます。", status=413)

@app.route('/api/reset', methods=['POST'])
def reset() -> ResponseOrTuple:
    """
    セッションリセットエンドポイント
    
    現在のセッションデータをクリアし、必要に応じて新しいセッションIDを発行します。
    """
    try:
        # CSRFトークンの検証
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            # セッションIDがない場合は新規作成して返す（実質リセットと同じ）
            session_id = str(uuid.uuid4())
        
        # Redis上のデータをリセット
        reset_session_data(session_id)
        
        response = make_response(jsonify({"status": "reset"}))
        # クッキーにセッションIDが設定されていない場合、新規設定
        if not request.cookies.get('session_id'):
             response.set_cookie('session_id', session_id, **security.cookie_settings(request))
             
        return response
    except Exception as e:
        logger.error(f"Reset endpoint failed: {e}")
        return jsonify({"error": "Reset failed"}), 500

@app.route('/api/user_type', methods=['POST'])
def set_user_type() -> ResponseOrTuple:
    """
    ユーザー種別設定エンドポイント
    
    ユーザーの種類（normal/premium）を設定し、Redisに保存します。
    """
    try:
        # CSRFトークンの検証
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        data = request.get_json(silent=True) or {}
        user_type = data.get('user_type', '').strip().lower()

        # 入力値のバリデーション
        if user_type not in ['normal', 'premium']:
            return error_response("ユーザー種別が正しくありません。", status=400)

        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            reset_session_data(session_id)

        # Redisにユーザー種別を保存
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
