#!/usr/bin/env python3
import os
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

# ─── DADOS DA PLANILHA INCLUÍDOS DIRETAMENTE NO CÓDIGO ────────────────────
buttons = {
    "Luzes": [
        {
            "label": "Quarto",
            "icone": "luz_on.svg",
            "webhook": "-CypOVrETUPzU3j597Zv_Zt5A"
        },
        {
            "label": "Abajur 1",
            "icone": "abajur_on.svg",
            "webhook": "-MFVOA3AtnRp1jXwKo1OC9OHG"
        },
        {
            "label": "Abajur 2",
            "icone": "abajur_on.svg",
            "webhook": "-ABK97nz2L99Ii7UEbruta9Qv"
        },
        {
            "label": "Cama",
            "icone": "cama_on.svg",
            "webhook": "-XWBgJ0fL2a3Qi1jDCOXSUccU"
        },
        {
            "label": "Banheiro Suíte",
            "icone": "banheiro_on.svg",
            "webhook": "-xX0MHHD3C5EWUCLZVDd-pN6x"
        },
        {
            "label": "Luz Noturna",
            "icone": "luz_on.svg",
            "webhook": "-ZNDib6M8xbHnRgpwpELIINvl"
        }
    ],
    "Dispositivos": [
        {
            "label": "Ar-condiconado",
            "icone": "ar_on.svg",
            "webhook": "-B5-obF5Y6y6wbXDwcmq6P8gM"
        },
        {
            "label": "Projetor",
            "icone": "projetor_on.svg",
            "webhook": "-oLWNzYt_bn3GE3GieCd50F6h"
        },
        {
            "label": "USB Ipad Quarto",
            "icone": "usb_on.svg",
            "webhook": "-AdcXN-BIm93zq9D2bzuhR-9n"
        }
    ],
    "Cenas": [
        {
            "label": "Luzes Vermelhas",
            "icone": "luzes_vermelhas_on.svg",
            "webhook": "-pKBlAuGBMXwVLP6QE_5PmKPU"
        }
    ]
}

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

# ─── GERA HTML FINAL ──────────────────────────────────────────────────────
html = r'''<!DOCTYPE html>
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
        {"".join(
            f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
            f'<img src="assets/icones/{b["icone"]}"><br>'
            f'{b["label"]}</div>'
            for b in buttons.get("Luzes", [])
        )}
      </div>
    </div>
    <!-- Outras seções... -->
  </div>
</body>
</html>'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
