"""
アプリ起動用の薄いエントリポイント。
Thin entrypoint module exposing the Flask app for Gunicorn.
"""

from backend.app import app


if __name__ == "__main__":
    app.run(debug=True)
