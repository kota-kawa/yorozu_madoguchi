from flask import Flask, render_template, request, jsonify, redirect
import llama_core
import reservation

app = Flask(__name__)

from reply.reply_main import reply_bp

# Blueprintの登録
app.register_blueprint(reply_bp)

# ホームのチャット画面
@app.route('/')
def home():
    # テキストファイルの内容を消す
    with open('./chat_history.txt', 'w') as file:
        pass  # ファイルを開いて何も書かないことで内容が空になります。
    with open('./decision.txt', 'w') as file:
        pass  # ファイルを開いて何も書かないことで内容が空になります。
    return render_template('travel_madoguchi.html')

# 予約完了画面
@app.route('/complete')
def complete():
    reservation_data = []
    with open('./reservation_plan.csv', 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        for line in lines:
            row = line.strip().split(',')
            if len(row) == 2 and row[0] and row[1]:
                key = row[0].strip()
                value = row[1].strip()
                if key and value:
                    reservation_data.append(f"{key}：{value}")
    # 結果を表示
    for item in reservation_data:
        print(item)
    return render_template('complete.html', reservation_data = reservation_data)

# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/travel_send_message', methods=['POST'])
def send_message():
    prompt = request.json.get('message')
    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt)
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@app.route('/travel_submit_plan', methods=['POST'])
def submit_plan():
    compile = reservation.complete_plan()
    return jsonify({'compile': compile})

if __name__ == '__main__':
    app.run(debug=True)
