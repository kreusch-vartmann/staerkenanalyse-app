# RBAC Manuelle Test-Checkliste

**Datum**: 13. Februar 2026  
**Ziel**: Validiere RBAC-Permissions manuell für folgende Szenarien:
- Admin-Rolle (all-access)
- Beobachter-Rolle (limited access)
- Custom Roles (spezifische Permissions)

---

## Setup für Tests

### Voraussetzungen
1. Flask-App läuft: `FLASK_APP=app.py flask run --port 5002`
2. Browser-Konsole offen (F12 → Console)
3. Zwei separate Browser-Fenster/Tabs bereit (Admin + Beobachter)

### Test-Benutzer vorbereiten
```bash
# In Python REPL oder über Flask Shell:
# Admin-Benutzer existiert: admin@test.de / testpassword123
# Beobachter-Benutzer existiert: observer@test.de / testpassword123
```

---

## Test-Matrix: Admin-Rolle

| Seite/Aktion | URL | Sichtbar | Erlaubt | Status |
|---|---|---|---|---|
| **Gruppen verwalten** | `/groups` | ✓ | ✓ | [ ] |
| → Neue Gruppe Button | - | ✓ (Admin) | ✓ | [ ] |
| → Edit Group Button | - | ✓ (Admin) | ✓ | [ ] |
| → Delete Group Button | - | ✓ (Admin) | ✓ | [ ] |
| → Aufgaben verwalten Modal | - | ✓ (Admin) | ✓ | [ ] |
| **Teilnehmer verwalten** | `/participants` | ✓ | ✓ | [ ] |
| → Teilnehmer hinzufügen | - | ✓ (Admin) | ✓ | [ ] |
| → Selbsteinschätzung Link | - | ✓ (Admin) | ✓ | [ ] |
| → Beobachtungsdaten Link | - | ✓ (Admin) | ✓ | [ ] |
| → KI-Analyse Link | - | ✓ (Admin) | ✓ | [ ] |
| → Fremdeinschätzung Link | - | ✓ (Admin) | ✓ | [ ] |
| → Abschlussbericht Link | - | ✓ (Admin) | ✓ | [ ] |
| → Edit Participant Button | - | ✓ (Admin) | ✓ | [ ] |
| → Delete Participant Button | - | ✓ (Admin) | ✓ | [ ] |
| **Beobachtungsaufgaben** | `/tasks` | ✓ | ✓ | [ ] |
| → Neue Aufgabe Button | - | ✓ (Admin) | ✓ | [ ] |
| → Edit Task Button | - | ✓ (Admin) | ✓ | [ ] |
| → Aufgabe löschen | - | ✓ (Admin) | ✓ | [ ] |
| **KI-Analyse** | `/analysis` | ✓ | ✓ | [ ] |
| → Bericht bearbeiten | - | ✓ (Admin) | ✓ | [ ] |
| → Fremdeinschätzung verwalten | - | ✓ (Admin) | ✓ | [ ] |
| **Admin-Panel** | `/admin/users` | ✓ | ✓ | [ ] |
| → Benutzer verwalten | - | ✓ (Admin) | ✓ | [ ] |
| → Rollen verwalten | `/admin/roles` | ✓ | ✓ | [ ] |
| → Neue Rolle erstellen | - | ✓ (Admin) | ✓ | [ ] |

---

## Test-Matrix: Beobachter-Rolle

