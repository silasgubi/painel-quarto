#!/usr/bin/env python3
import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira   # importe o bandeira.py

# ─── 1) BOTÕES: rótulo e entity_id conforme sua planilha ───────────────
BUTTONS_LIGHTS = [
    ("Quarto", "switch.sonoff_1001a6434"),
    ("Abajur 1", "switch.sonoff_1001e1e063"),
    ("Abajur 2", "switch.sonoff_1001e18c26"),
    ("Cama", "switch.sonoff_1001e49ef2_1"),
    ("Banheiro Suite", "switch.sonoff_1000e54832"),
]

BUTTONS_DEVICES = [
    ("Ar‑condicionado", "switch.sonoff_1000e4e667"),
    ("Projetor", "switch.sonoff_100118eb9b_1"),
    ("iPad", "switch.sonoff_1001e49ef2_2"),
]

BUTTONS_SCENES = [
    ("Vermelhas", "scene.vermelha"),
    ("Grafite",   "scene.grafite"),
    ("Aconchegante", "scene.aconchegante"),
    ("Banheiro",  "scene.banheiro"),
]

# ─── 2) Google Calendar (opcional) ─────────────────────────────────────
HAS_GOOGLE = False
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    pass

CALENDAR_ID = os.environ.get("CALENDAR_ID", "")
if HAS_GOOGLE and CALENDAR_ID:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(creds_json)
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

# ─── 3) Data e hora ──────────────────────────────────────────────────────
now = datetime.now()
data_hoje = now.strftime("%d/%m/%Y")
hora_hoje = now.strftime("%H:%M")

# ─── 4) Feriados SP ──────────────────────────────────────────────────────
br_holidays = holidays.Brazil(prov="SP")
feriado = br_holidays.get(now.date())
if feriado:
    feriado_text = f"Hoje é feriado: {feriado}"
else:
    futuros = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if futuros:
        pd = futuros[0]
        feriado_text = f"Próximo feriado: {br_holidays[pd]} em {pd.strftime('%d/%m/%Y')}"
    else:
        feriado_text = "Não há mais feriados este ano"

# ─── 5) Clima do quarto via REST HA ─────────────────────────────────────
HA_URL   = os.environ.get("HA_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

def get_clima_quarto():
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/climate.quarto",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=10
        ).json()
        temp = resp.get("state", "—")
        hum  = resp.get("attributes", {}).get("current_humidity", "—")
        return f"{data_hoje} {hora_hoje} — {temp}°C / {hum}%"
    except:
        return "Clima indisponível"

# ─── 6) Agenda via Google Calendar ──────────────────────────────────────
def get_agenda():
    if HAS_GOOGLE and CALENDAR_ID:
        time_min = now.isoformat() + "Z"
        time_max = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        try:
            events = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute().get("items", [])
            if not events:
                return "Compromissos: Nenhum"
            lines = []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                t = start.split("T")[1][:5] if "T" in start else start
                lines.append(f"{t} – {ev.get('summary','Sem título')}")
            return "Compromissos:<br>" + "<br>".join(lines)
        except:
            return "Agenda indisponível"
    return "Compromissos: Nenhum"

# ─── 7) Velocidade de Internet ──────────────────────────────────────────
def get_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        down = int(st.download() / 1_000_000)
        up   = int(st.upload()   / 1_000_000)
        return f"Velocidade: {down} ↓ / {up} ↑"
    except:
        return "Velocidade: Offline"

# ─── 8) Filtro do Ar ────────────────────────────────────────────────────
def get_filtro():
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=10
        ).json()
        return "Limpeza: 🚩" if resp.get("state") == "on" else "Limpeza: OK"
    except:
        return "Limpeza: —"

# ─── 9) Bandeira Tarifária ──────────────────────────────────────────────
def get_bandeira():
    try:
        return f"Bandeira: {fetch_bandeira()}"
    except:
        return "Bandeira: —"

# ─── 10) Tempo Atual e Previsão (via wttr.in) ──────────────────────────
def get_tempo_atual():
    try:
        return requests.get(
            "https://wttr.in/Sao+Paulo?format=São+Paulo:+%c+%C+%t+%h&lang=pt",
            timeout=10
        ).text
    except:
        return "Tempo indisponível"

def get_previsao():
    try:
        return requests.get(
            "https://wttr.in/Sao+Paulo?format=Previsão:+%c+Min+%m+Max+%M+Chuva+%p&lang=pt",
            timeout=10
        ).text
    except:
        return "Previsão indisponível"

# ─── 11) Monta o HTML com boot, botões e todos os blocos ──────────────
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto — {data_hoje} {hora_hoje}</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }}
    .outer {{ border:2px solid #0A0; max-width:800px; margin:10px auto; padding:10px; display:none; }}
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

  <!-- Boot MS‑DOS -->
  <div id="bootScreen" style="
    white-space: pre; color:#0F0; font-family:'VT323',monospace;
    background:#000; padding:20px; font-size:1.1em;
  "></div>

  <div class="outer">
    <div class="section"><h3>Luzes</h3>
      {"".join(f'<button onclick="toggleEntity(\\'{eid}\\')">{label}</button>' for label,eid in BUTTONS_LIGHTS)}
    </div>
    <div class="section"><h3>Dispositivos</h3>
      {"".join(f'<button onclick="toggleEntity(\\'{eid}\\')">{label}</button>' for label,eid in BUTTONS_DEVICES)}
    </div>
    <div class="section"><h3>Cenas</h3>
      {"".join(f'<button onclick="toggleEntity(\\'{eid}\\')">{label}</button>' for label,eid in BUTTONS_SCENES)}
    </div>
    <div class="section"><h3>Agenda</h3>
      <p>{data_hoje} {hora_hoje}</p>
      <p>{feriado_text}</p>
      <p>{get_agenda()}</p>
    </div>
    <div class="section"><h3>Tempo</h3>
      <p>{get_tempo_atual()}</p>
      <p>{get_previsao()}</p>
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>{get_clima_quarto()}</p>
      <p>{get_speed()}</p>
      <p>{get_filtro()}</p>
      <p>{get_bandeira()}</p>
    </div>
  </div>

  <script>
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
    let idx = 0;
    function showNext() {
      const el = document.getElementById('bootScreen');
      if (idx < bootLines.length) {
        el.innerText += bootLines[idx++] + "\\n";
        setTimeout(showNext, 300);
      } else {
        setTimeout(() => {
          el.style.display = "none";
          document.querySelector('.outer').style.display = "block";
        }, 1000);
      }
    }

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
      showNext();
    });
  </script>
</body>
</html>
"""

# salva em docs/index.html para o GitHub Pages
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
