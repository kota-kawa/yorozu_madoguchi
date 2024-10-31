from flask import Flask, render_template, request, jsonify
import js_repl

app = Flask(__name__)

# ホームのチャット画面
@app.route('/')
def home():
    return render_template('win_test.html')

# チャットメッセージを受け取るエンドポイント
@app.route('/submit_message', methods=['POST'])
def submit_message():
    data = request.get_json()  # JSONデータを受け取る
    message = data.get('message', '')  # メッセージを取得
    html_code = data.get('html', '')
    print(html_code, message)
    print(f"User message: {message}")  # コンソールにメッセージを表示
    extracted_code,remaining_text = js_repl.chain_main(message, html_code) 

    # ここで必要に応じてサーバー側で処理を行う
    response = {
        'user_message': message,
        'remaining_text': remaining_text,  # 仮のボットの返答
        'extracted_code': extracted_code  # 見つかったJavascriptコード (存在しない場合はNone)
    }

    return jsonify(response)  # JSON形式でレスポンスを返す

if __name__ == '__main__':
    app.run(debug=True)
