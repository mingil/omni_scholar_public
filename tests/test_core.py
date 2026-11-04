import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import responses
import requests
from unittest.mock import patch
import pandas as pd
from modules.data_fetcher import robust_get, extract_abstract, parse_work_metadata, run_data_pipeline, RateLimitException
from modules.query_optimizer import (
    optimize_search_query,
    detect_and_correct_typos,
    get_autocomplete_suggestions,
    suggest_closest_table_terms,
    ACADEMIC_AUTOCOMPLETE_CATALOG,
    JOURNAL_SEARCH_SUGGESTIONS,
)
from modules.export_utils import create_excel, generate_ris, format_citations_for_paper, build_export_filename
from modules.ui_components import render_journal_html

# ==========================================
# 1. 극한의 네트워크 환경 방어력 테스트 (robust_get)
# ==========================================
@responses.activate
def test_robust_get_success():
    """✅ 정상 응답 시 파이썬이 데이터를 즉시 잘 반환하는지 테스트"""
    responses.add(responses.GET, "https://api.test.com", json={"status": "ok"}, status=200)

    with requests.Session() as session:
        res = robust_get(session, "https://api.test.com", params=None, headers={})
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

@responses.activate
@patch("time.sleep", return_value=None)
def test_robust_get_429_recovery(mock_sleep):
    """✅ 429 에러가 났을 때 지수 백오프(대기) 후 정상 복구되는지 테스트"""
    # 가짜 서버가 처음엔 429 에러, 2번째에 200 정상 응답을 주도록 조작
    responses.add(responses.GET, "https://api.test.com", status=429)
    responses.add(responses.GET, "https://api.test.com", json={"status": "recovered"}, status=200)

    with requests.Session() as session:
        res = robust_get(session, "https://api.test.com", params=None, headers={}, max_retries=1)
        assert res.status_code == 200
        assert res.json() == {"status": "recovered"}
        # time.sleep이 실제로 호출되어 대기 로직이 작동했는지 검증
        mock_sleep.assert_called_once()

@responses.activate
@patch("time.sleep", return_value=None)
def test_robust_get_429_fail(mock_sleep):
    """🚨 429 에러가 끝내 안 풀리면 무한 대기(Hang)하지 않고 최종 예외를 던지는지 테스트"""
    responses.add(responses.GET, "https://api.test.com", status=429)
    responses.add(responses.GET, "https://api.test.com", status=429)
    responses.add(responses.GET, "https://api.test.com", status=429)

    with requests.Session() as session:
        with pytest.raises(RateLimitException):
            robust_get(session, "https://api.test.com", params=None, headers={}, max_retries=2)

# ==========================================
# 2. 데이터 파싱 내구성 테스트 (이상한 쓰레기 데이터 유입 방어)
# ==========================================
def test_extract_abstract_corrupted():
    """✅ OpenAlex API가 초록(Abstract) 데이터를 깨진 형태로 줬을 때 뻗지 않는지 테스트"""
    normal_idx = {"Hello": [0], "World": [1]}
    assert extract_abstract(normal_idx) == "Hello World"

    assert extract_abstract(None) == "" # 빈 데이터 방어

    # 딕셔너리가 아닌 리스트 등 형식이 완전히 깨진 데이터 방어
    corrupted_idx = ["this", "is", "wrong", "format"]
    assert extract_abstract(corrupted_idx) == ""

def test_parse_work_metadata_missing():
    """✅ 논문 메타데이터 중 제목이나 연도가 통째로 누락되었을 때의 방어 테스트"""
    bad_data = {
        "title": None,
        "publication_year": None,
        "cited_by_count": None
    }
    result = parse_work_metadata(bad_data)

    # 에러가 나지 않고 우리가 설정한 기본값(Fallback)으로 잘 메워졌는지 확인
    assert result["Title"] == "No Title"
    assert result["Citations"] == 0
    assert result["Year"] >= 2024


# ==========================================
# 3. 페이지네이션 오프셋 및 조기 종료(Early Exit) 최적화 테스트
# ==========================================
@responses.activate
def test_ultra_fast_pagination_and_early_exit():
    """✅ top_n=150 요청 시 2페이지에서도 per-page=100을 유지하여 51~100번 중복 누락 없이 정확히 150개를 수집하는지 테스트"""
    page1_works = [{"title": f"Paper {i}", "doi": f"10.1000/{i}", "cited_by_count": 1000 - i, "publication_year": 2025} for i in range(1, 101)]
    page2_works = [{"title": f"Paper {i}", "doi": f"10.1000/{i}", "cited_by_count": 1000 - i, "publication_year": 2025} for i in range(101, 161)]

    responses.add(responses.GET, "https://api.openalex.org/works", json={"meta": {"count": 160}, "results": page1_works}, status=200)
    responses.add(responses.GET, "https://api.openalex.org/works", json={"meta": {"count": 160}, "results": page2_works}, status=200)

    df = run_data_pipeline(
        issns=("0028-4793",),
        start_yr=2020,
        end_yr=2026,
        top_n=150,
        mode="⚡ Ultra-fast Scan (Trend Analysis)",
        kw="stroke",
        min_cites=0,
        oa_only=False,
        status_logger=None,
        prog_bar=None
    )

    assert len(df) == 150
    assert len(responses.calls) == 2
    assert "per-page=100" in responses.calls[1].request.url


