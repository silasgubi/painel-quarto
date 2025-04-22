#!/usr/bin/env python3
# get_painel_quarto.py

import os
import csv
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira

# ─── 1. CONFIGURAÇÃO DE AMBIENTE ──────────────────────────────────────────
HA_URL        = os.getenv("HA_URL")         # ex: https://seu-endereco.ui.nabu.casa
HA_TOKEN      = os.getenv("HA_TOKEN")       # usado APENAS aqui, não vai para o HTML
CALENDAR_ID   = os.getenv("CALENDAR_ID")
GOOGLE_CRED   = os.getenv("GOOGLE_CREDENTIALS")  # JSON do service account
PLANILHA_PATH = "planilha_quarto.csv"       # certifique-se de comitar esse CSV

# ─── 2. DADOS FIXOS ───────────────────────────────────────────────────────
now         = datetime.now()
data_hora   = now.strftime("%d/%m/%Y %H:%M")
data_str    = now.strftime("%d/%m/%Y")
hora_str    = now.strftime("%H:%M")

# Feriados SP
br_holidays = holidays.Brazil(prov="SP")
feriado     = br_holidays.get(now.date()) or "Nenhum"

# ─── 3. LEITURA DA PLANILHA E MONTAGEM DOS BOTÕES ────────────────────────
# Estrutura: { "Luzes":[{...}], "Dispositivos":[...], "Cenas":[...] }
botoes = {"Luzes": [], "Dispositivos": [], "Cenas": []}

with open(PLANILHA_PATH, encoding="utf-8") as fp:
    reader = csv.DictReader(fp, delimiter=";")
    for linha in reader:
        sec   = linha["Seção (Ex: Luzes, Cenas)"].strip()
        nome  = linha["Nome"].strip()
        secret= linha["Secrets no Github"].strip()
        icon  = linha["Icone"].strip()
        # recupera o ID real do webhook a partir do Secret
        hook_id = os.getenv(secret)
        if not hook_id:
            continue  # pula se o Secret não estiver definido
        url = f"{HA_URL}/api/webhook/{hook_id}"
        botoes[sec].append({
            "nome": nome,
            "icon": icon,
            "url":  url
        })

# ─── 4. CLIMA E UMIDADE DO QUARTO ────────────────────────────────────────
def get_clima_quarto():
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/climate.quarto",
            headers={"Authorization":f"Bearer {HA_TOKEN}","Content-Type":"application/json"}
        ).json()
        t = resp.get("attributes",{}).get("current_temperature","—")
        h = resp.get("attributes",{}).get("current_humidity","—")
        return f"{t}°C / {h}%"
    except:
        return "—"

clima_quarto = get_clima_quarto()

# ─── 5. VELOCIDADE DE INTERNET ────────────────────────────────────────────
try:
    st = speedtest.Speedtest(); st.get_best_server()
    down = int(st.download()/1e6); up = int(st.upload()/1e6)
    internet_text = f"{down} ↓ / {up} ↑"
except:
    internet_text = "Offline"

# ─── 6. FILTRO AR — VERIFICAÇÃO ──────────────────────────────────────────
try:
    resp = requests.get(
        f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
        headers={"Authorization":f"Bearer {HA_TOKEN}","Content-Type":"application/json"}
    ).json()
    limpeza_text = "Necessário" if resp.get("state")== "on" else "OK"
except:
    limpeza_text = "—"

# ─── 7. BANDEIRA TARIFÁRIA ────────────────────────────────────────────────
bandeira_text = fetch_bandeira()

# ─── 8. AGENDA (Google Calendar) ────────────────────────────────────────
from google.oauth2.service_account import Credentials
from googleapiclient.discovery      import build

# salva temporário JSON de credenciais
with open("service_account.json","w",encoding="utf-8") as f:
    f.write(GOOGLE_CRED)
