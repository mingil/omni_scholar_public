import pandas as pd
import io
import re
import datetime
import streamlit as st
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from modules.logger_setup import logger


def build_export_filename(
    query_str: str = "",
    search_mode: str = "ULTRA",
    paper_count: int = 0,
    cart_count: int = 0,
    lang: str = "KO_EN",
    ext: str = "xlsx",
    timestamp_str: str = None,
    prefix_tag: str = "",
) -> str:
    """Generates a clean, descriptive export filename with exact date and time (YYYYMMDD_HHMMSS)."""
    ts = timestamp_str or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    is_deep = "DEEP" in str(search_mode).upper()
    is_ko = str(lang).upper().startswith("KO")
    mode_tag = ("뿌리논문역추적" if is_deep else "트렌드스캔") if is_ko else ("RootNetwork" if is_deep else "TrendScan")

    clean_prefix = re.sub(r"[^가-힣a-zA-Z0-9]+", "_", str(prefix_tag or "").strip()).strip("_")

    raw_q = str(query_str or "").strip()
    # Strip boolean operators and quotes for a clean filename slug
    cleaned_q = re.sub(r"\b(OR|AND|NOT)\b", " ", raw_q)
    cleaned_q = re.sub(r'["\'()\[\]\-]+', " ", cleaned_q)
    cleaned_q = re.sub(r"[^가-힣a-zA-Z0-9]+", "_", cleaned_q)
    cleaned_q = re.sub(r"_+", "_", cleaned_q).strip("_")

    if len(cleaned_q) > 28:
        cleaned_q = cleaned_q[:28].rstrip("_")

    if not cleaned_q:
        if cart_count > 0:
            cleaned_q = f"지정학술지{int(cart_count)}곳" if is_ko else f"{int(cart_count)}Journals"
        else:
            cleaned_q = "학술논문분석" if is_ko else "Literature"

    parts = ["OmniScholar", mode_tag]
    if clean_prefix:
        parts.append(clean_prefix)
    parts.append(cleaned_q)
    if paper_count and int(paper_count) > 0:
        parts.append(f"{int(paper_count)}편" if is_ko else f"{int(paper_count)}papers")
    parts.append(ts)

    base_name = "_".join([p for p in parts if p])
    clean_ext = str(ext or "").strip().lstrip(".")
    return f"{base_name}.{clean_ext}" if clean_ext else base_name


