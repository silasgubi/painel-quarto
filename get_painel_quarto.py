#!/usr/bin/env python3
# get_painel_quarto.py

import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# ─── 1) BOTÕES: substitua pelos seus labels e entity_ids ──────────────────
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

# ─── 3) Datas e horas ────────────────────────────────────────────────────
now = datetime.now()
data_hoje = now.strftime("%d/%m/%Y")
hora_hoje = now.strftime("%H:%M")

# ─── 4) Feriados SP ──────────────────────────────────────────────────────
br_holidays = holidays.Brazil(prov="SP")
feriado = br_holidays.get(now.date())
if feriado:
    feriado_text = "Hoje é feriado: " + feriado
else:
    futuros = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if futuros:
        pd = futuros[0]
        feriado_text = "Próximo feriado: {} em {}".format(br_holidays[pd], pd.strftime("%d/%m/%Y"))
    else:
        feriado_text = "Não há mais feriados este ano"

# ─── 5) Clima do quarto via HA ───────────────────────────────────────────
HA_URL   = os.environ.get("HA_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

def get_clima_quarto():
    try:
        resp = requests.get(
            HA_URL + "/api/states/climate.quarto",
            headers={"Authorization": "Bearer " + HA_TOKEN, "Content-Type": "application/json"}
        ).json()
        temp = resp.get("state", "—")
        hum  = resp.get("attributes", {}).get("current_humidity", "—")
        return "{} {} — {}°C / {}%".format(data_hoje, hora_hoje, temp, hum)
    except:
        return "Clima quarto indisponível"

# ─── 6) Agenda via Google Calendar ──────────────────────────────────────
def get_agenda():
    if HAS_GOOGLE and CALENDAR_ID:
        tmin = now.isoformat() + "Z"
        tmax = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        try:
            evs = service.events().list(
                calendarId=CALENDAR_ID, timeMin=tmin, timeMax=tmax,
                singleEvents=True, orderBy="startTime"
            ).execute().get("items", [])
            if not evs:
                return "Compromissos: Nenhum"
            lst = []
            for e in evs:
                st = e["start"].get("dateTime", e["start"].get("date"))
                t = st.split("T")[1][:5] if "T" in st else st
                lst.append(t + " – " + e.get("summary","Sem título"))
            return "Compromissos:<br>" + "<br>".join(lst)
        except:
            return "Agenda indisponível"
    return "Compromissos: Nenhum"

# ─── 7) Velocidade de Internet ──────────────────────────────────────────
def get_speed():
    try:
        st = speedtest.Speedtest(); st.get_best_server()
        down = int(st.download()/1_000_000); up = int(st.upload()/1_000_000)
        return "Velocidade: {} ↓ / {} ↑".format(down, up)
    except:
        return "Velocidade: Offline"

# ─── 8) Filtro do Ar ────────────────────────────────────────────────────
def get_filtro():
    try:
        r = requests.get(
            HA_URL + "/api/states/binary_sensor.quarto_filter_clean_required",
            headers={"Authorization": "Bearer " + HA_TOKEN, "Content-Type": "application/json"}
        ).json()
        return "Limpeza: 🚩" if r.get("state") == "on" else "Limpeza: OK"
    except:
        return "Limpeza: —"

# ─── 9) Bandeira Tarifária ──────────────────────────────────────────────
def get_bandeira():
    try:
        return "Bandeira: " + fetch_bandeira()
    except:
        return "Bandeira: —"

# ─── 10) HTML final ─────────────────────────────────────────────────────
html = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel Quarto — %s %s</title>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
body {margin:0; background:#000; color:#0F0; font-family:'VT323',monospace;}
.outer {border:2px solid #0A0; max-width:800px; margin:10px auto; padding:10px; display:none;}
.section {border:1px solid #0A0; padding:10px; margin-top:10px;}
.section h3 {margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase;}
button {display:inline-block; margin:5px; padding:8px 12px;
        background:#000; color:#0F0; border:1px solid #0A0;
        font-family:'VT323',monospace; cursor:pointer;}
</style></head><body>
<audio id="bootSound" src="assets/sons/boot.mp3"></audio>
<div id="bootScreen" style="white-space:pre; color:#0F0; font-family:'VT323',monospace; background:#000; padding:20px; font-size:1.1em;"></div>
<div class="outer">
  <div class="section"><h3>Luzes</h3>%s</div>
  <div class="section"><h3>Dispositivos</h3>%s</div>
  <div class="section"><h3>Cenas</h3>%s</div>
  <div class="section"><h3>Agenda</h3>
    <p>Data: %s</p><p>Hora: %s</p><p>%s</p><p>%s</p>
  </div>
  <div class="section"><h3>Tempo</h3>
    <p>%s</p><p>%s</p>
  </div>
  <div class="section"><h3>Sistema</h3>
    <p>%s</p><p>%s</p><p>%s</p><p>%s</p>
  </div>
</div>
<script>
var HA_URL="%s",HA_TOKEN="%s";
var bootLines=[ "Phoenix Technologies Ltd. Version 4.06",
"Copyright (C) 1985-2001, Phoenix Technologies Ltd.","",
"Intel(R) Pentium(R) III CPU 1133MHz","Memory Testing: 524288K OK","",
"Primary Master: ST380021A  3.18","Primary Slave:  CD-ROM 52X",
"Secondary Master: None","Secondary Slave: None","","Keyboard Detected: USB Keyboard",
"Mouse Initialized: PS/2 Compatible","","Press DEL to enter Setup","","Loading DOS...",
"Starting Smart Panel Interface..." ];
var i=0;
function showNextLine(){
  var el=document.getElementById("bootScreen");
  if(i<bootLines.length){
    el.innerText+=bootLines[i++]+"\\n";
    setTimeout(showNextLine,300);
  } else {
    setTimeout(function(){
      el.style.display="none";
      document.querySelector(".outer").style.display="block";
    },800);
  }
}
function toggleEntity(eid){
  new Audio("assets/sons/on.mp3").play();
  var xhr=new XMLHttpRequest();
  xhr.open("POST",HA_URL+"/api/services/homeassistant/toggle",true);
  xhr.setRequestHeader("Authorization","Bearer "+HA_TOKEN);
  xhr.setRequestHeader("Content-Type","application/json");
  xhr.send(JSON.stringify({entity_id: eid}));
}
document.addEventListener("DOMContentLoaded",function(){
  document.getElementById("bootSound").play();
  showNextLine();
});
</script></body></html>
""" % (
    # título
    data_hoje, hora_hoje,
    # botões
    "".join('<button onclick="toggleEntity(\'%s\')">%s</button>'%(eid,label) for label,eid in BUTTONS_LIGHTS),
    "".join('<button onclick="toggleEntity(\'%s\')">%s</button>'%(eid,label) for label,eid in BUTTONS_DEVICES),
    "".join('<button onclick="toggleEntity(\'%s\')">%s</button>'%(eid,label) for label,eid in BUTTONS_SCENES),
    # agenda
    data_hoje, hora_hoje, feriado_text, get_agenda(),
    # tempo (atual + previsão mínima, máxima e chuva via wttr.in)
    requests.get("https://wttr.in/Sao+Paulo?format=☁️ %C %t&lang=pt&m").text + " Humidity " +
      requests.get("https://wttr.in/Sao+Paulo?format=%h&lang=pt").text,
    "Previsão: Min: "+requests.get("https://wttr.in/Sao+Paulo?format=%l&lang=pt").text+
      " Max: "+requests.get("https://wttr.in/Sao+Paulo?format=%M&lang=pt").text+
      " Chuva: "+requests.get("https://wttr.in/Sao+Paulo?format=%p&lang=pt").text+"mm",
    # sistema
    get_clima_quarto(), get_speed(), get_filtro(), get_bandeira(),
    # XHR toggle
    HA_URL, HA_TOKEN
)

# ─── 11) Grava em docs/index.html ────────────────────────────────────────
os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
