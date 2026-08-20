CREATE TABLE asn (
  id              SERIAL PRIMARY KEY,
  asn_number      INTEGER UNIQUE NOT NULL,
  name            VARCHAR(255),
  country_code    CHAR(2) NOT NULL,
  is_manrs_member BOOLEAN DEFAULT FALSE,
  manrs_score     SMALLINT DEFAULT 0,
  action_filtering    BOOLEAN DEFAULT FALSE,
  action_antispoofing BOOLEAN DEFAULT FALSE,
  action_coordination BOOLEAN DEFAULT FALSE,
  action_validation   BOOLEAN DEFAULT FALSE,
  last_updated    TIMESTAMP DEFAULT NOW()
);
CREATE TABLE countries (
  id                  SERIAL PRIMARY KEY,
  country_code        CHAR(2) UNIQUE NOT NULL,
  country_name        VARCHAR(100),
  total_asn           INTEGER DEFAULT 0,
  manrs_members       INTEGER DEFAULT 0,
  avg_manrs_score     DECIMAL(3,2) DEFAULT 0,
  roa_coverage_pct    DECIMAL(5,2) DEFAULT 0,
  last_updated        TIMESTAMP DEFAULT NOW()
);
CREATE TABLE prefixes (
  id           SERIAL PRIMARY KEY,
  asn_id       INTEGER REFERENCES asn(id),
  prefix       VARCHAR(50) NOT NULL,
  roa_status   VARCHAR(20),
  roa_asn      INTEGER,
  last_checked TIMESTAMP DEFAULT NOW()
);
CREATE TABLE ai_recommendations (
  id          SERIAL PRIMARY KEY,
  asn_id      INTEGER REFERENCES asn(id),
  language    CHAR(2) DEFAULT 'fr',
  content     TEXT,
  generated_at TIMESTAMP DEFAULT NOW()
);