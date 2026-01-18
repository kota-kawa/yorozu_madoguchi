import logging
import os
import guard
import redis_client
import re
from datetime import datetime
import warnings
import json
from typing import Any, Dict, List, Optional, Tuple

from groq_openai_client import get_groq_client

# ロギング設定
logger = logging.getLogger(__name__)
# 特定の警告を抑制
warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")

# APIキーと設定の読み込み
groq_api_key = os.getenv("GROQ_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "2000"))
MAX_DECISION_CHARS = int(os.getenv("MAX_DECISION_CHARS", "2000"))
# Groqモデル設定
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")
GROQ_FALLBACK_MODEL_NAME = os.getenv("GROQ_FALLBACK_MODEL_NAME")
# 出力ガードレールの有効化設定
OUTPUT_GUARD_ENABLED = os.getenv("OUTPUT_GUARD_ENABLED", "true").lower() in ("1", "true", "yes")

if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY が設定されていないか、無効です。")

DECISION_DEFAULT_MESSAGE = "決定している項目がありません。"
DECISION_IGNORED_LINES = {
    DECISION_DEFAULT_MESSAGE,
    "決定事項がありません。",
    "決定している項目はありません。",
    "決定事項の更新中にエラーが発生しました。",
    "Empty",
    "{}",
    "[]",
}
DECISION_BULLET_PREFIX_RE = re.compile(
    r"^\s*(?:[-*•・●○◎◯]|\d+[.)]|\d+[）)]|[①-⑳])\s*"
)
DECISION_KV_SEPARATOR_RE = re.compile(r"\s*[:：]\s*", re.UNICODE)
DECISION_PATCH_ALLOWED_KEYS = {"add", "update", "remove"}

# プロンプトの定義
# 各モード（travel, reply, fitness）ごとのシステムプロンプトと決定事項抽出プロンプトを定義
PROMPTS = {
    "travel": {
        "system": """
        # 命令書
        あなたは、優秀で親切な旅行計画のプロフェッショナル・コンシェルジュです。
        ユーザー一人ひとりに寄り添い、最高の旅行プランを作成するのを手伝ってください。

        ## あなたの役割
        - ユーザーとの対話を通じて、旅行の必須情報（目的地、日程など）と要望を引き出します。
        - 最適な旅行プランを提案し、丁寧で共感的な対話スタイルを保ってください。

        ## 実行ステップ
        1. 基本情報（目的地、出発地、日程）を一つずつ確認。
        2. 好みや要望をヒアリング。
        3. 具体的な提案と理由の提示。

        ## 制約条件と出力ルール（厳守）
        - 質問: 一度のメッセージで一つの質問。
        - 特殊形式: ユーザーのアクションが必要な場合は、以下の形式を**厳密に**使用すること。
          - Yes/No形式: 「Yes/No: [質問内容]」
          - 選択肢形式: 「Select: [選択肢1, 選択肢2, ..., その他]」（※半角括弧[]と半角カンマを使用、最大6つ）
          - 日付選択形式: 「DateSelect: true」
        - 重要: 特殊形式は**独立した行**として出力し、他の文章と混ぜないこと。
        - 重要: 特殊形式を出力する際は、その直前に必ずユーザーへの**親しみやすい案内文**を配置すること（特殊形式のみの出力は禁止）。
          - 案内文は「Select:」や角括弧の選択肢を含めない、ユーザーに話しかける自然な文にする。
          - 例: 「どのタイプに近いですか？」「当てはまるものを選んでください。」
        - 重要: 特殊形式は同時に複数使わない（Yes/No, Select, DateSelectはいずれか1つのみ）。

        ## 出力例（厳密）
        ユーザー: 目的は筋肥大です
        アシスタント: ありがとうございます。頻度は週に何回が理想ですか？
        ユーザー: 目的を選びたい
        アシスタント: どれが今の目的に一番近いですか？
        Select: [筋肥大, 減量, 姿勢改善, 体力向上, その他]
        ユーザー: 日付を選びたい
        アシスタント: 都合の良い日付を選んでください。
        DateSelect: true
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている旅行項目（目的地、出発地、日程など）の差分だけを抽出するアシスタントです。
        - 出力は**必ず**1つのJSONオブジェクトのみ（コードブロックや説明文は禁止）。
        - 形式: {"add": {"項目名": "内容"}, "update": {"項目名": "内容"}, "remove": ["項目名", ...]}
        - add: まだ無い決定事項の新規追加のみ
        - update: 既存の決定事項が変更・更新された場合のみ
        - remove: ユーザーが取り消し・不要と言った場合のみ
        - 変更が無い場合は {} を返す
        """
    },
    "reply": {
        "system": """
        # 命令書
        あなたは、親しみやすく丁寧なメッセージ返答アシスタントです。
        ユーザーからのメッセージに対し、簡潔かつ分かりやすい日本語で応答してください。

        ## あなたの役割
        - ユーザーからの問いかけに対して、親しみやすく回答する。
        - 必要に応じてユーザーの意向を確認し、決定を促す。

        ## 制約条件と出力ルール（厳守）
        - 言語: 日本語。
        - トーン: 親しみやすく、丁寧な「です・ます」調。
        - 応答の長さ: 200文字以内目安。
        - 質問: 一度のメッセージで一つの質問。
        - 特殊形式: ユーザーのアクションが必要な場合は、以下の形式を**厳密に**使用すること。
          - Yes/No形式: 「Yes/No: [質問内容]」
          - 選択肢形式: 「Select: [選択肢1, 選択肢2, ..., その他]」（※半角括弧[]と半角カンマを使用、最大6つ）
          - 日付選択形式: 「DateSelect: true」
        - 重要: 特殊形式は**独立した行**として出力し、他の文章と混ぜないこと。
        - 重要: 特殊形式を出力する際は、その直前に必ずユーザーへの**親しみやすい案内文**を配置すること（特殊形式のみの出力は禁止）。
          - 案内文は「Select:」や角括弧の選択肢を含めない、ユーザーに話しかける自然な文にする。
          - 例: 「どの方向性が近いですか？」「当てはまるものを選んでください。」
        - 重要: 特殊形式は同時に複数使わない（Yes/No, Select, DateSelectはいずれか1つのみ）。

        ## 出力例（厳密）
        ユーザー: どんな返事が良い？
        アシスタント: 返信のトーンは丁寧めが良いですか？
        Yes/No: 丁寧めで返しますか？
        ユーザー: 選択肢で選びたい
        アシスタント: どの返し方が一番しっくりきますか？
        Select: [短く返す, 丁寧に返す, 断りたい, 距離を置きたい, その他]
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている項目（返信内容の方針など）の差分だけを抽出するアシスタントです。
        - 出力は**必ず**1つのJSONオブジェクトのみ（コードブロックや説明文は禁止）。
        - 形式: {"add": {"項目名": "内容"}, "update": {"項目名": "内容"}, "remove": ["項目名", ...]}
        - add: まだ無い決定事項の新規追加のみ
        - update: 既存の決定事項が変更・更新された場合のみ
        - remove: ユーザーが取り消し・不要と言った場合のみ
        - 変更が無い場合は {} を返す
        """
    },
    "fitness": {
        "system": """
        # 命令書
        あなたは、筋トレ・フィットネス（健康全般）のアシスタントです。
        ユーザーの目的・体力・生活習慣に合わせて、安全で実践的な提案を行ってください。

        ## あなたの役割
        - 目標（筋肥大、減量、姿勢改善など）や経験、頻度、設備、制限（怪我・疾患）を確認。
        - 具体的で続けやすいメニューや習慣を提案し、丁寧で共感的な対話を保つ。
        - 医療判断は行わず、痛みや持病がある場合は医師相談を促す。

        ## 実行ステップ
        1. 目的と現状（経験・頻度・環境）を確認。
        2. 制約（時間、怪我、器具）を確認。
        3. 具体的な提案と理由を提示。
        4. 次回アクションの要約と確認。

        ## 制約条件と出力ルール（厳守）
        - 言語: 日本語。
        - 応答の長さ: 200文字以内目安。
        - 質問: 一度のメッセージで一つの質問。
        - 特殊形式: ユーザーのアクションが必要な場合は、以下の形式を**厳密に**使用すること。
          - Yes/No形式: 「Yes/No: [質問内容]」
          - 選択肢形式: 「Select: [選択肢1, 選択肢2, ..., その他]」（※半角括弧[]と半角カンマを使用、最大6つ）
          - 日付選択形式: 「DateSelect: true」
        - 重要: 特殊形式は**独立した行**として出力し、他の文章と混ぜないこと。
        - 重要: 特殊形式を出力する際は、その直前に必ずユーザーへの**親しみやすい案内文**を配置すること（特殊形式のみの出力は禁止）。
          - 案内文は「Select:」や角括弧の選択肢を含めない、ユーザーに話しかける自然な文にする。
          - 例: 「どの目的に近いですか？」「当てはまるものを選んでください。」
        - 重要: 特殊形式は同時に複数使わない（Yes/No, Select, DateSelectはいずれか1つのみ）。

        ## 出力例（厳密）
        ユーザー: 目的を選べる？
        アシスタント: どれが今の目的に一番近いですか？
        Select: [筋肥大, 減量, 姿勢改善, 体力向上, その他]
        ユーザー: 日付で区切ってほしい
        アシスタント: 都合の良い日付を選んでください。
        DateSelect: true
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている筋トレ・健康の項目（目標、頻度、制約、食事方針など）の差分だけを抽出するアシスタントです。
        - 出力は**必ず**1つのJSONオブジェクトのみ（コードブロックや説明文は禁止）。
        - 形式: {"add": {"項目名": "内容"}, "update": {"項目名": "内容"}, "remove": ["項目名", ...]}
        - add: まだ無い決定事項の新規追加のみ
        - update: 既存の決定事項が変更・更新された場合のみ
        - remove: ユーザーが取り消し・不要と言った場合のみ
        - 変更が無い場合は {} を返す
        """
    },
    "job": {
        "system": """
        # 命令書
        あなたは、就活（新卒・転職）の自己PR・ES・面接対策を支援するアシスタントです。
        事実に基づいた内容で、読み手に伝わる文章と答え方を一緒に作ります。

        ## あなたの役割
        - 自己PR、ガクチカ、志望動機、ES設問、面接対策の作成・添削・改善を行う。
        - 企業・業界・職種、文字数や設問文、選考フェーズを確認し、最適化する。
        - 具体例（数字・期間・役割・工夫・結果）を引き出して説得力を高める。
        - 事実の捏造はしない。不足情報は質問で補うか、プレースホルダーを提示する。

        ## 実行ステップ
        1. 取り組みたい内容（自己PR/ES/志望動機/面接など）を確認。
        2. 企業・業界・職種、設問文、文字数、背景情報を確認。
        3. 構成（PREP/STAR）を提示し、ドラフトを作成。
        4. 改善点の指摘と、修正版の提示。

        ## 制約条件と出力ルール（厳守）
        - 言語: 日本語。
        - 応答の長さ: 通常は400文字以内目安。文章作成は指定文字数を優先。
        - 質問: 一度のメッセージで一つの質問。
        - 特殊形式: ユーザーのアクションが必要な場合は、以下の形式を**厳密に**使用すること。
          - Yes/No形式: 「Yes/No: [質問内容]」
          - 選択肢形式: 「Select: [選択肢1, 選択肢2, ..., その他]」（※半角括弧[]と半角カンマを使用、最大6つ）
          - 日付選択形式: 「DateSelect: true」
        - 重要: 特殊形式は**独立した行**として出力し、他の文章と混ぜないこと。
        - 重要: 特殊形式を出力する際は、その直前に必ずユーザーへの**親しみやすい案内文**を配置すること（特殊形式のみの出力は禁止）。
          - 案内文は「Select:」や角括弧の選択肢を含めない、ユーザーに話しかける自然な文にする。
          - 例: 「どの項目から始めますか？」「当てはまるものを選んでください。」
        - 重要: 特殊形式は同時に複数使わない（Yes/No, Select, DateSelectはいずれか1つのみ）。

        ## 出力例（厳密）
        ユーザー: 就活の相談をしたい
        アシスタント: まずどこから取り組みたいですか？
        Select: [自己PR, ES, 志望動機, 面接対策, その他]
        ユーザー: 面接練習がしたい
        アシスタント: 対象企業・職種を教えてください。
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている就活の項目（対象企業・職種、設問文、文字数、自己PR要素、ガクチカ要素、志望動機要素、面接対策方針など）の差分だけを抽出するアシスタントです。
        - 出力は**必ず**1つのJSONオブジェクトのみ（コードブロックや説明文は禁止）。
        - 形式: {"add": {"項目名": "内容"}, "update": {"項目名": "内容"}, "remove": ["項目名", ...]}
        - add: まだ無い決定事項の新規追加のみ
        - update: 既存の決定事項が変更・更新された場合のみ
        - remove: ユーザーが取り消し・不要と言った場合のみ
        - 変更が無い場合は {} を返す
        """
    },
    "study": {
        "system": """
        # 命令書
        あなたは学習アシスタントです。授業メモや教材内容を、理解しやすい整理ノートに変換し、
        用語整理や確認問題など学習に必要な支援を行います。

        ## あなたの役割
        - 受け取ったメモを構造化し、見出し＋箇条書きで整理する。
        - 重要語句、要点サマリー、確認問題、次にやる学習タスクを作成する。
        - 事実が不明な場合は推測せず、不足情報を質問で補う。

        ## 出力の基本方針
        - 見出しは「##」で始める。
        - 箇条書きは「-」で統一する。
        - 1つの返答で1つのタスクに集中する。

        ## 制約条件と出力ルール（厳守）
        - 言語: 日本語。
        - 応答の長さ: 600文字以内目安（指定がある場合は指定優先）。
        - 質問: 一度のメッセージで一つの質問。
        - 特殊形式: ユーザーのアクションが必要な場合は、以下の形式を**厳密に**使用すること。
          - Yes/No形式: 「Yes/No: [質問内容]」
          - 選択肢形式: 「Select: [選択肢1, 選択肢2, ..., その他]」（※半角括弧[]と半角カンマを使用、最大6つ）
          - 日付選択形式: 「DateSelect: true」
        - 重要: 特殊形式は**独立した行**として出力し、他の文章と混ぜないこと。
        - 重要: 特殊形式を出力する際は、その直前に必ずユーザーへの**親しみやすい案内文**を配置すること（特殊形式のみの出力は禁止）。
          - 案内文は「Select:」や角括弧の選択肢を含めない、ユーザーに話しかける自然な文にする。
          - 例: 「当てはまるものを選んでください。」
        - 重要: 特殊形式は同時に複数使わない（Yes/No, Select, DateSelectはいずれか1つのみ）。

        ## 出力例（厳密）
        ユーザー: 整理ノートを作って
        アシスタント:
        ## 重要ポイント
        - ・・・
        ## 用語
        - ・・・
        """,
        "decision_system": """
        あなたは渡されたチャット履歴から、現在決定されている学習情報（授業名・範囲・学習目標・重要ポイント・用語・確認問題・次のタスク）の差分だけを抽出するアシスタントです。
        - 出力は**必ず**1つのJSONオブジェクトのみ（コードブロックや説明文は禁止）。
        - 形式: {"add": {"項目名": "内容"}, "update": {"項目名": "内容"}, "remove": ["項目名", ...]}
        - add: まだ無い決定事項の新規追加のみ
        - update: 既存の決定事項が変更・更新された場合のみ
        - remove: ユーザーが取り消し・不要と言った場合のみ
        - 変更が無い場合は {} を返す
        """
    }
}

def current_datetime_jp_line() -> str:
    """現在日時を日本語フォーマットで返すヘルパー関数"""
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    now = datetime.now()
    weekday = weekday_map[now.weekday()]
    return f"現在日時: {now.year}年{now.month}月{now.day}日（{weekday}） {now.hour:02d}:{now.minute:02d}"


def sanitize_llm_text(text: Optional[str], max_length: int = MAX_OUTPUT_CHARS) -> str:
    """
    LLMからの出力テキストをサニタイズ（制御文字除去、長さ制限）する
    """
    if text is None:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str(text))
    cleaned = cleaned.strip()
    if max_length and len(cleaned) > max_length:
        cleaned = f"{cleaned[:max_length]}..."
    return cleaned


