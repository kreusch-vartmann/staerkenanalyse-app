# CSP Browser Testing Guide

## Sprint 1.1: Security Headers Verification

**Server läuft auf:** http://localhost:5001

---

## Testing Checkliste

### 1. Chrome DevTools - Security Tab

1. **Browser öffnen:** Chrome/Firefox
2. **URL:** http://localhost:5001
3. **DevTools öffnen:** F12 oder Rechtsklick → "Untersuchen"
4. **Security Tab öffnen**

**Expected Headers:**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

---

### 2. Console Tab - CSP Violations

**Expected:** Keine CSP-Fehler

**Akzeptable Warnings:**
- Tailwind CDN (wenn in dev-mode)
- FontAwesome CDN

**Kritische Fehler (müssen gefixt werden):**
- `Refused to execute inline script because it violates CSP...`
- `Refused to load the stylesheet because it violates CSP...`

---

### 3. Funktionale Tests

**Kritische Workflows testen:**

1. **Login** (http://localhost:5001/auth/login)
   - Funktioniert Login-Form?
   - JavaScript executed?

2. **Dashboard** (http://localhost:5001/)
   - Laden alle Scripts?
   - Dropdown-Menüs funktional?

3. **Dateneingabe** (http://localhost:5001/data_entry_rework)
   - Formular funktioniert?
   - AJAX-Requests?

4. **Task-Generator** (http://localhost:5001/observation_tasks/generate)
   - Modal öffnet?
   - KI-Aufgabe generieren funktioniert?

---

## Chrome DevTools Schritte

### Schritt 1: Header Inspection

```
1. Seite öffnen: http://localhost:5001
2. F12 → Network Tab
3. Reload (Strg+R)
4. Click first entry (localhost document)
5. Headers Tab → Response Headers
```

**Sollte zeigen:**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-[random]' https://cdn.jsdelivr.net; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

---

### Schritt 2: Inline-Script Prüfung

```
1. DevTools → Elements Tab
2. Prüfe, ob inline <script> ohne nonce laufen
3. Console: Keine CSP-Fehler zu inline scripts
```

---

## Automated Check (Optional)

```bash
# CSP Header Check
curl -I http://localhost:5001 | grep -i "content-security"

# Expected Output:
# Content-Security-Policy: default-src 'self'; script-src...
```

---

## Bugfixes (wenn CSP-Violations auftreten)

### Problem: "Refused to execute inline script"
**Lösung:** Script hat kein nonce → Zum Template hinzufügen

### Problem: "Refused to load stylesheet"
**Lösung:** CDN nicht in `style-src` → In app.py CSP erweitern

### Problem: "Refused to connect"
**Lösung:** API-Endpoint nicht in `connect-src` → In app.py CSP erweitern

---

## Erfolgs-Kriterien

✅ Alle Headers im Response  
✅ Keine CSP Console-Errors  
✅ Login funktioniert  
✅ Dashboard lädt vollständig  
✅ Dateneingabe funktioniert  
✅ Task-Generator Modal öffnet  
✅ Inline-Scripts ohne CSP-Fehler  

---

## Nächste Schritte nach Testing

1. **Screenshots/Errors dokumentieren** (wenn Fehler)
2. **"Alles grün"** melden → Sprint 1.1 abschließen
3. **Commit:** `feat: Add CSP + security headers (Sprint 1.1)`
4. **Update PHASE3_STATUS.md**
5. **Sprint 1.2 starten**
