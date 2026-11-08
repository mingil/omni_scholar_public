import re
import difflib
import requests
from modules.logger_setup import logger

# ==========================================
# 🧠 Built-in Academic Korean-to-English Thesaurus
# ==========================================
KO_ACADEMIC_THESAURUS = {
    # Medicine & Rehabilitation
    "뇌졸중": "stroke",
    "뇌경색": '"ischemic stroke"',
    "뇌출혈": '"hemorrhagic stroke"',
    "연하장애": "(dysphagia OR swallowing)",
    "삼킴장애": "(dysphagia OR swallowing)",
    "비디오투시연하검사": "(VFSS OR videofluoroscopic)",
    "흡인성 폐렴": '"aspiration pneumonia"',
    "흡인성폐렴": '"aspiration pneumonia"',
    "폐렴": "pneumonia",
    "재활치료": "rehabilitation",
    "재활": "rehabilitation",
    "물리치료": '"physical therapy"',
    # 재활의학 용어 보강 (2026-11-08: 구글 무료 번역이 막히면 사전에 없는 단어가 조용히 빠지던 문제)
    "상지": '("upper limb" OR "upper extremity")',
    "하지": '("lower limb" OR "lower extremity")',
    "편마비": "(hemiparesis OR hemiplegia)",
    "경직": "spasticity",
    "실어증": "aphasia",
    "구음장애": "dysarthria",
    "인지재활": '"cognitive rehabilitation"',
    "인지장애": '"cognitive impairment"',
    "인지기능": '"cognitive function"',
    "통증": "pain",
    "요통": '"low back pain"',
    "근력": '"muscle strength"',
    "운동치료": '"exercise therapy"',
    "보행훈련": '"gait training"',
    "보조기": "orthosis",
    "외골격": "exoskeleton",
    "기능적 전기자극": '"functional electrical stimulation"',
    "전기자극": '"electrical stimulation"',
    "거울치료": '"mirror therapy"',
    "강제유도운동치료": '"constraint-induced movement therapy"',
    "원격재활": "telerehabilitation",
    "심장재활": '"cardiac rehabilitation"',
    "호흡재활": '"pulmonary rehabilitation"',
    "폐재활": '"pulmonary rehabilitation"',
    "림프부종": "lymphedema",
    "체외충격파": '"extracorporeal shockwave"',
    "보툴리눔": "botulinum",
    "보톡스": "botulinum",
    "뇌성마비": '"cerebral palsy"',
    "다발성 경화증": '"multiple sclerosis"',
    "다발성경화증": '"multiple sclerosis"',
    "일상생활동작": '"activities of daily living"',
    "일상생활": '"activities of daily living"',
    "삶의 질": '"quality of life"',
    "낙상": "falls",
    "어깨": "shoulder",
    "무릎": "knee",
    "척추": "spine",
    "초음파": "ultrasound",
    "예방": "prevention",
    "기능": "function",
    "회복": "recovery",
    "작업치료": '"occupational therapy"',
    "언어치료": '"speech therapy"',
    "파킨슨병": "Parkinson",
    "파킨슨": "Parkinson",
    "치매": "(dementia OR Alzheimer)",
    "알츠하이머": "Alzheimer",
    "척수손상": '"spinal cord injury"',
    "외상성 뇌손상": '"traumatic brain injury"',
    "뇌손상": '"brain injury"',
    "비침습적 뇌자극": '"non-invasive brain stimulation"',
    "경두개직류자극": "tDCS",
    "경두개자기자극": "rTMS",
    "보행": "gait",
    "균형": "balance",
    "근감소증": "sarcopenia",
    "골다공증": "osteoporosis",
    "골관절염": "osteoarthritis",
    "류마티스 관절염": '"rheumatoid arthritis"',
    "류마티스관절염": '"rheumatoid arthritis"',
    "심부전": '"heart failure"',
    "심근경색": '"myocardial infarction"',
    "당뇨병": "diabetes",
    "당뇨": "diabetes",
    "고혈압": "hypertension",
    "암": "cancer",
    "종양": "(tumor OR oncology)",
    "면역치료": "immunotherapy",
    "항암": "chemotherapy",
    "임상시험": '"clinical trial"',
    "무작위 대조 임상시험": '"randomized controlled trial"',
    "임상": "clinical",
    "전자의무기록": "(EHR OR EMR)",
    "의무기록": '(EHR OR "clinical notes")',
    "예후": "prognosis",
    "진단": "diagnosis",
    "예측": "prediction",
    "사망률": "mortality",
    "노인": "(elderly OR geriatric)",
    "소아": "pediatric",
    "우울증": "depression",
    "조현병": "schizophrenia",
    "불안장애": "anxiety",

    # AI, Computer Science & Data Science
    "인공지능": '("artificial intelligence" OR AI)',
    "머신러닝": '"machine learning"',
    "기계학습": '"machine learning"',
    "딥러닝": '"deep learning"',
    "심층학습": '"deep learning"',
    "거대언어모델": '("large language model" OR LLM)',
    "대규모언어모델": '("large language model" OR LLM)',
    "대형언어모델": '("large language model" OR LLM)',
    "자연어처리": '("natural language processing" OR NLP)',
    "자연어 처리": '("natural language processing" OR NLP)',
    "컴퓨터비전": '"computer vision"',
    "컴퓨터 비전": '"computer vision"',
    "강화학습": '"reinforcement learning"',
    "신경망": '"neural network"',
    "트랜스포머": "transformer",
    "빅데이터": '"big data"',
    "알고리즘": "algorithm",
    "로봇": "robotics",
    "웨어러블": "wearable",
    "가상현실": '"virtual reality"',
    "증강현실": '"augmented reality"',
    "디지털 치료제": '"digital therapeutics"',
    "디지털 헬스케어": '"digital health"',

    # Science, Engineering & Economics
    "양자컴퓨팅": '"quantum computing"',
    "양자 컴퓨팅": '"quantum computing"',
    "기후변화": '"climate change"',
    "기후 변화": '"climate change"',
    "탄소중립": '"carbon neutrality"',
    "신재생에너지": '"renewable energy"',
    "배터리": "battery",
    "반도체": "semiconductor",
    "유전자편집": '"gene editing"',
    "유전자": "genetic",
    "단백질": "protein",
    "줄기세포": '"stem cell"',
    "마이크로바이옴": "microbiome",
    "메타분석": '"meta-analysis"',
    "체계적 문헌고찰": '"systematic review"',
    "문헌고찰": "review",
    "경제성장": '"economic growth"',
    "인플레이션": "inflation",
    "금융": "finance",
}