creds   = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/calendar.readonly"])
service = build("calendar","v3",credentials=creds)
time_min = now.isoformat()+"Z"
time_max = datetime(now.year,now.month,now.day,23,59,59).isoformat()+"Z"
events = service.events().list(
    calendarId=CALENDAR_ID,
    timeMin=time_min, timeMax=time_max,
    singleEvents=True, orderBy="startTime"
).execute().get("items",[])
compromissos = events and "<br>".join(
    f"{e['start'].get('dateTime','').split('T')[-1][:5]} – {e.get('summary','')}"
    for e in events
) or "Nenhum"

# ─── 9. MONTA O HTML ────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang='pt-BR'>
<head><meta charset='UTF-8'><title>Quarto</title>
<link href='https://fonts.googleapis.com/css2?family=VT323&display=swap' rel='stylesheet'>
<style>
  body {{ margin:0;background:#000;color:#0f0;font-family:'VT323',monospace; }}
  .outer {{border:2px solid #0f0;max-width:700px;margin:10px auto;padding:10px;}}
  .section {{border:1px solid #0f0;margin-top:10px;padding:10px;}}
  .section h3 {{margin:0 0 5px;text-transform:uppercase;opacity:0.8;}}
  .grid {{display:flex;gap:8px;flex-wrap:wrap;}}
  .btn {{border:1px solid #0f0;padding:5px;cursor:pointer;}}
  .btn img {{width:32px;height:32px;}}
  .btn span {{display:block;font-size:.8em;text-align:center;}}
  .info {{margin-top:5px;}}
</style>
<script>
  function openHook(u){{ fetch(u).catch(e=>console.error(e)); }}
</script>
</head><body>
<div class='outer'>

  <!-- LUZES -->
  <div class='section'><h3>Luzes</h3><div class='grid'>"""
for b in botoes["Luzes"]:
    html += f"""
    <button class='btn' onclick="openHook('{b['url']}')">
      <img src='assets/icones/{b['icon']}' alt=''><span>{b['nome']}</span>
    </button>"""
html += """
  </div></div>

  <!-- DISPOSITIVOS -->
  <div class='section'><h3>Dispositivos</h3><div class='grid'>"""
for b in botoes["Dispositivos"]:
    html += f"""
    <button class='btn' onclick="openHook('{b['url']}')">
      <img src='assets/icones/{b['icon']}' alt=''><span>{b['nome']}</span>
    </button>"""
html += """
  </div></div>

  <!-- CENAS -->
  <div class='section'><h3>Cenas</h3><div class='grid'>"""
for b in botoes["Cenas"]:
    html += f"""
    <button class='btn' onclick="openHook('{b['url']}')">
      <img src='assets/icones/{b['icon']}' alt=''><span>{b['nome']}</span>
    </button>"""
html += f"""
  </div></div>

  <!-- AGENDA -->
  <div class='section'><h3>Agenda</h3>
    <p class='info'><strong>Data/Hora:</strong> {data_hora}</p>
    <p class='info'><strong>Feriado:</strong> {feriado}</p>
    <p class='info'><strong>Compromissos:</strong><br>{compromissos}</p>
  </div>

  <!-- TEMPO EXTERNO -->
  <!-- (já sai do wttr.in, não há botão) -->
  <div class='section'><h3>Tempo</h3>
    <p class='info'>{requests.get("https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m").text}</p>
  </div>

  <!-- SISTEMA -->
  <div class='section'><h3>Sistema</h3>
    <p class='info'><strong>Velocidade da Internet:</strong> {internet_text}</p>
    <p class='info'><strong>Limpeza dos Filtros do Ar-condicionado:</strong> {limpeza_text}</p>
    <p class='info'><strong>⚠ Bandeira Tarifária:</strong> {bandeira_text}</p>
    <p class='info'><strong>Quarto:</strong> {clima_quarto}</p>
  </div>

</div>
</body></html>
"""

# grava no docs para o GitHub Pages
os.makedirs("docs", exist_ok=True)
with open("docs/index.html","w",encoding="utf-8") as f:
    f.write(html)
