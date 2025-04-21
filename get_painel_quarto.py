# get_painel_quarto.py
import os
import requests
import speedtest
from datetime import datetime
import holidays

# IMPORTAÇÃO DO MÓDULO bandeira.py
from bandeira import fetch_bandeira

# --- CONFIGURAÇÃO INICIAL ---
HA_URL   = os.environ['HA_URL']       # ex: http://192.168.1.33:8123
HA_TOKEN = os.environ['HA_TOKEN']
CAL_ID   = os.environ.get('CALENDAR_ID', '')
GOOGLE_CRED = os.environ.get('GOOGLE_CREDENTIALS', '')

# Tentar inicializar Google Calendar
HAS_GOOGLE = False
if CAL_ID and GOOGLE_CRED:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        HAS_GOOGLE = True
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        with open('service_account.json', 'w', encoding='utf-8') as f:
            f.write(GOOGLE_CRED)
        creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception:
        HAS_GOOGLE = False

# --- DADOS DINÂMICOS ---
now = datetime.now()
data_hoje = now.strftime('%d/%m/%Y')
hora_hoje = now.strftime('%H:%M')

# Feriados SP
br_holidays = holidays.Brazil(prov='SP')
fer = br_holidays.get(now.date())
if fer:
    feriado_text = f'Hoje é feriado: {fer}'
else:
    pro = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if pro:
        pd = pro[0]
        feriado_text = f'Próximo feriado: {br_holidays.get(pd)} em {pd.strftime("%d/%m/%Y")}'
    else:
        feriado_text = 'Não há mais feriados este ano'

# Clima do quarto via REST HA
def get_clima():
    try:
        ent = 'climate.quarto'
        r = requests.get(f'{HA_URL}/api/states/{ent}',
                         headers={'Authorization': f'Bearer {HA_TOKEN}'})
        j = r.json()
        t = j.get('state','—')
        h = j.get('attributes',{}).get('current_humidity','—')
        return f'{data_hoje} {hora_hoje} — {t}°C / {h}%'
    except:
        return 'Clima indisponível'

# Agenda Google Calendar
def get_agenda():
    if not HAS_GOOGLE: return 'Compromissos: Nenhum'
    try:
        tmin = now.isoformat() + 'Z'
        tmax = datetime(now.year,now.month,now.day,23,59,59).isoformat() + 'Z'
        evs = service.events().list(
            calendarId=CAL_ID,
            timeMin=tmin, timeMax=tmax,
            singleEvents=True, orderBy='startTime'
        ).execute().get('items', [])
        if not evs: return 'Compromissos: Nenhum'
        lines = []
        for ev in evs:
            s = ev['start'].get('dateTime',ev['start'].get('date'))
            hh = s.split('T')[1][:5] if 'T' in s else s
            lines.append(f"{hh} – {ev.get('summary','Sem título')}")
        return 'Compromissos:<br>' + '<br>'.join(lines)
    except:
        return 'Agenda indisponível'

# Teste de velocidade
def get_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        d = int(st.download()/1e6)
        u = int(st.upload()/1e6)
        return f'Velocidade: {d} ↓ / {u} ↑'
    except:
        return 'Velocidade: Offline'

# Filtro do ar (binary_sensor)
def get_filtro():
    try:
        ent = 'binary_sensor.quarto_filter_clean_required'
        r = requests.get(f'{HA_URL}/api/states/{ent}',
                         headers={'Authorization': f'Bearer {HA_TOKEN}'})
        st = r.json().get('state','off')
        return 'Limpeza: 🚩' if st=='on' else 'Limpeza: OK'
    except:
        return 'Limpeza: —'

# Bandeira tarifária
def get_bandeira():
    try:
        b = fetch_bandeira()
        return f'Bandeira: {b}'
    except:
        return 'Bandeira: —'

# --- BOTÕES (substitua pelos seus IDs) ---
# Cada tupla: (Título no botão, entity_id no HA, ícone opcional em ASCII)
BUTTONS_LIGHTS = [
    ("Luz de teto",         "light.sonoff_1000xxxxxx_1"),
    ("Abajur",              "switch.sonoff_1000xxxxxx_2"),
    # ... etc
]
BUTTONS_DEVICES = [
    ("Ventilador",          "switch.sonoff_1000yyyyyy_3"),
    ("Ar‑condicionado",     "climate.ar_condicionado"),
    # ...
]
BUTTONS_SCENES = [
    ("Cena Cinema",         "scene.cinema_on"),
    ("Cena Dormir",         "scene.dormir_on"),
    # ...
]

# --- TEMPLATE HTML ---
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
  <!-- BOOT MS‑DOS -->
  <div id="bootScreen" style="
    white-space:pre; color:#0F0; font-family:'VT323',monospace;
    background:black; padding:20px; font-size:1.1em;
  "></div>

  <div class="outer">
    <div class="section"><h3>Luzes</h3>
      {''.join(f'<button onclick="toggleEntity(\'{eid}\')">{label}</button>' for label, eid in BUTTONS_LIGHTS)}
    </div>
    <div class="section"><h3>Dispositivos</h3>
      {''.join(f'<button onclick="toggleEntity(\'{eid}\')">{label}</button>' for label, eid in BUTTONS_DEVICES)}
    </div>
    <div class="section"><h3>Cenas</h3>
      {''.join(f'<button onclick="toggleEntity(\'{eid}\')">{label}</button>' for label, eid in BUTTONS_SCENES)}
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>{get_clima()}</p>
      <p>{get_agenda()}</p>
      <p>{get_speed()}</p>
      <p>{feriado_text}</p>
      <p>{get_filtro()}</p>
      <p>{get_bandeira()}</p>
    </div>
  </div>

  <script>
    // Boot MS‑DOS
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
    let li = 0;
    function showNext() {{
      const el = document.getElementById('bootScreen');
      if (li < bootLines.length) {{
        el.innerText += bootLines[li++] + "\\n";
        setTimeout(showNext, 300);
      }} else {{
        setTimeout(()=> {{
          document.getElementById('bootScreen').style.display='none';
          document.querySelector('.outer').style.display='block';
        }}, 1000);
      }}
    }}
    // Toggle REST via HA
    function toggleEntity(entity_id) {{
      // toca som retrô
      const s = new Audio('assets/sons/on.mp3');
      s.play();
      fetch('{HA_URL}/api/services/homeassistant/toggle', {{
        method:'POST',
        headers: {{
          'Authorization': 'Bearer {HA_TOKEN}',
          'Content-Type': 'application/json'
        }},
        body: JSON.stringify({{ entity_id }})
      }});
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      document.getElementById('bootSound').play();
      showNext();
    }});
  </script>
</body>
</html>
"""

# grava em docs/index.html
os.makedirs('docs', exist_ok=True)
with open('docs/index.html','w',encoding='utf-8') as f:
    f.write(html)
