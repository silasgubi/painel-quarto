name: Atualizar Painel REST do Quarto

# Permissões para poder dar push no repositório
permissions:
  contents: write

on:
  schedule:
    # todo dia de hora em hora
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          persist-credentials: true

      - name: Configurar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Instalar dependências
        run: |
          pip install requests speedtest-cli holidays google-api-python-client google-auth

      - name: Rodar script e gerar painel
        env:
          HA_URL:           ${{ secrets.HA_URL }}
          HA_TOKEN:         ${{ secrets.HA_TOKEN }}
          CALENDAR_ID:      ${{ secrets.CALENDAR_ID }}
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        run: python get_painel_quarto.py

      - name: Commit e Push
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          # adiciona apenas o HTML gerado dentro de docs/
          git add docs/index.html
          git commit -m "Atualização automática do painel" || echo "Nada para commitar"
          git push
