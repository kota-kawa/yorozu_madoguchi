from flask import Flask, render_template, request, jsonify
import llama_core

app = Flask(__name__)

# ホームのチャット画面
@app.route('/')
def home():
    return render_template('madoguchi2.html')

# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/send_message', methods=['POST'])
def send_message():
    prompt = request.json.get('message')
    # ここにサーバー側のロジックを追加する（例: チャットボットの応答生成）
    #bot_response = f"サーバーからの応答: {user_message} !!"
    response, current_plan, yes_no_phrase, remaining_text = llama_core.chat_with_llama(prompt)
    return jsonify({'response': response, 'current_plan': current_plan,'yes_no_phrase': yes_no_phrase,'remaining_text': remaining_text})

if __name__ == '__main__':
    app.run(debug=True)
