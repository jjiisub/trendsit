"""문체 검사 정규식(skills/style_ko.md). 평가(eval/graders*)와 S5 코드 검사가 같이 쓴다(S5 5.1-1)."""

from __future__ import annotations

import re

HAEYO = re.compile(r"(요|세요|어요|아요|에요|예요|해요|죠)[.!?…]*$")
# "요"로 끝나는 명사(명사형 끝말이라 해요체가 아님). "필요해요"처럼 뒤에 어미가 붙으면 HAEYO가 그대로 잡는다
NOUN_YO = re.compile(r"(필요|중요|주요|개요|수요|강요|소요)[.!?…]*$")
EVAL_ENDINGS = ("눈에 띈다", "핵심이다", "주목할 만하다", "공통 교훈이다", "주목할 만한", "눈여겨볼")
# 평가어(근거 없는 수식). 레포 설명, 포인트에서 쓰지 않는다
EVAL_WORDS = ("혁신적", "강력한", "놀라운", "최고의", "획기적", "뛰어난", "완벽한", "최첨단", "차세대", "혁명적",
              "압도적", "탁월한", "손쉬운", "쉽고 빠르게", "간편한", "똑똑한")
# 명사형이 아닌 문장 끝: "~다", "~요", "~까", 마침표 등. '요'로 끝나는 명사는 ends_as_sentence가 뺀다
SENTENCE_END = re.compile(r"(다|요|까|죠|니다|네)[.!?…]*$|[.!?]$")


def is_haeyo(sentence: str) -> bool:
    s = sentence.strip()
    return bool(HAEYO.search(s)) and not NOUN_YO.search(s)


def ends_as_sentence(text: str) -> bool:
    """명사형이 아니라 문장으로 끝남. '필요', '개요'처럼 요로 끝나는 명사는 명사형으로 본다."""
    s = text.strip()
    return bool(SENTENCE_END.search(s)) and not NOUN_YO.search(s)
