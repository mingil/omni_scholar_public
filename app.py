import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import os
import re
import hashlib
import uuid

st.set_page_config(
    page_title="OmniScholar | 학술 논문 인용·피인용 네트워크 분석 플랫폼",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Modules ---
from modules.config import *
from modules.logger_setup import logger
from modules.export_utils import create_excel, generate_ris, format_citations_for_paper, build_export_filename
from modules.data_fetcher import fetch_journal_info, parse_journal_data, run_data_pipeline, search_journal_db
from modules.query_optimizer import (
    optimize_search_query,
    detect_and_correct_typos,
    get_autocomplete_suggestions,
    suggest_closest_table_terms,
    ACADEMIC_AUTOCOMPLETE_CATALOG,
    JOURNAL_SEARCH_SUGGESTIONS,
)
from modules.ui_components import (
    apply_custom_css,
    render_workflow_stepper,
    render_step_banner,
    render_journal_html,
    render_interactive_citations,
    render_auto_scroll_and_keepalive,
    render_academic_glossary_panel,
)

apply_custom_css()

# ==========================================
# 🔐 Persistent Auth & Session Snapshot Store
#    (Prevents idle WebSocket timeouts from redirecting to Login)
# ==========================================
def get_expected_auth_token() -> str:
    if not APP_PASSWORD:
        return "public"
    raw_str = f"omnischolar_persist_{APP_PASSWORD}_v2"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:24]

@st.cache_resource
def get_persistent_session_store() -> dict:
    return {}

PERSISTED_KEYS = [
    "ui_lang",
    "show_guide",
    "show_glossary",
    "cart",
    "scope_mode",
    "last_nl_input",
    "last_typo_pairs",
    "step1_confirmed",
    "step2_confirmed",
    "step3_confirmed",
    "executed_config",
    "df",
    "skw_res",
    "kw_input",
    "start_yr_input",
    "end_yr_input",
    "step3_active_tab",
    "last_export_ts",
]

def _get_query_param(key: str) -> str:
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get(key, "")
            if isinstance(val, list):
                return str(val[0]) if val else ""
            return str(val or "")
    except Exception:
        pass
    return ""

def _set_query_params(auth_val: str, sid_val: str):
    try:
        if hasattr(st, "query_params"):
            cur_auth = _get_query_param("auth")
            cur_sid = _get_query_param("sid")
            updates = {}
            if auth_val and cur_auth != auth_val:
                updates["auth"] = auth_val
            if sid_val and cur_sid != sid_val:
                updates["sid"] = sid_val
            if updates:
                st.query_params.update(updates)
    except Exception:
        pass

def _clear_query_params():
    try:
        if hasattr(st, "query_params"):
            if _get_query_param("auth") or _get_query_param("sid"):
                st.query_params.clear()
    except Exception:
        pass

def restore_session_if_reconnected():
    expected_token = get_expected_auth_token()
    qp_auth = _get_query_param("auth")
    qp_sid = _get_query_param("sid")

    if APP_PASSWORD and qp_auth == expected_token and not st.session_state.get("_explicit_logout"):
        st.session_state.authenticated = True

    if qp_sid:
        st.session_state.session_sid = qp_sid
        store = get_persistent_session_store()
        if qp_sid in store and not st.session_state.get("_snapshot_restored"):
            snap = store[qp_sid]
            for k, v in snap.items():
                if k not in st.session_state or st.session_state[k] is None or k in ("authenticated", "step1_confirmed", "step2_confirmed", "step3_confirmed", "cart", "scope_mode", "step3_active_tab"):
                    st.session_state[k] = v
            st.session_state._snapshot_restored = True

def save_session_snapshot():
    if APP_PASSWORD and not st.session_state.get("authenticated"):
        return
    sid = st.session_state.get("session_sid")
    if not sid:
        sid = uuid.uuid4().hex[:12]
        st.session_state.session_sid = sid
    store = get_persistent_session_store()
    if len(store) > 120 and sid not in store:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)
    snap = {"authenticated": True}
    for k in PERSISTED_KEYS:
        if k in st.session_state:
            snap[k] = st.session_state[k]
    store[sid] = snap
    _set_query_params(get_expected_auth_token(), sid)


# ==========================================
# 🌐 Session State Initialization
# ==========================================
current_year_default = get_current_year()
restore_session_if_reconnected()

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "KO_EN"
if "show_guide" not in st.session_state:
    st.session_state.show_guide = False
if "show_glossary" not in st.session_state:
    st.session_state.show_glossary = False
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "session_sid" not in st.session_state:
    st.session_state.session_sid = _get_query_param("sid") or uuid.uuid4().hex[:12]
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "scope_mode" not in st.session_state:
    st.session_state.scope_mode = "GLOBAL"
if "step3_active_tab" not in st.session_state:
    st.session_state.step3_active_tab = "PRESET"
if "last_nl_input" not in st.session_state:
    st.session_state.last_nl_input = ""
if "last_typo_pairs" not in st.session_state:
    st.session_state.last_typo_pairs = []
if "last_search_typo_note" not in st.session_state:
    st.session_state.last_search_typo_note = ""
if "step1_confirmed" not in st.session_state:
    st.session_state.step1_confirmed = False
if "step2_confirmed" not in st.session_state:
    st.session_state.step2_confirmed = False
if "step3_confirmed" not in st.session_state:
    st.session_state.step3_confirmed = False
if "executed_config" not in st.session_state:
    st.session_state.executed_config = None
if "trigger_rerun_pipeline" not in st.session_state:
    st.session_state.trigger_rerun_pipeline = False
if "scroll_target_anchor" not in st.session_state:
    st.session_state.scroll_target_anchor = ""
if "scroll_seq" not in st.session_state:
    st.session_state.scroll_seq = 0
if "step_order_alert" not in st.session_state:
    st.session_state.step_order_alert = None
if "last_export_ts" not in st.session_state:
    st.session_state.last_export_ts = None

for state in ["df", "toast_msg", "skw_res"]:
    if state not in st.session_state:
        st.session_state[state] = None

def tr(ko_en_text, en_text):
    return en_text if st.session_state.ui_lang == "EN" else ko_en_text

def trigger_scroll_to(anchor_id: str, alert_msg: str = "", target_step_num: int = 0):
    st.session_state.scroll_target_anchor = anchor_id
    st.session_state.scroll_seq = int(st.session_state.get("scroll_seq", 0)) + 1
    if alert_msg:
        st.session_state.step_order_alert = {"step": target_step_num, "msg": alert_msg}
    else:
        st.session_state.step_order_alert = None

def toggle_language():
    st.session_state.ui_lang = "EN" if st.session_state.ui_lang == "KO_EN" else "KO_EN"
    st.session_state.toast_msg = {
        "msg": "🌐 Switched to English Only Mode." if st.session_state.ui_lang == "EN" else "🌐 한국어 + 영문 병기 모드로 전환되었습니다.",
        "icon": "🌐"
    }

def toggle_guide():
    st.session_state.show_guide = not st.session_state.show_guide
    st.session_state.toast_msg = {
        "msg": tr("📖 사용 가이드 화면을 열었습니다." if st.session_state.show_guide else "📖 사용 가이드 화면을 닫았습니다.",
                  "📖 User Guide opened." if st.session_state.show_guide else "📖 User Guide closed."),
        "icon": "📖"
    }

def toggle_glossary():
    st.session_state.show_glossary = not st.session_state.show_glossary
    st.session_state.toast_msg = {
        "msg": tr("📘 학술·서지 용어 쉬운 해설집을 열었습니다." if st.session_state.show_glossary else "📘 학술·서지 용어 쉬운 해설집을 닫았습니다.",
                  "📘 Academic Terminology Guide opened." if st.session_state.show_glossary else "📘 Academic Terminology Guide closed."),
        "icon": "📘"
    }

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg["msg"], icon=st.session_state.toast_msg.get("icon", "✅"))
    st.session_state.toast_msg = None


# ==========================================
# 🔒 Enterprise Portal Login Screen
# ==========================================
if APP_PASSWORD and not st.session_state.authenticated:
    st.markdown(f"""
    <div class="top-navbar">
        <div class="brand-logo-wrap">
            <div class="brand-icon">OS</div>
            <div>
                <div class="brand-title">OmniScholar <span style="font-weight:600; font-size:1.02rem; color:#475569;">| {tr('학술 논문 인용·피인용 네트워크 분석 플랫폼', 'Academic Citation & Literature Intelligence')}</span></div>
                <div class="brand-subtitle">{tr('전 세계 2억 5천만 편 논문 실시간 탐색 · 뿌리(Root) 논문 역추적 · 연구자 맞춤형 리포트', 'Real-time 250M+ Works Analysis · Foundational Root Tracing · Researcher Analytics Suite')}</div>
            </div>
        </div>
        <div>
            <span class="status-pill"><span class="status-dot"></span> {tr('OpenAlex 학술 엔진 정상 연결됨', 'OpenAlex Engine Online')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    lang_bar_l, lang_bar_r = st.columns([7.6, 2.4])
    with lang_bar_r:
        st.button(
            "🌐 English Only Mode" if st.session_state.ui_lang == "KO_EN" else "🌐 한국어 + English 모드",
            on_click=toggle_language,
            use_container_width=True
        )

    hero_left, login_right = st.columns([1.35, 1], gap="large")

    with hero_left:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding: 4px 4px;">
                <span style="background:#DBEAFE; color:#1E40AF; padding:5px 12px; border-radius:8px; font-weight:800; font-size:0.86rem;">✨ RESEARCH INTELLIGENCE SUITE</span>
                <h2 style="margin:12px 0 8px 0; font-size:1.5rem; color:#0F172A; line-height:1.38;">
                    {tr('연구자를 위한 차세대 학술 인용·피인용 탐색 워크스페이스', 'Next-Generation Literature & Citation Network Workspace')}
                </h2>
                <p style="color:#334155; font-size:0.98rem; margin:0 0 16px 0; line-height:1.65;">
                    {tr('복잡한 검색 수식을 몰라도 괜찮습니다.<br>평소 연구 질문을 말하듯 입력하거나 단어 조립 버튼을 클릭하면, 전 세계 2억 5천만 편 이상의 학술 데이터베이스에서 핵심 트렌드 논문과 역사적 뿌리(Root) 논문을 정확하게 발굴합니다.',
                        'No complex Boolean syntax required.<br>Enter your research topic naturally or use our interactive query builder to uncover high-velocity contemporary papers and foundational root literature.')}
                </p>
                <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-bottom:12px;">
                    <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:12px; padding:14px 16px;">
                        <div style="font-weight:800; color:#1E3A8A; font-size:0.97rem; margin-bottom:5px;">✨ 01. {tr('자연어 ➔ 학술 검색식 자동 변환', 'Smart Query Auto-Conversion')}</div>
                        <div style="font-size:0.91rem; color:#334155; line-height:1.52;">{tr('한글·영어 문장을 입력하면 즉시 최적의 영문 불리언(Boolean) 학술 검색식으로 자동 변환됩니다.', 'Automatically converts Korean or English questions into optimal Boolean search expressions.')}</div>
                    </div>
                    <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:12px; padding:14px 16px;">
                        <div style="font-weight:800; color:#1E3A8A; font-size:0.97rem; margin-bottom:5px;">🧭 02. {tr('트렌드 스캔 & 뿌리 논문 역추적', 'Dual Discovery Algorithms')}</div>
                        <div style="font-size:0.91rem; color:#334155; line-height:1.52;">{tr('연간 인용 속도(Velocity) 기반 최신 인기 논문 추출 및 참고문헌 역추적을 통한 원조(Root) 논문 발굴을 지원합니다.', 'Switch between contemporary Trend Scanning and Deep Reference Co-citation Root Tracing.')}</div>
                    </div>
                    <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:12px; padding:14px 16px;">
                        <div style="font-weight:800; color:#1E3A8A; font-size:0.97rem; margin-bottom:5px;">📑 03. {tr('8종 문헌 유형 & 연구자 지표', '8 Document Types & Impact Metrics')}</div>
                        <div style="font-size:0.91rem; color:#334155; line-height:1.52;">{tr('원저(Article), 종설(Review), 프리프린트, 학위논문 구분 및 분야 보정 영향력(FWCI), 소속 기관, 토픽 분석을 제공합니다.', 'Filter by 8 document types and inspect FWCI, Institutions, Topics, and Open Access PDF links.')}</div>
                    </div>
                    <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:12px; padding:14px 16px;">
                        <div style="font-weight:800; color:#1E3A8A; font-size:0.97rem; margin-bottom:5px;">📥 04. {tr('원클릭 엑셀 · RIS · 인용문 복사', 'Instant Excel, RIS & Citation Copy')}</div>
                        <div style="font-size:0.91rem; color:#334155; line-height:1.52;">{tr('전체 초록이 포함된 엑셀(.xlsx), Zotero/EndNote용 RIS(.ris), APA/AMA/BibTeX 인용문을 즉시 제공합니다.', 'Export styled Excel reports, RIS files, and copy-ready APA 7th, AMA, and BibTeX citations.')}</div>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px; background:#EFF6FF; border:1.5px solid #BFDBFE; border-radius:12px; padding:12px 14px; text-align:center;">
                    <div>
                        <div style="font-weight:900; font-size:1.18rem; color:#1D4ED8;">250M+</div>
                        <div style="font-size:0.84rem; font-weight:700; color:#334155;">{tr('전 세계 학술 문헌 DB', 'Global Scholarly Works')}</div>
                    </div>
                    <div>
                        <div style="font-weight:900; font-size:1.18rem; color:#1D4ED8;">300,000+</div>
                        <div style="font-size:0.84rem; font-weight:700; color:#334155;">{tr('수록 국제 학술지·저널', 'Indexed Academic Venues')}</div>
                    </div>
                    <div>
                        <div style="font-weight:900; font-size:1.18rem; color:#1D4ED8;">100% Free OA</div>
                        <div style="font-size:0.84rem; font-weight:700; color:#334155;">{tr('무료 전문 PDF 직결 링크', 'Direct Open Access Links')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with login_right:
        with st.container(border=True):
            st.markdown(f"""
            <div style="text-align:center; padding: 6px 8px 4px 8px;">
                <div style="width:50px; height:50px; border-radius:14px; background:linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); color:#FFF; display:inline-flex; align-items:center; justify-content:center; font-weight:800; font-size:1.35rem; box-shadow:0 4px 12px rgba(37,99,235,0.25); margin-bottom:8px;">🔑</div>
                <div style="font-size:0.84rem; font-weight:800; color:#2563EB; letter-spacing:0.05em; margin-bottom:4px;">AUTHORIZED RESEARCHER ACCESS</div>
                <h3 style="margin:0 0 6px 0; font-size:1.42rem; color:#0F172A;">{tr('워크스페이스 로그인', 'Workspace Sign In')}</h3>
                <p style="color:#334155; font-size:0.95rem; margin:0 0 12px 0; line-height:1.58;">
                    {tr('승인된 액세스 비밀번호를 입력하고 아래 반짝이는 접속 버튼을 클릭하세요.',
                        'Enter your access password and click the glowing launch button below.')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("portal_login_form", clear_on_submit=True, border=False):
                pwd_val = st.text_input(
                    "Access Password",
                    type="password",
                    placeholder=tr("🔑 액세스 비밀번호를 입력하세요...", "🔑 Enter Access Password..."),
                    label_visibility="collapsed"
                )
                submit_btn = st.form_submit_button(
                    tr("👉 워크스페이스 로그인 및 시작하기 (Launch Workspace)", "👉 Sign In & Launch Workspace"),
                    type="primary",
                    use_container_width=True
                )
                if submit_btn:
                    if pwd_val == APP_PASSWORD:
                        st.session_state.authenticated = True
                        st.session_state._explicit_logout = False
                        save_session_snapshot()
                        st.session_state.toast_msg = {
                            "msg": tr("🎉 로그인 성공! 1단계부터 반짝이는 안내 버튼을 따라 순서대로 진행해 보세요.", "🎉 Welcome! Follow the highlighted action buttons from Step 1 to Step 4."),
                            "icon": "🎉"
                        }
                        st.rerun()
                    else:
                        st.error(tr("🚨 비밀번호가 일치하지 않습니다. 다시 확인해 주세요.", "🚨 Invalid credentials. Please verify your access password."))

            st.markdown(f"""
            <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:12px; padding:13px 16px; margin-top:8px; font-size:0.92rem; color:#334155; line-height:1.65;">
                <b style="color:#0F172A; font-size:0.96rem;">📋 {tr('처음 접속하셨나요? 로그인 후 진행 순서', '4-Step Guided Workflow After Sign In')}:</b><br>
                <b>🎯 1단계:</b> {tr('연구 주제 입력 후 <b>[1단계 완료]</b> 버튼 클릭', 'Enter research topic & click <b>[Confirm Step 1]</b>')}<br>
                <b>🧭 2단계:</b> {tr('탐색 알고리즘·출판 연도 확인 후 <b>[2단계 완료]</b> 버튼 클릭', 'Review algorithm & years, then click <b>[Confirm Step 2]</b>')}<br>
                <b>🏛️ 3단계:</b> {tr('학술지 범위 확인 후 <b>[3단계 완료]</b> 버튼 클릭', 'Confirm journal scope & click <b>[Confirm Step 3]</b>')}<br>
                <b>🚀 4단계:</b> {tr('<b>[논문 데이터 수집 시작]</b> 클릭 후 엑셀·인용문 다운로드', 'Click <b>[Start Extraction]</b> & download Excel/RIS')}
            </div>
            """, unsafe_allow_html=True)
    st.stop()


# ==========================================
# 📅 Post-Login Safe Initialization for Year Inputs
# ==========================================
if "start_yr_input" not in st.session_state or "end_yr_input" not in st.session_state:
    st.session_state.start_yr_input = current_year_default - 10
    st.session_state.end_yr_input = current_year_default
elif st.session_state.start_yr_input == 1950 and st.session_state.end_yr_input == 1950:
    st.session_state.start_yr_input = current_year_default - 10
    st.session_state.end_yr_input = current_year_default


# ==========================================
# 🚀 Action Callbacks & Step Confirmation Handlers
# ==========================================
def cb_jump_to_step(step_num: int):
    anchor_map = {1: "step-01-anchor", 2: "step-02-anchor", 3: "step-03-anchor", 4: "step-04-anchor"}
    target_anchor = anchor_map.get(step_num, "step-01-anchor")
    msg_map_ko = {
        1: "🎯 1단계(연구 주제 입력 및 확정) 위치로 이동했습니다! 주제를 입력하고 [1단계 완료] 버튼을 눌러주세요.",
        2: "🧭 2단계(탐색 알고리즘 · 필터 설정) 위치로 이동했습니다! 옵션을 확인하고 [2단계 완료] 버튼을 눌러주세요.",
        3: "🏛️ 3단계(검색 대상 학술지 범위) 위치로 이동했습니다! 학술지 범위를 확인하고 [3단계 완료] 버튼을 눌러주세요.",
        4: "🚀 4단계(최종 점검 및 수집 실행) 위치로 이동했습니다!"
    }
    msg_map_en = {
        1: "🎯 Moved to Step 1! Enter your topic and click [Confirm Step 1].",
        2: "🧭 Moved to Step 2! Review your options and click [Confirm Step 2].",
        3: "🏛️ Moved to Step 3! Confirm your journal scope and click [Confirm Step 3].",
        4: "🚀 Moved to Step 4!"
    }
    msg = tr(msg_map_ko.get(step_num, ""), msg_map_en.get(step_num, ""))
    st.session_state.toast_msg = {"msg": msg, "icon": "⬆️"}
    trigger_scroll_to(target_anchor, alert_msg=msg, target_step_num=step_num)

def notify_step2_change(label_ko, label_en):
    st.session_state.step2_confirmed = False
    msg = tr(f"🔄 [{label_ko}] 설정이 변경되었습니다! 2단계 하단의 [2단계 완료] 버튼을 눌러 확정해 주세요.", f"🔄 Updated [{label_en}]. Please click [Confirm Step 2] below.")
    st.session_state.toast_msg = {"msg": msg, "icon": "🔄"}

def notify_step3_change():
    st.session_state.step3_confirmed = False
    msg = tr("🔄 [검색 대상 학술지 범위]가 변경되었습니다! 3단계 하단의 [3단계 완료] 버튼을 눌러 확정해 주세요.", "🔄 Updated [Target Journal Scope]. Please click [Confirm Step 3] below.")
    st.session_state.toast_msg = {"msg": msg, "icon": "🔄"}

def cb_on_kw_input_change():
    raw = st.session_state.get("kw_input", "").strip()
    if not raw:
        st.session_state.last_nl_input = ""
        st.session_state.last_typo_pairs = []
        st.session_state.step1_confirmed = False
        return
    opt = optimize_search_query(raw)
    st.session_state.last_typo_pairs = opt.get("typo_pairs", [])
    if opt["was_modified"] and opt["optimized"]:
        st.session_state.last_nl_input = raw
        st.session_state.kw_input = opt["optimized"]
        st.session_state.step1_confirmed = False
        if opt.get("typo_corrected") and opt.get("typo_pairs"):
            pair_str = ", ".join([f"'{w}'➔'{r}'" for w, r in opt["typo_pairs"]])
            st.session_state.toast_msg = {
                "msg": tr(f"🪄 오타 자동 교정({pair_str}) 및 학술 검색식 변환 완료! 아래 파란색 [1단계 완료] 버튼을 눌러 확정해 주세요.", f"🪄 Auto-corrected typo ({pair_str}) & converted to formula! Click [Confirm Step 1] below."),
                "icon": "🪄"
            }
        else:
            st.session_state.toast_msg = {
                "msg": tr("✨ 자연어가 학술 검색식으로 변환되었습니다! 바로 아래 파란색 [1단계 완료] 버튼을 눌러 확정해 주세요.", "✨ Converted to academic formula! Click the blue [Confirm Step 1] button below."),
                "icon": "✨"
            }
    else:
        st.session_state.step1_confirmed = False
        st.session_state.toast_msg = {
            "msg": tr("✍️ 검색어가 입력되었습니다! 바로 아래 파란색 [1단계 완료] 버튼을 눌러 1단계를 확정해 주세요.", "✍️ Query entered! Click the blue [Confirm Step 1] button below."),
            "icon": "✍️"
        }

def cb_auto_convert_and_confirm_step1():
    raw = st.session_state.get("kw_input", "").strip()
    if not raw and not st.session_state.get("cart"):
        st.session_state.last_nl_input = ""
        st.session_state.last_typo_pairs = []
        st.session_state.step1_confirmed = False
        err_msg = tr("🚨 1단계 검색창이 비어 있습니다! 먼저 연구 주제나 키워드를 입력하거나 아래 [예시 버튼]을 클릭해 주세요.", "🚨 Step 1 search box is empty! Please enter a research topic first.")
        st.session_state.toast_msg = {"msg": err_msg, "icon": "🚨"}
        trigger_scroll_to("step-01-anchor", alert_msg=err_msg, target_step_num=1)
        return
    opt = optimize_search_query(raw)
    if opt.get("typo_pairs"):
        st.session_state.last_typo_pairs = opt["typo_pairs"]
    if opt["was_modified"] and opt["optimized"]:
        st.session_state.last_nl_input = raw
        st.session_state.kw_input = opt["optimized"]
        st.session_state.step1_confirmed = True
        st.session_state.step_order_alert = None
        if opt.get("typo_corrected") and opt.get("typo_pairs"):
            pair_str = ", ".join([f"'{w}'➔'{r}'" for w, r in opt["typo_pairs"]])
            st.session_state.toast_msg = {
                "msg": tr(f"🪄 오타 자동 교정({pair_str}) 및 1단계 확정이 완료되었습니다! 이제 아래 2단계로 이동해 주세요.", f"🪄 Typo corrected ({pair_str}) & Step 1 confirmed! Proceed to Step 2."),
                "icon": "🪄"
            }
        else:
            st.session_state.toast_msg = {
                "msg": tr("🎉 자연어 자동 변환 및 1단계 확정이 완료되었습니다! 이제 아래 2단계로 내려가 [2단계 완료] 버튼을 눌러주세요.", "🎉 Natural language converted & Step 1 confirmed! Proceed to Step 2."),
                "icon": "🎉"
            }
    else:
        st.session_state.step1_confirmed = True
        st.session_state.step_order_alert = None
        st.session_state.toast_msg = {
            "msg": tr("🎉 1단계 학술 검색식 확정이 완료되었습니다! 이제 아래 2단계로 내려가 [2단계 완료] 버튼을 눌러주세요.", "🎉 Step 1 search formula confirmed! Proceed to Step 2."),
            "icon": "🎉"
        }

def cb_apply_typo_correction(corrected_text: str):
    opt = optimize_search_query(corrected_text)
    final_q = opt["optimized"] if (opt["was_modified"] and opt["optimized"]) else corrected_text
    st.session_state.kw_input = final_q
    st.session_state.step1_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr(f"✨ 오타 교정 검색식 [{final_q}]이 적용되고 1단계가 확정되었습니다!", f"✨ Applied corrected query [{final_q}] and confirmed Step 1!"),
        "icon": "✨"
    }

def cb_add_autocomplete_term(en_term: str, ko_label: str, mode: str = "AND"):
    cur_q = st.session_state.get("kw_input", "").strip()
    if mode == "REPLACE" or not cur_q:
        st.session_state.kw_input = en_term
        msg_ko = f"🔤 자동완성 키워드 [{ko_label} ➔ {en_term}]로 검색식이 설정되고 1단계가 확정되었습니다!"
        msg_en = f"🔤 Set query to autocomplete keyword [{en_term}] and confirmed Step 1!"
    else:
        if en_term.lower() not in cur_q.lower():
            st.session_state.kw_input = f"{cur_q} {en_term}".strip()
        msg_ko = f"➕ 자동완성 키워드 [{ko_label} ➔ {en_term}]가 검색식에 추가되고 1단계가 확정되었습니다!"
        msg_en = f"➕ Added autocomplete keyword [{en_term}] and confirmed Step 1!"
    st.session_state.step1_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {"msg": tr(msg_ko, msg_en), "icon": "🔤"}

def cb_add_from_catalog_dropdown(mode: str = "AND"):
    sel_idx = st.session_state.get("ac_catalog_select", 0)
    if sel_idx is None or sel_idx < 0 or sel_idx >= len(ACADEMIC_AUTOCOMPLETE_CATALOG):
        return
    item = ACADEMIC_AUTOCOMPLETE_CATALOG[sel_idx]
    cb_add_autocomplete_term(item.get("query", item["en"]), item["ko"], mode=mode)

def cb_unconfirm_step1():
    st.session_state.step1_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr("✏️ 1단계 검색식 수정 모드로 전환되었습니다. 수정 후 [1단계 완료] 버튼을 눌러주세요.", "✏️ Step 1 unlocked for editing."),
        "icon": "✏️"
    }

def cb_clear_kw():
    st.session_state.kw_input = ""
    st.session_state.last_nl_input = ""
    st.session_state.last_typo_pairs = []
    st.session_state.step1_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr("🗑️ 검색창을 비웠습니다. 새로운 연구 주제를 입력해 주세요.", "🗑️ Search box cleared."),
        "icon": "🗑️"
    }

def set_example_query(raw_example_str):
    opt = optimize_search_query(raw_example_str)
    st.session_state.last_typo_pairs = []
    if opt["was_modified"] and opt["optimized"]:
        st.session_state.last_nl_input = raw_example_str
        st.session_state.kw_input = opt["optimized"]
    else:
        st.session_state.last_nl_input = ""
        st.session_state.kw_input = raw_example_str

    st.session_state.step1_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr("🎉 예시 주제가 최적 학술 검색식으로 입력되어 1단계가 완료되었습니다! 이제 아래 2단계로 이동해 주세요.", "🎉 Example applied & Step 1 complete! Proceed to Step 2."),
        "icon": "🎉"
    }

