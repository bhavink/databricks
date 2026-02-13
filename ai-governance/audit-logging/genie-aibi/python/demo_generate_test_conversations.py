"""
On-demand test data for Genie audit pipeline: start a conversation and ask follow-ups per space.

Uses the Genie Conversation API (start-conversation, then POST messages for follow-ups).
Respects: 5 queries per minute per workspace (12+ s between POSTs), polling with exponential
backoff, 10 min timeout. Run on Databricks (notebook or job) so dbutils is available for OAuth.

Config: config.py — WORKSPACE_IDS, SPACE_IDS_BY_WORKSPACE, SECRETS_SCOPE; optional WORKSPACE_URLS.
If WORKSPACE_URLS is None, workspace URLs are read from main.genie_analytics.genie_messages_to_fetch
when run on Databricks.

Refs:
- Start conversation: https://docs.databricks.com/aws/en/genie/conversation-api#-start-a-conversation
- Ask follow-up questions: https://docs.databricks.com/aws/en/genie/conversation-api#-ask-follow-up-questions
- Best practices: https://docs.databricks.com/aws/en/genie/conversation-api#best-practices-for-using-the-genie-api
- Throughput limit: 5 queries per minute per workspace
"""
# =============================================================================
# Genie Conversation Test Data — On-Demand Messages via Genie Conversation API
# =============================================================================
# Purpose:
#   1. Start a Genie conversation per configured space (Conversation API).
#   2. Send 1–2 follow-up questions per space; poll until COMPLETED or timeout.
#   3. Generate audit events that flow into the SDP pipeline and message_details.
#   4. Respect 5 queries/min per workspace and polling best practices.
# =============================================================================
from __future__ import annotations

import time
import logging
from typing import Any

import requests

# Ensure same-folder imports when run as job or %run
import os
import sys
try:
    _this_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _this_dir = os.path.join(os.getcwd(), "python") if os.path.isdir(os.path.join(os.getcwd(), "python")) else os.getcwd()
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

import config as cfg
from genie_oauth import get_headers_for_workspace
from genie_message_ingestion import get_dbutils

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Genie API: throughput 5 queries per minute per workspace → min 12 s between POSTs
MIN_SECONDS_BETWEEN_POSTS = 15
POLL_INTERVAL_INITIAL = 2
POLL_INTERVAL_MAX = 60
POLL_TIMEOUT_SECONDS = 600  # 10 min
MAX_POLL_RETRIES = 3  # retries for GET (transient errors)
MAX_POST_RETRIES = 3  # retries for POST with exponential backoff

# Sample questions (generic so they work across spaces; spaces may have different tables)
INITIAL_QUESTION = "What were total sales last month?"
FOLLOW_UP_1 = "Break that down by region."
FOLLOW_UP_2 = "Show top 10 by revenue."


def _resolve_workspace_urls(dbutils) -> dict[str, str]:
    """Return dict workspace_id -> workspace_url. Prefer config WORKSPACE_URLS; else SOT table."""
    urls = getattr(cfg, "WORKSPACE_URLS", None)
    if urls and isinstance(urls, dict):
        return {k: v.rstrip("/") for k, v in urls.items() if v}
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        df = spark.table(f"{cfg.TARGET_CATALOG}.{cfg.TARGET_SCHEMA}.genie_messages_to_fetch")
        rows = df.select("workspace_id", "workspace_url").distinct().collect()
        return {r["workspace_id"]: (r["workspace_url"] or "").rstrip("/") for r in rows if r.get("workspace_url")}
    except Exception as e:
        log.warning("Could not resolve workspace URLs from SOT table: %s", e)
        return {}


def _list_workspace_space_pairs() -> list[tuple[str, str]]:
    """(workspace_id, space_id) from WORKSPACE_IDS and SPACE_IDS_BY_WORKSPACE."""
    workspace_ids = getattr(cfg, "WORKSPACE_IDS", None) or []
    space_by_ws = getattr(cfg, "SPACE_IDS_BY_WORKSPACE", None)
    out = []
    for ws_id in workspace_ids:
        if space_by_ws is None:
            # Script requires explicit spaces for targeted test; we don't list all spaces here
            log.warning("SPACE_IDS_BY_WORKSPACE is None; skipping workspace %s (set it for test)", ws_id)
            continue
        spaces = space_by_ws.get(ws_id)
        if not spaces:
            continue
        for space_id in spaces:
            out.append((ws_id, space_id))
    return out


def _poll_message(
    base_url: str,
    space_id: str,
    conversation_id: str,
    message_id: str,
    headers: dict,
) -> tuple[str, dict | None]:
    """
    Poll GET message until COMPLETED, FAILED, or CANCELLED. Returns (status, response_json).
    Uses exponential backoff (2s, 4s, ... max 60s), timeout 10 min.
    """
    url = f"{base_url}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}"
    start = time.monotonic()
    interval = POLL_INTERVAL_INITIAL
    last_response = None
    while (time.monotonic() - start) < POLL_TIMEOUT_SECONDS:
        for attempt in range(MAX_POLL_RETRIES):
            try:
                r = requests.get(url, headers=headers, timeout=30)
                r.raise_for_status()
                last_response = r.json()
                status = (last_response or {}).get("status") or ""
                if status in ("COMPLETED", "FAILED", "CANCELLED"):
                    return status, last_response
                break
            except requests.RequestException as e:
                if attempt == MAX_POLL_RETRIES - 1:
                    log.warning("Poll GET failed after retries: %s", e)
                    return "POLL_ERROR", last_response
                time.sleep(interval)
        time.sleep(interval)
        interval = min(interval * 2, POLL_INTERVAL_MAX)
    log.warning("Poll timeout after %s s", POLL_TIMEOUT_SECONDS)
    return "TIMEOUT", last_response


