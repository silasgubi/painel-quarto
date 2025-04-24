# bandeira.py
import requests

def fetch_bandeira():
    """
    Busca a bandeira tarifária mais recente no portal de dados abertos da ANEEL.
    Retorna: "VERDE", "AMARELA", "VERMELHA 1", etc., ou "—" em caso de erro.
    """
    resource_id = '0591b8f6-fe54-437b-b72b-1aa2efd46e42'
    api_url = (
        'https://dadosabertos.aneel.gov.br/api/3/action/datastore_search'
        f'?resource_id={resource_id}'
        '&sort=DatCompetencia%20desc'
        '&limit=1'
    )
    resp = requests.get(api_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    records = data.get('result', {}).get('records', [])
    if not records:
        return '—'
    return records[0].get('NomBandeiraAcionada', '—')