def cb_smart_builder_add(action_type):
    raw_term = st.session_state.get("builder_term_input", "").strip()
    cur_q = st.session_state.get("kw_input", "").strip()

    if not raw_term:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 조립기 입력칸에 추가하거나 제외할 단어를 입력해 주세요! (예: deep learning, 연하장애, animal)", "👆 Please type a word or phrase in the builder input box first!"),
            "icon": "👆"
        }
        return

    clean_term = raw_term.strip().strip('"').strip("'")
    typo_info = detect_and_correct_typos(clean_term)
    typo_note_ko = ""
    typo_note_en = ""
    if typo_info["has_typo"]:
        clean_term = typo_info["corrected_text"]
        pairs_txt = ", ".join([f"'{w}'➔'{r}'" for w, r in typo_info["corrections"]])
        typo_note_ko = f" (🪄 오타 자동 교정: {pairs_txt})"
        typo_note_en = f" (🪄 Auto-corrected: {pairs_txt})"

    if re.search(r"[가-힣]", clean_term):
        opt_t = optimize_search_query(clean_term)
        if opt_t["optimized"]:
            clean_term = opt_t["optimized"]

    if action_type == "AND":
        formatted = f'"{clean_term}"' if (" " in clean_term and not clean_term.startswith("(") and not clean_term.startswith('"')) else clean_term
        st.session_state.kw_input = f"{cur_q} {formatted}".strip()
        msg_ko = f"➕ 필수 포함(AND) 조건으로 [{formatted}] 항목이 검색식에 추가되고 1단계가 확정되었습니다!{typo_note_ko}"
        msg_en = f"➕ Added [{formatted}] as a required (AND) term!{typo_note_en}"

    elif action_type == "OR":
        formatted = f'"{clean_term}"' if (" " in clean_term and not clean_term.startswith("(") and not clean_term.startswith('"')) else clean_term
        if not cur_q:
            st.session_state.kw_input = formatted
        elif cur_q.endswith(")"):
            st.session_state.kw_input = f"{cur_q[:-1]} OR {formatted})"
        else:
            parts = cur_q.rsplit(" ", 1)
            if len(parts) == 1:
                st.session_state.kw_input = f"({parts[0]} OR {formatted})"
            else:
                st.session_state.kw_input = f"{parts[0]} ({parts[1]} OR {formatted})"
        msg_ko = f"🔄 동의어·유사어(OR) 묶음으로 [{formatted}] 항목이 결합되고 1단계가 확정되었습니다!{typo_note_ko}"
        msg_en = f"🔄 Combined [{formatted}] with OR logic!{typo_note_en}"

    elif action_type == "PHRASE":
        raw_unquoted = clean_term.strip('"').strip("'")
        formatted = f'"{raw_unquoted}"'
        st.session_state.kw_input = f"{cur_q} {formatted}".strip()
        msg_ko = f'🎯 정확한 구문 따옴표 [{formatted}] 항목이 추가되고 1단계가 확정되었습니다!{typo_note_ko}'
        msg_en = f'🎯 Added exact phrase [{formatted}] to query!{typo_note_en}'

    elif action_type == "EXCLUDE":
        raw_unquoted = clean_term.strip('"').strip("'").strip("()")
        if " OR " in raw_unquoted:
            tokens = [t.strip().strip('"') for t in raw_unquoted.split(" OR ") if t.strip()]
            formatted = " ".join([f'-"{t}"' if " " in t else f"-{t}" for t in tokens])
        else:
            formatted = f'-"{raw_unquoted}"' if " " in raw_unquoted else f"-{raw_unquoted}"
        st.session_state.kw_input = f"{cur_q} {formatted}".strip()
        msg_ko = f"🚫 제외 조건 [{formatted}] 항목이 반영되고 1단계가 확정되었습니다!{typo_note_ko}"
        msg_en = f"🚫 Added exclusion filter [{formatted}]!{typo_note_en}"

    st.session_state.builder_term_input = ""
    st.session_state.step1_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {"msg": tr(msg_ko, msg_en), "icon": "✅"}

def append_preset_snippet(snippet, desc_ko, desc_en):
    cur_q = st.session_state.get("kw_input", "").strip()
    if snippet not in cur_q:
        st.session_state.kw_input = f"{cur_q} {snippet}".strip()
    st.session_state.step1_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr(f"✅ {desc_ko} 조건({snippet})이 검색식에 추가되고 1단계가 확정되었습니다!", f"✅ Added {desc_en} ({snippet}) to query!"),
        "icon": "✅"
    }

def set_year_preset(years_back):
    cur_yr = get_current_year()
    st.session_state.end_yr_input = cur_yr
    if years_back is None:
        st.session_state.start_yr_input = 1980
        label_ko = f"1980년 – {cur_yr}년 (전체 기간)"
    else:
        st.session_state.start_yr_input = max(1950, cur_yr - years_back)
        label_ko = f"{st.session_state.start_yr_input}년 – {cur_yr}년 (최근 {years_back}년)"
    st.session_state.step2_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr(f"📅 출판 연도가 [{label_ko}]으로 변경되었습니다! 아래 [2단계 완료] 버튼을 눌러 확정해 주세요.", f"📅 Timeframe updated to {st.session_state.start_yr_input}–{cur_yr}! Click [Confirm Step 2] below."),
        "icon": "📅"
    }

def cb_confirm_step2():
    # Sequential Prerequisite Check: Ensure Step 1 is confirmed first!
    has_s1_data = bool(st.session_state.get("kw_input", "").strip() or st.session_state.get("cart"))
    if not (st.session_state.get("step1_confirmed") and has_s1_data):
        st.session_state.step2_confirmed = False
        if not has_s1_data:
            alarm_msg = tr(
                "🚨 [순서 알림] 아직 1단계(연구 주제 입력 및 확정)가 진행되지 않았습니다! 먼저 1단계를 완료하실 수 있도록 1단계 위치로 자동 이동합니다.",
                "🚨 [Order Alert] Step 1 (Research Topic) is not entered yet! Automatically scrolling to Step 1 so you can complete it in order."
            )
        else:
            alarm_msg = tr(
                "🚨 [순서 알림] 1단계 검색어는 입력되었으나 아직 [1단계 완료] 버튼을 누르지 않으셨습니다! 순서대로 진행되도록 1단계 위치로 자동 이동합니다.",
                "🚨 [Order Alert] Please click [Confirm Step 1] first! Automatically scrolling to Step 1."
            )
        st.session_state.toast_msg = {"msg": alarm_msg, "icon": "🚨"}
        trigger_scroll_to("step-01-anchor", alert_msg=alarm_msg, target_step_num=1)
        return

    if st.session_state.start_yr_input > st.session_state.end_yr_input:
        st.session_state.step2_confirmed = False
        yr_err = tr("🚨 시작 연도가 종료 연도보다 클 수 없습니다! 2단계 연도를 먼저 수정해 주세요.", "🚨 Start Year cannot exceed End Year!")
        st.session_state.toast_msg = {"msg": yr_err, "icon": "🚨"}
        trigger_scroll_to("step-02-anchor", alert_msg=yr_err, target_step_num=2)
        return

    st.session_state.step2_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr("🎉 2단계 완료! 탐색 알고리즘 및 필터 설정이 확정되었습니다. 이제 아래 3단계의 [3단계 완료] 버튼을 눌러주세요!", "🎉 Step 2 confirmed! Proceed to Step 3 below."),
        "icon": "🎉"
    }

def cb_confirm_step3():
    # 1. Check Step 1 prerequisite first!
    has_s1_data = bool(st.session_state.get("kw_input", "").strip() or st.session_state.get("cart"))
    if not (st.session_state.get("step1_confirmed") and has_s1_data):
        st.session_state.step3_confirmed = False
        alarm_s1 = tr(
            "🚨 [순서 알림] 전 단계인 1단계(연구 주제 입력 및 확정)가 아직 완료되지 않았습니다! 순서대로 완벽하게 진행되도록 1단계 위치로 자동 이동합니다.",
            "🚨 [Order Alert] Step 1 (Research Topic) has not been confirmed yet! Automatically scrolling to Step 1."
        )
        st.session_state.toast_msg = {"msg": alarm_s1, "icon": "🚨"}
        trigger_scroll_to("step-01-anchor", alert_msg=alarm_s1, target_step_num=1)
        return

    # 2. Check Step 2 prerequisite second!
    s2_ok = bool(st.session_state.get("step2_confirmed") and (st.session_state.get("start_yr_input", 2016) <= st.session_state.get("end_yr_input", 2026)))
    if not s2_ok:
        st.session_state.step3_confirmed = False
        alarm_s2 = tr(
            "🚨 [순서 알림] 바로 전 단계인 2단계(탐색 알고리즘 · 출판 연도 확정)가 아직 완료되지 않았습니다! 순서대로 진행되도록 2단계 위치로 자동 이동합니다.",
            "🚨 [Order Alert] Step 2 (Algorithm & Timeframe) has not been confirmed yet! Automatically scrolling to Step 2."
        )
        st.session_state.toast_msg = {"msg": alarm_s2, "icon": "🚨"}
        trigger_scroll_to("step-02-anchor", alert_msg=alarm_s2, target_step_num=2)
        return

    # 3. Validate Step 3 scope
    if st.session_state.scope_mode == "TARGETED" and len(st.session_state.cart) == 0:
        st.session_state.step3_confirmed = False
        err_s3 = tr("⚠️ [특정 학술지만 지정하여 검색]을 선택하셨습니다. 최소 1개 이상의 학술지를 먼저 추가하거나 [전 세계 모든 학술지 통합 검색]으로 변경해 주세요!", "⚠️ Please add at least 1 journal or switch to Global Search!")
        st.session_state.toast_msg = {"msg": err_s3, "icon": "⚠️"}
        trigger_scroll_to("step-03-anchor", alert_msg=err_s3, target_step_num=3)
        return

    st.session_state.step3_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr("🎉 3단계 완료! 1·2·3단계가 모두 순서대로 확정되었습니다. 이제 바로 아래 4단계에서 [🚀 논문 데이터 수집 시작하기] 버튼을 클릭하세요!", "🎉 Step 3 confirmed! Click Start Extraction in Step 4 below!"),
        "icon": "🎉"
    }

def cb_confirm_all_steps_quick():
    raw = st.session_state.get("kw_input", "").strip()
    if raw:
        opt = optimize_search_query(raw)
        if opt["was_modified"] and opt["optimized"]:
            st.session_state.last_nl_input = raw
            st.session_state.kw_input = opt["optimized"]
    st.session_state.step1_confirmed = True
    st.session_state.step2_confirmed = True
    st.session_state.step3_confirmed = True
    st.session_state.step_order_alert = None
    st.session_state.toast_msg = {
        "msg": tr("🎉 1·2·3단계 설정이 한 번에 확정되었습니다! 바로 아래 반짝이는 [🚀 논문 데이터 수집 시작하기] 버튼을 클릭하세요!", "🎉 Steps 1–3 confirmed! Click the glowing Start Extraction button below."),
        "icon": "🎉"
    }

def cb_add_preset(issn):
    st.session_state.step3_active_tab = "PRESET"
    info = fetch_journal_info(issn)
    if info:
        st.session_state.cart[issn] = info
        st.session_state[f"pre_chk_{issn}"] = False
        st.session_state.scope_mode = "TARGETED"
        st.session_state.step3_confirmed = False
        st.session_state.toast_msg = {
            "msg": tr(f"🏛️ '{info['name']}' 학술지가 추가되었습니다! (현재 {len(st.session_state.cart)}개) 추가 완료 후 아래 [3단계 완료] 버튼을 눌러주세요.", f"🏛️ Added '{info['name']}'! Click [Confirm Step 3] when done."),
            "icon": "✅"
        }

def cb_add_category_presets(cat_name):
    st.session_state.step3_active_tab = "PRESET"
    jrnls = GLOBAL_PRESETS.get(cat_name, {})
    added_names = []
    for j_name, issn in jrnls.items():
        if issn not in st.session_state.cart:
            info = fetch_journal_info(issn)
            if info:
                st.session_state.cart[issn] = info
                added_names.append(info["name"])
            st.session_state[f"pre_chk_{issn}"] = False
    st.session_state.scope_mode = "TARGETED"
    st.session_state.step3_confirmed = False
    if added_names:
        st.session_state.toast_msg = {
            "msg": tr(f"🏛️ [{cat_name}] 분야 학술지 {len(added_names)}개가 한 번에 추가되었습니다! (현재 총 {len(st.session_state.cart)}개)", f"🏛️ Added {len(added_names)} journals from [{cat_name}]!"),
            "icon": "✅"
        }
    else:
        st.session_state.toast_msg = {
            "msg": tr(f"ℹ️ [{cat_name}] 분야의 학술지는 이미 모두 목록에 추가되어 있습니다.", f"ℹ️ All journals in [{cat_name}] are already in your list."),
            "icon": "ℹ️"
        }

def cb_toggle_select_all_presets():
    st.session_state.step3_active_tab = "PRESET"
    available_issns = [
        issn for jrnls in GLOBAL_PRESETS.values() for issn in jrnls.values()
        if issn not in st.session_state.cart
    ]
    if not available_issns:
        return
    all_checked = all(bool(st.session_state.get(f"pre_chk_{issn}", False)) for issn in available_issns)
    target_val = not all_checked
    for issn in available_issns:
        st.session_state[f"pre_chk_{issn}"] = target_val
    st.session_state.toast_msg = {
        "msg": tr(
            f"☑️ 추가 가능한 권위 학술지 {len(available_issns)}개를 모두 선택했습니다! [체크한 학술지 한 번에 추가] 버튼을 눌러주세요." if target_val else "⬜ 권위 학술지 체크 선택을 모두 해제했습니다.",
            f"☑️ Selected all {len(available_issns)} available preset journals!" if target_val else "⬜ Cleared preset selections."
        ),
        "icon": "☑️"
    }

def cb_add_selected_presets():
    st.session_state.step3_active_tab = "PRESET"
    selected_issns = [
        issn for jrnls in GLOBAL_PRESETS.values() for issn in jrnls.values()
        if issn not in st.session_state.cart and st.session_state.get(f"pre_chk_{issn}", False)
    ]
    if not selected_issns:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 아래 분야별 학술지 목록에서 추가할 학술지의 왼쪽 체크박스(☑️)를 1개 이상 선택해 주세요!", "👆 Please check at least 1 preset journal checkbox below first!"),
            "icon": "👆"
        }
        return
    added_count = 0
    for issn in selected_issns:
        info = fetch_journal_info(issn)
        if info:
            st.session_state.cart[issn] = info
            added_count += 1
        st.session_state[f"pre_chk_{issn}"] = False
    if added_count > 0:
        st.session_state.scope_mode = "TARGETED"
        st.session_state.step3_confirmed = False
        st.session_state.toast_msg = {
            "msg": tr(f"🎉 선택한 권위 학술지 {added_count}개가 한 번에 추가되었습니다! (현재 총 {len(st.session_state.cart)}개)", f"🎉 Batch added {added_count} preset journals! (Total: {len(st.session_state.cart)})"),
            "icon": "🎉"
        }

def cb_add_searched(issn, info):
    st.session_state.step3_active_tab = "SEARCH"
    st.session_state.cart[issn] = info
    st.session_state[f"srch_chk_{issn}"] = False
    st.session_state.scope_mode = "TARGETED"
    st.session_state.step3_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr(f"🏛️ '{info['name']}' 학술지가 추가되었습니다! (현재 {len(st.session_state.cart)}개) 검색 화면에서 계속 다른 학술지를 추가하실 수 있습니다.", f"🏛️ Added '{info['name']}'! You can continue adding more journals from search results."),
        "icon": "✅"
    }

def cb_toggle_select_all_searched():
    st.session_state.step3_active_tab = "SEARCH"
    res = st.session_state.get("skw_res") or []
    available_issns = [r["issn"] for r in res if r.get("issn") and r["issn"] not in st.session_state.cart]
    if not available_issns:
        return
    all_checked = all(bool(st.session_state.get(f"srch_chk_{issn}", False)) for issn in available_issns)
    target_val = not all_checked
    for issn in available_issns:
        st.session_state[f"srch_chk_{issn}"] = target_val
    st.session_state.toast_msg = {
        "msg": tr(
            f"☑️ 검색된 학술지 {len(available_issns)}개를 모두 선택했습니다! [체크한 검색 학술지 한 번에 추가하기] 버튼을 눌러주세요." if target_val else "⬜ 검색 결과 선택을 모두 해제했습니다.",
            f"☑️ Selected all {len(available_issns)} searched journals!" if target_val else "⬜ Cleared search selections."
        ),
        "icon": "☑️"
    }

def cb_add_selected_searched():
    st.session_state.step3_active_tab = "SEARCH"
    res = st.session_state.get("skw_res") or []
    added_count = 0
    for info in res:
        issn = info.get("issn")
        if issn and issn not in st.session_state.cart and st.session_state.get(f"srch_chk_{issn}", False):
            st.session_state.cart[issn] = info
            st.session_state[f"srch_chk_{issn}"] = False
            added_count += 1
    if added_count == 0:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 검색 결과 목록에서 추가할 학술지의 왼쪽 체크박스(☑️)를 1개 이상 선택해 주세요!", "👆 Please check at least 1 journal checkbox in the search results first!"),
            "icon": "👆"
        }
        return
    st.session_state.scope_mode = "TARGETED"
    st.session_state.step3_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr(f"🎉 체크하신 검색 학술지 {added_count}개가 한 번에 추가되었습니다! (현재 총 {len(st.session_state.cart)}개)", f"🎉 Added {added_count} selected journals at once! (Total: {len(st.session_state.cart)})"),
        "icon": "🎉"
    }

def cb_remove_journal(issn):
    st.session_state.cart.pop(issn, None)
    st.session_state.pop(f"cart_chk_{issn}", None)
    st.session_state.step3_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr("🗑️ 선택한 학술지가 목록에서 제외되었습니다. 아래 [3단계 완료] 버튼을 다시 눌러 확정해 주세요.", "🗑️ Journal removed. Please re-confirm Step 3."),
        "icon": "🗑️"
    }

def cb_toggle_select_all_cart():
    cart_issns = list(st.session_state.cart.keys())
    if not cart_issns:
        return
    all_checked = all(bool(st.session_state.get(f"cart_chk_{issn}", False)) for issn in cart_issns)
    target_val = not all_checked
    for issn in cart_issns:
        st.session_state[f"cart_chk_{issn}"] = target_val
    st.session_state.toast_msg = {
        "msg": tr(
            f"☑️ 현재 담긴 학술지 {len(cart_issns)}개를 모두 체크했습니다! [체크한 학술지 선택 비우기] 버튼으로 일괄 삭제할 수 있습니다." if target_val else "⬜ 학술지 목록 체크 선택을 해제했습니다.",
            f"☑️ Selected all {len(cart_issns)} journals in list!" if target_val else "⬜ Deselected all journals in list."
        ),
        "icon": "☑️"
    }

def cb_remove_selected_cart():
    cart_issns = list(st.session_state.cart.keys())
    to_remove = [issn for issn in cart_issns if st.session_state.get(f"cart_chk_{issn}", False)]
    if not to_remove:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 비울 학술지의 왼쪽 체크박스(☑️)를 1개 이상 선택한 뒤 [체크한 학술지 선택 비우기] 버튼을 눌러주세요!", "👆 Please check at least 1 journal checkbox in your list to remove!"),
            "icon": "👆"
        }
        return
    for issn in to_remove:
        st.session_state.cart.pop(issn, None)
        st.session_state.pop(f"cart_chk_{issn}", None)
    st.session_state.step3_confirmed = False
    st.session_state.toast_msg = {
        "msg": tr(f"🗑️ 체크하신 학술지 {len(to_remove)}개가 목록에서 한 번에 제외되었습니다! (남은 학술지: {len(st.session_state.cart)}개)", f"🗑️ Removed {len(to_remove)} selected journal(s)! ({len(st.session_state.cart)} remaining)"),
        "icon": "🗑️"
    }

def cb_empty_cart(switch_to_global=False):
    for issn in list(st.session_state.cart.keys()):
        st.session_state.pop(f"cart_chk_{issn}", None)
    st.session_state.cart.clear()
    if switch_to_global:
        st.session_state.scope_mode = "GLOBAL"
        msg = tr("🌍 학술지 목록을 모두 비우고 전 세계 통합 검색 모드로 전환했습니다. 아래 [3단계 완료] 버튼을 눌러 확정해 주세요.", "🌍 Cleared journals and switched to Global Search Mode.")
    else:
        msg = tr("🗑️ 선택된 학술지 목록을 모두 비웠습니다.", "🗑️ Cleared all selected journals.")
    st.session_state.step3_confirmed = False
    st.session_state.toast_msg = {"msg": msg, "icon": "🗑️"}

def _execute_journal_search_with_typo_guard(raw_skw: str):
    st.session_state.step3_active_tab = "SEARCH"
    skw = (raw_skw or "").strip()
    st.session_state.last_search_typo_note = ""
    if not skw:
        return
    effective_skw = skw
    typo_info = detect_and_correct_typos(skw)
    if typo_info["has_typo"]:
        effective_skw = typo_info["corrected_text"]
        pairs_str = ", ".join([f"'{w}'➔'{r}'" for w, r in typo_info["corrections"]])
        st.session_state.last_search_typo_note = tr(
            f"🪄 입력하신 검색어의 오타를 자동 교정하여 검색했습니다 ({pairs_str})",
            f"🪄 Auto-corrected journal search typo ({pairs_str})"
        )
        st.session_state.search_kw_input = effective_skw

    # If Korean term entered in journal search, convert to primary English keyword
    if re.search(r"[가-힣]", effective_skw):
        opt_j = optimize_search_query(effective_skw)
        en_tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", opt_j.get("optimized", ""))
        en_tokens = [t for t in en_tokens if t.upper() not in ("OR", "AND", "NOT")]
        if en_tokens:
            mapped_en = " ".join(en_tokens[:2])
            st.session_state.last_search_typo_note = tr(
                f"🌐 한글 학술 키워드 '{skw}' ➔ 영문 학술지 검색어 '{mapped_en}'(으)로 자동 변환하여 검색했습니다.",
                f"🌐 Converted Korean keyword '{skw}' ➔ '{mapped_en}' for journal search."
            )
            effective_skw = mapped_en
            st.session_state.search_kw_input = mapped_en

    res = search_journal_db(effective_skw)
    st.session_state.skw_res = res
    for r in (res or []):
        if r.get("issn"):
            st.session_state[f"srch_chk_{r['issn']}"] = False
    if res:
        note_prefix = f"{st.session_state.last_search_typo_note} · " if st.session_state.last_search_typo_note else ""
        st.session_state.toast_msg = {
            "msg": tr(f"🔍 {note_prefix}총 {len(res)}개의 학술지를 찾았습니다! 여러 개를 체크해 한 번에 추가하거나 개별 [➕ 바로 추가] 버튼을 눌러보세요.", f"🔍 {note_prefix}Found {len(res)} matching journals! Check multiple to batch-add or click Add."),
            "icon": "✅"
        }
    else:
        st.session_state.toast_msg = {
            "msg": tr("❌ 일치하는 학술지가 없습니다. 아래 [원클릭 학술지 자동완성 추천 버튼]을 누르거나 다른 영문 학술지명을 입력해 보세요.", "❌ No matching journals found. Try clicking one of the autocomplete suggestion buttons below."),
            "icon": "❌"
        }

def cb_search_db():
    skw = st.session_state.get("search_kw_input", "").strip()
    _execute_journal_search_with_typo_guard(skw)

def cb_quick_search_journal(kw_str: str):
    st.session_state.search_kw_input = kw_str
    _execute_journal_search_with_typo_guard(kw_str)

def cb_manual_issn():
    st.session_state.step3_active_tab = "ISSN"
    raw_issn_str = st.session_state.get("manual_issn_input", "").strip()
    if not raw_issn_str:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 추가할 8자리 ISSN 번호(예: 0028-0836)를 입력해 주세요! 하이픈(-) 없이 숫자 8자리(00280836)만 입력해도 자동 교정됩니다.", "👆 Please enter one or more 8-digit ISSNs (e.g., 0028-0836)!"),
            "icon": "👆"
        }
        return

    # Support multiple ISSNs separated by comma, whitespace, or newline
    candidates = re.findall(r"\d{4}-\d{3}[\dXx]|\d{7}[\dXx]", raw_issn_str)
    if not candidates:
        candidates = [t.strip() for t in re.split(r"[,;\s]+", raw_issn_str) if t.strip()]

    added_names = []
    invalid_tokens = []
    digit_hints = []
    for token in candidates:
        clean_alnum = re.sub(r"[^0-9Xx]", "", token).upper()
        if len(clean_alnum) == 8:
            norm_issn = f"{clean_alnum[:4]}-{clean_alnum[4:]}"
        else:
            norm_issn = token.upper()
            if len(clean_alnum) in (7, 9):
                digit_hints.append(f"'{token}'({len(clean_alnum)}자리 ➔ 8자리 필요)")
        info = fetch_journal_info(norm_issn)
        if info:
            actual_issn = info.get("issn") or norm_issn
            st.session_state.cart[actual_issn] = info
            added_names.append(f"{info['name']} ({actual_issn})")
        else:
            invalid_tokens.append(token)

    if added_names:
        st.session_state.scope_mode = "TARGETED"
        st.session_state.step3_confirmed = False
        if len(added_names) == 1 and not invalid_tokens:
            msg = tr(f"✅ {added_names[0]} 학술지가 추가되었습니다! 계속 다른 ISSN을 추가하시거나 아래 [3단계 완료] 버튼을 눌러주세요.", f"✅ Added {added_names[0]}! Confirm Step 3 below when done.")
        else:
            fail_note = f" (미확인 {len(invalid_tokens)}건 제외)" if invalid_tokens else ""
            msg = tr(f"🎉 총 {len(added_names)}개의 ISSN 학술지가 한 번에 추가되었습니다!{fail_note}", f"🎉 Added {len(added_names)} ISSN journal(s)!{fail_note}")
        st.session_state.toast_msg = {"msg": msg, "icon": "✅"}
    else:
        hint_txt = f" [자릿수 오타 확인: {', '.join(digit_hints)}]" if digit_hints else ""
        st.session_state.toast_msg = {
            "msg": tr(f"❌ 유효하지 않은 ISSN 번호입니다.{hint_txt} 8자리 국제표준일련번호(예: 0028-0836)를 입력하거나 아래 [학술지 이름으로 ISSN 자동완성 선택]을 이용해 보세요.", f"❌ Invalid ISSN format.{hint_txt} Please use 8 digits (e.g., 0028-0836) or select from the autocomplete picker below."),
            "icon": "❌"
        }

def cb_add_selected_issn_autocomplete():
    st.session_state.step3_active_tab = "ISSN"
    selected_items = st.session_state.get("issn_autocomplete_multiselect", [])
    if not selected_items:
        st.session_state.toast_msg = {
            "msg": tr("👆 먼저 아래 자동완성 목록에서 추가할 학술지(ISSN)를 1개 이상 선택해 주세요!", "👆 Please select at least 1 journal from the ISSN autocomplete list first!"),
            "icon": "👆"
        }
        return
    added_cnt = 0
    for item_str in selected_items:
        m = re.search(r"(\d{4}-\d{3}[\dXx])", str(item_str))
        if m:
            issn = m.group(1)
            if issn not in st.session_state.cart:
                info = fetch_journal_info(issn)
                if info:
                    st.session_state.cart[issn] = info
                    added_cnt += 1
    st.session_state.issn_autocomplete_multiselect = []
    if added_cnt > 0:
        st.session_state.scope_mode = "TARGETED"
        st.session_state.step3_confirmed = False
        st.session_state.toast_msg = {
            "msg": tr(f"🎉 자동완성으로 선택하신 {added_cnt}개 학술지(ISSN)가 오타 없이 정확하게 추가되었습니다!", f"🎉 Added {added_cnt} journal(s) via ISSN autocomplete!"),
            "icon": "🎉"
        }

def cb_set_table_search(term_str: str):
    st.session_state.local_search_input = term_str
    if term_str:
        st.session_state.toast_msg = {
            "msg": tr(f"🔍 표 내부 검색어가 '{term_str}'(으)로 자동 설정되었습니다!", f"🔍 Table filter set to '{term_str}'!"),
            "icon": "🔍"
        }
    else:
        st.session_state.toast_msg = {
            "msg": tr("🔄 표 내부 키워드 검색 필터를 초기화하여 전체 논문을 표시합니다.", "🔄 Cleared table keyword filter."),
            "icon": "🔄"
        }

def cb_trigger_rerun():
    st.session_state.step1_confirmed = True
    st.session_state.step2_confirmed = True
    st.session_state.step3_confirmed = True
    st.session_state.trigger_rerun_pipeline = True

