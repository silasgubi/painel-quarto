#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import speedtest
from datetime import datetime
import holidays

# --------------------------------------------------------
# 1) Tente importar Google Calendar; se falhar, fallback
# --------------------------------------------------------
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# ID do seu calendário, vindo do secret CALENDAR_ID
CALENDAR_ID = os.getenv('CALENDAR_ID', '').strip()

if HAS_GOOGLE and CALENDAR_ID:
    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        creds_json = os.getenv('GOOGLE_CREDENTIALS')
        with open('service_account.json', 'w', encoding='utf-8') as f:
            f.write(creds_json)
        creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception:
        HAS_GOOGLE = False

# --------------------------------------------------------
# 2) Data e hora atuais
# --------------------------------------------------------
now        = datetime.now()
data_hoje   = now.strftime('%d/%m/%Y')
hora_hoje   = now.strftime('%H:%M')

# --------------------------------------------------------
# 3) Feriados Brasil (SP)
# --------------------------------------------------------
br = holidays.Brazil(prov='SP')
fer = br.get(now.date())
if fer:
    feriado_text = f"Hoje é feriado: {fer}"
else:
    futuros = sorted(d for d in br if d > now.date() and d.year == now.year)
    if futuros:
        proximo = futuros[0]
        feriado_text = f"Próximo feriado: {br.get(proximo)} em {proximo.strftime('%d/%m/%Y')}"
    else:
        feriado_text = "Não há mais feriados este ano"

# --------------------------------------------------------
# 4) Clima do quarto via API REST do Home Assistant
# --------------------------------------------------------
HA_URL   = os.getenv('HA_URL').rstrip('/')
HA_TOKEN = os.getenv('HA_TOKEN')
CLIMATE_ENTITY = 'climate.quarto'

try:
    r = requests.get(
        f"{HA_URL}/api/states/{CLIMATE_ENTITY}",
        headers={'Authorization': f"Bearer {HA_TOKEN}", 'Content-Type': 'application/json'},
        timeout=10
    ).json()
    temp = r.get('state', '—')
    hum  = r.get('attributes', {}).get('current_humidity', '—')
    clima_quarto = f"{data_hoje} {hora_hoje} — {temp}°C / {hum}%"
except:
    clima_quarto = "Clima indisponível"

# --------------------------------------------------------
# 5) Agenda: Google Calendar ou fallback
# --------------------------------------------------------
if HAS_GOOGLE and CALENDAR_ID:
    tmin = now.isoformat() + 'Z'
    tmax = datetime(now.year, now.month, now.day, 23,59,59).isoformat() + 'Z'
    try:
        evs = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=tmin, timeMax=tmax,
            singleEvents=True, orderBy='startTime'
        ).execute().get('items', [])
        if not evs:
            agenda_text = "Compromissos: Nenhum"
        else:
            lines = []
            for ev in evs:
                st = ev['start'].get('dateTime', ev['start'].get('date'))
                tm = st.split('T')[1][:5] if 'T' in st else st
                lines.append(f"{tm} – {ev.get('summary','Sem título')}")
            agenda_text = "Compromissos:<br>" + "<br>".join(lines)
    except:
        agenda_text = "Agenda indisponível"
else:
    agenda_text = "Agenda indisponível"

# --------------------------------------------------------
# 6) Teste de velocidade de Internet
# --------------------------------------------------------
try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up   = int(st.upload()   / 1_000_000)
    internet_text = f"Velocidade: {down} ↓ / {up} ↑"
except:
    internet_text = "Velocidade: Offline"

# --------------------------------------------------------
# 7) Filtro de ar-condicionado (binary_sensor)
# --------------------------------------------------------
FILTER_SENSOR = 'binary_sensor.quarto_filter_clean_required'
try:
    f = requests.get(
        f"{HA_URL}/api/states/{FILTER_SENSOR}",
        headers={'Authorization': f"Bearer {HA_TOKEN}", 'Content-Type': 'application/json'},
        timeout=5
    ).json()
    filtro_text = "Limpeza: 🚩" if f.get('state') == 'on' else "Limpeza: OK"
except:
    filtro_text = "Limpeza: —"

# --------------------------------------------------------
# 8) Bandeira tarifária (import do módulo bandeira.py)
# --------------------------------------------------------
try:
    from bandeira import fetch_bandeira
    bandeira_text = f"Bandeira: {fetch_bandeira()}"
except:
    bandeira_text = "Bandeira: —"

# --------------------------------------------------------
# 9) Montagem do HTML final
# --------------------------------------------------------
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Painel Quarto — {data_hoje} {hora_hoje}</title>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }}
  .outer {{ border:2px solid #0A0; max-width:700px; margin:10px auto; padding:10px; display:none; }}
  .section {{ border:1px solid #0A0; padding:10px; margin-top:10px; }}
  .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; opacity:0.9; }}
  #bootScreen {{ white-space:pre; background:#000; color:#0F0; padding:20px; font-size:1em; }}
</style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <div id="bootScreen"></div>
  <div class="outer">
    <div class="section"><h3>Luzes</h3><!-- botões REST aqui --></div>
    <div class="section"><h3>Dispositivos</h3><!-- botões REST aqui --></div>
    <div class="section"><h3>Cenas</h3><!-- botões REST aqui --></div>
    <div class="section"><h3>Sistema</h3>
      <p>{clima_quarto}</p>
      <p>{agenda_text}</p>
      <p>{internet_text}</p>
      <p>{feriado_text}</p>
      <p>{filtro_text}</p>
      <p>{bandeira_text}</p>
    </div>
  </div>
  <script>
    // Boot MS-DOS
    const lines = [
      "Phoenix Technologies Ltd. Version 4.06",
      "Memory Testing: 524288K OK",
      "Loading DOS...",
      "Starting Smart Panel Interface..."
    ];
    let i=0;
    function next() {{
      const el = document.getElementById('bootScreen');
      if (i < lines.length) {{
        el.innerText += lines[i++] + "\\n";
        setTimeout(next,300);
      }} else {{
        setTimeout(()=> {{
          document.getElementById('bootScreen').style.display='none';
          document.querySelector('.outer').style.display='block';
        }},1000);
      }}
    }}
    document.addEventListener('DOMContentLoaded', () => {{
      document.getElementById('bootSound').play();
      next();
    }});
  </script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