| Seite/Aktion | URL | Sichtbar | Erlaubt | Status |
|---|---|---|---|---|
| **Gruppen verwalten** | `/groups` | ✓ | ✓ | [ ] |
| → Neue Gruppe Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Edit Group Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Delete Group Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Aufgaben verwalten Modal | - | ✗ (versteckt) | ✗ (403) | [ ] |
| **Teilnehmer verwalten** | `/participants` | ✓ | ✓ | [ ] |
| → Teilnehmer hinzufügen | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Selbsteinschätzung Link | - | ✓ | ✓ | [ ] |
| → Beobachtungsdaten Link | - | ✓ | ✓ | [ ] |
| → KI-Analyse Link | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Fremdeinschätzung Link | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Abschlussbericht Link | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Edit Participant Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Delete Participant Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| **Beobachtungsaufgaben** | `/tasks` | ✓ | ✓ | [ ] |
| → Neue Aufgabe Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Edit Task Button | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Aufgabe löschen | - | ✗ (versteckt) | ✗ (403) | [ ] |
| **KI-Analyse** | `/analysis` | ✗ (versteckt) | ✗ (403) | [ ] |
| **Admin-Panel** | `/admin/users` | ✗ (versteckt) | ✗ (403) | [ ] |
| → Benutzer verwalten | - | ✗ (versteckt) | ✗ (403) | [ ] |
| → Rollen verwalten | - | ✗ (versteckt) | ✗ (403) | [ ] |

---

## Manuelle Test-Schritte

