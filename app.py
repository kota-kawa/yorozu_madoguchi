from flask import Flask, render_template, request, jsonify, redirect
import llama_core
import reservation

app = Flask(__name__)

# ホームのチャット画面
@app.route('/')
def home():
    return render_template('madoguchi2.html')

@app.route('/complete')
def complete():
    reservation_data = []
    with open('reservation_plan.csv', 'r', encoding='utf-8-sig') as file:
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
@app.route('/send_message', methods=['POST'])
def send_message():
    prompt = request.json.get('message')
    # ここにサーバー側のロジックを追加する（例: チャットボットの応答生成）
    #bot_response = f"サーバーからの応答: {user_message} !!"
    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt)
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

@app.route('/submit_plan', methods=['POST'])
def submit_plan():
    compile = reservation.complete_plan()
    return jsonify({'compile': compile})

if __name__ == '__main__':
    app.run(debug=True)
