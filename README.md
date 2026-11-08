# 🌍 OmniScholar — Academic Literature & Citation Network Intelligence

[![Python 3.12](https://img.shields.io/badge/Python-3.12-2563EB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-kimmingil%2Fomni__scholar__public-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/r/kimmingil/omni_scholar_public)
[![GHCR](https://img.shields.io/badge/GHCR-ghcr.io%2Fmingil%2Fomni__scholar__public-0284C7?logo=github&logoColor=white)](https://github.com/mingil/omni_scholar_public/pkgs/container/omni_scholar_public)
[![OpenAlex API](https://img.shields.io/badge/Data-OpenAlex%20250M%2B%20Works-0D9488)](https://openalex.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-16A34A.svg)](./LICENSE)

**OmniScholar**는 전 세계 **2억 5천만 편 이상의 학술 논문 데이터베이스(OpenAlex)**를 기반으로, 연구자가 자연어 질문이나 키워드를 입력하면 최적의 불리언(Boolean) 학술 검색식으로 자동 변환하고 **최신 트렌드 논문(Citation Velocity)** 및 **역사적 뿌리 논문(Co-citation Foundational Roots)**을 발굴해 주는 오픈소스 Docker 웹 애플리케이션입니다.

**OmniScholar** is a containerized open-source platform for academic literature discovery and bibliometric citation network analysis. Powered by the **OpenAlex REST API (250M+ scholarly works)**, it converts natural language research questions (English & Korean) into Boolean search formulas, uncovers high-velocity contemporary papers, traces foundational root literature across reference networks, and exports standardized datasets (`.xlsx`, `.ris`, APA/AMA/BibTeX).

---

## ✨ 주요 기능 (Key Features)

1. **🎯 스마트 자연어 ➔ 학술 검색식 변환 & 초보자용 검색어 조립기 (`STEP 01`)**
   - 한국어·영어 자연어 질문을 입력하면 불필요한 서술어를 제거하고 동의어·구문 따옴표가 결합된 최적 영문 불리언 검색식으로 자동 변환합니다.
   - 연산자(`AND`, `OR`, `"구문"`, `-제외`)를 몰라도 단어만 입력하면 수식을 조립해 주는 인터랙티브 빌더와 원클릭 필터 칩을 제공합니다.
2. **🧭 2가지 핵심 탐색 알고리즘 & 8종 문헌 유형 정밀 필터 (`STEP 02`)**
   - **⚡ 빠른 트렌드 스캔 (`Ultra-fast Scan`):** 총 피인용 수, 연간 인용 속도(`Velocity [Cites/Yr]`), 분야 보정 영향력(`FWCI`), 최신 연도 순으로 핵심 논문을 추출합니다.
   - **🧠 심층 뿌리 논문 역추적 (`Deep Network`):** 1차 검색된 상위 논문들의 참고문헌(References) 수만 건을 멀티스레드로 역추적하여 해당 분야 연구자들이 가장 많이 공통 인용한 **원조(Root) 논문(`Network Hits`)**을 발굴합니다.
   - **📑 8종 문헌 유형 필터:** 전체 문헌, 원저+종설 통합, 원저(`Article`), 종설(`Review`), 프리프린트(`arXiv/medRxiv/bioRxiv`), 단행본, 학위논문, 사설·레터 필터링을 지원합니다.
3. **🏛️ 30만 개 글로벌 학술지 통합 탐색 및 특정 저널 지정 (`STEP 03`)**
   - 전 세계 모든 학술지 통합 탐색은 물론, 9대 학문 분야 권위 학술지 프리셋(*Nature, Science, NEJM, The Lancet, JAMA, IEEE TPAMI* 등), 학술지명 실시간 검색, ISSN 직접 지정을 지원합니다.
4. **📊 연구자 분석 대시보드 · 원클릭 인용문 복사 · 엑셀/RIS 다운로드 (`STEP 04 & Report`)**
   - 6대 핵심 서지 지표 카드 및 연도·학술지·선도 연구기관·세부 토픽 분포 차트를 자동 생성합니다.
   - 전체 초록(Abstract) 뷰어 및 **APA 7판, AMA/Vancouver, BibTeX** 원클릭 클립보드 복사 기능을 제공합니다.
   - 서식이 자동 적용된 **엑셀 보고서(`.xlsx`)**와 Zotero·EndNote·Mendeley 호환 **서지 파일(`.ris`)**을 즉시 다운로드할 수 있습니다.

---

## 🐳 Docker로 빠르게 시작하기 (Quick Start with Docker)

이 프로젝트는 `Dockerfile`과 `compose.yaml`이 완비되어 있어, Docker가 설치된 모든 환경(Linux, macOS, Windows WSL2, Synology NAS 등)에서 즉시 빌드하여 독립적으로 구동할 수 있습니다.

### 1. 저장소 복제 (Clone Repository)
```bash
git clone https://github.com/mingil/omni_scholar_public.git
cd omni_scholar_public
```

### 2. 환경 변수 파일 생성 및 설정 (Configure `.env`)
개별 사용자의 설정값과 비밀번호는 Git에 공유되지 않도록 `.env.example` 템플릿으로 분리되어 있습니다.
```bash
cp .env.example .env
```
`.env` 파일을 열어 본인의 환경에 맞게 설정합니다:
| 변수명 (Variable) | 기본값 (Default) | 설명 (Description) |
| :--- | :--- | :--- |
| `OPENALEX_EMAIL` | `""` | 본인의 이메일 주소를 입력하면 OpenAlex **Polite Pool(고속·안정 응답 트랙)**이 자동 활성화됩니다. (권장) |
| `OPENALEX_API_KEY` | `""` | OpenAlex 유료/전용 API 키가 있는 경우에만 입력합니다. (선택) |
| `APP_PASSWORD` | `""` | 웹 접속 시 로그인 비밀번호를 걸고 싶을 때 설정합니다. **비워두면(`""`) 로그인 화면 없이 즉시 워크스페이스로 접속**됩니다. |
| `APP_PORT` | `18502` | 호스트 서버에서 접속할 외부 포트 번호입니다 (`http://localhost:18502`). |

### 3. Docker Compose로 컨테이너 빌드 및 실행 (Build & Run)
```bash
docker compose up -d --build
```
- 실행 완료 후 웹 브라우저에서 **`http://localhost:18502`** 로 접속합니다.
- 상태 확인 및 로그 조회:
  ```bash
  docker compose ps
  docker compose logs -f
  ```
- 컨테이너 종료:
  ```bash
  docker compose down
  ```

---

## 🏠 시놀로지 DDNS로 외부 접속하기 (권장 · 무료) (Synology DDNS Guide)

> **왜 각자 설치(Self-hosting)하나요?** OpenAlex API는 이메일·API 키 단위로 하루 사용량이 정해져 있습니다. 한 서버를 여러 사람이 함께 쓰면 금방 한도에 걸리므로, **각자 자신의 NAS·PC에 설치하고 본인 이메일(`OPENALEX_EMAIL`)과 키를 넣어 쓰는 것**을 권장합니다.

도메인을 따로 사지 않아도 시놀로지의 무료 주소(`내아이디.synology.me`)로 `https://` 외부 접속을 만들 수 있습니다.

1. **DDNS 주소 만들기:** DSM ➔ **제어판 ➔ 외부 액세스 ➔ DDNS ➔ 추가** ➔ 서비스 공급자 `Synology`, 호스트 이름(예: `myname.synology.me`) 입력, **"Let's Encrypt에서 인증서 가져오기"** 체크 ➔ 확인.
2. **역방향 프록시 연결:** DSM ➔ **제어판 ➔ 로그인 포털 ➔ 고급 ➔ 역방향 프록시 ➔ 생성**
   - 소스: 프로토콜 `HTTPS`, 호스트 이름 `myname.synology.me` (또는 `omni.myname.synology.me`), 포트 `443`
   - 대상: 프로토콜 `HTTP`, 호스트 이름 `localhost`, 포트 `18502` (`.env`의 `APP_PORT`)
   - **사용자 지정 머리글 ➔ 생성 ➔ WebSocket** 을 꼭 추가합니다 (Streamlit 화면은 WebSocket으로 동작하며, 빠지면 화면이 계속 로딩만 됩니다).
3. **인증서 지정:** 제어판 ➔ 보안 ➔ 인증서 ➔ 설정에서 위 주소에 Let's Encrypt 인증서를 선택합니다.
4. **공유기 포트포워딩:** 공유기에서 외부 `443` ➔ NAS `443` 을 열어 줍니다 (QuickConnect만으로는 Docker 앱에 접속할 수 없습니다).
5. 외부에 공개되는 만큼 **`.env`의 `APP_PASSWORD`를 반드시 설정**하세요.

> 이미 Nginx Proxy Manager를 쓰고 있다면 위 2단계 대신 NPM에서 `Forward Port 18502`, **Websockets Support 켜기**로 등록하면 됩니다.

---

## 🌐 (선택) 구매한 개인 도메인(Cloudflare)으로 외부 접속 연결하기 (Custom Domain Guide)

본인이 구매하여 **Cloudflare(클라우드플레어)**로 관리 중인 도메인(예: `yourdomain.com`)이 있다면, 복잡한 공유기 포트포워딩(`80/443`)이나 SSL 보안인증서 발급 과정 없이 **Cloudflare Tunnel(`cloudflared`)**을 통해 3분 만에 안전한 `https://` 외부 접속 주소를 만들 수 있습니다.

### 1단계: Cloudflare에서 무료 터널 토큰(`CF_TUNNEL_TOKEN`) 발급받기
1. [Cloudflare Zero Trust 대시보드 (one.dash.cloudflare.com)](https://one.dash.cloudflare.com/)에 접속합니다.
2. 왼쪽 메뉴에서 **`Networks` ➔ `Tunnels`** 로 이동한 뒤 **`Create a tunnel`** 클릭 ➔ **`Cloudflared`** 선택 ➔ 터널 이름(예: `omni-scholar`)을 입력하고 저장합니다.
3. 화면에 나오는 설치 명령어 중 `--token eyJhIjoi...` 뒷부분의 긴 토큰 문자열을 복사합니다.

### 2단계: 통합 도커 파일(`compose.cloudflare.yaml`)로 실행하기
1. `.env` 파일의 `CF_TUNNEL_TOKEN` 항목에 복사한 토큰을 붙여넣습니다:
   ```env
   CF_TUNNEL_TOKEN="eyJhIjoi..."
   ```
2. 아래 명령어로 OmniScholar와 Cloudflare 터널을 동시에 실행합니다 (시놀로지 Container Manager에서는 **[프로젝트]** 생성 시 `compose.cloudflare.yaml` 파일을 선택하면 됩니다):
   ```bash
   docker compose -f compose.cloudflare.yaml up -d
   ```

### 3단계: Cloudflare에서 내가 원하는 도메인 주소 연결하기
1. 방금 만든 Cloudflare Tunnel 설정 화면의 **`Public Hostname` (공개 호스트 이름)** 탭으로 이동하여 **`Add a public hostname`**을 클릭합니다.
2. 아래와 같이 입력하고 저장하면 **즉시 전 세계 어디서나 내 도메인으로 접속**할 수 있습니다:
   - **Subdomain (서브도메인):** 원하는 이름 입력 (예: `omni-scholar` 또는 `scholar`)
   - **Domain (도메인):** 클라우드플레어에 등록된 내 도메인 선택 (예: `yourdomain.com`)
   - **Service Type:** `HTTP`
   - **URL:**
     - `compose.cloudflare.yaml`로 함께 띄운 경우: **`omni_public:8501`**
     - 이미 시놀로지 NAS에 별도의 `cloudflared`가 설치되어 있는 경우: **`시놀로지내부IP:18502`** (또는 `localhost:18502`)

### 🛡️ (선택) 내 도메인에 클라우드플레어 악성 봇 차단(WAF) 자동 적용하기
외부에 도메인을 공개했을 때 무분별한 크롤링 봇으로부터 서버를 보호하려면 `.env` 파일에 `CF_ZONE_ID`, `CF_API_TOKEN`, `CF_DOMAIN`을 입력한 뒤 아래 스크립트를 1회 실행하세요:
```bash
python3 setup_waf.py
```

---

## 🔄 최신 버전으로 업데이트하기 (How to Update)

새로운 기능이나 UI 개선 사항이 GitHub에 업데이트되었을 때, 기존 사용자들은 본인들의 `.env` 설정을 그대로 유지한 채 아래 두 가지 방법 중 하나로 즉시 최신 버전을 반영할 수 있습니다.

### 방법 1. Git 저장소 기반 업데이트 (소스 복제 사용자)
```bash
git pull origin main
docker compose up -d --build
```

### 방법 2. 시놀로지 NAS (Container Manager & Watchtower) 자동/수동 업데이트
이 프로젝트는 **Docker Hub(`kimmingil/omni_scholar_public:latest`)**와 **GitHub Container Registry(`ghcr.io/mingil/omni_scholar_public:latest`)** 양쪽에 동시에 공식 이미지를 자동 배포합니다.
- **시놀로지 Container Manager에서 검색하여 바로 설치하기:**
  - Container Manager 좌측 **[레지스트리(Registry)]** 탭 검색창에 **`kimmingil/omni_scholar_public`** (또는 **`omni_scholar_public`**)을 입력하면 바로 검색되며, 더블클릭하여 `latest` 태그를 다운로드해 실행할 수 있습니다.
- **Watchtower가 설치된 경우:** 개발자가 GitHub `main` 브랜치에 코드를 업데이트하면 GitHub Actions가 자동으로 새 도커 이미지를 빌드·배포하며, 사용자의 NAS에 설치된 **Watchtower가 새 이미지를 자동 감지하여 무중단으로 최신 버전을 업데이트**합니다.
- **시놀로지 Container Manager 수동 업데이트:**
  1. Container Manager ➔ **[이미지]** 탭에서 `kimmingil/omni_scholar_public:latest` (또는 `ghcr.io/mingil/omni_scholar_public:latest`) 옆의 **[업데이트 가능]** 클릭 후 컨테이너 **[초기화(Reset)]**
  2. 또는 SSH에서 아래 명령어 실행:
     ```bash
     docker compose pull
     docker compose up -d
     ```

---

### 💡 단일 Docker 명령어로 실행하기 (Standalone Docker CLI)
`docker compose` 없이 단일 `docker build` & `docker run` 명령어로도 실행할 수 있습니다:
```bash
docker build -t omni-scholar:latest .
docker run -d \
  --name omni_scholar \
  -p 18502:8501 \
  -e OPENALEX_EMAIL="your_email@university.edu" \
  -e APP_PASSWORD="" \
  omni-scholar:latest
```

---

## 🐍 로컬 Python 환경에서 직접 실행하기 (Local Python Setup)

Docker 없이 일반 Python(3.11 이상) 환경에서 직접 실행하거나 코드를 수정할 수도 있습니다:
```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 필수 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정 (선택)
cp .env.example .env

# 4. Streamlit 웹 서버 실행
streamlit run app.py --server.port=8501
```

---

## 🗂️ 프로젝트 디렉터리 구조 (Project Structure)

```text
omni_scholar_public/
├── app.py                     # 메인 4단계 워크플로우 및 분석 대시보드 애플리케이션
├── pages/
│   └── 1_User_Manual.py       # 한/영 상세 사용 매뉴얼 페이지
├── modules/
│   ├── config.py              # 환경 변수 로드 및 9대 학문 분야 대표 저널 프리셋
│   ├── query_optimizer.py     # 한글·영어 자연어 ➔ 불리언 학술 검색식 스마트 변환기
│   ├── data_fetcher.py        # OpenAlex API 커넥션 풀, 트렌드 스캔 & 다중 스레드 참고문헌 역추적 엔진
│   ├── export_utils.py        # 엑셀(.xlsx) 스타일링, RIS 서지 생성, APA/AMA/BibTeX 포매터
│   ├── ui_components.py       # 커스텀 CSS 디자인 시스템, 단계별 상태바, 인터랙티브 인용 복사 위젯
│   └── logger_setup.py        # 로테이팅 파일 및 콘솔 로거
├── tests/
│   └── test_core.py           # API 복원력, 자연어 변환, 인용 네트워크, 엑셀/RIS 무결성 단위 테스트 (9종)
├── Dockerfile                 # Python 3.11-slim 기반 경량 컨테이너 이미지 빌드 명세
├── compose.yaml               # Docker Compose 멀티 환경 배포 설정
├── requirements.txt           # 호환성 검증 완료된 Python 패키지 버전 명세
├── .env.example               # 사용자별 환경 변수 설정 템플릿 (비밀번호 미포함)
└── LICENSE                    # MIT 오픈소스 라이선스
```

---

## 🧪 자동화 단위 테스트 실행 (Running Unit Tests)

```bash
python3 -m pytest tests/test_core.py -v
```

---

## 📄 라이선스 (License)
이 프로젝트는 [MIT License](./LICENSE) 하에 배포되는 오픈소스 소프트웨어입니다. 누구나 자유롭게 복제(Fork), 수정 및 배포할 수 있습니다.
