import csv

def write_reservation_plan(destinations, departure, hotel, airlines, railway, taxi, start, end, session_id=None):
    # 書き込み用のデータをリストとして定義
    data = [
        ['目的地', destinations],
        ['出発地', departure],
        ['ホテル', hotel],
        ['航空会社', airlines],
        ['鉄道会社', railway],
        ['タクシー会社', taxi],
        ['滞在開始日', start],
        ['滞在終了日', end]
    ]

    filename = './reservation_plan.csv'
    if session_id:
        filename = f'./reservation_plan_{session_id}.csv'

    # CSVファイルに書き込む
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerows(data)

    return 'finish!'
