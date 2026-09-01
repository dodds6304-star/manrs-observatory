from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "MANRS West Africa Observatory API"}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "manrs_observatory",
    "user": "manrs",
    "password": "changeme"
}

@app.get("/api/countries")
def get_countries():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT country_code, country_name, total_asn, manrs_members, avg_manrs_score, roa_coverage_pct FROM countries ORDER BY country_code")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    countries = []
    for row in rows:
        countries.append({
            "country_code": row[0],
            "country_name": row[1],
            "total_asn": row[2],
            "manrs_members": row[3],
            "avg_manrs_score": float(row[4]),
            "roa_coverage_pct": float(row[5])
        })
    return countries
@app.get("/api/countries/{code}")
def get_country_detail(code: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT country_code, country_name, total_asn, manrs_members, avg_manrs_score, roa_coverage_pct FROM countries WHERE country_code = %s", (code,))
    country_row = cur.fetchone()

    cur.execute("SELECT asn_number, name, is_manrs_member, manrs_score FROM asn WHERE country_code = %s ORDER BY asn_number", (code,))
    asn_rows = cur.fetchall()

    cur.close()
    conn.close()

    if not country_row:
        return {"error": "Pays non trouvé"}

    return {
        "country_code": country_row[0],
        "country_name": country_row[1],
        "total_asn": country_row[2],
        "manrs_members": country_row[3],
        "avg_manrs_score": float(country_row[4]),
        "roa_coverage_pct": float(country_row[5]),
        "asns": [
            {
                "asn_number": row[0],
                "name": row[1],
                "is_manrs_member": row[2],
                "manrs_score": row[3]
            }
            for row in asn_rows
        ]
    }
@app.get("/api/asn/{number}")
def get_asn_detail(number: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT asn_number, name, country_code, is_manrs_member, manrs_score,
               action_filtering, action_antispoofing, action_coordination, action_validation, last_updated
        FROM asn WHERE asn_number = %s
    """, (number,))
    asn_row = cur.fetchone()

    if not asn_row:
        cur.close()
        conn.close()
        return {"error": "ASN non trouvé"}

    cur.execute("SELECT id FROM asn WHERE asn_number = %s", (number,))
    asn_id = cur.fetchone()[0]

    cur.execute("SELECT prefix, roa_status FROM prefixes WHERE asn_id = %s", (asn_id,))
    prefix_rows = cur.fetchall()

    cur.close()
    conn.close()

    total_prefixes = len(prefix_rows)
    valid_prefixes = sum(1 for p in prefix_rows if p[1] == "valid")
    roa_coverage_pct = round((valid_prefixes / total_prefixes) * 100, 2) if total_prefixes else 0

    return {
        "asn_number": asn_row[0],
        "name": asn_row[1],
        "country_code": asn_row[2],
        "is_manrs_member": asn_row[3],
        "manrs_score": asn_row[4],
        "actions": {
            "filtering": asn_row[5],
            "anti_spoofing": asn_row[6],
            "coordination": asn_row[7],
            "validation": asn_row[8]
        },
        "prefixes": [
            {"prefix": row[0], "roa_status": row[1]}
            for row in prefix_rows
        ],
        "roa_coverage_pct": roa_coverage_pct,
        "last_updated": asn_row[9].isoformat()
    }
@app.get("/api/stats")
def get_stats():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM asn")
    total_asn = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM asn WHERE is_manrs_member = TRUE")
    manrs_members = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prefixes")
    total_prefixes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prefixes WHERE roa_status = 'valid'")
    valid_prefixes = cur.fetchone()[0]

    cur.close()
    conn.close()

    manrs_pct = round((manrs_members / total_asn) * 100, 2) if total_asn else 0
    roa_pct = round((valid_prefixes / total_prefixes) * 100, 2) if total_prefixes else 0

    return {
        "total_asn": total_asn,
        "manrs_members_pct": manrs_pct,
        "roa_coverage_pct": roa_pct
    }
@app.get("/api/search")
def search_asn(q: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    if q.isdigit():
        cur.execute("SELECT asn_number, name, country_code FROM asn WHERE asn_number = %s", (int(q),))
    else:
        cur.execute("SELECT asn_number, name, country_code FROM asn WHERE name ILIKE %s", (f"%{q}%",))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"asn_number": row[0], "name": row[1], "country_code": row[2]}
        for row in rows
    ]
@app.get("/api/asn/{number}/recommendation")
def get_asn_recommendation(number: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT id FROM asn WHERE asn_number = %s", (number,))
    asn_row = cur.fetchone()

    if not asn_row:
        cur.close()
        conn.close()
        return {"error": "ASN non trouvé"}

    asn_id = asn_row[0]
    cur.execute("SELECT content, generated_at FROM ai_recommendations WHERE asn_id = %s ORDER BY generated_at DESC LIMIT 1", (asn_id,))
    reco_row = cur.fetchone()

    cur.close()
    conn.close()

    if not reco_row:
        return {"content": None, "generated_at": None, "message": "Aucune recommandation générée pour cet ASN"}

    return {"content": reco_row[0], "generated_at": reco_row[1].isoformat()}