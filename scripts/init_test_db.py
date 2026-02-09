#!/usr/bin/env python3
"""Initialize test database for CI/CD pipeline."""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set testing environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['SECRET_KEY'] = 'test-secret-key-ci'
os.environ['WTF_CSRF_ENABLED'] = 'False'

try:
    from app import app, db
    
    with app.app_context():
        db.create_all()
        print('✅ Database initialized successfully')
        sys.exit(0)
except Exception as e:
    print(f'❌ Error: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
