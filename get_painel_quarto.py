import os
import csv
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# Google Calendar
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Configurações de ambiente
HA_URL           = os.getenv("HA_URL")
HA_TOKEN         = os.getenv("HA_TOKEN")
CALENDAR_ID      = os.getenv("CALENDAR_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# Datas e hora atuais
now        = datetime.now()
data_hoje  = now.strftime("%d/%m/%Y")
hora_hoje  = now.strftime("%H:%M")

# Feriados SP
br_holidays   = holidays.Brazil(prov="SP")
feriado_hoje  = br_holidays.get(now.date())
feriado_text  = feriado_hoje if feriado_hoje else "Nenhum"

# Leitura da planilha de botões (encoding corrigido)
botões = {"Luzes": [], "Dispositivos": [], "Cenas": []}
with open("planilha_quarto.csv", mode="r", encoding="latin-1", newline="") as f:
    reader = csv.DictReader(f)
    for linha in reader:
        sec = linha["seção"]              # deve ser exatamente "Luzes", "Dispositivos" ou "Cenas"
        botões[sec].append({
            "label": linha["label"],
            "icon":  linha["icone"],      # ex: assets/icones/luz.svg
            "webhook_on":  linha["webhook_on"],
            "webhook_off": linha["webhook_off"]
        })

# Clima atual (wttr.in)
clima_atual = requests.get(
    "https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m"
).text.strip()

# Velocidade de internet
try:
    st   = speedtest.Speedtest()
    down = int(st.download() / 1_000_000)
    up   = int(st.upload()   / 1_000_000)
    internet_text = f"{down} ↓ / {up} ↑"
except:
    internet_text = "Indisponível"

# Filtro do ar-condicionado
resp = requests.get(
    f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
    headers={
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
).json()
limpeza_text = "Necessário" if resp.get("state") == "on" else "OK"

# Bandeira tarifária
bandeira_text = fetch_bandeira()

# Agenda Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
# grava temporariamente credenciais
with open("service_account.json", "w", encoding="utf-8") as f:
    f.write(GOOGLE_CREDENTIALS)
creds   = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
service = build("calendar", "v3", credentials=creds)
time_min = now.isoformat() + "Z"
time_max = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"

events = service.events().list(
    calendarId=CALENDAR_ID,
    timeMin=time_min, timeMax=time_max,
    singleEvents=True, orderBy="startTime"
).execute().get("items", [])

if events:
    compromissos = "<br>".join(
        f"{e['start'].get('dateTime', e['start'].get('date')).split('T')[-1][:5]} – {e.get('summary','Sem título')}"
        for e in events
    )
else:
    compromissos = "Nenhum"

# Montagem do HTML
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Quarto</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0; background:#000; color:#0f0; font-family:'VT323',monospace; }}
    .outer {{ border:2px solid #0f0; max-width:700px; margin:10px auto; padding:10px; }}
    .section {{ border:1px solid #0f0; margin-top:10px; padding:10px; }}
    .grid {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .btn {{
      width:60px; height:60px; border:1px solid #0f0; display:flex;
      flex-direction:column; align-items:center; justify-content:center;
      cursor:pointer;
    }}
    .btn img {{ width:30px; height:30px; filter:invert(100%); }}
    .btn span {{ font-size:0.7em; margin-top:2px; }}
    .info p {{ margin:4px 0; }}
  </style>
  <script>
    function toggle(onUrl, offUrl) {{
      fetch(onUrl).catch(_=>fetch(offUrl));
    }}
  </script>
</head>
<body>
  <div class="outer">
    <!-- Luzes -->
    <div class="section"><h3>Luzes</h3>
      <div class="grid">"""
for b in botões["Luzes"]:
    html += f"""
        <div class="btn" onclick="fetch('{b['webhook_on']}')">
          <img src="{b['icon']}" alt="">
          <span>{b['label']}</span>
        </div>"""
    html += f"""
        <div class="btn" onclick="fetch('{b['webhook_off']}')">
          <img src="{b['icon'].replace('.svg','_off.svg')}" alt="">
          <span>{b['label']}</span>
        </div>"""
html += """
      </div>
    </div>"""

# Dispositivos
html += """
    <div class="section"><h3>Dispositivos</h3>
      <div class="grid">"""
for b in botões["Dispositivos"]:
    html += f"""
        <div class="btn" onclick="fetch('{b['webhook_on']}')">
          <img src="{b['icon']}" alt="">
          <span>{b['label']}</span>
        </div>"""
    html += f"""
        <div class="btn" onclick="fetch('{b['webhook_off']}')">
          <img src="{b['icon'].replace('.svg','_off.svg')}" alt="">
          <span>{b['label']}</span>
        </div>"""
html += """
      </div>
    </div>"""

# Cenas
html += """
    <div class="section"><h3>Cenas</h3>
      <div class="grid">"""
for b in botões["Cenas"]:
    html += f"""
        <div class="btn" onclick="fetch('{b['webhook_on']}')">
          <img src="{b['icon']}" alt="">
          <span>{b['label']}</span>
        </div>"""
html += """
      </div>
    </div>"""

# Agenda
html += f"""
    <div class="section">
      <h3>Agenda</h3>
      <p>Data/Hora: {data_hoje} {hora_hoje}</p>
      <p>Feriado: {feriado_text}</p>
      <p>Compromissos:<br>{compromissos}</p>
    </div>"""

# Tempo
html += f"""
    <div class="section">
      <h3>Tempo</h3>
      <p>{clima_atual}</p>
    </div>"""

# Sistema
html += f"""
    <div class="section">
      <h3>Sistema</h3>
      <div class="info">
        <p>Velocidade da Internet: {internet_text}</p>
        <p>Limpeza dos Filtros do Ar-condicionado: {limpeza_text}</p>
        <p>⚠ Bandeira Tarifária: {bandeira_text}</p>
        <p>Quarto: {fetch_bandeira.__module__}</p>
      </div>
    </div>"""

html += """
  </div>
</body>
</html>
"""

# Grava no docs/index.html
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
