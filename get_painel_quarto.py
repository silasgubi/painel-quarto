#!/usr/bin/env python3
# get_painel_quarto.py

import os
import requests
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# ─── 1) BOTÕES: ajuste os seus pares (rótulo, entity_id)
BUTTONS_LIGHTS = [
    ("Quarto",        "light.sonoff_a440020ad4"),
    ("Abajur 1",      "light.sonoff_a440022ce9"),
    ("Abajur 2",      "light.sonoff_a440031777"),
    ("Cama",          "light.sonoff_1000d6bdb1"),
    ("Banheiro Suite","light.sonoff_1000d6bdb2"),
]
BUTTONS_DEVICES = [
    ("Ventilador",    "switch.sonoff_1000e5465f"),
    ("Projetor",      "switch.sonoff_1000c43d82"),
    ("iPad",          "switch.sonoff_1000f541f7_1"),
]
BUTTONS_SCENES = [
    ("Vermelhas",     "scene.vermelhas"),
    ("Grafite",       "scene.grafite"),
    ("Aconchegante",  "scene.aconchegante"),
    ("Banheiro",      "scene.banheiro"),
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
data_hoje = now.strftime("%d/%m/%Y")
hora_hoje = now.strftime("%H:%M")

# ─── 4) Feriados SP
br_holidays = holidays.Brazil(prov="SP")
feriado = br_holidays.get(now.date())
if feriado:
    feriado_text = "Hoje é feriado: " + feriado
else:
    futuros = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if futuros:
        pd = futuros[0]
        feriado_text = (
            "Próximo feriado: {} em {}".format(br_holidays[pd], pd.strftime("%d/%m/%Y"))
        )
    else:
        feriado_text = "Não há mais feriados este ano"

# ─── 5) Clima do quarto via HA
HA_URL   = os.environ.get("HA_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

def get_clima_quarto():
    try:
        r = requests.get(
            HA_URL + "/api/states/climate.quarto",
            headers={
                "Authorization": "Bearer " + HA_TOKEN,
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        temp = r.get("state", "—")
        hum  = r.get("attributes", {}).get("current_humidity", "—")
        return "{} {} — {}°C / {}%".format(data_hoje, hora_hoje, temp, hum)
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
                timeMin=tmin,
                timeMax=tmax,
                singleEvents=True,
                orderBy="startTime"
            ).execute().get("items", [])
            if not evs:
                return "Compromissos: Nenhum"
            lst = []
            for e in evs:
                st = e["start"].get("dateTime", e["start"].get("date"))
                t  = st.split("T")[1][:5] if "T" in st else st
                lst.append(t + " – " + e.get("summary","Sem título"))
            return "Compromissos:<br>" + "<br>".join(lst)
        except:
            return "Agenda indisponível"
    return "Compromissos: Nenhum"

# ─── 7) **REMOVIDO** speedtest para não travar o CI
def get_speed():
    return "Velocidade: —"  # placeholder

# ─── 8) Filtro do Ar
def get_filtro():
    try:
        r = requests.get(
            HA_URL + "/api/states/binary_sensor.quarto_filter_clean_required",
            headers={
                "Authorization": "Bearer " + HA_TOKEN,
                "Content-Type": "application/json"
            },
            timeout=5
        ).json()
        return "Limpeza: 🚩" if r.get("state")=="on" else "Limpeza: OK"
    except:
        return "Limpeza: —"

# ─── 9) Bandeira Tarifária
def get_bandeira():
    try:
        return "Bandeira: " + fetch_bandeira()
    except:
        return "Bandeira: —"

# ─── 10) HTML final (todos os requests com timeout=5s)
#      wttr.in para tempo atual e previsão
try:
    tempo_atual = requests.get(
        "https://wttr.in/Sao+Paulo?format=☁️ %C %t&lang=pt&m", timeout=5
    ).text + " Humidity " + requests.get(
        "https://wttr.in/Sao+Paulo?format=%h&lang=pt", timeout=5
    ).text
    previsao = "Min: " + requests.get(
        "https://wttr.in/Sao+Paulo?format=%l&lang=pt", timeout=5
    ).text + " Max: " + requests.get(
        "https://wttr.in/Sao+Paulo?format=%M&lang=pt", timeout=5
    ).text + " Chuva: " + requests.get(
        "https://wttr.in/Sao+Paulo?format=%p&lang=pt", timeout=5
    ).text + "mm"
except:
    tempo_atual = "Tempo indisponível"
    previsao    = ""

html = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel Quarto — {data} {hora}</title>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
body {{margin:0; background:#000; color:#0F0; font-family:'VT323',monospace}}
.outer {{border:2px solid #0A0; max-width:800px; margin:10px auto; padding:10px; display:none}}
.section {{border:1px solid #0A0; padding:10px; margin-top:10px}}
.section h3 {{margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase}}
button {{display:inline-block; margin:5px; padding:8px 12px;
         background:#000; color:#0F0; border:1px solid #0A0;
         font-family:'VT323',monospace; cursor:pointer}}
</style></head><body>
<audio id="bootSound" src="assets/sons/boot.mp3"></audio>
<div id="bootScreen" style="white-space:pre;color:#0F0;background:#000;padding:20px;font-size:1.1em;"></div>
<div class="outer">
  <div class="section"><h3>Luzes</h3>{bot_luz}</div>
  <div class="section"><h3>Dispositivos</h3>{bot_dev}</div>
  <div class="section"><h3>Cenas</h3>{bot_scn}</div>
  <div class="section"><h3>Agenda</h3>
    <p>Data: {data}</p><p>Hora: {hora}</p>
    <p>{feriado}</p><p>{agenda}</p>
  </div>
  <div class="section"><h3>Tempo</h3>
    <p>{tempo_atual}</p><p>{previsao}</p>
  </div>
  <div class="section"><h3>Sistema</h3>
    <p>{clima}</p><p>{speed}</p>
    <p>{filtro}</p><p>{bandeira}</p>
  </div>
</div>
<script>
var HA_URL="{ha_url}",HA_TOKEN="{ha_token}";
var bootLines=[ 
  "Phoenix Technologies Ltd. Version 4.06","Copyright (C) 1985-2001",
  "Intel(R) Pentium(R) III CPU 1133MHz","Memory Testing: 524288K OK",
  "Loading DOS...","Starting Smart Panel Interface..."
];
var i=0;
function showNextLine(){ 
  var el=document.getElementById("bootScreen");
  if(i<bootLines.length){ el.innerText+=bootLines[i++]+"\\n";setTimeout(showNextLine,300);}
  else{ setTimeout(function(){
    el.style.display="none";document.querySelector(".outer").style.display="block";
  },800);}
}
function toggleEntity(eid){
  new Audio("assets/sons/on.mp3").play();
  fetch(HA_URL+"/api/services/homeassistant/toggle",{
    method:"POST",
    headers:{
      "Authorization":"Bearer "+HA_TOKEN,
      "Content-Type":"application/json"
    },
    body:JSON.stringify({entity_id:eid})
  });
}
document.addEventListener("DOMContentLoaded",function(){
  document.getElementById("bootSound").play();
  showNextLine();
});
</script></body></html>
""".format(
    data=data_hoje, hora=hora_hoje,
    bot_luz="".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid,label)
        for label,eid in BUTTONS_LIGHTS
    ),
    bot_dev="".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid,label)
        for label,eid in BUTTONS_DEVICES
    ),
    bot_scn="".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid,label)
        for label,eid in BUTTONS_SCENES
    ),
    feriado=feriado_text, agenda=get_agenda(),
    tempo_atual=tempo_atual, previsao=previsao,
    clima=get_clima_quarto(), speed=get_speed(),
    filtro=get_filtro(), bandeira=get_bandeira(),
    ha_url=HA_URL, ha_token=HA_TOKEN
)

# ─── 11) Escreve para o GH‑Pages ────────────────────────────────────────
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
