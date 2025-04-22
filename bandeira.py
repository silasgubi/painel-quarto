import requests
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        records = data.get('result', {}).get('records', [])
        if not records:
            return '—'
        return records[0].get('NomBandeiraAcionada', '—')
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
    return '—'
