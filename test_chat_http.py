#!/usr/bin/env python3
"""Test Chat-Refinement über HTTP (wie Browser)"""
import requests
import json

# Test-Daten
task_id = 1  # Anpassen an echte Task-ID
test_request = {
    "message": "Mache das Szenario deutlich kürzer",
    "current_content": """<h2>Test-Aufgabe: Team-Challenge</h2>

<h3>Szenario:</h3>
<p>Ihr seid das Managementteam der TechInnovate GmbH, einem mittelständischen Softwareunternehmen mit 200 Mitarbeitenden. Nach einem erfolgreichen Jahr habt ihr ein Budget von 100.000 € für eine strategische Initiative erhalten. Der Vorstand erwartet von euch einen konkreten Plan, wie dieses Budget eingesetzt werden soll, um das Unternehmen weiterzuentwickeln. Drei Bereiche stehen zur Auswahl: (1) Digitale Transformation der internen Prozesse, (2) Expansion in neue Märkte, (3) Weiterbildung und Mitarbeiterentwicklung.</p>

<h3>Eure Aufgabe:</h3>
<p>Entwickelt in 30 Minuten ein überzeugendes Konzept für den Einsatz des Budgets. Bereitet eine 5-minütige Präsentation vor, in der jedes Teammitglied einen Teil vorstellt.</p>

<h3>Rollenverteilung:</h3>
<ul>
<li><strong>CEO:</strong> Koordiniert das Team und trifft finale Entscheidungen</li>
<li><strong>CFO:</strong> Verantwortlich für Budget-Planung und Kosten-Kontrolle</li>
<li><strong>Head of HR:</strong> Fokus auf Mitarbeiterentwicklung</li>
<li><strong>CTO:</strong> Verantwortlich für technische Aspekte</li>
<li><strong>Marketing Lead:</strong> Entwickelt Kommunikationsstrategie</li>
</ul>

<h3>Ablauf & Zeitvorgaben:</h3>
<ol>
<li><strong>Phase 1 (10 Min):</strong> Brainstorming - Ideen sammeln</li>
<li><strong>Phase 2 (15 Min):</strong> Konzept entwickeln und Budget verteilen</li>
<li><strong>Phase 3 (5 Min):</strong> Präsentation vorbereiten</li>
</ol>

<h3>Materialien:</h3>
<ul>
<li>Flipchart-Papier (DIN A1, 3 Bögen)</li>
<li>Whiteboard-Marker (Set mit 6 Farben)</li>
<li>Post-its (3 Blöcke)</li>
<li>Stifte (6 Stück)</li>
<li>Budget-Tabelle (Vorlage)</li>
</ul>"""
}

base_url = "http://127.0.0.1:5001"

# Session für Cookies (Login)
session = requests.Session()

print("=" * 80)
print("LIVE-TEST: Chat-Refinement über HTTP")
print("=" * 80)

# 1. Login (anpassen an echte Credentials)
login_data = {
    "username": "admin",  # ANPASSEN!
    "password": "admin"   # ANPASSEN!
}

print("\n1. Login versuch...")
try:
    r = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"   Status: {r.status_code}")
    if r.status_code in [200, 302]:
        print("   ✓ Login erfolgreich")
    else:
        print(f"   ✗ Login fehlgeschlagen: {r.status_code}")
        print("   BITTE CREDENTIALS IN SKRIPT ANPASSEN!")
        exit(1)
except Exception as e:
    print(f"   ✗ Fehler: {e}")
    exit(1)

# 2. Chat-Request senden
print(f"\n2. Chat-Request an /beobachtungsaufgaben/{task_id}/chat")
print(f"   Message: {test_request['message']}")
print(f"   Current Content Length: {len(test_request['current_content'])} chars")

try:
    # CSRF-Token holen (wenn nötig)
    # Für den Test ignorieren wir CSRF
    session.headers.update({'X-Requested-With': 'XMLHttpRequest'})
    
    r = session.post(
        f"{base_url}/beobachtungsaufgaben/{task_id}/chat",
        json=test_request,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"\n   Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"\n   ✓ Response erfolgreich")
        print(f"\n   --- RESPONSE DATA ---")
        print(f"   status: {data.get('status')}")
        print(f"   ai_response: {data.get('ai_response')}")
        
        updated = data.get('updated_content', '')
        print(f"   updated_content length: {len(updated)} chars")
        
        if updated:
            # Analysiere Content
            li_count = updated.count('<li')
            ul_count = updated.count('<ul')
            p_count = updated.count('<p')
            
            print(f"\n   --- CONTENT ANALYSE ---")
            print(f"   <ul> tags: {ul_count}")
            print(f"   <li> items: {li_count}")
            print(f"   <p> tags: {p_count}")
            
            print(f"\n   --- UPDATED CONTENT (erste 500 chars) ---")
            print(updated[:500])
            print("\n   ...")
            
            # Vergleich: Hat sich was geändert?
            original_len = len(test_request['current_content'])
            if abs(len(updated) - original_len) > 100:
                print(f"\n   ✓ Content hat sich deutlich geändert ({original_len} → {len(updated)} chars)")
            else:
                print(f"\n   ⚠️  Content-Länge fast identisch ({original_len} → {len(updated)} chars)")
        else:
            print("   ✗ KEIN updated_content in Response!")
    else:
        print(f"   ✗ Fehler: {r.status_code}")
        print(f"   Response: {r.text[:500]}")
        
except Exception as e:
    print(f"   ✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
