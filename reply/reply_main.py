from flask import Blueprint, render_template, request, jsonify, redirect, make_response
import llama_core
import reservation
from database import SessionLocal
from models import ReservationPlan
import uuid
import redis_client
import logging

logger = logging.getLogger(__name__)

# Blueprintの定義
reply_bp = Blueprint('reply', __name__)

# ホームのチャット画面
@reply_bp.route('/reply')
def reply_home():
    session_id = str(uuid.uuid4())
    try:
        redis_client.reset_session(session_id)
    except Exception as e:
        logger.error(f"Failed to reset session for {session_id}: {e}")
        
    response = make_response(render_template('reply/reply_madoguchi.html'))
    response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')
    return response

# 予約完了画面
@reply_bp.route('/reply_complete')
def reply_complete():
    reservation_data = []
    db = SessionLocal()
    try:
        plan = db.query(ReservationPlan).first()
        if plan:
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
                if value:
                    reservation_data.append(f"{key}：{value}")
    except Exception as e:
        logger.error(f"Error loading reservation data: {e}")
    finally:
        db.close()

    # 結果をログ出力
    for item in reservation_data:
        logger.info(f"Reservation Data: {item}")
    return render_template('complete.html', reservation_data = reservation_data)

import limit_manager

# メッセージを受け取り、レスポンスを返すエンドポイント
@reply_bp.route('/reply_send_message', methods=['POST'])
def reply_send_message():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。ページをリロードしてください。'}), 400

    # 利用制限のチェック
    is_allowed, count = limit_manager.check_and_increment_limit()
    if not is_allowed:
        return jsonify({
            'response': f"申し訳ありませんが、本日の利用制限（{limit_manager.MAX_DAILY_LIMIT}回）に達しました。明日またご利用ください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    prompt = request.json.get('message')

    # 文字数制限のチェック
    if len(prompt) > 3000:
        return jsonify({
            'response': "入力された文字数が3000文字を超えています。短くして再度お試しください。",
            'current_plan': "",
            'yes_no_phrase': "",
            'remaining_text': ""
        })

    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(session_id, prompt, mode="reply")
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@reply_bp.route('/reply_submit_plan', methods=['POST'])
def reply_submit_plan():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'error': 'セッションが無効です。'}), 400
        
    compile = reservation.complete_plan(session_id)
    return jsonify({'compile': compile})