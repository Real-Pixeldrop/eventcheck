#!/usr/bin/env python3
"""
verify-event.py - Double vérification d'événements : API Eventbrite + parsing HTML
Usage: python3 verify-event.py <url> [date_cible YYYY-MM-DD]
"""

import sys
import json
import re
import urllib.request
from datetime import datetime

import os

API_KEY_PATH = os.environ.get("EVENTBRITE_API_KEY_PATH", os.path.expanduser("~/.config/eventbrite/api_key"))

def get_api_key():
    """Lire la clé API Eventbrite"""
    try:
        with open(API_KEY_PATH) as f:
            return f.read().strip()
    except:
        return None

def fetch_page(url):
    """Fetch une page web et retourne le HTML"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def fetch_json(url, token=None):
    """Fetch une URL JSON avec auth optionnelle"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except:
        return None

def extract_eventbrite_id(url):
    """Extraire l'ID d'un event Eventbrite depuis l'URL"""
    # Format: /e/billets-xxx-123456 ou /e/xxx-123456
    match = re.search(r'-(\d{10,})(?:\?|$|/)', url)
    if match:
        return match.group(1)
    # Format: /e/123456
    match = re.search(r'/e/(\d+)', url)
    if match:
        return match.group(1)
    return None

def verify_eventbrite_api(url):
    """Vérifier via l'API Eventbrite (source 1)"""
    token = get_api_key()
    if not token:
        return None
    
    event_id = extract_eventbrite_id(url)
    if not event_id:
        return None
    
    data = fetch_json(f"https://www.eventbriteapi.com/v3/events/{event_id}/?expand=venue", token)
    if not data or 'id' not in data:
        return None
    
    venue = data.get('venue', {}) or {}
    address = venue.get('address', {}) or {}
    
    return {
        'source': 'eventbrite_api',
        'name': data.get('name', {}).get('text', 'N/A'),
        'date': data.get('start', {}).get('local', 'N/A'),
        'end_date': data.get('end', {}).get('local', 'N/A'),
        'timezone': data.get('start', {}).get('timezone', 'N/A'),
        'location': venue.get('name', 'N/A'),
        'address': address.get('localized_address_display', address.get('address_1', 'N/A')),
        'status': data.get('status', 'N/A'),
        'url': data.get('url', url),
        'verified': True
    }

def extract_json_ld(html):
    """Extraire les données JSON-LD d'une page"""
    events = []
    matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') in ('Event', 'SocialEvent', 'BusinessEvent', 'MusicEvent', 'SportEvent'):
                        events.append(item)
            elif isinstance(data, dict):
                if data.get('@type') in ('Event', 'SocialEvent', 'BusinessEvent', 'MusicEvent', 'SportEvent'):
                    events.append(data)
                elif data.get('@type') == 'ItemList':
                    for item in data.get('itemListElement', []):
                        if item.get('@type') == 'Event':
                            events.append(item)
        except json.JSONDecodeError:
            pass
    return events

def verify_html(html, url):
    """Vérifier via parsing HTML/JSON-LD (source 2)"""
    events = extract_json_ld(html)
    if events:
        evt = events[0]
        loc = evt.get('location', {})
        if isinstance(loc, dict):
            location_name = loc.get('name', 'N/A')
            addr = loc.get('address', {})
            if isinstance(addr, dict):
                address = addr.get('streetAddress', addr.get('name', 'N/A'))
            else:
                address = str(addr) if addr else 'N/A'
        else:
            location_name = 'N/A'
            address = 'N/A'
        
        return {
            'source': 'html_json_ld',
            'name': evt.get('name', 'N/A'),
            'date': evt.get('startDate', 'N/A'),
            'end_date': evt.get('endDate', 'N/A'),
            'location': location_name,
            'address': address,
            'url': url,
            'verified': True
        }
    
    # Fallback Eventbrite : datetime dans le HTML
    if 'eventbrite' in url.lower():
        date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})', html)
        title_match = re.search(r'<title>(.*?)</title>', html)
        if date_match:
            return {
                'source': 'html_fallback',
                'name': title_match.group(1) if title_match else 'N/A',
                'date': date_match.group(1),
                'url': url,
                'verified': True
            }
    
    # Fallback Billetweb
    if 'billetweb' in url.lower():
        title_match = re.search(r'<title>(.*?)</title>', html)
        date_match = re.search(r'(\w+ \w+ \d+, \d{4})', html)
        if not date_match:
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', html)
        if title_match:
            return {
                'source': 'billetweb_html',
                'name': title_match.group(1).split(' - ')[0].strip() if ' - ' in title_match.group(1) else title_match.group(1),
                'date': date_match.group(1) if date_match else 'N/A',
                'url': url,
                'verified': True,
                'note': 'Parsed from HTML (no JSON-LD)'
            }
    
    # Page 404
    if 'Impossible de trouver' in html or '404' in html[:500]:
        return {'verified': False, 'reason': 'Page 404 - Événement supprimé ou inexistant'}
    
    return None

