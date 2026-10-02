import os

# must be set before the app is imported (config refuses to start without a real secret)
os.environ.setdefault("SECRET_KEY", "test-only-secret-test-only-secret-1234")
