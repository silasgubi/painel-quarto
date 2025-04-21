#!/usr/bin/env python3
import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# ─── 1) CONFIGURE AQUI SEUS LABELS E entity_id ───────────────────────────
BUTTONS_LIGHTS = [
    ("Quarto",            "switch.sonoff_1001a6434"),
    ("Abajur 1",          "switch.sonoff_a4400262ed"),
    ("Abajur 2",          "switch.sonoff_a4400235ee"),
    ("Cama",              "switch.sonoff_a440022d3e"),
    ("Banheiro Suite",    "switch.sonoff_1000e6bdb1"),
]

BUTTONS_DEVICES = [
    ("Ar-condicionado",   "climate.ar_condicionado_quarto"),
    ("Projetor",          "switch.projetor_quarto"),
    ("iPad",              "switch.ipad_quarto"),
]

BUTTONS_SCENES = [
    ("Vermelhas",         "scene.luzes_vermelhas"),
    ("Grafite",           "scene.luzes_grafite"),
    ("Aconchegante",      "scene.luzes_aconchegante"),
    ("Banheiro",          "scene.luzes_banheiro"),
]

# ─── 2) Google Calendar (opcional) ───────────────────────────────────────
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

# ─── 3) DATAS E HORAS ─────────────────────────────────────────────────────
now = datetime.now()
data_hoje = now.strftime("%d/%m/%Y")
hora_hoje = now.strftime("%H:%M")

# ─── 4) FERIADOS SP ──────────────────────────────────────────────────────
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

# ─── 5) CLIMA ATUAL via WTTR.IN (com ícone e condição) ───────────────────
def get_tempo_atual():
    try:
        txt = requests.get(
            "https://wttr.in/Sao+Paulo?format=%c+%C+%t&lang=pt&m",
            timeout=5
        ).text
        # Humidity: usar WTTR? fallback:
        # aqui só exibimos o texto retornado
        return txt
    except:
        return "Tempo indisponível"

# ─── 6) PREVISÃO via WTTR.IN (mín/max/chuva) ─────────────────────────────
def get_previsao():
    try:
        txt = requests.get(
            "https://wttr.in/Sao+Paulo?format=Min:+%m+Max:+%M+Chuva:+%p&lang=pt&m",
            timeout=5
        ).text
        return txt
    except:
        return "Previsão indisponível"

# ─── 7) CLIMA DO QUARTO via REST do HA ──────────────────────────────────
HA_URL   = os.environ.get("HA_URL", "").rstrip('/')
HA_TOKEN = os.environ.get("HA_TOKEN", "")

def get_clima_quarto():
    try:
        # sensor de temperatura e umidade (ajuste para seus entity_id)
        t = requests.get(f"{HA_URL}/api/states/sensor.quarto_temperature",
                         headers={"Authorization":f"Bearer {HA_TOKEN}","Content-Type":"application/json"}).json().get("state", "—")
        h = requests.get(f"{HA_URL}/api/states/sensor.quarto_humidity",
                         headers={"Authorization":f"Bearer {HA_TOKEN}","Content-Type":"application/json"}).json().get("state", "—")
        return f"{data_hoje} {hora_hoje} — {t}°C / {h}%"
    except:
        return "Clima quarto indisponível"

# ─── 8) AGENDA via Google Calendar ───────────────────────────────────────
def get_agenda():
    if HAS_GOOGLE and CALENDAR_ID:
        time_min = now.isoformat() + "Z"
        time_max = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        try:
            evs = service.events().list(
                calendarId=CALENDAR_ID, timeMin=time_min,
                timeMax=time_max, singleEvents=True,
                orderBy="startTime"
            ).execute().get("items", [])
            if not evs:
                return "Compromissos: Nenhum"
            lines = []
            for ev in evs:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                t = start.split("T")[1][:5] if "T" in start else start
                lines.append(f"{t} – {ev.get('summary','Sem título')}")
            return "Compromissos:<br>" + "<br>".join(lines)
        except:
            return "Agenda indisponível"
    return "Compromissos: Nenhum"

