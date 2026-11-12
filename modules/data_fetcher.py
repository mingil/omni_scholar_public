import requests
from requests.adapters import HTTPAdapter
import pandas as pd
from collections import Counter
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from modules.logger_setup import logger
from modules.config import OPENALEX_EMAIL, OPENALEX_API_KEY, get_current_year
from modules.query_optimizer import optimize_search_query
from modules import jcr_lookup
from requests.exceptions import Timeout, ReadTimeout

class RateLimitException(Exception):
    pass

def get_headers():
    headers = {}
    if OPENALEX_EMAIL:
        headers["User-Agent"] = f"mailto:{OPENALEX_EMAIL}"
    return headers

def robust_get(session, url, params, headers, timeout=(10, 25), max_retries=3):
    req_params = params.copy() if params else {}

    if OPENALEX_API_KEY:
        req_params["api_key"] = OPENALEX_API_KEY

    for attempt in range(max_retries + 1):
        try:
            res = session.get(url, params=req_params, headers=headers, timeout=timeout)

            if res.status_code == 429:
                if attempt < max_retries:
                    sleep_sec = 2 ** attempt
                    logger.warning(f"[API_429] Rate Limit Hit. Waiting {sleep_sec}s before retry... ({attempt+1}/{max_retries})")
                    time.sleep(sleep_sec)
                    continue
                else:
                    raise RateLimitException()

            if res.status_code in [500, 502, 503, 504]:
                if attempt < max_retries:
                    logger.warning(f"[API_SERVER_ERROR] {res.status_code}. Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                    continue

            res.raise_for_status()
            return res

        except (Timeout, ReadTimeout):
            if attempt == max_retries:
                logger.warning("[API_TIMEOUT] Server response delayed. Aborting request.")
                raise Exception("🚨 OpenAlex Server Timeout. The request is too heavy or the server is congested.")
            logger.warning(f"[API_TIMEOUT] Timeout occurred. Retrying ({attempt+1}/{max_retries})...")
            time.sleep(2)
        except RateLimitException:
            raise
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"[API_ERROR] Communication failure: {e}")
                if str(e).startswith("🚨"):
                    raise e
                raise Exception(f"🚨 Network communication error: {str(e)}")
            logger.warning(f"[API_ERROR] Connection error. Retrying ({attempt+1}/{max_retries})...")
            time.sleep(2)
    return None

def extract_abstract(abs_idx):
    if not abs_idx or not isinstance(abs_idx, dict):
        return ""
    try:
        positions = [max(pos) for pos in abs_idx.values() if pos]
        if not positions:
            return ""
        words = [""] * (max(positions) + 1)
        for w, p_list in abs_idx.items():
            for p in p_list:
                words[p] = w
        return " ".join(words).strip()
    except Exception:
        return ""

def parse_journal_data(r):
    stats = r.get("summary_stats")
    if not isinstance(stats, dict):
        stats = {}
    return {
        "name": r.get("display_name") or "Unknown Journal",
        "issn": r.get("issn_l") or "",
        "pub": r.get("host_organization_name") or "Unknown Publisher",
        "h_index": stats.get("h_index") or 0,
        "if_2yr": round(float(stats.get("2yr_mean_citedness") or 0.0), 2),
        "works": r.get("works_count") or 0,
        # (선택) 내 서버의 JCR 조회 창구가 설정된 경우에만 공식 JIF·분위
        "jcr": (jcr_lookup.lookup_many([(",".join(r.get("issn") or [r.get("issn_l") or ""]), r.get("display_name") or "")]).get((",".join(r.get("issn") or [r.get("issn_l") or ""]), r.get("display_name") or "")) if jcr_lookup.enabled() else None),
    }

@st.cache_data(show_spinner=False, ttl=86400, max_entries=300)
def fetch_journal_info(issn):
    logger.info(f"[API_CALL] Resolving ISSN: {issn}")
    try:
        t0 = time.time()
        with requests.Session() as session:
            res = robust_get(session, f"https://api.openalex.org/sources/issn:{issn}", params=None, headers=get_headers())
            if res and res.json().get("id"):
                latency = int((time.time() - t0) * 1000)
                logger.info(f"[API_SUCCESS] Resolved {issn} in {latency}ms")
                return parse_journal_data(res.json())
    except RateLimitException:
        logger.error("[API_429] Rate Limit Exceeded.")
        st.toast("🚨 Connection Failed: API Rate Limit Exceeded", icon="❌")
    except Exception as e:
        logger.error(f"[API_ERROR] Journal Reverse Lookup Failed for {issn}: {e}")
        st.toast("🚨 Connection Failed: Server Connection Error", icon="❌")
    return None