# ==========================================
# 🪄 Built-in Korean & English Academic Typo Correction Maps
# ==========================================
KO_TYPO_CORRECTIONS = {
    "뇌졸증": "뇌졸중",
    "뇌경섹": "뇌경색",
    "뇌출헐": "뇌출혈",
    "연하장해": "연하장애",
    "삼킴장해": "삼킴장애",
    "흡입성 폐렴": "흡인성 폐렴",
    "흡입성폐렴": "흡인성 폐렴",
    "파킨슨씨병": "파킨슨병",
    "파킨슨씨": "파킨슨병",
    "알츠하이머치매": "알츠하이머",
    "알쯔하이머": "알츠하이머",
    "근감소증환자": "근감소증",
    "인공지눙": "인공지능",
    "머신러님": "머신러닝",
    "머신런닝": "머신러닝",
    "딥러님": "딥러닝",
    "딥런닝": "딥러닝",
    "메타분석연구": "메타분석",
    "체계적문헌고찰": "체계적 문헌고찰",
    "류마티즘": "류마티스 관절염",
    "골관절염환자": "골관절염",
}

EN_PHRASE_TYPO_CORRECTIONS = {
    "machin learning": "machine learning",
    "mechine learning": "machine learning",
    "machine learing": "machine learning",
    "machine lerning": "machine learning",
    "deep learing": "deep learning",
    "deep lerning": "deep learning",
    "artifical intelligence": "artificial intelligence",
    "artificial inteligence": "artificial intelligence",
    "artifcial intelligence": "artificial intelligence",
    "large language modle": "large language model",
    "natural language procesing": "natural language processing",
    "aspriation pneumonia": "aspiration pneumonia",
    "aspiration pnuemonia": "aspiration pneumonia",
    "aspiration pnumonia": "aspiration pneumonia",
    "systemic review": "systematic review",
    "systematc review": "systematic review",
    "systmatic review": "systematic review",
    "meta anaysis": "meta-analysis",
    "meta-anaysis": "meta-analysis",
    "meta-anlaysis": "meta-analysis",
    "spinal cord injuy": "spinal cord injury",
    "traumatic brain injuy": "traumatic brain injury",
    "clincal trial": "clinical trial",
    "clincal decision support": "clinical decision support",
    "randomised controlled trial": "randomized controlled trial",
    "randomized controled trial": "randomized controlled trial",
}

