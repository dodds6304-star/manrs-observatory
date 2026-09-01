import os
from dotenv import load_dotenv

load_dotenv()
import psycopg2
import anthropic

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "manrs_observatory",
    "user": "manrs",
    "password": "changeme"
}

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def generate_recommendation_text(asn_data):
    missing_actions = [k for k, v in asn_data["actions"].items() if not v]

    prompt = f"""Tu es un expert en sécurité BGP. Analyse cet ASN et génère une recommandation claire en 3-5 points actionnables.

ASN: {asn_data['asn_number']} - {asn_data['name']}
Pays: {asn_data['country_code']}
Membre MANRS: {asn_data['is_manrs_member']}
Score MANRS: {asn_data['manrs_score']}
Actions manquantes: {missing_actions}
Couverture ROA: {asn_data['roa_coverage_pct']}%

Réponds en français. Sois concis et pratique."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def save_recommendation(conn, asn_id, content, score, is_member):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ai_recommendations (asn_id, language, content, score_at_generation, is_member_at_generation)
        VALUES (%s, 'fr', %s, %s, %s)
    """, (asn_id, content, score, is_member))
    conn.commit()
    cur.close()

def should_regenerate(conn, asn_id, current_score, current_is_member):
    cur = conn.cursor()
    cur.execute("""
        SELECT score_at_generation, is_member_at_generation
        FROM ai_recommendations
        WHERE asn_id = %s
        ORDER BY generated_at DESC
        LIMIT 1
    """, (asn_id,))
    last_reco = cur.fetchone()
    cur.close()

    if not last_reco:
        return True

    last_score, last_is_member = last_reco
    if last_score != current_score or last_is_member != current_is_member:
        return True

    return False
def run_recommendations():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, asn_number, name, country_code, is_manrs_member, manrs_score,
               action_filtering, action_antispoofing, action_coordination, action_validation
        FROM asn
    """)
    all_asns = cur.fetchall()
    cur.close()

    for row in all_asns:
        asn_id, asn_number, name, country_code, is_member, score, f, a, c, v = row

        if not should_regenerate(conn, asn_id, score, is_member):
            continue

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prefixes WHERE asn_id = %s AND roa_status = 'valid'", (asn_id,))
        valid_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM prefixes WHERE asn_id = %s", (asn_id,))
        total_count = cur.fetchone()[0]
        cur.close()
        roa_pct = round((valid_count / total_count) * 100, 2) if total_count else 0

        asn_data = {
            "asn_number": asn_number,
            "name": name or "Inconnu",
            "country_code": country_code,
            "is_manrs_member": is_member,
            "manrs_score": score,
            "actions": {
                "filtering": f, "anti_spoofing": a, "coordination": c, "validation": v
            },
            "roa_coverage_pct": roa_pct
        }

        try:
            content = generate_recommendation_text(asn_data)
            save_recommendation(conn, asn_id, content, score, is_member)
            print(f"Recommandation générée pour ASN {asn_number}")
        except Exception as e:
            print(f"Erreur pour ASN {asn_number}: {e}")

    conn.close()
    print("Génération des recommandations terminée.")

if __name__ == "__main__":
    run_recommendations()