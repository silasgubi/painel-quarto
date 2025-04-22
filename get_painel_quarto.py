#!/usr/bin/env python3
import os
import csv
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ─── CONFIGURAÇÃO VIA ENV VARS ────────────────────────────────────────────
HA_URL     = os.getenv("HA_URL").rstrip("/")
HA_TOKEN   = os.getenv("HA_TOKEN")
CAL_ID     = os.getenv("CALENDAR_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
NABU_BASE  = os.getenv("NABU_URL").rstrip("/")

# ─── LEITURA DA PLANILHA CSV (latin-1) ─────────────────────────────────────
buttons = {}
with open("planilha_quarto.csv", encoding="latin-1", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sec = row["seção"].strip()  # "Luzes", "Dispositivos" ou "Cenas"
        buttons.setdefault(sec, []).append({
            "label":   row["label"].strip(),
            "icone":   row["icone"].strip(),
            "webhook": row["webhook"].strip()
        })

# ─── DATA, HORA E FERIADOS ─────────────────────────────────────────────────
now       = datetime.now()
data_hora = now.strftime("%d/%m/%Y %H:%M")
br        = holidays.Brazil(prov="SP")
feriado   = br.get(now.date()) or "Nenhum"

# ─── TEMPERATURA & UMIDADE DO QUARTO ──────────────────────────────────────
try:
    resp = requests.get(
        f"{HA_URL}/api/states/climate.quarto",
        headers={"Authorization": f"Bearer {HA_TOKEN}"}, timeout=10
    ).json()
    t = resp.get("attributes", {}).get("current_temperature", "—")
    h = resp.get("attributes", {}).get("current_humidity", "—")
    quarto_text = f"{t}°C / {h}%"
except:
    quarto_text = "Indisponível"

# ─── VELOCIDADE DE INTERNET ────────────────────────────────────────────────
try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up   = int(st.upload() / 1_000_000)
    internet_text = f"{down} ↓ / {up} ↑"
except:
    internet_text = "Indisponível"

# ─── FILTRO DO AR-CONDICIONADO ─────────────────────────────────────────────
try:
    state = requests.get(
        f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
        headers={"Authorization": f"Bearer {HA_TOKEN}"}, timeout=5
    ).json().get("state", "off")
    limpeza_text = "Necessário" if state == "on" else "OK"
except:
    limpeza_text = "—"

# ─── BANDEIRA TARIFÁRIA ────────────────────────────────────────────────────
bandeira_text = fetch_bandeira()

# ─── AGENDA VIA GOOGLE CALENDAR ────────────────────────────────────────────
with open("service_account.json", "w", encoding="utf-8") as f:
    f.write(CREDS_JSON)
creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/calendar.readonly"]
)
service = build("calendar", "v3", credentials=creds)

start = now.isoformat() + "Z"
end   = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"
events = service.events().list(
    calendarId=CAL_ID, timeMin=start, timeMax=end,
    singleEvents=True, orderBy="startTime"
).execute().get("items", [])

if events:
    compromissos = "<br>".join([
        f"{(e['start'].get('dateTime') or e['start'].get('date')).split('T')[-1][:5]} – {e.get('summary','')}"
        for e in events
    ])
else:
    compromissos = "Nenhum"

# ─── GERA HTML FINAL (sem backslashes em f-strings) ────────────────────────
html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0;background:#000;color:#0f0;font-family:'VT323',monospace; }}
    .outer {{border:2px solid #0f0;max-width:700px;margin:10px auto;padding:10px;}}
    .section {{border:1px solid #0f0;margin-top:10px;padding:10px;}}
    .grid    {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .btn     {{ border:1px solid #0f0; padding:5px; text-align:center; cursor:pointer; }}
    .btn img {{ width:32px; height:32px; }}
  </style>
  <script>
    function toggle(wh) {{
      fetch("{NABU_BASE}/api/webhook/" + wh, {{ method: "POST" }});
    }}
    function atualizaHora() {{
      document.getElementById("dh").innerText = "{data_hora}";
    }}
  </script>
</head>
<body onload="atualizaHora()">
  <div class="outer">

    <!-- LUZES -->
    <div class="section">
      <h3>Luzes</h3>
      <div class="grid">
        {''.join(
            f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
            f'<img src="assets/icones/{b["icone"]}"><br>'
            f'{b["label"]}</div>'
            for b in buttons.get("Luzes", [])
        )}
      </div>
    </div>

    <!-- DISPOSITIVOS -->
    <div class="section">
      <h3>Dispositivos</h3>
      <div class="grid">
        {''.join(
            f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
            f'<img src="assets/icones/{b["icone"]}"><br>'
            f'{b["label"]}</div>'
            for b in buttons.get("Dispositivos", [])
        )}
      </div>
    </div>

    <!-- CENAS -->
    <div class="section">
      <h3>Cenas</h3>
      <div class="grid">
        {''.join(
            f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
            f'<img src="assets/icones/{b["icone"]}"><br>'
            f'{b["label"]}</div>'
            for b in buttons.get("Cenas", [])
        )}
      </div>
    </div>

    <!-- AGENDA -->
    <div class="section">
      <h3>Agenda</h3>
      <p id="dh">Carregando…</p>
      <p>Feriado: {feriado}</p>
      <p>Compromissos:<br>{compromissos}</p>
    </div>

    <!-- TEMPO -->
    <div class="section">
      <h3>Tempo</h3>
      <p>☁️ {requests.get("https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m").text}</p>
    </div>

    <!-- SISTEMA -->
    <div class="section">
      <h3>Sistema</h3>
      <p>Velocidade da Internet: {internet_text}</p>
      <p>Limpeza dos Filtros do Ar-condicionado: {limpeza_text}</p>
      <p>⚠ Bandeira Tarifária: {bandeira_text}</p>
      <p>Quarto: {quarto_text}</p>
    </div>

  </div>
</body>
</html>'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
