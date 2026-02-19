#!/bin/bash
# search-events.sh - Recherche d'événements vérifiés par API/scraping
# Usage: ./search-events.sh [ville] [date] [rayon_km] [mot_cle]
# Exemple: ./search-events.sh "Paris" "2026-02-20" "5" "networking"

CITY="${1:-Paris}"
DATE="${2:-$(date +%Y-%m-%d)}"
RADIUS="${3:-10}"
KEYWORD="${4:-networking}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== RECHERCHE ÉVÉNEMENTS ===${NC}"
echo -e "Ville: $CITY | Date: $DATE | Rayon: ${RADIUS}km | Mot-clé: $KEYWORD"
echo ""

# Date range pour la journée
DATE_START="${DATE}T00:00:00"
DATE_END="${DATE}T23:59:59"

# --- EVENTBRITE (scraping page recherche) ---
echo -e "${YELLOW}[1/3] Eventbrite...${NC}"

# Encoder les paramètres
ENCODED_CITY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$CITY'))")
ENCODED_KEYWORD=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$KEYWORD'))")

# Eventbrite search URL avec date
EB_URL="https://www.eventbrite.fr/d/france--${ENCODED_CITY}/${ENCODED_KEYWORD}/?start_date=${DATE}&end_date=${DATE}"
echo "  URL: $EB_URL"

# Récupérer et parser la page
EB_RESULT=$(curl -s -L --max-time 10 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  "$EB_URL" 2>/dev/null)

if [ -n "$EB_RESULT" ]; then
  # Extraire les événements via le JSON embarqué dans la page
  echo "$EB_RESULT" | python3 -c "
import sys, re, json

html = sys.stdin.read()

# Chercher les données structurées JSON-LD
json_ld_matches = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
events_found = []

for match in json_ld_matches:
    try:
        data = json.loads(match)
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'Event':
                    events_found.append(item)
        elif isinstance(data, dict) and data.get('@type') == 'Event':
            events_found.append(data)
    except:
        pass

# Aussi chercher dans window.__SERVER_DATA__ ou similaire
server_data = re.findall(r'window\.__SERVER_DATA__\s*=\s*({.*?});', html, re.DOTALL)
for sd in server_data:
    try:
        data = json.loads(sd)
        if 'search_data' in data:
            for evt in data['search_data'].get('events', {}).get('results', []):
                events_found.append({
                    'name': evt.get('name', 'N/A'),
                    'startDate': evt.get('start_date', 'N/A'),
                    'location': evt.get('primary_venue', {}).get('address', {}).get('localized_address_display', 'N/A'),
                    'url': evt.get('url', 'N/A'),
                    'is_free': evt.get('is_free', False)
                })
    except:
        pass

if events_found:
    print(f'  Trouvé {len(events_found)} événement(s) Eventbrite:')
    for i, evt in enumerate(events_found[:10], 1):
        name = evt.get('name', evt.get('text', 'N/A'))
        if isinstance(name, dict):
            name = name.get('text', str(name))
        start = evt.get('startDate', evt.get('start_date', 'N/A'))
        location = evt.get('location', {})
        if isinstance(location, dict):
            loc_name = location.get('name', location.get('localized_address_display', 'N/A'))
        else:
            loc_name = str(location)
        url = evt.get('url', 'N/A')
        print(f'  [{i}] {name}')
        print(f'      Date: {start}')
        print(f'      Lieu: {loc_name}')
        print(f'      URL: {url}')
        print()
else:
    print('  Aucun événement trouvé sur Eventbrite pour cette date.')
" 2>/dev/null || echo "  Erreur parsing Eventbrite"
else
  echo "  Pas de réponse Eventbrite"
fi

echo ""

# --- MEETUP (via page web) ---
echo -e "${YELLOW}[2/3] Meetup...${NC}"

MEETUP_URL="https://www.meetup.com/fr-FR/find/?keywords=${ENCODED_KEYWORD}&location=${ENCODED_CITY}&source=EVENTS&distance=${RADIUS}km&dateRange=${DATE}"
echo "  URL: $MEETUP_URL"

MEETUP_RESULT=$(curl -s -L --max-time 10 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  "$MEETUP_URL" 2>/dev/null)

if [ -n "$MEETUP_RESULT" ]; then
  echo "$MEETUP_RESULT" | python3 -c "
import sys, re, json

html = sys.stdin.read()
json_ld_matches = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
events_found = []

for match in json_ld_matches:
    try:
        data = json.loads(match)
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'Event':
                    events_found.append(item)
        elif isinstance(data, dict) and data.get('@type') == 'Event':
            events_found.append(data)
    except:
        pass

# Chercher aussi dans le JSON embarqué Apollo/Next.js
apollo = re.findall(r'\"__typename\":\"Event\".*?\"title\":\"(.*?)\".*?\"dateTime\":\"(.*?)\"', html)
for title, dt in apollo[:10]:
    events_found.append({'name': title, 'startDate': dt})

if events_found:
    print(f'  Trouvé {len(events_found)} événement(s) Meetup:')
    for i, evt in enumerate(events_found[:10], 1):
        name = evt.get('name', 'N/A')
        start = evt.get('startDate', evt.get('dateTime', 'N/A'))
        url = evt.get('url', 'N/A')
        print(f'  [{i}] {name}')
        print(f'      Date: {start}')
        print(f'      URL: {url}')
        print()
else:
    print('  Aucun événement Meetup trouvé pour cette date.')
" 2>/dev/null || echo "  Erreur parsing Meetup"
else
  echo "  Pas de réponse Meetup"
fi

echo ""

# --- BILLETWEB ---
echo -e "${YELLOW}[3/3] Billetweb...${NC}"

BW_URL="https://www.billetweb.fr/recherche?q=${ENCODED_KEYWORD}&l=${ENCODED_CITY}&d=${DATE}"
echo "  URL: $BW_URL"

BW_RESULT=$(curl -s -L --max-time 10 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  "$BW_URL" 2>/dev/null)

if [ -n "$BW_RESULT" ]; then
  echo "$BW_RESULT" | python3 -c "
import sys, re, json

html = sys.stdin.read()
json_ld_matches = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
events_found = []

for match in json_ld_matches:
    try:
        data = json.loads(match)
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'Event':
                    events_found.append(item)
        elif isinstance(data, dict) and data.get('@type') == 'Event':
            events_found.append(data)
    except:
        pass

if events_found:
    print(f'  Trouvé {len(events_found)} événement(s) Billetweb:')
    for i, evt in enumerate(events_found[:10], 1):
        name = evt.get('name', 'N/A')
        start = evt.get('startDate', 'N/A')
        url = evt.get('url', 'N/A')
        loc = evt.get('location', {})
        loc_name = loc.get('name', 'N/A') if isinstance(loc, dict) else str(loc)
        print(f'  [{i}] {name}')
        print(f'      Date: {start}')
        print(f'      Lieu: {loc_name}')
        print(f'      URL: {url}')
        print()
else:
    print('  Aucun événement Billetweb trouvé pour cette date.')
" 2>/dev/null || echo "  Erreur parsing Billetweb"
else
  echo "  Pas de réponse Billetweb"
fi

echo -e "${GREEN}=== FIN RECHERCHE ===${NC}"
