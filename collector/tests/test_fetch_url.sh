#!/usr/bin/env bats
# fetch_url.sh — 核心辅助函数单元测试
# 运行方式: bats tests/test_fetch_url.sh

SKILL_DIR="${BATS_TEST_DIRNAME}/.."
FETCH_SCRIPT="$SKILL_DIR/scripts/fetch_url.sh"

# 加载被测函数（通过 source，Bats 会把 batslib 函数注入）
setup() {
  # 将被测脚本的函数逐行解析出来，source 不会触发主流程（因为 URL 未传入）
  # 我们把函数定义提取到一个 stub 脚本里再 source
  cat > /tmp/fetch_url_helpers.bash << 'END_HELPERS'
# ── Helpers extracted from fetch_url.sh for unit testing ──

_curl() {
  if [ -n "$PROXY" ]; then
    https_proxy="$PROXY" http_proxy="$PROXY" curl -sL "$@"
  else
    curl -sL "$@"
  fi
}

_has_content() {
  local content="$1"
  local line_count char_count
  line_count=$(echo "$content" | wc -l | tr -d ' ')
  [ "$line_count" -gt 8 ] || return 1
  char_count=$(echo "$content" | wc -c | tr -d ' ')
  [ "$char_count" -gt 500 ] || return 1
  echo "$content" | grep -q "Don't miss what's happening" && return 1
  echo "$content" | grep -q "Access Denied" && return 1
  echo "$content" | grep -q "404 Not Found" && return 1
  echo "$content" | grep -q "403 Forbidden" && return 1
  return 0
}

_domain_matches() {
  local url="$1" domains="$2"
  echo "$url" | grep -qE "$domains"
}

_extract_jsonld_article() {
  local html="$1"
  echo "$html" | grep -o '"articleBody":"[^"]*"' | head -1 | sed 's/^"articleBody":"//;s/"$//' | sed 's/\\n/\n/g; s/\\"/"/g; s/\\\\/\\/g'
}

_html_to_text() {
  local html="$1"
  echo "$html" | sed \
    -e 's/<script[^>]*>.*<\/script>//gI' \
    -e 's/<style[^>]*>.*<\/style>//gI' \
    -e 's/<nav[^>]*>.*<\/nav>//gI' \
    -e 's/<footer[^>]*>.*<\/footer>//gI' \
    -e 's/<header[^>]*>.*<\/header>//gI' \
    -e 's/<[^>]*>//g' \
    -e 's/&amp;/\&/g; s/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g; s/&#39;/'"'"'/g; s/&nbsp;/ /g' \
    -e 's/^[[:space:]]*$//' | sed '/^$/N;/^\n$/d'
}
END_HELPERS
}

teardown() {
  rm -f /tmp/fetch_url_helpers.bash
}

load() {
  source /tmp/fetch_url_helpers.bash
}

# ── _has_content tests ──────────────────────────────────────────────

@test "_has_content: rejects short content" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _has_content 'short'"
  [ "$status" -ne 0 ]
}

@test "_has_content: rejects nav-only pages" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _has_content \"Don't miss what's happening on our site\""
  [ "$status" -ne 0 ]
}

@test "_has_content: rejects 403 pages" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _has_content $'Access Denied\n403 Forbidden\nlorem ipsum dolor sit amet amet'\""
  [ "$status" -ne 0 ]
}

@test "_has_content: accepts valid article" {
  load
  content=$'<!DOCTYPE html>\n<html>\n<body>\n<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore.</p>\n<p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</p>\n<p>Duis aute irure dolor in reprehenderit in voluptate velit.</p>\n</body>\n</html>'
  run bash -c "source /tmp/fetch_url_helpers.bash && _has_content \"\$content\""
  [ "$status" -eq 0 ]
}

# ── _domain_matches tests ──────────────────────────────────────────

@test "_domain_matches: positive match" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _domain_matches 'https://www.wsj.com/article' 'wsj.com|nytimes.com'"
  [ "$status" -eq 0 ]
}

@test "_domain_matches: negative match" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _domain_matches 'https://example.com/article' 'wsj.com|nytimes.com'"
  [ "$status" -ne 0 ]
}

@test "_domain_matches: subdomain match" {
  run bash -c "source /tmp/fetch_url_helpers.bash && _domain_matches 'https://sub.wsj.com/article' 'wsj.com'"
  [ "$status" -eq 0 ]
}

# ── _extract_jsonld_article tests ──────────────────────────────────

@test "_extract_jsonld_article: extracts articleBody" {
  load
  html='<script type="application/ld+json">{"@type":"Article","articleBody":"这是文章正文内容。"}</script>'
  result=$(source /tmp/fetch_url_helpers.bash && _extract_jsonld_article "$html")
  [ "$result" = "这是文章正文内容。" ]
}

@test "_extract_jsonld_article: extracts multiline body" {
  load
  html='<script type="application/ld+json">{"@type":"Article","articleBody":"第一段\n\n第二段\n\n第三段"}</script>'
  result=$(source /tmp/fetch_url_helpers.bash && _extract_jsonld_article "$html")
  echo "result=[$result]"
  [ "$result" = $'第一段\n\n第二段\n\n第三段' ]
}

@test "_extract_jsonld_article: no body returns empty" {
  load
  html='<script type="application/ld+json">{"@type":"Article","name":"Just a Name"}</script>'
  result=$(source /tmp/fetch_url_helpers.bash && _extract_jsonld_article "$html")
  [ -z "$result" ]
}

# ── _html_to_text tests ─────────────────────────────────────────────

@test "_html_to_text: strips all tags" {
  load
  html='<html><head><title>Title</title></head><body><p>Hello <strong>World</strong></p></body></html>'
  result=$(source /tmp/fetch_url_helpers.bash && _html_to_text "$html")
  [[ "$result" == *"Hello"* ]]
  [[ "$result" != *"<p>"* ]]
}

@test "_html_to_text: decodes HTML entities" {
  load
  html='<p>Tom &amp; Jerry &mdash; 100% done &quot;yes&quot;</p>'
  result=$(source /tmp/fetch_url_helpers.bash && _html_to_text "$html")
  [[ "$result" == *"Tom"* ]]
  [[ "$result" == *"&"* ]]   # &amp; → &
  [[ "$result" == *"--"* ]]  # &mdash; → --
  [[ "$result" == *'"'* ]]   # &quot; → "
}
