import csv

def write_reservation_plan(destinations, departure, hotel, airlines, railway, taxi, start, end):
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

    # CSVファイルに書き込む
    with open('reservation_plan.csv', mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerows(data)

    return 'finish!'