### Test 1: Admin - Gruppen Management
**Rolle**: Admin  
**Schritte**:
1. Login als admin@test.de
2. Navigiere zu `/groups`
3. [ ] Überprüfe: "Neue Gruppe" Button ist **sichtbar**
4. Scrolle nach unten zu existierender Gruppe
5. [ ] Überprüfe: Edit-Button neben jeder Gruppe ist **sichtbar**
6. [ ] Überprüfe: Delete-Button neben jeder Gruppe ist **sichtbar**
7. [ ] Überprüfe: "Aufgaben verwalten" Button ist **sichtbar**
8. Klick auf "Neue Gruppe" Button
9. [ ] Überprüfe: Modal öffnet sich
10. [ ] Überprüfe: Formular laden ohne Fehler
11. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 2: Admin - Teilnehmer Management
**Rolle**: Admin  
**Schritte**:
1. Login als admin@test.de
2. Navigiere zu `/participants`
3. [ ] Überprüfe: "Teilnehmer hinzufügen" Form ist **sichtbar**
4. Scrolle zu existierendem Teilnehmer
5. [ ] Überprüfe: "Selbsteinschätzung" Link ist **sichtbar** und funktioniert
6. [ ] Überprüfe: "Beobachtungsdaten" Link ist **sichtbar** und funktioniert
7. [ ] Überprüfe: "KI-Analyse" Link ist **sichtbar** und funktioniert (oder 403)
8. [ ] Überprüfe: "Fremdeinschätzung" Link ist **sichtbar**
9. [ ] Überprüfe: "Abschlussbericht" Link ist **sichtbar**
10. [ ] Überprüfe: Edit-Button ist **sichtbar** und funktioniert
11. [ ] Überprüfe: Delete-Button ist **sichtbar** und funktioniert
12. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 3: Beobachter - Gruppen Management
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de (separate Browser-Fenster/Tab)
2. Navigiere zu `/groups`
3. [ ] Überprüfe: "Neue Gruppe" Button ist **NICHT sichtbar** (versteckt)
4. [ ] Überprüfe: Edit-Buttons sind **NICHT sichtbar** (versteckt)
5. [ ] Überprüfe: Delete-Buttons sind **NICHT sichtbar** (versteckt)
6. [ ] Überprüfe: "Aufgaben verwalten" Modal ist **NICHT sichtbar** (versteckt)
7. Versuche manuell: POST zu `/group/add`
8. [ ] Überprüfe: Erhältst 403 Forbidden oder Redirect zu Home
9. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 4: Beobachter - Teilnehmer Management
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Navigiere zu `/participants`
3. [ ] Überprüfe: "Teilnehmer hinzufügen" Form ist **NICHT sichtbar** (versteckt)
4. Scrolle zu existierendem Teilnehmer
5. [ ] Überprüfe: "Selbsteinschätzung" Link ist **sichtbar** (Beobachter darf data_entry.view)
6. [ ] Überprüfe: "Beobachtungsdaten" Link ist **sichtbar** (Beobachter darf data_entry.view)
7. [ ] Überprüfe: "KI-Analyse" Link ist **NICHT sichtbar** (Beobachter darf NICHT analysis.run)
8. [ ] Überprüfe: "Fremdeinschätzung" Link ist **NICHT sichtbar** (versteckt)
9. [ ] Überprüfe: "Abschlussbericht" Link ist **NICHT sichtbar** (versteckt)
10. [ ] Überprüfe: Edit-Button ist **NICHT sichtbar** (versteckt)
11. [ ] Überprüfe: Delete-Button ist **NICHT sichtbar** (versteckt)
12. Versuche manuell: DELETE `/participant/{id}`
13. [ ] Überprüfe: Erhältst 403 Forbidden oder Redirect
14. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 5: Beobachter - Admin-Panel Zugriff VERWEIGERT
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Versuche zu navigieren: `/admin/users`
3. [ ] Überprüfe: Seite wird NICHT geladen (403 oder Redirect zu Login/Home)
4. Versuche zu navigieren: `/admin/roles`
5. [ ] Überprüfe: Seite wird NICHT geladen (403 oder Redirect)
6. [ ] Überprüfe: Keine Admin-Links sind in der Navigation sichtbar
7. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 6: Admin - KI-Analyse Zugriff
**Rolle**: Admin  
**Schritte**:
1. Login als admin@test.de
2. Navigiere zu `/analysis`
3. [ ] Überprüfe: Seite lädt ohne Fehler
4. [ ] Überprüfe: "KI-Analyse durchführen" Button ist **sichtbar**
5. [ ] Überprüfe: "Fremdeinschätzung verwalten" Link ist **sichtbar**
6. [ ] Überprüfe: "Schlussberichte verwalten" Link ist **sichtbar**
7. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 7: Beobachter - KI-Analyse Zugriff VERWEIGERT
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Versuche zu navigieren: `/analysis`
3. [ ] Überprüfe: Seite wird NICHT geladen (403 oder Redirect)
4. [ ] Überprüfe: KI-Analyse Links sind in Teilnehmer-Seite versteckt
5. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 8: Template Visibility Gates in manage_groups.html
**Rolle**: Admin  
**Schritte**:
1. Login als admin@test.de
2. Öffne DevTools (F12 → Elements/Inspector)
3. Navigiere zu `/groups`
4. Suche nach HTML-Element mit `onclick="openAddGroupModal()"` oder ähnlich
5. [ ] Überprüfe: Element ist **nicht gekapselt** in `<!-- hidden by permission -->` Kommentar (oder ist sichtbar)
6. Suche nach Edit-Buttons neben Gruppen
7. [ ] Überprüfe: Buttons sind **nicht gekapselt** in bedingter Logik (oder sind sichtbar)
8. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 9: Template Visibility Gates in manage_groups.html (Beobachter)
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Öffne DevTools (F12 → Elements/Inspector)
3. Navigiere zu `/groups`
4. Suche nach "Neue Gruppe" Button oder `openAddGroupModal()`
5. [ ] Überprüfe: Element ist **NICHT im HTML vorhanden** (Jinja2 gate wirkt)
6. Suche nach Edit-Buttons
7. [ ] Überprüfe: Buttons sind **NICHT im HTML vorhanden**
8. Öffne Browser Console
9. Führe aus: `document.querySelector('button[onclick*="Group"]')`
10. [ ] Überprüfe: Ergebnis ist `null` (keine unautorisierten Buttons)
11. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 10: Template Visibility Gates in manage_participants.html
**Rolle**: Admin  
**Schritte**:
1. Login als admin@test.de
2. Öffne DevTools → Network Tab
3. Navigiere zu `/participants`
4. Scrolle zu existierendem Teilnehmer
5. [ ] Überprüfe: Alle Action-Buttons (Edit, Delete, Links) sind **sichtbar**
6. [ ] Überprüfe: Edit-Modal ist in HTML vorhanden (nicht hidden)
7. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 11: Template Visibility Gates in manage_participants.html (Beobachter)
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Öffne DevTools → Elements
3. Navigiere zu `/participants`
4. Scrolle zu existierendem Teilnehmer
5. Suche nach "Edit" Button HTML
6. [ ] Überprüfe: Button ist **NICHT im HTML vorhanden** (Jinja2 gate: participants.edit permission)
7. Suche nach "Delete" Button HTML
8. [ ] Überprüfe: Button ist **NICHT im HTML vorhanden**
9. Suche nach "Selbsteinschätzung" Link
10. [ ] Überprüfe: Link ist **im HTML vorhanden** (data_entry.view permission: authorized)
11. Suche nach "KI-Analyse" Link
12. [ ] Überprüfe: Link ist **NICHT im HTML vorhanden** (analysis.run: not authorized)
13. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

