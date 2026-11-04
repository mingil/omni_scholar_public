import requests
import json
import os
from dotenv import load_dotenv

print("==========================================")
print("🛡️ OmniScholar WAF(방화벽) 최종 자동화 스크립트")
print("==========================================\n")

# 실행 위치와 상관없이 스크립트가 있는 폴더의 .env를 무조건 찾아서 읽습니다!
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(dotenv_path=env_path)

ZONE_ID = os.getenv("CF_ZONE_ID", "").strip().strip('"').strip("'")
API_TOKEN = os.getenv("CF_API_TOKEN", "").strip().strip('"').strip("'")
YOUR_DOMAIN = os.getenv("CF_DOMAIN", "").strip().strip('"').strip("'")

if not all([ZONE_ID, API_TOKEN, YOUR_DOMAIN]):
    print(f"❌ 오류: {env_path} 파일에 설정값이 누락되었습니다!")
    exit(1)

# 영역 WAF(Zone WAF) 권한에 완벽하게 호환되는 최신 방화벽 엔드포인트
url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/rulesets/phases/http_ratelimit/entrypoint"
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

payload = {
    "rules": [{
        "action": "block",
        "ratelimit": {
            "characteristics": [
                "cf.colo.id",
                "ip.src"
            ],
            "period": 10,
            "requests_per_period": 50,
            # 🔥 클라우드플레어 무료 요금제 강제 규정에 맞춰 차단 시간을 '10초'로 수정했습니다!
            "mitigation_timeout": 10
        },
        "expression": f"http.host eq \"{YOUR_DOMAIN}\"",
        "description": "OmniScholar Public Bot Protection"
    }]
}

print(f"🚀 [{YOUR_DOMAIN}] 서버로 방화벽 규칙을 전송합니다...")
res = requests.put(url, headers=headers, data=json.dumps(payload))

if res.status_code == 200:
    print("✅ 방화벽 세팅 완벽 성공! (요금제 정책에 맞춰 10초 단위로 봇을 즉각 무한 차단합니다.)")
else:
    print(f"❌ 오류 발생 (코드 {res.status_code}):")
    print(json.dumps(res.json(), indent=2))
