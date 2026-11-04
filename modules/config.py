import os
import datetime
from dotenv import load_dotenv

# ==========================================
# ⚙️ Environment Variables & Streamlit Secrets Support
# ==========================================
# 스크립트가 어디서 실행되든 무조건 프로젝트 루트의 .env를 찾아 로드합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

def _get_setting(key: str, default: str = "") -> str:
    val = os.getenv(key, "").strip()
    if val:
        return val
    try:
        secrets_paths = [
            os.path.join(BASE_DIR, ".streamlit", "secrets.toml"),
            os.path.expanduser("~/.streamlit/secrets.toml"),
        ]
        if any(os.path.isfile(p) for p in secrets_paths):
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key]).strip()
    except Exception:
        pass
    return default

OPENALEX_EMAIL = _get_setting("OPENALEX_EMAIL", "")
OPENALEX_API_KEY = _get_setting("OPENALEX_API_KEY", "")
APP_PASSWORD = _get_setting("APP_PASSWORD", "")

# Cloudflare WAF 설정 변수 (setup_waf.py 등 필요할 때 불러서 사용)
CF_ZONE_ID = _get_setting("CF_ZONE_ID", "").strip('"').strip("'")
CF_API_TOKEN = _get_setting("CF_API_TOKEN", "").strip('"').strip("'")
CF_DOMAIN = _get_setting("CF_DOMAIN", "").strip('"').strip("'")


def get_current_year():
    return datetime.datetime.now().year

# ==========================================
# 🌍 OmniScholar Global Academic Presets
# ==========================================
GLOBAL_PRESETS = {
    "👑 Multidisciplinary": {"Nature": "0028-0836", "Science": "0036-8075", "PNAS": "0027-8424"},
    "🩺 Medicine & Clinical": {"NEJM": "0028-4793", "The Lancet": "0140-6736", "JAMA": "0098-7484"},
    "💻 Computer Sci & AI": {"IEEE TPAMI": "0162-8828", "Nature Mach Intell": "2522-5839", "IEEE Access": "2169-3536"},
    "⚛️ Physics & Math": {"Phys Rev Letters": "0031-9007", "Nature Physics": "1745-2473", "Annals of Math": "0003-486X"},
    "🧬 Biology & Chemistry": {"Cell": "0092-8674", "JACS": "0002-7863", "Nature Genetics": "1061-4036"},
    "⚙️ Engineering & Materials": {"Advanced Materials": "0935-9648", "Nature Materials": "1476-1122", "Chemical Eng Journal": "1385-8947"},
    "📈 Economics & Finance": {"Quarterly J of Econ": "0033-5533", "Amer Economic Rev": "0002-8282", "Journal of Finance": "0022-1082"},
    "🧠 Psychology & Soc Sci": {"Psychological Bulletin": "0033-2909", "Amer Sociological Rev": "0003-1224", "Child Development": "0009-3920"},
    "🏛️ Humanities & Arts": {"The Historical Journal": "0018-246X", "Ethics": "0014-1704", "Mind (Philosophy)": "0026-4423"}
}
