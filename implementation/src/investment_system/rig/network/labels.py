"""One Data / One Terminology / Three Presentations. NEW IMPLEMENTATION.

Language only changes labels. Data, ids, states and ordering never depend on it.
"""

from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    EN = "EN"
    EN_KO = "EN_KO"
    KO = "KO"


TERMS: dict[str, tuple[str, str]] = {
    "news": ("News", "뉴스"),
    "network": ("Network", "관계망"),
    "NEW": ("New", "신규"),
    "UPDATE": ("Update", "업데이트"),
    "FOLLOW_UP": ("Follow-up", "후속"),
    "DUPLICATE": ("Duplicate", "중복"),
    "SUPPLY_CHAIN": ("Supply Chain", "공급망"),
    "CUSTOMER": ("Customer", "고객"),
    "COMPETITOR": ("Competitor", "경쟁사"),
    "VALUE_CHAIN": ("Value Chain", "밸류체인"),
    "FACT": ("Confirmed Fact", "확인된 사실"),
    "SUPPORTED_INFERENCE": ("Expected / Unconfirmed", "예상·미확인"),
    "sources": ("sources", "출처"),
    "more": ("More", "더보기"),
    "fit": ("Fit graph", "그래프 맞춤"),
    "search": ("Search company", "기업 검색"),
    "more_relationships": ("more relationships", "개 관계 더보기"),
    "as_of": ("As of", "기준 시점"),
    "no_news": ("No news as of this time", "해당 시점 뉴스 없음"),
    "relationship": ("Relationship", "관계"),
    "company": ("Company", "기업"),
    "available_at": ("Available at", "공개 시점"),
    "last_confirmed_at": ("Last confirmed", "최근 확인"),
    "evidence_note": ("Evidence only — does not change QGV / Technical / Macro scores",
                      "근거 정보 — QGV / Technical / Macro 점수를 바꾸지 않음"),
}


def term(key: str, lang: Language, extra: dict[str, tuple[str, str]] | None = None) -> str:
    en, ko = (extra or {}).get(key) or TERMS.get(key) or (key, key)
    if lang is Language.EN:
        return en
    if lang is Language.KO:
        return ko
    return en if en == ko else f"{en} ({ko})"