@responses.activate
def test_deep_network_hits_and_sorting():
    """✅ Deep Network 모드에서 공통 인용 빈도(Network Hits)가 정확히 계산되고 1순위로 정렬되는지 테스트"""
    phase1_works = [
        {"referenced_works": ["https://openalex.org/W100", "https://openalex.org/W200"]},
        {"referenced_works": ["https://openalex.org/W100", "https://openalex.org/W300"]},
        {"referenced_works": ["https://openalex.org/W100", "https://openalex.org/W200"]},
    ]
    restored_works = [
        {"id": "https://openalex.org/W200", "title": "Root Paper B", "doi": "10.1000/b", "cited_by_count": 5000, "publication_year": 2018},
        {"id": "https://openalex.org/W100", "title": "Root Paper A", "doi": "10.1000/a", "cited_by_count": 1200, "publication_year": 2019},
        {"id": "https://openalex.org/W300", "title": "Root Paper C", "doi": "10.1000/c", "cited_by_count": 9000, "publication_year": 2015},
    ]

    responses.add(responses.GET, "https://api.openalex.org/works", json={"meta": {"count": 3}, "results": phase1_works}, status=200)
    responses.add(responses.GET, "https://api.openalex.org/works", json={"results": restored_works}, status=200)

    df = run_data_pipeline(
        issns=("0028-4793",),
        start_yr=2020,
        end_yr=2026,
        top_n=50,
        mode="🧠 Deep Network (Foundational Roots)",
        kw="stroke",
        min_cites=0,
        oa_only=False,
        status_logger=None,
        prog_bar=None
    )

    assert "Network Hits" in df.columns
    assert list(df["Title"]) == ["Root Paper A", "Root Paper B", "Root Paper C"]
    assert list(df["Network Hits"]) == [3, 2, 1]


# ==========================================
# 4. 자연어 문장(한글/영문) 스마트 쿼리 변환기 테스트
# ==========================================
def test_smart_query_optimizer_korean_and_english_nl():
    """✅ 한국어 자연어 문장, 영어 자연어 질문, 정밀 불리언 수식이 각각 최적의 학술 검색식으로 변환되는지 테스트"""
    # 1. 한국어 자연어 문장
    res_ko = optimize_search_query("뇌졸중 환자의 연하장애와 흡인성 폐렴을 머신러닝으로 예측하는 연구 찾아줘")
    assert res_ko["was_modified"] is True
    assert "stroke" in res_ko["optimized"]
    assert "(dysphagia OR swallowing)" in res_ko["optimized"]
    assert '"aspiration pneumonia"' in res_ko["optimized"]
    assert '"machine learning"' in res_ko["optimized"]

    # 2. 영어 자연어 질문 문장
    res_en = optimize_search_query("What is the role of large language models in clinical decision support?")
    assert res_en["was_modified"] is True
    assert '"large language models"' in res_en["optimized"]
    assert '"clinical decision support"' in res_en["optimized"]
    assert "what" not in res_en["optimized"].lower()

    # 3. 사용자가 직접 작성한 정밀 불리언 수식은 훼손 없이 그대로 보존
    exact_q = '"machine learning" (stroke OR dysphagia) -pediatric'
    res_bool = optimize_search_query(exact_q)
    assert res_bool["was_modified"] is False
    assert res_bool["optimized"] == exact_q


