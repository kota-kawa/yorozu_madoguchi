import json
import datetime
import os
import fcntl
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LIMIT_FILE = BASE_DIR / 'daily_usage.json'
MAX_DAILY_LIMIT = 10

def check_and_increment_limit(user_id="default"):
    """
    指定されたユーザーID（IPアドレスなど）の利用回数をチェックし、
    制限内であればカウントを増やしてTrueを返す。
    制限を超えていればFalseを返す。
    ファイルロックを使用して同時アクセス時の整合性を保つ。
    """
    today_str = datetime.date.today().isoformat()
    
    # ファイルを読み書きモードで開く（存在しない場合は作成されるように 'a+' で開いてから読み込む手もあるが、
    # ロックのために 'r+' または 'w+' が望ましい。初期作成は別途処理する）
    
    if not LIMIT_FILE.exists():
        with open(LIMIT_FILE, 'w') as f:
            json.dump({'date': today_str, 'usage': {}}, f)
            
    try:
        with open(LIMIT_FILE, 'r+') as f:
            # 排他ロックを取得（他プロセスが書き込み中の場合待機する）
            fcntl.flock(f, fcntl.LOCK_EX)
            
            try:
                content = f.read()
                if not content:
                    data = {'date': today_str, 'usage': {}}
                else:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = {'date': today_str, 'usage': {}}

                # データ構造の検証と日付リセット
                # 古い形式({"count": ...})の場合や日付が変わった場合はリセット
                if data.get('date') != today_str or 'usage' not in data or not isinstance(data['usage'], dict):
                    data = {'date': today_str, 'usage': {}}
                
                current_count = data['usage'].get(user_id, 0)
                
                if current_count >= MAX_DAILY_LIMIT:
                    return False, current_count
                
                # カウントアップ
                new_count = current_count + 1
                data['usage'][user_id] = new_count
                
                # ファイルの先頭に戻って書き込み
                f.seek(0)
                f.truncate()
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno()) # ディスクへの書き込みを確実に
                
                return True, new_count

            finally:
                # ロック解除
                fcntl.flock(f, fcntl.LOCK_UN)
                
    except IOError as e:
        print(f"Error accessing limit file: {e}")
        # エラー時は安全側に倒して（または厳密にエラーとして）処理。
        # ここでは一時的なエラーとしてFalseを返すべきかもしれないが、
        # ユーザー体験を損なわないよう、ファイルアクセスエラーなら許可するという考え方もできる。
        # しかし「厳密なロジック」という要望なので、管理できない場合は拒否する方が安全。
        return False, -1