import streamlit as st
import os
import sys

st.set_page_config(
    page_title="OmniScholar | 상세 사용 매뉴얼 (User Manual)",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.ui_components import apply_custom_css
apply_custom_css()

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "KO_EN"

def toggle_language():
    st.session_state.ui_lang = "EN" if st.session_state.ui_lang == "KO_EN" else "KO_EN"

def tr(ko_en_text, en_text):
    return en_text if st.session_state.ui_lang == "EN" else ko_en_text

st.markdown(f"""
<div class="top-navbar">
    <div class="brand-logo-wrap">
        <div class="brand-icon">OS</div>
        <div>
            <div class="brand-title">OmniScholar <span style="font-weight:500; font-size:0.95rem; color:#475569;">| {tr('상세 사용 매뉴얼 (Comprehensive User Manual)', 'Comprehensive User Manual')}</span></div>
            <div class="brand-subtitle">{tr('자연어 검색 · 불리언 문법 · 탐색 알고리즘 · 엑셀 및 RIS 리포트 활용 가이드', 'Natural Language Search · Boolean Logic · Exploration Algorithms · Export Guide')}</div>
        </div>
    </div>
    <div>
        <a href="./" target="_self" style="display:inline-block; background:#1E40AF; color:#FFFFFF; padding:8px 16px; border-radius:9px; font-weight:700; font-size:0.86rem; text-decoration:none;">
            ← {tr('메인 워크스페이스로 돌아가기 (Back to Workspace)', 'Back to Main Workspace')}
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

_, lang_col = st.columns([7.5, 2.5])
with lang_col:
    st.button(
        "🌐 Language: 🇰🇷 한국어 + English" if st.session_state.ui_lang == "KO_EN" else "🌐 Language: 🇺🇸 English Only",
        on_click=toggle_language,
        use_container_width=True
    )

with st.container(border=True):
    if st.session_state.ui_lang == "KO_EN":
        st.markdown("""
        ### 01. 스마트 자연어 검색 & 사전 필터(Pre-filter) 작동 원리
        **OmniScholar**의 `STEP 01` 검색창은 **자연어 문장(한국어·영어)**과 **전문 불리언(Boolean) 검색식**을 모두 완벽하게 지원합니다.
        - **한국어 자연어 입력:** `"뇌졸중 환자의 연하장애와 흡인성 폐렴을 머신러닝으로 예측하는 연구 찾아줘"`라고 입력하면, 내장된 학술 시소러스와 스마트 변환기가 불필요한 서술어를 제거하고 `stroke (dysphagia OR swallowing) "aspiration pneumonia" "machine learning"` 형태의 최적 영문 학술 검색식으로 자동 변환합니다.
        - **영어 자연어 질문 입력:** `"What is the role of large language models in clinical decision support?"`라고 입력하면 핵심 학술 개념어인 `"large language models" "clinical decision support"`를 자동 추출합니다.
        - **데이터베이스 직결 스캔:** 변환된 검색식은 전 세계 **2억 5천만 편 이상의 학술 데이터베이스(OpenAlex)**에 직접 주입되어 수억 편 논문의 **제목(Title)과 초록(Abstract)**을 실시간으로 정밀 스캔합니다.

        ---

        ### 02. 정밀 검색어 연산자 조합 가이드 (Boolean Search Syntax)
        직접 정밀한 검색식을 작성하고 싶으실 때는 아래 5가지 규칙을 조합하여 사용할 수 있습니다.

        | 연산자 (Syntax) | 논리 의미 (Logic) | 입력 예시 (Example) | 작동 방식 (Description) |
        | :--- | :--- | :--- | :--- |
        | **띄어쓰기 (Space)** | **그리고 (AND)** | `stroke dysphagia` | 두 단어가 **모두 포함된** 논문만 추출합니다. |
        | **대문자 `OR`** | **또는 (OR)** | `dysphagia OR swallowing` | 동의어나 유사 개념 중 **하나라도 포함된** 논문을 모두 추출합니다. |
        | **큰따옴표 `" "`** | **정확한 구문 일치** | `"aspiration pneumonia"` | 단어가 흩어지지 않고 **정확히 순서대로 이어진 구문**만 추출합니다. |
        | **마이너스 `-`** | **특정 단어 제외 (NOT)** | `stroke -pediatric -animal` | 소아(`pediatric`)나 동물 실험(`animal`) 논문을 **제외**합니다. |
        | **소괄호 `( )`** | **우선순위 그룹화** | `(VFSS OR FEES) stroke` | 괄호 안의 `OR` 조건을 먼저 묶어 정확하게 연산합니다. |

        ---

        ### 03. 두 가지 탐색 알고리즘 완벽 비교 (`STEP 02`)

        #### A. 빠른 트렌드 스캔 (`Ultra-fast Scan — Trend Analysis`)
        - **목적:** 특정 연구 주제에서 **가장 많이 인용된 대표 논문과 최신 급상승 트렌드 논문**을 수 초 내에 빠르게 확보할 때 사용합니다.
        - **핵심 지표 (`연간 인용 속도 Velocity`):** 총 피인용 수를 출판 경과 연수로 나눈 값(`Citations / Year`)으로, 출판된 지 얼마 되지 않았더라도 학계에서 폭발적으로 인용되고 있는 최신 논문을 즉시 식별할 수 있습니다.

        #### B. 심층 뿌리 논문 역추적 (`Deep Network — Foundational Roots`)
        - **목적:** 연구 분야의 서론(Introduction)을 작성하거나 문헌 고찰을 수행할 때, **해당 분야 연구자들이 공통으로 가장 많이 인용하는 역사적 근본(Root/Cornerstone) 논문**을 발굴할 때 사용합니다.
        - **작동 메커니즘:** 1차로 검색된 상위 논문들의 **참고문헌(References) 수만 건을 전수 역추적**한 뒤, 네트워크 내에서 **동시에 가장 많이 인용된 횟수(`공통 인용 Network Hits`)**를 기준으로 1순위부터 정렬하여 복원합니다.

        ---

        ### 04. 검증된 결과물 확인 및 보고서 다운로드 (`STEP 04`)
        - **프로페셔널 엑셀 보고서 (`.xlsx`):** 헤더 디자인, 1행 틀 고정, 자동 필터, 열 너비 자동 맞춤, DOI/PDF 클릭 하이퍼링크, **전체 초록(Abstract) 자동 줄바꿈**까지 완벽하게 서식이 적용된 엑셀 파일로 다운로드됩니다.
        - **국제 표준 서지 파일 (`.ris`):** **Zotero, EndNote, Mendeley** 등 서지관리 프로그램에 즉시 불러올 수 있으며, 노트(Notes) 필드에 피인용 횟수·인용 속도·공통 인용 지표가 함께 기록됩니다.
        """)
    else:
        st.markdown("""
        ### 01. Smart Natural Language & Database Pre-filtering
        The search bar in `STEP 01` seamlessly supports both **natural language sentences (English or Korean)** and **explicit Boolean search expressions**.
        - **Natural Language Questions:** Typing `"What is the role of large language models in clinical decision support?"` automatically strips conversational stopwords and extracts `"large language models" "clinical decision support"`.
        - **Database-Level Execution:** Queries are injected directly into the **OpenAlex global database (250M+ works)** to scan paper **Titles and Abstracts** prior to extraction.

        ---

        ### 02. Boolean Search Syntax Reference

        | Syntax | Logic | Example | Description |
        | :--- | :--- | :--- | :--- |
        | **Space** | **AND** | `stroke dysphagia` | Retrieves papers containing **both** terms. |
        | **Capital `OR`** | **OR** | `dysphagia OR swallowing` | Retrieves papers containing **either** synonym. |
        | **Quotes `" "`** | **Exact Phrase** | `"aspiration pneumonia"` | Enforces exact sequential phrase matching. |
        | **Minus `-`** | **NOT (Exclude)** | `stroke -pediatric -animal` | Excludes papers mentioning `pediatric` or `animal`. |
        | **Parentheses `( )`** | **Grouping** | `(VFSS OR FEES) stroke` | Defines logical operator hierarchy clearly. |

        ---

        ### 03. Exploration Algorithms (`STEP 02`)
        - **Ultra-fast Scan (`Trend Analysis`):** Directly retrieves top-cited papers matching your query and computes **Citation Velocity (`Citations / Year`)** to highlight rapidly rising contemporary works.
        - **Deep Network (`Foundational Roots`):** Scans tens of thousands of references cited by your matched literature to isolate timeless foundational papers ranked by **In-Network Co-citations (`Network Hits`)**.

        ---

        ### 04. Verified Exports (`STEP 04`)
        - **Formatted Excel Report (`.xlsx`):** Includes styled headers, frozen top row, auto-filters, clickable DOI/OA hyperlinks, optimal column widths, and full abstracts.
        - **Standard RIS File (`.ris`):** Ready for one-click import into Zotero, EndNote, and Mendeley.
        """)
