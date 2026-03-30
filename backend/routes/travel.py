"""
旅行計画機能のBlueprint実装。
Blueprint for the travel planning feature.
"""

from flask import Blueprint, request, jsonify, redirect, make_response, Response, stream_with_context
import logging
import uuid
from typing import Generator, List, Tuple, Union

from backend import llama_core
from backend import reservation
from backend.database import SessionLocal
from backend.models import ReservationPlan
from backend import limit_manager
from backend import redis_client
from backend import security
from backend.session_request_lock import (
    acquire_session_lock,
    release_session_lock,
    session_request_lock,
)
from backend.routes.common import error_response, reset_session_data, resolve_frontend_url

logger = logging.getLogger(__name__)

# Blueprintの定義: 旅行計画機能（travel）のルートを管理
# Blueprint definition for travel routes
travel_bp = Blueprint('travel', __name__)

ResponseOrTuple = Union[Response, Tuple[Response, int]]


def load_reservation_data(session_id: str) -> List[dict]:
    """
    セッション単位で最新の予約プランを読み込む
    Load the latest reservation plan for a session.
    
    データベースから該当セッションの最新の旅行計画を取得し、辞書のリストとして返します。
    Fetches the most recent plan and returns a list of dicts.
    """
    if not session_id:
        return []

    db = SessionLocal()
    try:
        plan = (
            db.query(ReservationPlan)
            .filter(ReservationPlan.session_id == session_id)
            .order_by(ReservationPlan.id.desc())
            .first()
        )
        if plan:
            return [{
                "id": plan.id,
                "session_id": plan.session_id,
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


@travel_bp.route('/')
def home() -> Response:
    """
    旅行計画機能の初期化エンドポイント
    Initialize travel feature and start a new session.
    
    （ルートパス '/' に割り当てられているため、デフォルトのエントリーポイントとなります）
    新規セッション発行後、フロントエンドへリダイレクトします。
    Issues a new session ID and redirects to the frontend.
    """
    session_id = str(uuid.uuid4())
    reset_session_data(session_id)

    redirect_url = resolve_frontend_url()
    response = make_response(redirect(redirect_url))
    response.set_cookie('session_id', session_id, **security.cookie_settings(request))
    return response


@travel_bp.route('/complete')
def complete() -> ResponseOrTuple:
    """
    完了画面表示用エンドポイント
    Completion screen endpoint.
    
    予約プランデータを取得して返します。
    Returns reservation plan data.
    """
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        reservation_data = load_reservation_data(session_id)
        accepts_json = request.accept_mimetypes.get('application/json', 0)
        accepts_html = request.accept_mimetypes.get('text/html', 0)
        # JSON要求の場合はデータを返す
        # Return JSON when requested
        if accepts_json >= accepts_html:
            return jsonify({"reservation_data": reservation_data})

        for item in reservation_data:
            logger.info(f"Reservation Data: {item}")
        return redirect(resolve_frontend_url('/complete'))
    except Exception as e:
        logger.error(f"Complete endpoint failed: {e}")
        return "サーバー内部エラーが発生しました。", 500


@travel_bp.route('/travel_send_message', methods=['POST'])
def send_message() -> ResponseOrTuple:
    """
    メッセージ送信処理エンドポイント
    Message handling endpoint for travel feature.
    
    ユーザーからのメッセージを受け取り、旅行コンシェルジュとしての応答を生成します。
    Receives user input and generates concierge responses.
    """
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            return error_response("セッションが無効です。ページをリロードしてください。", status=400)

        data = request.get_json(silent=True)
        if data is None:
            return error_response("リクエストの形式が正しくありません（JSONを送信してください）。", status=400)

        # 利用制限のチェック
        # Check rate limits
        is_allowed, count, limit, user_type, total_exceeded, error_code = (
            limit_manager.check_and_increment_limit(session_id, user_type=data.get("user_type"))
        )
        if error_code == "redis_unavailable":
            return error_response("利用状況を確認できません。しばらく待ってから再試行してください。", status=503)
        if not user_type:
            return error_response("ユーザー種別を選択してください。", status=400)
        if total_exceeded:
            return error_response("今日の上限に達しました。明日またご利用ください。", status=429)
        if not is_allowed:
            return error_response(
                f"本日の利用制限（{limit}回）に達しました。明日またご利用ください。",
                status=429
            )

        prompt = data.get('message', '')

        if not prompt:
            return error_response("メッセージを入力してください。", status=400)

        if len(prompt) > 3000:
            return error_response("入力された文字数が3000文字を超えています。短くして再度お試しください。", status=400)

        stored_language = redis_client.get_user_language(session_id)
        language = llama_core.resolve_user_language(
            prompt,
            fallback=stored_language,
            accept_language=request.headers.get("Accept-Language"),
        )
        redis_client.save_user_language(session_id, language)

        wants_stream = bool(data.get("stream")) or (
            request.accept_mimetypes.get("text/event-stream", 0)
            > request.accept_mimetypes.get("application/json", 0)
        )
        if wants_stream:
            lock_acquired = acquire_session_lock(session_id)
            if not lock_acquired:
                return error_response(
                    "前のメッセージを処理中です。応答が返るまでお待ちください。",
                    status=409,
                )

            def generate() -> Generator[str, None, None]:
                try:
                    for chunk in llama_core.stream_chat_with_llama(
                        session_id,
                        prompt,
                        mode="travel",
                        language=language,
                    ):
                        yield chunk
                finally:
                    release_session_lock(session_id)

            response = Response(stream_with_context(generate()), mimetype="text/event-stream")
            response.headers["Cache-Control"] = "no-cache"
            response.headers["X-Accel-Buffering"] = "no"
            return response

        with session_request_lock(session_id) as lock_acquired:
            if not lock_acquired:
                return error_response(
                    "前のメッセージを処理中です。応答が返るまでお待ちください。",
                    status=409,
                )

            (
                response,
                current_plan,
                yes_no_phrase,
                choices,
                is_date_select,
                remaining_text,
                used_web_search,
            ) = llama_core.chat_with_llama(
                session_id,
                prompt,
                mode="travel",
                language=language,
            )
            return jsonify({
                'response': response,
                'current_plan': current_plan,
                'yes_no_phrase': yes_no_phrase,
                'choices': choices,
                'is_date_select': is_date_select,
                'remaining_text': remaining_text,
                'used_web_search': used_web_search,
            })

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return error_response("サーバー内部でエラーが発生しました。しばらく待ってから再試行してください。", status=500)


@travel_bp.route('/travel_submit_plan', methods=['POST'])
def submit_plan() -> ResponseOrTuple:
    """
    プラン確定処理エンドポイント
    Finalize plan endpoint.
    
    現在のセッションでの旅行計画を解析し、データベースに保存します。
    Parses session decisions and stores the plan in DB.
    """
    try:
        if not security.is_csrf_valid(request):
            return error_response("不正なリクエストです。", status=403)

        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'error': 'セッションが無効です。'}), 400

        result = reservation.complete_plan(session_id)
        return jsonify({'compile': result})
    except Exception as e:
        logger.error(f"Error in submit_plan: {e}", exc_info=True)
        return jsonify({'error': 'プランの保存に失敗しました。'}), 500