### Test 12: Direct HTTP Access - Permission Denial
**Rolle**: Beobachter  
**Schritte**:
1. Login als observer@test.de
2. Öffne Browser Console
3. Führe aus (via fetch):
```javascript
fetch('/group/add', {
  method: 'POST',
  body: new FormData(document.querySelector('form'))
})
.then(r => r.status)
.then(s => console.log('Status:', s))
```
4. [ ] Überprüfe: Response Status ist 403 oder 302 (nicht 200)
5. [ ] Überprüfe: Gruppe wurde **NICHT erstellt**
6. **Status**: [ ] Bestanden [ ] Fehlgeschlagen

---

## Test-Ergebnisse Zusammenfassung

### Admin-Rolle: `___/___` Subtests Bestanden
- [ ] Gruppen Management: OK
- [ ] Teilnehmer Management: OK
- [ ] Beobachtungsaufgaben: OK
- [ ] KI-Analyse: OK
- [ ] Admin-Panel: OK
- [ ] Template Gates (Admin): OK

### Beobachter-Rolle: `___/___` Subtests Bestanden
- [ ] Gruppen versteckt: OK
- [ ] Teilnehmer beschränkt: OK
- [ ] Admin-Panel verweigert: OK
- [ ] KI-Analyse verweigert: OK
- [ ] Template Gates (Beobachter): OK
- [ ] Direct HTTP Denial: OK

### Gesamt-Status
- **Bestanden**: `___/12`
- **Fehlgeschlagen**: `___/12`
- **Kritische Probleme**: [ ] Keine [ ] Ja (siehe unten)

---

## Beobachtete Mängel (falls vorhanden)

| ID | Problem | Seite | Rolle | Severity | Aktion |
|---|---|---|---|---|---|
| DEFECT-001 | [Beschreibung] | / | Admin/Beobachter | High/Med/Low | [ ] Fix [ ] Ignore |
| DEFECT-002 | [Beschreibung] | / | Admin/Beobachter | High/Med/Low | [ ] Fix [ ] Ignore |

---

## Empfehlungen für nächste Schritte

1. **Automated Testing**: Führe `pytest tests/integration/test_rbac_permissions.py` aus
   ```bash
   pytest tests/integration/test_rbac_permissions.py -v --tb=short
   ```

2. **Coverage überprüfen**:
   ```bash
   pytest tests/integration/test_rbac_permissions.py --cov=blueprints --cov-report=html
   ```

3. **Spezifische Defekte testen**: Falls Fehler gefunden:
   - Dokumentiere im RBAC_DEFECTS.md
   - Erstelle pytest-Fall für jeden Defekt
   - Fix + Re-Test

4. **Rollout-Vorbereitung**:
   - [ ] Aktualisiere Permissions in Produktion
   - [ ] Trainiere Support-Team
   - [ ] Erstelle User-Dokumentation

---

## Notes

**Getestet am**: _______________  
**Von**: _______________  
**Browser**: _______________  
**Python Version**: 3.12.12  
**Environment**: Development [ ] Staging [ ] Production
