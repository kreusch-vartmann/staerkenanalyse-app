# Codex Task 9: Vollständiges RBAC-System (Role-Based Access Control)

## Ziel
Ein feingranulares Rechte-System, bei dem der Admin:
- Rollen frei erstellen/bearbeiten kann (außer der System-Admin-Rolle, die unveränderbar alle Rechte hat)
- Jeder Rolle einzelne Permissions (lesend/schreibend pro Funktionsbereich) zuweisen kann
- Die Beobachter-Rolle mit eingeschränkten Rechten kommt vorkonfiguriert
- User bekommen genau eine Rolle zugewiesen (bestehendes Single-FK-Pattern bleibt)

## Projekt-Stack
- Python 3.12, Flask 2.x, SQLAlchemy 2.x, Flask-Login, Flask-Migrate (Alembic)
- Jinja2-Templates mit Tailwind CSS (indigo-600 als Primärfarbe)
- Alle `<script>`-Tags: `nonce="{{ csp_nonce }}"`
- CSP-Nonce wird in `base.html` über `{{ csp_nonce }}` bereitgestellt
- Datenbank: SQLite (Entwicklung)
- Blueprints: admin, analysis, auth, data_import, data_io, explanation_blocks, groups, observation_tasks, participants, prompts, reports

## Bestehende Modelle (Kontext)

```python
# models.py (relevant excerpt)
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    users = db.relationship("User", back_populates="role")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")
    
    @property
    def is_admin(self) -> bool:
        return self.role.name.lower() == "admin"
```

## Bestehende Decorator-Logik in `decorators.py`

```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user or not current_user.is_admin:
            flash("Sie haben keine Berechtigung für diesen Bereich.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function
```

Weitere Decoratoren: `group_access_required`, `participant_access_required`, `filter_groups_by_access`, `filter_participants_by_group`

---

## Schritt 1: Neue Modelle in `models.py`

### 1a: `Permission`-Modell (nach `Role`-Klasse einfügen)

```python
# Permission ↔ Role Many-to-Many
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)


class Permission(db.Model):
    """Einzelne Berechtigung für RBAC."""
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    codename = db.Column(db.String(100), nullable=False, unique=True)  # z.B. "groups.view"
    description = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=True)  # z.B. "Gruppen", "Analyse"

    roles = db.relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.codename}>"
```

### 1b: Felder zu `Role` hinzufügen

```python
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_system = db.Column(db.Boolean, default=False)  # NEU: True = unveränderbar (Admin)

    users = db.relationship("User", back_populates="role")
    permissions = db.relationship("Permission", secondary=role_permissions, back_populates="roles")  # NEU

    def has_permission(self, codename):
        """Prüft ob die Rolle eine bestimmte Berechtigung hat."""
        if self.is_system:  # System-Rollen (Admin) haben immer alle Rechte
            return True
        return any(p.codename == codename for p in self.permissions)

    def __repr__(self):
        return f"<Role {self.name}>"
```

### 1c: Helper auf `User` hinzufügen

```python
# In class User, als Property/Methode hinzufügen:
def has_permission(self, codename):
    """Prüft ob der User die angegebene Berechtigung hat."""
    return self.role.has_permission(codename)
```

## Schritt 2: Vordefinierte Permissions

Erstelle eine Datei `seed_permissions.py` im Projekt-Root:

