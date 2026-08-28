import json
import os
import time
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

WEST_AFRICA_COUNTRIES = {
    'BJ': 'Bénin', 'BF': 'Burkina Faso', 'CV': 'Cap-Vert',
    'CI': "Côte d'Ivoire", 'GM': 'Gambie', 'GH': 'Ghana',
    'GN': 'Guinée', 'GW': 'Guinée-Bissau', 'LR': 'Liberia',
    'ML': 'Mali', 'MR': 'Mauritanie', 'NE': 'Niger',
    'NG': 'Nigeria', 'SN': 'Sénégal', 'SL': 'Sierra Leone',
    'TG': 'Togo'
}

def get_asns_for_country(country_code):
    url = f"https://stat.ripe.net/data/country-asns/data.json?resource={country_code}&lod=1"
    response = requests.get(url)
    data = response.json()
    routed_raw = data["data"]["countries"][0]["routed"]
    asns = re.findall(r"AsnSingle\((\d+)\)", routed_raw)
    return [int(asn) for asn in asns]

def get_announced_prefixes(asn_number):
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn_number}"
    response = requests.get(url)
    data = response.json()
    prefixes = data["data"]["prefixes"]
    return [p["prefix"] for p in prefixes]

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

def get_manrs_score_details(asn_number):
    api_key = os.environ.get("MANRS_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://observatory.manrs.org/api/v2/scores/details?asn={asn_number}"
    response = requests.get(url, headers=headers)
    print("Status code:", response.status_code)
    print("Contenu brut:", response.text[:500])

def get_manrs_score_summary(country_code):
    api_key = os.environ.get("MANRS_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://observatory.manrs.org/api/v2/scores/summary?region={country_code}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return 0
    data = response.json()
    key_figures = data["scores"]["keyFigures"]

    actions_to_use = ["antiSpoofing", "coordination", "filtering", "routingInformationRPKI"]
    values = []
    for figure in key_figures:
        if figure["id"] in actions_to_use:
            values.append(figure["value"])

    if not values:
        return 0

    moyenne = sum(values) / len(values)
    return round(moyenne * 100, 2)

def download_rpki_data():
    url = "https://rpki.cloudflare.com/rpki.json"
    response = requests.get(url)
    data = response.json()
    print("Nombre de clés dans le JSON:", list(data.keys()))
    print("Nombre de ROA:", len(data["roas"]))
    print("Exemple de ROA:", data["roas"][0])
    return data

def check_roa_status(prefix, asn_number, roa_data):
    prefix_ip = prefix.split("/")[0]
    prefix_length = int(prefix.split("/")[1])

    matching_roas = [r for r in roa_data["roas"] if r["prefix"].split("/")[0] == prefix_ip]

    if not matching_roas:
        return "not-found"

    for roa in matching_roas:
        roa_length = int(roa["prefix"].split("/")[1])
        if roa["asn"] == asn_number and prefix_length <= roa["maxLength"] and prefix_length >= roa_length:
            return "valid"

    return "invalid"

def test_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    print("Connexion réussie à PostgreSQL")
    conn.close()

def save_asn(conn, asn_number, country_code, manrs_info, manrs_score):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO asn (asn_number, country_code, is_manrs_member, manrs_score,
                          action_filtering, action_antispoofing, action_coordination, action_validation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (asn_number) DO UPDATE SET
            is_manrs_member = EXCLUDED.is_manrs_member,
            manrs_score = EXCLUDED.manrs_score,
            last_updated = NOW()
        RETURNING id
    """, (
        asn_number, country_code, manrs_info["is_manrs_member"], manrs_score,
        False, False, False, False
    ))
    asn_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return asn_id

def save_prefixes(conn, asn_id, prefixes_with_status):
    cur = conn.cursor()
    cur.execute("DELETE FROM prefixes WHERE asn_id = %s", (asn_id,))
    for prefix, status in prefixes_with_status:
        cur.execute("""
            INSERT INTO prefixes (asn_id, prefix, roa_status)
            VALUES (%s, %s, %s)
        """, (asn_id, prefix, status))
    conn.commit()
    cur.close()

def collect_country(conn, country_code, roa_data):
    print(f"--- Collecte pour {country_code} ---")
    score = get_manrs_score_summary(country_code)
    asns = get_asns_for_country(country_code)

    for asn_number in asns:
        try:
            manrs_info = get_manrs_status(asn_number)
            asn_id = save_asn(conn, asn_number, country_code, manrs_info, score)

            prefixes = get_announced_prefixes(asn_number)
            prefixes_with_status = [(p, check_roa_status(p, asn_number, roa_data)) for p in prefixes]
            save_prefixes(conn, asn_id, prefixes_with_status)

            print(f"  ASN {asn_number}: {len(prefixes_with_status)} préfixes")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Erreur sur ASN {asn_number}: {e}")

def run_full_collection():
    conn = psycopg2.connect(**DB_CONFIG)
    roa_data = download_rpki_data()

    for country_code in WEST_AFRICA_COUNTRIES:
        try:
            collect_country(conn, country_code, roa_data)
            time.sleep(1)
        except Exception as e:
            print(f"Erreur sur le pays {country_code}: {e}")

    conn.close()
    print("Collecte complète terminée.")

if __name__ == "__main__":
    run_full_collection()