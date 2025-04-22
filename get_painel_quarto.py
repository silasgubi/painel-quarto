html = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body {{ margin:0;background:#000;color:#0f0;font-family:'VT323',monospace; }}
    .outer {{border:2px solid #0f0;max-width:700px;margin:10px auto;padding:10px;}}
    .section {{border:1px solid #0f0;margin-top:10px;padding:10px;}}
    .grid    {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .btn     {{ border:1px solid #0f0; padding:5px; text-align:center; cursor:pointer; }}
    .btn img {{ width:32px; height:32px; }}
  </style>
  <script>
    function toggle(wh) {{
      fetch("{NABU_BASE}/api/webhook/" + wh, {{ method: "POST" }});
    }}
    function atualizaHora() {{
      document.getElementById("dh").innerText = "{data_hora}";
    }}
  </script>
</head>
<body onload="atualizaHora()">
  <div class="outer">
    <!-- LUZES -->
    <div class="section">
      <h3>Luzes</h3>
      <div class="grid">
        {luzes_buttons}
      </div>
    </div>

    <!-- DISPOSITIVOS -->
    <div class="section">
      <h3>Dispositivos</h3>
      <div class="grid">
        {dispositivos_buttons}
      </div>
    </div>

    <!-- CENAS -->
    <div class="section">
      <h3>Cenas</h3>
      <div class="grid">
        {cenas_buttons}
      </div>
    </div>

    <!-- OUTRAS SEÇÕES -->
  </div>
</body>
</html>
'''

# Gerar os botões separadamente
luzes_buttons = ''.join(
    f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
    f'<img src="assets/icones/{b["icone"]}"><br>'
    f'{b["label"]}</div>'
    for b in buttons.get("Luzes", [])
)

dispositivos_buttons = ''.join(
    f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
    f'<img src="assets/icones/{b["icone"]}"><br>'
    f'{b["label"]}</div>'
    for b in buttons.get("Dispositivos", [])
)

cenas_buttons = ''.join(
    f'<div class="btn" onclick="toggle(\'{b["webhook"]}\')">'
    f'<img src="assets/icones/{b["icone"]}"><br>'
    f'{b["label"]}</div>'
    for b in buttons.get("Cenas", [])
)

# Substituir as variáveis no HTML
html = html.format(
    NABU_BASE=NABU_BASE,
    data_hora=data_hora,
    luzes_buttons=luzes_buttons,
    dispositivos_buttons=dispositivos_buttons,
    cenas_buttons=cenas_buttons
)

# Salvar o HTML no arquivo
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
