
import os
import requests
import speedtest
from datetime import datetime
import holidays
from bandeira import fetch_bandeira
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==============================
# CONFIGURAÇÃO
# ==============================
HA_URL      = os.getenv("HA_URL").rstrip("/")
HA_TOKEN    = os.getenv("HA_TOKEN")
CAL_ID      = os.getenv("CALENDAR_ID")
CREDS_JSON  = os.getenv("GOOGLE_CREDENTIALS")
NABU_BASE   = os.getenv("NABU_URL").rstrip("/")

# ==============================
# BOTÕES DIRETAMENTE DEFINIDOS AQUI
# ==============================
buttons = {
    "Luzes": [
        {"label": "Quarto", "icone": "luz_on.svg", "webhook": os.getenv("webhook_luz_quarto")},
        {"label": "Abajur 1", "icone": "abajur_on.svg", "webhook": os.getenv("webhook_abajur_1")},
        {"label": "Abajur 2", "icone": "abajur_on.svg", "webhook": os.getenv("webhook_abajur_2")},
        {"label": "Cama", "icone": "cama_on.svg", "webhook": os.getenv("webhook_luz_cama")},
        {"label": "Banheiro Suíte", "icone": "banheiro_on.svg", "webhook": os.getenv("webhook_luz_wc_suite")},
        {"label": "Luz Noturna", "icone": "luz_on.svg", "webhook": os.getenv("webhook_luz_noturna")},
    ],
    "Dispositivos": [
        {"label": "Ar-condicionado", "icone": "ar_on.svg", "webhook": os.getenv("webhook_ar")},
        {"label": "USB Projetor", "icone": "projetor_on.svg", "webhook": os.getenv("webhook_projetor")},
        {"label": "USB iPad", "icone": "usb_on.svg", "webhook": os.getenv("webhook_ipad")},
    ],
    "Cenas": [
        {"label": "Luzes Vermelhas", "icone": "luzes_vermelhas_on.svg", "webhook": os.getenv("webhook_vermelho")},
    ]
}

# ==============================
# FUNÇÕES MODULARES DE HTML
# ==============================

def render_secao(nome, botoes):
    if not botoes:
        return ""
    blocos = "".join([
        f"<div class='btn' onclick=\"toggle('{b['webhook']}')\">"
        f"<img src='assets/icones/{b['icone']}'><br>{b['label']}</div>"
        for b in botoes
    ])
    return f"<div class='section'><h3>{nome}</h3><div class='grid'>{blocos}</div></div>"

def render_agenda(dh_str, feriado, compromissos):
    return f"<div class='section'><h3>Agenda</h3><p id='dh'>{dh_str}</p><p>Feriado: {feriado}</p><p>Compromissos:<br>{compromissos}</p></div>"

def render_tempo():
    try:
        tempo = requests.get("https://wttr.in/Sao+Paulo?format=%c+%C+%t+Humidity+%h&lang=pt&m").text
    except:
        tempo = "Indisponível"
    return f"<div class='section'><h3>Tempo</h3><p>{tempo}</p></div>"

def render_sistema(velocidade, limpeza, bandeira, clima):
    return f"<div class='section'><h3>Sistema</h3><p>Velocidade da Internet: {velocidade}</p><p>Limpeza dos Filtros do Ar-condicionado: {limpeza}</p><p>⚠ Bandeira Tarifária: {bandeira}</p><p>Quarto: {clima}</p></div>"

# ==============================
# DADOS DINÂMICOS
# ==============================
now        = datetime.now()
data_hora  = now.strftime("%d/%m/%Y %H:%M")
br         = holidays.Brazil(prov="SP")
feriado    = br.get(now.date()) or "Nenhum"

# Clima interno
try:
    r = requests.get(f"{HA_URL}/api/states/climate.quarto",
        headers={"Authorization": f"Bearer {HA_TOKEN}"}, timeout=10).json()
    t = r.get("attributes", {}).get("current_temperature", "—")
    h = r.get("attributes", {}).get("current_humidity", "—")
    quarto_text = f"{t}°C / {h}%"
except:
    quarto_text = "—"

# Internet
try:
    st = speedtest.Speedtest(); st.get_best_server()
    down = int(st.download()/1e6); up = int(st.upload()/1e6)
    internet_text = f"{down} ↓ / {up} ↑"
except:
    internet_text = "—"

# Filtro
try:
    r = requests.get(f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
        headers={"Authorization": f"Bearer {HA_TOKEN}"}, timeout=5).json()
    limpeza = "Necessário" if r.get("state") == "on" else "OK"
except:
    limpeza = "—"

# Bandeira
bandeira = fetch_bandeira()

# Agenda
with open("service_account.json", "w", encoding="utf-8") as f:
    f.write(CREDS_JSON)
creds = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/calendar.readonly"])
svc   = build("calendar", "v3", credentials=creds)
start = now.isoformat()+"Z"
end   = datetime(now.year, now.month, now.day, 23,59,59).isoformat()+"Z"
events = svc.events().list(calendarId=CAL_ID, timeMin=start, timeMax=end,
                           singleEvents=True, orderBy="startTime").execute().get("items", [])
compromissos = "<br>".join([
    f"{(e['start'].get('dateTime') or e['start'].get('date')).split('T')[-1][:5]} – {e.get('summary','')}"
    for e in events
]) if events else "Nenhum"

# ==============================
# MONTA HTML FINAL
# ==============================
html = f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'>
<title>Painel Quarto</title>
<link href='https://fonts.googleapis.com/css2?family=VT323&display=swap' rel='stylesheet'>
<style>
body {{margin:0;background:#000;color:#0f0;font-family:'VT323',monospace;}}
.outer {{border:2px solid #0f0;max-width:700px;margin:10px auto;padding:10px;}}
.section {{border:1px solid #0f0;margin-top:10px;padding:10px;}}
.grid {{display:flex;gap:10px;flex-wrap:wrap;}}
.btn {{border:1px solid #0f0;padding:5px;text-align:center;cursor:pointer;}}
.btn img {{width:32px;height:32px;}}
</style>
<script>
function toggle(wh) {{
  fetch('{NABU_BASE}/api/webhook/' + wh, {{ method: 'POST' }});
}}
function atualizaHora() {{
  document.getElementById('dh').innerText = '{data_hora}';
}}
</script></head><body onload="atualizaHora()"><div class='outer'>
"""

# Concatena seções
html += render_secao("Luzes", buttons.get("Luzes", []))
html += render_secao("Dispositivos", buttons.get("Dispositivos", []))
html += render_secao("Cenas", buttons.get("Cenas", []))
html += render_agenda(data_hora, feriado, compromissos)
html += render_tempo()
html += render_sistema(internet_text, limpeza, bandeira, quarto_text)
html += "</div></body></html>"

# Salva HTML
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
