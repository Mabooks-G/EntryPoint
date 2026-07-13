# api/index.py
import sys
from pathlib import Path

# Add the project root to sys.path so we can import the 'backend' module
root = Path(__file__).parent.parent
sys.path.append(str(root))

from backend.app import app  # FastAPI app instance

# Vercel will use this 'app' variable