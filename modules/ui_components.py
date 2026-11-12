import streamlit as st
import streamlit.components.v1 as components
import html

def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

        /* =========================================================
           1. HIDE ALL DEFAULT STREAMLIT CHROME & SIDEBAR
        ========================================================= */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        header[data-testid="stHeader"],
        footer,
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* =========================================================
           2. EDITORIAL-GRADE KOREAN/ENGLISH TYPOGRAPHY
              (word-break: keep-all prevents mid-word breaks)
        ========================================================= */
        html, body, [class*="css"], .stMarkdown, .stMarkdown p, .stMarkdown li {
            font-family: 'Pretendard Variable', 'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
            color: #1E293B;
            background-color: transparent;
            font-size: 1.02rem;
            line-height: 1.65;
            letter-spacing: -0.012em;
            word-break: keep-all;
            overflow-wrap: break-word;
            -webkit-font-smoothing: antialiased;
        }
        h1, h2, h3, h4, .brand-heading {
            font-family: 'Plus Jakarta Sans', 'Pretendard Variable', 'Inter', sans-serif !important;
            font-weight: 800;
            color: #0F172A;
            letter-spacing: -0.025em;
            line-height: 1.36;
            word-break: keep-all;
            overflow-wrap: break-word;
        }
        .stApp {
            background: linear-gradient(180deg, #E8EEF5 0%, #F1F5F9 300px, #F1F5F9 100%) !important;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p,
        .stCaption {
            font-size: 0.96rem !important;
            color: #334155 !important;
            font-weight: 500 !important;
            line-height: 1.58 !important;
            word-break: keep-all !important;
        }

        .block-container {
            padding-top: 0.85rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1.8rem !important;
            padding-right: 1.8rem !important;
            max-width: 1320px !important;
        }

        /* =========================================================
           3. KEYFRAME ANIMATIONS FOR ATTENTION-GRABBING CTAs
        ========================================================= */
        @keyframes ctaPulseBlue {
            0% {
                box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.55), 0 6px 18px rgba(37, 99, 235, 0.28);
            }
            70% {
                box-shadow: 0 0 0 11px rgba(37, 99, 235, 0), 0 8px 22px rgba(37, 99, 235, 0.36);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(37, 99, 235, 0), 0 6px 18px rgba(37, 99, 235, 0.28);
            }
        }

        @keyframes ctaBoxGlow {
            0%, 100% {
                border-color: #2563EB;
                box-shadow: 0 4px 16px rgba(37, 99, 235, 0.14);
            }
            50% {
                border-color: #1D4ED8;
                box-shadow: 0 6px 22px rgba(37, 99, 235, 0.26);
            }
        }

        @keyframes ctaAmberGlow {
            0%, 100% {
                border-color: #F59E0B;
                box-shadow: 0 4px 18px rgba(217, 119, 6, 0.16);
            }
            50% {
                border-color: #DC2626;
                box-shadow: 0 6px 24px rgba(220, 38, 38, 0.28);
            }
        }

        @keyframes bouncePointer {
            0%, 100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(4px);
            }
        }

        @keyframes badgeFlash {
            0%, 100% {
                opacity: 1;
                transform: scale(1);
            }
            50% {
                opacity: 0.88;
                transform: scale(1.04);
            }
        }

        .bounce-icon {
            display: inline-block;
            animation: bouncePointer 1.1s ease-in-out infinite;
        }

        /* =========================================================
           4. ACTION-REQUIRED CALLOUTS & CONFIRMED BANNERS
        ========================================================= */
        .cta-attention-box {
            background: linear-gradient(90deg, #EFF6FF 0%, #DBEAFE 100%);
            border: 2.5px solid #2563EB;
            border-left: 8px solid #1D4ED8;
            border-radius: 13px;
            padding: 14px 20px;
            margin-top: 10px;
            margin-bottom: 10px;
            color: #0F172A;
            animation: ctaBoxGlow 2.2s infinite ease-in-out;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            line-height: 1.6;
        }
        .cta-attention-badge {
            background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%);
            color: #FFFFFF;
            font-weight: 800;
            font-size: 0.86rem;
            padding: 5px 12px;
            border-radius: 999px;
            white-space: nowrap;
            animation: badgeFlash 1.6s infinite ease-in-out;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
        }

        .cta-attention-amber {
            background: linear-gradient(90deg, #FFFBEB 0%, #FEF3C7 100%);
            border: 2.5px solid #F59E0B;
            border-left: 8px solid #DC2626;
            border-radius: 13px;
            padding: 16px 20px;
            margin-top: 10px;
            margin-bottom: 12px;
            color: #78350F;
            animation: ctaAmberGlow 2s infinite ease-in-out;
            line-height: 1.65;
        }
        .cta-amber-badge {
            background: linear-gradient(135deg, #DC2626 0%, #D97706 100%);
            color: #FFFFFF;
            font-weight: 800;
            font-size: 0.86rem;
            padding: 5px 12px;
            border-radius: 999px;
            white-space: nowrap;
            animation: badgeFlash 1.5s infinite ease-in-out;
        }

        .cta-confirmed-bar {
            background: linear-gradient(90deg, #F0FDF4 0%, #DCFCE7 100%);
            border: 2px solid #22C55E;
            border-left: 8px solid #16A34A;
            border-radius: 13px;
            padding: 14px 20px;
            margin-top: 10px;
            margin-bottom: 8px;
            color: #14532D;
            font-weight: 700;
            font-size: 0.98rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            line-height: 1.58;
            box-shadow: 0 3px 10px rgba(22, 163, 74, 0.08);
        }
        .cta-confirmed-pill {
            background: #16A34A;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 0.86rem;
            padding: 5px 13px;
            border-radius: 999px;
            white-space: nowrap;
        }

        /* =========================================================
           5. TARGET ONLY EXPLICIT BORDERED CONTAINERS
        ========================================================= */
        div[data-testid="stVerticalBlockBorderWrapper"][style*="border"] {
            background-color: #FFFFFF !important;
            border: 2px solid #CBD5E1 !important;
            border-radius: 16px !important;
            padding: 20px 24px !important;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04) !important;
        }

        /* =========================================================
           6. TOP NAVIGATION BAR & BRAND HEADER
        ========================================================= */
        .top-navbar {
            background: #FFFFFF;
            border: 2px solid #CBD5E1;
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 10px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
        }
        .brand-logo-wrap {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.2rem;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
            flex-shrink: 0;
        }
        .brand-title {
            font-size: 1.32rem;
            font-weight: 800;
            color: #0F172A;
            margin: 0;
            line-height: 1.3;
            letter-spacing: -0.025em;
        }
        .brand-subtitle {
            font-size: 0.94rem;
            color: #475569;
            font-weight: 500;
            margin: 3px 0 0 0;
            line-height: 1.42;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #ECFDF5;
            border: 1.5px solid #6EE7B7;
            color: #047857;
            font-size: 0.9rem;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 999px;
            white-space: nowrap;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #10B981;
            border-radius: 50%;
            display: inline-block;
        }

        /* =========================================================
           7. WORKFLOW STEPPER & CLEAR STEP BOUNDARY BANNERS
        ========================================================= */
        .stepper-wrap {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 4px;
            margin-bottom: 16px;
            background: #FFFFFF;
            padding: 12px;
            border-radius: 15px;
            border: 2px solid #CBD5E1;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
        }
        .stepper-item {
            background: #F8FAFC;
            border: 1.5px solid #CBD5E1;
            border-radius: 12px;
            padding: 12px 14px;
            display: flex;
            align-items: flex-start;
            gap: 11px;
            text-decoration: none !important;
            transition: all 0.15s ease;
        }
        .stepper-item:hover {
            transform: translateY(-1px);
            border-color: #2563EB;
        }
        .stepper-item.done {
            border-color: #16A34A;
            background: linear-gradient(180deg, #F0FDF4 0%, #DCFCE7 100%);
        }
        .stepper-item.active {
            border-color: #2563EB;
            border-width: 2px;
            background: #EFF6FF;
            animation: ctaBoxGlow 2.2s infinite ease-in-out;
        }
        .stepper-item.warn {
            border-color: #D97706;
            border-width: 2px;
            background: #FEF3C7;
            animation: ctaAmberGlow 2s infinite ease-in-out;
        }
        .stepper-item.pending {
            border-color: #CBD5E1;
            background: #F8FAFC;
            opacity: 0.85;
        }
        .stepper-badge {
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.86rem;
            font-weight: 800;
            flex-shrink: 0;
            margin-top: 1px;
        }
        .stepper-badge.done {
            background: #16A34A;
            color: #FFFFFF;
        }
        .stepper-badge.active {
            background: #2563EB;
            color: #FFFFFF;
        }
        .stepper-badge.warn {
            background: #D97706;
            color: #FFFFFF;
        }
        .stepper-badge.pending {
            background: #CBD5E1;
            color: #334155;
        }
        .stepper-text-title {
            font-size: 0.96rem;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.32;
        }
        .stepper-text-sub {
            font-size: 0.86rem;
            color: #334155;
            margin-top: 3px;
            line-height: 1.38;
            font-weight: 600;
        }

        /* Distinct Step Outer Header Banner */
        .step-boundary-banner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            padding: 13px 22px;
            border-radius: 14px;
            margin-top: 18px;
            margin-bottom: 6px;
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
        }
        .step-boundary-banner.step1 {
            background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
        }
        .step-boundary-banner.step2 {
            background: linear-gradient(90deg, #0F766E 0%, #0D9488 100%);
        }
        .step-boundary-banner.step3 {
            background: linear-gradient(90deg, #3730A3 0%, #4F46E5 100%);
        }
        .step-boundary-banner.step4 {
            background: linear-gradient(90deg, #9A3412 0%, #EA580C 100%);
        }
        .step-boundary-banner.step-result {
            background: linear-gradient(90deg, #14532D 0%, #16A34A 100%);
        }
        .step-boundary-left {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .step-boundary-num {
            background: rgba(255, 255, 255, 0.22);
            border: 1.5px solid rgba(255, 255, 255, 0.5);
            color: #FFFFFF;
            font-weight: 900;
            font-size: 0.9rem;
            padding: 4px 13px;
            border-radius: 999px;
            letter-spacing: 0.04em;
            white-space: nowrap;
        }
        .step-boundary-title {
            font-size: 1.18rem;
            font-weight: 800;
            color: #FFFFFF;
            margin: 0;
            line-height: 1.35;
        }
        .step-boundary-status {
            padding: 5px 14px;
            border-radius: 999px;
            font-size: 0.9rem;
            font-weight: 800;
            background: #FFFFFF;
            white-space: nowrap;
        }
        .step-boundary-status.done {
            color: #15803D;
        }
        .step-boundary-status.active {
            color: #1D4ED8;
        }
        .step-boundary-status.todo {
            color: #475569;
        }
        .step-boundary-status.warn {
            color: #B45309;
        }

        .step-prereq-alert {
            background: #FEF2F2;
            border: 2px solid #FCA5A5;
            border-left: 7px solid #DC2626;
            padding: 13px 18px;
            border-radius: 12px;
            margin-bottom: 14px;
            font-size: 0.96rem;
            color: #7F1D1D;
            font-weight: 600;
            line-height: 1.6;
        }

        /* =========================================================
           8. SECTION DESCRIPTIONS & INTERACTIVE BUTTONS
        ========================================================= */
        .section-desc-text {
            font-size: 0.98rem;
            color: #334155;
            margin-top: 0px;
            margin-bottom: 12px;
            line-height: 1.65;
            word-break: keep-all;
        }

        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            height: auto !important;
            min-height: 2.85rem !important;
            line-height: 1.45 !important;
            border-radius: 11px !important;
            font-weight: 700 !important;
            font-size: 0.96rem !important;
            transition: all 0.16s ease !important;
            padding: 0.55rem 1.05rem !important;
            border: 1.5px solid #CBD5E1 !important;
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        }
        div.stButton > button p,
        div.stButton > button span,
        div.stButton > button div,
        div.stDownloadButton > button p,
        div.stDownloadButton > button span,
        div.stDownloadButton > button div,
        div[data-testid="stFormSubmitButton"] > button p,
        div[data-testid="stFormSubmitButton"] > button span,
        div[data-testid="stFormSubmitButton"] > button div {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            line-height: 1.45 !important;
            font-size: 0.96rem !important;
            font-weight: 700 !important;
        }
        div.stButton > button:hover,
        div.stDownloadButton > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #EFF6FF !important;
            border-color: #2563EB !important;
            color: #1E3A8A !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.14) !important;
        }
        div.stButton > button:active,
        div.stDownloadButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:active {
            transform: scale(0.97) !important;
            background-color: #DBEAFE !important;
        }

        /* ATTENTION-GRABBING PULSING PRIMARY CTA BUTTONS */
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1E40AF 0%, #2563EB 50%, #0284C7 100%) !important;
            color: #FFFFFF !important;
            border: 2px solid #93C5FD !important;
            font-weight: 800 !important;
            padding: 0.92rem 1.4rem !important;
            font-size: 1.05rem !important;
            border-radius: 12px !important;
            animation: ctaPulseBlue 1.9s infinite !important;
        }
        div.stButton > button[kind="primary"] p,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
            font-size: 1.05rem !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #1E3A8A 0%, #1D4ED8 100%) !important;
            transform: translateY(-2px) scale(1.005) !important;
            box-shadow: 0 10px 25px rgba(37, 99, 235, 0.42) !important;
        }
        div.stButton > button[kind="primary"]:active,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:active {
            transform: scale(0.97) !important;
            background: #15803D !important;
        }
        div.stButton > button[disabled] {
            opacity: 0.55 !important;
            cursor: not-allowed !important;
            background-color: #F1F5F9 !important;
            color: #94A3B8 !important;
            border: 1.5px solid #E2E8F0 !important;
            box-shadow: none !important;
            transform: none !important;
            animation: none !important;
        }

        /* Labels & Radio / Checkbox / Expander */
        div[role="radiogroup"] label,
        div[role="radiogroup"] label p,
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p,
        div[data-testid="stExpander"] summary p,
        div[data-testid="stWidgetLabel"] p {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            line-height: 1.56 !important;
            color: #0F172A !important;
            font-size: 0.99rem !important;
            font-weight: 600 !important;
        }
        div[role="radiogroup"] > label {
            padding-top: 3px !important;
            padding-bottom: 3px !important;
        }

        /* Text Inputs, Selectboxes & Number Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        div[data-baseweb="select"] > div {
            border-radius: 10px !important;
            border: 1.5px solid #94A3B8 !important;
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            font-size: 1.01rem !important;
            font-weight: 500 !important;
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input {
            padding: 0.68rem 1.0rem !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus {
            background-color: #FFFFFF !important;
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
        }

        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #E2E8F0;
            padding: 6px;
            border-radius: 12px;
            border-bottom: none !important;
        }
        .stTabs [data-baseweb="tab"] {
            height: auto !important;
            padding: 10px 18px !important;
            border-radius: 9px !important;
            color: #334155 !important;
            font-weight: 700 !important;
            font-size: 0.96rem !important;
            border: none !important;
            background-color: transparent !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #1E40AF !important;
            font-weight: 800 !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1) !important;
        }

        /* Journal Badges */
        .journal-badge {
            display: inline-block;
            padding: 4px 11px;
            font-size: 0.87rem;
            font-weight: 700;
            border-radius: 7px;
            margin-right: 6px;
            margin-top: 4px;
            white-space: normal !important;
            word-break: keep-all;
            line-height: 1.45;
        }
        .badge-pub { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }
        .badge-h { background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
        .badge-if { background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
        .badge-works { background-color: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }

        /* Metric Cards */
        .metric-box {
            background: #FFFFFF;
            border: 1.5px solid #D5DFEB;
            padding: 16px 18px;
            border-radius: 13px;
            text-align: left;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.025);
            height: 100%;
            margin-bottom: 10px;
            border-top: 4px solid #2563EB;
        }
        .metric-value {
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
            font-size: 1.82rem;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.25;
        }
        .metric-label {
            font-size: 0.98rem;
            font-weight: 800;
            color: #1E293B;
            margin-top: 5px;
            word-break: keep-all;
        }
        .metric-sub {
            font-size: 0.89rem;
            color: #475569;
            margin-top: 4px;
            font-weight: 500;
            word-break: keep-all;
        }

        /* Syntax & Info Boxes */
        .syntax-box {
            background: #F8FAFC;
            border: 1.5px solid #CBD5E1;
            border-radius: 12px;
            padding: 14px 18px;
            margin-top: 12px;
            font-size: 0.95rem;
            color: #1E293B;
            line-height: 1.62;
            word-break: keep-all;
        }
        .syntax-code {
            background: #DBEAFE;
            color: #1E3A8A;
            padding: 2px 7px;
            border-radius: 6px;
            font-family: monospace;
            font-weight: 700;
            font-size: 0.92rem;
        }
        .guide-box {
            background-color: #F8FAFC;
            border: 1.5px solid #CBD5E1;
            border-left: 5px solid #2563EB;
            padding: 14px 18px;
            border-radius: 10px;
            margin-top: 6px;
            margin-bottom: 12px;
            font-size: 0.96rem;
            color: #1E293B;
            line-height: 1.62;
            word-break: keep-all;
        }
        .guide-title {
            font-weight: 800;
            color: #0F172A;
            font-size: 1.02rem;
            margin-bottom: 4px;
            display: block;
        }

        /* Pre-Flight Filter Dashboard Cards (STEP 04) */
        .preflight-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 14px;
        }
        .preflight-card {
            background: linear-gradient(180deg, #F0FDF4 0%, #ECFDF5 100%);
            border: 1.5px solid #6EE7B7;
            border-left: 5px solid #10B981;
            border-radius: 12px;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            word-break: keep-all;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.06);
        }
        .preflight-card.highlight {
            background: linear-gradient(180deg, #EFF6FF 0%, #E0F2FE 100%);
            border-color: #60A5FA;
            border-left: 5px solid #2563EB;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
        }
        .preflight-card.active-filter {
            background: linear-gradient(180deg, #F0FDF4 0%, #DCFCE7 100%);
            border-color: #4ADE80;
            border-left: 5px solid #16A34A;
            box-shadow: 0 2px 8px rgba(22, 163, 74, 0.08);
        }
        .preflight-card.ready-inclusive {
            background: linear-gradient(180deg, #F0FDFA 0%, #ECFDF5 100%);
            border-color: #5EEAD4;
            border-left: 5px solid #0D9488;
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.07);
        }
        .preflight-label {
            font-size: 0.9rem;
            font-weight: 800;
            color: #1E293B;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
        }
        .preflight-value {
            font-size: 1.02rem;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.44;
        }
        .preflight-sub {
            font-size: 0.88rem;
            color: #1E293B;
            margin-top: 5px;
            font-weight: 600;
            line-height: 1.42;
        }
        .filter-pill-on {
            background: #DCFCE7;
            color: #15803D;
            border: 1.5px solid #4ADE80;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 800;
            white-space: nowrap;
        }
        .filter-pill-default,
        .filter-pill-inclusive {
            background: #CCFBF1;
            color: #0F766E;
            border: 1.5px solid #5EEAD4;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 800;
            white-space: nowrap;
        }

        /* Step 3 Stateful Tab Selector Styling (Horizontal Radio) */
        div[role="radiogroup"][aria-orientation="horizontal"] {
            background: #E2E8F0 !important;
            padding: 6px !important;
            border-radius: 12px !important;
            gap: 8px !important;
            display: flex !important;
            flex-wrap: wrap !important;
        }
        div[role="radiogroup"][aria-orientation="horizontal"] > label {
            background: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 9px !important;
            padding: 9px 16px !important;
            margin: 0 !important;
            flex: 1 1 auto !important;
            justify-content: center !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
        }
        div[role="radiogroup"][aria-orientation="horizontal"] > label:hover {
            border-color: #2563EB !important;
            background: #EFF6FF !important;
        }
        div[role="radiogroup"][aria-orientation="horizontal"] > label:has(input:checked) {
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
            border-color: #1D4ED8 !important;
            color: #FFFFFF !important;
            box-shadow: 0 3px 10px rgba(37, 99, 235, 0.25) !important;
        }
        div[role="radiogroup"][aria-orientation="horizontal"] > label:has(input:checked) p,
        div[role="radiogroup"][aria-orientation="horizontal"] > label:has(input:checked) span {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }

        /* Academic Glossary & Typo Suggestion Cards */
        .glossary-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            margin-top: 8px;
            margin-bottom: 10px;
        }
        .glossary-card {
            background: #FFFFFF;
            border: 1.5px solid #CBD5E1;
            border-left: 5px solid #2563EB;
            border-radius: 12px;
            padding: 13px 16px;
            line-height: 1.58;
            word-break: keep-all;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
        }
        .glossary-card.emerald {
            border-left-color: #0D9488;
            background: #F0FDFA;
        }
        .glossary-card.indigo {
            border-left-color: #4F46E5;
            background: #EEF2FF;
        }
        .glossary-card.amber {
            border-left-color: #D97706;
            background: #FFFBEB;
        }
        .glossary-term-head {
            font-size: 0.98rem;
            font-weight: 800;
            color: #0F172A;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px;
        }
        .glossary-term-tag {
            background: #E2E8F0;
            color: #1E293B;
            font-size: 0.78rem;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 999px;
            white-space: nowrap;
        }
        .glossary-term-desc {
            font-size: 0.92rem;
            color: #334155;
            font-weight: 500;
            line-height: 1.56;
        }
        .typo-suggest-box {
            background: linear-gradient(90deg, #FFFBEB 0%, #FEF3C7 100%);
            border: 2px solid #F59E0B;
            border-left: 7px solid #D97706;
            border-radius: 12px;
            padding: 12px 16px;
            margin-top: 6px;
            margin-bottom: 10px;
            color: #78350F;
            font-size: 0.95rem;
            line-height: 1.58;
            word-break: keep-all;
        }

        /* Responsive Breakpoints */
        @media (max-width: 960px) {
            .stepper-wrap {
                grid-template-columns: repeat(2, 1fr);
            }
            .preflight-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .glossary-grid {
                grid-template-columns: 1fr;
            }
        }
        @media (max-width: 640px) {
            .block-container {
                padding-top: 0.5rem !important;
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
            }
            .top-navbar {
                padding: 12px 14px;
            }
            .stepper-wrap,
            .preflight-grid {
                grid-template-columns: 1fr;
                gap: 8px;
            }
            .step-boundary-title {
                font-size: 1.06rem !important;
            }
            .metric-value {
                font-size: 1.52rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def render_step_banner(step_class: str, step_num_text: str, title_text: str, state: str, status_text: str, anchor_id: str):
    icon_map = {
        "done": "✅",
        "active": "🔵",
        "todo": "⏳",
        "warn": "⚠️"
    }
    icon = icon_map.get(state, "⏳")
    st.markdown(f"""
    <div id="{anchor_id}" class="step-boundary-banner {step_class}">
        <div class="step-boundary-left">
            <span class="step-boundary-num">{step_num_text}</span>
            <h3 class="step-boundary-title">{title_text}</h3>
        </div>
        <div class="step-boundary-status {state}">
            {icon} {status_text}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_workflow_stepper(
    s1_done: bool = False,
    s2_done: bool = False,
    s3_done: bool = False,
    all_ready: bool = False,
    has_results: bool = False,
    is_stale: bool = False,
    mode_short: str = "",
    scope_short: str = "",
    lang: str = "KO_EN",
    **kwargs
):
    if "has_query" in kwargs and not s1_done:
        s1_done = bool(kwargs["has_query"])

    s1_state = "done" if s1_done else "active"
    s1_badge = "✓" if s1_done else "01"

    if s2_done:
        s2_state, s2_badge = "done", "✓"
    elif s1_done:
        s2_state, s2_badge = "active", "02"
    else:
        s2_state, s2_badge = "pending", "02"

    if s3_done:
        s3_state, s3_badge = "done", "✓"
    elif s1_done and s2_done:
        s3_state, s3_badge = "active", "03"
    else:
        s3_state, s3_badge = "pending", "03"

    if has_results and not is_stale:
        s4_state, s4_badge = "done", "✓"
    elif is_stale:
        s4_state, s4_badge = "warn", "!"
    elif all_ready:
        s4_state, s4_badge = "active", "04"
    else:
        s4_state, s4_badge = "pending", "04"

    if lang == "EN":
        header_txt = "📍 Workflow Progress Tracker (Confirm each step in order; click any card to jump)"
        s1_t = "🎯 STEP 01. Research Topic"
        s1_d = "✅ Confirmed" if s1_done else "👉 Action Required: Enter & Confirm Topic"
        s2_t = "🧭 STEP 02. Algorithm & Filters"
        s2_d = f"✅ Confirmed ({mode_short})" if s2_done else ("👉 Action Required: Click Confirm Step 2" if s1_done else "⏳ Waiting for Step 1")
        s3_t = "🏛️ STEP 03. Journal Scope"
        s3_d = f"✅ Confirmed ({scope_short})" if s3_done else ("👉 Action Required: Click Confirm Step 3" if (s1_done and s2_done) else "⏳ Waiting for Step 2")
        s4_t = "🚀 STEP 04. Verify & Extract"
        s4_d = (
            "⚠️ Filters changed! Click Re-run" if is_stale else
            ("✅ Report generated below" if has_results else
             ("👉 Ready! Click Start in Step 4" if all_ready else "⏳ Complete Steps 1–3 first"))
        )
    else:
        header_txt = "📍 단계별 진행 상태판 (파란색 반짝이는 단계의 완료 버튼을 순서대로 눌러주세요 · 카드 클릭 시 해당 단계로 이동)"
        s1_t = "🎯 1단계: 연구 주제 입력"
        s1_d = "✅ 검색식 확정 완료" if s1_done else "👉 필수 진행: 검색어 입력 및 확정 클릭"
        s2_t = "🧭 2단계: 탐색 방식 · 필터"
        s2_d = f"✅ 확정 완료 ({mode_short})" if s2_done else ("👉 필수 클릭: 2단계 완료 버튼 눌러주세요" if s1_done else "⏳ 1단계 완료 후 진행")
        s3_t = "🏛️ 3단계: 학술지 범위"
        s3_d = f"✅ 확정 완료 ({scope_short})" if s3_done else ("👉 필수 클릭: 3단계 완료 버튼 눌러주세요" if (s1_done and s2_done) else "⏳ 2단계 완료 후 진행")
        s4_t = "🚀 4단계: 최종 점검 · 수집"
        s4_d = (
            "⚠️ 필터 변경됨! 재분석 클릭 필수" if is_stale else
            ("✅ 논문 수집 및 리포트 완료" if has_results else
             ("👉 준비 완료! 수집 시작 버튼 클릭" if all_ready else "⏳ 1~3단계를 먼저 확정해 주세요"))
        )

    st.markdown(f"""
    <div style="font-size:0.95rem; font-weight:800; color:#1E3A8A; margin-top:4px; margin-bottom:2px;">
        {header_txt}
    </div>
    <div class="stepper-wrap">
        <a href="#step-01-anchor" class="stepper-item {s1_state}">
            <div class="stepper-badge {s1_state}">{s1_badge}</div>
            <div>
                <div class="stepper-text-title">{s1_t}</div>
                <div class="stepper-text-sub">{s1_d}</div>
            </div>
        </a>
        <a href="#step-02-anchor" class="stepper-item {s2_state}">
            <div class="stepper-badge {s2_state}">{s2_badge}</div>
            <div>
                <div class="stepper-text-title">{s2_t}</div>
                <div class="stepper-text-sub">{s2_d}</div>
            </div>
        </a>
        <a href="#step-03-anchor" class="stepper-item {s3_state}">
            <div class="stepper-badge {s3_state}">{s3_badge}</div>
            <div>
                <div class="stepper-text-title">{s3_t}</div>
                <div class="stepper-text-sub">{s3_d}</div>
            </div>
        </a>
        <a href="#step-04-anchor" class="stepper-item {s4_state}">
            <div class="stepper-badge {s4_state}">{s4_badge}</div>
            <div>
                <div class="stepper-text-title">{s4_t}</div>
                <div class="stepper-text-sub">{s4_d}</div>
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)


def render_journal_html(info, lang="KO_EN"):
    if_val = info.get("if_2yr", "N/A")
    h_val = info.get("h_index", "N/A")
    pub_val = info.get("pub", "Unknown")
    works_val = int(info.get("works", 0) or 0)
    name_val = info.get("name", "Journal")
    issn_val = info.get("issn", "")
    jcr = info.get("jcr") or {}
    jcr_label = (f"{jcr.get('source', 'JCR')} JIF {jcr.get('jif')} · {jcr.get('best_quartile', '')}" if jcr.get("jif") is not None else "")
    jcr_title = ("Clarivate JCR official Journal Impact Factor and best quartile (institutional subscription data)" if lang == "EN"
                 else "Clarivate JCR 공식 영향력 지수(JIF)와 가장 좋은 분위 — 기관 구독 자료") + (f" · {jcr.get('label', '')}" if jcr.get("label") else "")
    if lang == "EN":
        issn_title = "ISSN: 8-digit international unique serial ID for this journal"
        if_title = "2Yr-IF (2-Year Impact Factor): Average citations received per paper published in the last 2 years"
        h_title = "H-Index (Academic Impact): At least H papers in this journal have been cited H or more times"
        pub_title = "Academic Publisher / Society"
        works_title = "Total indexed scholarly articles in this journal"
        if_label = f"⭐ 2Yr Impact (2Yr-IF, Avg Cites): {if_val}"
        h_label = f"📊 H-Index (Cumulative Authority): {h_val}"
        pub_label = f"🏢 Publisher: {pub_val}"
        works_label = f"📚 Indexed Works: {works_val:,}"
    else:
        issn_title = "ISSN(국제표준일련번호): 전 세계 학술지를 식별하는 8자리 고유 번호입니다."
        if_title = "2년 인용지수(2Yr-IF): 최근 2년간 이 학술지에 실린 논문 1편당 평균 피인용 횟수입니다. 높을수록 최신 파급력이 큽니다."
        h_title = "학술 영향력(H-index): 이 학술지에서 H번 이상 인용된 핵심 논문이 최소 H편 이상임을 뜻하는 누적 권위 지표입니다."
        pub_title = "학술지를 발행하는 국제 출판사 또는 학회입니다."
        works_title = "OpenAlex 데이터베이스에 등록된 이 학술지의 총 논문 수입니다."
        if_label = f"⭐ 2년 인용지수(2Yr-IF · 평균 인용): {if_val}"
        h_label = f"📊 학술 영향력(H-index · 누적 권위): {h_val}"
        pub_label = f"🏢 출판사: {pub_val}"
        works_label = f"📚 수록 논문: {works_val:,}편"

    return (
        f"<div style='margin-bottom: 4px; line-height: 1.62; word-break: keep-all; overflow-wrap: break-word;'>"
        f"<div style='font-weight: 800; font-size: 1.04rem; color: #0F172A; margin-bottom: 4px;'>"
        f"🏛️ {name_val} <span title='{issn_title}' style='font-weight: 600; color: #475569; font-size: 0.9rem; cursor: help; border-bottom: 1px dotted #94A3B8;'>(ISSN 고유번호: {issn_val})</span>"
        f"</div>"
        f"<div style='display: flex; flex-wrap: wrap; gap: 6px;'>"
        + (f"<span class='journal-badge badge-if' title='{jcr_title}' style='cursor: help; background:#ecfdf5; color:#065f46; border-color:#a7f3d0;'>🏅 {jcr_label}</span>" if jcr_label else "")
        + f"<span class='journal-badge badge-if' title='{if_title}' style='cursor: help;'>{if_label}</span>"
        f"<span class='journal-badge badge-h' title='{h_title}' style='cursor: help;'>{h_label}</span>"
        f"<span class='journal-badge badge-pub' title='{pub_title}'>{pub_label}</span>"
        f"<span class='journal-badge badge-works' title='{works_title}'>{works_label}</span>"
        f"</div></div>"
    )


def render_academic_glossary_panel(lang: str = "KO_EN"):
    """
    Renders a comprehensive, beginner-friendly Academic Terminology & Metrics Dictionary
    so any user can understand every bibliometric and academic term used across the platform.
    """
    if lang == "EN":
        html_content = """
        <div style="background:#FFFFFF; border:2px solid #2563EB; border-radius:15px; padding:18px 22px; margin-bottom:14px; box-shadow:0 4px 14px rgba(37,99,235,0.08);">
            <div style="font-size:1.12rem; font-weight:800; color:#1E3A8A; margin-bottom:6px;">
                📘 Easy Academic &amp; Bibliometric Terminology Guide (Understand While You Search)
            </div>
            <div style="font-size:0.93rem; color:#334155; margin-bottom:12px;">
                Hover over any metric or refer to this quick dictionary whenever you encounter unfamiliar academic indicators.
            </div>
            <div class="glossary-grid">
                <div class="glossary-card">
                    <div class="glossary-term-head">
                        <span>🔗 Network Hits (In-Network Co-Citations)</span>
                        <span class="glossary-term-tag">Root Snowballing Metric</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>How many recent papers in your search results cited this foundational paper together.</b><br>
                        Whereas Total Citations counts citations across all fields globally, Network Hits reveals the <b>true foundational root papers</b> specifically within your current research topic.
                    </div>
                </div>
                <div class="glossary-card">
                    <div class="glossary-term-head">
                        <span>📈 Total Citations &amp; Median Citations</span>
                        <span class="glossary-term-tag">Cumulative Impact</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>Total Citations:</b> Total number of times a paper has been cited by other scholarly works worldwide since publication.<br>
                        <b>Median Citations:</b> The middle value when papers are lined up by citation count (prevents 1–2 mega-hit papers from distorting the average).
                    </div>
                </div>
                <div class="glossary-card emerald">
                    <div class="glossary-term-head">
                        <span>🌍 FWCI (Field-Weighted Citation Impact)</span>
                        <span class="glossary-term-tag">1.0x = World Average</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>Relative citation impact normalized by publication year, document type, and academic field.</b><br>
                        <b>1.0x</b> equals the global average for similar papers. <b>2.5x</b> means the paper is cited <b>2.5 times more</b> than the world average in its exact field.
                    </div>
                </div>
                <div class="glossary-card emerald">
                    <div class="glossary-term-head">
                        <span>⚡ Citation Velocity (Citations / Year)</span>
                        <span class="glossary-term-tag">Hot Trend Speed</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>Average citations gained per year since publication (Total Citations ÷ Years since publication).</b><br>
                        Even if a newly published paper has fewer total citations than a 20-year-old classic, a high Citation Velocity shows it is <b>rapidly gaining attention right now</b>.
                    </div>
                </div>
                <div class="glossary-card indigo">
                    <div class="glossary-term-head">
                        <span>⭐ 2Yr Impact Factor (2Yr-IF / Citation Index)</span>
                        <span class="glossary-term-tag">Journal Prestige</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>Average number of citations received per paper published in a journal over the past 2 years.</b><br>
                        A higher 2Yr-IF means papers published in that journal receive immediate, high-impact attention from researchers worldwide.
                    </div>
                </div>
                <div class="glossary-card indigo">
                    <div class="glossary-term-head">
                        <span>📊 Academic Impact (H-Index) &amp; ISSN</span>
                        <span class="glossary-term-tag">Journal Authority &amp; ID</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>H-Index:</b> A journal has an H-index of <i>H</i> if at least <i>H</i> of its papers have been cited <i>H</i> or more times (measures sustained, cumulative authority).<br>
                        <b>ISSN:</b> An 8-digit international serial ID (e.g., <code>0028-0836</code> for <i>Nature</i>) that uniquely identifies a journal without title confusion.
                    </div>
                </div>
                <div class="glossary-card amber">
                    <div class="glossary-term-head">
                        <span>📑 Article vs Review vs Preprint &amp; Open Access (OA)</span>
                        <span class="glossary-term-tag">Document Types</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>Original Article:</b> New experimental/clinical research findings.<br>
                        <b>Review / Systematic Review:</b> Comprehensive synthesis of existing literature on a topic.<br>
                        <b>Preprint:</b> Early draft shared before formal peer review.<br>
                        <b>Open Access (OA):</b> Free full-text PDF available to anyone without paywalls.
                    </div>
                </div>
                <div class="glossary-card amber">
                    <div class="glossary-term-head">
                        <span>🔖 DOI · APA / AMA / BibTeX · RIS File</span>
                        <span class="glossary-term-tag">Citation &amp; Export</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>DOI:</b> Permanent digital link to a paper.<br>
                        <b>APA 7th / AMA / BibTeX:</b> Standard reference styles for social sciences (APA), medicine (AMA/Vancouver), and LaTeX (BibTeX).<br>
                        <b>.RIS File:</b> Universal bibliography file that imports all papers into EndNote, Zotero, or Mendeley in 1 click.
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        html_content = """
        <div style="background:#FFFFFF; border:2px solid #2563EB; border-radius:15px; padding:18px 22px; margin-bottom:14px; box-shadow:0 4px 14px rgba(37,99,235,0.08);">
            <div style="font-size:1.12rem; font-weight:800; color:#1E3A8A; margin-bottom:6px;">
                📘 처음 보는 분들을 위한 「학술·서지 용어 쉬운 해설집」 (사용하면서 바로 이해하는 핵심 지표 가이드)
            </div>
            <div style="font-size:0.93rem; color:#334155; margin-bottom:12px;">
                학술 검색에서 자주 등장하는 <b>공통인용, 총인용, FWCI, 인용속도, 인용지수(2Yr-IF), 학술 영향력(H-index), ISSN</b> 등 생소한 용어를 누구나 쉽게 이해할 수 있도록 정리했습니다.
            </div>
            <div class="glossary-grid">
                <div class="glossary-card">
                    <div class="glossary-term-head">
                        <span>🔗 공통인용 (Network Hits · 네트워크 내 동시 인용)</span>
                        <span class="glossary-term-tag">뿌리 역추적 핵심 지표</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>내가 검색한 최신 논문들이 '공통으로 함께 참고(인용)한 횟수'</b>입니다.<br>
                        예: 최신 논문 60편 중 18편이 특정 고전 논문을 동시에 참고문헌으로 인용했다면 <b>공통인용 = 18회</b>입니다. 내 연구 주제의 <b>진짜 기틀(뿌리)이 된 핵심 원전 논문</b>을 찾아내는 가장 정확한 지표입니다.
                    </div>
                </div>
                <div class="glossary-card">
                    <div class="glossary-term-head">
                        <span>📈 총인용 (Total Citations) &amp; 피인용 중앙값 (Median)</span>
                        <span class="glossary-term-tag">누적 영향력 지표</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>총인용(총 피인용):</b> 해당 논문이 출판된 이후 전 세계 모든 후속 논문들로부터 인용된 <b>전체 누적 횟수</b>입니다.<br>
                        <b>피인용 중앙값:</b> 논문들을 인용 순으로 한 줄로 세웠을 때 <b>정중앙(50%)에 위치한 값</b>으로, 극소수 초대박 논문 때문에 평균이 부풀려지는 착시를 막아줍니다.
                    </div>
                </div>
                <div class="glossary-card emerald">
                    <div class="glossary-term-head">
                        <span>🌍 FWCI (학문분야·연도 보정 영향력 지수)</span>
                        <span class="glossary-term-tag">1.0배 = 세계 평균</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>출판 연도·학문 분야·논문 유형이 같은 전 세계 논문들과 비교한 '상대적 영향력 배수'</b>입니다.<br>
                        <b>1.0배</b>가 세계 평균이며, 예를 들어 <b>FWCI 3.2배</b>라면 같은 해·같은 분야에서 나온 논문들보다 <b>3.2배나 더 많이 인용된 최상위급 논문</b>이라는 뜻입니다.
                    </div>
                </div>
                <div class="glossary-card emerald">
                    <div class="glossary-term-head">
                        <span>⚡ 인용속도 (연간 인용 속도 · Citation Velocity)</span>
                        <span class="glossary-term-tag">최신 급상승 척도 [회/년]</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>논문이 출판된 뒤 '1년에 평균 몇 번씩 인용되고 있는가'를 나타내는 속도(총인용 ÷ 경과 연수)</b>입니다.<br>
                        출판된 지 1~2년밖에 안 된 최신 논문은 누적 총인용이 적을 수 있지만, <b>인용속도(회/년)가 높다면 지금 학계에서 가장 뜨겁게 주목받는 급상승 논문</b>임을 뜻합니다.
                    </div>
                </div>
                <div class="glossary-card indigo">
                    <div class="glossary-term-head">
                        <span>⭐ 인용지수 (2년 인용지수 · 2Yr-IF / Impact Factor)</span>
                        <span class="glossary-term-tag">학술지 파급력 지표</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>해당 학술지(저널)에 최근 2년 동안 실린 논문 1편이 평균 몇 번 인용되었는지 나타내는 점수</b>입니다.<br>
                        일반 전공 학술지는 보통 <b>2~5점</b>, 분야 최상위 권위지는 <b>10점 이상</b>, <i>Nature·Lancet·NEJM</i> 같은 세계 최고 권위지는 <b>30~100점 이상</b>을 기록합니다.
                    </div>
                </div>
                <div class="glossary-card indigo">
                    <div class="glossary-term-head">
                        <span>📊 학술 영향력 (H-index) &amp; ISSN 고유번호</span>
                        <span class="glossary-term-tag">학술지 권위 · 식별번호</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>학술 영향력(H-index):</b> 그 학술지에서 <b>H번 이상 인용된 논문이 최소 H편 이상</b>이라는 뜻으로, 숫자가 클수록 오랜 기간 검증된 대표 권위지입니다.<br>
                        <b>ISSN(국제표준일련번호):</b> 전 세계 모든 학술지에 부여된 <b>8자리 고유 주민등록번호</b>(예: <code>0028-0836</code>)로, 이름이 비슷한 저널을 혼동 없이 정확히 찾아줍니다.
                    </div>
                </div>
                <div class="glossary-card amber">
                    <div class="glossary-term-head">
                        <span>📑 원저(Article) · 종설(Review) · 프리프린트 &amp; 오픈액세스(OA)</span>
                        <span class="glossary-term-tag">문헌 유형 · 무료 원문</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>원저(Article):</b> 새로운 실험·임상·설문 데이터를 직접 분석한 일반 연구 논문입니다.<br>
                        <b>종설·체계적 문헌고찰(Review):</b> 특정 주제의 기존 논문 수십~수백 편을 종합 정리해 연구 흐름을 한눈에 파악하기 좋은 논문입니다.<br>
                        <b>프리프린트(Preprint):</b> 정식 심사 전에 빠르게 공개한 초안 논문 / <b>오픈 액세스(OA):</b> 결제 없이 <b>무료로 전문(PDF) 열람·다운로드</b>가 가능한 논문입니다.
                    </div>
                </div>
                <div class="glossary-card amber">
                    <div class="glossary-term-head">
                        <span>🔖 DOI · 인용 양식(APA/AMA/BibTeX) · 서지 파일(.ris)</span>
                        <span class="glossary-term-tag">출처 표기 · 서지 관리</span>
                    </div>
                    <div class="glossary-term-desc">
                        <b>DOI:</b> 논문마다 부여된 영구 인터넷 주소 링크입니다.<br>
                        <b>APA 7판 / AMA / BibTeX:</b> 사회·심리·일반 학술지 표준(APA), 의학·보건 계열 번호형 표준(AMA), LaTeX 수식 논문용 코드(BibTeX)입니다.<br>
                        <b>서지 파일(.ris):</b> 다운로드한 뒤 <b>EndNote · Zotero · Mendeley</b>에서 열면 수집된 논문 전체가 참고문헌 라이브러리에 자동 등록되는 파일입니다.
                    </div>
                </div>
            </div>
        </div>
        """
    st.markdown(html_content, unsafe_allow_html=True)



def render_interactive_citations(cites_dict: dict, lang: str = "KO_EN"):
    apa_escaped = html.escape(cites_dict.get("apa", ""))
    ama_escaped = html.escape(cites_dict.get("ama", ""))
    bib_escaped = html.escape(cites_dict.get("bibtex", ""))

    if lang == "EN":
        title_apa = "📘 APA 7th Style (Social & General Sciences)"
        title_ama = "📗 AMA / Vancouver Style (Medical & Health)"
        title_bib = "📙 BibTeX Code (LaTeX & Overleaf)"
        btn_default = "📋 Copy Citation to Clipboard"
        btn_copied = "✅ Copied! (Press Ctrl+V to paste)"
    else:
        title_apa = "📘 APA 7판 양식 (사회·교육·심리·일반 학술지)"
        title_ama = "📗 AMA / Vancouver 양식 (의학·보건·생명과학)"
        title_bib = "📙 BibTeX 서지 코드 (LaTeX · Overleaf 논문용)"
        btn_default = "📋 이 인용문 원클릭 복사하기"
        btn_copied = "✅ 클립보드에 복사 완료! (Ctrl+V로 붙여넣으세요)"

    widget_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
        * {{
            box-sizing: border-box;
            font-family: 'Pretendard Variable', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        body {{
            margin: 0;
            padding: 2px;
            background: transparent;
        }}
        .cite-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
        }}
        @media (max-width: 860px) {{
            .cite-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .cite-card {{
            background: #F8FAFC;
            border: 1.5px solid #CBD5E1;
            border-radius: 12px;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s ease;
        }}
        .cite-card.copied {{
            background: #F0FDF4;
            border-color: #22C55E;
            box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18);
        }}
        .cite-title {{
            font-size: 0.96rem;
            font-weight: 800;
            color: #0F172A;
            margin-bottom: 8px;
            word-break: keep-all;
        }}
        .cite-box {{
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 12px;
            font-size: 0.92rem;
            line-height: 1.58;
            color: #1E293B;
            word-break: break-word;
            white-space: pre-wrap;
            height: 125px;
            overflow-y: auto;
            margin-bottom: 10px;
            font-family: 'Pretendard Variable', monospace;
        }}
        .copy-btn {{
            width: 100%;
            padding: 10px 14px;
            border-radius: 9px;
            border: 1.5px solid #2563EB;
            background: #EFF6FF;
            color: #1D4ED8;
            font-size: 0.94rem;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.15s ease;
            text-align: center;
            word-break: keep-all;
        }}
        .copy-btn:hover {{
            background: #2563EB;
            color: #FFFFFF;
        }}
        .copy-btn.success {{
            background: #16A34A !important;
            border-color: #15803D !important;
            color: #FFFFFF !important;
            transform: scale(1.01);
        }}
    </style>
    </head>
    <body>
        <div class="cite-grid">
            <div class="cite-card" id="card-apa">
                <div>
                    <div class="cite-title">{title_apa}</div>
                    <div class="cite-box" id="txt-apa">{apa_escaped}</div>
                </div>
                <button class="copy-btn" id="btn-apa" onclick="copyCitation('txt-apa', 'btn-apa', 'card-apa')">{btn_default}</button>
            </div>
            <div class="cite-card" id="card-ama">
                <div>
                    <div class="cite-title">{title_ama}</div>
                    <div class="cite-box" id="txt-ama">{ama_escaped}</div>
                </div>
                <button class="copy-btn" id="btn-ama" onclick="copyCitation('txt-ama', 'btn-ama', 'card-ama')">{btn_default}</button>
            </div>
            <div class="cite-card" id="card-bib">
                <div>
                    <div class="cite-title">{title_bib}</div>
                    <div class="cite-box" id="txt-bib">{bib_escaped}</div>
                </div>
                <button class="copy-btn" id="btn-bib" onclick="copyCitation('txt-bib', 'btn-bib', 'card-bib')">{btn_default}</button>
            </div>
        </div>

        <script>
        function copyCitation(txtId, btnId, cardId) {{
            var text = document.getElementById(txtId).innerText;
            var btn = document.getElementById(btnId);
            var card = document.getElementById(cardId);

            function showSuccess() {{
                btn.innerText = "{btn_copied}";
                btn.classList.add("success");
                card.classList.add("copied");
                setTimeout(function() {{
                    btn.innerText = "{btn_default}";
                    btn.classList.remove("success");
                    card.classList.remove("copied");
                }}, 3500);
            }}

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(showSuccess).catch(function() {{
                    fallbackCopy(text, showSuccess);
                }});
            }} else {{
                fallbackCopy(text, showSuccess);
            }}
        }}

        function fallbackCopy(text, callback) {{
            var ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.left = "-9999px";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try {{
                document.execCommand('copy');
                callback();
            }} catch (e) {{}}
            document.body.removeChild(ta);
        }}
        </script>
    </body>
    </html>
    """
    components.html(widget_html, height=235, scrolling=False)


def render_auto_scroll_and_keepalive(target_anchor: str = "", scroll_seq: int = 0, auth_token: str = "", sid: str = ""):
    """
    Smoothly scrolls the parent Streamlit viewport to `target_anchor` when triggered and highlights the banner.
    Renders nothing when `target_anchor` is empty so normal interactions have zero extra iframe overhead.
    """
    if not target_anchor:
        return

    safe_anchor = html.escape(str(target_anchor))
    seq_val = int(scroll_seq or 0)

    js_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;overflow:hidden;">
    <script>
    (function() {{
        var anchorId = "{safe_anchor}";
        var seqVal = {seq_val};

        try {{
            var pWin = window.parent;
            var pDoc = pWin.document;

            if (anchorId && pWin.__omniLastScrollSeq !== seqVal) {{
                pWin.__omniLastScrollSeq = seqVal;
                setTimeout(function() {{
                    var targetEl = pDoc.getElementById(anchorId);
                    if (targetEl) {{
                        targetEl.scrollIntoView({{ behavior: "smooth", block: "start" }});
                        var origShadow = targetEl.style.boxShadow;
                        var origTransform = targetEl.style.transform;
                        var origTransition = targetEl.style.transition;
                        targetEl.style.transition = "all 0.35s ease";
                        targetEl.style.boxShadow = "0 0 0 5px #F59E0B, 0 10px 28px rgba(245, 158, 11, 0.45)";
                        targetEl.style.transform = "scale(1.01)";
                        setTimeout(function() {{
                            targetEl.style.boxShadow = origShadow;
                            targetEl.style.transform = origTransform;
                            targetEl.style.transition = origTransition;
                        }}, 2800);
                    }}
                }}, 100);
            }}
        }} catch (err) {{}}
    }})();
    </script>
    </body>
    </html>
    """
    components.html(js_html, height=0, scrolling=False)

