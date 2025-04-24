#!/usr/bin/env python3
import os
import requests
import speedtest
import holidays
from datetime import datetime
from bandeira import fetch_bandeira
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ─── CONFIGURAÇÃO ──────────────────────────────────────────────────────────
HA_URL       = os.getenv("HA_URL")
HA_TOKEN     = os.getenv("HA_TOKEN")
CALENDAR_ID  = os.getenv("CALENDAR_ID")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDENTIALS")

# ─── BOTÕES (substitua pelos seus labels, entity_ids e nome do arquivo de ícone) ──
BUTTONS_LIGHTS = [
    ("Quarto",           "light.sonoff_1000ea5c7af",      "luz_0n.svg"),
    ("Abajur 1",         "light.sonoff_1000ec2a21",      "abajur_on.svg"),
    ("Abajur 2",         "light.sonoff_1000ef8557",      "abajur_on.svg"),
    ("Cama",             "light.sonoff_1000e52367",      "cama_on.svg"),
    ("Banheiro Suite",   "light.sonoff_1000e5465f",      "banheiro_on.svg"),
]

BUTTONS_DEVICES = [
    ("Ar‑condicionado",  "climate.quarto",               "ar_on.svg"),
    ("Projetor",         "switch.sonoff_1000bdffc5",     "usb_on.svg"),
    ("iPad",             "switch.sonoff_1000ef1234",     "usb_on.svg"),
]

BUTTONS_SCENES = [
    ("Vermelhas",        "scene.luzes_vermelhas",        "vermelhas_vermelhas.svg"),
    ("Grafite",          "scene.luzes_grafite",          "grafite.svg"),
    ("zzZZzz",     "scene.luzes_aconchegantes",    "aconchegante.svg"),
    ("Banheiro",         "scene.luzes_banheiro",         "banheiro.svg"),
]

# ─── DADOS DINÂMICOS ────────────────────────────────────────────────────────
now        = datetime.now()
data_hoje  = now.strftime("%d/%m/%Y")
hora_hoje  = now.strftime("%H:%M")
br_holidays= holidays.Brazil(prov="SP")
feriado    = br_holidays.get(now.date())
feriado_text = feriado if feriado else "Nenhum"

# Clima atual do quarto (via HA)
def get_clima_quarto():
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/climate.quarto",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        t = resp.get("attributes", {}).get("current_temperature", "—")
        h = resp.get("attributes", {}).get("current_humidity", "—")
        return f"{t}°C / {h}%"
    except:
        return "—"
clima_quarto = get_clima_quarto()

# Velocidade da internet
def get_speed():
    try:
        st   = speedtest.Speedtest()
        st.get_best_server()
        down = int(st.download()/1_000_000)
        up   = int(st.upload()/1_000_000)
        return f"{down} ↓ / {up} ↑"
    except:
        return "—"
internet_text = get_speed()

# Limpeza filtros ar
def get_limpeza():
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        return "❌ ☣️" if resp.get("state")=="on" else "✅"
    except:
        return "—"
limpeza_text = get_limpeza()

# Bandeira tarifária
bandeira_text = fetch_bandeira()

# Agenda no Google Calendar
with open("service_account.json","w",encoding="utf-8") as f:
    f.write(GOOGLE_CREDS)
creds   = Credentials.from_service_account_file("service_account.json",
                                               scopes=["https://www.googleapis.com/auth/calendar.readonly"])
service = build("calendar","v3",credentials=creds)
time_min = now.isoformat()+"Z"
time_max = now.replace(hour=23,minute=59,second=59).isoformat()+"Z"
events  = service.events().list(
    calendarId=CALENDAR_ID,
    timeMin=time_min,
    timeMax=time_max,
    singleEvents=True,
    orderBy="startTime"
).execute().get("items",[])
if events:
    compromissos = "<br>".join(
        f"{e['start'].get('dateTime',e['start'].get('date')).split('T')[-1][:5]} – {e.get('summary','Sem título')}"
        for e in events
    )
else:
    compromissos = "Nenhum"