EN_WORD_TYPO_CORRECTIONS = {
    # Dysphagia / Swallowing / Stroke / Rehab
    "dyspagia": "dysphagia",
    "disphagia": "dysphagia",
    "dysphgia": "dysphagia",
    "dysfagia": "dysphagia",
    "dyphagia": "dysphagia",
    "swalowing": "swallowing",
    "swallwing": "swallowing",
    "storke": "stroke",
    "strok": "stroke",
    "strke": "stroke",
    "rehabilitaion": "rehabilitation",
    "rehablitation": "rehabilitation",
    "rehabiliation": "rehabilitation",
    "rehabiltation": "rehabilitation",
    "rehabilitaiton": "rehabilitation",
    "pnuemonia": "pneumonia",
    "pnumonia": "pneumonia",
    "pnemonia": "pneumonia",
    "aspriation": "aspiration",
    "aspiraton": "aspiration",
    # Neurology / Aging / Internal Medicine
    "alzhimer": "Alzheimer",
    "alzheimers": "Alzheimer",
    "alzeimer": "Alzheimer",
    "alzhiemer": "Alzheimer",
    "parkinsons": "Parkinson",
    "parkison": "Parkinson",
    "dementa": "dementia",
    "demetia": "dementia",
    "sarcopena": "sarcopenia",
    "sarcopnia": "sarcopenia",
    "osteoporsis": "osteoporosis",
    "osteoporisis": "osteoporosis",
    "osteoarthrtis": "osteoarthritis",
    "osteoarthrits": "osteoarthritis",
    "cardiovasular": "cardiovascular",
    "cardivascular": "cardiovascular",
    "cardiovascuar": "cardiovascular",
    "myocaridal": "myocardial",
    "myocardal": "myocardial",
    "infraction": "infarction",
    "infartion": "infarction",
    "hypertention": "hypertension",
    "hipertension": "hypertension",
    "diabtes": "diabetes",
    "diabetis": "diabetes",
    "schizoprenia": "schizophrenia",
    "schizofrenia": "schizophrenia",
    "depresion": "depression",
    "deppression": "depression",
    "oncolgy": "oncology",
    "oncoloy": "oncology",
    "immunotherpy": "immunotherapy",
    "imunotherapy": "immunotherapy",
    "immunotheraphy": "immunotherapy",
    "chemotherpy": "chemotherapy",
    "chemotheraphy": "chemotherapy",
    "clincal": "clinical",
    "clinicial": "clinical",
    "prognoss": "prognosis",
    "prognsis": "prognosis",
    "diagnoss": "diagnosis",
    "diagnsis": "diagnosis",
    "pediatrc": "pediatric",
    "geriatrc": "geriatric",
    "neurologi": "neurology",
    "nuerology": "neurology",
    "pschiatry": "psychiatry",
    "psychiaty": "psychiatry",
    # AI / Tech
    "machin": "machine",
    "mechine": "machine",
    "mahcine": "machine",
    "learing": "learning",
    "lerning": "learning",
    "leanring": "learning",
    "artifical": "artificial",
    "artifcial": "artificial",
    "aritficial": "artificial",
    "inteligence": "intelligence",
    "intellgence": "intelligence",
    "intelligance": "intelligence",
    "transfomer": "transformer",
    "tranformer": "transformer",
    "transfromer": "transformer",
    "nueral": "neural",
    "nerual": "neural",
    "netwrok": "network",
    "netowrk": "network",
    "algoritm": "algorithm",
    "algorthm": "algorithm",
    # Journals / Publishers
    "lancett": "Lancet",
    "lacet": "Lancet",
    "nautre": "Nature",
    "natre": "Nature",
    "scinece": "Science",
    "sicence": "Science",
    "springerlink": "Springer",
    "elseveir": "Elsevier",
    "elsvier": "Elsevier",
}

# Canonical vocabulary for fuzzy matching (difflib) when an unknown word is very close to a known medical/academic term
CANONICAL_EN_VOCAB = [
    "dysphagia", "swallowing", "stroke", "rehabilitation", "pneumonia", "aspiration",
    "alzheimer", "parkinson", "dementia", "sarcopenia", "osteoporosis", "osteoarthritis",
    "cardiovascular", "myocardial", "infarction", "hypertension", "diabetes", "obesity",
    "cancer", "oncology", "immunotherapy", "chemotherapy", "radiotherapy", "carcinoma",
    "neurology", "neuroscience", "neuroplasticity", "neuroimaging", "psychiatry",
    "depression", "schizophrenia", "anxiety", "epilepsy", "afibrillation", "arrhythmia",
    "clinical", "prognosis", "diagnosis", "mortality", "morbidity", "epidemiology",
    "pediatric", "geriatric", "orthopedics", "rheumatology", "gastroenterology",
    "pulmonology", "nephrology", "endocrinology", "hematology", "surgery", "anesthesiology",
    "machine", "learning", "artificial", "intelligence", "transformer", "neural", "network",
    "robotics", "wearable", "telemedicine", "biomarker", "genomics", "proteomics",
    "microbiome", "crispr", "quantum", "semiconductor", "battery", "photovoltaic",
    "meta-analysis", "systematic", "randomized", "placebo", "cohort", "longitudinal",
    "videofluoroscopic", "endoscopic", "transcranial", "stimulation", "spasticity",
    "aphasia", "hemiplegia", "paraplegia", "tetraplegia", "gait", "balance", "locomotion",
]