@st.cache_data(show_spinner=False)
def create_excel(df):
    """Generates a professionally styled, publication-ready Excel (.xlsx) report."""
    try:
        bio = io.BytesIO()
        export_df = df.copy()

        for col in export_df.columns:
            if export_df[col].dtype == object:
                export_df[col] = export_df[col].fillna("")

        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="OmniScholar_Report")
            ws = writer.sheets["OmniScholar_Report"]

            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            body_font = Font(name="Calibri", size=10, color="0F172A")
            bold_font = Font(name="Calibri", size=10, bold=True, color="0F172A")
            link_font = Font(name="Calibri", size=10, color="2563EB", underline="single")
            thin_border = Border(
                left=Side(style="thin", color="E2E8F0"),
                right=Side(style="thin", color="E2E8F0"),
                top=Side(style="thin", color="E2E8F0"),
                bottom=Side(style="thin", color="E2E8F0"),
            )

            col_widths = {
                "Rank": 8,
                "Title": 48,
                "Authors": 28,
                "Institution": 28,
                "Journal": 26,
                "Year": 10,
                "Type": 12,
                "Topic": 26,
                "Network Hits": 15,
                "Citations": 14,
                "Velocity (Cites/Yr)": 18,
                "FWCI": 12,
                "Refs": 10,
                "OA_Status": 12,
                "OA_Link": 24,
                "DOI": 28,
                "Abstract": 65,
            }

            center_cols = {"Rank", "Year", "Type", "Network Hits", "Citations", "Velocity (Cites/Yr)", "FWCI", "Refs", "OA_Status"}

            ws.row_dimensions[1].height = 28
            for col_idx, col_name in enumerate(export_df.columns, start=1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = col_widths.get(col_name, 18)

            for row_idx in range(2, len(export_df) + 2):
                ws.row_dimensions[row_idx].height = 42
                is_even = (row_idx % 2 == 0)
                for col_idx, col_name in enumerate(export_df.columns, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.border = thin_border
                    if is_even:
                        cell.fill = zebra_fill

                    if col_name in center_cols:
                        cell.font = bold_font if col_name in ["Rank", "Network Hits", "Citations"] else body_font
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col_name in ["DOI", "OA_Link"]:
                        val = str(cell.value or "").strip()
                        if val.startswith("http"):
                            cell.hyperlink = val
                            cell.font = link_font
                        else:
                            cell.font = body_font
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
                    else:
                        cell.font = bold_font if col_name == "Title" else body_font
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        return bio.getvalue()
    except Exception as e:
        logger.error(f"Excel Generation Error: {e}")
        return None


@st.cache_data(show_spinner=False)
def generate_ris(df):
    """Generates a clean, standards-compliant RIS citation file for Zotero, EndNote, and Mendeley."""
    ris_lines = []
    for _, row in df.iterrows():
        ris_lines.append("TY  - JOUR")

        title = str(row.get("Title") or "").strip()
        if title:
            ris_lines.append(f"TI  - {title}")

        journal = str(row.get("Journal") or "").strip()
        if journal and journal != "Unknown":
            ris_lines.append(f"JO  - {journal}")
            ris_lines.append(f"T2  - {journal}")

        year = row.get("Year")
        if pd.notna(year) and str(year).strip():
            ris_lines.append(f"PY  - {int(year)}")

        doi = str(row.get("DOI") or "").strip()
        if doi and doi.lower() != "none":
            clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            if clean_doi:
                ris_lines.append(f"DO  - {clean_doi}")

        authors = str(row.get("Authors") or "").strip()
        if authors and authors.lower() != "none":
            for au in authors.split(","):
                clean_au = au.replace("et al.", "").strip()
                if clean_au:
                    ris_lines.append(f"AU  - {clean_au}")

        oa_link = row.get("OA_Link")
        if oa_link and pd.notna(oa_link) and str(oa_link).strip().startswith("http"):
            ris_lines.append(f"UR  - {str(oa_link).strip()}")
        elif doi and doi.startswith("http"):
            ris_lines.append(f"UR  - {doi}")

        abstract = str(row.get("Abstract") or "").strip()
        if abstract and abstract.lower() != "none":
            clean_abs = abstract.replace("\r", " ").replace("\n", " ")
            ris_lines.append(f"AB  - {clean_abs}")

        note_parts = [
            f"Citations: {int(row.get('Citations', 0))}",
            f"Velocity: {row.get('Velocity (Cites/Yr)', 0)}/yr",
            f"FWCI: {row.get('FWCI', 0.0)}"
        ]
        if "Network Hits" in row and pd.notna(row["Network Hits"]):
            note_parts.insert(0, f"In-Network Co-citations: {int(row['Network Hits'])}")
        ris_lines.append(f"N1  - {' | '.join(note_parts)}")

        ris_lines.append("ER  - ")
        ris_lines.append("")

    return "\n".join(ris_lines).encode("utf-8-sig")


def format_citations_for_paper(row) -> dict:
    """Generates APA 7th, AMA/Vancouver, and BibTeX formatted citation strings for a single paper."""
    title = str(row.get("Title") or "Untitled").strip().rstrip(".")
    authors = str(row.get("Authors") or "Unknown Author").strip()
    journal = str(row.get("Journal") or "Unknown Journal").strip()
    year = str(row.get("Year") or "").strip()
    doi = str(row.get("DOI") or "").strip()
    clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    doi_url = f"https://doi.org/{clean_doi}" if clean_doi else ""

    # 1. APA 7th Style
    apa = f"{authors} ({year}). {title}. {journal}."
    if doi_url:
        apa += f" {doi_url}"

    # 2. AMA / Vancouver (Medical & Scientific Standard)
    ama = f"{authors}. {title}. {journal}. {year}."
    if clean_doi:
        ama += f" doi:{clean_doi}"

    # 3. BibTeX
    first_author_token = re.sub(r"[^a-zA-Z]", "", authors.split(",")[0].split(" ")[-1]).lower() or "author"
    first_title_token = re.sub(r"[^a-zA-Z]", "", title.split(" ")[0]).lower() or "work"
    cite_key = f"{first_author_token}{year}{first_title_token}"
    bibtex_authors = " and ".join([a.strip() for a in authors.replace(" et al.", "").split(",") if a.strip()])
    bibtex = (
        f"@article{{{cite_key},\n"
        f"  author = {{{bibtex_authors}}},\n"
        f"  title = {{{title}}},\n"
        f"  journal = {{{journal}}},\n"
        f"  year = {{{year}}}"
        + (f",\n  doi = {{{clean_doi}}}" if clean_doi else "")
        + "\n}"
    )

    return {"apa": apa, "ama": ama, "bibtex": bibtex}
