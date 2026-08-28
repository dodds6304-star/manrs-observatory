# Notes sur les APIs externes

Documentation des découvertes, pièges et solutions rencontrés lors de l'intégration des APIs externes au collecteur (Module 1).

## RIPE Stat

**Endpoint utilisé pour la liste des ASN par pays**
GET https://stat.ripe.net/data/country-asns/data.json?resource={code_pays}&lod=1

**Piège 1 — le paramètre `&lod=1` est obligatoire**
Sans lui, la réponse est incomplète.

**Piège 2 — la structure de la réponse n'est pas celle du cahier des charges**
La liste des ASN routés n'est pas dans `data.routed` mais dans `data["data"]["countries"][0]["routed"]` (`countries` est une liste, même avec un seul pays interrogé).

**Piège 3 — le champ `routed` n'est pas une vraie liste JSON**
C'est une chaîne de texte au format `"{AsnSingle(123), AsnSingle(456), ...}"`. Il faut la parser avec une regex :
```python
import re
asns = re.findall(r"AsnSingle\((\d+)\)", routed_raw)
```

**Endpoint utilisé pour les préfixes annoncés par un ASN**
GET https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{numero_asn}
Note : le préfixe `AS` devant le numéro est obligatoire ici (contrairement à l'endpoint précédent).
## MANRS Observatory

**Découverte majeure — migration v1 vers v2 (2026)**
L'API documentée dans le cahier des charges (`/api/v1/participants/{asn}`) est obsolète. Depuis le rachat de MANRS par la Global Cyber Alliance (janvier 2024), l'Observatory a été entièrement reconstruit avec une nouvelle API v2. L'ancien endpoint renvoie une page HTML de documentation (statut 200, mais pas de JSON exploitable) au lieu d'une vraie erreur claire — piège silencieux à surveiller.

Guide de migration officiel : docs.manrs.org/docs/api-migration

**Authentification obligatoire**
Contrairement à ce que suggérait le cahier des charges, `/participants` nécessite une clé API (`Authorization: Bearer {clé}`), même si elle est censée être un endpoint de base. Sans clé : `401 Unauthorized`.
Clé obtenue via inscription sur observatory.manrs.org (icône de profil en haut à droite du dashboard).
Clé stockée dans `backend/.env` (jamais commitée, exclue par `.gitignore`).

**Endpoint statut membre**
GET https://observatory.manrs.org/api/v2/participants?asn={numero_asn}
Renvoie `{"participants": [...]}`, liste vide si l'ASN n'est pas membre (pas une erreur 404 comme documenté, plutôt un statut 200 avec liste vide).

**Endpoint score détaillé par ASN — INACCESSIBLE**
GET https://observatory.manrs.org/api/v2/scores/details?asn={numero_asn}
Renvoie systématiquement `403 Forbidden` ("You are not authorized to view scores for this ASN"), même avec une clé API valide et authentifiée. Limitation liée au niveau de compte, pas un bug côté collecteur. Contrainte assumée : `manrs_score` reste à 0 au niveau ASN individuel dans ce projet.

**Endpoint score agrégé par pays — fonctionne**
GET https://observatory.manrs.org/api/v2/scores/summary?region={code_pays}
Piège : le paramètre s'appelle `region`, pas `country` ni `countryCode` comme on pourrait le deviner (les deux renvoient une erreur 422 "unknown query parameter"). Découvert empiriquement, non documenté clairement dans la doc publique.

Renvoie 5 catégories dans `scores.keyFigures` : `antiSpoofing`, `coordination`, `filtering`, `routingInformationIRR`, `routingInformationRPKI` — chacune avec un `value` (0 à 1) et une répartition `severities`.

Le projet ne retient que 4 de ces 5 catégories (cohérent avec le schéma `asn` à 4 actions) : `antiSpoofing`, `coordination`, `filtering`, `routingInformationRPKI`. `routingInformationIRR` est exclu (pas d'équivalent dans le schéma).

Calcul du score pays stocké dans `countries.avg_manrs_score` : moyenne des 4 `value` retenus, convertie en pourcentage (`moyenne * 100`, arrondi à 2 décimales).
## Cloudflare RPKI

**Pas d'endpoint par ASN individuel**
Le cahier des charges suggère `GET /api/v1/asn/{asn}/prefixes`, mais cet endpoint n'existe pas. La seule approche disponible : télécharger un fichier global unique et filtrer localement.

**Endpoint utilisé**
GET https://rpki.cloudflare.com/rpki.json
Fichier volumineux (~100 Mo, environ 996 000 ROA lors des tests). Téléchargé une seule fois par cycle de collecte (pas par ASN, ni par pays), gardé en mémoire pour toute la durée de `run_full_collection()`.

**Structure d'un ROA dans le fichier**
```json
{"asn": 13335, "prefix": "1.0.0.0/24", "maxLength": 24, "ta": "apnic", "expires": 1788358651}
```
- `asn` : l'ASN autorisé à annoncer ce préfixe
- `maxLength` : la longueur maximale de sous-préfixe couverte par ce ROA
- `ta` : la Trust Anchor (RIR) ayant signé le ROA (pour l'Afrique de l'Ouest : `afrinic`)

**Logique de calcul du `roa_status`**
Pour un préfixe annoncé par un ASN donné :
1. Chercher tous les ROA dont l'adresse de base correspond exactement au préfixe → si aucun, statut `not-found`
2. Parmi les ROA trouvés, vérifier s'il en existe un où l'ASN correspond ET où la longueur du préfixe est comprise entre la longueur du ROA et son `maxLength` → si oui, statut `valid`
3. Sinon (des ROA existent pour cette adresse, mais aucun ne valide notre ASN/longueur) → statut `invalid`

**Limitation assumée**
La recherche compare l'adresse de base exacte, pas le "plus long préfixe correspondant" (longest prefix match) qu'utiliserait une implémentation professionnelle avec une structure d'arbre radix (ex: librairie `pytricia`). Simplification volontaire, suffisante pour le scope de ce projet, mais qui pourrait manquer certains cas de couverture par un ROA plus général.

## Résumé des constats terrain

- Score MANRS moyen observé pour le Bénin : ~55% (test initial)
- Statut RPKI très faible dans la région : `routingInformationRPKI` à seulement ~19.5% pour le Bénin lors des tests (cohérent avec le grand nombre de préfixes `not-found` observés en base)
- Aucun des ASN ouest-africains testés n'est membre MANRS