def _post_with_retry(
    url: str,
    headers: dict,
    json_body: dict,
    description: str,
) -> tuple[bool, dict | None]:
    """POST with exponential backoff on 429/5xx. Returns (success, response_json)."""
    for attempt in range(MAX_POST_RETRIES):
        try:
            r = requests.post(url, headers=headers, json=json_body, timeout=60)
            if r.status_code == 200:
                return True, r.json()
            if r.status_code == 429 or r.status_code >= 500:
                backoff = (2 ** attempt) * 5  # 5, 10, 20 s
                log.warning("%s: %s %s; retry in %s s", description, r.status_code, r.text[:200], backoff)
                time.sleep(backoff)
                continue
            log.error("%s: %s %s", description, r.status_code, r.text[:500])
            return False, None
        except requests.RequestException as e:
            backoff = (2 ** attempt) * 5
            log.warning("%s: %s; retry in %s s", description, e, backoff)
            time.sleep(backoff)
    return False, None


def run_conversation_test(
    dbutils,
    scope: str | None = None,
    initial_question: str = INITIAL_QUESTION,
    follow_ups: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    For each (workspace, space) from config: start a conversation, poll, send follow-ups, poll.
    Respects 5 queries/min per workspace (15 s between POSTs). Returns list of result dicts
    (workspace_id, space_id, conversation_id, message_ids, statuses, errors).
    """
    scope = scope or getattr(cfg, "SECRETS_SCOPE", "genie-obs")
    follow_ups = follow_ups if follow_ups is not None else [FOLLOW_UP_1, FOLLOW_UP_2]

    workspace_urls = _resolve_workspace_urls(dbutils)
    pairs = _list_workspace_space_pairs()
    if not pairs:
        log.warning("No (workspace_id, space_id) pairs from config; check WORKSPACE_IDS and SPACE_IDS_BY_WORKSPACE.")
        return []

    results = []
    for ws_id, space_id in pairs:
        base_url = workspace_urls.get(ws_id)
        if not base_url:
            log.warning("No workspace_url for workspace_id=%s; set WORKSPACE_URLS in config or run pipeline once.", ws_id)
            results.append({"workspace_id": ws_id, "space_id": space_id, "error": "no_workspace_url"})
            continue

        try:
            headers = get_headers_for_workspace(base_url, dbutils=dbutils, scope=scope)
        except Exception as e:
            log.exception("OAuth failed for workspace %s: %s", ws_id, e)
            results.append({"workspace_id": ws_id, "space_id": space_id, "error": str(e)})
            continue

        # Start conversation
        start_url = f"{base_url}/api/2.0/genie/spaces/{space_id}/start-conversation"
        ok, start_resp = _post_with_retry(
            start_url, headers, {"content": initial_question}, "start-conversation"
        )
        if not ok or not start_resp:
            results.append({"workspace_id": ws_id, "space_id": space_id, "error": "start_conversation_failed"})
            continue

        conversation = start_resp.get("conversation") or {}
        message = start_resp.get("message") or {}
        conversation_id = conversation.get("id")
        message_id = message.get("id")
        if not conversation_id or not message_id:
            results.append({"workspace_id": ws_id, "space_id": space_id, "error": "missing_conversation_or_message_id"})
            continue

        log.info("Started conversation %s, message %s on workspace %s space %s", conversation_id, message_id, ws_id, space_id)
        status1, _ = _poll_message(base_url, space_id, conversation_id, message_id, headers)
        message_ids = [message_id]
        statuses = [status1]

        # Follow-ups
        for i, content in enumerate(follow_ups):
            time.sleep(MIN_SECONDS_BETWEEN_POSTS)  # Throughput: 5/min per workspace
            follow_url = f"{base_url}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages"
            ok, follow_resp = _post_with_retry(follow_url, headers, {"content": content}, f"follow-up-{i+1}")
            if not ok or not follow_resp:
                statuses.append("POST_FAILED")
                break
            msg = follow_resp.get("message") or follow_resp
            mid = msg.get("id")
            if mid:
                message_ids.append(mid)
                st, _ = _poll_message(base_url, space_id, conversation_id, mid, headers)
                statuses.append(st)
            else:
                statuses.append("NO_MESSAGE_ID")

        results.append({
            "workspace_id": ws_id,
            "space_id": space_id,
            "conversation_id": conversation_id,
            "message_ids": message_ids,
            "statuses": statuses,
            "error": None,
        })
        # Rate limit before next workspace
        time.sleep(MIN_SECONDS_BETWEEN_POSTS)

    return results


def main():
    """Entrypoint when run as script (e.g. Databricks job or %run)."""
    dbutils = get_dbutils()
    if not dbutils:
        raise RuntimeError("dbutils not available; run this script on Databricks (notebook or job).")
    results = run_conversation_test(dbutils)
    for r in results:
        if r.get("error"):
            log.info("Result: %s", r)
        else:
            log.info("Result: workspace=%s space=%s conversation=%s message_ids=%s statuses=%s",
                     r["workspace_id"], r["space_id"], r["conversation_id"], r["message_ids"], r["statuses"])
    return results


if __name__ == "__main__":
    main()
