"""Wishlist watcher script for detecting updates on Amazon wishlist and notifying Slack."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from html import unescape
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlencode, urljoin, urlparse
import re

import requests
from bs4 import BeautifulSoup, Tag

# Default constants matching the spec but overridable with environment variables.
DEFAULT_STATE_FILENAME = "state_friend.json"
DEFAULT_LIST_URL = "https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
DEFAULT_ACCEPT_LANGUAGE = "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
DEFAULT_WEBHOOK_URL = os.environ.get("DEFAULT_WEBHOOK_URL")
REQUEST_TIMEOUT = 20  # seconds
MAX_FETCH_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 2
MAX_PAGINATION_PAGES = int(os.environ.get("MAX_PAGINATION_PAGES", "300"))

logger = logging.getLogger("wishlist_watcher")

IGNORED_TITLE_TEXTS = {"", "もっと見る", "詳細を見る", "今すぐチェック", "すべて表示"}


@dataclass(frozen=True)
class WishlistItem:
    """Represents a single wishlist item snapshot."""

    item_id: str
    title: str
    price: Optional[float]
    url: str

    @classmethod
    def from_html(cls, node: Tag, base_url: str) -> Optional["WishlistItem"]:
        """Convert an item node into a WishlistItem, or return None if parsing fails."""

        title, link = _extract_title_and_link(node)
        if not title and not link:
            return None
        if not title:
            return None

        absolute_url = urljoin(base_url, link) if link else base_url
        item_id = _extract_asin(link) if link else None
        if not item_id:
            # Fallback to hash of title and URL to produce stable identifier.
            hash_source = f"{title}\n{absolute_url}".encode("utf-8", errors="ignore")
            item_id = hashlib.sha1(hash_source).hexdigest()

        price = _extract_price(node)
        return cls(item_id=item_id, title=title, price=price, url=absolute_url)


@dataclass
class WishlistState:
    """Serialization-friendly representation of wishlist state."""

    last_checked_at: str
    items: List[WishlistItem]

    def to_dict(self) -> Dict[str, object]:
        return {
            "last_checked_at": self.last_checked_at,
            "items": [
                {
                    "id": item.item_id,
                    "title": item.title,
                    "price": item.price,
                    "url": item.url,
                }
                for item in self.items
            ],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "WishlistState":
        items_payload = payload.get("items", [])
        items = [
            WishlistItem(
                item_id=item["id"],
                title=item.get("title", ""),
                price=item.get("price"),
                url=item.get("url", ""),
            )
            for item in items_payload
            if isinstance(item, dict)
        ]
        last_checked = payload.get("last_checked_at") or datetime.now(timezone.utc).isoformat()
        return cls(last_checked_at=last_checked, items=items)


@dataclass
class WishlistDiff:
    added: List[WishlistItem]
    removed: List[WishlistItem]
    price_changes: List[Tuple[WishlistItem, WishlistItem]]  # (old, new)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.price_changes)


class WishlistWatcherError(Exception):
    """Raised for unrecoverable watcher failures."""


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    list_url = _resolve_list_url()
    webhook_url = _resolve_webhook_url()
    state_dir = Path(os.environ.get("STATE_DIR", "."))
    state_path = state_dir / os.environ.get("STATE_FILENAME", DEFAULT_STATE_FILENAME)
    baseline_only = os.environ.get("BASELINE_ONLY", "false").lower() == "true"

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": os.environ.get("HTTP_USER_AGENT", DEFAULT_USER_AGENT),
            "Accept-Language": os.environ.get("HTTP_ACCEPT_LANGUAGE", DEFAULT_ACCEPT_LANGUAGE),
        }
    )

    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        items = _fetch_all_items(session, list_url)
        now_iso = datetime.now(timezone.utc).isoformat()
        new_state = WishlistState(last_checked_at=now_iso, items=items)

        previous_state = _load_state(state_path)

        if previous_state is None:
            _save_state(state_path, new_state)
            if not baseline_only:
                _notify_slack(webhook_url, "すばるほしいものリスト ベースラインを保存しました (初回実行)", session)
            return 0

        diff = _diff_items(previous_state.items, new_state.items)
        _save_state(state_path, new_state)

        if diff.has_changes:
            text = _format_diff_message(diff, new_state.items)
        else:
            text = _format_no_change_message(new_state.items)
        _notify_slack(webhook_url, text, session)
    except Exception as exc:  # noqa: BLE001
        logger.exception("wishlist watcher failed")
        error_message = f"すばる ウォッチャーでエラーが発生しました: {exc}"
        try:
            _notify_slack(webhook_url, error_message, session)
        except Exception:  # noqa: BLE001
            logger.exception("failed to notify slack about error")
        return 0

    return 0


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise WishlistWatcherError(f"環境変数 {key} が設定されていません")
    return value


def _resolve_list_url() -> str:
    list_url = os.environ.get("LIST_URL", DEFAULT_LIST_URL)
    if not list_url:
        raise WishlistWatcherError("Amazon ウィッシュリストの URL が設定されていません")
    return list_url


def _resolve_webhook_url() -> str:
    candidate = os.environ.get("WEBHOOK_URL")
    webhook_url = candidate or DEFAULT_WEBHOOK_URL
    if not webhook_url:
        raise WishlistWatcherError("Slack Webhook URL が設定されていません")
    return webhook_url


def _fetch_with_retry(session: requests.Session, url: str) -> str:
    last_exception: Optional[Exception] = None

    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                raise WishlistWatcherError("HTTP 429 Too Many Requests")
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_exception = exc
            sleep_seconds = BACKOFF_BASE_SECONDS ** attempt
            logger.warning(
                "failed to fetch wishlist (attempt %s/%s): %s", attempt, MAX_FETCH_ATTEMPTS, exc
            )
            time.sleep(sleep_seconds)

    raise WishlistWatcherError(f"ウィッシュリストの取得に失敗しました: {last_exception}")


def _parse_wishlist(html: str, base_url: str) -> List[WishlistItem]:
    soup = BeautifulSoup(html, "html.parser")
    return _parse_items_from_soup(soup, base_url)


ASIN_PATTERN = re.compile(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})", re.IGNORECASE)


def _extract_title_and_link(node: Tag) -> Tuple[str, Optional[str]]:
    anchors = node.find_all("a", href=True)

    candidate_anchor: Optional[Tag] = None
    candidate_title = ""

    for anchor in anchors:
        href = anchor.get("href", "")
        if ASIN_PATTERN.search(href):
            text = _sanitize_title(anchor.get_text(" ", strip=True))
            if text not in IGNORED_TITLE_TEXTS and text:
                candidate_anchor = anchor
                candidate_title = text
                break
            title_attr = _sanitize_title(anchor.get("title", ""))
            if title_attr and title_attr not in IGNORED_TITLE_TEXTS:
                candidate_anchor = anchor
                candidate_title = title_attr
                break
            candidate_anchor = anchor

    if candidate_anchor is None and anchors:
        candidate_anchor = anchors[0]

    if candidate_anchor and not candidate_title:
        candidate_title = _sanitize_title(candidate_anchor.get_text(" ", strip=True)) or _sanitize_title(
            candidate_anchor.get("title", "")
        )

    if not candidate_title:
        candidate_title = _extract_title_from_node(node)

    href = candidate_anchor.get("href") if candidate_anchor else None
    return candidate_title, href


def _extract_title_from_node(node: Tag) -> str:
    selectors = [
        "span.a-size-base-plus.a-color-base",
        "span.a-size-medium",
        "span.a-size-large",
        "span[id^='itemName_']",
        "h3 a",
        "h4 a",
    ]
    for selector in selectors:
        element = node.select_one(selector)
        if element:
            text = _sanitize_title(element.get_text(" ", strip=True))
            if text and text not in IGNORED_TITLE_TEXTS:
                return text
    return ""


def _sanitize_title(value: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    for token in IGNORED_TITLE_TEXTS - {""}:
        cleaned = cleaned.replace(token, " ")
    return _clean_text(cleaned)


def _clean_text(value: str) -> str:
    return " ".join(value.split()) if value else ""


def _extract_asin(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    match = ASIN_PATTERN.search(href)
    if match:
        return match.group(1).upper()
    parts = urlparse(href)
    path = parts.path
    if not path:
        return None
    segments = path.strip("/").split("/")
    for idx, segment in enumerate(segments):
        if segment.upper() == "DP" and idx + 1 < len(segments):
            candidate = segments[idx + 1]
            if candidate:
                return candidate
    return None


def _extract_price(node: Tag) -> Optional[float]:
    # Amazon renders multiple price formats, try the most specific selectors first.
    price_node = node.select_one(".a-price .a-offscreen")
    if price_node and price_node.get_text(strip=True):
        return _parse_price(price_node.get_text(strip=True))

    whole = node.select_one(".a-price-whole")
    if whole:
        whole_text = whole.get_text(strip=True)
        frac_node = node.select_one(".a-price-fraction")
        if frac_node:
            frac_text = frac_node.get_text(strip=True)
            price_text = f"{whole_text}.{frac_text}"
        else:
            price_text = whole_text
        return _parse_price(price_text)

    alt_node = node.find(class_="a-color-price")
    if alt_node and alt_node.get_text(strip=True):
        return _parse_price(alt_node.get_text(strip=True))

    return None


def _extract_show_more_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    from_input = soup.select_one("[name='showMoreUrl']")
    if from_input and from_input.get("value"):
        value = unescape(from_input.get("value", ""))
        if value:
            return urljoin(base_url, value)

    for script_tag in soup.find_all("script", {"type": "a-state"}):
        data_state_attr = script_tag.attrs.get("data-a-state")
        if not data_state_attr:
            continue
        if "scrollState" not in data_state_attr:
            continue
        raw_text = script_tag.string or ""
        if not raw_text.strip():
            continue
        try:
            payload = json.loads(unescape(raw_text))
        except json.JSONDecodeError:
            continue
        show_more = payload.get("showMoreUrl")
        if show_more:
            return urljoin(base_url, unescape(show_more))
        pagination_token = payload.get("paginationToken")
        if pagination_token:
            query = {
                "filter": "unpurchased",
                "paginationToken": pagination_token,
                "itemsLayout": "LIST",
                "sort": "date-added",
                "type": "wishlist",
            }
            parsed_base = urlparse(base_url)
            lid = parsed_base.path.rstrip("/").split("/")[-1]
            query["lid"] = lid
            return urljoin(base_url, f"/hz/wishlist/slv/items?{urlencode(query)}")

    return None


def _parse_price(text: str) -> Optional[float]:
    cleansed = text.replace("¥", "").replace("￥", "").replace(",", "").strip()
    if cleansed == "":
        return None
    try:
        return float(cleansed)
    except ValueError:
        return None


def _load_state(path: Path) -> Optional[WishlistState]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if not isinstance(payload, dict):
            raise ValueError("state payload must be object")
        return WishlistState.from_dict(payload)
    except Exception as exc:  # noqa: BLE001
        raise WishlistWatcherError(f"状態ファイルの読み込みに失敗しました: {exc}") from exc


def _save_state(path: Path, state: WishlistState) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fp:
        json.dump(state.to_dict(), fp, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _diff_items(old_items: Sequence[WishlistItem], new_items: Sequence[WishlistItem]) -> WishlistDiff:
    old_map: Dict[str, WishlistItem] = {item.item_id: item for item in old_items}
    new_map: Dict[str, WishlistItem] = {item.item_id: item for item in new_items}

    added = [new_map[item_id] for item_id in new_map.keys() - old_map.keys()]
    removed = [old_map[item_id] for item_id in old_map.keys() - new_map.keys()]

    price_changes: List[Tuple[WishlistItem, WishlistItem]] = []
    for item_id in new_map.keys() & old_map.keys():
        old_item = old_map[item_id]
        new_item = new_map[item_id]
        if old_item.price != new_item.price:
            price_changes.append((old_item, new_item))

    return WishlistDiff(added=added, removed=removed, price_changes=price_changes)


def _format_diff_message(diff: WishlistDiff, current_items: Iterable[WishlistItem]) -> str:
    lines = ["すばるほしい物リスト 更新 (変化あり)"]

    total_price = _sum_prices(current_items)
    if total_price is not None:
        lines.append(f"総額: ¥{int(total_price):,}")
    else:
        lines.append("総額: 不明")

    if diff.added:
        lines.append("\n【追加】")
        for item in sorted(diff.added, key=lambda i: i.title.lower()):
            price_text = _format_price(item.price)
            lines.append(f"- {item.title}{price_text}")

    if diff.removed:
        lines.append("\n【削除】")
        for item in sorted(diff.removed, key=lambda i: i.title.lower()):
            lines.append(f"- {item.title}")

    if diff.price_changes:
        lines.append("\n【価格変更】")
        for old_item, new_item in sorted(diff.price_changes, key=lambda pair: pair[1].title.lower()):
            before = _format_price(old_item.price, include_parens=False)
            after = _format_price(new_item.price, include_parens=False)
            delta = _format_price_delta(old_item.price, new_item.price)
            lines.append(f"- {new_item.title}: {before} → {after} ({delta})")

    return "\n".join(lines)


def _format_no_change_message(current_items: Sequence[WishlistItem]) -> str:
    lines = ["すばるほしい物リスト 更新 (変化なし)"]

    total_price = _sum_prices(current_items)
    if total_price is not None:
        lines.append(f"総額: ¥{int(total_price):,}")
    else:
        lines.append("総額: 不明")

    lines.append("")
    lines.append("【現在のリスト】")

    for item in sorted(current_items, key=lambda i: i.title.lower()):
        price_text = _format_price(item.price)
        lines.append(f"- {item.title}{price_text}")

    return "\n".join(lines)


def _format_price(price: Optional[float], include_parens: bool = True) -> str:
    if price is None:
        return " (価格不明)" if include_parens else "価格不明"
    formatted = f"¥{int(price):,}"
    return f" ({formatted})" if include_parens else formatted


def _format_price_delta(old_price: Optional[float], new_price: Optional[float]) -> str:
    if old_price is None or new_price is None:
        return "変動" if new_price != old_price else "変更なし"
    diff_value = new_price - old_price
    sign = "+" if diff_value >= 0 else "-"
    return f"{sign}¥{abs(int(diff_value)):,}"


def _sum_prices(items: Iterable[WishlistItem]) -> Optional[float]:
    total = 0.0
    found = False
    for item in items:
        if item.price is None:
            continue
        total += item.price
        found = True
    return total if found else None


def _notify_slack(webhook_url: str, text: str, session: requests.Session) -> None:
    payload = {"text": text}
    response = session.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code >= 400:
        raise WishlistWatcherError(f"Slack通知に失敗しました: {response.status_code} {response.text}")


def _fetch_all_items(session: requests.Session, list_url: str) -> List[WishlistItem]:
    html = _fetch_with_retry(session, list_url)
    all_items: List[WishlistItem] = []
    seen_ids: set[str] = set()

    page_count = 0
    next_url: Optional[str] = None
    visited_urls: set[str] = set()

    while True:
        page_count += 1
        if page_count > MAX_PAGINATION_PAGES:
            raise WishlistWatcherError("ページネーションの追跡が上限を超えました")

        soup = BeautifulSoup(html, "html.parser")
        page_items = _parse_items_from_soup(soup, list_url)
        new_items = 0
        for item in page_items:
            if item.item_id in seen_ids:
                continue
            seen_ids.add(item.item_id)
            all_items.append(item)
            new_items += 1

        logger.info("page %s: fetched %s items (%s new)", page_count, len(page_items), new_items)

        next_url = _extract_show_more_url(soup, list_url)
        if not next_url:
            break

        if next_url in visited_urls:
            logger.warning("pagination returned previously seen URL; stopping to avoid loop")
            break

        if new_items == 0:
            logger.warning("pagination returned no new items; stopping early")
            break

        visited_urls.add(next_url)
        last_url = next_url
        html = _fetch_with_retry(session, next_url)

    if not all_items:
        raise WishlistWatcherError("ウィッシュリストの解析に失敗しました (項目が見つかりません)")

    return all_items


def _parse_items_from_soup(soup: BeautifulSoup, base_url: str) -> List[WishlistItem]:
    container = _locate_items_container(soup)
    if container is None:
        raise WishlistWatcherError("ウィッシュリストの解析に失敗しました (リストコンテナが見つかりません)")

    item_nodes = list(container.select("[data-itemid]"))

    fallback_nodes = container.select("li")
    for node in fallback_nodes:
        if node.get("data-itemid"):
            continue
        if not node.find("a", href=True):
            continue
        item_nodes.append(node)

    items: List[WishlistItem] = []
    seen_ids: set[str] = set()

    for node in item_nodes:
        item = WishlistItem.from_html(node, base_url)
        if not item:
            continue
        if item.item_id in seen_ids:
            continue
        seen_ids.add(item.item_id)
        items.append(item)

    return items


def _locate_items_container(soup: BeautifulSoup) -> Optional[Tag]:
    container = soup.select_one("#g-items")
    if container is None:
        container = soup.select_one("[data-testid='g-items']")
    return container


if __name__ == "__main__":
    sys.exit(main())
