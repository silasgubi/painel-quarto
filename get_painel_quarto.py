import os
import requests
import speedtest
from datetime import datetime
import holidays

HA_URL = os.environ['HA_URL']
HA_TOKEN = os.environ['HA_TOKEN']

HEADERS = {
    'Authorization': f'Bearer {HA_TOKEN}',
    'Content-Type': 'application/json'
}

# Dados do quarto
try:
    r = requests.get(f"{HA_URL}/api/states/climate.quarto", headers=HEADERS, timeout=5)
    a = r.json().get("attributes", {})
    clima_quarto_txt = f"{a.get('temperature', '--')}°C  {a.get('humidity', '--')}%"
except:
    clima_quarto_txt = "—"

try:
    r = requests.get(f"{HA_URL}/api/states/binary_sensor.quarto_filter_clean_required", headers=HEADERS, timeout=5)
    filtro_text = "Filtro precisa limpeza" if r.json().get("state") == "on" else "Filtro OK"
except:
    filtro_text = "Erro no filtro"

now = datetime.now()
data_hoje = now.strftime('%d/%m/%Y')
hora_hoje = now.strftime('%H:%M')
dia_semana = now.strftime('%a.')

br_hols = holidays.Brazil(prov='SP')
feriado = br_hols.get(now.date())
if feriado:
    feriado_txt = f"Hoje é feriado: {feriado}"
else:
    futuros = sorted(d for d in br_hols if d > now.date() and d.year == now.year)
    feriado_txt = f"Próximo: {br_hols.get(futuros[0])} em {futuros[0].strftime('%d/%m/%Y')}" if futuros else "Sem feriados"

agenda_txt = "Compromissos: manter código antigo"

try:
    st = speedtest.Speedtest()
    st.get_best_server()
    down = int(st.download() / 1_000_000)
    up = int(st.upload() / 1_000_000)
    internet_txt = f"Velocidade: {down} ↓ / {up} ↑"
except:
    internet_txt = "Velocidade offline"

html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto</title>
</head>
<body style='background:#000; color:#0f0; font-family:monospace'>
  <h2>{dia_semana} {data_hoje} — {hora_hoje}</h2>
  <p>Clima do Quarto: {clima_quarto_txt}</p>
  <p>{agenda_txt}</p>
  <p>{internet_txt}</p>
  <p>{filtro_text}</p>
  <p>{feriado_txt}</p>
  <p id="bandeira">Bandeira: carregando…</p>
  <script>
    fetch('https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?resource_id=0591b8f6-fe54-437b-b72b-1aa2efd46e42&sort=DatCompetencia%20desc&limit=1')
      .then(r=>r.json()).then(resp=>{
        const rec = resp.result.records[0].NomBandeiraAcionada;
        document.getElementById('bandeira').textContent = 'Bandeira: ' + rec;
      }).catch(_=>{
        document.getElementById('bandeira').textContent = 'Bandeira: erro';
      });
  </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
