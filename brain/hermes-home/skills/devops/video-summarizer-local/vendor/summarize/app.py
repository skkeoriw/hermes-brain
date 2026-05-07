"""SUMMARIZE - Video Summarizer.

Streamlit entry point. All implementation lives in the ``webapp``
package; this file exists so ``streamlit run app.py`` keeps working.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Use explicit path to ensure it works in Docker containers
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

from webapp.ui import main

if __name__ == "__main__":
    main()
