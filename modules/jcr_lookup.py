"""(선택 기능) 기관이 구독한 JCR 공식 지표를 내 서버의 JCR 조회 창구에서 받아 붙인다.

- 환경변수 JCR_LOOKUP_URL(예: http://172.17.0.1:18611)이 있을 때만 동작한다.
  없으면 아무 일도 하지 않으므로 공개 배포판의 화면·결과는 그대로다.
- JCR 자료 자체는 이 저장소에 담지 않는다(JCR은 기관 구독 자료라 재배포 불가).
- 조회 창구 응답 형식: POST /api/lookup_batch  [{"id","issn","name"}] → {id: {"found","jif","best_quartile","label","source",...}}
"""
import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)
_URL = os.environ.get("JCR_LOOKUP_URL", "").strip().rstrip("/")
_cache: dict = {}


def enabled() -> bool:
    return bool(_URL)


def lookup_many(items):
    """items: [(issn, name), ...] → {(issn, name): 결과 dict 또는 None}. 실패하면 빈 결과."""
    out = {}
    if not _URL:
        return out
    todo = [(i, n) for (i, n) in dict.fromkeys(items) if (i or n) and (i, n) not in _cache]
    for start in range(0, len(todo), 300):
        chunk = todo[start:start + 300]
        body = json.dumps([{"id": str(k), "issn": i or "", "name": n or ""} for k, (i, n) in enumerate(chunk)]).encode()
        try:
            req = urllib.request.Request(f"{_URL}/api/lookup_batch", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                res = json.load(r)
            for k, key in enumerate(chunk):
                v = res.get(str(k)) or {}
                _cache[key] = v if v.get("found") else None
        except Exception as e:  # 조회 실패는 검색 결과에 영향 없음
            logger.info(f"[JCR] 조회 생략: {type(e).__name__}")
            break
    for key in items:
        out[key] = _cache.get(key)
    return out


def short_label(r) -> str:
    """표에 넣을 짧은 글: 'Q1 · 4.0'."""
    if not r or r.get("jif") is None:
        return ""
    return f"{r.get('best_quartile', '')} · {r['jif']}"
