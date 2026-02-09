# PHASE 1 SETUP & VERIFICATION GUIDE

## ⚡ Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app
source venv/bin/activate
pip install -q -r requirements.txt
```

### 2. Apply Database Migrations
```bash
flask db upgrade
# Output should show: "Running upgrade ... add_auth_models_001"
```

### 3. Create Initial Admin User
```bash
flask create-admin
# Follow prompts:
#   Admin E-Mail: admin@local.de
#   Vorname: Admin
#   Nachname: User
# → Generates secure 16-character password, displays it

# Output example:
# 🔑 Generiertes Passwort: K7$Xp2mR!wQ9nL4s
# ✅ Admin-Benutzer 'admin@local.de' erfolgreich erstellt.
```

### 4. Start Application
```bash
flask run
# Output: Running on http://127.0.0.1:5000
```

### 5. Test Login
1. Open `http://localhost:5000` in browser
2. Should redirect to `/login` (success!)
3. Login with:
   - E-Mail: `admin@local.de`
   - Passwort: `K7$Xp2mR!wQ9nL4s` (from step 3)
4. Prompted to change password
5. After password change → Dashboard visible with full sidebar

---

## ✅ Verification Checklist

### Authentication System
- [ ] Login page accessible at `/login`
- [ ] Login redirects authenticated users to dashboard
- [ ] Logout works and redirects to login
- [ ] Unauthenticated access redirects to `/login`
- [ ] Password change works with minimum 8 char validation
- [ ] Password reset button in admin panel works

### Authorization (Role-Based)
- [ ] Admin user has full sidebar with "Verwaltung" section
- [ ] Beobachter users have limited sidebar (no admin menus)
- [ ] Admin can access `/admin/users` page
- [ ] Beobachter cannot access admin panel (redirect with error)

### User Management
- [ ] Admin can create new users
- [ ] Newly created user must change password on first login
- [ ] Admin can reset user password
- [ ] Admin can toggle user active/inactive status
- [ ] Admin can assign groups to Beobachter
- [ ] Beobachter see only assigned groups in sidebar

### Database
- [ ] `roles` table created with 'admin' and 'beobachter' entries
- [ ] `users` table created with admin user
- [ ] `user_groups` table created
- [ ] Passwords are hashed (NOT plaintext) in DB:
  ```bash
  sqlite3 instance/database.db "SELECT email, password_hash FROM users;"
  # Should show hashed passwords like: pgb2:sha256$...
  ```

### Session Management
- [ ] Login session persists across page reloads
- [ ] Logout clears session
- [ ] Session timeout after 8 hours (can test by setting PERMANENT_SESSION_LIFETIME)

---

## 🔧 Common Setup Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'flask_login'"
**Fix:** Run `pip install -r requirements.txt`

### Issue: "No such table: roles"
**Fix:** Run `flask db upgrade`

### Issue: "User loader function not found"
**Fix:** Restart Flask (`flask run` again)

### Issue: "Circular import error in decorators.py"
**Fix:** Check imports in decorators.py and blueprints - should import from extensions, not app

### Issue: Password hashing doesn't work
**Fix:** Ensure `from werkzeug.security import generate_password_hash, check_password_hash` is in models.py

---

## ⚠️ Known Limitations (Phase 1)

1. **Only 5 of 52 routes fully protected** (groups.py done as example)
   - Remaining routes in other blueprints need similar @login_required + role decorators
   - See PHASE1_IMPLEMENTATION_STATUS.md for detailed list

2. **No email-based password reset**
   - Only admin can reset passwords
   - Could add in Phase 3 with SMTP configuration

3. **No rate limiting yet**
   - flask-limiter is installed but not globally configured
   - Login has 5/minute limit configured in auth.py but not applied
   - Should add globally in app.py: `limiter.init_app(app)`

4. **Tests not yet updated**
   - Existing tests will fail because routes now require login
   - Need to update conftest.py with auth fixtures and apply @login_required decorator knowledge

