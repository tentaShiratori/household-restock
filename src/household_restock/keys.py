"""DynamoDB キー形状（v0.1.0 採用案）。"""

from __future__ import annotations

ITEM_PK_PREFIX = "ITEM#"
META_SK = "META"
RESTOCK_SK_PREFIX = "RESTOCK#"
ENTITY_ITEM = "ITEM"
ENTITY_RESTOCK = "RESTOCK"


def item_pk(item_id: str) -> str:
    return f"{ITEM_PK_PREFIX}{item_id}"


def restock_sk(stream_event_id: str) -> str:
    return f"{RESTOCK_SK_PREFIX}{stream_event_id}"


def parse_item_id_from_pk(pk: str) -> str | None:
    if not pk.startswith(ITEM_PK_PREFIX):
        return None
    item_id = pk.removeprefix(ITEM_PK_PREFIX)
    return item_id or None


def is_item_meta_record(*, pk: str, sk: str, entity_type: str | None) -> bool:
    """品目メタ行か。補充リクエスト行は False。"""
    if parse_item_id_from_pk(pk) is None:
        return False
    if sk != META_SK:
        return False
    if entity_type is not None and entity_type != ENTITY_ITEM:
        return False
    return True


def sfn_execution_name(*, item_id: str, stream_event_id: str) -> str:
    """Step Functions 実行名（同一 eventID で一意）。許可文字以外は '-'。"""
    raw = f"restock-{item_id}-{stream_event_id}"
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)
    return cleaned[:80]