```python
#!/usr/bin/env python
"""Seed default permissions and assign them to roles."""
from app import app, db
import models

DEFAULT_PERMISSIONS = [
    # Gruppen
    ("groups.view", "Gruppen anzeigen", "Gruppen"),
    ("groups.edit", "Gruppen erstellen/bearbeiten", "Gruppen"),
    ("groups.delete", "Gruppen löschen", "Gruppen"),
    # Teilnehmer
    ("participants.view", "Teilnehmer anzeigen", "Teilnehmer"),
    ("participants.edit", "Teilnehmer bearbeiten/hinzufügen", "Teilnehmer"),
    ("participants.delete", "Teilnehmer löschen", "Teilnehmer"),
    # Beobachtungsdaten
    ("data_entry.view", "Beobachtungsdaten ansehen", "Daten"),
    ("data_entry.edit", "Beobachtungsdaten eingeben/bearbeiten", "Daten"),
    # KI-Analyse
    ("analysis.run", "KI-Analyse ausführen", "Analyse"),
    ("analysis.view_reports", "Berichte ansehen", "Analyse"),
    ("analysis.edit_reports", "Berichte bearbeiten", "Analyse"),
    # Beobachtungsaufgaben
    ("observation_tasks.view", "Beobachtungsaufgaben ansehen", "Aufgaben"),
    ("observation_tasks.manage", "Beobachtungsaufgaben verwalten", "Aufgaben"),
    # Prompts
    ("prompts.view", "Prompts ansehen", "Verwaltung"),
    ("prompts.manage", "Prompts verwalten", "Verwaltung"),
    # Textbausteine
    ("explanation_blocks.view", "Textbausteine ansehen", "Verwaltung"),
    ("explanation_blocks.manage", "Textbausteine verwalten", "Verwaltung"),
    # Import/Export
    ("import.run", "Daten importieren", "Datenübertragung"),
    ("export.run", "Daten exportieren", "Datenübertragung"),
    # User-Verwaltung
    ("users.manage", "Benutzer verwalten", "Administration"),
    ("roles.manage", "Rollen verwalten", "Administration"),
]

# Rollen-Vorlagen: Rolle → Liste von Permission-Codenames
ROLE_TEMPLATES = {
    "admin": None,  # None = is_system=True, hat automatisch alle Rechte
    "beobachter": [
        "groups.view",
        "participants.view",
        "participants.edit",
        "data_entry.view",
        "data_entry.edit",
        "analysis.view_reports",
        "observation_tasks.view",
    ],
}

with app.app_context():
    # 1. Seed Permissions
    for codename, desc, category in DEFAULT_PERMISSIONS:
        existing = db.session.scalar(
            db.select(models.Permission).where(models.Permission.codename == codename)
        )
        if not existing:
            db.session.add(models.Permission(codename=codename, description=desc, category=category))
            print(f"  ✅ Permission '{codename}' erstellt")
    db.session.commit()

    # 2. Update Roles
    for role_name, perm_codes in ROLE_TEMPLATES.items():
        role = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == role_name.lower())
        )
        if not role:
            print(f"  ⚠️ Rolle '{role_name}' nicht gefunden, wird übersprungen")
            continue

        if perm_codes is None:
            # System-Rolle (Admin)
            role.is_system = True
            print(f"  ✅ Rolle '{role_name}' als System-Rolle markiert")
        else:
            # Permissions zuweisen
            role.permissions = []
            for code in perm_codes:
                perm = db.session.scalar(
                    db.select(models.Permission).where(models.Permission.codename == code)
                )
                if perm:
                    role.permissions.append(perm)
            print(f"  ✅ Rolle '{role_name}' → {len(perm_codes)} Permissions zugewiesen")

    db.session.commit()
    print("✅ Alle Permissions und Rollen-Zuordnungen erstellt!")
```

## Schritt 3: Migration

```bash
flask db migrate -m "add_permissions_and_role_permissions"
flask db upgrade
python seed_permissions.py
```

## Schritt 4: Neuer Decorator `permission_required` in `decorators.py`

Füge **nach** dem bestehenden `admin_required` Decorator hinzu:

```python
def permission_required(codename):
    """
    Decorator: Erfordert eine bestimmte Berechtigung.
    Admin (is_system-Rolle) hat automatisch alle Berechtigungen.
    
    Verwendung: @login_required @permission_required("groups.edit")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(codename):
                flash("Sie haben keine Berechtigung für diese Aktion.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

**WICHTIG:** Den bestehenden `@admin_required` Decorator NICHT entfernen. Er bleibt als Shortcut. Schrittweise können einzelne Routes auf `@permission_required(...)` umgestellt werden, aber das ist optional und kann separat passieren.

## Schritt 5: Admin-UI für Rollenverwaltung

### 5a: Routes in `blueprints/admin.py`

Füge am Ende der Datei hinzu (vor dem letzten Zeilenumbruch):

```python
# === Rollenverwaltung ===

