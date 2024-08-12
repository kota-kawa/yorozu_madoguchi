from flask import Flask, render_template

app = Flask(__name__)

# ホームのチャット画面
@app.route('/')
def home():
    return render_template('madoguchi.html')

if __name__ == '__main__':
    app.run(debug=True)