# ==========================================
# 5. 엑셀(.xlsx) 및 RIS(.ris) 결과물 무결성 검증 테스트
# ==========================================
def test_export_excel_and_ris_integrity():
    """✅ 추출된 논문 데이터프레임이 오류 없이 프로페셔널 엑셀(.xlsx)과 표준 RIS(.ris) 포맷으로 변환되는지 검증"""
    sample_df = pd.DataFrame([
        {
            "Rank": 1,
            "Title": "Deep Learning in Stroke Dysphagia",
            "Authors": "Kim, J., Lee, S.",
            "Journal": "Stroke",
            "Year": 2025,
            "Network Hits": 12,
            "Citations": 85,
            "Velocity (Cites/Yr)": 42.5,
            "OA_Link": "https://example.org/paper1.pdf",
            "DOI": "https://doi.org/10.1000/stroke.1",
            "Abstract": "This study investigates deep learning for dysphagia."
        }
    ])

    excel_bytes = create_excel(sample_df)
    assert excel_bytes is not None
    assert len(excel_bytes) > 1000

    ris_bytes = generate_ris(sample_df)
    ris_text = ris_bytes.decode("utf-8-sig")
    assert "TY  - JOUR" in ris_text
    assert "TI  - Deep Learning in Stroke Dysphagia" in ris_text
    assert "DO  - 10.1000/stroke.1" in ris_text
    assert "In-Network Co-citations: 12" in ris_text
    assert "ER  - " in ris_text

    cites = format_citations_for_paper(sample_df.iloc[0])
    assert "Kim, J., Lee, S." in cites["apa"]
    assert "Deep Learning in Stroke Dysphagia" in cites["ama"]
    assert "@article{" in cites["bibtex"]


# ==========================================
# 6. Python 3.11 & 3.12 호환성 (f-string 백슬래시/중첩 방지) 테스트
# ==========================================
def test_python_fstring_cross_version_compatibility():
    """✅ 모든 파이썬 소스 파일에 Python 3.11 이하에서 SyntaxError를 유발하는 f-string 내부 백슬래시(\\)나 중첩 f-string이 없는지 AST로 전수 검사"""
    import ast
    import glob

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    py_files = sorted(glob.glob(os.path.join(project_root, "**", "*.py"), recursive=True))
    assert len(py_files) > 0

    issues = []
    for fpath in py_files:
        with open(fpath, "r", encoding="utf-8") as fp:
            src = fp.read()
        tree = ast.parse(src, filename=fpath)
        for node in ast.walk(tree):
            if isinstance(node, ast.FormattedValue):
                seg = ast.get_source_segment(src, node)
                if seg and "\\" in seg:
                    issues.append(f"Backslash in f-string at {os.path.relpath(fpath, project_root)}:{node.lineno}")
                for child in ast.walk(node.value):
                    if isinstance(child, ast.JoinedStr):
                        issues.append(f"Nested f-string at {os.path.relpath(fpath, project_root)}:{node.lineno}")

    assert issues == [], f"Found Python <3.12 incompatible f-strings: {issues}"


def test_config_no_secrets_file_safe():
    """✅ .env 및 secrets.toml이 전혀 없는 초기 도커 컨테이너 환경에서도 st.secrets 경고가 발생하지 않고 기본값("")을 안전하게 반환하는지 테스트"""
    from modules.config import _get_setting
    assert _get_setting("NON_EXISTENT_ENV_VAR_FOR_TEST", "fallback_val") == "fallback_val"


def test_build_export_filename_with_timestamp_and_context():
    """✅ 다운로드 파일명에 검색 모드, 연구 주제, 논문 수, 날짜·시간(YYYYMMDD_HHMMSS)이 정확히 포함되는지 검증"""
    fn_ko = build_export_filename(
        query_str='"dysphagia" AND (stroke OR rehabilitation)',
        search_mode="⚡ Ultra-fast Scan (Trend Analysis)",
        paper_count=150,
        cart_count=0,
        lang="KO_EN",
        ext="xlsx",
        timestamp_str="20261104_125000"
    )
    assert fn_ko.startswith("OmniScholar_트렌드스캔_")
    assert "dysphagia" in fn_ko
    assert "150편" in fn_ko
    assert "20261104_125000.xlsx" in fn_ko

    fn_deep = build_export_filename(
        query_str="",
        search_mode="🧠 Deep Network (Foundational Roots)",
        paper_count=85,
        cart_count=3,
        lang="EN_ONLY",
        ext="ris",
        timestamp_str="20261104_125000",
        prefix_tag="Filtered"
    )
    assert "RootNetwork" in fn_deep
    assert "3Journals" in fn_deep
    assert "85papers" in fn_deep
    assert "Filtered" in fn_deep
    assert fn_deep.endswith("_20261104_125000.ris")


