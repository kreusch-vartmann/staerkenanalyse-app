#!/usr/bin/env python3
"""Test-Script: Leere-Sektionen-Erkennung + generate + refine"""
import os, sys, re
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("TEST 1: _has_empty_sections")
print("=" * 60)
from ki_services import _clean_html_output, _has_empty_sections, _validate_task_content

html_empty = '<h3>Szenario</h3><p>Ein ausreichend langer Text fuer den Test.</p><h3>Ablauf</h3><h3>Materialien</h3>'
empty = _has_empty_sections(html_empty)
assert 'Ablauf' in empty and 'Materialien' in empty
assert 'Szenario' not in empty
print(f"  \u2713 Leere erkannt: {empty}")

html_ok = '<h3>Szenario</h3><p>Ein guter Text hier.</p><h3>Ablauf</h3><ol><li>Phase 1 Vorbereitung</li></ol><h3>Materialien</h3><ul><li>Flipchart-Papier</li></ul>'
assert len(_has_empty_sections(html_ok)) == 0
print("  ✓ Gefüllte Sektionen OK")

print("\n" + "=" * 60)
print("TEST 2: _validate_task_content")
print("=" * 60)

bad = '<h2>T</h2><h3>S</h3><p>Lang genug Text hier drin fuer den Test mit mehr als zweihundert Zeichen bitte danke schoen.</p><h3>Aufgabe</h3><p>Macht was.</p><h3>Ablauf</h3><h3>Mat</h3><ol><li>A</li><li>B</li><li>C</li></ol>'
v, r = _validate_task_content(bad)
assert not v, f"Sollte invalid sein wegen leerer Sektion, ist aber: {r}"
print(f"  ✓ Leere Sektion rejected: {r}")

print("\n" + "=" * 60)
print("TEST 3: generate_task (Mistral API)")
print("=" * 60)

from ki_services import generate_task
result = generate_task(
    observation_area="Soziale Kompetenzen",
    participant_count=4, duration_minutes=30, ki_model="mistral"
)

if result and result.get("content"):
    c = result["content"]
    print(f"  Titel: {result.get('title')}")
    print(f"  Länge: {len(c)}")
    empty = _has_empty_sections(c)
    print(f"  Leere Sektionen: {empty if empty else '✓ KEINE'}")
    v, r = _validate_task_content(c)
    print(f"  Validierung: {'✓' if v else '✗'} {r}")
    has_md = bool(re.search(r'\*\*[^<]+\*\*', c))
    print(f"  Markdown: {'✗ JA!' if has_md else '✓ NEIN'}")
    print(f"\n  --- Content ---\n  {c[:700]}\n  ---")
else:
    print("  ✗ FEHLGESCHLAGEN")

print("\n" + "=" * 60)
print("TEST 4: refine_task_content (Mistral API)")
print("=" * 60)

if result and result.get("content"):
    from ki_services import refine_task_content
    ref = refine_task_content(
        draft_content=result["content"],
        user_request="Mache das Szenario kürzer auf 2 Sätze",
        ki_model="mistral"
    )
    if ref and ref.get("updated_content"):
        rc = ref["updated_content"]
        changed = rc != result["content"]
        print(f"  Geändert: {'✓ JA' if changed else '✗ NEIN'}")
        empty = _has_empty_sections(rc)
        print(f"  Leere Sektionen: {empty if empty else '✓ KEINE'}")
        v, r = _validate_task_content(rc)
        print(f"  Validierung: {'✓' if v else '✗'} {r}")
        has_md = bool(re.search(r'\*\*[^<]+\*\*', rc))
        print(f"  Markdown: {'✗ JA!' if has_md else '✓ NEIN'}")
        print(f"\n  --- Refined ---\n  {rc[:700]}\n  ---")
    else:
        print("  ✗ FEHLGESCHLAGEN")

print("\n✅ TESTS ABGESCHLOSSEN")
