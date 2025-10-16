import hashlib

import importlib.util
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup


MODULE_PATH = Path(__file__).resolve().parents[1] / "watcher.py"
spec = importlib.util.spec_from_file_location("watcher", MODULE_PATH)
watcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = watcher
spec.loader.exec_module(watcher)


SAMPLE_HTML = """
<html>
  <body>
    <ul id="g-items">
      <li data-itemid="item-1">
        <a class="a-link-normal" href="/dp/B000TEST01/">商品A</a>
        <span class="a-price">
          <span class="a-offscreen">￥1,580</span>
        </span>
      </li>
      <li data-itemid="item-2">
        <a class="a-link-normal" href="/gp/product/B000TEST02/">商品B</a>
        <span class="a-price">
          <span class="a-price-whole">3,980</span>
          <span class="a-price-fraction">50</span>
        </span>
      </li>
      <li>
        <a class="a-link-normal" href="https://example.com/itemC">商品C</a>
      </li>
      <li>
        <a class="a-link-normal" href="/gp/see-more">もっと見る</a>
      </li>
    </ul>
  </body>
</html>
"""


SHOW_MORE_HTML = """
<html>
  <body>
    <div id="g-items"></div>
    <input type="hidden" name="showMoreUrl" value="/hz/wishlist/slv/items?filter=unpurchased&amp;paginationToken=TOKEN123&amp;itemsLayout=LIST&amp;sort=date-added&amp;type=wishlist&amp;lid=20XG7YB46EBUX"/>
  </body>
</html>
"""


NESTED_TITLE_HTML = """
<li data-itemid="nested-1">
  <a class="a-link-normal" href="/dp/B000TEST03/">
    <span class="a-size-base-plus a-color-base"> 商品C </span>
    <span class="a-color-secondary">もっと見る</span>
  </a>
  <a class="a-link-normal" href="/dp/B000TEST03/?show=more">もっと見る</a>
</li>
"""


def test_parse_wishlist_extracts_items():
    items = watcher._parse_wishlist(SAMPLE_HTML, "https://www.amazon.co.jp")
    assert len(items) == 3

    first, second, third = items
    assert first.item_id == "B000TEST01"
    assert first.title == "商品A"
    assert first.price == 1580.0
    assert first.url.startswith("https://www.amazon.co.jp/dp/B000TEST01")

    assert second.item_id == "B000TEST02"
    assert second.price == pytest.approx(3980.5)

    assert third.price is None
    expected_hash = hashlib.sha1(
        f"商品C\nhttps://example.com/itemC".encode("utf-8", errors="ignore")
    ).hexdigest()
    assert third.item_id == expected_hash


def test_diff_detects_add_remove_and_price_changes():
    old_items = [
        watcher.WishlistItem(item_id="A", title="Item A", price=100.0, url="http://example/a"),
        watcher.WishlistItem(item_id="B", title="Item B", price=None, url="http://example/b"),
    ]
    new_items = [
        watcher.WishlistItem(item_id="B", title="Item B", price=120.0, url="http://example/b"),
        watcher.WishlistItem(item_id="C", title="Item C", price=90.0, url="http://example/c"),
    ]

    diff = watcher._diff_items(old_items, new_items)

    assert [item.item_id for item in diff.added] == ["C"]
    assert [item.item_id for item in diff.removed] == ["A"]
    assert [(old.item_id, new.item_id) for old, new in diff.price_changes] == [("B", "B")]


def test_format_diff_message_includes_sections():
    old_items = [
        watcher.WishlistItem(item_id="A", title="Item A", price=100.0, url="http://example/a"),
    ]
    new_items = [
        watcher.WishlistItem(item_id="A", title="Item A", price=90.0, url="http://example/a"),
        watcher.WishlistItem(item_id="B", title="Item B", price=None, url="http://example/b"),
    ]

    diff = watcher._diff_items(old_items, new_items)
    message = watcher._format_diff_message(diff, new_items)

    assert "変化あり" in message
    assert "【追加】" in message
    assert "【価格変更】" in message
    assert "Item B" in message
    assert "Item A" in message


def test_format_no_change_message_lists_current_items():
    items = [
        watcher.WishlistItem(item_id="B", title="Item B", price=None, url="http://example/b"),
        watcher.WishlistItem(item_id="A", title="Item A", price=1234.0, url="http://example/a"),
    ]

    message = watcher._format_no_change_message(items)

    assert "変化なし" in message
    assert "総額" in message
    assert "【現在のリスト】" in message
    # Should be sorted alphabetically and include price formatting / no price markers
    expected_lines = [
        "- Item A (¥1,234)",
        "- Item B (価格不明)",
    ]
    for line in expected_lines:
        assert line in message


def test_extract_show_more_url_from_hidden_input():
    soup = BeautifulSoup(SHOW_MORE_HTML, "html.parser")
    base_url = "https://www.amazon.co.jp/hz/wishlist/ls/20XG7YB46EBUX"
    result = watcher._extract_show_more_url(soup, base_url)
    assert result is not None
    parsed = urlparse(result)
    assert parsed.path == "/hz/wishlist/slv/items"
    query = parse_qs(parsed.query)
    assert query["paginationToken"] == ["TOKEN123"]
    assert query["filter"] == ["unpurchased"]


def test_extract_title_skips_more_link():
    soup = BeautifulSoup(NESTED_TITLE_HTML, "html.parser")
    node = soup.select_one("li")
    title, href = watcher._extract_title_and_link(node)
    assert title == "商品C"
    assert href == "/dp/B000TEST03/"
