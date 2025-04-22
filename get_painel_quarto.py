import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# Google Calendar
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configuração
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
calendar_id = os.getenv("CALENDAR_ID")
credentials_json = os.getenv("GOOGLE_CREDENTIALS")

# Dados dinâmicos
now = datetime.now()
data_hoje = now.strftime('%d/%m/%Y')
hora_hoje = now.strftime('%H:%M')

br_holidays = holidays.Brazil(prov='SP')
feriado_hoje = br_holidays.get(now.date())
feriado_text = feriado_hoje if feriado_hoje else 'Nenhum'

# Clima atual
clima_atual = requests.get("https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m").text

# Velocidade Internet
try:
    st = speedtest.Speedtest()
    down = int(st.download() / 1_000_000)
    up = int(st.upload() / 1_000_000)
    internet_text = f'{down} ↓ / {up} ↑'
except:
    internet_text = 'Indisponível'

# Filtro Ar-condicionado
filtro = requests.get(
    f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
    headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
).json()
limpeza_text = "Necessário" if filtro['state'] == "on" else "OK"

# Bandeira Tarifária
bandeira_text = fetch_bandeira()

# Agenda
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
with open('service_account.json', 'w', encoding='utf-8') as f:
    f.write(credentials_json)
creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)
time_min = now.isoformat() + 'Z'
time_max = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'
events = service.events().list(
    calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
    singleEvents=True, orderBy='startTime'
).execute().get('items', [])
compromissos = '<br>'.join([f"{e['start'].get('dateTime', e['start'].get('date')).split('T')[-1][:5]} - {e['summary']}" for e in events]) or 'Nenhum'

# HTML final
html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='UTF-8'>
  <title>Quarto</title>
  <link href='https://fonts.googleapis.com/css2?family=VT323&display=swap' rel='stylesheet'>
  <style>
    body {{ margin:0;background:#000;color:#0f0;font-family:'VT323',monospace; }}
    .outer {{border:2px solid #0f0;max-width:700px;margin:10px auto;padding:10px;}}
    .section {{border:1px solid #0f0;margin-top:10px;padding:10px;}}
  </style>
</head>
<body>
<div class='outer'>
  <div class='section'>
    <h3>Agenda</h3>
    <p>Data: {data_hoje}</p>
    <p>Hora: {hora_hoje}</p>
    <p>Feriado: {feriado_text}</p>
    <p>Compromissos: {compromissos}</p>
  </div>
  <div class='section'>
    <h3>Tempo</h3>
    <p>{clima_atual}</p>
  </div>
  <div class='section'>
    <h3>Sistema</h3>
    <p>Internet: {internet_text}</p>
    <p>Limpeza: {limpeza_text}</p>
    <p>Bandeira: {bandeira_text}</p>
  </div>
</div>
</body>
</html>
"""

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
