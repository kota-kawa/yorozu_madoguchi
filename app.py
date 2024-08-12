from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ホームのチャット画面
@app.route('/')
def home():
    return render_template('madoguchi.html')

# メッセージを受け取り、レスポンスを返すエンドポイント
@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')
    # ここにサーバー側のロジックを追加する（例: チャットボットの応答生成）
    bot_response = f"サーバーからの応答: {user_message} !!"
    return jsonify({'response': bot_response})

if __name__ == '__main__':
    app.run(debug=True)
