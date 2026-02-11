#!/usr/bin/env python3
"""Test-Skript für Chat-Refinement Validierung"""

import sys
import os

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ki_services import refine_task_content

# Test-Aufgabe mit vollständigem Content
test_draft = """<h2>Team-Challenge: Innovative Tech-Lounge</h2>

<h3>Szenario:</h3>
<p>Ihr seid das Führungsteam eines erfolgreichen Tech-Startups mit 150 Mitarbeitenden. Eure Firma hat gerade eine Serie-B-Finanzierung von 10 Millionen Euro erhalten und möchte einen Teil davon (50.000 €) in eine moderne Mitarbeiter-Lounge investieren. Der Vorstand hat euch beauftragt, ein innovatives Lounge-Konzept zu entwickeln, das drei Ziele erfüllt: (1) Die Mitarbeiterzufriedenheit steigern, (2) die Kreativität fördern, (3) den Teamgeist stärken. Die Lounge soll ein Ort werden, wo sich verschiedene Abteilungen begegnen, austauschen und gemeinsam entspannen können.</p>

<h3>Eure Aufgabe:</h3>
<p>Entwickelt in 25 Minuten ein überzeugendes Konzept für die Tech-Lounge. Bereitet eine 5-minütige Präsentation vor, in der jedes Teammitglied einen Teil vorstellt. Am Ende präsentiert ihr dem Vorstand (Moderator) eure Idee.</p>

<h3>Rollenverteilung:</h3>
<ul>
<li><strong>CEO:</strong> Koordiniert das Team, moderiert Diskussionen, trifft finale Entscheidungen bei Uneinigkeit</li>
<li><strong>CFO:</strong> Verantwortlich für Budget-Planung, Kosten-Kontrolle, ROI-Berechnung</li>
<li><strong>Head of HR:</strong> Fokus auf Mitarbeiterbedürfnisse, Umfragen, Feedback-Integration</li>
<li><strong>Head of Design:</strong> Entwickelt räumliches Konzept, Möblierung, Atmosphäre</li>
<li><strong>Head of IT:</strong> Integriert technische Features (VR, Smart-Tech, Gaming)</li>
<li><strong>Marketing Lead:</strong> Entwickelt Kommunikationsstrategie für Launch und Nutzung</li>
</ul>

<h3>Ablauf & Zeitvorgaben:</h3>
<ol>
<li><strong>Phase 1 (5 Min):</strong> Brainstorming - Sammelt Ideen für Lounge-Features (jeder bringt 2-3 Ideen)</li>
<li><strong>Phase 2 (10 Min):</strong> Konzept entwickeln - Einigt euch auf 5 Kern-Features, Budget verteilen</li>
<li><strong>Phase 3 (7 Min):</strong> Präsentation vorbereiten - Jeder übernimmt einen Teil (Rollen aufteilen)</li>
<li><strong>Phase 4 (3 Min):</strong> Pitch-Training - Ein Durchlauf der kompletten Präsentation</li>
</ol>

<h3>Materialien:</h3>
<ul>
<li>Flipchart-Papier (DIN A1, 3 Bögen)</li>
<li>Whiteboard-Marker (Set mit 6 Farben)</li>
<li>Post-its (3 Blöcke in verschiedenen Farben)</li>
<li>Stifte und Textmarker (je 6 Stück)</li>
<li>Budget-Tabelle (Vorlage)</li>
<li>Timer für Zeitmanagement</li>
</ul>"""

# Test-Anfrage
user_request = "Mache das Szenario kürzer und fokussiere auf die junge Zielgruppe"

print("=" * 80)
print("TEST: Chat-Refinement mit Mistral")
print("=" * 80)
print(f"\nUser-Request: {user_request}")
print(f"\nDraft Content Length: {len(test_draft)} chars\n")

# Führe Refinement aus
result = refine_task_content(
    draft_content=test_draft,
    user_request=user_request,
    conversation_history=[],
    ki_model="mistral"
)

print("\n" + "=" * 80)
print("ERGEBNIS:")
print("=" * 80)

if result and result.get("updated_content"):
    updated = result["updated_content"]
    print(f"\nAI Response: {result.get('ai_response', 'N/A')}")
    print(f"\nUpdated Content Length: {len(updated)} chars")
    
    # Analysiere den Content
    li_count = updated.count("<li")
    ul_count = updated.count("<ul")
    ol_count = updated.count("<ol")
    p_count = updated.count("<p")
    
    # Prüfe auf leere Listen
    import re
    empty_lists = re.findall(r'<ul>\s*</ul>|<ol>\s*</ol>', updated)
    
    print(f"\n--- STRUKTUR-ANALYSE ---")
    print(f"<ul> Tags: {ul_count}")
    print(f"<ol> Tags: {ol_count}")
    print(f"<li> Items: {li_count}")
    print(f"<p> Tags: {p_count}")
    print(f"Leere Listen gefunden: {len(empty_lists)}")
    
    if empty_lists:
        print(f"\n⚠️  WARNUNG: {len(empty_lists)} leere Listen gefunden!")
        for empty in empty_lists:
            print(f"   - {empty}")
    
    # Zeige Auszug
    print(f"\n--- CONTENT (erste 800 Zeichen) ---")
    print(updated[:800])
    print("\n...")
    
    # Zeige Listen-Sektionen
    print(f"\n--- LISTEN-SEKTIONEN ---")
    for section in ["Rollenverteilung", "Ablauf", "Materialien"]:
        if section in updated:
            idx = updated.find(section)
            snippet = updated[idx:idx+300]
            print(f"\n{section}:")
            print(snippet[:250] + "...")
else:
    print("\n❌ FEHLER: Kein Result oder kein updated_content")
    print(f"Result: {result}")

print("\n" + "=" * 80)
