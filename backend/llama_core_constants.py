"""
llama_core で共有する設定値・定数。
Shared configuration and constants for llama_core modules.
"""

import os
import re

# APIキーと設定の読み込み
# Load API keys and configuration
groq_api_key = os.getenv("GROQ_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "0"))
MAX_DECISION_CHARS = int(os.getenv("MAX_DECISION_CHARS", "2000"))
DECISION_MAX_ITEMS = int(os.getenv("DECISION_MAX_ITEMS", "10"))
DECISION_FLEX_KEY_LIMIT = int(os.getenv("DECISION_FLEX_KEY_LIMIT", "2"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ja").strip().lower() or "ja"
SUPPORTED_LANGUAGES = {"ja", "en"}
LANGUAGE_NAMES = {"ja": "日本語", "en": "English"}
DECISION_MEMO_KEYS_BY_LANGUAGE = {
    "ja": os.getenv("DECISION_MEMO_KEY_JA", os.getenv("DECISION_MEMO_KEY", "メモ")),
    "en": os.getenv("DECISION_MEMO_KEY_EN", "Notes"),
}
# Groqモデル設定
# Groq model configuration
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")
GROQ_FALLBACK_MODEL_NAME = os.getenv("GROQ_FALLBACK_MODEL_NAME")
# 出力ガードレールの有効化設定
# Toggle output guardrails
OUTPUT_GUARD_ENABLED = os.getenv("OUTPUT_GUARD_ENABLED", "true").lower() in ("1", "true", "yes")

if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY が設定されていないか、無効です。")

DECISION_DEFAULT_MESSAGES = {
    "ja": "決定している項目がありません。",
    "en": "No decisions yet.",
}
DECISION_ERROR_MESSAGES = {
    "ja": "決定事項の更新中にエラーが発生しました。",
    "en": "Failed to update decisions.",
}
DECISION_SAFETY_MESSAGES = {
    "ja": "安全性の理由で表示できません。",
    "en": "This content can't be shown for safety reasons.",
}
DECISION_GUARD_BLOCKED_MESSAGES = {
    "ja": "それには答えられません",
    "en": "I can't answer that.",
}
DECISION_DEFAULT_MESSAGE = DECISION_DEFAULT_MESSAGES["ja"]
DECISION_IGNORED_LINES = {
    DECISION_DEFAULT_MESSAGES["ja"],
    DECISION_DEFAULT_MESSAGES["en"],
    "決定事項がありません。",
    "決定している項目はありません。",
    DECISION_ERROR_MESSAGES["ja"],
    DECISION_ERROR_MESSAGES["en"],
    "Empty",
    "{}",
    "[]",
}
DECISION_BULLET_PREFIX_RE = re.compile(
    r"^\s*(?:[-*•・●○◎◯]|\d+[.)]|\d+[）)]|[①-⑳])\s*"
)
DECISION_KV_SEPARATOR_RE = re.compile(r"\s*[:：]\s*", re.UNICODE)
DECISION_PATCH_ALLOWED_KEYS = {"add", "update", "remove"}
DECISION_UNKNOWN_ANSWER_RE = re.compile(
    r"^(?:\?|？|わからない|不明|未定|まだ|さっき言った|前に言った|そのまま|not sure|unknown|tbd|later|no idea|same as before|as before)$",
    re.IGNORECASE,
)
DECISION_DATE_LIKE_RE = re.compile(
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日)"
)
DECISION_YES_NO_TOKENS = {
    "はい",
    "いいえ",
    "うん",
    "うーん",
    "yes",
    "no",
    "y",
    "n",
    "ok",
}
LANGUAGE_JA_RE = re.compile(r"[ぁ-んァ-ン一-龯]")
LANGUAGE_LATIN_RE = re.compile(r"[A-Za-z]")

DECISION_KEY_LABELS_BY_MODE = {
    "travel": {
        "ja": {
            "destination": "目的地",
            "departure": "出発地",
            "dates": "日程",
            "travelers": "人数",
            "budget": "予算",
            "transport": "交通手段",
            "accommodation": "宿泊",
            "companions": "同行者",
        },
        "en": {
            "destination": "Destination",
            "departure": "Departure",
            "dates": "Dates",
            "travelers": "Travelers",
            "budget": "Budget",
            "transport": "Transport",
            "accommodation": "Accommodation",
            "companions": "Companions",
        },
    },
    "reply": {
        "ja": {
            "response_policy": "返信方針",
            "tone": "トーン",
            "length": "長さ",
            "purpose": "目的",
            "key_points": "伝えたい内容",
            "avoid": "避けたい内容",
        },
        "en": {
            "response_policy": "Response policy",
            "tone": "Tone",
            "length": "Length",
            "purpose": "Purpose",
            "key_points": "Key points",
            "avoid": "Avoid",
        },
    },
    "fitness": {
        "ja": {
            "goal": "目標",
            "frequency": "頻度",
            "time": "時間",
            "experience": "経験",
            "environment": "環境",
            "constraints": "制約",
            "diet": "食事方針",
        },
        "en": {
            "goal": "Goal",
            "frequency": "Frequency",
            "time": "Time",
            "experience": "Experience",
            "environment": "Environment",
            "constraints": "Constraints",
            "diet": "Diet",
        },
    },
    "job": {
        "ja": {
            "company": "対象企業",
            "role": "職種",
            "prompt": "設問文",
            "word_count": "文字数",
            "self_pr": "自己PR要素",
            "gakuchika": "ガクチカ要素",
            "motive": "志望動機要素",
            "interview": "面接対策方針",
        },
        "en": {
            "company": "Company",
            "role": "Role",
            "prompt": "Prompt",
            "word_count": "Word count",
            "self_pr": "Self PR",
            "gakuchika": "Gakuchika",
            "motive": "Motivation",
            "interview": "Interview prep",
        },
    },
    "study": {
        "ja": {
            "class": "授業名",
            "scope": "範囲",
            "goal": "学習目標",
            "key_points": "重要ポイント",
            "terms": "用語",
            "questions": "確認問題",
            "next_task": "次のタスク",
        },
        "en": {
            "class": "Class",
            "scope": "Scope",
            "goal": "Learning goal",
            "key_points": "Key points",
            "terms": "Terms",
            "questions": "Check questions",
            "next_task": "Next task",
        },
    },
}

DECISION_KEY_EXTRA_ALIASES_BY_MODE = {
    "travel": {
        "destination": ["行き先", "旅行先", "destinations"],
        "departure": ["出発地点", "出発", "origin", "from"],
        "dates": ["日付", "旅行日程", "schedule", "date", "when"],
        "travelers": ["人数", "旅行人数", "people", "guests"],
        "budget": ["費用", "price", "price range"],
        "transport": ["交通", "移動手段", "transportation", "transit"],
        "accommodation": ["ホテル", "宿", "stay", "lodging"],
        "companions": ["同行", "同伴者", "companion", "companions"],
    },
    "reply": {
        "response_policy": ["返答方針", "返信の方針", "reply policy", "response"],
        "tone": ["口調"],
        "length": ["文字数", "word count"],
        "purpose": ["狙い", "goal"],
        "key_points": ["要点", "伝えたいこと", "message"],
        "avoid": ["避けたいこと", "ng", "don't mention"],
    },
    "fitness": {
        "goal": ["目的"],
        "frequency": ["回数", "per week"],
        "time": ["duration", "minutes"],
        "experience": ["経験値", "level"],
        "environment": ["設備", "equipment"],
        "constraints": ["制限", "怪我", "injury", "limitations"],
        "diet": ["食事", "nutrition"],
    },
    "job": {
        "company": ["企業"],
        "role": ["ポジション", "position"],
        "prompt": ["質問", "question"],
        "word_count": ["字数"],
        "self_pr": ["自己PR"],
        "gakuchika": ["ガクチカ"],
        "motive": ["志望動機"],
        "interview": ["面接方針", "interview"],
    },
    "study": {
        "class": ["科目", "course"],
        "scope": ["coverage"],
        "goal": ["目標"],
        "key_points": ["要点"],
        "terms": ["vocabulary"],
        "questions": ["確認", "practice questions"],
        "next_task": ["次やること"],
    },
}

DECISION_ALLOWED_KEYS_BY_MODE = {
    mode: list(labels.get("ja", {}).keys())
    for mode, labels in DECISION_KEY_LABELS_BY_MODE.items()
}
DECISION_SLOT_QUESTION_PATTERNS = {
    "出発地": re.compile(
        r"(出発|出発地|出発地点).*(どこ|どちら|どこから|どちらから)|"
        r"(departure|origin|from).*(where|which|location)",
        re.IGNORECASE,
    ),
    "目的地": re.compile(
        r"(目的地|行き先|旅行先|行きたい場所|どこに行きたい)|"
        r"(destination|where to|where do you want to go|travel to)",
        re.IGNORECASE,
    ),
    "日程": re.compile(
        r"(日程|いつ|ご都合|何日|何泊|何月|何日から)|"
        r"(dates|date|schedule|when)",
        re.IGNORECASE,
    ),
}
DECISION_SLOT_VALUE_PATTERNS = {
    "出発地": re.compile(
        r"(出発地|出発地点|出発は|出発|departure|origin)\s*(?:は|:|：|is)?\s*(.+)",
        re.IGNORECASE,
    ),
    "目的地": re.compile(
        r"(目的地|行き先|旅行先|行きたい場所|行き先は|destination)\s*(?:は|:|：|is)?\s*(.+)",
        re.IGNORECASE,
    ),
    "日程": re.compile(
        r"(日程|日付|出発日|旅行日程|ご都合|dates|date|schedule)\s*(?:は|:|：|is)?\s*(.+)",
        re.IGNORECASE,
    ),
}
