#!/usr/bin/env python3
import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- 1) Configurações vindas dos Secrets do GitHub Actions ---
HA_URL       = os.getenv("HA_URL")        # ex: https://tpplz8oygoqmaagdruizwe214e6bl6cs.ui.nabu.casa
HA_TOKEN     = os.getenv("HA_TOKEN")
CALENDAR_ID  = os.getenv("CALENDAR_ID")
CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

# Checagem rápida de Secrets
if not (HA_URL and HA_TOKEN and CALENDAR_ID and CREDENTIALS_JSON):
    raise RuntimeError("Um ou mais Secrets (HA_URL, HA_TOKEN, CALENDAR_ID, GOOGLE_CREDENTIALS) não configurados!")

# --- 2) Dados de Data/Hora e Feriados ---
now         = datetime.now()
data_hoje   = now.strftime("%d/%m/%Y")
hora_hoje   = now.strftime("%H:%M")

br_holidays = holidays.Brazil(prov="SP")
feriado_hoje = br_holidays.get(now.date())
feriado_text = feriado_hoje if feriado_hoje else "Nenhum"

# --- 3) Clima via wttr.in ---
try:
    clima_atual = requests.get(
        "https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m",
        timeout=10
    ).text.strip()
except Exception as e:
    clima_atual = f"Erro ao obter clima: {e}"

# --- 4) Velocidade de Internet ---
try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up   = int(st.upload()   / 1_000_000)
    internet_text = f"{down} ↓ / {up} ↑"
except Exception as e:
    internet_text = f"Erro Speedtest: {e}"

# --- 5) Filtro do Ar-condicionado via HA REST ---
try:
    resp = requests.get(
        f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10
    )
    filtro = resp.json().get("state", "")
    limpeza_text = "Necessário" if filtro=="on" else "OK"
except Exception as e:
    limpeza_text = f"Erro HA filtro: {e}"

# --- 6) Bandeira Tarifária ANEEL ---
try:
    bandeira_text = fetch_bandeira()
except Exception as e:
    bandeira_text = f"Erro bandeira: {e}"

# --- 7) Agenda via Google Calendar ---
compromissos = "Nenhum"
try:
    # salva temporariamente o JSON das credenciais
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(CREDENTIALS_JSON)

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

    time_min = now.isoformat() + "Z"
    time_max = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

    events = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    if events:
        lines = []
        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            hora = start.split("T")[-1][:5] if "T" in start else start
            lines.append(f"{hora} – {ev.get('summary','Sem título')}")
        compromissos = "<br>".join(lines)
except Exception as e:
    compromissos = f"Erro agenda: {e}"

# --- 8) Montagem do HTML final ---
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto — {data_hoje} {hora_hoje}</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }}
    .outer {{ border:2px solid #0A0; max-width:700px; margin:10px auto; padding:10px; }}
    .section {{ border:1px solid #0A0; padding:10px; margin-top:10px; }}
    .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; opacity:0.8; }}
    .section p {{ margin:5px 0; }}
  </style>
</head>
<body>
  <div class="outer">
    <div class="section">
      <h3>Agenda</h3>
      <p>Data: {data_hoje}</p>
      <p>Hora: {hora_hoje}</p>
      <p>Feriado: {feriado_text}</p>
      <p>Compromissos:<br>{compromissos}</p>
    </div>
    <div class="section">
      <h3>Tempo</h3>
      <p>{clima_atual}</p>
    </div>
    <div class="section">
      <h3>Sistema</h3>
      <p>Internet: {internet_text}</p>
      <p>Limpeza: {limpeza_text}</p>
      <p>Bandeira: {bandeira_text}</p>
    </div>
  </div>
</body>
</html>
"""

# DEBUG: mostra no console do Actions
print("=== HTML GERADO ===")
print(html)
print("===================")

# --- 9) Grava no docs/index.html ---
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