# Curated Autocomplete Catalog for Step 1 & Query Builder (No-Typo Quick Selection)
ACADEMIC_AUTOCOMPLETE_CATALOG = [
    {"cat": "🧠 신경·재활·뇌질환", "ko": "뇌졸중 (Stroke)", "en": "Stroke", "query": "stroke"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "연하장애 · 삼킴장애 (Dysphagia)", "en": "Dysphagia / Swallowing", "query": "(dysphagia OR swallowing)"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "흡인성 폐렴 (Aspiration Pneumonia)", "en": "Aspiration Pneumonia", "query": '"aspiration pneumonia"'},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "비디오투시연하검사 (VFSS)", "en": "VFSS (Videofluoroscopic)", "query": "(VFSS OR videofluoroscopic)"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "재활치료 · 물리/작업치료 (Rehabilitation)", "en": "Rehabilitation", "query": "rehabilitation"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "비침습적 뇌자극 (tDCS · rTMS)", "en": "Non-invasive Brain Stimulation (tDCS/rTMS)", "query": '("non-invasive brain stimulation" OR tDCS OR rTMS)'},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "척수손상 (Spinal Cord Injury)", "en": "Spinal Cord Injury", "query": '"spinal cord injury"'},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "외상성 뇌손상 (Traumatic Brain Injury)", "en": "Traumatic Brain Injury", "query": '"traumatic brain injury"'},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "파킨슨병 (Parkinson's Disease)", "en": "Parkinson's Disease", "query": "Parkinson"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "치매 · 알츠하이머 (Dementia / Alzheimer)", "en": "Dementia / Alzheimer", "query": "(dementia OR Alzheimer)"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "보행 및 균형 재활 (Gait & Balance)", "en": "Gait & Balance", "query": "(gait OR balance)"},
    {"cat": "🧠 신경·재활·뇌질환", "ko": "근감소증 (Sarcopenia)", "en": "Sarcopenia", "query": "sarcopenia"},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "머신러닝 · 기계학습 (Machine Learning)", "en": "Machine Learning", "query": '"machine learning"'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "딥러닝 · 심층학습 (Deep Learning)", "en": "Deep Learning", "query": '"deep learning"'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "인공지능 통합 (Artificial Intelligence / AI)", "en": "Artificial Intelligence (AI)", "query": '("artificial intelligence" OR AI)'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "거대언어모델 (Large Language Model / LLM)", "en": "Large Language Models (LLM)", "query": '("large language model" OR LLM)'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "임상 의사결정 지원 (Clinical Decision Support)", "en": "Clinical Decision Support", "query": '"clinical decision support"'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "전자의무기록 분석 (EHR / EMR)", "en": "Electronic Health Records (EHR)", "query": '(EHR OR EMR OR "electronic health records")'},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "웨어러블 · 로봇 재활 (Wearable / Robotics)", "en": "Wearable & Robotics", "query": "(wearable OR robotics)"},
    {"cat": "🤖 AI·머신러닝·디지털헬스", "ko": "가상현실 · 디지털 치료제 (VR / Digital Therapeutics)", "en": "Virtual Reality / Digital Therapeutics", "query": '("virtual reality" OR "digital therapeutics")'},
    {"cat": "🫀 내과·암·만성질환·임상", "ko": "암 면역치료 (Cancer Immunotherapy)", "en": "Cancer Immunotherapy", "query": '"immunotherapy" cancer'},
    {"cat": "🫀 내과·암·만성질환·임상", "ko": "심부전 · 심근경색 (Heart Failure / MI)", "en": "Heart Failure / Myocardial Infarction", "query": '("heart failure" OR "myocardial infarction")'},
    {"cat": "🫀 내과·암·만성질환·임상", "ko": "당뇨병 · 고혈압 (Diabetes / Hypertension)", "en": "Diabetes / Hypertension", "query": "(diabetes OR hypertension)"},
    {"cat": "🫀 내과·암·만성질환·임상", "ko": "골다공증 · 골관절염 (Osteoporosis / Osteoarthritis)", "en": "Osteoporosis / Osteoarthritis", "query": "(osteoporosis OR osteoarthritis)"},
    {"cat": "📊 연구방법론·문헌고찰", "ko": "체계적 문헌고찰 · 메타분석 (Systematic Review / Meta-analysis)", "en": "Systematic Review & Meta-analysis", "query": '("systematic review" OR "meta-analysis")'},
    {"cat": "📊 연구방법론·문헌고찰", "ko": "무작위 대조 임상시험 (Randomized Controlled Trial)", "en": "Randomized Controlled Trial (RCT)", "query": '"randomized controlled trial"'},
    {"cat": "📊 연구방법론·문헌고찰", "ko": "예후 및 예측 모델 (Prognosis & Prediction)", "en": "Prognosis & Prediction", "query": "(prognosis OR prediction)"},
    {"cat": "🧬 생명·공학·에너지·경제", "ko": "유전자 편집 · 줄기세포 (Gene Editing / Stem Cell)", "en": "Gene Editing / Stem Cell", "query": '("gene editing" OR "stem cell")'},
    {"cat": "🧬 생명·공학·에너지·경제", "ko": "마이크로바이옴 (Microbiome)", "en": "Microbiome", "query": "microbiome"},
    {"cat": "🧬 생명·공학·에너지·경제", "ko": "기후변화 · 탄소중립 (Climate Change / Carbon Neutrality)", "en": "Climate Change & Renewable Energy", "query": '("climate change" OR "renewable energy")'},
    {"cat": "🧬 생명·공학·에너지·경제", "ko": "양자컴퓨팅 · 반도체 (Quantum Computing / Semiconductor)", "en": "Quantum Computing & Semiconductor", "query": '("quantum computing" OR semiconductor)'},
]

