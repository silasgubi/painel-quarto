import os
import requests
import speedtest
from datetime import datetime
import holidays

# 1. Informações do HA (REST)
HA_URL = os.environ.get("HA_URL", "")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# 2. Google Calendar
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

calendar_id = os.environ.get("CALENDAR_ID", "")
if HAS_GOOGLE and calendar_id:
    try:
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        credentials_json = os.environ["GOOGLE_CREDENTIALS"]
        with open("service_account.json", "w", encoding="utf-8") as f:
            f.write(credentials_json)
        creds = Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)
    except Exception:
        HAS_GOOGLE = False

# 3. Data e feriado
now = datetime.now()
data_hoje = now.strftime("%d/%m/%Y")
hora_hoje = now.strftime("%H:%M")
dia_semana = now.strftime("%a.")

br_holidays = holidays.Brazil(prov="SP")
feriado_hoje = br_holidays.get(now.date())
if feriado_hoje:
    feriado_text = f"Hoje é feriado: {feriado_hoje}"
else:
    proximos = sorted(d for d in br_holidays if d > now.date() and d.year == now.year)
    if proximos:
        pd = proximos[0]
        feriado_text = f"Próximo feriado: {br_holidays.get(pd)} em {pd.strftime('%d/%m/%Y')}"
    else:
        feriado_text = "Não há mais feriados este ano"

# 4. Clima
try:
    clima = requests.get(
        "https://wttr.in/Sao+Paulo?format=São+Paulo:+%c+%C+%t&lang=pt&m"
    ).text
except:
    clima = "Clima indisponível"

# 5. Agenda
if HAS_GOOGLE and calendar_id:
    try:
        time_min = now.isoformat() + "Z"
        time_max = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"
        events = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
            .get("items", [])
        )
        if not events:
            agenda_text = "Compromissos: Nenhum"
        else:
            lines = []
            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                t = start.split("T")[1][:5] if "T" in start else start
                lines.append(f"{t} - {ev.get('summary','Sem título')}")
            agenda_text = "Compromissos:<br>" + "<br>".join(lines)
    except:
        agenda_text = "Agenda indisponível"
else:
    agenda_text = "Agenda indisponível"

# 6. Velocidade Internet
try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up = int(st.upload() / 1_000_000)
    internet_text = f"Velocidade: {down} ↓ / {up} ↑"
except:
    internet_text = "Velocidade: Offline"

# 7. Sensor Filtro Ar-condicionado
try:
    r = requests.get(
        f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required",
        headers=HEADERS,
        timeout=10,
    )
    if r.status_code == 200 and r.json().get("state") == "on":
        filtro_text = "Limpeza do filtro: ⚠️ Necessária"
    else:
        filtro_text = "Limpeza do filtro: ✅ OK"
except:
    filtro_text = "Filtro: Indisponível"

# 8. Bandeira Tarifária
try:
    r = requests.get(
        f"{HA_URL}/api/states/sensor.bandeira_tarifaria", headers=HEADERS, timeout=10
    )
    if r.status_code == 200:
        bandeira = r.json().get("state", "desconhecida")
        bandeira_text = f"Bandeira Tarifária: {bandeira.capitalize()}"
    else:
        bandeira_text = "Bandeira: Indisponível"
except:
    bandeira_text = "Bandeira: Indisponível"

# 9. Sensor de temperatura e umidade
try:
    r = requests.get(f"{HA_URL}/api/states/climate.quarto", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        rec = r.json()
        temp = rec.get("attributes", {}).get("current_temperature", "?")
        hum = rec.get("attributes", {}).get("humidity", "?")
        clima_quarto = f"{temp}°C / {hum}%"
    else:
        clima_quarto = "Desconhecido"
except:
    clima_quarto = "Desconhecido"

# 10. Gera HTML
html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{data_hoje} — {clima_quarto}</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0; background:#000; color:#00FF00; font-family:'VT323',monospace; }}
    .outer {{ border:2px solid #00AA00; max-width:700px; margin:10px auto; padding:10px; background:#000; display:none; }}
    .section {{ border:1px solid #00AA00; padding:10px; margin-top:10px; }}
    .section h3 {{ margin:0 0 5px; border-bottom:1px dashed #00AA00; padding-bottom:5px; opacity:0.9; text-transform:uppercase; }}
    #bootScreen {{ white-space:pre; background:#000; color:#00FF00; padding:20px; font-size:1em; }}
    @keyframes blink {{ 50% {{ opacity:0; }} }}
  </style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <div id="bootScreen"></div>
  <div class="outer">
    <div class="section">
      <h3>Luzes</h3>
    </div>
    <div class="section">
      <h3>Dispositivos</h3>
    </div>
    <div class="section">
      <h3>Cenas</h3>
    </div>
    <div class="section">
      <h3>Sistema</h3>
      <p>{clima}</p>
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

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
