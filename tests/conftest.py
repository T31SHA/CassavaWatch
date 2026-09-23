import os
import sys
import tempfile
from pathlib import Path

# isolated DB for tests; must be set before app.models is imported
os.environ["CASSAVAWATCH_DB"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
