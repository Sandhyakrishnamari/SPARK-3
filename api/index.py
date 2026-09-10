import sys
import os

# Add parent directory to path so we can import app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Set environment variable for Vercel
os.environ.setdefault('VERCEL', '1')

from app import app

# Vercel Python runtime expects the WSGI app to be called 'app'
application = app

# For local development
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
