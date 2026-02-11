#!/usr/bin/env python3
"""Direkter Test der refine_task_content Funktion mit Mistral"""
import sys
sys.path.insert(0, '/home/timok/kDrive/Dokumente/staerkenanalyse-app')

from ki_services import refine_task_content

# Test-Aufgabe
test_draft = """<h2>Team-Challenge: Krisenmanagement Projekt GreenOffice</h2>

<h3>Szenario:</h3>
<p>Ihr seid das Projektteam von "GreenOffice", einem internen Nachhaltigkeitsprojekt eines mittelständischen Unternehmens mit 500 Mitarbeitenden. Ziel ist es, die CO2-Bilanz des Bürobetriebs bis Ende des Jahres um 30% zu senken. Doch plötzlich gibt es eine Krise: Der Hauptlieferant für umweltfreundliche Büromaterialien ist insolvent, das Budget wurde um 40% gekürzt, und die Geschäftsführung fordert trotzdem Ergebnisse in nur 6 Wochen statt wie geplant 6 Monaten. Gleichzeitig gibt es Widerstand aus verschiedenen Abteilungen, die befürchten, dass die Umstellung ihre tägliche Arbeit behindert.</p>

<h3>Eure Aufgabe:</h3>
<p>Entwickelt in 30 Minuten einen Notfallplan, wie ihr das Projekt trotz aller Widrigkeiten noch rechtzeitig umsetzen könnt. Bereitet eine 5-minütige Präsentation vor, in der jedes Teammitglied einen Teil vorstellt.</p>

<h3>Rollenverteilung:</h3>
<ul>
<li><strong>Projektleiter:in (Sarah Weber):</strong> Koordiniert das Team, moderiert die Diskussion, trifft finale Entscheidungen bei Meinungsverschiedenheiten</li>
<li><strong>Budget-Manager:in (Tom Fischer):</strong> Verantwortlich für die Umpriorisierung des gekürzten Budgets und Kosten-Nutzen-Analysen</li>
<li><strong>Nachhaltigkeitsexpert:in (Lisa Grün):</strong> Entwickelt alternative Lösungen für ausgefallene Lieferanten und prüft ökologische Standards</li>
<li><strong>Change Management (David Klein):</strong> Kümmert sich um Kommunikation mit Abteilungen und entwickelt Strategien gegen Widerstände</li>
<li><strong>Operations Manager:in (Anna Berger):</strong> Plant die konkrete Umsetzung und Zeitpläne, sorgt für Machbarkeit</li>
</ul>

<h3>Ablauf & Zeitvorgaben:</h3>
<ol>
<li><strong>Phase 1 (5 Min): Problemanalyse</strong> - Welche Punkte der Krise sind am kritischsten? Prioritäten setzen.</li>
<li><strong>Phase 2 (15 Min): Lösungsentwicklung</strong> - Brainstorming für alternative Ansätze, Budget neu verteilen, Quick Wins identifizieren</li>
<li><strong>Phase 3 (7 Min): Maßnahmenplan</strong> - Konkrete Schritte mit Verantwortlichen und Deadlines festlegen</li>
<li><strong>Phase 4 (3 Min): Präsentation vorbereiten</strong> - Rollen für 5-Min-Pitch aufteilen</li>
</ol>

<h3>Materialien:</h3>
<ul>
<li>Flipchart-Papier (DIN A1, 4 Bögen)</li>
<li>Whiteboard-Marker (Set mit 8 Farben)</li>
<li>Post-its in 4 Farben (je 1 Block)</li>
<li>Stifte und Textmarker (je 6 Stück)</li>
<li>Ausgedruckte Budget-Tabelle (Original + gekürzt)</li>
<li>Timer für Zeitmanagement</li>
<li>Vorlagen: Stakeholder-Matrix, Prioritäts-Grid</li>
</ul>"""

print("=" * 80)
print("DIREKTER TEST: refine_task_content() mit Mistral")
print("=" * 80)

# Test 1: Kürzere Aufgabe
print("\n\nTEST 1: 'Mache das Szenario deutlich kürzer'")
print("-" * 80)

result1 = refine_task_content(
    draft_content=test_draft,
    user_request="Mache das Szenario deutlich kürzer - maximal 80 Wörter",
    conversation_history=[],
    ki_model="mistral"
)

if result1 and result1.get('updated_content'):
    updated = result1['updated_content']
    print(f"\n✓ Response erhalten")
    print(f"  AI Response: {result1.get('ai_response')}")
    print(f"  Content Length: {len(updated)} chars (Original: {len(test_draft)} chars)")
    
    # Zähle Szenario-Länge
    import re
    scenario_match = re.search(r'<h3>Szenario:</h3>\s*<p>(.*?)</p>', updated, re.DOTALL)
    if scenario_match:
        scenario_text = scenario_match.group(1)
        word_count = len(scenario_text.split())
        print(f"  Szenario: {word_count} Wörter (sollte ~80 sein)")
        print(f"  Szenario-Text: {scenario_text[:200]}...")
    
    # Struktur-Check
    li_count = updated.count('<li')
    print(f"  <li> Items: {li_count}")
    
    # Zeige ersten Teil
    print(f"\n  --- UPDATED CONTENT (erste 600 chars) ---")
    print(updated[:600])
    print("  ...")
else:
    print("✗ FEHLER: Keine Response!")
    print(f"  Result: {result1}")

# Test 2: Thema ändern
print("\n\n" + "=" * 80)
print("TEST 2: 'Ändere das Thema von Nachhaltigkeit zu Digitalisierung'")
print("-" * 80)

result2 = refine_task_content(
    draft_content=test_draft,
    user_request="Ändere das Thema komplett: Statt Nachhaltigkeit geht es jetzt um die Einführung neuer Collaboration-Software im Unternehmen",
    conversation_history=[],
    ki_model="mistral"
)

if result2 and result2.get('updated_content'):
    updated2 = result2['updated_content']
    print(f"\n✓ Response erhalten")
    print(f"  Content Length: {len(updated2)} chars")
    
    # Prüfe ob Thema geändert wurde
    if 'nachhaltigkeit' in updated2.lower():
        print("  ⚠️  'Nachhaltigkeit' noch im Text!")
    if 'software' in updated2.lower() or 'digital' in updated2.lower():
        print("  ✓ Neues Thema (Software/Digitalisierung) vorhanden")
    
    # Zeige Szenario
    scenario_match = re.search(r'<h3>Szenario:</h3>\s*<p>(.*?)</p>', updated2, re.DOTALL)
    if scenario_match:
        print(f"\n  --- NEUES SZENARIO ---")
        print(scenario_match.group(1)[:400])
        print("  ...")

print("\n" + "=" * 80)
print("TESTS ABGESCHLOSSEN")
print("=" * 80)
