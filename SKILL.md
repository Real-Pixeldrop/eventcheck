---
name: eventcheck
description: "Verify event dates and details from URLs (Eventbrite, Meetup, Billetweb, and any site with JSON-LD). Use when sharing event links to prevent wrong-date disasters. Double verification: Eventbrite API + HTML parsing. Catches date mismatches between search results and actual event pages."
---

# EventCheck

Verify events before sharing them. Search engines and AI often mix up event dates. This skill checks the actual source page.

## How it works

Two verification layers:
1. **Eventbrite API** (when URL is Eventbrite) - structured data, reliable
2. **HTML/JSON-LD parsing** (all sites) - reads schema.org event data from the page

When both sources are available, cross-checks them. Flags any discrepancies.

## Usage

### Verify a single event
```bash
python3 scripts/verify-event.py "https://eventbrite.com/e/my-event-123456" "2026-03-15"
```

Output:
- Event name, date, location, address
- Whether the date matches your target date
- Cross-verification status (if multiple sources available)

### Search events by city/date
```bash
bash scripts/search-events.sh [city] [date] [radius_km] [keyword]
# Example:
bash scripts/search-events.sh Paris 2026-03-15 10 networking
```

Searches Eventbrite, Meetup, and Billetweb, then verifies each result.

## Setup

### Optional: Eventbrite API key
Store your Eventbrite API token for double verification:
```bash
mkdir -p ~/.config/eventbrite
echo "YOUR_TOKEN" > ~/.config/eventbrite/api_key
```
Get a free key at https://www.eventbrite.com/platform/api-keys

Without an API key, the skill still works via HTML parsing (single source).

## Supported platforms

| Platform | API | HTML/JSON-LD | Notes |
|----------|-----|-------------|-------|
| Eventbrite | Yes | Yes | Double verification when API key set |
| Meetup | No | Yes | JSON-LD parsing |
| Billetweb | No | Partial | Title + date from HTML |
| Any site with schema.org Event | No | Yes | Generic JSON-LD parsing |

## Important rule

ALWAYS verify event dates on the source page before sharing links. Search engine results frequently show wrong dates.
