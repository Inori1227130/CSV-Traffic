from flask import Flask, render_template, request
from flask import session # ボタンの状態を保持するライブラリ（HTTPリクエストごとに状態はリセット）参考：https://ittrip.xyz/python/flask-session-mgmt
import pandas as pd
import sqlite3
import csv
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = 'secret1234' # セッション用キー(Cookieを暗号化する際に使用する秘密鍵だがローカルのアプリなので直接ここに記載)

@app.route('/')
def index(): # http://127.0.0.1:5000/にアクセスしたときに実行される関数
  session.setdefault('formula', '') # セッションデータ（辞書型）の初期化
  
  #データベースに接続
  conn = sqlite3.connect('sample.db')
  c = conn.cursor()

  # scoresテーブルを作成（すでに存在していれば作らない）
  c.execute('''
   CREATE TABLE IF NOT EXISTS accidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    dead INTEGER,
    injuries INTEGER,
    latitude REAL,
    longitude REAL,
    weather TEXT,
    age INTEGER
   )
  ''')

#csvファイルを開く

  c.execute("SELECT COUNT(*) FROM accidents")
  count = c.fetchone()[0]

  if count == 0:
    with open('data/honhyo_2023.csv',encoding='shift_jis') as csvfile:
     reader = csv.DictReader(csvfile)
     for row in reader:
       try:
         accidentyear = row['発生日時　　年']
         accidentmonth = row['発生日時　　月']
         accidentday = row['発生日時　　日']
         accidenthour = row['発生日時　　時']
         accidentminute = row['発生日時　　分']
         
         
          # datetimeで文字列を組み立ててから変換
         accidentdate = f"{accidentyear}-{accidentmonth.zfill(2)}-{accidentday.zfill(2)} {accidenthour.zfill(2)}:{accidentminute.zfill(2)}"
         
         #死者数と負傷者数
         dead = int(row['死者数'])
         injured = int(row['負傷者数'])
         
         #緯度と経度
         if row['地点　緯度（北緯）']:
           latitude = float(row['地点　緯度（北緯）']) 
         else:
           latitude = None
         if row['地点　経度（東経）']:
           longitude = float(row['地点　経度（東経）'])
         else:
           longitude = None
           
         #天候
         weather = row["天候"]
         
         #年齢
         age = row["年齢（当事者A）"]
         
         c.execute("INSERT INTO accidents (date, dead, injuries, latitude, longitude, weather, age) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (accidentdate, dead, injured, latitude, longitude, weather, age))
         
       except Exception as e:
         print("読み込みエラー:", e)
        
  conn.commit()

    # 死者数の平均・最大・最小を計算する
  c.execute("SELECT AVG(dead), MAX(dead), MIN(dead) FROM accidents")
  avg_fatalities, max_fatalities, min_fatalities = c.fetchone()

  # 負傷者数の平均・最大・最小を計算する
  c.execute("SELECT AVG(injuries), MAX(injuries), MIN(injuries) FROM accidents")
  avg_injuries, max_injuries, min_injuries = c.fetchone()

  # pandasでデータを取得する
  df = pd.read_sql_query("SELECT * FROM accidents", conn)
  df['date'] = pd.to_datetime(df['date'], errors='coerce')
  df = df.dropna(subset=['date'])
  df['weekday'] = df['date'].dt.day_name()

  # 曜日の順番を決める
  weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  df['weekday'] = pd.Categorical(df['weekday'], categories=weekday_order, ordered=True)
  df = df.sort_values('weekday')
  weekday_counts = df['weekday'].value_counts().reindex(weekday_order)
  
  #天候別の事故件数
  weather_order = ['1', '2', '3', '4', '5']
  df['weather'] = pd.Categorical(df['weather'], categories=weather_order, ordered=True)
  df = df.sort_values('weather')
  weather_counts = df['weather'].value_counts().reindex(weather_order)
  
  #年齢別の事故件数
  df['age'] = df['age'].astype(str).str.extract('(\d+)')
  df['age'] = pd.to_numeric(df['age'], errors='coerce')
  df = df.dropna(subset=['age'])
  df['age'] = df['age'].astype(int)

  age_counts = df['age'].value_counts().sort_index()
  
  
  #地図の表示
  locations = df[['latitude', 'longitude']].dropna().head(200).values.tolist()
  
  os.makedirs('static', exist_ok=True)

  # 曜日ごとのグラフ描画
  plt.figure(figsize=(5,5))
  weekday_counts.plot(kind='bar', color='red')
  plt.title("Day of the day of accident")
  plt.xlabel("Day of the day")
  plt.ylabel("Number of accidents")
  plt.tight_layout()
  plt.savefig('static/accidents_by_weekday.png')
  plt.close()

  # 天候ごとのグラフ描画
  plt.figure(figsize=(5,5))
  weather_counts.plot(kind='bar', color='red')
  plt.title("Weather of accidents")
  plt.xlabel("weather")
  plt.ylabel("Number of accident")
  plt.tight_layout()
  plt.savefig('static/accidents_by_weather.png')
  plt.close()
  
  # 年齢ごとのグラフ描画
  plt.figure(figsize=(5,5))
  age_counts.plot(kind='bar',color='red' )
  plt.title("Age of accidents")
  plt.xlabel("age")
  plt.ylabel("Number of accident")
  plt.tight_layout()
  plt.savefig('static/accidents_by_age.png')
  plt.close()
  

  conn.close()

  # 結果を表示
  print("死者数の統計:")
  print(f"【死者数】 平均: {avg_fatalities:.2f}, 最大: {max_fatalities}, 最小: {min_fatalities}")
  print("負傷者数の統計:")
  print(f"【負傷者数】 平均: {avg_injuries:.2f}, 最大: {max_injuries}, 最小: {min_injuries}")
  print(df.columns)

  return render_template(
   'index.html', 
    formula=session['formula'],
    result=None,
    error=None,
    graph_path='static/accidents_by_weekday.png',
    avg_fatalities=avg_fatalities,
    max_fatalities=max_fatalities,
    min_fatalities=min_fatalities,
    avg_injuries=avg_injuries,
    max_injuries=max_injuries,
    min_injuries=min_injuries,
    locations = locations
  )

if __name__ == '__main__':
  app.run()