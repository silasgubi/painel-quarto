#!/usr/bin/env python3
# get_painel_quarto.py

import os
import requests
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# ─── 1) BOTÕES: ajuste seus (rótulo, entity_id) conforme sua planilha
BUTTONS_LIGHTS = [
    ("Quarto",        "light.sonoff_a440020ad4"),
    ("Abajur 1",      "light.sonoff_a440022ce9"),
    ("Abajur 2",      "light.sonoff_a440031777"),
    ("Cama",          "light.sonoff_1000d6bdb1"),
    ("Banheiro Suite","light.sonoff_1000d6bdb2"),
]
BUTTONS_DEVICES = [
    ("Ventilador", "switch.sonoff_1000e5465f"),
    ("Projetor",   "switch.sonoff_1000c43d82"),
    ("iPad",       "switch.sonoff_1000f541f7_1"),
]
BUTTONS_SCENES = [
    ("Vermelhas",    "scene.vermelhas"),
    ("Grafite",      "scene.grafite"),
    ("Aconchegante", "scene.aconchegante"),
    ("Banheiro",     "scene.banheiro"),
]

# ─── 2) Google Calendar (opcional)
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

# ─── 3) Datas e horas
now = datetime.now()
DATA = now.strftime("%d/%m/%Y")
HORA = now.strftime("%H:%M")

# ─── 4) Feriados SP
br_holidays = holidays.Brazil(prov="SP")
hoje_feriado = br_holidays.get(now.date())
if hoje_feriado:
    FERIDO_TEXT = f"Hoje é feriado: {hoje_feriado}"
else:
    proximos = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if proximos:
        pd = proximos[0]
        FERIDO_TEXT = f"Próximo feriado: {br_holidays[pd]} em {pd.strftime('%d/%m/%Y')}"
    else:
        FERIDO_TEXT = "Não há mais feriados este ano"

