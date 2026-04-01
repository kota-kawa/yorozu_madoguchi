"""
アプリケーションのエントリーポイント（Flask API）。
Application entry point for the Flask API.
"""

from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
from dotenv import load_dotenv 
import os 
import logging
from typing import Tuple, Union
from backend.database import init_db
import uuid
from backend import redis_client
from backend import security
from backend.errors import (
    ForbiddenError,
    PayloadTooLargeError,
    ValidationError,
    classify_backend_exception,
    json_error_response,
)
from werkzeug.exceptions import RequestEntityTooLarge
from backend.routes.reply import reply_bp
from backend.routes.travel import travel_bp
from backend.routes.fitness import fitness_bp
from backend.routes.job import job_bp
from backend.routes.study import study_bp

# 環境変数の読み込み
# Load environment variables
load_dotenv()

# ロギング設定
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化
# Initialize database tables at application startup
init_db()

# 許可されたオリジンを取得（CORS設定用）
# Resolve allowed origins for CORS configuration
ALLOWED_ORIGINS = security.get_allowed_origins()

app = Flask(__name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]
# 最大リクエストサイズを制限
# Limit max request size (default 256KB) to reduce DoS risk
try:
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "262144"))
except ValueError:
    app.config["MAX_CONTENT_LENGTH"] = 262144
# CORSの設定
# Allow requests from specific origins and enable credentials
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)

# 各機能のBlueprintを登録
# Register feature-specific blueprints
app.register_blueprint(reply_bp)
app.register_blueprint(travel_bp)
app.register_blueprint(fitness_bp)
app.register_blueprint(job_bp)
app.register_blueprint(study_bp)

def reset_session_data(session_id: str) -> None:
    """
    Redisのセッションデータをリセットする
    Reset session data stored in Redis.
    
    指定されたセッションIDに関連するチャット履歴や一時データを削除・初期化します。
    Clears chat history and temporary data for the given session ID.
    """
    redis_client.reset_session(session_id)

def error_response(
    message: str,
    status: int = 400,
    *,
    error_type: str | None = None,
) -> Tuple[Response, int]:
    """
    エラーレスポンスを返すヘルパー関数
    Helper to return a consistent JSON error response.
    
    一貫した形式でJSONエラーメッセージを生成します。
    Generates JSON error messages in a uniform format.
    """
    return json_error_response(message, status=status, error_type=error_type)

@app.after_request
def apply_security_headers(response: Response) -> Response:
    """
    すべてのレスポンスにセキュリティヘッダーを付与する
    Attach security headers to every response.
    
    X-Content-Type-Options, X-Frame-Options などのヘッダーを設定し、
    ブラウザベースの攻撃（クリックジャッキングなど）を軽減します。
    Adds headers (e.g., X-Content-Type-Options, X-Frame-Options) to mitigate browser-based attacks.
    """
    return security.apply_security_headers(response)

@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error: RequestEntityTooLarge) -> Tuple[Response, int]:
    """
    リクエストサイズ超過エラーのハンドリング
    Handle request payloads that exceed the configured size limit.
    """
    typed_error = PayloadTooLargeError("リクエストサイズが大きすぎます。", cause=error)
    return error_response(
        typed_error.message,
        status=typed_error.status_code,
        error_type=typed_error.error_type,
    )

@app.route('/api/reset', methods=['POST'])
def reset() -> ResponseOrTuple:
    """
    セッションリセットエンドポイント
    Session reset endpoint.
    
    現在のセッションデータをクリアし、必要に応じて新しいセッションIDを発行します。
    Clears current session data and issues a new session ID if needed.
    """
    try:
        # CSRFトークンの検証
        # Validate CSRF token
        if not security.is_csrf_valid(request):
            raise ForbiddenError("不正なリクエストです。")

        session_id = request.cookies.get('session_id')
        if not session_id:
            # セッションIDがない場合は新規作成して返す（実質リセットと同じ）
            # If no session ID exists, create one (equivalent to reset)
            session_id = str(uuid.uuid4())
        
        # Redis上のデータをリセット
        # Reset data in Redis
        reset_session_data(session_id)
        
        response = make_response(jsonify({"status": "reset"}))
        # クッキーにセッションIDが設定されていない場合、新規設定
        # Set session cookie if missing
        if not request.cookies.get('session_id'):
             response.set_cookie('session_id', session_id, **security.cookie_settings(request))
             
        return response
    except Exception as error:
        backend_error = classify_backend_exception(
            error,
            default_message="セッションのリセットに失敗しました。",
        )
        logger.error(
            "Reset endpoint failed (%s): %s",
            backend_error.error_type,
            backend_error,
            exc_info=True,
        )
        return error_response(
            backend_error.message,
            status=backend_error.status_code,
            error_type=backend_error.error_type,
        )

@app.route('/api/user_type', methods=['POST'])
def set_user_type() -> ResponseOrTuple:
    """
    ユーザー種別設定エンドポイント
    User type configuration endpoint.
    
    ユーザーの種類（normal/premium）を設定し、Redisに保存します。
    Stores the user type (normal/premium) in Redis.
    """
    try:
        # CSRFトークンの検証
        # Validate CSRF token
        if not security.is_csrf_valid(request):
            raise ForbiddenError("不正なリクエストです。")

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("リクエスト形式が正しくありません。")

        raw_user_type = data.get('user_type', '')
        if not isinstance(raw_user_type, str):
            raise ValidationError("ユーザー種別が正しくありません。")
        user_type = raw_user_type.strip().lower()

        # 入力値のバリデーション
        # Validate input
        if user_type not in ['normal', 'premium']:
            raise ValidationError("ユーザー種別が正しくありません。")

        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            reset_session_data(session_id)

        # Redisにユーザー種別を保存
        # Persist user type in Redis
        redis_client.save_user_type(session_id, user_type)

        response = make_response(jsonify({"user_type": user_type}))
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, **security.cookie_settings(request))
        return response
    except Exception as error:
        backend_error = classify_backend_exception(
            error,
            default_message="ユーザー種別の登録に失敗しました。",
        )
        logger.error(
            "User type endpoint failed (%s): %s",
            backend_error.error_type,
            backend_error,
            exc_info=True,
        )
        return error_response(
            backend_error.message,
            status=backend_error.status_code,
            error_type=backend_error.error_type,
        )


if __name__ == '__main__':
    app.run(debug=True)
