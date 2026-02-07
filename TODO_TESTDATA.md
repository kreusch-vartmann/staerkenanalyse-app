# TODO: Testdaten-Generator (✅ ERLEDIGT)

**Status:** ✅ Implementiert  
**Priorität:** Abgeschlossen  
**Erstellt:** 2026-02-07  
**Fertiggestellt:** 2026-02-07

## ✅ Was wurde umgesetzt

### Implementierung komplett

**Neues Modul:** `generate_test_data.py`

**Flask CLI Command:**
```bash
flask generate-test-data [--groups N] [--participants X-Y] [--clear]
```

**Features:**
- ✅ LiteLLM-Integration für realistische deutsche Namen
- ✅ Gruppen mit Fake-Daten (Städte, Datum, Leiter, Beobachter)
- ✅ Participants mit vollständigen Daten:
  - Beobachtungen (KI-generiert, 50-80 Wörter)
  - SK/VK Ratings (zufällig 0-10, Summe max 25)
  - KI-Texte (HTML, 100-130 Wörter)
  - Footer-Daten
- ✅ SelfAssessments für ~65% (HTML, 180-220 Wörter)
- ✅ Fallback bei API-Fehler (generische Daten)
- ✅ Fortschrittsanzeige im Terminal
- ✅ `--clear` Option mit Sicherheitsabfrage

**Dokumentation:**
- ✅ `MIGRATION_GUIDE.md` - Schritt-für-Schritt-Anleitung
- ✅ In `app.py` registriert
- ✅ Inline-Dokumentation vorhanden

---

## 📋 Nutzung

Siehe: **`MIGRATION_GUIDE.md`** für vollständige Anleitung.

**Quickstart:**
```bash
# 1. Realdaten exportieren (manuell im Browser)
# 2. Gruppen löschen (manuell im Browser)

# 3. Testdaten generieren
flask generate-test-data

# Oder mit mehr Daten:
flask generate-test-data --groups 4 --participants 12-15
```

---

## 🎯 Ergebnis

Keine realen Nutzerdaten mehr im System → Datenschutz-Risiko eliminiert ✅
