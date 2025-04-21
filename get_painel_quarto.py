# ... (todo o código de coleta de dados acima permanece igual)

# -----------------------------
# Montagem do HTML corrigida
# -----------------------------
html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel Quarto — %s %s</title>
  <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
  <style>
    body { margin:0; background:#000; color:#0F0; font-family:'VT323',monospace; }
    .outer { border:2px solid #0A0; max-width:700px; margin:10px auto; padding:10px; display:none; }
    .section { border:1px solid #0A0; padding:10px; margin-top:10px; }
    .section h3 { margin:0 0 5px; border-bottom:1px dashed #0A0; text-transform:uppercase; }
    button {
      display:inline-block; margin:5px; padding:8px 12px;
      background:#000; color:#0F0; border:1px solid #0A0;
      font-family:'VT323',monospace; cursor:pointer;
    }
  </style>
</head>
<body>
  <audio id="bootSound" src="assets/sons/boot.mp3"></audio>
  <!-- Tela de Boot MS‑DOS -->
  <div id="bootScreen" style="
    white-space: pre; color: #00FF00; font-family: 'VT323', monospace;
    background: black; padding: 20px; font-size: 1.1em;
  "></div>

  <div class="outer">
    <div class="section"><h3>Luzes</h3>
      %s
    </div>
    <div class="section"><h3>Dispositivos</h3>
      %s
    </div>
    <div class="section"><h3>Cenas</h3>
      %s
    </div>
    <div class="section"><h3>Sistema</h3>
      <p>%s</p>
      <p>%s</p>
      <p>%s</p>
      <p>%s</p>
      <p>%s</p>
      <p>%s</p>
    </div>
  </div>

  <script>
    // Boot MS‑DOS...
    const bootLines = [ /* ... */ ];
    let li = 0;
    function showNext() {
      const el = document.getElementById('bootScreen');
      if (li < bootLines.length) {
        el.innerText += bootLines[li++] + "\\n";
        setTimeout(showNext, 300);
      } else {
        setTimeout(() => {
          el.style.display = "none";
          document.querySelector('.outer').style.display = "block";
        }, 1000);
      }
    }

    function toggleEntity(entity_id) {
      new Audio('assets/sons/on.mp3').play();
      fetch('%s/api/services/homeassistant/toggle', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer %s',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ entity_id })
      });
    }

    document.addEventListener('DOMContentLoaded', () => {
      document.getElementById('bootSound').play();
      showNext();
    });
  </script>
</body>
</html>
""" % (
    data_hoje, hora_hoje,
    # luzes
    "".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid, label)
        for label, eid in BUTTONS_LIGHTS
    ),
    # dispositivos
    "".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid, label)
        for label, eid in BUTTONS_DEVICES
    ),
    # cenas
    "".join(
        '<button onclick="toggleEntity(\'%s\')">%s</button>' % (eid, label)
        for label, eid in BUTTONS_SCENES
    ),
    # sistema
    get_clima(),
    get_agenda(),
    get_speed(),
    feriado_text,
    get_filtro(),
    get_bandeira_text(),
    # variáveis para REST toggle
    HA_URL, HA_TOKEN
)

# grava em docs/index.html
os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