def parse_date(date_str):
    """Parser une date depuis différents formats"""
    if not date_str or date_str == 'N/A':
        return None
    # Nettoyer timezone
    clean = re.sub(r'[+-]\d{2}:\d{2}$', '', str(date_str))
    clean = re.sub(r'Z$', '', clean)
    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d']:
        try:
            return datetime.strptime(clean, fmt)
        except:
            continue
    return None

def check_date_match(event_date_str, target_date_str):
    """Vérifier si la date correspond"""
    event_dt = parse_date(event_date_str)
    if not event_dt:
        return None
    try:
        target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')
        return event_dt.date() == target_dt.date()
    except:
        return None

def verify_event(url, target_date=None):
    """Double vérification : API + HTML"""
    results = []
    api_result = None
    html_result = None
    
    # SOURCE 1 : API Eventbrite (si c'est un lien Eventbrite)
    if 'eventbrite' in url.lower():
        api_result = verify_eventbrite_api(url)
        if api_result:
            results.append(api_result)
    
    # SOURCE 2 : Parsing HTML (toujours)
    html = fetch_page(url)
    if html:
        html_result = verify_html(html, url)
        if html_result:
            results.append(html_result)
    
    if not results:
        return {
            'verified': False,
            'reason': 'Aucune source n\'a pu vérifier cet événement',
            'sources_checked': ['api' if 'eventbrite' in url.lower() else None, 'html'],
        }
    
    # Comparer les deux sources si disponibles
    primary = results[0]
    
    if len(results) == 2:
        api_date = parse_date(results[0].get('date', ''))
        html_date = parse_date(results[1].get('date', ''))
        
        if api_date and html_date:
            if api_date.date() == html_date.date():
                primary['cross_verified'] = True
                primary['verification'] = 'API + HTML concordent'
            else:
                primary['cross_verified'] = False
                primary['verification'] = f'ATTENTION : API dit {api_date.date()}, HTML dit {html_date.date()}'
                primary['html_date'] = str(html_date.date())
        else:
            primary['cross_verified'] = None
            primary['verification'] = 'Une seule source datée'
    else:
        primary['verification'] = f'Source unique : {primary["source"]}'
    
    # Vérification date cible
    if target_date:
        match = check_date_match(primary.get('date', ''), target_date)
        primary['target_date'] = target_date
        primary['date_matches_target'] = match
    
    primary['sources_count'] = len(results)
    return primary

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 verify-event.py <url> [date_cible YYYY-MM-DD]")
        sys.exit(1)
    
    url = sys.argv[1]
    target_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = verify_event(url, target_date)
    
    if result.get('verified'):
        sources = result.get('sources_count', 1)
        cross = result.get('cross_verified')
        
        if cross is True:
            print(f"✅ DOUBLEMENT VÉRIFIÉ ({sources} sources concordantes)")
        elif cross is False:
            print(f"⚠️  VÉRIFIÉ MAIS SOURCES DISCORDANTES")
        else:
            print(f"✅ VÉRIFIÉ (source : {result.get('source', '?')})")
        
        print(f"   Nom: {result.get('name', 'N/A')}")
        print(f"   Date: {result.get('date', 'N/A')}")
        if result.get('end_date') and result['end_date'] != 'N/A':
            print(f"   Fin: {result['end_date']}")
        if result.get('timezone') and result['timezone'] != 'N/A':
            print(f"   TZ: {result['timezone']}")
        print(f"   Lieu: {result.get('location', 'N/A')}")
        if result.get('address') and result['address'] != 'N/A':
            print(f"   Adresse: {result['address']}")
        if result.get('status') and result['status'] != 'N/A':
            print(f"   Statut: {result['status']}")
        print(f"   Vérification: {result.get('verification', '?')}")
        print(f"   URL: {result.get('url', 'N/A')}")
        
        if target_date:
            match = result.get('date_matches_target')
            if match is True:
                print(f"   📅 Date correspond a {target_date} ✅")
            elif match is False:
                print(f"   ⚠️  DATE NE CORRESPOND PAS a {target_date} ❌")
            else:
                print(f"   ⚠️  Impossible de vérifier la date cible")
    else:
        print(f"❌ NON VÉRIFIÉ")
        print(f"   Raison: {result.get('reason', 'Inconnue')}")
    
    print(f"\n---JSON---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