@admin_bp.route("/roles", methods=["GET"])
@login_required
@admin_required
def manage_roles():
    """Admin: Übersicht aller Rollen."""
    roles = db.session.scalars(db.select(models.Role).order_by(models.Role.name)).all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Rollenverwaltung"},
    ]
    return render_template("admin/manage_roles.html", roles=roles, breadcrumbs=breadcrumbs)


@admin_bp.route("/role/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_role():
    """Admin: Neue Rolle erstellen."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        perm_ids = request.form.getlist("permissions")

        if not name:
            flash("Rollenname ist erforderlich.", "error")
            return redirect(url_for("admin.add_role"))

        existing = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == name.lower())
        )
        if existing:
            flash(f"Rolle '{name}' existiert bereits.", "error")
            return redirect(url_for("admin.add_role"))

        new_role = models.Role(name=name, description=description, is_system=False)
        
        for pid in perm_ids:
            perm = db.session.get(models.Permission, int(pid))
            if perm:
                new_role.permissions.append(perm)

        db.session.add(new_role)
        db.session.commit()
        flash(f"Rolle '{name}' erfolgreich erstellt.", "success")
        return redirect(url_for("admin.manage_roles"))

    permissions = db.session.scalars(
        db.select(models.Permission).order_by(models.Permission.category, models.Permission.codename)
    ).all()
    
    # Gruppiere Permissions nach Kategorie
    perm_groups = {}
    for p in permissions:
        cat = p.category or "Sonstige"
        perm_groups.setdefault(cat, []).append(p)

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_roles"), "text": "Rollenverwaltung"},
        {"text": "Neue Rolle"},
    ]
    return render_template(
        "admin/role_form.html",
        role=None,
        perm_groups=perm_groups,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/role/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_role(role_id):
    """Admin: Rolle bearbeiten."""
    role = db.session.get(models.Role, role_id)
    if not role:
        flash("Rolle nicht gefunden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.is_system:
        flash("System-Rollen können nicht bearbeitet werden.", "warning")
        return redirect(url_for("admin.manage_roles"))

    if request.method == "POST":
        role.name = request.form.get("name", "").strip() or role.name
        role.description = request.form.get("description", "").strip()
        perm_ids = request.form.getlist("permissions")

        role.permissions = []
        for pid in perm_ids:
            perm = db.session.get(models.Permission, int(pid))
            if perm:
                role.permissions.append(perm)

        db.session.commit()
        flash(f"Rolle '{role.name}' aktualisiert.", "success")
        return redirect(url_for("admin.manage_roles"))

    permissions = db.session.scalars(
        db.select(models.Permission).order_by(models.Permission.category, models.Permission.codename)
    ).all()
    
    perm_groups = {}
    for p in permissions:
        cat = p.category or "Sonstige"
        perm_groups.setdefault(cat, []).append(p)

    role_perm_ids = {p.id for p in role.permissions}

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_roles"), "text": "Rollenverwaltung"},
        {"text": f"Rolle: {role.name}"},
    ]
    return render_template(
        "admin/role_form.html",
        role=role,
        perm_groups=perm_groups,
        role_perm_ids=role_perm_ids,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/role/<int:role_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_role(role_id):
    """Admin: Rolle löschen (nur wenn keine User zugewiesen)."""
    role = db.session.get(models.Role, role_id)
    if not role:
        flash("Rolle nicht gefunden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.is_system:
        flash("System-Rollen können nicht gelöscht werden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.users:
        flash(f"Rolle '{role.name}' hat noch {len(role.users)} zugewiesene Benutzer. Bitte erst die Benutzer einer anderen Rolle zuweisen.", "error")
        return redirect(url_for("admin.manage_roles"))

    db.session.delete(role)
    db.session.commit()
    flash(f"Rolle '{role.name}' gelöscht.", "success")
    return redirect(url_for("admin.manage_roles"))
```

### 5b: Template `templates/admin/manage_roles.html`

Erstelle die Datei:

```html
{% extends "base.html" %}

{% block title %}Rollenverwaltung - Stärkenanalyse{% endblock %}

{% block content %}
<div class="mx-auto max-w-6xl px-4 py-6">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
        <h2 class="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <i class="fas fa-shield-alt text-indigo-600"></i> Rollenverwaltung
        </h2>
        <a href="{{ url_for('admin.add_role') }}" class="inline-flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700">
            <i class="fas fa-plus"></i> Neue Rolle
        </a>
    </div>

    {% if roles %}
    <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
            <thead class="bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                    <th class="px-4 py-3 text-left">Name</th>
                    <th class="px-4 py-3 text-left">Beschreibung</th>
                    <th class="px-4 py-3 text-left">Berechtigungen</th>
                    <th class="px-4 py-3 text-left">Benutzer</th>
                    <th class="px-4 py-3 text-left">Typ</th>
                    <th class="px-4 py-3 text-left">Aktionen</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
                {% for role in roles %}
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3 font-semibold text-gray-900">{{ role.name | upper }}</td>
                    <td class="px-4 py-3 text-gray-700">{{ role.description or '—' }}</td>
                    <td class="px-4 py-3">
                        {% if role.is_system %}
                            <span class="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">Alle Rechte</span>
                        {% else %}
                            <span class="text-gray-600">{{ role.permissions | length }} Berechtigungen</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3 text-gray-700">{{ role.users | length }}</td>
                    <td class="px-4 py-3">
                        {% if role.is_system %}
                            <span class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">System</span>
                        {% else %}
                            <span class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">Benutzerdefiniert</span>
                        {% endif %}
                    </td>
                    <td class="px-4 py-3">
                        {% if not role.is_system %}
                        <div class="flex items-center gap-2">
                            <a href="{{ url_for('admin.edit_role', role_id=role.id) }}" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50">
                                <i class="fas fa-edit"></i>
                            </a>
                            <form method="POST" action="{{ url_for('admin.delete_role', role_id=role.id) }}" onsubmit="return confirm('Rolle wirklich löschen?')">
                                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                                <button type="submit" class="inline-flex items-center rounded-md border border-red-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </form>
                        </div>
                        {% else %}
                            <span class="text-xs text-gray-400">Geschützt</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="rounded-md border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">
        <i class="fas fa-info-circle mr-2"></i> Noch keine Rollen vorhanden.
    </div>
    {% endif %}
</div>
{% endblock %}
```

### 5c: Template `templates/admin/role_form.html`

```html
{% extends "base.html" %}

{% block title %}{{ "Rolle bearbeiten" if role else "Neue Rolle" }} - Stärkenanalyse{% endblock %}

{% block content %}
<div class="mx-auto max-w-4xl px-4 py-6">
    <h2 class="text-3xl font-bold text-gray-900 flex items-center gap-2 mb-6">
        <i class="fas fa-shield-alt text-indigo-600"></i>
        {{ "Rolle bearbeiten: " + role.name if role else "Neue Rolle erstellen" }}
    </h2>

    <form method="POST" class="space-y-6">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>

        <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div class="border-b border-gray-200 px-6 py-4">
                <h5 class="text-sm font-semibold text-gray-900">Grunddaten</h5>
            </div>
            <div class="px-6 py-5 space-y-4">
                <div>
                    <label for="name" class="block text-sm font-medium text-gray-700">Rollenname</label>
                    <input type="text" id="name" name="name" value="{{ role.name if role else '' }}" required
                           class="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500">
                </div>
                <div>
                    <label for="description" class="block text-sm font-medium text-gray-700">Beschreibung</label>
                    <input type="text" id="description" name="description" value="{{ role.description if role else '' }}"
                           class="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500">
                </div>
            </div>
        </div>

        <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div class="border-b border-gray-200 px-6 py-4">
                <h5 class="text-sm font-semibold text-gray-900">Berechtigungen</h5>
            </div>
            <div class="px-6 py-5">
                {% for category, perms in perm_groups.items() %}
                <div class="mb-6 last:mb-0">
                    <h6 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{{ category }}</h6>
                    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {% for perm in perms %}
                        <label class="flex items-start gap-3 rounded-md border border-gray-200 p-3 hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" name="permissions" value="{{ perm.id }}"
                                   class="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                   {% if role_perm_ids is defined and perm.id in role_perm_ids %}checked{% endif %}>
                            <div>
                                <span class="block text-sm font-medium text-gray-900">{{ perm.description }}</span>
                                <span class="block text-xs text-gray-500 font-mono">{{ perm.codename }}</span>
                            </div>
                        </label>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="flex gap-3">
            <button type="submit" class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
                <i class="fas fa-save"></i> {{ "Aktualisieren" if role else "Erstellen" }}
            </button>
            <a href="{{ url_for('admin.manage_roles') }}" class="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
                Abbrechen
            </a>
        </div>
    </form>
</div>
{% endblock %}
```

## Schritt 6: Navigation zur Rollenverwaltung

### 6a: In `templates/base.html` Sidebar
Im `{% if current_user.is_admin %}` Block in der Sidebar (Verwaltung-Bereich), nach dem Export-Link, füge hinzu:

```html
<a class="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium {% if request.endpoint and 'role' in request.endpoint %}bg-indigo-50 text-indigo-700{% else %}text-gray-700 hover:bg-gray-50{% endif %}" href="{{ url_for('admin.manage_roles') }}">
    <span>🛡️</span> Rollen
</a>
```

### 6b: In `templates/base.html` User-Dropdown
Im `{% if current_user.is_admin %}` Block im User-Dropdown-Menü (nach "Benutzerverwaltung"):

```html
<a class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50" href="{{ url_for('admin.manage_roles') }}">
    <i class="fas fa-shield-alt"></i> Rollenverwaltung
</a>
```

### 6c: Dashboard-Kachel (optional)
Im Dashboard unter "Verwaltung" eine neue Kachel:

```html
{% if current_user.is_admin %}
<a href="{{ url_for('admin.manage_roles') }}" class="block rounded-lg border border-gray-200 bg-white p-6 shadow-sm hover:bg-gray-50 transition-colors">
    <h5 class="mb-2 text-2xl font-bold tracking-tight text-gray-900">🛡️ Rollen</h5>
    <p class="font-normal text-gray-700">Benutzerrollen und Berechtigungen verwalten.</p>
</a>
{% endif %}
```

## Schritt 7: Bestehende `@admin_required`-Routes schrittweise umstellen (optional)

Das ist optional und kann schrittweise passieren. Beispiel:

```python
# Vorher:
@groups_bp.route("/groups")
@login_required
def manage_groups():

# Nachher (Route sichtbar für alle mit groups.view):
@groups_bp.route("/groups")
@login_required
@permission_required("groups.view")
def manage_groups():
```

**WICHTIG:** Für diese erste Iteration NICHT alle Routes umstellen. Nur den neuen `permission_required` Decorator bereitstellen. Die schrittweise Umstellung kann separat erfolgen, da `admin_required` weiterhin funktioniert und Admin-User über `is_system` auch bei `permission_required` immer Zugriff haben.

## Validierung
1. `flask db migrate -m "add_permissions_and_role_permissions"` → Migration erstellt
2. `flask db upgrade` → Tabellen erstellt
3. `python seed_permissions.py` → Permissions und Rollen-Zuordnungen erstellt
4. Server starten: `flask run --port 5002` → Keine Fehler
5. `/admin/roles` → Zeigt Admin (System) und Beobachter mit jeweiligen Permissions
6. Neue Rolle erstellen → Funktioniert mit Permission-Checkboxen
7. System-Rolle "Admin" → Bearbeiten/Löschen nicht möglich
8. `/admin/user/add` → Dropdown zeigt jetzt admin + beobachter + neue Rollen
9. Beobachter-User anlegen → Beobachter sieht nur zugewiesene Gruppen (wie bisher)

## Wichtige Hinweise
- **Admin-Rolle** muss `is_system=True` sein → hat automatisch ALLE Rechte, unveränderbar
- **Bestehende `is_admin` Property** auf User bleibt erhalten → funktioniert wie bisher
- **Bestehende `admin_required` Decorator** bleibt unverändert → Abwärtskompatibilität
- Alle Templates nutzen Tailwind CSS mit indigo-600 als Primärfarbe
- Alle `<script>`-Tags brauchen `nonce="{{ csp_nonce }}"`
- Alle Formulare brauchen `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>`