# Popular Journal Search Keywords for Step 3 Tab 2 Autocomplete
JOURNAL_SEARCH_SUGGESTIONS = [
    {"label": "🧠 Stroke (뇌졸중 최고 권위지)", "label_ko": "🧠 Stroke (뇌졸중 최고 권위지)", "label_en": "🧠 Stroke", "kw": "Stroke"},
    {"label": "🗣️ Dysphagia (연하장애 전문지)", "label_ko": "🗣️ Dysphagia (연하장애 전문지)", "label_en": "🗣️ Dysphagia", "kw": "Dysphagia"},
    {"label": "♿ Rehabilitation (재활의학 전체)", "label_ko": "♿ Rehabilitation (재활의학 전체)", "label_en": "♿ Rehabilitation", "kw": "Rehabilitation"},
    {"label": "🏛️ Archives of Physical Medicine (APMR)", "label_ko": "🏛️ Archives of Physical Medicine (APMR)", "label_en": "🏛️ Archives of Physical Medicine", "kw": "Archives of Physical Medicine"},
    {"label": "🔬 Neurorehabilitation (신경재활)", "label_ko": "🔬 Neurorehabilitation (신경재활)", "label_en": "🔬 Neurorehabilitation", "kw": "Neurorehabilitation"},
    {"label": "🧠 Neurology / Lancet Neurology", "label_ko": "🧠 Neurology / Lancet Neurology", "label_en": "🧠 Neurology", "kw": "Neurology"},
    {"label": "🏥 New England Journal of Medicine", "label_ko": "🏥 New England Journal of Medicine", "label_en": "🏥 New England Journal of Medicine", "kw": "New England Journal of Medicine"},
    {"label": "🌍 The Lancet (란셋 시리즈)", "label_ko": "🌍 The Lancet (란셋 시리즈)", "label_en": "🌍 The Lancet", "kw": "Lancet"},
    {"label": "⭐ Nature / Nature Medicine", "label_ko": "⭐ Nature / Nature Medicine", "label_en": "⭐ Nature Medicine", "kw": "Nature Medicine"},
    {"label": "🤖 IEEE / Artificial Intelligence", "label_ko": "🤖 IEEE / Artificial Intelligence", "label_en": "🤖 Artificial Intelligence", "kw": "Artificial Intelligence"},
    {"label": "🎗️ Oncology / Cancer (종양학)", "label_ko": "🎗️ Oncology / Cancer (종양학)", "label_en": "🎗️ Oncology", "kw": "Oncology"},
    {"label": "🫀 Circulation / Cardiology (심장학)", "label_ko": "🫀 Circulation / Cardiology (심장학)", "label_en": "🫀 Circulation", "kw": "Circulation"},
]

# Known English multi-word academic phrases to preserve together when parsing natural language
KNOWN_EN_PHRASES = [
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "large language model",
    "large language models",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
    "neural network",
    "neural networks",
    "clinical trial",
    "clinical trials",
    "clinical notes",
    "clinical decision support",
    "electronic health records",
    "electronic health record",
    "aspiration pneumonia",
    "ischemic stroke",
    "hemorrhagic stroke",
    "spinal cord injury",
    "traumatic brain injury",
    "brain stimulation",
    "non-invasive brain stimulation",
    "physical therapy",
    "occupational therapy",
    "speech therapy",
    "stroke rehabilitation",
    "heart failure",
    "myocardial infarction",
    "rheumatoid arthritis",
    "breast cancer",
    "lung cancer",
    "colorectal cancer",
    "stem cell",
    "stem cells",
    "gene editing",
    "climate change",
    "renewable energy",
    "quantum computing",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "randomized controlled trial",
    "virtual reality",
    "augmented reality",
    "digital therapeutics",
    "digital health",
    "public health",
    "mental health",
    "supply chain",
    "economic growth",
]

# English conversational & filler stopwords to strip from natural language questions
EN_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "where", "why", "how",
    "what", "which", "who", "whom", "whose", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "can", "could", "should",
    "would", "may", "might", "must", "shall", "will", "about", "above", "across", "after",
    "against", "along", "among", "around", "at", "before", "behind", "below", "beneath",
    "beside", "between", "beyond", "by", "concerning", "considering", "despite", "down",
    "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off",
    "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through",
    "throughout", "to", "toward", "towards", "under", "underneath", "until", "unto", "up",
    "upon", "with", "within", "without", "using", "use", "used", "utilizing", "utilize",
    "based", "study", "studies", "research", "paper", "papers", "article", "articles",
    "literature", "find", "search", "show", "me", "please", "tell", "give", "recent",
    "latest", "new", "advances", "effect", "effects", "impact", "impacts", "role", "roles",
    "relationship", "between", "among", "patients", "patient", "people", "human", "humans",
    "analysis", "investigate", "investigation", "evaluation", "evaluate", "assess",
    "assessment", "method", "methods", "approach", "approaches", "application", "applications",
    "help", "helps", "helping", "improve", "improving", "effective", "efficacy", "whether",
    "there", "any", "some", "many", "most", "more", "other", "such", "as", "than", "too",
    "very", "just", "only", "also", "I", "want", "need", "know", "looking"
}