@st.cache_data(show_spinner=False, ttl=86400, max_entries=300)
def search_journal_db(skw):
    logger.info(f"[API_CALL] Querying Source DB with keyword: '{skw}'")
    try:
        t0 = time.time()
        req_url = "https://api.openalex.org/sources"
        params = {"search": skw.strip(), "filter": "type:journal", "sort": "works_count:desc", "per-page": 15}
        with requests.Session() as session:
            res = robust_get(session, req_url, params=params, headers=get_headers())
            if res:
                latency = int((time.time() - t0) * 1000)
                data = res.json()
                results = [parse_journal_data(r) for r in data.get("results", []) if r.get("issn_l")]
                logger.info(f"[API_SUCCESS] DB Search complete in {latency}ms. Found {len(results)} matches.")
                return results
    except RateLimitException:
        logger.error("[API_429] Rate Limit Exceeded.")
        st.toast("🚨 Connection Failed: API Rate Limit Exceeded", icon="❌")
    except Exception as e:
        logger.error(f"[API_ERROR] Search DB Error: {e}", exc_info=True)
        st.toast("🚨 Connection Failed: Server Connection Error", icon="❌")
    return []

def parse_work_metadata(w, count=None):
    current_yr = get_current_year()
    title = w.get("title") or "No Title"
    loc = w.get("primary_location") or {}
    source = loc.get("source") or {} if isinstance(loc, dict) else {}
    journal = source.get("display_name") if isinstance(source, dict) else "Unknown"
    journal_issn = (source.get("issn_l") or "") if isinstance(source, dict) else ""
    year = w.get("publication_year") or current_yr
    cites = w.get("cited_by_count") or 0
    doi = w.get("doi") or ""
    abstract = extract_abstract(w.get("abstract_inverted_index") or {})

    # Document Type (Article, Review, etc.)
    work_type = str(w.get("type") or "article").capitalize()

    # Authors & Lead Institution extraction
    authorships = w.get("authorships") or []
    authors_list = [a.get("author", {}).get("display_name", "") for a in authorships if isinstance(a, dict)]
    authors = ", ".join([a for a in authors_list[:5] if a]) + (" et al." if len(authors_list) > 5 else "")

    institutions = []
    for a in authorships:
        if isinstance(a, dict):
            for inst in (a.get("institutions") or []):
                if isinstance(inst, dict) and inst.get("display_name"):
                    inst_name = inst["display_name"]
                    if inst_name not in institutions:
                        institutions.append(inst_name)
    lead_institution = institutions[0] if institutions else "N/A"

    # Primary Academic Topic
    primary_topic = w.get("primary_topic") or {}
    topic_name = primary_topic.get("display_name") if isinstance(primary_topic, dict) else ""
    if not topic_name:
        concepts = w.get("concepts") or []
        if concepts and isinstance(concepts[0], dict):
            topic_name = concepts[0].get("display_name") or "General"
        else:
            topic_name = "General"

    # Field-Weighted Citation Impact (FWCI) & Reference Count
    fwci_raw = w.get("fwci")
    try:
        fwci = round(float(fwci_raw), 2) if fwci_raw is not None else 0.0
    except Exception:
        fwci = 0.0

    ref_count = w.get("referenced_works_count")
    if ref_count is None:
        ref_count = len(w.get("referenced_works") or [])

    # Open Access Metadata
    oa = w.get("open_access") or {}
    oa_url = oa.get("oa_url") if isinstance(oa, dict) and oa.get("is_oa") else None
    oa_status = str(oa.get("oa_status") or "closed").upper() if isinstance(oa, dict) else "CLOSED"

    try:
        velocity = round(cites / max((current_yr - int(year) + 1), 1), 1)
    except Exception:
        velocity = 0.0

    meta = {
        "Title": title,
        "Authors": authors,
        "Institution": lead_institution,
        "Journal": journal,
        "_ISSN": journal_issn,
        "Year": year,
        "Type": work_type,
        "Topic": topic_name,
        "Citations": cites,
        "Velocity (Cites/Yr)": velocity,
        "FWCI": fwci,
        "Refs": int(ref_count or 0),
        "OA_Status": oa_status,
        "OA_Link": oa_url,
        "DOI": doi,
        "Abstract": abstract,
    }
    if count is not None:
        meta["Network Hits"] = int(count)
    return meta


