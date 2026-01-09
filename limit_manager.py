import json
import datetime
import os
import fcntl
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LIMIT_FILE = BASE_DIR / 'daily_usage.json'
MAX_DAILY_LIMIT = 10

def check_and_increment_limit():
    """
    全ユーザー合計の利用回数をチェックし、
    制限内であればカウントを増やしてTrueを返す。
    制限を超えていればFalseを返す。
    ファイルロックを使用して同時アクセス時の整合性を保つ。
    """
    today_str = datetime.date.today().isoformat()
    
    if not LIMIT_FILE.exists():
        with open(LIMIT_FILE, 'w') as f:
            json.dump({'date': today_str, 'count': 0}, f)
            
    try:
        with open(LIMIT_FILE, 'r+') as f:
            # 排他ロックを取得
            fcntl.flock(f, fcntl.LOCK_EX)
            
            try:
                content = f.read()
                if not content:
                    data = {'date': today_str, 'count': 0}
                else:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = {'date': today_str, 'count': 0}

                # 日付が変わっていたらリセット
                # データ構造が古い場合('usage'がある場合など)もリセット
                if data.get('date') != today_str or 'count' not in data:
                    data = {'date': today_str, 'count': 0}
                
                if data['count'] >= MAX_DAILY_LIMIT:
                    return False, data['count']
                
                # カウントアップ
                data['count'] += 1
                
                # ファイルの先頭に戻って書き込み
                f.seek(0)
                f.truncate()
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
                
                return True, data['count']

            finally:
                # ロック解除
                fcntl.flock(f, fcntl.LOCK_UN)
                
    except IOError as e:
        print(f"Error accessing limit file: {e}")
        # エラー時は安全のためFalseを返す（または運用に合わせてTrue）
        return False, -1