---

## 📝 Remaining Manual Work

### Complete Route Protection (for all 52 routes)

Pattern for each blueprint:

```python
# At top of blueprint file
from flask_login import login_required
from flask_login import current_user
from decorators import admin_required, group_access_required, filter_*_by_access

# For admin-only routes:
@some_route_bp.route("/admin/something")
@login_required
@admin_required
def admin_function():
    ...

# For group-based visibility (list views):
@some_route_bp.route("/items")
@login_required
def list_items():
    query = filter_items_by_access(current_user)  # or filter_groups_by_access
    items = db.session.scalars(query).all()
    ...

# For specific group access (detail/edit views):
@some_route_bp.route("/item/<int:item_id>/edit")
@login_required
@group_access_required  # Checks item_id belongs to user's groups
def edit_item(item_id):
    ...
```

**Files to update (in order of priority):**
1. ✅ `blueprints/groups.py` - DONE
2. `blueprints/participants.py` - 8 routes
3. `blueprints/analysis.py` - 14 routes (most complex)
4. `blueprints/prompts.py` - 5 routes (all admin)
5. `blueprints/explanation_blocks.py` - 4 routes (all admin)
6. `blueprints/data_io.py` - 10 routes
7. `blueprints/reports.py` - 14 routes

---

## 🧪 Testing Phase 1

### Manual Test Flows

**Flow 1: Admin Login & User Management**
```
1. Login as admin
2. Navigate to admin panel
3. Create new Beobachter account
4. Assign some groups
5. Note generated password
6. Logout as admin
7. Login as Beobachter
8. Verify: Can only see assigned groups
9. Verify: Cannot access admin panel
```

**Flow 2: Password Management**
```
1. Login as new user (forced password change)
2. Change password to something new
3. Logout
4. Login with new password (should work)
5. As admin: Reset user's password
6. Login as user with new admin-generated password
7. Verify forced change again
```

**Flow 3: Security Checks**
```
1. Try to access /admin/users without login → should redirect to /login
2. Login as Beobachter
3. Try to manually visit /admin/users → should show error + redirect to dashboard
4. Try to access group data not assigned to you:
   DELETE request to /participant/{other_group_participant_id}/delete
   → should return 403 or redirect with error
```

### Automated Tests (To Be Written)

```python
# tests/unit/test_auth.py
def test_user_model_password_hashing():
    user = models.User(email="test@test.de")
    user.set_password("TestPassword123")
    assert user.check_password("TestPassword123")
    assert not user.check_password("WrongPassword")

# tests/integration/test_auth_blueprint.py
def test_login_with_valid_credentials(client, admin_user):
    response = client.post('/login', data={
        'email': 'admin@test.de',
        'password': 'test_password'
    })
    assert response.status_code == 302  # Redirect to dashboard

# tests/integration/test_permissions.py
def test_observer_cannot_access_admin_panel(observer_client):
    response = observer_client.get('/admin/users')
    assert response.status_code == 302  # Or 403
    assert 'Berechtigung' in response.data or response.status_code == 302
```

---

## 📊 Phase 1 Completion Status

- ✅ **Auth System**: 95% complete (routes not fully protected yet)
- ✅ **Models**: 100% complete
- ✅ **Login/Logout**: 100% complete
- ✅ **Admin Panel**: 100% complete
- ✅ **Decorators**: 100% complete
- ✅ **Config**: 100% complete
- 🟡 **Route Protection**: 10% complete (5/52 routes)
- 🟡 **Tests**: 0% complete
- 🟡 **Docker Integration**: 75% complete (needs startup sequence testing)

---

## 🚀 Next Phase After Phase 1

Once all 52 routes are protected and tests pass, Phase 2 begins:
- Aufgabengenerator implementation
- Task management models
- KI integration for task generation
- Chat interface for refinement

---

**Document generated**: 2026-02-09
**Estimated time to full completion**: 2-3 hours (if following this guide exactly)