def test_websocket_ping_and_sessioninfo_stability():
    """✅ Tornado 6.4.x 고정 및 Streamlit WebSocket 핑 타임아웃(20s/60s)·SessionInfo 방어 패치가 정상 적용되는지 검증"""
    import glob
    import tornado
    import streamlit
    import streamlit.web.server.server as st_server
    from patch_streamlit_runtime import apply_streamlit_patches

    apply_streamlit_patches()
    import importlib
    importlib.reload(st_server)

    # 1. Verify Tornado version does not clamp ping_timeout to 1s
    major_minor = tuple(int(x) for x in tornado.version.split(".")[:2])
    assert major_minor < (6, 5), f"Tornado {tornado.version} clamps ping_timeout to 1s; must be < 6.5"

    # 2. Verify Streamlit TORNADO_SETTINGS has relaxed ping_interval (20s) and ping_timeout (60s)
    assert st_server.TORNADO_SETTINGS["websocket_ping_interval"] >= 20
    assert st_server.TORNADO_SETTINGS["websocket_ping_timeout"] >= 60

    # 3. Verify static JS bundle no longer throws 'Tried to use SessionInfo before it was initialized'
    st_dir = os.path.dirname(streamlit.__file__)
    js_files = glob.glob(os.path.join(st_dir, "static", "static", "js", "main.*.js"))
    assert len(js_files) > 0
    for jpath in js_files:
        with open(jpath, "r", encoding="utf-8", errors="ignore") as fp:
            js_src = fp.read()
        assert 'throw new Error("Tried to use SessionInfo before it was initialized")' not in js_src


def test_typo_detection_and_autocorrection():
    """✅ 한국어·영어 학술 검색어 오타 자동 감지 및 교정, 자동완성 추천, 표 내부 유사어 제안 기능 검증"""
    # 1. 한국어 오타 자동 교정 (뇌졸증 -> 뇌졸중, 연하장해 -> 연하장애, 머신러님 -> 머신러닝)
    ko_typo = detect_and_correct_typos("뇌졸증 환자의 연하장해와 머신러님 예측")
    assert ko_typo["has_typo"] is True
    assert "뇌졸중" in ko_typo["corrected_text"]
    assert "연하장애" in ko_typo["corrected_text"]
    assert "머신러닝" in ko_typo["corrected_text"]

    # optimize_search_query와 결합 시 오타가 있어도 완벽한 영문 학술 검색식으로 변환되는지 검증
    opt_ko = optimize_search_query("뇌졸증 환자의 연하장해와 흡입성 폐렴을 머신러님으로 예측")
    assert opt_ko["typo_corrected"] is True
    assert "stroke" in opt_ko["optimized"]
    assert "dysphagia" in opt_ko["optimized"]
    assert '"aspiration pneumonia"' in opt_ko["optimized"]
    assert '"machine learning"' in opt_ko["optimized"]

    # 2. 영어 오타 자동 교정 (dyspagia -> dysphagia, rehabilitaion -> rehabilitation)
    en_typo = detect_and_correct_typos("stroke dyspagia rehabilitaion")
    assert en_typo["has_typo"] is True
    assert "dysphagia" in en_typo["corrected_text"].lower()
    assert "rehabilitation" in en_typo["corrected_text"].lower()

    # 3. 자동완성 추천 (get_autocomplete_suggestions)
    ac_ko = get_autocomplete_suggestions("뇌졸중", limit=5)
    assert len(ac_ko) > 0
    assert any("stroke" in item["en"].lower() for item in ac_ko)

    ac_en = get_autocomplete_suggestions("dysph", limit=5)
    assert len(ac_en) > 0
    assert any("dysphagia" in item["en"].lower() for item in ac_en)

    # 4. 표 내부 검색 0건 시 유사 단어 제안 (suggest_closest_table_terms)
    table_candidates = [
        "Deep Learning in Stroke Dysphagia Rehabilitation",
        "Aspiration Pneumonia in Post-Stroke Patients",
        "Journal of NeuroEngineering and Rehabilitation",
    ]
    closest = suggest_closest_table_terms("dyspagia", table_candidates, limit=3)
    assert "dysphagia" in [c.lower() for c in closest]

    assert len(ACADEMIC_AUTOCOMPLETE_CATALOG) >= 25
    assert len(JOURNAL_SEARCH_SUGGESTIONS) >= 8


def test_journal_html_and_terminology_tooltips():
    """✅ 학술지 배지 HTML에 2년 인용지수(2Yr-IF), 학술 영향력(H-index), ISSN 고유번호 설명 및 툴팁이 포함되는지 검증"""
    sample_info = {
        "name": "Stroke",
        "issn": "0039-2499",
        "if_2yr": 8.4,
        "h_index": 310,
        "pub": "American Heart Association",
        "works": 45000,
    }
    html_ko = render_journal_html(sample_info, lang="KO_EN")
    assert "2년 인용지수(2Yr-IF" in html_ko
    assert "학술 영향력(H-index" in html_ko
    assert "ISSN 고유번호: 0039-2499" in html_ko
    assert "title=" in html_ko





