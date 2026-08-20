import os
from dotenv import load_dotenv

load_dotenv()
import requests
import psycopg2
import re

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "manrs_observatory",
    "user": "manrs",
    "password": "changeme"
}

def get_asns_for_country(country_code):
    url = f"https://stat.ripe.net/data/country-asns/data.json?resource={country_code}&lod=1"
    response = requests.get(url)
    data = response.json()
    routed_raw = data["data"]["countries"][0]["routed"]
    asns = re.findall(r"AsnSingle\((\d+)\)", routed_raw)
    return [int(asn) for asn in asns]

def get_manrs_status(asn_number):
    api_key = os.environ.get("MANRS_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://observatory.manrs.org/api/v2/participants?asn={asn_number}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"is_manrs_member": False, "manrs_score": 0}
    data = response.json()
    participants = data.get("participants", [])
    if not participants:
        return {"is_manrs_member": False, "manrs_score": 0}
    status = participants[0].get("status")
    return {"is_manrs_member": status == "approved", "manrs_score": 0}

def test_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    print("Connexion réussie à PostgreSQL")
    conn.close()

if __name__ == "__main__":
    asns = get_asns_for_country("BJ")
    print(asns)
    manrs_status = get_manrs_status(13335)
    print(manrs_status)