# ─── 5) Clima do quarto via Home Assistant
HA_URL   = os.environ.get("HA_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

def get_clima_quarto():
    try:
        r = requests.get(
            f"{HA_URL}/api/states/climate.quarto",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        temp = r.get("state", "—")
        hum  = r.get("attributes", {}).get("current_humidity", "—")
        return f"{DATA} {HORA} — {temp}°C / {hum}%"
    except:
        return "Clima quarto indisponível"

# ─── 6) Agenda via Google Calendar
def get_agenda():
    if HAS_GOOGLE and CALENDAR_ID:
        tmin = now.isoformat() + "Z"
        tmax = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        try:
            evs = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=tmin, timeMax=tmax,
                singleEvents=True, orderBy="startTime"
            ).execute().get("items", [])
            if not evs:
                return "Compromissos: Nenhum"
            lines = []
            for e in evs:
                st = e["start"].get("dateTime", e["start"].get("date"))
                t  = st.split("T")[1][:5] if "T" in st else st
                lines.append(f"{t} – {e.get('summary','Sem título')}")
            return "Compromissos:<br>" + "<br>".join(lines)
        except:
            return "Agenda indisponível"
    return "Compromissos: Nenhum"

# ─── 7) Speedtest removido para CI não travar
def get_speed():
    return "Velocidade: —"

# ─── 8) Filtro do ar-cond.
def get_filtro():
    try:
        r = requests.get(
            f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        return "Limpeza: 🚩" if r.get("state") == "on" else "Limpeza: OK"
    except:
        return "Limpeza: —"

# ─── 9) Bandeira ANEEL
def get_bandeira():
    try:
        return "Bandeira: " + fetch_bandeira()
    except:
        return "Bandeira: —"

# ─── 10) Tempo e previsão via wttr.in (todos com timeout)
try:
    TA = requests.get(
        "https://wttr.in/Sao+Paulo?format=☁️ %C %t&lang=pt&m", timeout=5
    ).text + " Humidity " + requests.get(
        "https://wttr.in/Sao+Paulo?format=%h&lang=pt", timeout=5
    ).text
    PV = (
        "Min: " + requests.get("https://wttr.in/Sao+Paulo?format=%l&lang=pt", timeout=5).text +
        " Max: " + requests.get("https://wttr.in/Sao+Paulo?format=%M&lang=pt", timeout=5).text +
        " Chuva: " + requests.get("https://wttr.in/Sao+Paulo?format=%p&lang=pt", timeout=5).text + "mm"
    )
except:
    TA = "Tempo indisponível"
    PV = ""

# ─── 11) Template HTML com **TODOS** os {{ }} escapados
html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel Quarto — {DATA} {HORA}</title>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }}
  .outer {{ border:2px solid #0A0; max-width:800px; margin:10px auto; padding:10px; display:none; }}
  .section {{ border:1px solid #0A0; padding:10px; margin-top:10px; }}
  .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; }}
  button {{ display:inline-block; margin:5px; padding:8px 12px;
             background:#000; color:#0F0; border:1px solid #0A0;
             font-family:'VT323',monospace; cursor:pointer; }}
</style>
</head><body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <div id="bootScreen" style="white-space:pre;color:#0F0;background:#000;padding:20px;font-size:1.1em;"></div>
  <div class="outer">
    <div class="section"><h3>Luzes</h3>
      {"".join(f"<button onclick=\"toggleEntity('{eid}')\">{label}</button>"
               for label,eid in BUTTONS_LIGHTS)}
    </div>
    <div class="section"><h3>Dispositivos</h3>
      {"".join(f"<button onclick=\"toggleEntity('{eid}')\">{label}</button>"
               for label,eid in BUTTONS_DEVICES)}
    </div>
    <div class="section"><h3>Cenas</h3>
      {"".join(f"<button onclick=\"toggleEntity('{eid}')\">{label}</button>"
               for label,eid in BUTTONS_SCENES)}
    </div>
    <div class="section"><h3>Agenda</h3>
      <p>Data: {DATA}</p><p>Hora: {HORA}</p>
      <p>{FERIDO_TEXT}</p><p>{get_agenda()}</p>
    </div>
    <div class="section"><h3>Tempo</h3>
      <p>{TA}</p><p>{PV}</p>
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>{get_clima_quarto()}</p><p>{get_speed()}</p>
      <p>{get_filtro()}</p><p>{get_bandeira()}</p>
    </div>
  </div>
  <script>
    const HA_URL = "{HA_URL}", HA_TOKEN = "{HA_TOKEN}";
    const bootLines = [
      "Phoenix Technologies Ltd. Version 4.06",
      "Copyright (C) 1985-2001",
      "Intel(R) Pentium(R) III CPU 1133MHz",
      "Memory Testing: 524288K OK",
      "Loading DOS...", "Starting Smart Panel Interface..."
    ];
    let idx = 0;
    function showNextLine() {{
      const el = document.getElementById("bootScreen");
      if (idx < bootLines.length) {{
        el.innerText += bootLines[idx++] + "\\n";
        setTimeout(showNextLine, 300);
      }} else {{
        setTimeout(() => {{
          el.style.display = "none";
          document.querySelector(".outer").style.display = "block";
        }}, 800);
      }}
    }}
    function toggleEntity(eid) {{
      new Audio("assets/sons/on.mp3").play();
      fetch(`${{HA_URL}}/api/services/homeassistant/toggle`, {{
        method: "POST",
        headers: {{
          "Authorization": `Bearer ${{HA_TOKEN}}`,
          "Content-Type": "application/json"
        }},
        body: JSON.stringify({{ entity_id: eid }})
      }});
    }}
    document.addEventListener("DOMContentLoaded", () => {{
      document.getElementById("bootSound").play();
      showNextLine();
    }});
  </script>
</body></html>
"""

# ─── 12) Salva em docs/index.html para o GitHub Pages
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