# Korean conversational endings & filler words to strip before processing
KO_FILLER_PATTERNS = [
    r"에\s*대한", r"에\s*관한", r"을\s*이용한", r"를\s*이용한", r"을\s*활용한", r"를\s*활용한",
    r"을\s*통한", r"를\s*통한", r"에서의", r"에서", r"으로", r"로써", r"로서",
    r"환자들?의?", r"환자", r"연구들?을?", r"연구", r"논문들?을?", r"논문",
    r"찾아줘요?", r"찾아주세요", r"찾아봐줘", r"알려줘요?", r"알려주세요", r"검색해줘요?", r"검색해주세요",
    r"보여줘요?", r"보여주세요", r"추천해줘", r"무엇인가요", r"어떤가요", r"있나요", r"할까요",
    r"관한", r"대한", r"관련된", r"관련", r"최신", r"최근", r"대표적인", r"핵심", r"효과", r"영향", r"분석",
    r"치료법", r"치료", r"방법"
]


def detect_and_correct_typos(raw_text: str) -> dict:
    """
    Inspects user input (Korean or English) for common academic/medical typos and fuzzy misspellings.

    Returns:
        {
            "has_typo": bool,
            "original": str,
            "corrected": str,
            "corrections": list of (wrong_str, right_str),
            "suggestions": list of dict (matching autocomplete items)
        }
    """
    text = (raw_text or "").strip()
    if not text:
        return {
            "has_typo": False,
            "original": "",
            "corrected": "",
            "corrected_text": "",
            "corrections": [],
            "suggestions": [],
        }

    working = text
    corrections = []

    # 1. Korean typo dictionary check
    for wrong_ko, right_ko in KO_TYPO_CORRECTIONS.items():
        if wrong_ko in working:
            working = working.replace(wrong_ko, right_ko)
            corrections.append((wrong_ko, right_ko))

    # 2. English multi-word phrase typo check (case-insensitive)
    for wrong_ph, right_ph in EN_PHRASE_TYPO_CORRECTIONS.items():
        pattern = re.compile(re.escape(wrong_ph), re.IGNORECASE)
        if pattern.search(working):
            working = pattern.sub(right_ph, working)
            corrections.append((wrong_ph, right_ph))

    # 3. Individual English word typo check + fuzzy matching against CANONICAL_EN_VOCAB
    tokens = re.findall(r"[A-Za-z\-]{3,}", working)
    already_replaced = set()
    for tok in tokens:
        tok_low = tok.lower()
        if tok_low in already_replaced or tok_low in EN_STOPWORDS or tok_low in ("and", "not"):
            continue
        if tok_low in EN_WORD_TYPO_CORRECTIONS:
            right_w = EN_WORD_TYPO_CORRECTIONS[tok_low]
            if tok != right_w:
                working = re.sub(r"\b" + re.escape(tok) + r"\b", right_w, working)
                corrections.append((tok, right_w))
                already_replaced.add(tok_low)
        elif len(tok_low) >= 5 and tok_low not in CANONICAL_EN_VOCAB:
            # Fuzzy match against canonical academic vocabulary (high similarity >= 0.84)
            matches = difflib.get_close_matches(tok_low, CANONICAL_EN_VOCAB, n=1, cutoff=0.84)
            if matches and matches[0] != tok_low:
                right_w = matches[0]
                if right_w in ("alzheimer", "parkinson"):
                    right_w = right_w.capitalize()
                working = re.sub(r"\b" + re.escape(tok) + r"\b", right_w, working)
                corrections.append((tok, right_w))
                already_replaced.add(tok_low)

    # 4. Find related autocomplete suggestions based on current input tokens
    suggestions = get_autocomplete_suggestions(working, limit=6)

    return {
        "has_typo": len(corrections) > 0 and (working != text),
        "original": text,
        "corrected": working,
        "corrected_text": working,
        "corrections": corrections,
        "suggestions": suggestions,
    }


def get_autocomplete_suggestions(partial_text: str, limit: int = 6) -> list:
    """Returns matching or complementary academic terms from ACADEMIC_AUTOCOMPLETE_CATALOG."""
    q = (partial_text or "").strip().lower()
    if not q:
        return ACADEMIC_AUTOCOMPLETE_CATALOG[:limit]

    matched = []
    # 1. Direct substring match on ko, en, or query
    for item in ACADEMIC_AUTOCOMPLETE_CATALOG:
        haystack = f"{item['ko']} {item['en']} {item['query']}".lower()
        # Check if any word in q matches haystack, but item['query'] isn't already identical to q
        words = [w for w in re.split(r"[\s\(\)\"']+", q) if len(w) >= 2 and w not in ("or", "and", "not")]
        if any(w in haystack for w in words):
            if item["query"].lower() not in q:
                matched.append(item)

    # 2. If fewer than limit, suggest complementary high-frequency terms (e.g., Rehab, ML, Systematic Review)
    if len(matched) < limit:
        for item in ACADEMIC_AUTOCOMPLETE_CATALOG:
            if item not in matched and item["query"].lower() not in q:
                matched.append(item)
            if len(matched) >= limit:
                break

    return matched[:limit]