# ─── GERAÇÃO DO HTML ────────────────────────────────────────────────────────
def render_buttons(lst):
    return "\n".join(
        f"<button onclick=\"toggleEntity('{eid}')\">"
        f"<img src=\"assets/icones/{icon}\" alt=\"{label}\"><span>{label}</span>"
        "</button>"
        for label,eid,icon in lst
    )

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{
      margin:0;
      background:#000;
      color:#0f0;
      font-family:'VT323',monospace;
      display: flex;
      justify-content: center;
      }}
    .outer {{
      border:2px solid #39FF14;  /* borda externa */
      max-width:700px;
      margin:10px auto;
      padding:10px;
      box-sizing: border-box;
      background: #111;
      }}
    .section {{
      border:1px solid #39FF14; /* bordas das seções */
      margin-top:10px;
      padding:10px;
      }}
    .section h3 {{
      margin:0 0 10px;
      text-transform:uppercase;
      font-size: 1em;
      letter-spacing: 1px;
      border-bottom: 1px dashed #39FF14; /* título da seção */
      padding-bottom: 5px;
      opacity: 0.8;
      }}
    .grid {{
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      }}
    button {{
      background: #222;
      border: 1px solid #39FF14; /* borda dos botões */
      border-radius: 5px;
      width: 60px;
      height: 60px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.1s, background 0.2s;
      }}
    button img {{width:24px;
      height:24px;
      display:block;
      margin:0 auto 4px;
      filter:invert(100%);
    }}
     .btn span {{
      font-size: 0.75em; 
      color: #0f0; 
      font-weight: bold;
      margin-top: -3px;
    .info p {{
      margin:4px 0;
      }}
  </style>
</head>
<body>

  <!-- SEÇÃO LUZES -->
  <div class="outer">
    <div class="section">
      <h3>Luzes</h3>
      <div class="grid">
        {render_buttons(BUTTONS_LIGHTS)}
      </div>
    </div>

    <!-- SEÇÃO DISPOSITIVOS -->
    <div class="section">
      <h3>Dispositivos</h3>
      <div class="grid">
        {render_buttons(BUTTONS_DEVICES)}
      </div>
    </div>

    <!-- SEÇÃO CENAS -->
    <div class="section">
      <h3>Cenas</h3>
      <div class="grid">
        {render_buttons(BUTTONS_SCENES)}
      </div>
    </div>

    <!-- SEÇÃO AGENDA -->
    <div class="section" id="agenda">
      <h3>Agenda</h3>
      <p>Data/Hora: <span id="dt">{data_hoje} {hora_hoje}</span></p>
      <p>Feriado: {feriado_text}</p>
      <p>Compromissos:<br>{compromissos}</p>
    </div>

    <!-- SEÇÃO TEMPO -->
    <div class="section">
      <h3>Tempo</h3>
      <p>{requests.get("https://wttr.in/Sao+Paulo?format=%l|%c|%C|🌡️%t|💧%h|🌬️%w|💦%p&lang=pt&m").text}</p>
    </div>

    <!-- SEÇÃO SISTEMA -->
    <div class="section">
      <h3>Sistema</h3>
      <div class="info">
        <p>⚡Bandeira Tarifária⚡: {bandeira_text}</p>
        <p>🚀Velocidade da Internet🚀: {internet_text}</p>
        <p>❄️Climatização do Quarto💨: {clima_quarto}</p>
        <p>🧽Limpeza dos Filtros do Ar‑condicionado🧽: {limpeza_text}</p>
      </div>
    </div>
  </div>

  <script>
    const HA_URL   = "{HA_URL}";
    const HA_TOKEN = "{HA_TOKEN}";

    function toggleEntity(entity) {{
      fetch(`${{HA_URL}}/api/services/homeassistant/toggle`, {{
        method: "POST",
        headers: {{
          "Authorization": `Bearer ${{HA_TOKEN}}`,
          "Content-Type": "application/json"
        }},
        body: JSON.stringify({{entity_id: entity}})
      }});
    }}

    function atualizaDateTime() {{
      const now = new Date();
      const dt  = now.toLocaleDateString("pt-BR",{{day:"2-digit",month:"2-digit",year:"numeric"}}) 
                  + " " 
                  + now.toLocaleTimeString("pt-BR",{{hour:"2-digit",minute:"2-digit"}});
      document.getElementById("dt").innerText = dt;
    }}
    setInterval(atualizaDateTime,60000);
    document.addEventListener("DOMContentLoaded",atualizaDateTime);
  </script>
</body>
</html>
"""

os.makedirs("docs", exist_ok=True)
with open("docs/index.html","w",encoding="utf-8") as f:
    f.write(html)
