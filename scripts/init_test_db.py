#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['SECRET_KEY'] = 'test-secret-key-ci'
try:
    from app import app
    from extensions import db
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
    print('✅ Test database initialized successfully!')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