def suggest_closest_table_terms(user_kw: str, candidate_strings: list, limit: int = 4) -> list:
    """
    When a user's in-table filter keyword returns 0 results, finds the closest matching words
    actually present in the extracted DataFrame (titles, journals, topics, authors) to fix typos.
    """
    q = (user_kw or "").strip().lower()
    if not q or len(q) < 2:
        return []

    vocab = set()
    for text in candidate_strings:
        if not text:
            continue
        for w in re.findall(r"[가-힣A-Za-z0-9\-]{3,}", str(text)):
            w_clean = w.strip("-")
            if len(w_clean) >= 3 and w_clean.lower() not in EN_STOPWORDS:
                vocab.add(w_clean)

    vocab_lower_map = {v.lower(): v for v in vocab}
    # Substring matches first
    sub_matches = [orig for low, orig in vocab_lower_map.items() if q in low or low in q]
    if len(sub_matches) >= limit:
        return sorted(sub_matches, key=len)[:limit]

    # Fuzzy matches via difflib
    close_lows = difflib.get_close_matches(q, list(vocab_lower_map.keys()), n=limit, cutoff=0.68)
    results = list(sub_matches)
    for cl in close_lows:
        orig_val = vocab_lower_map[cl]
        if orig_val not in results:
            results.append(orig_val)
    return results[:limit]


