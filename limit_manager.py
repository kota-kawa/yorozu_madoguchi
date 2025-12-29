import json
import datetime
import os

LIMIT_FILE = 'daily_usage.json'
MAX_DAILY_LIMIT = 30

def check_and_increment_limit():
    today_str = datetime.date.today().isoformat()
    
    if not os.path.exists(LIMIT_FILE):
        data = {'date': today_str, 'count': 0}
    else:
        try:
            with open(LIMIT_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {'date': today_str, 'count': 0}

    # 日付が変わっていたらリセット
    if data.get('date') != today_str:
        data = {'date': today_str, 'count': 0}
    
    if data['count'] >= MAX_DAILY_LIMIT:
        return False, data['count']
    
    data['count'] += 1
    
    with open(LIMIT_FILE, 'w') as f:
        json.dump(data, f)
        
    return True, data['count']
