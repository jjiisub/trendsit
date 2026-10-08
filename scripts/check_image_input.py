"""S4 준비물: generate 별칭(고정 제공사)이 이미지 메시지를 받는지 프레임 1장으로 확인(S4_TASK 2장).

    TRENDSIT_SPEC=S4 uv run python scripts/check_image_input.py data/media/<id>/frames/<run>/frame_0001.jpg

비용은 실행 기록(S4)에 남는다. 기록에는 이미지 원본 대신 경로와 해시만.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

from trendsit.core.context import open_ctx

PROMPT = "이 화면에 보이는 글자를 줄마다 그대로 옮겨 적는다. 영상에 입힌 자막 줄은 [자막]으로 표시한다. 다른 설명은 쓰지 않는다."


def main(path: str) -> int:
    img = Path(path).read_bytes()
    digest = hashlib.sha256(img).hexdigest()
    uri = "data:image/jpeg;base64," + base64.b64encode(img).decode()
    ctx = open_ctx("image-check", spec="S4", note=f"image input {path}")
    messages = [{"role": "user", "content": [{"type": "text", "text": PROMPT},
                                             {"type": "image_url", "image_url": {"url": uri}}]}]
    status = "failed"
    try:
        res = ctx.llm.chat("generate", messages, max_tokens=300, no_cache=True)
        request = json.loads(json.dumps(res.request).replace(uri, f"image:{path}#sha256={digest}"))
        ctx.tracer.step(kind="llm", role="image_check", text="이미지 입력 확인", model=res.model,
                        provider=res.provider, tokens_in=res.tokens_in, tokens_out=res.tokens_out,
                        cost_usd=res.cost_usd, cost_estimated=res.cost_estimated, latency_ms=res.latency_ms,
                        output=res.content, request=request, response=res.response)
        print(json.dumps({"model": res.model, "provider": res.provider, "tokens_in": res.tokens_in,
                          "tokens_out": res.tokens_out, "cost_usd": res.cost_usd, "latency_ms": res.latency_ms},
                         ensure_ascii=False))
        print(res.content)
        status = "ok"
        return 0
    except Exception as e:  # noqa: BLE001 - 지원하지 않으면 오류 문구가 곧 결과
        ctx.tracer.step(kind="code", role="image_check", text="이미지 입력 실패", attention=True, error=str(e))
        print(f"실패: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        ctx.tracer.finish(status)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