# ─── 9) VELOCIDADE DE INTERNET ────────────────────────────────────────────
def get_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        down = int(st.download()/1_000_000)
        up   = int(st.upload()/1_000_000)
        return f"Velocidade: {down} ↓ / {up} ↑"
    except:
        return "Velocidade: offline"

# ───10) FILTRO DE AR ─────────────────────────────────────────────────────
def get_filtro():
    try:
        st = requests.get(
            f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
            headers={"Authorization":f"Bearer {HA_TOKEN}","Content-Type":"application/json"}
        ).json()
        return "Limpeza: 🚩" if st.get("state")=="on" else "Limpeza: OK"
    except:
        return "Limpeza: —"

# ───11) BANDEIRA ANEEL ───────────────────────────────────────────────────
def get_bandeira():
    try:
        return f"Bandeira: {fetch_bandeira()}"
    except:
        return "Bandeira: —"

# ───12) MONTA O HTML ─────────────────────────────────────────────────────
buttons_html = lambda lst: "".join(
    f'<button onclick="toggleEntity(\\\'{eid}\\\')">{label}</button>'
    for label, eid in lst
)

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
    .section h3 {{ margin:0; border-bottom:1px dashed #0A0; text-transform:uppercase; }}
    button {{ margin:4px; padding:8px 12px; background:#000; color:#0F0; border:1px solid #0A0; cursor:pointer; }}
  </style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <!-- Boot MS‑DOS -->
  <div id="bootScreen" style="white-space:pre; color:#0F0; font-family:'VT323',monospace; background:#000; padding:20px; font-size:1.1em;"></div>
  <div class="outer">
    <div class="section"><h3>Luzes</h3>{buttons_html(BUTTONS_LIGHTS)}</div>
    <div class="section"><h3>Dispositivos</h3>{buttons_html(BUTTONS_DEVICES)}</div>
    <div class="section"><h3>Cenas</h3>{buttons_html(BUTTONS_SCENES)}</div>
    <div class="section"><h3>Agenda</h3>
      <p>Data: {data_hoje}</p>
      <p>Hora: {hora_hoje}</p>
      <p>{feriado_text}</p>
      <p>{get_agenda()}</p>
    </div>
    <div class="section"><h3>Tempo</h3>
      <p>{get_tempo_atual()}</p>
      <p>Previsão: {get_previsao()}</p>
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>{get_clima_quarto()}</p>
      <p>{get_speed()}</p>
      <p>{get_filtro()}</p>
      <p>{get_bandeira()}</p>
    </div>
  </div>
  <script>
    const HA_URL   = "{HA_URL}";
    const HA_TOKEN = "{HA_TOKEN}";
    const bootLines = [
      "Phoenix Technologies Ltd.  Version 4.06",
      "Copyright (C) 1985-2001, Phoenix Technologies Ltd.",
      "",
      "Loading DOS...",
      "Starting Smart Panel Interface..."
    ];
    let i=0;
    function showNextLine() {{
      const el = document.getElementById("bootScreen");
      if(i<bootLines.length) {{
        el.innerText += bootLines[i++] + "\\n";
        setTimeout(showNextLine, 300);
      }} else {{
        setTimeout(()=>{{ el.style.display="none"; document.querySelector(".outer").style.display="block"; }}, 800);
      }}
    }}
    function toggleEntity(entity_id) {{
      new Audio("assets/sons/on.mp3").play();
      fetch(`${{HA_URL}}/api/services/homeassistant/toggle`, {{
        method:"POST",
        headers:{{
          "Authorization":`Bearer ${{HA_TOKEN}}`,
          "Content-Type":"application/json"
        }},
        body: JSON.stringify({{ entity_id }})
      }});
    }}
    document.addEventListener("DOMContentLoaded",()=>{{ 
      document.getElementById("bootSound").play();
      showNextLine();
    }});
  </script>
</body>
</html>
"""

# ───13) SALVA index.html na raiz, será movido para /docs ─────────────────
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
