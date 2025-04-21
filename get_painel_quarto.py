#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira  # módulo bandeira.py já criado

# -----------------------------
# Configuração via Secrets
# -----------------------------
HA_URL      = os.environ['HA_URL'].rstrip('/')
HA_TOKEN    = os.environ['HA_TOKEN']
CALENDAR_ID = os.environ.get('CALENDAR_ID', '').strip()
GOOGLE_CRED = os.environ.get('GOOGLE_CREDENTIALS', '')

# -----------------------------
# Google Calendar (opcional)
# -----------------------------
HAS_GOOGLE = False
if CALENDAR_ID and GOOGLE_CRED:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        HAS_GOOGLE = True
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        with open('service_account.json', 'w', encoding='utf-8') as f:
            f.write(GOOGLE_CRED)
        creds   = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except:
        HAS_GOOGLE = False

# -----------------------------
# Dados dinâmicos
# -----------------------------
now        = datetime.now()
data_hoje   = now.strftime('%d/%m/%Y')
hora_hoje   = now.strftime('%H:%M')

# Feriados SP
br = holidays.Brazil(prov='SP')
fer = br.get(now.date())
if fer:
    feriado_text = f"Hoje é feriado: {fer}"
else:
    futuros = sorted(d for d in br if d > now.date() and d.year == now.year)
    if futuros:
        pd = futuros[0]
        feriado_text = f"Próximo feriado: {br.get(pd)} em {pd.strftime('%d/%m/%Y')}"
    else:
        feriado_text = "Não há mais feriados este ano"

def get_clima():
    try:
        e = 'climate.quarto'
        r = requests.get(f"{HA_URL}/api/states/{e}",
                         headers={'Authorization': f"Bearer {HA_TOKEN}"}, timeout=5)
        j = r.json()
        t = j.get('state','—')
        h = j.get('attributes',{}).get('current_humidity','—')
        return f"{data_hoje} {hora_hoje} — {t}°C / {h}%"
    except:
        return "Clima indisponível"

def get_agenda():
    if not HAS_GOOGLE:
        return "Compromissos: Nenhum"
    try:
        tmin = now.isoformat() + 'Z'
        tmax = datetime(now.year,now.month,now.day,23,59,59).isoformat() + 'Z'
        evs = service.events().list(
            calendarId=CALENDAR_ID, timeMin=tmin, timeMax=tmax,
            singleEvents=True, orderBy='startTime'
        ).execute().get('items', [])
        if not evs:
            return "Compromissos: Nenhum"
        lines = []
        for ev in evs:
            st = ev['start'].get('dateTime', ev['start'].get('date'))
            tm = st.split('T')[1][:5] if 'T' in st else st
            lines.append(f"{tm} – {ev.get('summary','Sem título')}")
        return "Compromissos:<br>" + "<br>".join(lines)
    except:
        return "Agenda indisponível"

def get_speed():
    try:
        st = speedtest.Speedtest(); st.get_best_server()
        d = int(st.download()/1e6); u = int(st.upload()/1e6)
        return f"Velocidade: {d} ↓ / {u} ↑"
    except:
        return "Velocidade: Offline"

def get_filtro():
    try:
        e = 'binary_sensor.quarto_filter_clean_required'
        r = requests.get(f"{HA_URL}/api/states/{e}",
                         headers={'Authorization': f"Bearer {HA_TOKEN}"}, timeout=5)
        state = r.json().get('state','off')
        return "Limpeza: 🚩" if state=='on' else "Limpeza: OK"
    except:
        return "Limpeza: —"

def get_bandeira_text():
    try:
        return f"Bandeira: {fetch_bandeira()}"
    except:
        return "Bandeira: —"

# -----------------------------
# Listas de botões (da planilha)
# -----------------------------
BUTTONS_LIGHTS = [
    ("Quarto",        "light.sonoff_a4400262ed"),
    ("Abajur 1",      "switch.sonoff_1000da054f"),
    ("Abajur 2",      "switch.sonoff_1001e1e063"),
    ("Cama",          "switch.sonoff_1000e52367"),
    ("Banheiro Suíte","switch.sonoff_1000e54832"),
]

BUTTONS_DEVICES = [
    ("Ar",      "climate.quarto"),
    ("Projetor","switch.sonoff_100118eb9b_1"),
    ("Ipad",    "switch.sonoff_1001e49ef2_1"),
]

BUTTONS_SCENES = [
    # nenhuma cena listada na planilha para Quarto
]

# -----------------------------
# Montagem do HTML
# -----------------------------
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
    .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; }}
    button {{ 
      display:inline-block; margin:5px; padding:8px 12px; 
      background:#000; color:#0F0; border:1px solid #0A0; 
      font-family:'VT323',monospace; cursor:pointer;
    }}
  </style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <!-- Tela de Boot MS‑DOS -->
  <div id="bootScreen" style="
    white-space: pre; color: #00FF00; font-family: 'VT323', monospace;
    background: black; padding: 20px; font-size: 1.1em;
  "></div>

  <div class="outer">
    <div class="section"><h3>Luzes</h3>
      {"".join(f'<button onclick=\"toggleEntity(\\\"{eid}\\\")\">{label}</button>' for label,eid in BUTTONS_LIGHTS)}
    </div>
    <div class="section"><h3>Dispositivos</h3>
      {"".join(f'<button onclick=\"toggleEntity(\\\"{eid}\\\")\">{label}</button>' for label,eid in BUTTONS_DEVICES)}
    </div>
    <div class="section"><h3>Cenas</h3>
      {"".join(f'<button onclick=\"toggleEntity(\\\"{eid}\\\")\">{label}</button>' for label,eid in BUTTONS_SCENES)}
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>{get_clima()}</p>
      <p>{get_agenda()}</p>
      <p>{get_speed()}</p>
      <p>{feriado_text}</p>
      <p>{get_filtro()}</p>
      <p>{get_bandeira_text()}</p>
    </div>
  </div>

  <script>
    // Funções de Boot MS‑DOS (do seu boot.txt)
    const bootLines = [
      "Phoenix Technologies Ltd.  Version 4.06",
      "Copyright (C) 1985-2001, Phoenix Technologies Ltd.",
      "",
      "Intel(R) Pentium(R) III CPU 1133MHz",
      "Memory Testing: 524288K OK",
      "",
      "Primary Master: ST380021A  3.18",
      "Primary Slave:  CD-ROM 52X",
      "Secondary Master: None",
      "Secondary Slave: None",
      "",
      "Keyboard Detected: USB Keyboard",
      "Mouse Initialized: PS/2 Compatible",
      "",
      "Press DEL to enter Setup",
      "",
      "Loading DOS...",
      "Starting Smart Panel Interface..."
    ];
    let lineIndex = 0;
    function showNextLine() {
      const el = document.getElementById('bootScreen');
      if (lineIndex < bootLines.length) {
        el.innerText += bootLines[lineIndex++] + "\\n";
        setTimeout(showNextLine, 300);
      } else {
        setTimeout(() => {
          el.style.display = "none";
          document.querySelector('.outer').style.display = "block";
        }, 1000);
      }
    }

    // Toggle REST para Home Assistant
    function toggleEntity(entity_id) {
      new Audio('assets/sons/on.mp3').play();
      fetch(`${HA_URL}/api/services/homeassistant/toggle`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${HA_TOKEN}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ entity_id })
      });
    }

    document.addEventListener('DOMContentLoaded', () => {
      document.getElementById('bootSound').play();
      showNextLine();
    });
  </script>
</body>
</html>
"""

# Grava no docs/index.html
os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
