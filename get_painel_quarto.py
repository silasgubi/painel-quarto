import os
import requests
import speedtest
from datetime import datetime
import holidays

# Tentar importar Google Calendar; se falhar, usar fallback
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# 1. Configuração do Google Calendar (fallback se não disponível)
calendar_id = os.environ.get('CALENDAR_ID', '')
if HAS_GOOGLE and calendar_id:
    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        credentials_json = os.environ['GOOGLE_CREDENTIALS']
        # Escreve temporariamente o JSON de credenciais
        with open('service_account.json', 'w', encoding='utf-8') as f:
            f.write(credentials_json)
        creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception:
        HAS_GOOGLE = False

# 2. Coleta de dados dinâmicos
now = datetime.now()
data_hoje = now.strftime('%d/%m/%Y')
hora_hoje = now.strftime('%H:%M')
dia_semana = now.strftime('%a.')

# Feriados - Brasil (SP)
br_holidays = holidays.Brazil(prov='SP')
feriado_hoje = br_holidays.get(now.date())
if feriado_hoje:
    feriado_text = f'Hoje é feriado: {feriado_hoje}'
else:
    proximos = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if proximos:
        pd = proximos[0]
        feriado_text = f'Próximo feriado: {br_holidays.get(pd)} em {pd.strftime("%d/%m/%Y")}'
    else:
        feriado_text = 'Não há mais feriados este ano'

# Clima do quarto (via Home Assistant REST)
ha_url   = os.environ.get('HA_URL', '')
ha_token = os.environ.get('HA_TOKEN', '')
climate_entity = 'climate.quarto'
try:
    resp = requests.get(
        f'{ha_url}/api/states/{climate_entity}',
        headers={'Authorization': f'Bearer {ha_token}', 'Content-Type': 'application/json'}
    ).json()
    temp = resp.get('state', '—')
    hum  = resp.get('attributes', {}).get('current_humidity', '—')
    clima_quarto = f'{data_hoje} {hora_hoje} — {temp}°C / {hum}%'
except Exception:
    clima_quarto = 'Clima indisponível'

# Agenda (Google Calendar ou fallback)
if HAS_GOOGLE and calendar_id:
    time_min = now.isoformat() + 'Z'
    time_max = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'
    try:
        events = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        if not events:
            agenda_text = 'Compromissos: Nenhum'
        else:
            lines = []
            for ev in events:
                start = ev['start'].get('dateTime', ev['start'].get('date'))
                t = start.split('T')[1][:5] if 'T' in start else start
                lines.append(f"{t} – {ev.get('summary','Sem título')}")
            agenda_text = 'Compromissos:<br>' + '<br>'.join(lines)
    except:
        agenda_text = 'Agenda indisponível'
else:
    agenda_text = 'Agenda indisponível'

# Teste de velocidade de Internet
try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up   = int(st.upload()   / 1_000_000)
    internet_text = f'Velocidade: {down} ↓ / {up} ↑'
except:
    internet_text = 'Velocidade: Offline'

# Filtro do ar-condicionado (binary_sensor do HA)
filter_req = 'binary_sensor.quarto_filter_clean_required'
try:
    fr = requests.get(
        f'{ha_url}/api/states/{filter_req}',
        headers={'Authorization': f'Bearer {ha_token}', 'Content-Type': 'application/json'}
    ).json()
    filtro_text = 'Limpeza: 🚩' if fr.get('state') == 'on' else 'Limpeza: OK'
except:
    filtro_text = 'Limpeza: —'

# Bandeira tarifária (via CKAN ANEEL)
from bandeira import fetch_bandeira  # import do seu module Bandeira.txt convertido
try:
    bandeira_text = f'Bandeira: {fetch_bandeira()}'
except:
    bandeira_text = 'Bandeira: —'

# 3. HTML template com as seções e observações
html_template = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto — {data_hora}</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }}
    .outer {{ border:2px solid #0A0; max-width:700px; margin:10px auto; padding:10px; display:none; }}
    .section {{ border:1px solid #0A0; padding:10px; margin-top:10px; }}
    .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; opacity:0.9; }}
    #bootScreen {{ white-space:pre; background:#000; color:#0F0; padding:20px; }}
  </style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <div id="bootScreen"></div>
  <div class="outer">
    <div class="section"><h3>Luzes</h3><!-- botões --></div>
    <div class="section"><h3>Dispositivos</h3><!-- botões --></div>
    <div class="section"><h3>Cenas</h3><!-- botões --></div>
    <div class="section"><h3>Sistema</h3>
      <p>{clima_quarto}</p>
      <p>{agenda_text}</p>
      <p>{internet_text}</p>
      <p>{feriado_text}</p>
      <p>{filtro_text}</p>
      <p>{bandeira_text}</p>
    </div>
  </div>
  <script>
    const bootLines = [
      'Phoenix Technologies Ltd. Version 4.06',
      'Memory Testing: 524288K OK',
      'Loading DOS...',
      'Starting Smart Panel Interface...'
    ];
    let idx = 0;
    function showNext() {{
      const el = document.getElementById('bootScreen');
      if (idx < bootLines.length) {{
        el.innerText += bootLines[idx] + '\\n';
        idx++;
        setTimeout(showNext, 300);
      }} else {{
        setTimeout(() => {{
          document.getElementById('bootScreen').style.display = 'none';
          document.querySelector('.outer').style.display = 'block';
        }}, 1000);
      }}
    }}
    document.addEventListener('DOMContentLoaded', () => {{
      document.getElementById('bootSound').play();
      showNext();
    }});
  </script>
</body>
</html>
"""

html = html_template.format(
    data_hora=f"{data_hoje} {hora_hoje}",
    clima_quarto=clima_quarto,
    agenda_text=agenda_text,
    internet_text=internet_text,
    feriado_text=feriado_text,
    filtro_text=filtro_text,
    bandeira_text=bandeira_text
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