def reset_all_states():
    cur_yr = get_current_year()
    st.session_state.cart = {}
    st.session_state.df = None
    st.session_state.executed_config = None
    st.session_state.skw_res = None
    st.session_state.scope_mode = "GLOBAL"
    st.session_state.step3_active_tab = "PRESET"
    st.session_state.last_nl_input = ""
    st.session_state.last_typo_pairs = []
    st.session_state.last_search_typo_note = ""
    st.session_state.step1_confirmed = False
    st.session_state.step2_confirmed = False
    st.session_state.step3_confirmed = False
    st.session_state.step_order_alert = None
    st.session_state.scroll_target_anchor = ""
    st.session_state.start_yr_input = cur_yr - 10
    st.session_state.end_yr_input = cur_yr
    for key in list(st.session_state.keys()):
        if key in ["kw_input", "builder_term_input", "search_kw_input", "manual_issn_input", "local_search_input", "issn_autocomplete_multiselect"] or key.startswith(("pre_chk_", "srch_chk_", "cart_chk_")):
            del st.session_state[key]
    st.cache_data.clear()
    save_session_snapshot()
    st.session_state.toast_msg = {
        "msg": tr(f"🔄 모든 설정이 초기 상태(출판 연도 {cur_yr-10}–{cur_yr}년)로 깨끗하게 리셋되었습니다.", "🔄 All settings and results have been reset."),
        "icon": "🔄"
    }

def log_out():
    sid = st.session_state.get("session_sid")
    if sid:
        get_persistent_session_store().pop(sid, None)
    _clear_query_params()
    st.session_state.authenticated = False
    st.session_state._explicit_logout = True
    st.session_state.toast_msg = {
        "msg": tr("🚪 안전하게 로그아웃되었습니다. 다시 이용하시려면 비밀번호를 입력해 로그인해 주세요.", "🚪 You have been safely logged out."),
        "icon": "🚪"
    }



# ==========================================
# 🌟 Top Navigation Bar & Spacious Utility Controls
# ==========================================
st.markdown(f"""
<div class="top-navbar">
    <div class="brand-logo-wrap">
        <div class="brand-icon">OS</div>
        <div>
            <div class="brand-title">OmniScholar <span style="font-weight:600; font-size:1.02rem; color:#475569;">| {tr('학술 논문 인용·피인용 네트워크 분석 플랫폼', 'Academic Citation & Literature Intelligence')}</span></div>
            <div class="brand-subtitle">{tr('전 세계 2억 5천만 편 논문 실시간 탐색 · 뿌리(Root) 논문 역추적 · 원클릭 엑셀/RIS/인용문 리포트', 'Real-time 250M+ Works Analysis · Foundational Root Tracing · Formatted Excel, RIS & Citation Export')}</div>
        </div>
    </div>
    <div>
        <span class="status-pill"><span class="status-dot"></span> {tr('OpenAlex 학술 엔진 정상 가동 중', 'OpenAlex Engine Online')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if APP_PASSWORD:
    nav_c1, nav_c_gloss, nav_c2, nav_c3, nav_c4 = st.columns([2.3, 2.7, 2.1, 1.6, 1.3])
else:
    nav_c1, nav_c_gloss, nav_c2, nav_c3 = st.columns([2.6, 3.0, 2.4, 2.0])

with nav_c1:
    st.button(
        tr("📖 사용 가이드 열기 / 닫기", "📖 Toggle User Guide"),
        on_click=toggle_guide,
        use_container_width=True
    )
with nav_c_gloss:
    st.button(
        tr("📘 학술 용어·지표 쉬운 해설집 열기/닫기", "📘 Academic Terms & Metrics Guide"),
        on_click=toggle_glossary,
        use_container_width=True
    )
with nav_c2:
    st.button(
        "🌐 언어 모드: 한국어 + English" if st.session_state.ui_lang == "KO_EN" else "🌐 Language: English Only",
        on_click=toggle_language,
        use_container_width=True
    )
with nav_c3:
    st.button(
        tr("🔄 처음부터 초기화 (Reset)", "🔄 Reset Workspace"),
        on_click=reset_all_states,
        use_container_width=True
    )
if APP_PASSWORD:
    with nav_c4:
        st.button(
            tr("🚪 로그아웃 (Logout)", "🚪 Logout"),
            on_click=log_out,
            use_container_width=True
        )

if st.session_state.show_glossary:
    render_academic_glossary_panel(lang=st.session_state.ui_lang)

if st.session_state.show_guide:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; border-bottom:1.5px solid #E2E8F0; padding-bottom:10px; margin-bottom:12px;">
            <span style="font-size:1.15rem; font-weight:800; color:#0F172A;">📖 {tr('OmniScholar 4단계 진행 가이드 (반짝이는 파란색 완료 버튼을 순서대로 눌러주세요)', 'OmniScholar 4-Step Quick Guide')}</span>
            <a href="User_Manual" target="_blank" style="font-size:0.94rem; font-weight:800; color:#2563EB; text-decoration:none;">
                {tr('↗ 새 탭에서 전체 매뉴얼 자세히 보기', '↗ Open Full Manual in New Tab')}
            </a>
        </div>
        """, unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3, gap="medium")
        with g1:
            st.markdown(f"""
            **🎯 1단계: {tr('연구 주제 및 검색식 확정', 'Confirm Topic & Query')}**
            - {tr('평소 말하듯 자연어 문장을 입력하고 반짝이는 **[👉 1단계 완료]** 버튼을 누르면 최적 학술 검색식으로 확정되며 완료 배지로 바뀝니다.', 'Enter any natural sentence and click the glowing **[👉 Confirm Step 1]** button.')}
            - {tr('검색 연산자가 익숙하지 않다면 아래 **[🧩 초보자용 검색어 자동 조립기]**나 **[예시 버튼]**을 이용해 보세요.', 'Use the Interactive Query Builder or Example buttons to build queries effortlessly.')}
            """)
        with g2:
            st.markdown(f"""
            **🧭 2–3단계: {tr('탐색 방식 및 학술지 범위 확정', 'Confirm Algorithm & Scope')}**
            - {tr('**2단계**에서 탐색 알고리즘과 출판 연도(기본 최근 10년)를 확인한 뒤 반짝이는 **[👉 2단계 완료]** 버튼을 누릅니다.', 'In Step 2, review your algorithm and publication years, then click **[👉 Confirm Step 2]**.')}
            - {tr('**3단계**에서 전 세계 통합 검색 또는 특정 저널 지정을 확인한 뒤 반짝이는 **[👉 3단계 완료]** 버튼을 누릅니다.', 'In Step 3, confirm global or targeted journal scope.')}
            """)
        with g3:
            st.markdown(f"""
            **🚀 4단계: {tr('최종 점검 · 수집 · 인용 복사', 'Verify, Extract & Copy Citations')}**
            - {tr('1·2·3단계를 모두 확정하면 **4단계**의 **[🚀 논문 데이터 수집 시작하기]** 버튼이 반짝이며 활성화됩니다.', 'Once Steps 1–3 are confirmed, click the glowing extraction button in Step 4.')}
            - {tr('수집 후 위쪽 필터를 변경하면 **주황색 재분석 유도 버튼**이 자동으로 나타나 이전 결과와 혼동되는 일을 완벽히 방지합니다.', 'If you change any filter after extraction, a pulsing re-run button appears automatically.')}
            """)

stepper_placeholder = st.empty()


# ==========================================
# 🎯 STEP 01: Research Topic & Interactive Formula Builder
# ==========================================
raw_kw_pre = st.session_state.get("kw_input", "").strip()
if not raw_kw_pre and not st.session_state.cart:
    st.session_state.step1_confirmed = False

s1_banner_state = "done" if st.session_state.step1_confirmed else "active"
s1_banner_text = tr("1단계 확정 완료", "Step 1 Confirmed") if st.session_state.step1_confirmed else tr("필수 진행: 검색어 입력 후 완료 버튼을 눌러주세요", "Action Required: Enter Topic & Click Confirm")

render_step_banner(
    step_class="step1",
    step_num_text="STEP 01 / 04",
    title_text=tr("🎯 1단계: 연구 주제 입력 및 스마트 학술 검색식 확정", "🎯 STEP 01: Enter Research Topic & Confirm Search Formula"),
    state=s1_banner_state,
    status_text=s1_banner_text,
    anchor_id="step-01-anchor"
)