def _translate_ko_to_en_fallback(text):
    """Lightweight fallback translation via Google GTX free endpoint if unmapped Korean words remain."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": text}
        res = requests.get(url, params=params, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data[0], list):
                translated = "".join([part[0] for part in data[0] if part and part[0]])
                return translated.strip()
    except Exception as e:
        logger.debug(f"[QUERY_OPT] Translation fallback skipped: {e}")
    return ""


def optimize_search_query(raw_query: str) -> dict:
    """
    Converts natural language sentences (Korean or English) or free-form keywords
    into an optimal OpenAlex Boolean search query while preserving explicit Boolean queries
    and automatically correcting common academic spelling typos.

    Returns:
        {
            "original": str,
            "optimized": str,
            "fallback": str,
            "was_modified": bool,
            "typo_corrected": bool,
            "typo_pairs": list,
            "explanation_ko": str,
            "explanation_en": str
        }
    """
    q = (raw_query or "").strip()
    if not q:
        return {
            "original": "",
            "optimized": "",
            "fallback": "",
            "was_modified": False,
            "typo_corrected": False,
            "typo_pairs": [],
            "explanation_ko": "",
            "explanation_en": ""
        }

    # Pre-pass: check for common Korean/English academic typos
    typo_info = detect_and_correct_typos(q)
    q_clean = typo_info["corrected"] if typo_info["has_typo"] else q
    typo_pairs = typo_info["corrections"]
    typo_note_ko = ""
    typo_note_en = ""
    if typo_pairs:
        pair_str = ", ".join([f"'{w}'➔'{r}'" for w, r in typo_pairs])
        typo_note_ko = f" (오타 자동 보정: {pair_str})"
        typo_note_en = f" (Auto-corrected typo: {pair_str})"

    has_korean = bool(re.search(r"[가-힣]", q_clean))
    has_explicit_boolean = bool(
        re.search(r'\b(OR|AND|NOT)\b', q_clean) or '"' in q_clean or "(" in q_clean or ")" in q_clean or re.search(r'(?:^|\s)-[a-zA-Z]', q_clean)
    )

    # 1. If it's pure English and already uses explicit Boolean operators (and isn't a question sentence), respect user's exact query!
    if not has_korean and has_explicit_boolean and "?" not in q_clean:
        return {
            "original": q,
            "optimized": q_clean,
            "fallback": q_clean,
            "was_modified": (q_clean != q),
            "typo_corrected": bool(typo_pairs),
            "typo_pairs": typo_pairs,
            "explanation_ko": f"사용자 지정 정밀 검색식(`{q_clean}`)을 적용했습니다.{typo_note_ko}",
            "explanation_en": f"Applied your Boolean search syntax (`{q_clean}`).{typo_note_en}"
        }

    extracted_tokens = []
    working_text = q_clean
    dropped_ko = []

    # 2. Handle Korean input (Natural language sentence or Korean keywords)
    if has_korean:
        # Sort thesaurus keys by length descending so longer medical terms ("흡인성 폐렴") match first
        for ko_term in sorted(KO_ACADEMIC_THESAURUS.keys(), key=len, reverse=True):
            if ko_term in working_text:
                en_mapped = KO_ACADEMIC_THESAURUS[ko_term]
                if en_mapped not in extracted_tokens:
                    extracted_tokens.append(en_mapped)
                working_text = working_text.replace(ko_term, " ")

        # Also extract any English acronyms/terms already embedded in the Korean text (e.g., VFSS, LLM, tDCS)
        en_embedded = re.findall(r'[A-Za-z0-9\-]{2,}', working_text)
        for ew in en_embedded:
            if ew.lower() not in EN_STOPWORDS and ew not in extracted_tokens:
                extracted_tokens.append(ew)
        working_text = re.sub(r'[A-Za-z0-9\-]{2,}', ' ', working_text)

        # Strip Korean conversational fillers & particles
        for pat in KO_FILLER_PATTERNS:
            working_text = re.sub(pat, " ", working_text)
        working_text = re.sub(r"\b[가-힣]+?(?:은|는|이|가|을|를|의|에|와|과|로|도|만)\b", " ", working_text)
        remaining_ko = re.sub(r"[^가-힣\s]", " ", working_text).strip()

        # If there are still meaningful unmapped Korean words (and we haven't already extracted enough tokens)
        if remaining_ko and len(remaining_ko) >= 2:
            translated_en = _translate_ko_to_en_fallback(remaining_ko if not extracted_tokens else q_clean)
            if not translated_en:
                dropped_ko = [w for w in remaining_ko.split() if len(w) >= 2]
            if translated_en and not extracted_tokens:
                working_text = translated_en
                has_korean = False
            elif translated_en:
                rem_opt = _extract_english_keywords(translated_en)
                for rt in rem_opt:
                    if rt.lower() not in " ".join(extracted_tokens).lower():
                        extracted_tokens.append(rt)

        if extracted_tokens:
            core_tokens = extracted_tokens[:5]
            optimized_q = " ".join(core_tokens)
            fallback_q = " OR ".join(core_tokens[:3]) if len(core_tokens) >= 2 else optimized_q
            return {
                "original": q,
                "optimized": optimized_q,
                "fallback": fallback_q,
                "was_modified": True,
                "typo_corrected": bool(typo_pairs),
                "typo_pairs": typo_pairs,
                "explanation_ko": f"한국어 입력을 분석하여 글로벌 학술 DB 맞춤 영문 검색식(`{optimized_q}`)으로 자동 변환했습니다.{typo_note_ko}"
                + (f" ⚠️ 영어로 바꾸지 못해 빠진 단어: {', '.join(dropped_ko)} — 필요하면 영어로 직접 추가하세요." if dropped_ko else ""),
                "explanation_en": f"Automatically translated and optimized your query into academic search terms (`{optimized_q}`).{typo_note_en}"
                + (f" ⚠️ Untranslated words dropped: {', '.join(dropped_ko)} — add them in English if needed." if dropped_ko else ""),
                "dropped_terms": dropped_ko
            }

    # 3. Handle English Natural Language Sentence or Free-form Words
    en_tokens = _extract_english_keywords(working_text)
    if not en_tokens:
        cleaned = re.sub(r"[^\w\s\-]", " ", q_clean).strip()
        return {
            "original": q,
            "optimized": cleaned or q_clean,
            "fallback": cleaned or q_clean,
            "was_modified": (cleaned != q),
            "typo_corrected": bool(typo_pairs),
            "typo_pairs": typo_pairs,
            "explanation_ko": f"검색어(`{cleaned or q_clean}`)를 적용했습니다.{typo_note_ko}",
            "explanation_en": f"Applied search query (`{cleaned or q_clean}`).{typo_note_en}"
        }

    core_en = en_tokens[:5]
    optimized_en = " ".join(core_en)
    fallback_en = " ".join(core_en[:3]) if len(core_en) > 3 else (" OR ".join(core_en) if len(core_en) >= 2 else optimized_en)
    was_mod = (optimized_en.lower() != q.lower().strip()) or bool(typo_pairs)

    return {
        "original": q,
        "optimized": optimized_en,
        "fallback": fallback_en,
        "was_modified": was_mod,
        "typo_corrected": bool(typo_pairs),
        "typo_pairs": typo_pairs,
        "explanation_ko": f"핵심 학술 키워드(`{optimized_en}`)를 추출했습니다.{typo_note_ko}" if was_mod else "",
        "explanation_en": f"Extracted core academic concepts (`{optimized_en}`).{typo_note_en}" if was_mod else ""
    }


def _extract_english_keywords(text: str) -> list:
    """Extracts known academic phrases and core non-stopword terms from an English sentence."""
    lower_text = text.lower()
    tokens = []

    # 1. Preserve any user-quoted phrases first
    quoted = re.findall(r'"([^"]+)"', text)
    for qp in quoted:
        if qp.strip():
            tokens.append(f'"{qp.strip()}"')
            lower_text = lower_text.replace(f'"{qp.lower()}"', " ")

    # 2. Match known multi-word academic phrases
    for phrase in sorted(KNOWN_EN_PHRASES, key=len, reverse=True):
        if re.search(r'\b' + re.escape(phrase) + r'\b', lower_text):
            formatted = f'"{phrase}"'
            if formatted not in tokens:
                tokens.append(formatted)
            lower_text = re.sub(r'\b' + re.escape(phrase) + r'\b', " ", lower_text)

    # 3. Extract remaining individual meaningful words
    words = re.findall(r"[A-Za-z0-9\-]{2,}", lower_text)
    for w in words:
        w_clean = w.strip("-")
        if len(w_clean) < 2:
            continue
        if w_clean.lower() not in EN_STOPWORDS:
            if w_clean.lower() in {"ai", "llm", "llms", "nlp", "ehr", "emr", "vfss", "fees", "tdcs", "rtms", "mri", "eeg", "ecg", "icu", "covid", "rna", "dna", "pcr"}:
                w_clean = w_clean.upper()
            if w_clean.lower() not in [t.lower().strip('"') for t in tokens]:
                tokens.append(w_clean)

    return tokens