def run_data_pipeline(
    issns,
    start_yr,
    end_yr,
    top_n,
    mode,
    kw,
    min_cites,
    oa_only,
    status_logger,
    prog_bar=None,
    doc_type="ALL",
    sort_by="DEFAULT",
    require_abstract=False,
    deep_max_phases=15,
    restrict_root_years=False,
):
    headers = get_headers()

    q_info = optimize_search_query(kw)
    effective_kw = q_info["optimized"]
    fallback_kw = q_info["fallback"]

    logger.info("=" * 60)
    logger.info(f"[PIPELINE_INIT] Mode: {mode} | Target N: {top_n} | Targets: {'GLOBAL DB' if not issns else str(len(issns))+' ISSNs'}")
    logger.info(f"[PIPELINE_CONFIG] Range: {start_yr}-{end_yr} | Raw KW: '{kw}' -> Optimized KW: '{effective_kw}' | OA_Only: {oa_only} | DocType: {doc_type}")
    logger.info("=" * 60)

    sort_by_norm = str(sort_by or "DEFAULT").upper()

    DOC_TYPE_FILTER_MAP = {
        "ALL": None,
        "ARTICLE_REVIEW": "type:article|review",
        "ARTICLE": "type:article",
        "REVIEW": "type:review",
        "PREPRINT": "type:preprint",
        "BOOK": "type:book|book-chapter",
        "DISSERTATION": "type:dissertation",
        "EDITORIAL_LETTER": "type:editorial|letter",
    }
    doc_type_filter = DOC_TYPE_FILTER_MAP.get(str(doc_type or "ALL").upper())

    def _build_filter(query_str):
        f_list = [f"publication_year:{start_yr}-{end_yr}"]
        if issns:
            issn_str = "|".join(issns)
            f_list.append(f"primary_location.source.issn:{issn_str}")
        if query_str.strip():
            f_list.append(f"title_and_abstract.search:{query_str.strip()}")
        if oa_only:
            f_list.append("is_oa:true")
        if min_cites > 0:
            f_list.append(f"cited_by_count:>{min_cites-1}")
        if doc_type_filter:
            f_list.append(doc_type_filter)
        if require_abstract:
            f_list.append("has_abstract:true")
        return ",".join(f_list)

    base_filter = _build_filter(effective_kw)
    logger.info(f"[FILTER_COMPILED] URL Filter String: {base_filter}")

    # Determine API-level sort for Ultra-fast mode
    api_sort = "cited_by_count:desc"
    if "Ultra-fast" in mode and sort_by_norm in ("YEAR", "YEAR_DESC"):
        api_sort = "publication_year:desc,cited_by_count:desc"

    try:
        with requests.Session() as session:
            adapter = HTTPAdapter(pool_connections=15, pool_maxsize=15)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            def _execute_search(active_filter):
                local_results = []
                if "Ultra-fast" in mode:
                    if status_logger:
                        status_logger.update(label="Fetching database records...")
                    if prog_bar:
                        prog_bar.progress(5, text="Fetching database records... [5%]")

                    page = 1
                    per_page = min(100, top_n)
                    while len(local_results) < top_n:
                        params = {"filter": active_filter, "per-page": per_page, "page": page, "sort": api_sort}

                        res = robust_get(session, "https://api.openalex.org/works", params, headers)
                        if not res:
                            break

                        data = res.json()
                        page_results = data.get("results") or []
                        if not page_results:
                            break

                        for w in page_results:
                            if len(local_results) >= top_n:
                                break
                            parsed = parse_work_metadata(w)
                            if require_abstract and not parsed["Abstract"].strip():
                                continue
                            local_results.append(parsed)

                        if status_logger:
                            status_logger.update(label=f"Fetching database records... ({len(local_results)}/{top_n} entries)")
                        if prog_bar:
                            pct = min(5 + int((len(local_results) / top_n) * 85), 90)
                            prog_bar.progress(pct, text=f"Fetching database records... ({len(local_results)}/{top_n} entries) [{pct}%]")

                        total_count = (data.get("meta") or {}).get("count")
                        if len(page_results) < per_page or (isinstance(total_count, int) and page * per_page >= total_count):
                            logger.info(f"[PIPELINE_EARLY_EXIT] All available records ({len(local_results)}) fetched at page {page}.")
                            break

                        page += 1
                    return local_results

                else:
                    max_phases = max(1, int(deep_max_phases or 15))
                    if status_logger:
                        status_logger.update(label="Scanning reference topology...")
                    if prog_bar:
                        prog_bar.progress(5, text=f"Scanning reference topology... (Phase 1/{max_phases}) [5%]")

                    page = 1
                    all_refs = []

                    while page <= max_phases:
                        params = {"filter": active_filter, "select": "referenced_works", "per-page": 100, "page": page, "sort": "cited_by_count:desc"}

                        logger.info(f"[ENGINE_DEEP_PHASE] Requesting Phase {page}/{max_phases}...")
                        res = robust_get(session, "https://api.openalex.org/works", params, headers)

                        if not res:
                            logger.warning(f"[PHASE_SKIP] Phase {page} failed or timed out. Proceeding with collected data.")
                            break

                        data = res.json()
                        page_results = data.get("results") or []
                        if not page_results:
                            break

                        for w in page_results:
                            all_refs.extend(w.get("referenced_works", []))

                        logger.info(f"[ENGINE_DEEP_PHASE] Phase {page}/{max_phases} successfully scanned ({len(page_results)} works).")

                        total_count = (data.get("meta") or {}).get("count")
                        if isinstance(total_count, int) and total_count > 0:
                            max_phases = min(max_phases, (total_count + 99) // 100)

                        if status_logger:
                            status_logger.update(label=f"Scanning reference topology... (Phase {page}/{max_phases})")
                        if prog_bar:
                            pct = min(5 + int((page / max(max_phases, 1)) * 40), 45)
                            prog_bar.progress(pct, text=f"Scanning reference topology... (Phase {page}/{max_phases}) [{pct}%]")

                        if len(page_results) < 100 or page >= max_phases:
                            logger.info(f"[ENGINE_DEEP_EARLY_EXIT] Reference topology scan completed at Phase {page}/{max_phases}.")
                            break

                        page += 1

                    if not all_refs:
                        return []

                    top_refs = Counter(all_refs).most_common(top_n * 3)
                    ref_dict = {ref_id.split("/")[-1]: count for ref_id, count in top_refs}
                    ref_ids = list(ref_dict.keys())

                    if status_logger:
                        status_logger.update(label="Restoring structural metadata...")
                    if prog_bar:
                        prog_bar.progress(45, text="Restoring structural metadata... [45%]")

                    chunk_size = 50
                    chunks = [ref_ids[i : i + chunk_size] for i in range(0, len(ref_ids), chunk_size)]
                    completed_chunks = 0

                    def fetch_and_parse_chunk(chunk):
                        chunk_str = "|".join(chunk)
                        filter_str = f"openalex:{chunk_str}"
                        if restrict_root_years:
                            filter_str += f",publication_year:{start_yr}-{end_yr}"
                        if oa_only:
                            filter_str += ",is_oa:true"
                        if min_cites > 0:
                            filter_str += f",cited_by_count:>{min_cites-1}"
                        if doc_type_filter:
                            filter_str += f",{doc_type_filter}"

                        p = {"filter": filter_str, "per-page": len(chunk)}
                        response = robust_get(session, "https://api.openalex.org/works", p, headers)

                        parsed_results = []
                        if response:
                            for w in response.json().get("results", []):
                                work_id = (w.get("id") or "").split("/")[-1]
                                parsed = parse_work_metadata(w, count=ref_dict.get(work_id, 0))
                                if require_abstract and not parsed["Abstract"].strip():
                                    continue
                                parsed_results.append(parsed)
                        return parsed_results

                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = {executor.submit(fetch_and_parse_chunk, c): c for c in chunks}
                        for future in as_completed(futures):
                            try:
                                local_results.extend(future.result())
                            except Exception as e:
                                logger.error(f"[THREAD_ERROR] Chunk processing failed: {e}")

                            completed_chunks += 1
                            if status_logger:
                                status_logger.update(label=f"Restoring structural metadata... (Chunk {completed_chunks}/{len(chunks)})")
                            if prog_bar:
                                pct = min(45 + int((completed_chunks / len(chunks)) * 45), 90)
                                prog_bar.progress(pct, text=f"Restoring structural metadata... (Chunk {completed_chunks}/{len(chunks)}) [{pct}%]")

                    return local_results

            results = _execute_search(base_filter)

            if not results and fallback_kw and fallback_kw != effective_kw:
                logger.info(f"[SMART_FALLBACK] 0 results with '{effective_kw}'. Retrying with relaxed query: '{fallback_kw}'")
                fallback_filter = _build_filter(fallback_kw)
                results = _execute_search(fallback_filter)

        df = pd.DataFrame(results)
        if not df.empty:
            df = df.drop_duplicates(subset=["DOI", "Title"], keep="first")

            # Apply Researcher's Selected Sorting Criterion
            if "Network Hits" in df.columns:
                if sort_by_norm == "CITATIONS":
                    df = df.sort_values(by=["Citations", "Network Hits"], ascending=[False, False])
                elif sort_by_norm == "VELOCITY":
                    df = df.sort_values(by=["Velocity (Cites/Yr)", "Network Hits"], ascending=[False, False])
                elif sort_by_norm == "FWCI":
                    df = df.sort_values(by=["FWCI", "Network Hits"], ascending=[False, False])
                elif sort_by_norm in ("YEAR", "YEAR_DESC"):
                    df = df.sort_values(by=["Year", "Network Hits"], ascending=[False, False])
                else:
                    df = df.sort_values(by=["Network Hits", "Citations"], ascending=[False, False])
                ordered_cols = [
                    "Title", "Authors", "Institution", "Journal", "Year", "Type", "Topic",
                    "Network Hits", "Citations", "Velocity (Cites/Yr)", "FWCI", "Refs",
                    "OA_Status", "OA_Link", "DOI", "Abstract"
                ]
            else:
                if sort_by_norm == "VELOCITY":
                    df = df.sort_values(by=["Velocity (Cites/Yr)", "Citations"], ascending=[False, False])
                elif sort_by_norm == "FWCI":
                    df = df.sort_values(by=["FWCI", "Citations"], ascending=[False, False])
                elif sort_by_norm in ("YEAR", "YEAR_DESC"):
                    df = df.sort_values(by=["Year", "Citations"], ascending=[False, False])
                else:
                    df = df.sort_values(by="Citations", ascending=False)
                ordered_cols = [
                    "Title", "Authors", "Institution", "Journal", "Year", "Type", "Topic",
                    "Citations", "Velocity (Cites/Yr)", "FWCI", "Refs",
                    "OA_Status", "OA_Link", "DOI", "Abstract"
                ]

            if jcr_lookup.enabled() and "Journal" in df.columns:
                try:
                    keys = list(zip(df.get("_ISSN", pd.Series([""] * len(df))).fillna("").astype(str), df["Journal"].fillna("").astype(str)))
                    got = jcr_lookup.lookup_many(keys)
                    df["JCR"] = [jcr_lookup.short_label(got.get(k)) for k in keys]
                    ordered_cols.insert(ordered_cols.index("Journal") + 1, "JCR")
                except Exception as e:
                    logger.info(f"[JCR] 열 추가 생략: {type(e).__name__}")
            df = df[[c for c in ordered_cols if c in df.columns]].head(top_n).reset_index(drop=True)
            df.insert(0, "Rank", range(1, len(df) + 1))

        return df

    except RateLimitException:
        err_msg = "🚨 API Rate Limit Exceeded (429): API key is missing or daily quota (100k) has been exhausted."
        logger.error(err_msg)
        raise Exception(err_msg)

    except BaseException as e:
        if type(e).__name__ in ["StopException", "ScriptRunControlException", "RerunException"]:
            logger.warning("[USER_ABORT] Pipeline forcefully terminated by Streamlit UI interaction.")
            raise e

        if str(e).startswith("🚨"):
            raise e

        err_msg = f"🚨 An error occurred during data extraction: {str(e)}"
        logger.error(f"[PIPELINE_ERROR] {err_msg}")
        raise Exception(err_msg)