with st.container(border=True):
    if st.session_state.step_order_alert and st.session_state.step_order_alert.get("step") == 1:
        st.markdown(f"""
        <div class="cta-attention-amber">
            <div>
                🚨 <b>{st.session_state.step_order_alert.get("msg")}</b><br>
                {tr('아래 검색창에 연구 주제를 입력(또는 예시 버튼 클릭)하신 뒤 반짝이는 <b>[👉 1단계 완료]</b> 버튼을 먼저 눌러주세요!', 'Please enter your research topic below and click the glowing <b>[👉 Confirm Step 1]</b> button first!')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Eye-catching instruction prompt when Step 1 is NOT yet confirmed
    if not raw_kw_pre:
        st.markdown(f"""
        <div class="cta-attention-box">
            <div>
                <span class="bounce-icon">👇</span> <b>{tr('[1단계 필수 입력] 먼저 바로 아래 검색창에 찾고 싶은 연구 주제(한글·영어 문장 또는 키워드)를 입력하거나, 아래쪽 [예시 버튼] 중 하나를 클릭해 주세요!', '[Step 1 Required Input] First, type your research topic below (in English or Korean) or click one of the [Example Topic] buttons below!')}</b>
            </div>
            <span class="cta-attention-badge">✨ {tr('지금 입력 필요', 'INPUT REQUIRED')}</span>
        </div>
        """, unsafe_allow_html=True)

    st.text_input(
        tr("검색어 또는 자연어 문장 입력", "Search Query Input"),
        key="kw_input",
        on_change=cb_on_kw_input_change,
        placeholder=tr(
            '✍️ 여기에 연구 주제를 자연어 문장 또는 검색식으로 입력하세요 (예: 뇌졸중 환자의 연하장애와 흡인성 폐렴을 머신러닝으로 예측하는 연구)',
            '✍️ Enter your research question or Boolean formula here (e.g., How does machine learning predict aspiration pneumonia in stroke dysphagia?)'
        ),
        label_visibility="collapsed"
    )

    current_kw_text = st.session_state.get("kw_input", "").strip()
    live_opt = optimize_search_query(current_kw_text)
    live_typo_check = detect_and_correct_typos(current_kw_text)

    # 🪄 Live Typo Detection & 1-Click Auto-Correction Banner
    if live_typo_check["has_typo"]:
        typo_pairs_txt = ", ".join([f"'{w}' ➔ '{r}'" for w, r in live_typo_check["corrections"]])
        corrected_preview = live_typo_check["corrected_text"]
        typo_box_title = tr(
            f"🪄 [오타·철자 교정 제안] 입력하신 검색어에서 오타 가능성({typo_pairs_txt})이 감지되었습니다!",
            f"🪄 [Did You Mean?] Possible spelling typo detected ({typo_pairs_txt})!"
        )
        typo_box_sub = tr(
            f"아래 버튼을 누르거나 [1단계 완료] 버튼을 클릭하시면 정확한 학술 철자({corrected_preview})로 자동 교정됩니다.",
            f"Click the button below or [Confirm Step 1] to automatically apply the corrected spelling ({corrected_preview})."
        )
        st.markdown(f"""
        <div class="typo-suggest-box">
            <b>{typo_box_title}</b><br>
            <span>• {typo_box_sub}</span>
        </div>
        """, unsafe_allow_html=True)
        st.button(
            tr(f"✨ 오타 즉시 교정 및 1단계 확정하기: {typo_pairs_txt}", f"✨ Apply Corrected Spelling Now: {typo_pairs_txt}"),
            key="btn_apply_live_typo_fix",
            on_click=cb_apply_typo_correction,
            args=(corrected_preview,),
            use_container_width=True
        )
    elif st.session_state.get("last_typo_pairs"):
        applied_pairs_txt = ", ".join([f"'{w}' ➔ '{r}'" for w, r in st.session_state.last_typo_pairs])
        applied_msg = tr(
            f"🪄 입력하셨던 단어의 철자 오타({applied_pairs_txt})를 인공지능이 정확한 학술 용어로 자동 교정하여 반영했습니다.",
            f"🪄 Automatically corrected spelling typo ({applied_pairs_txt}) into canonical academic terminology."
        )
        st.markdown(
            f"<div style='background:#EFF6FF; border:1.5px solid #93C5FD; border-radius:10px; padding:8px 14px; margin-bottom:8px; font-size:0.9rem; color:#1E3A8A; font-weight:700;'>"
            f"✅ {applied_msg}</div>",
            unsafe_allow_html=True
        )

    # 🔤 Dynamic Related Autocomplete Chips when typing in kw_input
    if current_kw_text:
        ac_suggestions = get_autocomplete_suggestions(current_kw_text, limit=4)
        if ac_suggestions:
            ac_hdr = tr(
                "🔤 입력하신 단어와 관련된 추천 학술 키워드 자동완성 (클릭 시 오타 없이 검색식에 바로 추가됩니다):",
                "🔤 Related Academic Autocomplete Suggestions (Click to append without typos):"
            )
            st.markdown(f"<div style='font-size:0.89rem; font-weight:700; color:#1E40AF; margin-top:4px; margin-bottom:4px;'>{ac_hdr}</div>", unsafe_allow_html=True)
            ac_cols = st.columns(len(ac_suggestions), gap="small")
            for idx_ac, ac_item in enumerate(ac_suggestions):
                with ac_cols[idx_ac]:
                    btn_lbl = f"➕ {ac_item['ko']} ({ac_item['en']})" if st.session_state.ui_lang == "KO_EN" else f"➕ {ac_item['en']}"
                    st.button(
                        btn_lbl,
                        key=f"dyn_ac_{idx_ac}_{ac_item['en']}",
                        on_click=cb_add_autocomplete_term,
                        args=(ac_item.get("query", ac_item["en"]), ac_item["ko"], "AND"),
                        use_container_width=True
                    )

    # Dynamic Action Area for STEP 01:
    # - When NOT confirmed: Shows a pulsing CTA prompt + glowing Primary button!
    # - When CONFIRMED: The pulsing button DISAPPEARS and transforms into an emerald Confirmed Banner!
    if not st.session_state.step1_confirmed:
        if current_kw_text:
            preview_formula = live_opt["optimized"] if (live_opt["was_modified"] and live_opt["optimized"]) else current_kw_text
            st.markdown(f"""
            <div class="cta-attention-box">
                <div>
                    <span class="bounce-icon">👇</span> <b>{tr('[1단계 완료 클릭 필수!] 검색어가 입력되었습니다! 다음 2단계로 넘어가기 위해 바로 아래 반짝이는 파란색 [1단계 완료] 버튼을 꼭 클릭해 주세요!', '[Action Required!] Your topic is entered! Click the glowing blue [Confirm Step 1] button right below to lock in your formula and proceed to Step 2!')}</b><br>
                    <span style="font-size:0.93rem; color:#1E3A8A;">• {tr('적용 예정 최적 학술 검색식', 'Formula to be confirmed')}: <code style="background:#FFFFFF; padding:2px 8px; border-radius:6px; font-weight:800; color:#1D4ED8;">{preview_formula}</code></span>
                </div>
                <span class="cta-attention-badge">👉 {tr('아래 버튼 클릭 필수', 'CLICK BELOW')}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="font-size:0.94rem; color:#475569; margin-top:4px; margin-bottom:8px;">
                💡 {tr('위 검색창에 연구 주제를 입력하신 뒤 아래 파란색 <b>[👉 1단계 완료: 학술 검색식 자동 변환 및 확정하기]</b> 버튼을 클릭하시거나, 아래쪽 <b>[예시 버튼]</b>을 클릭하시면 1단계가 즉시 완료됩니다.', 'Type your research topic above and click the blue <b>[👉 Confirm Step 1]</b> button below, or click an <b>[Example Topic]</b> button.')}
            </div>
            """, unsafe_allow_html=True)

        s1_act_c1, s1_act_c2 = st.columns([3.4, 1.0], gap="small")
        with s1_act_c1:
            st.button(
                tr("👉 여기를 눌러 1단계 완료하기: 자연어 ➔ 최적 학술 검색식 자동 변환 및 확정 (Click to Confirm Step 1)", "👉 Click Here to Complete Step 1: Auto-Convert & Confirm Search Formula"),
                type="primary",
                on_click=cb_auto_convert_and_confirm_step1,
                use_container_width=True
            )
        with s1_act_c2:
            st.button(
                tr("🗑️ 검색창 비우기", "🗑️ Clear Input"),
                on_click=cb_clear_kw,
                use_container_width=True
            )
    else:
        # STEP 01 IS CONFIRMED! The pulsing primary button has disappeared and transformed into this Confirmed Banner!
        orig_note = (
            f"<br><span style='font-size:0.91rem; font-weight:600; color:#166534;'>• {tr('입력하셨던 자연어 원문', 'Original Question')}: \"{st.session_state.last_nl_input}\"</span>"
            if (st.session_state.last_nl_input and st.session_state.last_nl_input != current_kw_text) else ""
        )
        st.markdown(f"""
        <div class="cta-confirmed-bar">
            <div>
                ✅ <b>{tr('[1단계 확정 완료!] 학술 검색식이 성공적으로 적용되었습니다:', '[Step 1 Confirmed!] Active Academic Search Formula:')}</b>
                <code style="font-size:1.03rem; font-weight:800; color:#14532D; background:#FFFFFF; border:1.5px solid #86EFAC; padding:3px 10px; border-radius:7px; margin-left:6px;">{current_kw_text}</code>
                {orig_note}
            </div>
            <span class="cta-confirmed-pill">⬇️ {tr('이제 아래 2단계로 이동하세요', 'PROCEED TO STEP 2 BELOW')}</span>
        </div>
        """, unsafe_allow_html=True)

        s1_edit_c1, s1_edit_c2 = st.columns([1, 1], gap="small")
        with s1_edit_c1:
            st.button(
                tr("✏️ 검색식 다시 다듬기 / 재변환 모드 열기", "✏️ Edit or Re-convert Formula"),
                on_click=cb_unconfirm_step1,
                use_container_width=True
            )
        with s1_edit_c2:
            st.button(
                tr("🗑️ 검색창 비우고 처음부터 다시 입력하기", "🗑️ Clear & Enter New Topic"),
                on_click=cb_clear_kw,
                use_container_width=True
            )

    # Example Topic Buttons (Placed prominently so first-time users can test with 1 click!)
    st.markdown(f"<div style='font-size:0.96rem; font-weight:800; color:#0F172A; margin-top:12px; margin-bottom:6px;'>💡 {tr('원클릭 연구 주제 예시 (아무 버튼이나 클릭하면 최적 검색식으로 자동 변환되어 1단계가 즉시 완료됩니다!):', 'One-Click Example Topics (Click any button to auto-convert and immediately complete Step 1!):')}</div>", unsafe_allow_html=True)
    ex_c1, ex_c2 = st.columns(2, gap="small")
    with ex_c1:
        st.button(
            tr("💬 [한글 자연어 예시] 뇌졸중 환자의 연하장애와 흡인성 폐렴을 머신러닝으로 예측하는 연구", "💬 [Natural Language] How does machine learning predict aspiration pneumonia in stroke dysphagia?"),
            on_click=set_example_query,
            args=("뇌졸중 환자의 연하장애와 흡인성 폐렴을 머신러닝으로 예측하는 연구",),
            use_container_width=True
        )
        st.button(
            tr("🔬 [암 면역치료 수식 예시] 암 면역관문억제제 및 CAR-T 세포치료 (\"immunotherapy\" (PD-1 OR CAR-T) cancer)", "🔬 [Oncology Formula] Cancer Immunotherapy (\"immunotherapy\" (PD-1 OR CAR-T) cancer)"),
            on_click=set_example_query,
            args=('"immunotherapy" (PD-1 OR CAR-T) cancer',),
            use_container_width=True
        )
    with ex_c2:
        st.button(
            tr("💬 [영어 자연어 예시] What is the role of large language models in clinical decision support?", "💬 [Natural Language] What is the role of large language models in clinical decision support?"),
            on_click=set_example_query,
            args=("What is the role of large language models in clinical decision support?",),
            use_container_width=True
        )
        st.button(
            tr("🧠 [신경재활 수식 예시] 비침습 뇌자극 뇌졸중 재활 ((tDCS OR rTMS) stroke rehabilitation -animal)", "🧠 [Neuro-Rehab Formula] Brain Stimulation ((tDCS OR rTMS) stroke rehabilitation -animal)"),
            on_click=set_example_query,
            args=('(tDCS OR rTMS) stroke rehabilitation -animal',),
            use_container_width=True
        )

    # 🔤 Searchable No-Typo Academic Keyword Autocomplete Catalog
    ac_dict_title = tr(
        "🔤 오타 걱정 없는 학술 키워드 자동완성 사전 (클릭 후 1~2글자만 입력해도 정확한 한·영 학술 용어가 자동완성됩니다!)",
        "🔤 Typo-Free Academic Keyword Autocomplete Dictionary (Type 1–2 letters in the box below to filter & add exact terms!)"
    )
    st.markdown(f"<div style='font-size:0.95rem; font-weight:800; color:#1E3A8A; margin-top:10px; margin-bottom:5px;'>{ac_dict_title}</div>", unsafe_allow_html=True)
    ac_sel_c1, ac_sel_c2, ac_sel_c3 = st.columns([5.2, 2.6, 2.2], gap="small")
    with ac_sel_c1:
        st.selectbox(
            "Academic Autocomplete Catalog",
            options=list(range(len(ACADEMIC_AUTOCOMPLETE_CATALOG))),
            key="ac_catalog_select",
            format_func=lambda idx: (
                f"[{ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['cat']}] {ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['ko']} ➔ {ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['en']}"
                if st.session_state.ui_lang == "KO_EN" else
                f"[{ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['cat']}] {ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['en']} ({ACADEMIC_AUTOCOMPLETE_CATALOG[idx]['ko']})"
            ),
            label_visibility="collapsed"
        )
    with ac_sel_c2:
        st.button(
            tr("➕ 선택 키워드 검색식에 추가 (AND)", "➕ Append Selected Keyword (AND)"),
            key="btn_ac_cat_and",
            on_click=cb_add_from_catalog_dropdown,
            args=("AND",),
            use_container_width=True
        )
    with ac_sel_c3:
        st.button(
            tr("🔄 선택 키워드로 새로 검색", "🔄 Replace with Selected"),
            key="btn_ac_cat_replace",
            on_click=cb_add_from_catalog_dropdown,
            args=("REPLACE",),
            use_container_width=True
        )

    # 🧩 Interactive Query Builder + 4 Essential Syntax Rules Side-by-Side / Stacked cleanly
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-radius:14px; padding:16px 18px; margin-top:10px;">
        <div style="font-weight:800; font-size:1.02rem; color:#0F172A; margin-bottom:4px;">
            🧩 {tr('초보자용 검색어 자동 조립기 & 자주 쓰는 조건 원클릭 추가 (오타 자동 교정 지원 · 버튼만 누르면 결합됩니다)', 'Interactive Query Builder & One-Click Filter Chips (With Auto Typo-Correction)')}
        </div>
        <div style="font-size:0.93rem; color:#334155; margin-bottom:10px; line-height:1.55;">
            {tr('아래 입력칸에 <b>추가하거나 제외할 단어(한글·영어 모두 가능, 철자 오타 자동 교정)</b>를 적고 조건 버튼을 누르면 위 검색창에 자동으로 조립되며 1단계가 즉시 확정됩니다.',
                'Type a word or phrase below (with automatic typo correction) and click any operator button to format and confirm Step 1.')}
        </div>
    """, unsafe_allow_html=True)

    st.text_input(
        "Builder Term Input",
        key="builder_term_input",
        placeholder=tr("👉 조립할 단어를 입력하세요 (예: deep learning, 연하장애, 재활, animal) — 입력 후 아래 4개 버튼 중 하나 클릭", "👉 Type a word or phrase to add or exclude (e.g., deep learning, rehabilitation, animal)"),
        label_visibility="collapsed"
    )

    b_btn1, b_btn2, b_btn3, b_btn4 = st.columns(4, gap="small")
    with b_btn1:
        st.button(
            tr("➕ 필수 포함 (AND) 추가", "➕ Must Include (AND)"),
            on_click=cb_smart_builder_add,
            args=("AND",),
            use_container_width=True
        )
    with b_btn2:
        st.button(
            tr("🔄 동의어로 묶기 (OR)", "🔄 Group Synonym (OR)"),
            on_click=cb_smart_builder_add,
            args=("OR",),
            use_container_width=True
        )
    with b_btn3:
        st.button(
            tr('🎯 정확한 구문 (" ") 추가', '🎯 Exact Phrase (" ")'),
            on_click=cb_smart_builder_add,
            args=("PHRASE",),
            use_container_width=True
        )
    with b_btn4:
        st.button(
            tr("🚫 이 단어 제외하기 (-)", "🚫 Exclude Term (-)"),
            on_click=cb_smart_builder_add,
            args=("EXCLUDE",),
            use_container_width=True
        )

    chip_r1_c1, chip_r1_c2 = st.columns(2, gap="small")
    with chip_r1_c1:
        st.button(
            tr("🚫 동물실험 논문 제외 추가 (-animal -mice -rat)", "🚫 Exclude Animal Studies (-animal -mice -rat)"),
            on_click=append_preset_snippet,
            args=("-animal -mice -rat", "동물실험 제외", "Exclude animal studies"),
            use_container_width=True
        )
        st.button(
            tr('🚫 단순 증례보고 제외 추가 (-"case report")', '🚫 Exclude Case Reports (-"case report")'),
            on_click=append_preset_snippet,
            args=('-"case report"', "증례보고 제외", "Exclude case reports"),
            use_container_width=True
        )
    with chip_r1_c2:
        st.button(
            tr("🚫 소아·아동 연구 제외 추가 (-pediatric -children)", "🚫 Exclude Pediatric Studies (-pediatric -children)"),
            on_click=append_preset_snippet,
            args=("-pediatric -children", "소아 연구 제외", "Exclude pediatric studies"),
            use_container_width=True
        )
        st.button(
            tr('🤖 인공지능·머신러닝 조건 결합 (AI OR ML)', '🤖 Combine AI / Machine Learning Filter'),
            on_click=append_preset_snippet,
            args=('("machine learning" OR "deep learning" OR "artificial intelligence")', "AI·딥러닝 결합", "AI/ML filter"),
            use_container_width=True
        )

    st.markdown(f"""
        <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; margin-top:10px; padding-top:10px; border-top:1px dashed #CBD5E1; font-size:0.88rem;">
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px;">
                <b>① {tr('띄어쓰기 (AND)', 'Space (AND)')}</b><br><span class="syntax-code">stroke dysphagia</span> {tr('모두 포함', 'Both terms')}
            </div>
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px;">
                <b>② {tr('대문자 OR (동의어)', 'Capital OR')}</b><br><span class="syntax-code">(A OR B)</span> {tr('하나라도 포함', 'Either term')}
            </div>
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px;">
                <b>③ {tr('"큰따옴표" (구문)', '"Quotes"')}</b><br><span class="syntax-code">"deep learning"</span> {tr('연속된 구문', 'Exact phrase')}
            </div>
            <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 10px;">
                <b>④ {tr('-마이너스 (제외)', '-Minus (NOT)')}</b><br><span class="syntax-code">-animal</span> {tr('해당 단어 제외', 'Excludes word')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 🧭 STEP 02: Exploration Algorithm, Clear Depth Guide & 8 Document Types
# ==========================================
step1_is_ready = bool(st.session_state.step1_confirmed and (st.session_state.get("kw_input", "").strip() or st.session_state.cart))
step2_years_ok = (st.session_state.start_yr_input <= st.session_state.end_yr_input)
if not step2_years_ok:
    st.session_state.step2_confirmed = False

if not step1_is_ready:
    s2_banner_state = "todo"
    s2_banner_text = tr("1단계 완료 후 진행해 주세요", "Complete Step 1 First")
elif st.session_state.step2_confirmed and step2_years_ok:
    s2_banner_state = "done"
    s2_banner_text = tr("2단계 설정 확정 완료", "Step 2 Confirmed")
else:
    s2_banner_state = "active"
    s2_banner_text = tr("필수 진행: 옵션 확인 후 하단 완료 버튼을 눌러주세요", "Action Required: Click Confirm Step 2 Below")

render_step_banner(
    step_class="step2",
    step_num_text="STEP 02 / 04",
    title_text=tr("🧭 2단계: 논문 탐색 알고리즘 · 문헌 유형(8종) · 출판 연도 확정", "🧭 STEP 02: Select Algorithm, Document Type & Timeframe"),
    state=s2_banner_state,
    status_text=s2_banner_text,
    anchor_id="step-02-anchor"
)

with st.container(border=True):
    if st.session_state.get("step_order_alert") and st.session_state.step_order_alert.get("step") == 2:
        alert_msg_s2 = st.session_state.step_order_alert.get("msg", "")
        st.markdown(f"""
        <div class="cta-attention-amber" style="margin-bottom:12px;">
            <div>
                <span class="bounce-icon">🚨</span> <b>{alert_msg_s2}</b><br>
                <span style="font-size:0.92rem; color:#78350F;">{tr('아래 2단계 탐색 알고리즘과 연도·문헌 유형을 확인하신 뒤 하단 파란색 <b>[2단계 완료]</b> 버튼을 먼저 눌러주세요.', 'Please review your Step 2 options below and click the blue [Confirm Step 2] button first.')}</span>
            </div>
            <span class="cta-amber-badge">📍 {tr('2단계 순서 진행 필수', 'CONFIRM STEP 2 FIRST')}</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.step_order_alert = None

    if not step1_is_ready:
        st.markdown(f"""
        <div class="step-prereq-alert">
            🚨 <b>{tr('[이전 단계 미완료 안내] 아직 위쪽 1단계(STEP 01)의 연구 주제 확정이 완료되지 않았습니다.', '[Prerequisite Notice] STEP 01 (Research Topic) has not been confirmed yet.')}</b><br>
            {tr('모든 단계가 순서대로 완벽하게 진행되도록 위 <b>1단계</b>에서 주제를 입력하고 <b>[1단계 완료]</b> 버튼을 먼저 눌러주세요. 아래 버튼을 누르면 1단계로 즉시 스크롤됩니다.', 'Please complete Step 1 first. Click the button below to jump directly to Step 1.')}
        </div>
        """, unsafe_allow_html=True)
        st.button(
            tr("⬆️ 1단계(연구 주제 입력 및 확정)로 바로 이동하기", "⬆️ Jump Directly to Step 1 (Research Topic)"),
            key="jump_s2_to_s1",
            on_click=cb_jump_to_step,
            args=(1,),
            use_container_width=True
        )

    # Full-width Algorithm Selection for clean, unbroken Korean sentences
    st.markdown(f"#### 🧭 {tr('1) 핵심 논문 탐색 알고리즘 선택 (Discovery Algorithm)', '1) Select Discovery Algorithm')}")
    search_mode = st.radio(
        "Exploration Mode",
        options=[
            "⚡ Ultra-fast Scan (Trend Analysis)",
            "🧠 Deep Network (Foundational Roots)"
        ],
        on_change=notify_step2_change,
        args=("탐색 알고리즘", "Discovery Algorithm"),
        format_func=lambda x: (
            tr("⚡ 빠른 트렌드 스캔 (Ultra-fast Scan) — 입력한 검색어가 제목이나 초록에 포함된 대표·최신 인기 논문을 직접 추출합니다.", "⚡ Ultra-fast Scan (Trend Analysis) — Direct retrieval of top-cited or trending papers matching your query.")
            if "Ultra-fast" in x else
            tr("🧠 심층 뿌리 논문 역추적 (Deep Network) — 검색된 논문들의 참고문헌을 역추적하여 이 분야 연구자들이 가장 많이 공통 인용한 원조(Root) 논문을 발굴합니다.", "🧠 Deep Network (Foundational Roots) — Trace cited references to uncover foundational root papers.")
        ),
        label_visibility="collapsed"
    )

    if "Ultra-fast" in search_mode:
        st.markdown(
            f"<div class='guide-box'><span class='guide-title'>⚡ {tr('빠른 트렌드 스캔 (Ultra-fast Scan) 안내', 'About Ultra-fast Scan')}</span>"
            f"{tr('검색어가 제목이나 초록에 직접 포함된 논문들 가운데 <b>가장 많이 인용된 대표 논문이나 최근 급부상하는 트렌드 논문</b>을 약 5초 이내에 빠르게 추출합니다. 아래에서 정렬 우선순위를 선택하세요.', 'Directly retrieves top papers matching your query within seconds. Choose your preferred primary ranking criterion below.')}</div>",
            unsafe_allow_html=True
        )
        sort_by = st.selectbox(
            tr("📊 논문 정렬 및 추출 우선순위 기준 (Primary Sort Metric)", "📊 Primary Ranking & Sort Metric"),
            options=["CITATIONS", "VELOCITY", "FWCI", "YEAR_DESC"],
            on_change=notify_step2_change,
            args=("논문 정렬 기준", "Primary Sort Metric"),
            format_func=lambda x: {
                "CITATIONS": tr("🏆 총 피인용 횟수 순 (Total Citations — 가장 검증된 클래식 대표 논문 우선)", "🏆 Total Citations (Most cited classic papers first)"),
                "VELOCITY": tr("🔥 연간 인용 속도 순 (Citation Velocity [회/년] — 최근 급부상하는 핫 트렌드 논문 우선)", "🔥 Citation Velocity [Cites/Yr] (Fastest-growing recent papers first)"),
                "FWCI": tr("⚖️ 학문분야 보정 영향력 순 (FWCI — 동일 연도·동일 분야 세계 평균 대비 영향력이 높은 논문 우선)", "⚖️ Field-Weighted Citation Impact (FWCI — Highest normalized impact)"),
                "YEAR_DESC": tr("🆕 최신 출판 연도 순 (Newest Year First — 가장 최근에 발표된 최신 연구 동향 우선)", "🆕 Newest Publication Date (Most recent publications first)")
            }[x]
        )
        deep_max_phases = 3
        restrict_root_years = False
    else:
        st.markdown(
            f"<div class='guide-box'><span class='guide-title'>🧠 {tr('심층 뿌리 논문 역추적 (Deep Network) 안내', 'About Deep Root Network Tracing')}</span>"
            f"{tr('검색어로 먼저 찾은 논문들의 <b>맨 뒤 참고문헌(References) 목록 수만 건을 역추적</b>하여, 이 분야 연구자들이 공통적으로 가장 많이 인용한 <b>역사적 원조(Root) 논문(공통 인용 빈도 1순위)</b>을 찾아냅니다.', 'Scans tens of thousands of references cited by your matched literature to isolate foundational root papers ranked by In-Network Co-citations (Network Hits).')}</div>",
            unsafe_allow_html=True
        )
        sort_by = "DEFAULT"

        st.markdown(f"**🔍 {tr('참고문헌 역추적 탐색 범위 선택 (얼마나 꼼꼼하게 조사할까요?)', 'Select Reference Tracing Depth')}**")
        deep_max_phases = st.radio(
            "Seed Literature Scan Depth",
            options=[1, 3, 5, 10],
            index=1,
            on_change=notify_step2_change,
            args=("참고문헌 역추적 탐색 범위", "Reference Tracing Depth"),
            format_func=lambda v: {
                1: tr("⚡ 1단계: 빠른 핵심 조사 (상위 100편의 참고문헌 약 4,000건 스캔 · 약 8초 소요) — 주제를 처음 탐색할 때 추천", "⚡ Level 1: Fast Core Scan (Top 100 papers / approx. 4,000 refs · 8s) — Quick overview"),
                3: tr("⭐ 2단계: 표준 균형 조사 [가장 추천] (상위 300편의 참고문헌 약 12,000건 스캔 · 약 20초 소요) — 일반 연구 논문 작성 시 최적", "⭐ Level 2: Standard Balanced [Recommended] (Top 300 papers / approx. 12,000 refs · 20s) — Best balance"),
                5: tr("🔬 3단계: 정밀 심층 조사 (상위 500편의 참고문헌 약 20,000건 스캔 · 약 35초 소요) — 체계적 문헌고찰 및 학위논문 추천", "🔬 Level 3: Deep Precision Scan (Top 500 papers / approx. 20,000 refs · 35s) — Ideal for systematic reviews"),
                10: tr("🌐 4단계: 전수 최대 조사 (최대 1,000편의 참고문헌 약 40,000건 전수 스캔 · 약 60초 소요) — 하나도 빠짐없이 모든 뿌리 논문을 찾을 때", "🌐 Level 4: Exhaustive Full Scan (Up to 1,000 papers / approx. 40,000 refs · 60s) — Exhaustive trace")
            }[v],
            label_visibility="collapsed"
        )

        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        restrict_root_years = st.toggle(
            tr("🔒 뿌리(Root) 논문도 아래에 지정한 출판 연도 범위 내로만 제한하기 (기본값: 꺼짐 권장)", "🔒 Restrict Root Papers to Selected Publication Year Range (Default: OFF recommended)"),
            value=False,
            on_change=notify_step2_change,
            args=("뿌리 논문 연도 제한 옵션", "Root Year Restriction")
        )
        if restrict_root_years:
            st.markdown(
                f"<div style='background:#FEF3C7; border:1px solid #FDE68A; border-radius:8px; padding:9px 14px; font-size:0.93rem; color:#92400E; margin-bottom:6px;'>"
                f"🔒 <b>{tr('현재 상태: 뿌리 논문 연도 제한 켜짐', 'Root Year Restriction ON')}</b> — {tr('아래에서 지정한 시작 연도 이전에 발표된 오래된 고전 뿌리 논문은 결과에서 제외됩니다.', 'Older historical root papers published before your Start Year will be excluded.')}"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:9px 14px; font-size:0.93rem; color:#065F46; margin-bottom:6px;'>"
                f"🔓 <b>{tr('현재 상태: 역사적 고전 뿌리 논문 전체 발굴 (권장 설정)', 'Historical Root Discovery Active (Recommended)')}</b> — {tr('출판 연도에 구애받지 않고 1980년대부터 최근까지 이 분야의 토대가 된 모든 뿌리 논문을 발굴합니다.', 'Uncovers foundational root papers across all historical eras without year cutoff.')}"
                f"</div>",
                unsafe_allow_html=True
            )

    # 📘 Beginner-friendly inline guide for Step 2 metrics & document types
    s2_term_hdr = tr(
        "📘 [2단계 용어 쉬운 해설] 총 피인용 · 인용 속도 · FWCI · 공통 인용 · 문헌 유형이 무슨 뜻인가요?",
        "📘 [Step 2 Term Guide] What do Total Citations, Velocity, FWCI, Network Hits, and Document Types mean?"
    )
    with st.expander(s2_term_hdr, expanded=False):
        st.markdown(f"""
        <div style="font-size:0.93rem; color:#1E293B; line-height:1.68;">
            • <b>🏆 {tr('총 피인용 (Total Citations)', 'Total Citations')}:</b> {tr('논문이 출판된 이후 전 세계 다른 논문들로부터 인용된 <b>전체 누적 횟수</b>입니다. 학계에서 가장 검증된 클래식 대표 논문을 찾을 때 유리합니다.', 'Cumulative number of times a paper has been cited globally since publication.')}<br>
            • <b>🔥 {tr('연간 인용 속도 (Citation Velocity [회/년])', 'Citation Velocity [Cites/Yr]')}:</b> {tr('<code>총 피인용 ÷ 경과 연수</code>로 계산됩니다. 출판된 지 1~2년밖에 안 되어 누적 인용은 적더라도 <b>1년에 인용되는 속도가 폭발적인 최신 핫 트렌드 논문</b>을 찾아냅니다.', 'Average citations gained per year since publication; highlights rapidly rising recent papers.')}<br>
            • <b>⚖️ {tr('학문분야 보정 영향력 (FWCI · Field-Weighted Citation Impact)', 'FWCI (Field-Weighted Citation Impact)')}:</b> {tr('출판 연도·학문 분야·논문 유형이 같은 전 세계 논문들의 <b>평균 인용을 1.0배</b>로 놓았을 때의 상대적 영향력입니다. 예를 들어 <b>FWCI 3.0</b>이면 세계 평균보다 <b>3배 더 많이 인용된 최상위 논문</b>입니다.', '1.0x equals the world average for the same year, field, and document type. 3.0x means cited 3 times more than the global average.')}<br>
            • <b>🔗 {tr('공통 인용 (Network Hits · 심층 뿌리 역추적 전용)', 'Network Hits (In-Network Co-Citations)')}:</b> {tr('내가 검색한 최신 논문들이 참고문헌에서 <b>동시에 함께 인용한 횟수</b>입니다. 내 연구 주제의 <b>진짜 기원(Root)이 된 역사적 원전 논문</b>을 가장 정확하게 찾아줍니다.', 'How many papers in your search network cited this foundational paper together.')}<br>
            • <b>📑 {tr('원저(Article) vs 종설(Review) vs 프리프린트(Preprint) vs 오픈 액세스(OA)', 'Article vs Review vs Preprint vs Open Access (OA)')}:</b> {tr('<b>원저(Article)</b>는 새로운 실험·임상 데이터를 분석한 연구 논문, <b>종설(Review)</b>은 기존 논문들을 종합 정리한 문헌고찰 논문, <b>프리프린트</b>는 정식 심사 전 공개 초안, <b>오픈 액세스(OA)</b>는 결제 없이 무료로 전문 PDF를 볼 수 있는 논문입니다.', 'Articles report new data; Reviews synthesize existing literature; Preprints are early drafts; OA provides free full-text PDFs.')}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='margin-top:12px; margin-bottom:14px; border-top:1.5px solid #E2E8F0;'>", unsafe_allow_html=True)

    # Perfectly Height-Balanced 2-Column Layout for Document Type, Timeframe, and Quality Filters
    flt_left, flt_right = st.columns([1, 1], gap="large")

    with flt_left:
        st.markdown(f"#### 📑 {tr('2) 문헌 유형 필터 선택 (8종 카테고리)', '2) Document Type Filter (8 Categories)')}")
        DOC_TYPE_LABELS = {
            "ALL": tr("📚 전체 학술 문헌 통합 (모든 유형 포함)", "📚 All Scholarly Works (Unrestricted)"),
            "ARTICLE_REVIEW": tr("⭐ 학술지 핵심 논문 통합 [추천] (원저 Article + 종설 Review)", "⭐ Journal Articles & Reviews Combined [Recommended]"),
            "ARTICLE": tr("🔬 원저 연구 논문만 (Original Research Articles Only)", "🔬 Original Research Articles Only"),
            "REVIEW": tr("📖 종설 · 체계적 문헌고찰만 (Reviews & Systematic Reviews)", "📖 Reviews & Systematic Reviews Only"),
            "PREPRINT": tr("🚀 최신 프리프린트 논문만 (Preprints: arXiv · medRxiv · bioRxiv)", "🚀 Preprints Only (arXiv, medRxiv, bioRxiv)"),
            "BOOK": tr("📕 학술 단행본 · 북챕터 (Books & Book Chapters)", "📕 Books & Book Chapters Only"),
            "DISSERTATION": tr("🎓 석·박사 학위논문 (Dissertations & Theses)", "🎓 Dissertations & Theses Only"),
            "EDITORIAL_LETTER": tr("✉️ 사설 · 레터 · 코멘터리 (Editorials & Letters)", "✉️ Editorials, Letters & Commentaries")
        }
        doc_type = st.selectbox(
            tr("문헌 유형 선택", "Select Document Type"),
            options=list(DOC_TYPE_LABELS.keys()),
            on_change=notify_step2_change,
            args=("문헌 유형 필터", "Document Type Filter"),
            format_func=lambda k: DOC_TYPE_LABELS[k],
            label_visibility="collapsed"
        )

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        st.markdown(f"#### 🛡️ {tr('3) 수집 논문 수 및 최소 피인용 기준', '3) Extraction Capacity & Citation Cutoff')}")
        top_n = st.slider(
            tr("📊 최종 추출할 최대 논문 수 (기본 150편 권장)", "📊 Maximum Papers to Extract (Default: 150)"),
            min_value=50,
            max_value=1000,
            value=150,
            step=50,
            on_change=notify_step2_change,
            args=("최대 추출 논문 수", "Max Papers to Extract")
        )

        min_citations = st.number_input(
            tr("⭐ 최소 피인용 횟수 기준 (지정한 횟수 이상 인용된 논문만 추출)", "⭐ Minimum Citations Cutoff"),
            min_value=0,
            max_value=50000,
            value=0,
            step=10,
            on_change=notify_step2_change,
            args=("최소 피인용 횟수 기준", "Minimum Citations Cutoff")
        )

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        st.markdown(f"**🔓 {tr('원문 PDF 및 초록 필수 포함 옵션', 'Full-Text PDF & Abstract Gates')}**")
        oa_only = st.toggle(
            tr("🔓 무료 전문 PDF(Open Access) 보유 논문만 추출하기", "🔓 Open Access Full-Text PDF Only"),
            value=False,
            on_change=notify_step2_change,
            args=("무료 전문 PDF(OA) 필터", "Open Access PDF Filter")
        )
        require_abstract = st.toggle(
            tr("📝 초록(Abstract) 본문이 수록된 논문만 추출하기", "📝 Require Indexed Abstract Text"),
            value=False,
            on_change=notify_step2_change,
            args=("초록(Abstract) 필수 필터", "Require Abstract Filter")
        )

    with flt_right:
        current_year_val = get_current_year()
        yr_hdr_txt = tr(
            f"4) 출판 연도 범위 설정 (기본값: {current_year_val-10}년 – {current_year_val}년)",
            f"4) Publication Timeframe (Default: {current_year_val-10}–{current_year_val})"
        )
        st.markdown(f"#### 📅 {yr_hdr_txt}")

        yp_r1_c1, yp_r1_c2 = st.columns(2, gap="small")
        with yp_r1_c1:
            st.button(tr(f"📅 최근 3년 ({current_year_val-3}–{current_year_val}년)", f"📅 Last 3 Years ({current_year_val-3}–{current_year_val})"), on_click=set_year_preset, args=(3,), use_container_width=True)
            st.button(tr(f"📅 최근 10년 [기본] ({current_year_val-10}–{current_year_val}년)", f"📅 Last 10 Years [Default] ({current_year_val-10}–{current_year_val})"), on_click=set_year_preset, args=(10,), use_container_width=True)
        with yp_r1_c2:
            st.button(tr(f"📅 최근 5년 ({current_year_val-5}–{current_year_val}년)", f"📅 Last 5 Years ({current_year_val-5}–{current_year_val})"), on_click=set_year_preset, args=(5,), use_container_width=True)
            st.button(tr(f"📅 전체 기간 (1980–{current_year_val}년)", f"📅 All Years (1980–{current_year_val})"), on_click=set_year_preset, args=(None,), use_container_width=True)

        cy1, cy2 = st.columns(2, gap="small")
        with cy1:
            start_year = st.number_input(
                tr("시작 연도 (Start Year)", "Start Year"),
                min_value=1950,
                max_value=current_year_val,
                key="start_yr_input",
                on_change=notify_step2_change,
                args=("시작 연도", "Start Year"),
                step=1
            )
        with cy2:
            end_year = st.number_input(
                tr("종료 연도 (End Year)", "End Year"),
                min_value=1950,
                max_value=current_year_val,
                key="end_yr_input",
                on_change=notify_step2_change,
                args=("종료 연도", "End Year"),
                step=1
            )

        if start_year > end_year:
            st.error(tr("🚨 시작 연도는 종료 연도보다 작거나 같아야 합니다.", "🚨 Start Year must precede or equal End Year."))

        # Live Step 2 Configuration Summary Box to eliminate any bottom empty space in the right column!
        mode_summary_txt = tr("⚡ 빠른 트렌드 스캔" if "Ultra-fast" in search_mode else f"🧠 심층 뿌리 역추적 ({deep_max_phases*100}편 참고문헌 스캔)", "⚡ Trend Scan" if "Ultra-fast" in search_mode else f"🧠 Deep Root Network ({deep_max_phases*100} seeds)")
        span_yrs = max(1, end_year - start_year + 1)
        min_cite_summary_txt = tr(f"최소 {min_citations}회 인용", f"Min {min_citations} cites")
        oa_summary_txt = tr("무료 PDF 전용" if oa_only else "모든 원문 허용", "OA Only" if oa_only else "All Access")
        abs_summary_txt = tr("초록 필수" if require_abstract else "초록 선택", "Abstract Req" if require_abstract else "Abstract Opt")
        st.markdown(f"""
        <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-left:5px solid #0D9488; border-radius:12px; padding:14px 16px; margin-top:10px; font-size:0.93rem; color:#1E293B; line-height:1.62;">
            <div style="font-weight:800; color:#0F172A; font-size:0.97rem; margin-bottom:6px;">
                📋 {tr('현재 2단계 탐색 설정 실시간 요약', 'Live Step 2 Configuration Summary')}
            </div>
            • <b>{tr('선택된 탐색 방식', 'Algorithm')}:</b> {mode_summary_txt}<br>
            • <b>{tr('출판 연도 범위', 'Timeframe')}:</b> <span style="color:#0F766E; font-weight:800;">{start_year}년 – {end_year}년 ({span_yrs}개년도)</span><br>
            • <b>{tr('문헌 유형 및 수집량', 'Type & Capacity')}:</b> {DOC_TYPE_LABELS[doc_type]} · <b>최대 {top_n}편</b><br>
            • <b>{tr('품질 조건', 'Quality Gates')}:</b> {min_cite_summary_txt} · {oa_summary_txt} · {abs_summary_txt}
        </div>
        """, unsafe_allow_html=True)

    # Dynamic Action Area for STEP 02:
    # - When NOT confirmed: Shows a pulsing CTA prompt + glowing Primary button!
    # - When CONFIRMED: The pulsing button DISAPPEARS and transforms into an emerald Confirmed Banner!
    if not (st.session_state.step2_confirmed and (start_year <= end_year)):
        s2_cta_txt = tr(
            f"[2단계 완료 클릭 필수!] 위 탐색 알고리즘과 출판 연도({start_year}–{end_year}년) 설정을 확인하셨다면, 다음 3단계로 넘어가기 위해 바로 아래 반짝이는 파란색 [2단계 완료] 버튼을 꼭 클릭해 주세요!",
            f"[Action Required!] Review your algorithm and timeframe ({start_year}–{end_year}) above, then click the glowing blue [Confirm Step 2] button below to proceed to Step 3!"
        )
        st.markdown(f"""
        <div class="cta-attention-box">
            <div>
                <span class="bounce-icon">👇</span> <b>{s2_cta_txt}</b>
            </div>
            <span class="cta-attention-badge">👉 {tr('아래 버튼 클릭 필수', 'CLICK BELOW')}</span>
        </div>
        """, unsafe_allow_html=True)

        st.button(
            tr("👉 여기를 눌러 2단계 설정 완료하기: 현재 탐색 알고리즘 · 문헌 유형 · 출판 연도로 확정 (Click to Confirm Step 2)", "👉 Click Here to Complete Step 2: Confirm Algorithm, Document Type & Timeframe"),
            type="primary",
            on_click=cb_confirm_step2,
            use_container_width=True
        )
    else:
        mode_short_footer = "빠른 트렌드 스캔" if "Ultra-fast" in search_mode else f"심층 뿌리 논문 역추적 (상위 {deep_max_phases*100}편 참고문헌 스캔)"
        s2_done_txt = tr(
            f"[2단계 확정 완료!] [{mode_short_footer} · {start_year}–{end_year}년 · 최대 {top_n}편] 설정이 확정되었습니다!",
            f"[Step 2 Confirmed!] [{start_year}–{end_year} · Max {top_n} papers] locked in!"
        )
        st.markdown(f"""
        <div class="cta-confirmed-bar">
            <div>
                ✅ <b>{s2_done_txt}</b>
                <span style="font-size:0.9rem; font-weight:500; color:#166534; margin-left:6px;">{tr('(위 옵션을 변경하시면 완료 버튼이 자동으로 다시 나타납니다)', '(Changing any option above will re-open confirmation)')}</span>
            </div>
            <span class="cta-confirmed-pill">⬇️ {tr('이제 아래 3단계로 이동하세요', 'PROCEED TO STEP 3 BELOW')}</span>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 📚 STEP 03: Target Journal Scope
# ==========================================
step3_selection_valid = (st.session_state.scope_mode == "GLOBAL" and not st.session_state.cart) or (len(st.session_state.cart) > 0)
if not step3_selection_valid:
    st.session_state.step3_confirmed = False

if not (step1_is_ready and st.session_state.step2_confirmed):
    s3_banner_state = "todo"
    s3_banner_text = tr("1·2단계 완료 후 진행해 주세요", "Complete Steps 1 & 2 First")
elif st.session_state.step3_confirmed and step3_selection_valid:
    s3_banner_state = "done"
    s3_banner_text = tr("3단계 학술지 범위 확정 완료", "Step 3 Confirmed")
else:
    s3_banner_state = "active"
    s3_banner_text = tr("필수 진행: 범위 확인 후 하단 완료 버튼을 눌러주세요", "Action Required: Click Confirm Step 3 Below")

render_step_banner(
    step_class="step3",
    step_num_text="STEP 03 / 04",
    title_text=tr("🏛️ 3단계: 검색 대상 학술지 범위 지정 및 확정", "🏛️ STEP 03: Select & Confirm Target Journal Scope"),
    state=s3_banner_state,
    status_text=s3_banner_text,
    anchor_id="step-03-anchor"
)

with st.container(border=True):
    if st.session_state.get("step_order_alert") and st.session_state.step_order_alert.get("step") == 3:
        alert_msg_s3 = st.session_state.step_order_alert.get("msg", "")
        st.markdown(f"""
        <div class="cta-attention-amber" style="margin-bottom:12px;">
            <div>
                <span class="bounce-icon">🚨</span> <b>{alert_msg_s3}</b><br>
                <span style="font-size:0.92rem; color:#78350F;">{tr('아래 3단계 검색 대상 학술지 범위를 확인하신 뒤 하단 파란색 <b>[3단계 완료]</b> 버튼을 눌러주세요.', 'Please review your Step 3 journal scope below and click the blue [Confirm Step 3] button.')}</span>
            </div>
            <span class="cta-amber-badge">📍 {tr('3단계 순서 진행 필수', 'CONFIRM STEP 3 FIRST')}</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.step_order_alert = None

    if not (step1_is_ready and st.session_state.step2_confirmed):
        missing_prev = []
        if not step1_is_ready:
            missing_prev.append("1단계(연구 주제 확정)")
        if not st.session_state.step2_confirmed:
            missing_prev.append("2단계(탐색 방식·필터 확정)")
        missing_prev_joined = ", ".join(missing_prev)
        prereq_s3_title = tr(
            f"[이전 단계 미완료 안내] 위쪽 {missing_prev_joined} 버튼이 아직 클릭되지 않았습니다.",
            "[Prerequisite Notice] Previous steps have not been confirmed yet."
        )
        st.markdown(f"""
        <div class="step-prereq-alert">
            🚨 <b>{prereq_s3_title}</b><br>
            {tr('모든 단계가 순서대로 진행되도록 위 단계의 완료 버튼을 먼저 눌러주세요. 아래 바로가기 버튼을 누르면 미완료 단계로 즉시 스크롤됩니다.', 'Please confirm the earlier steps in order. Click the jump button(s) below to scroll directly to the unconfirmed step.')}
        </div>
        """, unsafe_allow_html=True)
        jmp_cols_s3 = st.columns(2 if (not step1_is_ready and not st.session_state.step2_confirmed) else 1, gap="small")
        j_idx = 0
        if not step1_is_ready:
            with jmp_cols_s3[j_idx]:
                st.button(
                    tr("⬆️ 1단계(연구 주제 입력·확정)로 바로 이동하기", "⬆️ Jump Directly to Step 1 (Research Topic)"),
                    key="jump_s3_to_s1",
                    on_click=cb_jump_to_step,
                    args=(1,),
                    use_container_width=True
                )
            j_idx += 1
        if not st.session_state.step2_confirmed:
            with jmp_cols_s3[j_idx]:
                st.button(
                    tr("⬆️ 2단계(탐색 방식·필터 확정)로 바로 이동하기", "⬆️ Jump Directly to Step 2 (Algorithm & Filters)"),
                    key="jump_s3_to_s2",
                    on_click=cb_jump_to_step,
                    args=(2,),
                    use_container_width=True
                )

    scope_choice = st.radio(
        "Journal Scope Selection",
        options=["GLOBAL", "TARGETED"],
        on_change=notify_step3_change,
        format_func=lambda x: (
            tr("🌍 전 세계 모든 학술지 통합 검색 [기본 추천] — 특정 저널로 제한하지 않고 2억 5천만 편 전체 데이터베이스에서 탐색합니다.", "🌍 Search All Global Journals [Recommended] — Scan across all 250M+ global scholarly works without venue restrictions.")
            if x == "GLOBAL" else
            tr(f"🎯 특정 학술지(저널)만 지정하여 검색 (Targeted Journals) — 내가 선택한 학술지(현재 {len(st.session_state.cart)}개 선택됨) 내의 논문만 추출합니다.", f"🎯 Filter by Specific Target Journals ({len(st.session_state.cart)} journal(s) selected)")
        ),
        index=0 if (st.session_state.scope_mode == "GLOBAL" and not st.session_state.cart) else 1,
        label_visibility="collapsed"
    )
    st.session_state.scope_mode = scope_choice

    if scope_choice == "GLOBAL" and not st.session_state.cart:
        # Rich 3-Column Global Coverage Cards so STEP 03 has zero dead space and clear value!
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-top:8px; margin-bottom:6px;">
            <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-top:4px solid #4F46E5; border-radius:12px; padding:12px 15px;">
                <div style="font-weight:800; color:#1E3A8A; font-size:0.95rem; margin-bottom:4px;">🌐 {tr('전 세계 30만 개 학술지 통합 탐색', '300,000+ Global Journals')}</div>
                <div style="font-size:0.89rem; color:#334155; line-height:1.5;">{tr('Nature, Science, NEJM, Lancet, IEEE, Elsevier, Springer 등 모든 출판사의 학술 논문을 빠짐없이 통합 스캔합니다.', 'Simultaneously scans across all major global academic publishers and indexed venues.')}</div>
            </div>
            <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-top:4px solid #0D9488; border-radius:12px; padding:12px 15px;">
                <div style="font-weight:800; color:#0F766E; font-size:0.95rem; margin-bottom:4px;">🔗 {tr('학제 간 융합·뿌리 논문 누락 방지', 'Zero Cross-Disciplinary Blindspots')}</div>
                <div style="font-size:0.89rem; color:#334155; line-height:1.5;">{tr('특정 저널에만 국한되지 않으므로 의학·공학·컴퓨터과학 등 인접 분야 학술지에 실린 핵심 인용 논문까지 모두 포착합니다.', 'Captures interdisciplinary breakthroughs published outside narrow specialty journals.')}</div>
            </div>
            <div style="background:#F8FAFC; border:1.5px solid #CBD5E1; border-top:4px solid #2563EB; border-radius:12px; padding:12px 15px;">
                <div style="font-weight:800; color:#1D4ED8; font-size:0.95rem; margin-bottom:4px;">🎯 {tr('특정 학술지만 골라 보고 싶다면?', 'Need Specific Target Journals?')}</div>
                <div style="font-size:0.89rem; color:#334155; line-height:1.5;">{tr('위 선택지에서 두 번째 <b>[특정 학술지만 지정하여 검색]</b>을 클릭하시면 9개 학문 분야 최정상 저널 프리셋과 검색기가 열립니다.', 'Switch to the second option above to access 9 discipline presets and ISSN search.')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if scope_choice == "GLOBAL" and st.session_state.cart:
        st.warning(tr(
            f"⚠️ 현재 **{len(st.session_state.cart)}개**의 학술지가 선택되어 있습니다. 전 세계 모든 학술지를 대상으로 검색하려면 아래 **[🗑️ 선택 학술지 모두 비우기]** 버튼을 눌러주세요.",
            f"⚠️ You currently have **{len(st.session_state.cart)}** journal(s) selected. Click **[🗑️ Clear Selected Journals]** below to switch to Global Search."
        ))
        st.button(tr("🗑️ 선택 학술지 모두 비우기 (전 세계 통합 검색으로 전환)", "🗑️ Clear Selected Journals"), on_click=cb_empty_cart)

    if scope_choice == "TARGETED" or st.session_state.cart:
        st.markdown("<hr style='margin-top:10px; margin-bottom:12px; border-top:1.5px solid #E2E8F0;'>", unsafe_allow_html=True)

        # 📘 Beginner-friendly explanation of Step 3 journal badges (2Yr-IF, H-index, ISSN)
        s3_j_guide_title = tr(
            "📘 [학술지 카드 3대 용어 쉬운 해설] 2년 인용지수(2Yr-IF) · 학술 영향력(H-index) · ISSN 고유번호란?",
            "📘 [Journal Metrics Guide] What do 2Yr Impact (2Yr-IF), Academic Impact (H-Index), and ISSN mean?"
        )
        s3_j_if_txt = tr(
            "<b>⭐ 2년 인용지수 (2Yr-IF · Impact Factor):</b> 최근 2년간 그 학술지에 실린 논문 1편이 <b>평균 몇 번 인용되었는지</b> 나타내는 파급력 점수입니다. (전공 학술지 평균 2~5점 / 최정상 학술지 10~100점 이상)",
            "<b>⭐ 2Yr Impact (2Yr-IF):</b> Average citations received per paper published in that journal over the last 2 years."
        )
        s3_j_h_txt = tr(
            "<b>📊 학술 영향력 (H-index):</b> 그 학술지에서 <b>H번 이상 인용된 핵심 논문이 최소 H편 이상</b>임을 뜻하는 누적 권위 지표입니다. 숫자가 클수록 오랜 역사와 권위를 가진 대표 저널입니다.",
            "<b>📊 Academic Impact (H-Index):</b> At least H papers in this journal have been cited H or more times, reflecting cumulative historical authority."
        )
        s3_j_issn_txt = tr(
            "<b>🔢 ISSN (국제표준일련번호):</b> 전 세계 학술지마다 부여된 <b>8자리 고유 식별번호</b>(예: <code>0028-0836</code>)입니다. 이름이 비슷한 다른 학술지와 혼동되지 않게 정확히 지정해 줍니다.",
            "<b>🔢 ISSN:</b> 8-digit international unique serial ID (e.g., <code>0028-0836</code>) that identifies a journal without title ambiguity."
        )
        st.markdown(f"""
        <div style="background:#EEF2FF; border:1.5px solid #C7D2FE; border-left:5px solid #4F46E5; border-radius:11px; padding:11px 15px; margin-bottom:12px; font-size:0.9rem; color:#1E293B; line-height:1.58;">
            <div style="font-weight:800; color:#312E81; font-size:0.95rem; margin-bottom:4px;">{s3_j_guide_title}</div>
            • {s3_j_if_txt}<br>
            • {s3_j_h_txt}<br>
            • {s3_j_issn_txt}
        </div>
        """, unsafe_allow_html=True)

        checked_cart_count = sum(1 for k in st.session_state.cart if st.session_state.get(f"cart_chk_{k}", False))
        cart_hdr_txt = tr(
            f"현재 지정된 분석 대상 학술지 목록 ({len(st.session_state.cart)}개 담김 · {checked_cart_count}개 체크됨)",
            f"Selected Target Journals ({len(st.session_state.cart)} total · {checked_cart_count} checked)"
        )
        st.markdown(f"#### 🎯 {cart_hdr_txt}")

        if not st.session_state.cart:
            st.markdown(f"""
            <div class="cta-attention-amber">
                <div>
                    <span class="bounce-icon">👇</span> <b>{tr('[학술지 추가 필수!] 특정 학술지 지정 검색을 선택하셨지만 아직 추가된 학술지가 0개입니다!', '[Action Required!] Targeted mode is selected, but 0 journals have been added!')}</b><br>
                    {tr('바로 아래 <b>① 분야별 권위 학술지 선택·추가</b>, <b>② 30만 개 학술지 이름·분야 검색</b>, <b>③ ISSN 고유번호로 직접 추가</b>에서 원하는 학술지를 개별 또는 여러 개 동시에 선택해 담아주세요.', 'Please add at least 1 journal from the options below, or switch back to Global Search above.')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption(tr(
                "💡 비우고 싶은 학술지 왼쪽 체크박스를 여러 개 선택한 뒤 [🗑️ 체크한 학술지 선택 비우기]를 누르시면 원하는 학술지만 한 번에 제외할 수 있습니다.",
                "💡 Check multiple journals below and click [🗑️ Remove Checked Journals] to batch-remove specific journals, or click [🗑️ Clear All]."
            ))
            cart_act_c1, cart_act_c2, cart_act_c3 = st.columns([3.2, 3.8, 3.0], gap="small")
            with cart_act_c1:
                st.button(
                    tr("☑️ 목록 전체 선택 / 해제", "☑️ Select / Deselect All"),
                    key="btn_toggle_all_cart",
                    on_click=cb_toggle_select_all_cart,
                    use_container_width=True
                )
            with cart_act_c2:
                del_sel_label = tr(
                    f"🗑️ 체크한 학술지 선택 비우기 ({checked_cart_count}개)",
                    f"🗑️ Remove Checked Journals ({checked_cart_count})"
                )
                st.button(
                    del_sel_label,
                    key="btn_remove_selected_cart",
                    type="primary" if checked_cart_count > 0 else "secondary",
                    on_click=cb_remove_selected_cart,
                    use_container_width=True
                )
            with cart_act_c3:
                st.button(
                    tr("🗑️ 선택 목록 전체 비우기", "🗑️ Clear All Journals"),
                    key="btn_empty_all_cart",
                    on_click=cb_empty_cart,
                    use_container_width=True
                )

            for issn, info in list(st.session_state.cart.items()):
                is_cart_checked = bool(st.session_state.get(f"cart_chk_{issn}", False))
                card_bg = "#FEF2F2" if is_cart_checked else "#F8FAFC"
                card_border = "#F87171" if is_cart_checked else "#93C5FD"
                card_left = "#DC2626" if is_cart_checked else "#2563EB"
                jc_chk, jc1, jc2 = st.columns([0.65, 7.35, 2.0])
                with jc_chk:
                    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                    st.checkbox(
                        tr("선택", "Select"),
                        key=f"cart_chk_{issn}",
                        label_visibility="collapsed"
                    )
                jc1.markdown(
                    f"<div style='padding: 11px 15px; background:{card_bg}; border:1.5px solid {card_border}; border-left:5px solid {card_left}; border-radius:12px; margin-bottom:6px;'>"
                    f"{render_journal_html(info, lang=st.session_state.ui_lang)}</div>",
                    unsafe_allow_html=True
                )
                jc2.button(
                    tr("🗑️ 개별 제외", "🗑️ Remove"),
                    key=f"del_{issn}",
                    on_click=cb_remove_journal,
                    args=(issn,),
                    use_container_width=True
                )

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.95rem; font-weight:800; color:#1E3A8A; margin-bottom:6px;'>"
            f"📌 {tr('학술지 추가 방식 선택 (학술지를 클릭하거나 추가해도 현재 보고 계신 탭 화면이 초기화되지 않고 그대로 유지됩니다!)', 'Select Journal Addition Method (Your active tab stays locked even after clicking or adding journals!)')}"
            f"</div>",
            unsafe_allow_html=True
        )
        STEP3_TAB_LABELS = {
            "PRESET": tr("⭐ ① 분야별 권위 학술지 선택·추가", "⭐ ① Premier Discipline Presets"),
            "SEARCH": tr("🔍 ② 30만 개 학술지 이름·분야 검색", "🔍 ② Search 300,000+ Journals"),
            "ISSN": tr("🔢 ③ ISSN 고유번호로 직접 추가", "🔢 ③ Add by Exact ISSN")
        }
        if st.session_state.get("step3_active_tab") not in STEP3_TAB_LABELS:
            st.session_state.step3_active_tab = "PRESET"

        active_step3_tab = st.radio(
            "Step 3 Journal Addition Mode",
            options=["PRESET", "SEARCH", "ISSN"],
            horizontal=True,
            key="step3_active_tab",
            format_func=lambda k: STEP3_TAB_LABELS[k],
            label_visibility="collapsed"
        )

        if active_step3_tab == "PRESET":
            checked_preset_count = sum(
                1 for cat_jrnls in GLOBAL_PRESETS.values()
                for _, issn in cat_jrnls.items()
                if issn not in st.session_state.cart and st.session_state.get(f"pre_chk_{issn}", False)
            )
            st.caption(tr(
                "👆 9개 학문 분야의 최정상급 학술지입니다. 개별 버튼을 눌러 바로 추가하거나, 왼쪽 체크박스를 여러 개 선택한 뒤 [➕ 체크한 권위 학술지 한 번에 추가하기]를 누르세요.",
                "👆 Click any journal button to add immediately, or check multiple boxes and click [➕ Add All Checked Presets] to batch-add."
            ))
            pre_bar_c1, pre_bar_c2 = st.columns([6.2, 3.8], gap="small")
            with pre_bar_c1:
                add_pre_label = tr(
                    f"➕ 체크한 권위 학술지 한 번에 추가하기 ({checked_preset_count}개 선택됨)",
                    f"➕ Add All Checked Preset Journals ({checked_preset_count} selected)"
                )
                st.button(
                    add_pre_label,
                    key="btn_batch_add_presets",
                    type="primary" if checked_preset_count > 0 else "secondary",
                    on_click=cb_add_selected_presets,
                    use_container_width=True
                )
            with pre_bar_c2:
                st.button(
                    tr("☑️ 미추가 권위 학술지 전체 선택 / 해제", "☑️ Select / Deselect All Unadded"),
                    key="btn_toggle_all_presets",
                    on_click=cb_toggle_select_all_presets,
                    use_container_width=True
                )

            cols = st.columns(3)
            for i, (cat, jrnls) in enumerate(GLOBAL_PRESETS.items()):
                with cols[i % 3]:
                    st.markdown(f"<div style='background:#EFF6FF; padding:7px 13px; border-radius:9px; border-left:4px solid #1E40AF; margin-top:6px; margin-bottom:6px; font-size:0.95rem; font-weight:800; color:#0F172A;'>{cat}</div>", unsafe_allow_html=True)
                    unadded_in_cat = [issn for _, issn in jrnls.items() if issn not in st.session_state.cart]
                    if unadded_in_cat:
                        st.button(
                            tr(f"📥 이 분야 학술지 {len(unadded_in_cat)}개 일괄 추가", f"📥 Add All {len(unadded_in_cat)} in Category"),
                            key=f"cat_all_{i}",
                            on_click=cb_add_category_presets,
                            args=(cat,),
                            use_container_width=True
                        )
                    for j, (j_name, issn) in enumerate(jrnls.items()):
                        if issn in st.session_state.cart:
                            st.button(
                                f"✅ {j_name} ({issn}) — {tr('추가됨', 'Selected')}",
                                key=f"p_{i}_{j}_{issn}",
                                disabled=True,
                                use_container_width=True
                            )
                        else:
                            pc_chk, pc_btn = st.columns([1.3, 8.7])
                            with pc_chk:
                                st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
                                st.checkbox(
                                    tr("선택", "Select"),
                                    key=f"pre_chk_{issn}",
                                    label_visibility="collapsed"
                                )
                            with pc_btn:
                                st.button(
                                    f"➕ {j_name} ({issn})",
                                    key=f"a_{i}_{j}_{issn}",
                                    on_click=cb_add_preset,
                                    args=(issn,),
                                    use_container_width=True
                                )

        elif active_step3_tab == "SEARCH":
            st.caption(tr(
                "🔍 찾으시는 학술지의 영문 이름이나 분야(예: Stroke, Dysphagia, Rehabilitation, Lancet, Nature)를 입력하고 검색하세요. 한글이나 철자 오타를 입력해도 자동으로 교정해 검색하며, 학술지를 추가해도 이 검색 탭 화면이 그대로 유지됩니다!",
                "🔍 Search by journal title, publisher, or field (with automatic typo correction). This search tab remains active after clicking, and you can select multiple journals to batch-add at once!"
            ))
            with st.form("sf", border=False):
                ca, cb = st.columns([7.2, 2.8])
                with ca:
                    st.text_input(
                        "Search Parameters",
                        key="search_kw_input",
                        label_visibility="collapsed",
                        placeholder=tr("✍️ 학술지 이름·분야 입력 (예: Stroke, Rehabilitation, Nature — 한글/오타 자동 교정 지원)...", "✍️ e.g., Stroke, Rehabilitation, Neuroscience (Auto typo-correction enabled)...")
                    )
                with cb:
                    st.form_submit_button(
                        tr("🔍 학술지 DB 검색", "🔍 Search Journals"),
                        on_click=cb_search_db,
                        use_container_width=True
                    )

            # 🔤 One-Click Popular Journal & Field Autocomplete Chips
            j_ac_hdr = tr(
                "🔤 오타 걱정 없는 인기 학술지·분야 원클릭 자동완성 검색 (클릭 시 즉시 검색됩니다):",
                "🔤 One-Click Popular Journal & Discipline Autocomplete (Click to search immediately):"
            )
            st.markdown(f"<div style='font-size:0.89rem; font-weight:700; color:#1E40AF; margin-bottom:5px;'>{j_ac_hdr}</div>", unsafe_allow_html=True)
            j_ac_cols = st.columns(4, gap="small")
            for idx_j_ac, j_sug in enumerate(JOURNAL_SEARCH_SUGGESTIONS[:8]):
                with j_ac_cols[idx_j_ac % 4]:
                    j_btn_lbl = j_sug["label"] if st.session_state.ui_lang == "KO_EN" else f"🔍 {j_sug['kw']}"
                    st.button(
                        j_btn_lbl,
                        key=f"btn_j_ac_{idx_j_ac}",
                        on_click=cb_quick_search_journal,
                        args=(j_sug["kw"],),
                        use_container_width=True
                    )

            if st.session_state.get("last_search_typo_note"):
                st.markdown(
                    f"<div class='typo-suggest-box' style='margin-top:6px; margin-bottom:8px;'>"
                    f"<b>{st.session_state.last_search_typo_note}</b></div>",
                    unsafe_allow_html=True
                )

            if st.session_state.skw_res:
                checked_srch_count = sum(
                    1 for item in st.session_state.skw_res
                    if item["issn"] not in st.session_state.cart and st.session_state.get(f"srch_chk_{item['issn']}", False)
                )
                srch_res_guide_txt = tr(
                    f"검색 결과 총 {len(st.session_state.skw_res)}건 — 왼쪽 체크박스를 여러 개 선택한 뒤 아래 [➕ 체크한 검색 학술지 한 번에 추가하기] 버튼을 누르시거나, 우측 [➕ 바로 추가] 버튼을 누르세요. (클릭 후에도 현재 검색 화면이 그대로 유지됩니다!)",
                    f"Found {len(st.session_state.skw_res)} journals — Check multiple boxes and click [➕ Add Checked Search Results] or click [➕ Add Journal] individually."
                )
                st.markdown(
                    f"<div style='background:#EFF6FF; border:1.5px solid #93C5FD; border-radius:10px; padding:10px 14px; margin-bottom:8px; font-size:0.92rem; color:#1E3A8A; font-weight:700;'>"
                    f"💡 {srch_res_guide_txt}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                srch_bar_c1, srch_bar_c2 = st.columns([6.4, 3.6], gap="small")
                with srch_bar_c1:
                    add_srch_label = tr(
                        f"➕ 체크한 검색 학술지 한 번에 추가하기 ({checked_srch_count}개 선택됨)",
                        f"➕ Add All Checked Search Results ({checked_srch_count} selected)"
                    )
                    st.button(
                        add_srch_label,
                        key="btn_batch_add_searched_top",
                        type="primary" if checked_srch_count > 0 else "secondary",
                        on_click=cb_add_selected_searched,
                        use_container_width=True
                    )
                with srch_bar_c2:
                    st.button(
                        tr("☑️ 검색 결과 전체 선택 / 해제", "☑️ Select / Deselect All Results"),
                        key="btn_toggle_all_searched",
                        on_click=cb_toggle_select_all_searched,
                        use_container_width=True
                    )

                for idx, info in enumerate(st.session_state.skw_res):
                    issn_code = info["issn"]
                    already_in_cart = (issn_code in st.session_state.cart)
                    is_srch_checked = bool(st.session_state.get(f"srch_chk_{issn_code}", False)) and not already_in_cart
                    row_bg = "#ECFDF5" if already_in_cart else ("#EFF6FF" if is_srch_checked else "#FFFFFF")
                    row_border = "#10B981" if already_in_cart else ("#3B82F6" if is_srch_checked else "#E2E8F0")
                    sc_chk, c1, c2 = st.columns([0.65, 6.95, 2.4])
                    with sc_chk:
                        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                        st.checkbox(
                            tr("선택", "Select"),
                            key=f"srch_chk_{issn_code}",
                            disabled=already_in_cart,
                            label_visibility="collapsed"
                        )
                    c1.markdown(
                        f"<div style='padding:9px 12px; background:{row_bg}; border:1.5px solid {row_border}; border-radius:10px; margin-bottom:5px;'>"
                        f"{render_journal_html(info, lang=st.session_state.ui_lang)}</div>",
                        unsafe_allow_html=True
                    )
                    if already_in_cart:
                        c2.button(tr("✅ 추가됨", "✅ Added"), key=f"sad_{idx}_{issn_code}", disabled=True, use_container_width=True)
                    else:
                        c2.button(tr("➕ 바로 추가", "➕ Add Journal"), key=f"sa_{idx}_{issn_code}", on_click=cb_add_searched, args=(issn_code, info), use_container_width=True)

                if len(st.session_state.skw_res) > 5:
                    st.button(
                        add_srch_label,
                        key="btn_batch_add_searched_bottom",
                        type="primary" if checked_srch_count > 0 else "secondary",
                        on_click=cb_add_selected_searched,
                        use_container_width=True
                    )

        elif active_step3_tab == "ISSN":
            st.caption(tr(
                "🔢 학술지의 8자리 국제표준일련번호(ISSN, 예: 0028-0836)를 입력하세요. 하이픈(-) 없이 숫자 8자리(00280836)만 입력해도 자동으로 교정되며, 쉼표(,)로 여러 개를 한 번에 입력할 수도 있습니다!",
                "🔢 Input one or multiple 8-digit ISSNs separated by commas or spaces (e.g., 0028-0836 or 00280836; hyphens are auto-formatted)."
            ))
            with st.form("if", clear_on_submit=True, border=False):
                cc, cd = st.columns([7.2, 2.8])
                with cc:
                    st.text_input(
                        "ISSN Parameter",
                        key="manual_issn_input",
                        label_visibility="collapsed",
                        placeholder=tr("✍️ ISSN 1개 또는 여러 개 입력 (예: 0028-0836, 0036-8075 — 숫자 8자리만 쳐도 자동 하이픈 교정)", "✍️ Single or multiple ISSNs (e.g., 0028-0836, 0036-8075)")
                    )
                with cd:
                    st.form_submit_button(
                        tr("➕ ISSN 학술지(단일·복수) 추가", "➕ Add ISSN(s)"),
                        on_click=cb_manual_issn,
                        use_container_width=True
                    )

            # 🔤 Searchable No-Typo ISSN Autocomplete Multiselect
            issn_ac_options = [
                f"{j_name} — ISSN: {issn} ({cat})"
                for cat, jrnls in GLOBAL_PRESETS.items()
                for j_name, issn in jrnls.items()
                if issn not in st.session_state.cart
            ]
            if issn_ac_options:
                issn_ac_title = tr(
                    "🔤 숫자 오타 걱정 없이 학술지 이름으로 ISSN 자동완성 선택 (여러 개 동시 선택 가능):",
                    "🔤 Typo-Free ISSN Autocomplete Picker by Journal Name (Multi-select supported):"
                )
                st.markdown(f"<div style='font-size:0.9rem; font-weight:700; color:#1E40AF; margin-top:4px; margin-bottom:4px;'>{issn_ac_title}</div>", unsafe_allow_html=True)
                ia_c1, ia_c2 = st.columns([7.2, 2.8], gap="small")
                with ia_c1:
                    st.multiselect(
                        "ISSN Autocomplete Multiselect",
                        options=issn_ac_options,
                        key="issn_autocomplete_multiselect",
                        placeholder=tr("👉 여기를 클릭해 학술지 이름이나 ISSN 앞자리를 입력하면 자동완성 목록이 뜹니다...", "👉 Click and type journal name or ISSN digits to autocomplete..."),
                        label_visibility="collapsed"
                    )
                with ia_c2:
                    st.button(
                        tr("➕ 자동완성 선택 ISSN 일괄 추가", "➕ Add Selected ISSN(s)"),
                        key="btn_add_issn_autocomplete",
                        on_click=cb_add_selected_issn_autocomplete,
                        use_container_width=True
                    )

    # Dynamic Action Area for STEP 03:
    # - When NOT confirmed (and valid): Shows a pulsing CTA prompt + glowing Primary button!
    # - When CONFIRMED: The pulsing button DISAPPEARS and transforms into an emerald Confirmed Banner!
    step3_now_valid = (scope_choice == "GLOBAL" and not st.session_state.cart) or (len(st.session_state.cart) > 0)
    if step3_now_valid and not st.session_state.step3_confirmed:
        st.markdown(f"""
        <div class="cta-attention-box">
            <div>
                <span class="bounce-icon">👇</span> <b>{tr('[3단계 완료 클릭 필수!] 위 학술지 검색 범위를 확인하셨다면, 마지막 4단계 수집 실행을 활성화하기 위해 바로 아래 반짝이는 파란색 [3단계 완료] 버튼을 꼭 클릭해 주세요!', '[Action Required!] Confirm your target journal scope by clicking the glowing blue [Confirm Step 3] button below to unlock Step 4 extraction!')}</b>
            </div>
            <span class="cta-attention-badge">👉 {tr('아래 버튼 클릭 필수', 'CLICK BELOW')}</span>
        </div>
        """, unsafe_allow_html=True)

        st.button(
            tr("👉 여기를 눌러 3단계 학술지 범위 완료하기: 확정 후 4단계 논문 수집으로 이동 (Click to Confirm Step 3)", "👉 Click Here to Complete Step 3: Confirm Target Journal Scope"),
            type="primary",
            on_click=cb_confirm_step3,
            use_container_width=True
        )
    elif st.session_state.step3_confirmed and step3_now_valid:
        scope_done_msg = (
            tr("🌍 전 세계 모든 학술지 통합 검색 모드로 확정되었습니다!", "🌍 Confirmed: Search All Global Journals!")
            if not st.session_state.cart else
            tr(f"🎯 총 {len(st.session_state.cart)}개의 지정 학술지로 확정되었습니다!", f"🎯 Confirmed: {len(st.session_state.cart)} target journal(s)!")
        )
        st.markdown(f"""
        <div class="cta-confirmed-bar">
            <div>
                ✅ <b>{tr('[3단계 확정 완료!]', '[Step 3 Confirmed!]')} {scope_done_msg}</b>
                <span style="font-size:0.9rem; font-weight:500; color:#166534; margin-left:6px;">{tr('(범위를 변경하시면 완료 버튼이 자동으로 다시 나타납니다)', '(Changing scope above will re-open confirmation)')}</span>
            </div>
            <span class="cta-confirmed-pill">⬇️ {tr('이제 아래 4단계 수집 버튼을 클릭하세요!', 'CLICK START IN STEP 4 BELOW!')}</span>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 🔍 Compute True Sequential Step Readiness & Stale Filter Diff Detection
# ==========================================
target_kw = st.session_state.get("kw_input", "").strip()
opt_final = optimize_search_query(target_kw)
effective_cart = st.session_state.cart if st.session_state.scope_mode == "TARGETED" or st.session_state.cart else {}
active_formula_str = opt_final["optimized"] if opt_final["optimized"] else target_kw

data_s1_valid = bool(target_kw or effective_cart)
data_s2_valid = (start_year <= end_year)
data_s3_valid = (st.session_state.scope_mode == "GLOBAL" and not st.session_state.cart) or (len(st.session_state.cart) > 0)
all_data_valid = (data_s1_valid and data_s2_valid and data_s3_valid)

s1_done = bool(st.session_state.step1_confirmed and data_s1_valid)
s2_done = bool(st.session_state.step2_confirmed and data_s2_valid)
s3_done = bool(st.session_state.step3_confirmed and data_s3_valid)
all_steps_ready = (s1_done and s2_done and s3_done)

current_config = {
    "formula": active_formula_str,
    "search_mode": "DEEP" if "Deep" in search_mode else "ULTRA",
    "sort_by": sort_by,
    "doc_type": doc_type,
    "start_year": int(start_year),
    "end_year": int(end_year),
    "top_n": int(top_n),
    "min_citations": int(min_citations),
    "oa_only": bool(oa_only),
    "require_abstract": bool(require_abstract),
    "deep_max_phases": int(deep_max_phases) if "Deep" in search_mode else 0,
    "restrict_root_years": bool(restrict_root_years) if "Deep" in search_mode else False,
    "issns": tuple(sorted(effective_cart.keys())),
}

def get_changed_filter_descriptions(old_cfg, new_cfg):
    if not old_cfg:
        return []
    changes = []
    if old_cfg["formula"] != new_cfg["formula"]:
        changes.append(tr(f"검색식 ('{old_cfg['formula'] or '없음'}' ➔ '{new_cfg['formula'] or '없음'}')", f"Query ('{old_cfg['formula']}' ➔ '{new_cfg['formula']}')"))
    if old_cfg["search_mode"] != new_cfg["search_mode"]:
        changes.append(tr("탐색 알고리즘 (트렌드 스캔 ↔ 뿌리 역추적)", "Discovery Algorithm"))
    if old_cfg["sort_by"] != new_cfg["sort_by"]:
        changes.append(tr("논문 정렬 기준", "Primary Sort Metric"))
    if old_cfg["doc_type"] != new_cfg["doc_type"]:
        changes.append(tr(f"문헌 유형 ({old_cfg['doc_type']} ➔ {new_cfg['doc_type']})", f"Document Type ({old_cfg['doc_type']} ➔ {new_cfg['doc_type']})"))
    if (old_cfg["start_year"], old_cfg["end_year"]) != (new_cfg["start_year"], new_cfg["end_year"]):
        changes.append(tr(f"출판 연도 ({old_cfg['start_year']}–{old_cfg['end_year']}년 ➔ {new_cfg['start_year']}–{new_cfg['end_year']}년)", f"Years ({old_cfg['start_year']}–{old_cfg['end_year']} ➔ {new_cfg['start_year']}–{new_cfg['end_year']})"))
    if old_cfg["top_n"] != new_cfg["top_n"]:
        changes.append(tr(f"최대 추출 논문 수 ({old_cfg['top_n']}편 ➔ {new_cfg['top_n']}편)", f"Max Papers ({old_cfg['top_n']} ➔ {new_cfg['top_n']})"))
    if old_cfg["min_citations"] != new_cfg["min_citations"]:
        changes.append(tr(f"최소 피인용 기준 ({old_cfg['min_citations']}회 ➔ {new_cfg['min_citations']}회)", f"Min Citations ({old_cfg['min_citations']} ➔ {new_cfg['min_citations']})"))
    if old_cfg["oa_only"] != new_cfg["oa_only"]:
        changes.append(tr(f"무료 PDF(OA) 전용 필터 ({'켜짐' if new_cfg['oa_only'] else '꺼짐'})", f"OA Only Filter ({'ON' if new_cfg['oa_only'] else 'OFF'})"))
    if old_cfg["require_abstract"] != new_cfg["require_abstract"]:
        changes.append(tr(f"초록 필수 필터 ({'켜짐' if new_cfg['require_abstract'] else '꺼짐'})", f"Require Abstract ({'ON' if new_cfg['require_abstract'] else 'OFF'})"))
    if old_cfg["deep_max_phases"] != new_cfg["deep_max_phases"]:
        changes.append(tr("참고문헌 역추적 탐색 범위", "Reference Tracing Depth"))
    if old_cfg["restrict_root_years"] != new_cfg["restrict_root_years"]:
        changes.append(tr("뿌리 논문 출판 연도 제한 여부", "Root Year Restriction"))
    if old_cfg["issns"] != new_cfg["issns"]:
        changes.append(tr(f"대상 학술지 범위 ({len(old_cfg['issns'])}개 ➔ {len(new_cfg['issns'])}개)", f"Target Journals ({len(old_cfg['issns'])} ➔ {len(new_cfg['issns'])})"))
    return changes

has_extracted_df = (st.session_state.df is not None and not st.session_state.df.empty)
changed_filter_list = get_changed_filter_descriptions(st.session_state.executed_config, current_config) if has_extracted_df else []
is_result_stale = bool(has_extracted_df and changed_filter_list)

with stepper_placeholder.container():
    render_workflow_stepper(
        s1_done=s1_done,
        s2_done=s2_done,
        s3_done=s3_done,
        all_ready=all_steps_ready,
        has_results=has_extracted_df,
        is_stale=is_result_stale,
        mode_short=tr("트렌드 스캔" if "Ultra-fast" in search_mode else "뿌리 논문 역추적", "Trend Scan" if "Ultra-fast" in search_mode else "Root Network"),
        scope_short=(
            tr("전 세계 전체 학술지", "All Global Journals")
            if not effective_cart else
            tr(f"지정 학술지 {len(effective_cart)}개", f"{len(effective_cart)} Journal(s)")
        ),
        lang=st.session_state.ui_lang
    )


# ==========================================
# 🚀 STEP 04: Visual Pre-Flight Filter Verification & Execution
# ==========================================
if has_extracted_df and not is_result_stale and all_steps_ready:
    s4_banner_state = "done"
    s4_banner_text = tr("현재 설정으로 논문 수집 완료", "Extraction Up-to-Date")
elif is_result_stale:
    s4_banner_state = "warn"
    s4_banner_text = tr("필터 변경됨 — 재분석 클릭 필수", "Filters Changed — Click Re-run")
elif all_steps_ready:
    s4_banner_state = "active"
    s4_banner_text = tr("필수 클릭: 아래 수집 시작 버튼을 눌러주세요", "Ready: Click Start Extraction Below")
else:
    s4_banner_state = "todo"
    s4_banner_text = tr("1·2·3단계 확정 후 진행 가능", "Confirm Steps 1–3 First")

render_step_banner(
    step_class="step4",
    step_num_text="STEP 04 / 04",
    title_text=tr("🚀 4단계: 최종 필터 점검 및 논문 데이터 수집 실행", "🚀 STEP 04: Pre-Flight Filter Check & Execute Extraction"),
    state=s4_banner_state,
    status_text=s4_banner_text,
    anchor_id="step-04-anchor"
)

with st.container(border=True):
    # 1. Prominent Search Formula Banner in STEP 04
    if active_formula_str:
        orig_input_html = (
            f"<div style='font-size:0.91rem; color:#334155; margin-top:5px;'>💬 {tr('입력하셨던 자연어 원문', 'Original Input')}: \"{st.session_state.last_nl_input}\"</div>"
            if (st.session_state.last_nl_input and st.session_state.last_nl_input != active_formula_str) else ""
        )
        st.markdown(f"""
        <div style="background:linear-gradient(90deg, #EFF6FF 0%, #F8FAFC 100%); border:2px solid #60A5FA; border-left:7px solid #1D4ED8; border-radius:13px; padding:14px 18px; margin-bottom:14px;">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:5px;">
                <span style="font-size:0.95rem; font-weight:800; color:#1E40AF;">🎯 {tr('최종 적용될 학술 검색식 (Active Search Formula)', 'Active Academic Search Formula')}</span>
                <span class="filter-pill-on">🟢 {tr('검색식 필터 작동 중', 'QUERY FILTER ACTIVE')}</span>
            </div>
            <div style="font-family:monospace; font-size:1.08rem; font-weight:800; color:#0F172A; background:#FFFFFF; border:1px solid #BFDBFE; padding:9px 14px; border-radius:9px; word-break:break-all;">
                {active_formula_str}
            </div>
            {orig_input_html}
        </div>
        """, unsafe_allow_html=True)

    # 2. 6-Card Visual Pre-Flight Filter Grid
    is_deep = "Deep" in search_mode
    sort_label_ko = {
        "CITATIONS": "총 피인용 횟수 순",
        "VELOCITY": "연간 인용 속도(회/년) 순",
        "FWCI": "분야 보정 영향력(FWCI) 순",
        "YEAR_DESC": "최신 출판 연도 순",
        "DEFAULT": "공통 인용 빈도(Network Hits) 순"
    }.get(sort_by, "총 피인용 횟수 순")
    sort_label_en = {
        "CITATIONS": "Total Citations",
        "VELOCITY": "Citation Velocity",
        "FWCI": "FWCI Impact",
        "YEAR_DESC": "Newest Year First",
        "DEFAULT": "In-Network Co-citations"
    }.get(sort_by, "Total Citations")

    algo_val = (
        tr(f"🧠 심층 뿌리 논문 역추적 (상위 {deep_max_phases*100}편 참고문헌 스캔)", f"🧠 Deep Root Network ({deep_max_phases*100} seeds)")
        if is_deep else
        tr("⚡ 빠른 트렌드 스캔 (대표·인기 논문 추출)", "⚡ Ultra-fast Trend Scan")
    )
    algo_sub = tr(f"정렬 기준: {sort_label_ko}", f"Sorted by: {sort_label_en}")

    scope_active = bool(effective_cart)
    scope_val = (
        tr(f"🎯 지정 학술지 {len(effective_cart)}개 전용", f"🎯 {len(effective_cart)} Selected Journal(s)")
        if scope_active else
        tr("🌍 전 세계 모든 학술지 통합", "🌍 All Global Academic Journals")
    )
    scope_sub = (
        ", ".join([v["name"] for v in list(effective_cart.values())[:2]]) + (f" 외 {len(effective_cart)-2}개" if len(effective_cart) > 2 else "")
        if scope_active else
        tr("2억 5천만 편 전체 데이터베이스 탐색", "Unrestricted global literature scan")
    )

    year_span = max(1, end_year - start_year + 1)
    year_val = tr(f"📅 {start_year}년 – {end_year}년 (총 {year_span}개년도)", f"📅 {start_year} – {end_year} ({year_span} yrs)")
    year_sub = (
        tr("🔒 뿌리 논문도 이 연도 내로만 제한됨" if restrict_root_years else "🔓 뿌리 논문은 연도 제한 없이 고전까지 발굴",
           "🔒 Root papers restricted to range" if restrict_root_years else "🔓 Root papers traced across all history")
        if is_deep else
        tr("해당 기간 내 출판된 논문만 필터링", "Filters works published in this window")
    )

    doc_active = (doc_type != "ALL")
    doc_short_ko = {
        "ALL": "📚 전체 학술 문헌 (모든 유형)",
        "ARTICLE_REVIEW": "⭐ 학술지 핵심 논문 (원저 + 종설)",
        "ARTICLE": "🔬 원저 연구 논문만 (Article)",
        "REVIEW": "📖 종설·문헌고찰만 (Review)",
        "PREPRINT": "🚀 최신 프리프린트만 (Preprint)",
        "BOOK": "📕 단행본 · 북챕터 전용",
        "DISSERTATION": "🎓 석·박사 학위논문 전용",
        "EDITORIAL_LETTER": "✉️ 사설 · 레터 · 코멘터리 전용"
    }.get(doc_type, "📚 전체 학술 문헌")
    doc_short_en = {
        "ALL": "📚 All Scholarly Works",
        "ARTICLE_REVIEW": "⭐ Articles & Reviews Only",
        "ARTICLE": "🔬 Original Articles Only",
        "REVIEW": "📖 Reviews Only",
        "PREPRINT": "🚀 Preprints Only",
        "BOOK": "📕 Books & Chapters Only",
        "DISSERTATION": "🎓 Dissertations Only",
        "EDITORIAL_LETTER": "✉️ Editorials & Letters Only"
    }.get(doc_type, "📚 All Works")

    cap_val = tr(f"📊 최대 {top_n}편 추출", f"📊 Up to {top_n} Papers")
    cap_sub = (
        tr(f"⭐ 최소 {min_citations:,}회 이상 인용된 논문만 엄선", f"⭐ Min {min_citations:,} citations required")
        if min_citations > 0 else
        tr("최소 인용 횟수 제한 없음 (0회 이상 포함)", "No minimum citation cutoff (0+)")
    )

    qual_active = (oa_only or require_abstract)
    oa_badge_txt = tr("🔓 무료 PDF(OA) 전용: 켜짐", "🔓 OA PDF Only: ON") if oa_only else tr("🔓 무료·유료 원문 모두 정상 포함", "🔓 All Access Types Included")
    abs_badge_txt = tr("📝 초록 필수 포함: 켜짐", "📝 Abstract Required: ON") if require_abstract else tr("초록 유무와 무관하게 모든 논문 포함", "Includes Records With or Without Abstract")
    min_cite_pill_txt = tr(f"🟢 최소 {min_citations}회↑ 적용됨", f"🟢 MIN {min_citations} APPLIED") if min_citations > 0 else tr("🟢 인용 제한 없음 (정상 적용)", "🟢 ALL CITATIONS (READY)")
    scope_pill_txt = tr("🟢 지정 학술지 적용됨", "🟢 TARGETED APPLIED") if scope_active else tr("🟢 전 세계 통합 (정상 적용)", "🟢 GLOBAL READY")
    doc_pill_txt = tr("🟢 유형 필터 적용됨", "🟢 TYPE FILTER ON") if doc_active else tr("🟢 전체 허용 (정상 적용)", "🟢 ALL TYPES READY")
    qual_pill_txt = tr("🟢 품질 필터 적용됨", "🟢 GATES ACTIVE") if qual_active else tr("🟢 전체 허용 (정상 적용)", "🟢 ALL ACCESS READY")
    doc_card_val = doc_short_ko if st.session_state.ui_lang == "KO_EN" else doc_short_en
    doc_card_sub = tr(
        "선택한 유형의 문헌만 정밀 추출합니다" if doc_active else "유형 제한 없이 모든 학술 문헌을 빠짐없이 포함합니다",
        "Strictly filters by selected type" if doc_active else "Inclusively scans all scholarly document types"
    )

    st.markdown(
        f"<div style='font-size:0.92rem; font-weight:700; color:#0F766E; background:#F0FDFA; border:1px solid #99F6E4; border-radius:9px; padding:8px 13px; margin-bottom:10px;'>"
        f"✅ {tr('아래 6개 최종 필터 카드가 모두 초록색·청록색 배지(🟢 설정됨 / 🟢 전체 허용 정상 적용)로 표시되어 있으면 모든 조건이 정상 준비된 상태입니다!', 'All 6 filter cards below are active and ready (both custom filters and inclusive All-Allowed defaults are verified)!')}"
        f"</div>",
        unsafe_allow_html=True
    )

    st.markdown(f"""
    <div class="preflight-grid">
        <div class="preflight-card highlight">
            <div>
                <div class="preflight-label">
                    <span>🧭 {tr('1. 탐색 알고리즘 & 정렬', '1. Algorithm & Sort')}</span>
                    <span class="filter-pill-on">🟢 {tr('알고리즘 설정됨', 'CONFIGURED')}</span>
                </div>
                <div class="preflight-value">{algo_val}</div>
            </div>
            <div class="preflight-sub">{algo_sub}</div>
        </div>
        <div class="preflight-card {'active-filter' if scope_active else 'ready-inclusive'}">
            <div>
                <div class="preflight-label">
                    <span>🏛️ {tr('2. 대상 학술지 범위', '2. Journal Scope')}</span>
                    <span class="{'filter-pill-on' if scope_active else 'filter-pill-inclusive'}">{scope_pill_txt}</span>
                </div>
                <div class="preflight-value">{scope_val}</div>
            </div>
            <div class="preflight-sub">{scope_sub}</div>
        </div>
        <div class="preflight-card {'active-filter' if restrict_root_years else 'ready-inclusive'}">
            <div>
                <div class="preflight-label">
                    <span>📅 {tr('3. 출판 연도 범위', '3. Publication Years')}</span>
                    <span class="filter-pill-on">🟢 {tr('연도 범위 적용됨', 'YEARS APPLIED')}</span>
                </div>
                <div class="preflight-value">{year_val}</div>
            </div>
            <div class="preflight-sub">{year_sub}</div>
        </div>
        <div class="preflight-card {'active-filter' if doc_active else 'ready-inclusive'}">
            <div>
                <div class="preflight-label">
                    <span>📑 {tr('4. 문헌 유형 필터', '4. Document Type')}</span>
                    <span class="{'filter-pill-on' if doc_active else 'filter-pill-inclusive'}">{doc_pill_txt}</span>
                </div>
                <div class="preflight-value">{doc_card_val}</div>
            </div>
            <div class="preflight-sub">{doc_card_sub}</div>
        </div>
        <div class="preflight-card {'active-filter' if min_citations > 0 else 'ready-inclusive'}">
            <div>
                <div class="preflight-label">
                    <span>📊 {tr('5. 수집 규모 & 인용 기준', '5. Capacity & Cutoff')}</span>
                    <span class="{'filter-pill-on' if min_citations > 0 else 'filter-pill-inclusive'}">{min_cite_pill_txt}</span>
                </div>
                <div class="preflight-value">{cap_val}</div>
            </div>
            <div class="preflight-sub">{cap_sub}</div>
        </div>
        <div class="preflight-card {'active-filter' if qual_active else 'ready-inclusive'}">
            <div>
                <div class="preflight-label">
                    <span>🛡️ {tr('6. 원문 PDF & 초록 필터', '6. PDF & Abstract Gates')}</span>
                    <span class="{'filter-pill-on' if qual_active else 'filter-pill-inclusive'}">{qual_pill_txt}</span>
                </div>
                <div class="preflight-value">{oa_badge_txt}</div>
            </div>
            <div class="preflight-sub">{abs_badge_txt}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Dynamic State Machine for STEP 04 Action Buttons:
    start_clicked = False

    if not all_steps_ready:
        missing_steps_html = []
        unconfirmed_step_nums = []
        if not s1_done:
            unconfirmed_step_nums.append(1)
            if not data_s1_valid:
                missing_steps_html.append(tr("• <b>1단계 (연구 주제 입력):</b> ❌ 아직 검색어가 입력되지 않았습니다. 맨 위 <b>1단계</b>에서 연구 주제를 먼저 입력해 주세요.", "• <b>Step 1 (Research Topic):</b> ❌ No search query entered yet."))
            else:
                missing_steps_html.append(tr("• <b>1단계 (연구 주제 입력):</b> ⏳ 검색어는 입력되었으나 아직 <b>[1단계 완료]</b> 버튼이 클릭되지 않았습니다.", "• <b>Step 1 (Research Topic):</b> ⏳ Query entered, awaiting confirmation."))
        else:
            missing_steps_html.append(tr("• <b>1단계 (연구 주제 입력):</b> ✅ 확정 완료", "• <b>Step 1 (Research Topic):</b> ✅ Confirmed"))

        if not s2_done:
            unconfirmed_step_nums.append(2)
            if not data_s2_valid:
                missing_steps_html.append(tr("• <b>2단계 (탐색 방식·필터):</b> ❌ 시작 연도가 종료 연도보다 큽니다. 위 <b>2단계</b>에서 연도를 수정해 주세요.", "• <b>Step 2 (Algorithm & Filters):</b> ❌ Start Year exceeds End Year."))
            else:
                missing_steps_html.append(tr("• <b>2단계 (탐색 방식·필터):</b> ⏳ 아직 <b>[2단계 완료]</b> 버튼이 클릭되지 않았습니다.", "• <b>Step 2 (Algorithm & Filters):</b> ⏳ Awaiting Step 2 confirmation."))
        else:
            missing_steps_html.append(tr("• <b>2단계 (탐색 방식·필터):</b> ✅ 확정 완료", "• <b>Step 2 (Algorithm & Filters):</b> ✅ Confirmed"))

        if not s3_done:
            unconfirmed_step_nums.append(3)
            if not data_s3_valid:
                missing_steps_html.append(tr("• <b>3단계 (대상 학술지 범위):</b> ❌ 특정 학술지 검색 모드이지만 추가된 학술지가 0개입니다.", "• <b>Step 3 (Journal Scope):</b> ❌ Targeted mode selected with 0 journals."))
            else:
                missing_steps_html.append(tr("• <b>3단계 (대상 학술지 범위):</b> ⏳ 아직 <b>[3단계 완료]</b> 버튼이 클릭되지 않았습니다.", "• <b>Step 3 (Journal Scope):</b> ⏳ Awaiting Step 3 confirmation."))
        else:
            missing_steps_html.append(tr("• <b>3단계 (대상 학술지 범위):</b> ✅ 확정 완료", "• <b>Step 3 (Journal Scope):</b> ✅ Confirmed"))

        checklist_joined = "<br>".join(missing_steps_html)
        st.markdown(f"""
        <div class="step-prereq-alert">
            📋 <b>{tr('[진행 안내] 아직 완료 버튼을 누르지 않은 단계가 있습니다! 아래 바로가기 버튼을 누르면 해당 단계로 즉시 이동합니다.', '[Action Guide] Some previous steps have not been confirmed yet! Click a button below to jump directly to that step.')}</b><br>
            <div style="margin-top:6px; line-height:1.7;">{checklist_joined}</div>
        </div>
        """, unsafe_allow_html=True)

        if unconfirmed_step_nums:
            jump_btn_cols = st.columns(len(unconfirmed_step_nums), gap="small")
            step_jump_labels = {
                1: tr("⬆️ 1단계(연구 주제 입력·확정)로 바로 이동하기", "⬆️ Jump to Step 1 (Research Topic)"),
                2: tr("⬆️ 2단계(탐색 방식·필터 확정)로 바로 이동하기", "⬆️ Jump to Step 2 (Algorithm & Filters)"),
                3: tr("⬆️ 3단계(대상 학술지 범위 확정)로 바로 이동하기", "⬆️ Jump to Step 3 (Journal Scope)")
            }
            for col_i, st_num in enumerate(unconfirmed_step_nums):
                with jump_btn_cols[col_i]:
                    st.button(
                        step_jump_labels[st_num],
                        key=f"btn_s4_jump_to_s{st_num}",
                        on_click=cb_jump_to_step,
                        args=(st_num,),
                        use_container_width=True
                    )

        if all_data_valid:
            st.markdown(f"""
            <div class="cta-attention-box">
                <div>
                    <span class="bounce-icon">👇</span> <b>{tr('[원클릭 확정 가능!] 위 6개 최종 필터 카드의 설정 내용이 맞다면, 위로 다시 올라갈 필요 없이 바로 아래 반짝이는 파란색 버튼을 클릭해 미완료 단계를 한 번에 확정하세요!', '[One-Click Confirmation!] If the 6 filter cards above look right, click the glowing blue button below to confirm Steps 1–3 all at once!')}</b>
                </div>
                <span class="cta-attention-badge">⚡ {tr('원클릭 일괄 확정', 'CONFIRM ALL')}</span>
            </div>
            """, unsafe_allow_html=True)
            st.button(
                tr("👉 여기를 클릭해 현재 설정 그대로 1·2·3단계를 한 번에 확정하기 (클릭 시 즉시 논문 수집 버튼이 열립니다!)", "👉 Click Here to Confirm All Steps 1–3 with Current Settings (Unlocks Extraction Immediately!)"),
                type="primary",
                on_click=cb_confirm_all_steps_quick,
                use_container_width=True
            )
    else:
        # all_steps_ready is True!
        if is_result_stale:
            # Filters were changed after a previous run -> Show high-attention pulsing Amber/Red Re-run Prompt & Primary Button!
            st.markdown(f"""
            <div class="cta-attention-amber">
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
                    <span style="font-size:1.06rem; font-weight:900; color:#991B1B;">
                        <span class="bounce-icon">👇</span> 🔄 {tr('[필터 변경 감지 — 재분석 클릭 필수!] 위에서 검색 조건이나 필터를 변경하셨습니다!', '[Filter Change Detected — Re-run Required!] You modified search parameters above!')}
                    </span>
                    <span class="cta-amber-badge">🚨 {tr('새 필터 재분석 필수', 'RE-RUN REQUIRED')}</span>
                </div>
                <div style="font-size:0.95rem; line-height:1.62;">
                    • <b>{tr('새로 변경된 필터 항목', 'Modified Filters')}:</b> <span style="background:#FDE68A; padding:2px 8px; border-radius:6px; font-weight:800; color:#92400E;">{" / ".join(changed_filter_list)}</span><br>
                    • {tr('현재 아래쪽에 표시된 리포트는 <b>변경 전(이전) 필터 결과</b>입니다. 바로 아래 반짝이는 버튼을 클릭하시면 변경된 새 필터로 다시 분석되어 이 알림이 사라집니다!',
                          'The report below reflects your previous filters. Click the glowing button below to re-run extraction with your updated settings!')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            start_clicked = st.button(
                tr("🔄 지금 여기를 클릭해 변경된 새 필터 설정으로 논문 데이터 다시 수집·분석하기 (RE-RUN EXTRACTION)", "🔄 Click Here to Re-Run Extraction with Updated Filters"),
                type="primary",
                use_container_width=True
            )
        elif not has_extracted_df:
            # Ready for first extraction -> Show high-attention pulsing Blue Callout & Primary Start Button!
            st.markdown(f"""
            <div class="cta-attention-box">
                <div>
                    <span class="bounce-icon">👇</span> <b>{tr('🎉 [모든 단계 확정 완료 — 최종 수집 클릭 필수!] 1·2·3단계 설정이 모두 완료되었습니다! 지금 바로 아래 반짝이는 파란색 [논문 데이터 수집 시작하기] 버튼을 클릭하시면 실시간 분석이 시작됩니다!', '🎉 [All Steps Confirmed — Ready to Launch!] Click the glowing blue button right below to start real-time literature extraction and citation analysis!')}</b>
                </div>
                <span class="cta-attention-badge">🚀 {tr('수집 시작 클릭 필수', 'CLICK TO START')}</span>
            </div>
            """, unsafe_allow_html=True)
            start_clicked = st.button(
                tr("🚀 지금 여기를 클릭해 위 필터 설정으로 논문 데이터 수집 및 인용 분석 시작하기 (START EXTRACTION)", "🚀 Click Here to Start Academic Data Extraction & Citation Analysis"),
                type="primary",
                use_container_width=True
            )
        else:
            # Extraction is ALREADY DONE for the current filters!
            # The big pulsing Start button DISAPPEARS and is replaced by this reassuring Emerald Completion Banner!
            s4_done_txt = tr(
                f"[논문 데이터 수집 및 분석 완료!] 위 필터 설정으로 총 {len(st.session_state.df)}편의 핵심 논문 추출이 완료되어 바로 아래 [📊 최종 분석 리포트]에 표시되고 있습니다.",
                f"[Extraction Complete!] All {len(st.session_state.df)} papers matching your active filters are displayed in the Final Report below."
            )
            st.markdown(f"""
            <div class="cta-confirmed-bar">
                <div>
                    ✅ <b>{s4_done_txt}</b><br>
                    <span style="font-size:0.9rem; font-weight:500; color:#166534;">• {tr('위 1~3단계에서 검색어, 알고리즘, 연도, 문헌 유형 등을 변경하시면 [🔄 변경된 새 필터로 다시 분석하기] 버튼이 이곳에 자동으로 다시 나타납니다.', 'If you modify any filter in Steps 1–3 above, the Re-run Extraction button will automatically reappear here.')}</span>
                </div>
                <span class="cta-confirmed-pill">📊 {tr('아래 리포트 확인', 'REPORT READY BELOW')}</span>
            </div>
            """, unsafe_allow_html=True)

    # Preview of Upcoming Report Suite when no extraction has been executed yet (Eliminates empty bottom space!)
    if not has_extracted_df and not start_clicked and not st.session_state.trigger_rerun_pipeline:
        st.markdown(f"""
        <div style="margin-top:14px; padding-top:14px; border-top:1.5px dashed #CBD5E1;">
            <div style="font-size:0.96rem; font-weight:800; color:#334155; margin-bottom:10px;">
                📊 {tr('데이터 수집 시작 시 바로 아래에 생성되는 4대 핵심 분석 리포트 미리보기', 'Preview of the 4 Analytical Suites Generated Upon Execution')}
            </div>
            <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px;">
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:12px 14px;">
                    <div style="font-weight:800; font-size:0.93rem; color:#1E3A8A; margin-bottom:4px;">📈 ① {tr('6대 핵심 서지 지표 & 차트', '6 KPI Metrics & 4 Charts')}</div>
                    <div style="font-size:0.86rem; color:#475569; line-height:1.48;">{tr('평균 피인용, 무료 PDF 비율, FWCI 영향력, 연도·저널·기관·토픽 분포 차트 제공', 'Mean citations, OA ratio, FWCI, and chronological/venue/institution charts')}</div>
                </div>
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:12px 14px;">
                    <div style="font-weight:800; font-size:0.93rem; color:#0F766E; margin-bottom:4px;">🏆 ② {tr('필독 대표·뿌리 논문 스포트라이트', 'Spotlight & Root Papers')}</div>
                    <div style="font-size:0.86rem; color:#475569; line-height:1.48;">{tr('상위 15~100편 대표 논문과 최근 3년 내 급상승 브레이크스루 논문 초록 즉시 열람', 'Inspect top 15–100 papers and 3-year high-velocity breakthroughs with abstracts')}</div>
                </div>
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:12px 14px;">
                    <div style="font-weight:800; font-size:0.93rem; color:#4F46E5; margin-bottom:4px;">📋 ③ {tr('APA · AMA · BibTeX 원클릭 복사', 'Instant Citation Copy')}</div>
                    <div style="font-size:0.86rem; color:#475569; line-height:1.48;">{tr('모든 논문의 전체 초록 뷰어 및 클릭 즉시 복사 완료 표시가 뜨는 인용문 생성기', 'Full abstract reader and 1-click APA 7th, AMA, and BibTeX citation cards')}</div>
                </div>
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:12px 14px;">
                    <div style="font-weight:800; font-size:0.93rem; color:#B45309; margin-bottom:4px;">📥 ④ {tr('엑셀(.xlsx) & 서지(.ris) 다운로드', 'Excel & RIS Export')}</div>
                    <div style="font-size:0.86rem; color:#475569; line-height:1.48;">{tr('틀 고정·자동 필터·초록이 완비된 엑셀 보고서 및 Zotero/EndNote 호환 파일', 'Styled Excel workbook with full abstracts and reference manager RIS export')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if (start_clicked or st.session_state.trigger_rerun_pipeline) and all_data_valid:
        st.session_state.trigger_rerun_pipeline = False
        st.session_state.step1_confirmed = True
        st.session_state.step2_confirmed = True
        st.session_state.step3_confirmed = True

        if opt_final["was_modified"] and opt_final["optimized"]:
            st.session_state.last_nl_input = target_kw
            target_kw = opt_final["optimized"]

        st.session_state.df = None

        ui_progress_bar = st.progress(0, text=tr("🌐 OpenAlex 글로벌 학술 데이터베이스 연결 중...", "🌐 Connecting to OpenAlex Global Database..."))

        with st.status(tr("🔍 실시간 학술 데이터 수집 및 인용 네트워크 분석 진행 중...", "🔍 Executing academic literature extraction & citation analysis..."), expanded=True) as status_logger:
            st.write(tr(
                f"• **적용된 학술 검색식:** `{opt_final['optimized'] or 'Selected Journals All Works'}`",
                f"• **Active Query:** `{opt_final['optimized'] or 'Selected Journals All Works'}`"
            ))
            st.write(tr(
                "• 완료(100%)될 때까지 페이지를 새로고침하지 말고 잠시만 기다려 주세요.",
                "• Please wait until completion (100%) without refreshing the browser."
            ))

            issn_tuple = tuple(effective_cart.keys())
            start_time = time.time()

            try:
                st.session_state.df = run_data_pipeline(
                    issn_tuple,
                    start_year,
                    end_year,
                    top_n,
                    search_mode,
                    target_kw,
                    min_citations,
                    oa_only,
                    status_logger,
                    ui_progress_bar,
                    doc_type=doc_type,
                    sort_by=sort_by,
                    require_abstract=require_abstract,
                    deep_max_phases=deep_max_phases,
                    restrict_root_years=restrict_root_years
                )
                elapsed = round(time.time() - start_time, 2)

                if st.session_state.df is not None and not st.session_state.df.empty:
                    st.session_state.executed_config = current_config.copy()
                    st.session_state.last_export_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_session_snapshot()
                    status_logger.update(
                        label=tr(f"✅ 분석 완료: 총 {len(st.session_state.df)}편의 핵심 논문을 {elapsed}초 만에 완벽히 수집했습니다!", f"✅ Completed: Extracted {len(st.session_state.df)} papers in {elapsed}s!"),
                        state="complete",
                        expanded=False
                    )
                    ui_progress_bar.progress(100, text=tr(f"✅ 데이터 수집 및 무결성 검증 완료 ({elapsed}초)", f"✅ Extraction & validation complete ({elapsed}s)"))
                    time.sleep(0.2)
                    ui_progress_bar.empty()
                    st.session_state.toast_msg = {
                        "msg": tr(f"🎉 총 {len(st.session_state.df)}편의 논문 수집이 완료되었습니다! 바로 아래 최종 분석 리포트를 확인하세요.", f"🎉 Extracted {len(st.session_state.df)} papers!"),
                        "icon": "🎉"
                    }
                    st.rerun()
                else:
                    ui_progress_bar.empty()
                    status_logger.update(
                        label=tr("⚠️ 탐색 완료: 조건에 부합하는 논문이 없습니다 (0건).", "⚠️ Completed: 0 matching records found."),
                        state="complete",
                        expanded=False
                    )
                    st.warning(tr(
                        "조건에 일치하는 논문이 없습니다. 출판 연도 범위를 넓히거나 최소 피인용 수 / 문헌 유형 필터를 완화해 보세요.",
                        "No matching papers found. Consider broadening the publication year range or relaxing filters."
                    ))

            except Exception as e:
                if type(e).__name__ in ["StopException", "ScriptRunControlException", "RerunException"]:
                    raise e
                ui_progress_bar.empty()
                status_logger.update(label=tr("🚨 데이터 수집 중 오류 발생", "🚨 Pipeline Execution Error"), state="error", expanded=True)
                st.error(f"**{tr('오류 상세 안내 (Error Details)', 'Execution Terminated')}:** {str(e)}")
                st.session_state.df = None


# ==========================================
# 🌟 FINAL REPORT: Analytical Results, Stale-Result Guard & Validated Export Suite
# ==========================================
if st.session_state.df is not None and not st.session_state.df.empty:
    df = st.session_state.df

    render_step_banner(
        step_class="step-result",
        step_num_text="FINAL REPORT",
        title_text=tr(f"📊 최종 분석 리포트 및 결과물 다운로드 (총 {len(df)}편 추출됨)", f"📊 Final Analytical Report & Exports ({len(df)} Papers)"),
        state="warn" if is_result_stale else "done",
        status_text=tr("주의: 이전 필터 기준 결과 (재분석 클릭 필수)" if is_result_stale else "최신 필터 기준 분석 완료", "Stale Result: Click Re-run" if is_result_stale else "Matches Current Filters"),
        anchor_id="step-result-anchor"
    )

    with st.container(border=True):
        if is_result_stale:
            old_c = st.session_state.executed_config or {}
            st.markdown(f"""
            <div class="cta-attention-amber">
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                    <span style="font-size:1.1rem; font-weight:900; color:#991B1B;">
                        <span class="bounce-icon">👇</span> ⚠️ {tr('[중요 안내] 위에서 필터 설정을 변경하셨습니다! 지금 보고 계신 아래 표와 차트는 "변경 전(이전) 필터"로 분석된 결과입니다.',
                               '[Important Notice] You changed filter settings above! The results shown below are from your PREVIOUS extraction.')}
                    </span>
                    <span class="cta-amber-badge">🚨 {tr('아래 재분석 버튼 클릭 필수', 'CLICK RE-RUN BELOW')}</span>
                </div>
                <div style="font-size:0.96rem; color:#78350F; line-height:1.65; margin-bottom:6px;">
                    • <b>{tr('현재 화면에 표시된 이전 결과의 기준', 'Current Report Was Extracted With')}:</b>
                      <code>{old_c.get('formula') or '지정 학술지 전체'}</code> ({old_c.get('start_year')}–{old_c.get('end_year')}년 · {old_c.get('doc_type')} · 최대 {old_c.get('top_n')}편)<br>
                    • <b>{tr('방금 새로 변경하신 필터 항목', 'Newly Changed Filters (Not Applied Yet)')}:</b>
                      <span style="background:#FDE68A; color:#92400E; padding:3px 9px; border-radius:6px; font-weight:800;">{" / ".join(changed_filter_list)}</span><br>
                    👉 {tr('<b>새로 변경하신 필터가 반영된 결과</b>로 업데이트하시려면 바로 아래 반짝이는 파란색 버튼을 클릭해 주세요! (클릭 시 새로 분석되며 이 경고창이 사라집니다)',
                           'Click the glowing button right below to <b>re-run the analysis</b> and update the report!')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.button(
                tr("🔄 지금 여기를 클릭해 변경된 새 필터 설정으로 다시 분석 시작하기 (클릭 시 새 결과로 업데이트됩니다)", "🔄 Click Here Now to Re-Run Extraction with Updated Filters"),
                type="primary",
                on_click=cb_trigger_rerun,
                use_container_width=True
            )
            st.markdown("<hr style='margin-top:12px; margin-bottom:14px; border-top:2px dashed #F59E0B;'>", unsafe_allow_html=True)

        dl_c1, dl_c2 = st.columns(2, gap="medium")
        now_dl_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        exec_cfg_for_dl = st.session_state.executed_config or current_config
        dl_query_str = exec_cfg_for_dl.get("formula", "") or target_kw
        dl_mode_str = exec_cfg_for_dl.get("search_mode", search_mode)
        dl_cart_cnt = len(exec_cfg_for_dl.get("issns", ()))
        excel_filename = build_export_filename(
            query_str=dl_query_str,
            search_mode=dl_mode_str,
            paper_count=len(df),
            cart_count=dl_cart_cnt,
            lang=st.session_state.ui_lang,
            ext="xlsx",
            timestamp_str=now_dl_ts
        )
        ris_filename = build_export_filename(
            query_str=dl_query_str,
            search_mode=dl_mode_str,
            paper_count=len(df),
            cart_count=dl_cart_cnt,
            lang=st.session_state.ui_lang,
            ext="ris",
            timestamp_str=now_dl_ts
        )
        excel_bytes = create_excel(df)
        ris_bytes = generate_ris(df)

        with dl_c1:
            st.download_button(
                tr("📥 프로페셔널 엑셀 보고서 다운로드 (.xlsx — 소속기관·토픽·FWCI·전체 초록 포함)", "📥 Download Formatted Excel Report (.xlsx — Institutions, FWCI & Abstracts)"),
                data=excel_bytes,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with dl_c2:
            st.download_button(
                tr("📥 서지관리 프로그램 호환 파일 다운로드 (.ris — Zotero · EndNote · Mendeley)", "📥 Download Reference Manager Citations (.ris — Zotero · EndNote)"),
                data=ris_bytes,
                file_name=ris_filename,
                mime="application/x-research-info-systems",
                use_container_width=True
            )
        st.caption(
            f"🕒 {tr('자동 부여 저장 파일명 (주제·모드·편수·날짜·시간 자동 반영)', 'Auto-generated export filenames with topic, count & timestamp')}: "
            f"`{excel_filename}`  |  `{ris_filename}`"
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        is_deep_df = ("Network Hits" in df.columns)
        default_spot_n = 20 if is_deep_df else 15

        res_tab1, res_tab2 = st.tabs([
            tr(f"📊 종합 분석 대시보드 & 핵심 대표 논문 Top {default_spot_n}+ 보기", f"📊 Researcher Analytics & Top {default_spot_n}+ Spotlight"),
            tr("📑 전체 논문 데이터베이스 표 · 초록 뷰어 & 인용문 복사", "📑 Full Literature Matrix, Abstract Reader & Citation Copy")
        ])

        with res_tab1:
            oa_count = int(df['OA_Link'].notna().sum())
            oa_pct = round((oa_count / len(df)) * 100) if len(df) > 0 else 0
            mean_cites = int(df['Citations'].mean()) if len(df) > 0 else 0
            median_cites = int(df['Citations'].median()) if len(df) > 0 else 0
            mean_fwci = round(float(df['FWCI'].mean()), 2) if 'FWCI' in df.columns and len(df) > 0 else 0.0
            abs_count = int(df['Abstract'].astype(str).str.strip().replace("", pd.NA).notna().sum()) if 'Abstract' in df.columns else 0
            min_yr, max_yr = int(df['Year'].min()), int(df['Year'].max())

            r1_k1, r1_k2, r1_k3 = st.columns(3, gap="medium")
            abs_sub_txt = tr(f"초록(Abstract) 본문 수록: {abs_count}편", f"{abs_count} records with full abstract")
            median_sub_txt = tr(f"피인용 중앙값(정중앙 순위 값): {median_cites:,}회", f"Median citations (50th percentile): {median_cites:,}")
            span_sub_txt = tr(f"총 {max_yr - min_yr + 1}개년도에 걸친 핵심 문헌 포괄", f"Spans across {max_yr - min_yr + 1} publication years")

            r1_k1.markdown(
                f"<div class='metric-box'><div class='metric-value'>{len(df)}편</div>"
                f"<div class='metric-label'>📚 {tr('수집된 핵심 논문 수', 'Total Extracted Papers')}</div>"
                f"<div class='metric-sub'>{abs_sub_txt}</div></div>",
                unsafe_allow_html=True
            )
            r1_k2.markdown(
                f"<div class='metric-box'><div class='metric-value'>{oa_count}편 ({oa_pct}%)</div>"
                f"<div class='metric-label'>🔓 {tr('무료 전문 PDF(Open Access) 보유율', 'Open Access Full-Text PDF')}</div>"
                f"<div class='metric-sub'>{tr('결제·구독 없이 즉시 원문 PDF 무료 열람 가능', 'Free full-text PDF links available')}</div></div>",
                unsafe_allow_html=True
            )
            r1_k3.markdown(
                f"<div class='metric-box'><div class='metric-value'>{mean_cites:,}회</div>"
                f"<div class='metric-label'>🏆 {tr('논문 1편당 평균 총인용 횟수', 'Mean Total Citations per Paper')}</div>"
                f"<div class='metric-sub'>{median_sub_txt}</div></div>",
                unsafe_allow_html=True
            )

            r2_k1, r2_k2, r2_k3 = st.columns(3, gap="medium")
            r2_k1.markdown(
                f"<div class='metric-box'><div class='metric-value'>{mean_fwci}배 (x)</div>"
                f"<div class='metric-label'>⚖️ {tr('학문분야 보정 평균 영향력 (FWCI)', 'Mean Field-Weighted Impact (FWCI)')}</div>"
                f"<div class='metric-sub'>{tr('동일 연도·분야 세계 평균(1.0배) 대비 몇 배 인용되었는가', '1.0x equals the world average in the same field & year')}</div></div>",
                unsafe_allow_html=True
            )
            if is_deep_df:
                r2_k2.markdown(
                    f"<div class='metric-box'><div class='metric-value'>{int(df['Network Hits'].max())}회</div>"
                    f"<div class='metric-label'>🔗 {tr('최다 공통인용 횟수 (Network Hits)', 'Peak In-Network Co-citations')}</div>"
                    f"<div class='metric-sub'>{tr('내가 검색한 논문들이 참고문헌에서 함께 인용한 최고 횟수', 'Most frequently co-cited foundational root paper')}</div></div>",
                    unsafe_allow_html=True
                )
            else:
                r2_k2.markdown(
                    f"<div class='metric-box'><div class='metric-value'>{df['Velocity (Cites/Yr)'].max()}회/년</div>"
                    f"<div class='metric-label'>🔥 {tr('최고 연간 인용속도 (Citation Velocity)', 'Peak Citation Velocity')}</div>"
                    f"<div class='metric-sub'>{tr('출판 이후 1년당 평균 가장 빠르게 인용된 속도(총인용÷경과연수)', 'Highest average citations gained per year since publication')}</div></div>",
                    unsafe_allow_html=True
                )
            r2_k3.markdown(
                f"<div class='metric-box'><div class='metric-value'>{min_yr}년 – {max_yr}년</div>"
                f"<div class='metric-label'>📅 {tr('수록 논문 출판 연도 분포', 'Publication Year Span')}</div>"
                f"<div class='metric-sub'>{span_sub_txt}</div></div>",
                unsafe_allow_html=True
            )

            rep_gloss_hdr = tr(
                "📘 [리포트 학술 용어 쉬운 해설] 공통인용 · 총인용 · 피인용 중앙값 · FWCI · 인용속도 · OA · RIS가 무슨 뜻인가요? (클릭하여 열기)",
                "📘 [Report Metrics Guide] What do Network Hits, Total/Median Citations, FWCI, Velocity, OA, and RIS mean? (Click to expand)"
            )
            with st.expander(rep_gloss_hdr, expanded=False):
                render_academic_glossary_panel(lang=st.session_state.ui_lang)

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

            chart_col1, chart_col2 = st.columns(2, gap="medium")
            with chart_col1:
                st.markdown(f"#### 📅 {tr('연도별 핵심 논문 출판 추이', 'Chronological Publication Trend')}")
                year_df = (
                    df.groupby("Year", as_index=False)
                    .agg(Papers=("Title", "count"), Mean_Citations=("Citations", "mean"))
                    .sort_values("Year")
                )
                year_df["Mean_Citations"] = year_df["Mean_Citations"].round(1)
                year_chart = (
                    alt.Chart(year_df)
                    .mark_bar(color="#2563EB", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                    .encode(
                        x=alt.X("Year:O", title=tr("출판 연도 (Year)", "Publication Year"), axis=alt.Axis(labelAngle=-45, labelFontSize=12, titleFontSize=13)),
                        y=alt.Y("Papers:Q", title=tr("논문 수 (Papers)", "Number of Papers"), axis=alt.Axis(labelFontSize=12, titleFontSize=13)),
                        tooltip=[
                            alt.Tooltip("Year:O", title=tr("출판 연도 (Year)", "Year")),
                            alt.Tooltip("Papers:Q", title=tr("논문 수 (Papers)", "Papers")),
                            alt.Tooltip("Mean_Citations:Q", title=tr("평균 인용 수 (Mean Cites)", "Mean Citations"))
                        ]
                    )
                    .properties(height=260)
                )
                st.altair_chart(year_chart, use_container_width=True)

            with chart_col2:
                st.markdown(f"#### 🏛️ {tr('최다 수록 상위 10대 학술지', 'Top 10 Publishing Academic Journals')}")
                venue_df = (
                    df[df["Journal"].notna() & (df["Journal"] != "Unknown")]
                    .groupby("Journal", as_index=False)
                    .agg(Papers=("Title", "count"), Mean_Citations=("Citations", "mean"))
                    .sort_values(["Papers", "Mean_Citations"], ascending=[False, False])
                    .head(10)
                )
                venue_df["Mean_Citations"] = venue_df["Mean_Citations"].round(1)
                if not venue_df.empty:
                    venue_chart = (
                        alt.Chart(venue_df)
                        .mark_bar(color="#0D9488", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                        .encode(
                            x=alt.X("Papers:Q", title=tr("수록 논문 수 (Papers)", "Number of Papers"), axis=alt.Axis(labelFontSize=12, titleFontSize=13)),
                            y=alt.Y("Journal:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300, labelFontSize=12)),
                            tooltip=[
                                alt.Tooltip("Journal:N", title=tr("학술지 (Journal)", "Journal")),
                                alt.Tooltip("Papers:Q", title=tr("논문 수 (Papers)", "Papers")),
                                alt.Tooltip("Mean_Citations:Q", title=tr("평균 인용 수 (Mean Cites)", "Mean Citations"))
                            ]
                        )
                        .properties(height=260)
                    )
                    st.altair_chart(venue_chart, use_container_width=True)
                else:
                    st.info(tr("학술지 분포를 표시할 데이터가 부족합니다.", "Insufficient journal metadata for chart."))

            chart_col3, chart_col4 = st.columns(2, gap="medium")
            with chart_col3:
                st.markdown(f"#### 🏢 {tr('이 주제를 선도하는 상위 10대 연구 기관', 'Top 10 Leading Research Institutions')}")
                if "Institution" in df.columns:
                    inst_df = (
                        df[df["Institution"].notna() & (~df["Institution"].isin(["Unknown", "N/A", ""]))]
                        .groupby("Institution", as_index=False)
                        .agg(Papers=("Title", "count"), Mean_Citations=("Citations", "mean"))
                        .sort_values(["Papers", "Mean_Citations"], ascending=[False, False])
                        .head(10)
                    )
                    inst_df["Mean_Citations"] = inst_df["Mean_Citations"].round(1)
                    if not inst_df.empty:
                        inst_chart = (
                            alt.Chart(inst_df)
                            .mark_bar(color="#4F46E5", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                            .encode(
                                x=alt.X("Papers:Q", title=tr("논문 수 (Papers)", "Number of Papers"), axis=alt.Axis(labelFontSize=12, titleFontSize=13)),
                                y=alt.Y("Institution:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300, labelFontSize=12)),
                                tooltip=[
                                    alt.Tooltip("Institution:N", title=tr("연구 기관 (Institution)", "Institution")),
                                    alt.Tooltip("Papers:Q", title=tr("논문 수 (Papers)", "Papers")),
                                    alt.Tooltip("Mean_Citations:Q", title=tr("평균 인용 수 (Mean Cites)", "Mean Citations"))
                                ]
                            )
                            .properties(height=250)
                        )
                        st.altair_chart(inst_chart, use_container_width=True)
                    else:
                        st.info(tr("기관 정보가 수록된 논문이 부족합니다.", "Insufficient institution metadata."))

            with chart_col4:
                st.markdown(f"#### 🧭 {tr('세부 연구 토픽 분포 (상위 10대 분야)', 'Top 10 Academic Research Topics')}")
                if "Topic" in df.columns:
                    topic_df = (
                        df[df["Topic"].notna() & (~df["Topic"].isin(["General", ""]))]
                        .groupby("Topic", as_index=False)
                        .agg(Papers=("Title", "count"), Mean_Citations=("Citations", "mean"))
                        .sort_values(["Papers", "Mean_Citations"], ascending=[False, False])
                        .head(10)
                    )
                    topic_df["Mean_Citations"] = topic_df["Mean_Citations"].round(1)
                    if not topic_df.empty:
                        topic_chart = (
                            alt.Chart(topic_df)
                            .mark_bar(color="#D97706", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                            .encode(
                                x=alt.X("Papers:Q", title=tr("논문 수 (Papers)", "Number of Papers"), axis=alt.Axis(labelFontSize=12, titleFontSize=13)),
                                y=alt.Y("Topic:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300, labelFontSize=12)),
                                tooltip=[
                                    alt.Tooltip("Topic:N", title=tr("연구 토픽 (Topic)", "Topic")),
                                    alt.Tooltip("Papers:Q", title=tr("논문 수 (Papers)", "Papers")),
                                    alt.Tooltip("Mean_Citations:Q", title=tr("평균 인용 수 (Mean Cites)", "Mean Citations"))
                                ]
                            )
                            .properties(height=250)
                        )
                        st.altair_chart(topic_chart, use_container_width=True)
                    else:
                        st.info(tr("세부 토픽 분류 데이터가 부족합니다.", "Insufficient topic metadata."))

            st.markdown("<hr style='margin-top: 10px; margin-bottom: 16px; border-top: 2px solid #CBD5E1;'>", unsafe_allow_html=True)

            sp_hdr_col, sp_ctrl_col = st.columns([6.8, 3.2])
            with sp_ctrl_col:
                spot_count = st.selectbox(
                    tr("📋 대표 논문 표시 개수 선택", "📋 Number of Spotlight Papers"),
                    options=[10, 15, 20, 30, 50, 100],
                    index=2 if is_deep_df else 1,
                    format_func=lambda n: tr(f"상위 {n}편 바로 보기 (Top {n})", f"Show Top {n} Papers")
                )

            if is_deep_df:
                with sp_hdr_col:
                    deep_spot_hdr = tr(
                        f"심층 역추적 필독 뿌리(Root) 논문 Top {spot_count} (공통 인용 빈도 기준)",
                        f"Top {spot_count} Foundational Root Papers (By In-Network Co-citations)"
                    )
                    st.markdown(f"#### 🏆 {deep_spot_hdr}")
                    st.caption(tr(
                        "검색된 상위 논문들의 참고문헌에서 가장 많이 공통 인용된 이 분야의 기원(Root) 논문들입니다. 각 항목을 클릭하면 전체 초록과 원문 링크가 펼쳐집니다.",
                        "Foundational root papers most frequently co-cited across your seed literature network. Click any paper to expand its full abstract."
                    ))
                seed_denom = max(100, int((st.session_state.executed_config or {}).get("deep_max_phases", 3)) * 100)
                spotlight_df = df.sort_values(by=["Network Hits", "Citations"], ascending=[False, False]).head(spot_count)

                for _, srow in spotlight_df.iterrows():
                    hits_val = int(srow["Network Hits"])
                    share_pct = round((hits_val / seed_denom) * 100, 1)
                    fwci_val = srow.get("FWCI", 0.0)
                    header_label = (
                        f"🏅 #{int(srow['Rank'])} [{srow['Year']}] {srow['Title']} "
                        f"({tr('공통 인용', 'Net Hits')}: {hits_val}회 [{share_pct}%] | 총 {int(srow['Citations']):,}회 인용 | FWCI: {fwci_val})"
                    )
                    with st.expander(header_label, expanded=False):
                        st.markdown(
                            f"**👥 {tr('저자 (Authors)', 'Authors')}:** {srow['Authors'] or 'N/A'}  \n"
                            f"**🏢 {tr('대표 소속 기관 (Institution)', 'Institution')}:** {srow.get('Institution', 'N/A')}  \n"
                            f"**🏛️ {tr('학술지 (Journal)', 'Journal')}:** *{srow['Journal']}* ({srow['Year']}) · **📑 유형:** `{srow.get('Type', 'Article')}` · **🧭 토픽:** `{srow.get('Topic', 'General')}`"
                        )
                        link_md = []
                        if srow.get("DOI"):
                            link_md.append(f"[↗ {tr('출판사 공식 원문 페이지 열기 (DOI)', 'Open Official DOI Page')}]({srow['DOI']})")
                        if srow.get("OA_Link") and pd.notna(srow.get("OA_Link")):
                            link_md.append(f"[📄 {tr('무료 전문 PDF 열람하기 (Open Access)', 'Read Free Full-Text PDF')}]({srow['OA_Link']})")
                        if link_md:
                            st.markdown(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(link_md))
                        abs_txt = srow.get("Abstract")
                        if abs_txt and str(abs_txt).strip():
                            st.markdown(
                                f"<div style='background:#F8FAFC; padding:14px 18px; border-left:5px solid #2563EB; border-radius:10px; font-size:0.98rem; line-height:1.72; margin-top:8px; color:#0F172A;'>"
                                f"<b>📝 {tr('초록 (Abstract)', 'Abstract')}:</b><br>{abs_txt}</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.caption(tr("ℹ️ 이 논문은 OpenAlex 데이터베이스에 초록 본문이 수록되어 있지 않습니다. 위의 DOI 원문 링크를 통해 확인해 주세요.", "ℹ️ No abstract text indexed in OpenAlex for this record."))

            else:
                with sp_hdr_col:
                    ultra_spot_hdr = tr(
                        f"빠른 트렌드 스캔 대표·급상승 논문 하이라이트 (상위 {spot_count}편)",
                        f"Trend Scan Spotlight Papers (Top {spot_count})"
                    )
                    st.markdown(f"#### 🏆 {ultra_spot_hdr}")
                    st.caption(tr(
                        "전체 기간 대표 논문과 최근 3년 내 급부상한 최신 트렌드 논문을 탭으로 나누어 풍부하게 확인하실 수 있습니다.",
                        "Explore overall top-ranked papers as well as recent 3-year high-velocity breakthroughs."
                    ))

                sub_sp1, sub_sp2 = st.tabs([
                    tr(f"🏆 전체 핵심 대표 논문 Top {spot_count} (현재 정렬 기준)", f"🏆 Overall Top {spot_count} Spotlight Papers"),
                    tr("🔥 최근 3년 내 발표된 급상승 신진 논문 Top 15 (최신 브레이크스루)", "🔥 Recent 3-Year High-Velocity Breakthroughs (Top 15)")
                ])

                with sub_sp1:
                    spotlight_df = df.head(spot_count)
                    for _, srow in spotlight_df.iterrows():
                        fwci_val = srow.get("FWCI", 0.0)
                        header_label = (
                            f"🏅 #{int(srow['Rank'])} [{srow['Year']}] {srow['Title']} "
                            f"(총 {int(srow['Citations']):,}회 인용 | 연간 {srow['Velocity (Cites/Yr)']}회/년 | FWCI: {fwci_val})"
                        )
                        with st.expander(header_label, expanded=False):
                            st.markdown(
                                f"**👥 {tr('저자 (Authors)', 'Authors')}:** {srow['Authors'] or 'N/A'}  \n"
                                f"**🏢 {tr('대표 소속 기관 (Institution)', 'Institution')}:** {srow.get('Institution', 'N/A')}  \n"
                                f"**🏛️ {tr('학술지 (Journal)', 'Journal')}:** *{srow['Journal']}* ({srow['Year']}) · **📑 유형:** `{srow.get('Type', 'Article')}` · **🧭 토픽:** `{srow.get('Topic', 'General')}`"
                            )
                            link_md = []
                            if srow.get("DOI"):
                                link_md.append(f"[↗ {tr('출판사 공식 원문 페이지 열기 (DOI)', 'Open Official DOI Page')}]({srow['DOI']})")
                            if srow.get("OA_Link") and pd.notna(srow.get("OA_Link")):
                                link_md.append(f"[📄 {tr('무료 전문 PDF 열람하기 (Open Access)', 'Read Free Full-Text PDF')}]({srow['OA_Link']})")
                            if link_md:
                                st.markdown(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(link_md))
                            abs_txt = srow.get("Abstract")
                            if abs_txt and str(abs_txt).strip():
                                st.markdown(
                                    f"<div style='background:#F8FAFC; padding:14px 18px; border-left:5px solid #2563EB; border-radius:10px; font-size:0.98rem; line-height:1.72; margin-top:8px; color:#0F172A;'>"
                                    f"<b>📝 {tr('초록 (Abstract)', 'Abstract')}:</b><br>{abs_txt}</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.caption(tr("ℹ️ 이 논문은 OpenAlex 데이터베이스에 초록 본문이 수록되어 있지 않습니다. 위의 DOI 원문 링크를 통해 확인해 주세요.", "ℹ️ No abstract text indexed in OpenAlex for this record."))

                with sub_sp2:
                    recent_cutoff = get_current_year() - 3
                    recent_df = df[df["Year"] >= recent_cutoff].sort_values(by=["Velocity (Cites/Yr)", "Citations"], ascending=[False, False]).head(15)
                    if recent_df.empty:
                        st.info(tr(f"수집된 논문 중 최근 3년({recent_cutoff}년 이후) 내에 출판된 논문이 없습니다.", f"No papers published since {recent_cutoff} in the current dataset."))
                    else:
                        for idx_r, (_, srow) in enumerate(recent_df.iterrows(), 1):
                            fwci_val = srow.get("FWCI", 0.0)
                            header_label = (
                                f"🔥 [최신 급상승 #{idx_r}] [{srow['Year']}] {srow['Title']} "
                                f"(연간 {srow['Velocity (Cites/Yr)']}회/년 | 총 {int(srow['Citations']):,}회 인용 | FWCI: {fwci_val})"
                            )
                            with st.expander(header_label, expanded=False):
                                st.markdown(
                                    f"**👥 {tr('저자 (Authors)', 'Authors')}:** {srow['Authors'] or 'N/A'}  \n"
                                    f"**🏢 {tr('대표 소속 기관 (Institution)', 'Institution')}:** {srow.get('Institution', 'N/A')}  \n"
                                    f"**🏛️ {tr('학술지 (Journal)', 'Journal')}:** *{srow['Journal']}* ({srow['Year']}) · **📑 유형:** `{srow.get('Type', 'Article')}` · **🧭 토픽:** `{srow.get('Topic', 'General')}`"
                                )
                                link_md = []
                                if srow.get("DOI"):
                                    link_md.append(f"[↗ {tr('출판사 공식 원문 페이지 열기 (DOI)', 'Open Official DOI Page')}]({srow['DOI']})")
                                if srow.get("OA_Link") and pd.notna(srow.get("OA_Link")):
                                    link_md.append(f"[📄 {tr('무료 전문 PDF 열람하기 (Open Access)', 'Read Free Full-Text PDF')}]({srow['OA_Link']})")
                                if link_md:
                                    st.markdown(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(link_md))
                                abs_txt = srow.get("Abstract")
                                if abs_txt and str(abs_txt).strip():
                                    st.markdown(
                                        f"<div style='background:#F8FAFC; padding:14px 18px; border-left:5px solid #2563EB; border-radius:10px; font-size:0.98rem; line-height:1.72; margin-top:8px; color:#0F172A;'>"
                                        f"<b>📝 {tr('초록 (Abstract)', 'Abstract')}:</b><br>{abs_txt}</div>",
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.caption(tr("ℹ️ 이 논문은 OpenAlex 데이터베이스에 초록 본문이 수록되어 있지 않습니다. 위의 DOI 원문 링크를 통해 확인해 주세요.", "ℹ️ No abstract text indexed in OpenAlex for this record."))

        with res_tab2:
            col_guide_line = tr(
                "• <b>📘 표 컬럼 용어 요약:</b> <code>공통인용(Net Hits)</code>=내 검색 논문들이 함께 인용한 횟수 · <code>총 인용수(Cites)</code>=전 세계 누적 피인용 · <code>인용속도(Velocity)</code>=연간 평균 인용수(회/년) · <code>FWCI</code>=동일 연도·분야 세계 평균(1.0배) 대비 영향력 · <code>OA 상태</code>=무료 원문 PDF 여부",
                "• <b>📘 Column Metrics Summary:</b> <code>Net Hits</code>=In-network co-citations · <code>Cites</code>=Total global citations · <code>Velocity</code>=Citations per year · <code>FWCI</code>=Field-weighted impact (1.0x=World Avg) · <code>OA Status</code>=Open Access availability"
            )
            st.markdown(f"""
            <div class='guide-box'>
                <span class='guide-title'>💡 {tr('전체 논문 데이터베이스 탐색 · 초록 뷰어 · 인용문(APA/AMA/BibTeX) 원클릭 복사 안내', 'Interactive Database Matrix, Abstract Reader & Citation Generator')}</span>
                • <b>📊 {tr('컬럼 정렬 (Sort)', 'Sort Columns')}:</b> {tr('표 상단 헤더(예: <code>총 인용수</code>, <code>인용속도</code>, <code>FWCI</code>, <code>연도</code>)를 클릭하면 오름차순/내림차순으로 즉시 정렬됩니다.', 'Click any column header (e.g., <code>Cites</code>, <code>Velocity</code>, <code>FWCI</code>, <code>Year</code>) to sort ascending or descending.')}<br>
                {col_guide_line}<br>
                • <b>📋 {tr('전문 초록 및 인용문 원클릭 복사', 'Abstract & Citation Copy')}:</b> {tr('표 바로 아래에서 논문을 선택하고 <b>[📋 이 인용문 원클릭 복사하기]</b> 버튼을 누르면 버튼이 초록색(<b>✅ 클립보드에 복사 완료!</b>)으로 바뀌며 즉시 복사됩니다.', 'Click the copy button on any citation card below for instant visual confirmation (<b>✅ Copied to Clipboard!</b>).')}
            </div>
            """, unsafe_allow_html=True)

            search_table = st.text_input(
                tr("🔍 결과 내 실시간 키워드 필터링 (제목 · 저자 · 소속기관 · 학술지 · 토픽 · 초록 본문 통합 검색 — 오타 교정 제안 지원)", "🔍 Filter Results (Searches Title, Authors, Institution, Journal, Topic, and Full Abstract — With Typo Suggestions)"),
                key="local_search_input",
                placeholder=tr("✍️ 찾고 싶은 단어를 입력하거나 아래 [원클릭 자동완성 필터 버튼]을 클릭하세요...", "✍️ Type any keyword or click a quick-filter autocomplete button below...")
            )

            # 🔤 Dynamic Quick-Filter Autocomplete Chips from Top Topics & Journals in df
            quick_terms = []
            if "Topic" in df.columns:
                top_topics = [
                    str(t).strip() for t in df["Topic"].dropna().value_counts().head(3).index
                    if str(t).strip() and str(t).strip() != "General"
                ]
                quick_terms.extend(top_topics)
            if "Journal" in df.columns:
                top_jrnls = [
                    str(j).strip() for j in df["Journal"].dropna().value_counts().head(2).index
                    if str(j).strip() and str(j).strip() != "Unknown"
                ]
                for j_item in top_jrnls:
                    if j_item not in quick_terms:
                        quick_terms.append(j_item)

            if quick_terms:
                qf_hdr = tr(
                    "🏷️ 오타 걱정 없는 결과 내 주요 토픽·학술지 원클릭 자동완성 필터 (클릭 시 표가 즉시 필터링됩니다):",
                    "🏷️ One-Click Quick Filter Autocomplete from Extracted Results:"
                )
                st.markdown(f"<div style='font-size:0.88rem; font-weight:700; color:#1E40AF; margin-bottom:4px;'>{qf_hdr}</div>", unsafe_allow_html=True)
                qf_cols = st.columns(len(quick_terms) + (1 if search_table else 0), gap="small")
                for idx_qf, q_term in enumerate(quick_terms):
                    with qf_cols[idx_qf]:
                        short_q = q_term if len(q_term) <= 24 else f"{q_term[:22]}.."
                        st.button(
                            f"🔍 {short_q}",
                            key=f"btn_qf_table_{idx_qf}",
                            on_click=cb_set_table_search,
                            args=(q_term,),
                            use_container_width=True
                        )
                if search_table:
                    with qf_cols[-1]:
                        st.button(
                            tr("🔄 전체 보기 (필터 해제)", "🔄 Show All (Clear)"),
                            key="btn_qf_table_clear",
                            on_click=cb_set_table_search,
                            args=("",),
                            use_container_width=True
                        )

            filtered_full_df = df.copy()
            if search_table:
                try:
                    mask = filtered_full_df.astype(str).apply(lambda x: x.str.contains(search_table, case=False, na=False)).any(axis=1)
                except Exception:
                    mask = filtered_full_df.astype(str).apply(lambda x: x.str.contains(search_table, case=False, na=False, regex=False)).any(axis=1)
                filtered_full_df = filtered_full_df[mask]

                # 🪄 Typo / Did-You-Mean Suggestion if 0 rows match or if a known typo was entered
                if filtered_full_df.empty:
                    cand_strings = []
                    for col_name in ["Title", "Topic", "Journal", "Authors", "Institution"]:
                        if col_name in df.columns:
                            cand_strings.extend(df[col_name].dropna().astype(str).tolist())
                    closest_terms = suggest_closest_table_terms(search_table, cand_strings, limit=4)
                    typo_chk_tbl = detect_and_correct_typos(search_table)
                    if typo_chk_tbl["has_typo"] and typo_chk_tbl["corrected_text"] not in closest_terms:
                        closest_terms.insert(0, typo_chk_tbl["corrected_text"])

                    no_match_msg = tr(
                        f"⚠️ 입력하신 '{search_table}' 키워드와 일치하는 논문이 표에 없습니다.",
                        f"⚠️ No rows in the table matched '{search_table}'."
                    )
                    if closest_terms:
                        sug_sub_msg = tr(
                            "🪄 혹시 오타인가요? 현재 수집된 논문 데이터 내에 존재하는 가장 유사한 단어입니다 (클릭 시 즉시 재검색):",
                            "🪄 Did you mean one of these terms present in the extracted papers? (Click to filter):"
                        )
                        st.markdown(
                            f"<div class='typo-suggest-box'><b>{no_match_msg}</b><br><span>• {sug_sub_msg}</span></div>",
                            unsafe_allow_html=True
                        )
                        sug_cols = st.columns(len(closest_terms) + 1, gap="small")
                        for idx_sg, sg_word in enumerate(closest_terms):
                            with sug_cols[idx_sg]:
                                st.button(
                                    f"✨ '{sg_word}'(으)로 교정 검색",
                                    key=f"btn_tbl_typo_sug_{idx_sg}",
                                    on_click=cb_set_table_search,
                                    args=(sg_word,),
                                    use_container_width=True
                                )
                        with sug_cols[-1]:
                            st.button(
                                tr("🔄 검색어 지우고 전체 보기", "🔄 Clear Filter"),
                                key="btn_tbl_typo_clear",
                                on_click=cb_set_table_search,
                                args=("",),
                                use_container_width=True
                            )
                    else:
                        st.warning(no_match_msg)

            d_cols = [c for c in filtered_full_df.columns if c not in ['Abstract']]
            display_df = filtered_full_df[d_cols].copy()

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=460,
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        tr("순위", "Rank"),
                        help=tr("현재 선택한 정렬 기준에 따른 논문 순위입니다.", "Ranking order based on your selected sort metric.")
                    ),
                    "Title": st.column_config.TextColumn(
                        tr("논문 제목 (Title)", "Title"),
                        width="large",
                        help=tr("논문의 공식 영문 제목입니다.", "Official publication title.")
                    ),
                    "Authors": st.column_config.TextColumn(
                        tr("저자 (Authors)", "Authors"),
                        help=tr("논문의 주요 저자 목록입니다.", "Lead and contributing authors.")
                    ),
                    "Institution": st.column_config.TextColumn(
                        tr("대표 기관 (Institution)", "Institution"),
                        help=tr("제1저자 또는 핵심 연구진의 소속 대학·병원·연구소입니다.", "Primary affiliated university, hospital, or research institute.")
                    ),
                    "Journal": st.column_config.TextColumn(
                        tr("학술지 (Journal)", "Journal"),
                        help=tr("논문이 게재된 학술지(저널) 이름입니다.", "Academic journal or venue where the work was published.")
                    ),
                    "Year": st.column_config.NumberColumn(
                        tr("연도 (Year)", "Year"),
                        format="%d",
                        help=tr("논문이 정식 출판된 연도입니다.", "Publication year.")
                    ),
                    "Type": st.column_config.TextColumn(
                        tr("유형 (Type)", "Type"),
                        help=tr("원저(article), 종설(review), 프리프린트(preprint) 등 문헌 유형입니다.", "Document type (article, review, preprint, etc.).")
                    ),
                    "Topic": st.column_config.TextColumn(
                        tr("연구 토픽 (Topic)", "Topic"),
                        help=tr("OpenAlex 인공지능이 분류한 이 논문의 핵심 세부 학문 토픽입니다.", "Primary academic subfield/topic classified by OpenAlex.")
                    ),
                    "Network Hits": st.column_config.NumberColumn(
                        tr("공통인용 (Net Hits)", "Net Hits"),
                        help=tr("내가 검색한 최신 논문들이 참고문헌에서 이 뿌리 논문을 '공통으로 함께 인용한 횟수'입니다. 높을수록 이 주제의 핵심 기원 논문입니다.", "Number of seed papers in your search network that co-cited this foundational root paper.")
                    ),
                    "Citations": st.column_config.NumberColumn(
                        tr("총 인용수 (Cites)", "Cites"),
                        help=tr("출판 이후 전 세계 모든 학술 문헌으로부터 인용된 전체 누적 피인용 횟수입니다.", "Total global citations received since publication.")
                    ),
                    "Velocity (Cites/Yr)": st.column_config.NumberColumn(
                        tr("인용속도 (Velocity)", "Velocity"),
                        help=tr("출판 후 1년에 평균 몇 번씩 인용되고 있는지 나타내는 연간 인용 속도(총 인용수 ÷ 경과 연수)입니다. 최신 급상승 논문을 보여줍니다.", "Average citations per year since publication (Total Citations / Years elapsed).")
                    ),
                    "FWCI": st.column_config.NumberColumn(
                        "FWCI",
                        help=tr("학문분야·출판연도 보정 영향력 지수입니다. 세계 평균이 1.0배이며, 2.5라면 동일 연도·분야 평균보다 2.5배 더 인용된 우수 논문입니다.", "Field-Weighted Citation Impact (1.0 = World Average for same year & field).")
                    ),
                    "Refs": st.column_config.NumberColumn(
                        tr("참고문헌수 (Refs)", "Refs"),
                        help=tr("이 논문이 인용하고 있는 참고문헌(References)의 총 개수입니다.", "Total number of references cited by this paper.")
                    ),
                    "OA_Status": st.column_config.TextColumn(
                        tr("OA 상태", "OA Status"),
                        help=tr("오픈 액세스(Open Access, 무료 원문 공개) 여부입니다.", "Open Access availability status.")
                    ),
                    "DOI": st.column_config.LinkColumn(
                        tr("원문 링크 (DOI)", "DOI URL"),
                        display_text=tr("↗ 원문 열기", "↗ Open DOI"),
                        help=tr("출판사 공식 논문 페이지로 이동하는 영구 디지털 주소(DOI)입니다.", "Permanent Digital Object Identifier link to the publisher page.")
                    ),
                    "OA_Link": st.column_config.LinkColumn(
                        tr("무료 PDF (OA)", "Free PDF"),
                        display_text=tr("📄 PDF 열기", "📄 Read PDF"),
                        help=tr("결제 없이 무료로 전문 PDF를 열람·다운로드할 수 있는 오픈 액세스 링크입니다.", "Direct link to free Open Access full-text PDF.")
                    )
                }
            )

            if not filtered_full_df.empty:
                flt_dl_c1, flt_dl_c2 = st.columns(2, gap="small")
                flt_prefix = f"키워드필터_{search_table[:15]}" if search_table else ""
                flt_xlsx_name = build_export_filename(
                    query_str=dl_query_str,
                    search_mode=dl_mode_str,
                    paper_count=len(filtered_full_df),
                    cart_count=dl_cart_cnt,
                    lang=st.session_state.ui_lang,
                    ext="xlsx",
                    timestamp_str=now_dl_ts,
                    prefix_tag=flt_prefix
                )
                flt_csv_name = build_export_filename(
                    query_str=dl_query_str,
                    search_mode=dl_mode_str,
                    paper_count=len(filtered_full_df),
                    cart_count=dl_cart_cnt,
                    lang=st.session_state.ui_lang,
                    ext="csv",
                    timestamp_str=now_dl_ts,
                    prefix_tag=flt_prefix
                )
                with flt_dl_c1:
                    st.download_button(
                        tr(f"📥 현재 표 목록 엑셀 저장 ({len(filtered_full_df)}편 · .xlsx)", f"📥 Export Current Table ({len(filtered_full_df)} rows · .xlsx)"),
                        data=create_excel(filtered_full_df),
                        file_name=flt_xlsx_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_filtered_xlsx",
                        use_container_width=True
                    )
                with flt_dl_c2:
                    st.download_button(
                        tr(f"📥 현재 표 목록 CSV 저장 ({len(filtered_full_df)}편 · .csv)", f"📥 Export Current Table ({len(filtered_full_df)} rows · .csv)"),
                        data=filtered_full_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=flt_csv_name,
                        mime="text/csv",
                        key="dl_filtered_csv",
                        use_container_width=True
                    )

                st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
                st.markdown(f"#### 📖 {tr('논문 초록(Abstract) 상세 뷰어 & 원클릭 인용문(APA · AMA · BibTeX) 생성기', 'Interactive Abstract Reader & Instant Citation Generator')}")
                st.caption(tr(
                    "아래 드롭다운 박스를 클릭해 논문을 선택하시면 전체 초록(Abstract)과 함께 클릭 즉시 '✅ 복사 완료!' 표시가 뜨는 인용문 복사 카드가 나타납니다.",
                    "Select any manuscript below to inspect its complete abstract and copy standard citations with instant confirmation."
                ))

                paper_options = {
                    f"🏅 [#{int(r['Rank'])}] {r['Title']} ({r['Journal']}, {r['Year']} — {int(r['Citations']):,} Cites)": idx
                    for idx, r in filtered_full_df.iterrows()
                }
                selected_label = st.selectbox(
                    "Select Manuscript to Inspect",
                    options=list(paper_options.keys()),
                    label_visibility="collapsed"
                )
                if selected_label in paper_options:
                    sel_row = filtered_full_df.loc[paper_options[selected_label]]
                    net_str = (
                        f" &nbsp;|&nbsp; <b>🔗 {tr('공통 인용 (Network Hits)', 'Network Hits')}:</b> {int(sel_row['Network Hits'])}"
                        if "Network Hits" in sel_row and pd.notna(sel_row["Network Hits"]) else ""
                    )
                    doi_link = (
                        f"<a href='{sel_row['DOI']}' target='_blank' style='color:#1D4ED8; font-weight:800; text-decoration:none; background:#EFF6FF; padding:6px 12px; border-radius:8px; border:1px solid #BFDBFE;'>↗ {tr('출판사 공식 원문 페이지 이동 (Open DOI)', 'Open Publisher DOI')}</a>"
                        if sel_row.get("DOI") else ""
                    )
                    oa_link = (
                        f"<a href='{sel_row['OA_Link']}' target='_blank' style='color:#047857; font-weight:800; text-decoration:none; background:#ECFDF5; padding:6px 12px; border-radius:8px; border:1px solid #A7F3D0;'>📄 {tr('무료 전문 PDF 열기 (Read OA PDF)', 'Read Full-Text OA PDF')}</a>"
                        if sel_row.get("OA_Link") and pd.notna(sel_row.get("OA_Link")) else ""
                    )
                    links_html = " &nbsp;&nbsp; ".join([l for l in [doi_link, oa_link] if l])
                    abs_content = sel_row.get("Abstract")
                    abs_html = (
                        str(abs_content).strip()
                        if abs_content and str(abs_content).strip()
                        else f"<i>{tr('이 논문은 OpenAlex 데이터베이스에 초록 본문이 등록되어 있지 않습니다. 위의 [출판사 공식 원문 페이지 이동] 버튼을 클릭해 원문에서 확인해 주세요.', 'No abstract text is indexed in OpenAlex for this publication. Please use the DOI link above.')}</i>"
                    )

                    links_block_html = f"<div style='margin-bottom:14px; font-size:0.95rem;'>{links_html}</div>" if links_html else ""
                    st.markdown(f"""
                    <div style='background:#FFFFFF; border:1.5px solid #93C5FD; border-left:6px solid #2563EB; border-radius:14px; padding:18px 22px; box-shadow: 0 4px 14px rgba(15,23,42,0.04); word-break: keep-all; overflow-wrap: break-word; margin-bottom:14px;'>
                        <div style='font-size:1.18rem; font-weight:800; color:#0F172A; margin-bottom:8px; line-height:1.42;'>{sel_row['Title']}</div>
                        <div style='font-size:0.97rem; color:#1E293B; margin-bottom:6px;'><b>👥 {tr('저자 (Authors)', 'Authors')}:</b> {sel_row['Authors'] or 'Unknown'} &nbsp;|&nbsp; <b>🏢 {tr('대표 기관 (Institution)', 'Institution')}:</b> {sel_row.get('Institution', 'N/A')}</div>
                        <div style='font-size:0.97rem; color:#1E293B; margin-bottom:12px; line-height:1.62;'>
                            <b>🏛️ {tr('학술지 (Journal)', 'Journal')}:</b> <i>{sel_row['Journal']}</i> ({sel_row['Year']}){net_str} &nbsp;|&nbsp;
                            <b>📑 {tr('유형 (Type)', 'Type')}:</b> {sel_row.get('Type', 'Article')} &nbsp;|&nbsp;
                            <b>🧭 {tr('토픽 (Topic)', 'Topic')}:</b> {sel_row.get('Topic', 'General')} &nbsp;|&nbsp;
                            <b>🏆 {tr('총 피인용', 'Citations')}:</b> {int(sel_row['Citations']):,} &nbsp;|&nbsp;
                            <b>🔥 {tr('인용 속도', 'Velocity')}:</b> {sel_row['Velocity (Cites/Yr)']}/yr &nbsp;|&nbsp;
                            <b>⚖️ FWCI:</b> {sel_row.get('FWCI', 0.0)} &nbsp;|&nbsp;
                            <b>📚 {tr('참고문헌 수', 'References')}:</b> {int(sel_row.get('Refs', 0))}
                        </div>
                        {links_block_html}
                        <div style='background:#F8FAFC; padding:14px 18px; border-radius:10px; font-size:0.98rem; color:#0F172A; line-height:1.72; border:1.5px solid #CBD5E1;'>
                            <b>📝 {tr('논문 초록 (Abstract)', 'Abstract')}:</b><br>{abs_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(
                        f"<div style='font-size:1.02rem; font-weight:800; color:#0F172A; margin-bottom:6px;'>"
                        f"📋 {tr('표준 학술 인용 양식 원클릭 복사 (아래 [📋 이 인용문 원클릭 복사하기] 버튼을 누르면 즉시 [✅ 복사 완료!]로 바뀝니다!)', 'One-Click Standard Citation Copy (Click the button inside any card for instant copy confirmation!)')}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    cites_dict = format_citations_for_paper(sel_row)
                    render_interactive_citations(cites_dict, lang=st.session_state.ui_lang)

                    cite_dl_c1, cite_dl_c2 = st.columns(2, gap="small")
                    paper_title_short = str(sel_row.get("Title", "Paper"))[:30]
                    cite_txt_name = build_export_filename(
                        query_str=paper_title_short,
                        search_mode="CITATION",
                        paper_count=1,
                        cart_count=0,
                        lang=st.session_state.ui_lang,
                        ext="txt",
                        timestamp_str=now_dl_ts,
                        prefix_tag=f"Rank{int(sel_row.get('Rank', 1))}"
                    )
                    cite_bib_name = build_export_filename(
                        query_str=paper_title_short,
                        search_mode="BIBTEX",
                        paper_count=1,
                        cart_count=0,
                        lang=st.session_state.ui_lang,
                        ext="bib",
                        timestamp_str=now_dl_ts,
                        prefix_tag=f"Rank{int(sel_row.get('Rank', 1))}"
                    )
                    nl_sep = "\n\n"
                    cite_txt_body = (
                        f"Title: {sel_row.get('Title', '')}\n"
                        f"Authors: {sel_row.get('Authors', '')}\n"
                        f"Journal: {sel_row.get('Journal', '')} ({sel_row.get('Year', '')})\n"
                        f"DOI: {sel_row.get('DOI', '')}\n\n"
                        f"[APA 7th]\n{cites_dict.get('apa', '')}\n\n"
                        f"[AMA / Vancouver]\n{cites_dict.get('ama', '')}\n\n"
                        f"[BibTeX]\n{cites_dict.get('bibtex', '')}\n\n"
                        f"[Abstract]\n{sel_row.get('Abstract', '')}"
                    )
                    with cite_dl_c1:
                        st.download_button(
                            tr("📥 선택한 논문 초록·인용문 통합 텍스트 저장 (.txt)", "📥 Download Selected Paper Abstract & Citations (.txt)"),
                            data=cite_txt_body.encode("utf-8"),
                            file_name=cite_txt_name,
                            mime="text/plain",
                            key="dl_single_cite_txt",
                            use_container_width=True
                        )
                    with cite_dl_c2:
                        st.download_button(
                            tr("📥 선택한 논문 BibTeX 서지 파일 저장 (.bib)", "📥 Download Selected Paper BibTeX (.bib)"),
                            data=cites_dict.get("bibtex", "").encode("utf-8"),
                            file_name=cite_bib_name,
                            mime="text/plain",
                            key="dl_single_cite_bib",
                            use_container_width=True
                        )


# ==========================================
# 🔄 Persistent Session Snapshot & Smooth Auto-Scroll / Keepalive Heartbeat
# ==========================================
save_session_snapshot()
render_auto_scroll_and_keepalive(
    target_anchor=st.session_state.get("scroll_target_anchor", ""),
    scroll_seq=st.session_state.get("scroll_seq", 0),
    auth_token=get_expected_auth_token() if st.session_state.get("authenticated") else "",
    sid=st.session_state.get("session_sid", "")
)
st.session_state.scroll_target_anchor = ""