def _normalize_decision_line(line: str) -> str:
    cleaned = DECISION_BULLET_PREFIX_RE.sub("", line.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _split_decision_lines(text: Optional[str]) -> List[str]:
    if not text:
        return []
    lines: List[str] = []
    for raw in str(text).splitlines():
        cleaned = _normalize_decision_line(raw)
        if not cleaned or cleaned in DECISION_IGNORED_LINES:
            continue
        lines.append(cleaned)
    return lines


def _parse_decision_key_value(line: str) -> Optional[Tuple[str, str]]:
    parts = DECISION_KV_SEPARATOR_RE.split(line, maxsplit=1)
    if len(parts) != 2:
        return None
    key, value = parts[0].strip(), parts[1].strip()
    if not key or not value:
        return None
    return key, value


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_json_object(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = _strip_code_fences(str(text))
    cleaned = cleaned.strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                obj = json.loads(snippet)
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
    return None


def _normalize_decision_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch or not isinstance(patch, dict):
        return None
    filtered = {k: v for k, v in patch.items() if k in DECISION_PATCH_ALLOWED_KEYS}

    def normalize_map(value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {}
        normalized: Dict[str, str] = {}
        for key, val in value.items():
            k = str(key).strip()
            v = str(val).strip()
            if k and v:
                normalized[k] = v
        return normalized

    def normalize_remove(value: Any) -> List[str]:
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = [value]
        else:
            return []
        result: List[str] = []
        for item in items:
            key = str(item).strip()
            if key:
                result.append(key)
        return result

    add = normalize_map(filtered.get("add"))
    update = normalize_map(filtered.get("update"))
    remove = normalize_remove(filtered.get("remove"))

    if not add and not update and not remove:
        return {}
    return {"add": add, "update": update, "remove": remove}


def _parse_decision_items(text: Optional[str]) -> Tuple[List[Dict[str, str]], Dict[str, int], set]:
    items: List[Dict[str, str]] = []
    key_index: Dict[str, int] = {}
    plain_set: set = set()
    for line in _split_decision_lines(text):
        kv = _parse_decision_key_value(line)
        if kv:
            key, value = kv
            item = {"type": "kv", "key": key, "value": value}
            if key in key_index:
                items[key_index[key]] = item
            else:
                key_index[key] = len(items)
                items.append(item)
        else:
            if line not in plain_set:
                items.append({"type": "plain", "value": line})
                plain_set.add(line)
    return items, key_index, plain_set


def _decision_items_to_text(items: List[Dict[str, str]]) -> str:
    if not items:
        return DECISION_DEFAULT_MESSAGE
    lines: List[str] = []
    for item in items:
        if item["type"] == "kv":
            lines.append(f'{item["key"]}：{item["value"]}')
        else:
            lines.append(item["value"])
    return "\n".join(lines)


def _apply_decision_patch(prev_text: Optional[str], patch: Dict[str, Any]) -> str:
    add = patch.get("add") or {}
    update = patch.get("update") or {}
    remove_list = patch.get("remove") or []

    if not add and not update and not remove_list:
        existing = "\n".join(_split_decision_lines(prev_text))
        return existing if existing else DECISION_DEFAULT_MESSAGE

    items, key_index, plain_set = _parse_decision_items(prev_text)

    remove_set = {key for key in remove_list if key}
    if remove_set:
        items = [
            item
            for item in items
            if not (item["type"] == "kv" and item["key"] in remove_set)
        ]
        key_index = {item["key"]: idx for idx, item in enumerate(items) if item["type"] == "kv"}

    def apply_map(value_map: Dict[str, str]) -> None:
        for key, value in value_map.items():
            if key in remove_set:
                continue
            item = {"type": "kv", "key": key, "value": value}
            if key in key_index:
                items[key_index[key]] = item
            else:
                key_index[key] = len(items)
                items.append(item)

    apply_map(add)
    apply_map(update)

    merged = _decision_items_to_text(items)
    return sanitize_llm_text(merged, max_length=MAX_DECISION_CHARS)


def _merge_decision_text(prev_text: Optional[str], new_text: Optional[str]) -> str:
    prev_lines = _split_decision_lines(prev_text)
    new_lines = _split_decision_lines(new_text)

    if not prev_lines and not new_lines:
        return DECISION_DEFAULT_MESSAGE
    if not new_lines:
        return "\n".join(prev_lines)

    result_lines = list(prev_lines)
    key_index: Dict[str, int] = {}
    for idx, line in enumerate(result_lines):
        kv = _parse_decision_key_value(line)
        if kv:
            key_index[kv[0]] = idx

    seen_plain = {line for line in result_lines if not _parse_decision_key_value(line)}

    for line in new_lines:
        kv = _parse_decision_key_value(line)
        if kv:
            key = kv[0]
            if key in key_index:
                result_lines[key_index[key]] = line
            else:
                key_index[key] = len(result_lines)
                result_lines.append(line)
        else:
            if line not in seen_plain:
                result_lines.append(line)
                seen_plain.add(line)

    merged = "\n".join(result_lines)
    return sanitize_llm_text(merged, max_length=MAX_DECISION_CHARS)


def output_is_safe(text: str) -> bool:
    """
    出力テキストの安全性をチェックする（Guard使用）
    """
    if not OUTPUT_GUARD_ENABLED or not text:
        return True
    try:
        result = guard.content_checker(text)
        return "unsafe" not in result
    except Exception as e:
        logger.error(f"Output safety check failed: {e}")
        return False


def _build_messages(
    system_prompt: str,
    chat_history: List[Tuple[str, str]],
    user_input: str,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for role, content in chat_history:
        if role == "assistant":
            messages.append({"role": "assistant", "content": content})
        else:
            messages.append({"role": "user", "content": content})
    messages.append({"role": "user", "content": user_input})
    return messages


def _invoke_chat_completion(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
    tool_choice: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> str:
    client = get_groq_client()
    payload: Dict[str, Any] = {
        "model": model_name or GROQ_MODEL_NAME,
        "messages": messages,
    }
    if tool_choice:
        payload["tool_choice"] = tool_choice
    if tools is not None:
        payload["tools"] = tools
    completion = client.chat.completions.create(**payload)
    return _extract_message_content(completion.choices[0].message)


PASS_THROUGH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "assistant",
            "description": "Return assistant message content when the model tries to call a tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    }
]


def _extract_message_content(message: Any) -> str:
    content = getattr(message, "content", None) or ""
    if content:
        return content
    tool_calls = getattr(message, "tool_calls", None) or []
    for call in tool_calls:
        function = getattr(call, "function", None)
        if not function:
            continue
        name = getattr(function, "name", "")
        if name != "assistant":
            continue
        args = getattr(function, "arguments", None)
        parsed = None
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError:
                parsed = None
        elif isinstance(args, dict):
            parsed = args
        if isinstance(parsed, dict):
            content_value = parsed.get("content")
            if content_value:
                return str(content_value)
        if isinstance(args, str) and args:
            return args
    return ""


def _invoke_with_tool_retries(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> str:
    try:
        return _invoke_chat_completion(messages, model_name=model_name)
    except Exception as e:
        if not _is_tool_use_failed(e):
            raise

    if GROQ_FALLBACK_MODEL_NAME:
        logger.warning(
            "Groq tool_use_failed; retrying with fallback model: %s",
            GROQ_FALLBACK_MODEL_NAME,
        )
        try:
                return _invoke_chat_completion(messages, model_name=GROQ_FALLBACK_MODEL_NAME)
        except Exception as retry_err:
            if _is_tool_use_failed(retry_err):
                logger.warning("Groq tool_use_failed on fallback; retrying with tool_choice=auto")
                return _invoke_chat_completion(
                    messages,
                    model_name=GROQ_FALLBACK_MODEL_NAME,
                    tool_choice="auto",
                    tools=PASS_THROUGH_TOOLS,
                )
            raise

    logger.warning("Groq tool_use_failed; retrying with tool_choice=auto")
    return _invoke_chat_completion(
        messages,
        model_name=model_name,
        tool_choice="auto",
        tools=PASS_THROUGH_TOOLS,
    )

def _is_tool_use_failed(err: Exception) -> bool:
    text = f"{err}"
    if "tool_use_failed" in text or "Tool choice is none" in text or "called a tool" in text:
        return True
    body = getattr(err, "body", None)
    if isinstance(body, dict):
        error = body.get("error") or {}
        if error.get("code") == "tool_use_failed":
            return True
        if "tool" in str(error.get("message", "")):
            return True
    return False

def run_qa_chain(
    message: str,
    chat_history: List[Tuple[str, str]],
    mode: str = "travel",
    decision_text: Optional[str] = None,
) -> Tuple[str, Optional[str], Optional[List[str]], bool, str]:
    """
    ユーザーのメッセージに対してLLMで応答を生成する
    
    1. プロンプトの構築（システムプロンプト + 履歴 + ユーザー入力）
    2. LLMの呼び出し
    3. レスポンスのサニタイズと安全性チェック
    4. 特殊形式（Select, Yes/No, DateSelect）の抽出と解析
    """
    system_prompt = PROMPTS.get(mode, PROMPTS["travel"])["system"] + "\n" + current_datetime_jp_line()
    decision_text = (decision_text or "").strip()
    if decision_text in ("決定している項目がありません。", "決定事項の更新中にエラーが発生しました。"):
        decision_text = ""
    if decision_text:
        system_prompt += (
            "\n\n## 既に決定している情報\n"
            f"{decision_text}\n"
            "- 既に決定している内容は繰り返し質問せず、次に必要な情報を確認してください。"
        )
    
    messages = _build_messages(system_prompt, chat_history, message)
    response = _invoke_with_tool_retries(messages)
    response = sanitize_llm_text(response)

    if not output_is_safe(response):
        safe_message = "安全性の理由で表示できません。"
        return safe_message, None, None, False, safe_message

    # Yes/No形式の抽出ロジック
    yes_no_phrase = None
    choices = None
    is_date_select = False
    remaining_text = response

    # Select: [...] 形式の抽出 (正規表現)
    select_match = re.search(r'Select\s*[:：]\s*[\[\［](.*?)[\]\］]', response, re.DOTALL)
    if select_match:
        choices_str = select_match.group(1)
        # カンマ区切り（全角・半角）でリスト化し、引用符などを除去
        parts = re.split(r'[,、，]', choices_str)
        choices = [c.strip().strip('"\'') for c in parts if c.strip()]
        # Select部分を除去してremaining_textを更新
        remaining_text = remaining_text.replace(select_match.group(0), "").strip()

    # DateSelect: true 形式の抽出
    date_match = re.search(r'DateSelect\s*[:：]\s*true', remaining_text, re.IGNORECASE)
    if date_match:
        is_date_select = True
        remaining_text = remaining_text.replace(date_match.group(0), "").strip()

    # Yes/No形式の抽出 (Selectが見つからなかった場合、または共存する場合)
    if not choices and not is_date_select and "Yes/No" in remaining_text:
        start = remaining_text.find('Yes/No:')
        if start != -1:
            q_full = remaining_text.find('？', start)
            q_half = remaining_text.find('?', start)
            q_pos = q_full if q_full != -1 else q_half
            
            if q_pos != -1:
                yes_no_phrase = remaining_text[start + len('Yes/No:'):q_pos + 1]
                remaining_text = remaining_text[:start] + remaining_text[q_pos + 1:]
                
    remaining_text = sanitize_llm_text(remaining_text)
    if not remaining_text.strip():
        remaining_text = "Empty"

    return response, yes_no_phrase, choices, is_date_select, remaining_text

def write_decision(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    mode: str = "travel",
) -> str:
    """
    チャット履歴から決定事項を抽出し、Redisに保存する
    
    LLMを使用して、会話の内容から「目的地」や「日程」などの確定事項を要約させます。
    """
    default_message = DECISION_DEFAULT_MESSAGE
    message = (
        "これまでの決定事項に新しく追加・変更された内容があれば、その項目だけをJSONで出力してください。"
        "未確定や推測は書かず、説明や挨拶は一切不要です。"
    )
    
    try:
        previous_text = redis_client.get_decision(session_id) or ""
        previous_lines = _split_decision_lines(previous_text)
        content = "\n".join(previous_lines) if previous_lines else default_message
        system_prompt = (
            PROMPTS.get(mode, PROMPTS["travel"])["decision_system"]
            + "\n"
            + current_datetime_jp_line()
            + f"\n以前の決定事項:\n{content}\n"
        )
        messages = _build_messages(system_prompt, chat_history, message)
        response = _invoke_with_tool_retries(messages)
        response = sanitize_llm_text(response, max_length=MAX_DECISION_CHARS)
        if not output_is_safe(response):
            safe_text = "\n".join(previous_lines) if previous_lines else default_message
            redis_client.save_decision(session_id, safe_text)
            return safe_text

        patch = _normalize_decision_patch(_extract_json_object(response))
        if patch is not None:
            merged = _apply_decision_patch(previous_text, patch)
        else:
            merged = _merge_decision_text(previous_text, response)

        redis_client.save_decision(session_id, merged)
        return merged
    except Exception as e:
        logger.error(f"Error in write_decision: {e}")
        return "決定事項の更新中にエラーが発生しました。"

def chat_with_llama(
    session_id: str,
    prompt: str,
    mode: str = "travel",
) -> Tuple[Optional[str], str, Optional[str], Optional[List[str]], bool, str]:
    """
    LLMとの対話を行うメイン関数
    
    1. 入力の安全性チェック
    2. チャット履歴の取得
    3. LLM応答の生成（run_qa_chain）
    4. 履歴と決定事項の保存
    """
    result = guard.content_checker(prompt)
    if 'unsafe' in result:
        return None, redis_client.get_decision(session_id) or "安全性の問題で表示できません", None, None, False, "それには答えられません"
    
    chat_history = redis_client.get_chat_history(session_id)
    decision_text = redis_client.get_decision(session_id)

    response, yes_no_phrase, choices, is_date_select, remaining_text = run_qa_chain(
        prompt, chat_history, mode=mode, decision_text=decision_text
    )
    response = sanitize_llm_text(response)
    remaining_text = sanitize_llm_text(remaining_text)
    
    chat_history.append(("human", prompt))
    chat_history.append(("assistant", response))
    redis_client.save_chat_history(session_id, chat_history)
    current_plan = write_decision(session_id, chat_history, mode=mode)
    
    return response, current_plan, yes_no_phrase, choices, is_date_select, remaining_text
