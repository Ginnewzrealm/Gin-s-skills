#!/usr/bin/env bash
# Fetch a URL as Markdown via proxy cascade with paywall bypass.
# Self-contained: no external skill dependencies.
#
# Bypass strategies (learned from Bypass Paywalls Clean):
#   1. r.jina.ai / defuddle.md — proxy services
#   2. Site-specific bot UA (Googlebot/Bingbot) via SEO whitelist
#   3. Referer spoofing (Google/Facebook/Twitter)
#   4. Cookie clearing + social referer
#   5. AMP page redirect
#   6. JSON-LD article extraction from raw HTML
#   7. archive.today (with browser fallback for CAPTCHA)
#   8. agent-fetch
#
# Usage: fetch_url.sh <url> [proxy_url]
set -uo pipefail

URL="${1:?Usage: fetch_url.sh <url> [proxy_url]}"
PROXY="${2:-}"

# Auto-load proxy from config if not provided
if [ -z "$PROXY" ]; then
  PROXY_CONFIG="$(dirname "$0")/../proxy.config"
  if [ -f "$PROXY_CONFIG" ]; then
    PROXY=$(grep -v '^#' "$PROXY_CONFIG" | grep -v '^[[:space:]]*$' | head -1 | sed 's/[[:space:]]*#.*$//' | tr -d '\n')
  fi
fi

# ── Paywall domain lists ───────────────────────────────────────────────

# Sites where Googlebot UA gets full content (SEO whitelist)
GOOGLEBOT_DOMAINS="wsj.com|barrons.com|ft.com|economist.com|theaustralian.com.au|thetimes.co.uk|telegraph.co.uk|zeit.de|handelsblatt.com|leparisien.fr|nzz.ch|usatoday.com|quora.com|lefigaro.fr|lemonde.fr|spiegel.de|sueddeutsche.de|frankfurter-allgemeine.de|wires.com|brisbanetimes.com.au|smh.com.au|theage.com.au"

# Sites where Bingbot UA works
BINGBOT_DOMAINS="haaretz.com|nzherald.co.nz|stratfor.com|themarker.com"

# Sites that allow social referral traffic
FACEBOOK_REF_DOMAINS="law.com|ftm.nl|law360.com|sloanreview.mit.edu"

# Sites with usable AMP versions
AMP_DOMAINS="wsj.com|bostonglobe.com|latimes.com|chicagotribune.com|seattletimes.com|theatlantic.com|wired.com|newyorker.com|washingtonpost.com|smh.com.au|theage.com.au|brisbanetimes.com.au"

# All known paywall domains (for generic bypass attempts)
PAYWALL_DOMAINS="nytimes.com|wsj.com|ft.com|economist.com|bloomberg.com|washingtonpost.com|newyorker.com|wired.com|theatlantic.com|medium.com|businessinsider.com|technologyreview.com|scmp.com|seattletimes.com|bostonglobe.com|latimes.com|chicagotribune.com|theglobeandmail.com|afr.com|thetimes.co.uk|telegraph.co.uk|spiegel.de|zeit.de|sueddeutsche.de|barrons.com|forbes.com|foreignaffairs.com|foreignpolicy.com|harvard.edu|newscientist.com|scientificamerican.com|theinformation.com|statista.com|handelsblatt.com|nzz.ch|leparisien.fr|lefigaro.fr|lemonde.fr|haaretz.com|nzherald.co.nz|theaustralian.com.au|smh.com.au|theage.com.au|quora.com|usatoday.com"

# ── Helper functions ─────────────────────────────────────────────────

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

_is_paywall_content() {
  local content="$1"
  echo "$content" | grep -qiE '(subscribe to (continue|read|access|unlock)|paywall|premium[._]content|metered[._]paywall|article[._]limit|sign[._]in[._]to[._](continue|read)|create[._]a[._]free[._]account[._]to[._]unlock|membership[._]to[._]continue|subscribe now for full access|to continue reading|remaining free articles|has been removed|subscribe or|already a subscriber)' && return 0
  return 1
}

_is_captcha_page() {
  local content="$1"
  echo "$content" | grep -qiE '(security check|captcha|recaptcha|hcaptcha|please complete|cloudflare.*challenge|verify you are human)' && return 0
  return 1
}

# Extract article body from JSON-LD in HTML
_extract_jsonld_article() {
  local html="$1"
  echo "$html" | grep -o '"articleBody":"[^"]*"' | head -1 | sed 's/^"articleBody":"//;s/"$//' | sed 's/\\n/\n/g; s/\\"/"/g; s/\\\\/\\/g'
}

# Convert raw HTML to plain text
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

# Print result and exit if content is valid (not paywalled)
_try_output() {
  local content="$1"
  if _has_content "$content"; then
    if ! _is_paywall_content "$content"; then
      echo "$content"
      exit 0
    fi
  fi
}

# Fetch with curl, try JSON-LD extraction first, fall back to HTML-to-text.
# Args: extra_curl_opts...
_fetch_and_try() {
  local extra_curl_opts=("$@")
  OUT=$(_curl --max-time 15 "${extra_curl_opts[@]}" "$URL" 2>/dev/null || true)
  ARTICLE=$(_extract_jsonld_article "$OUT")
  if [ -n "$ARTICLE" ] && [ ${#ARTICLE} -gt 200 ]; then
    TITLE=$(echo "$OUT" | grep -o '<title[^>]*>[^<]*</title>' | sed 's/<[^>]*>//g' | head -1)
    echo "# ${TITLE:-Article}"
    echo ""
    echo "Source: $URL"
    echo ""
    echo "$ARTICLE"
    exit 0
  fi
  TEXT=$(_html_to_text "$OUT")
  _try_output "$TEXT"
}

# ── Level 1: Proxy services ─────────────────────────────────────────

OUT=$(_curl --max-time 20 "https://r.jina.ai/$URL" 2>/dev/null || true)
_try_output "$OUT"

OUT=$(_curl --max-time 20 "https://defuddle.md/$URL" 2>/dev/null || true)
_try_output "$OUT"

# ── Level 2: Site-specific bot UA bypass ─────────────────────────────

if _domain_matches "$URL" "$GOOGLEBOT_DOMAINS"; then
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" \
    -H "Referer: https://www.google.com/" \
    -H "Accept: text/html,application/xhtml+xml" \
    -b ""
fi

if _domain_matches "$URL" "$BINGBOT_DOMAINS"; then
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)" \
    -H "Referer: https://www.bing.com/" \
    -H "Accept: text/html,application/xhtml+xml" \
    -b ""
fi

# ── Level 3: Generic paywall bypass ─────────────────────────────────

if _domain_matches "$URL" "$PAYWALL_DOMAINS"; then

  # 3a. Googlebot UA
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" \
    -H "Referer: https://www.google.com/" \
    -H "Accept: text/html,application/xhtml+xml" \
    -b ""

  # 3b. Bingbot UA
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)" \
    -H "Referer: https://www.bing.com/" \
    -H "Accept: text/html,application/xhtml+xml" \
    -b ""

  # 3c. Facebook Referer (social traffic)
  if _domain_matches "$URL" "$FACEBOOK_REF_DOMAINS"; then
    _fetch_and_try \
      -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36" \
      -H "Referer: https://www.facebook.com/" \
      -b ""
  fi

  # 3d. Twitter Referer
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36" \
    -H "Referer: https://t.co/" \
    -b ""

  # 3e. AMP pages (weaker paywall on AMP versions)
  if _domain_matches "$URL" "$AMP_DOMAINS"; then
    for AMP_SUFFIX in "/amp" "?outputType=amp" ".amp.html" "?amp"; do
      [[ "$URL" == *"$AMP_SUFFIX" ]] && continue
      AMP_URL="${URL}${AMP_SUFFIX}"
      _fetch_and_try "$AMP_URL"
    done
    # Also try .html/amp pattern (e.g., wsj.com → wsj.com.amp.html)
    AMP_URL=$(echo "$URL" | sed 's|\.html$|\.amp.html|' | sed 's|/$|/amp|')
    if [ "$AMP_URL" != "$URL" ]; then
      _fetch_and_try "$AMP_URL"
    fi
  fi

  # 3f. EU-region IP hint (geographic pricing/routing差异)
  _fetch_and_try \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36" \
    -H "X-Forwarded-For: 185.199.108.1" \
    -H "Referer: https://www.google.com/" \
    -b ""
fi

# ── Level 4: archive.today ───────────────────────────────────────────

ARCHIVE_URL="https://archive.today/newest/$URL"
ARCHIVE_OUT=$(_curl -sL "$ARCHIVE_URL" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  --max-time 20 2>/dev/null || true)

if _has_content "$ARCHIVE_OUT"; then
  if ! _is_captcha_page "$ARCHIVE_OUT"; then
    TEXT=$(_html_to_text "$ARCHIVE_OUT")
    if _has_content "$TEXT"; then
      echo "$TEXT"
      exit 0
    fi
  fi
fi

echo "ARCHIVE_CAPTCHA:$ARCHIVE_URL" >&2
echo "⚠️  archive.ph needs human verification, trying next fallback..." >&2

# ── Level 5: Google cache ────────────────────────────────────────────

CACHE_URL="https://webcache.googleusercontent.com/search?q=cache:$URL"
OUT=$(_curl --max-time 15 "$CACHE_URL" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  2>/dev/null || true)

if _has_content "$OUT"; then
  TEXT=$(_html_to_text "$OUT")
  if _has_content "$TEXT"; then
    echo "$TEXT"
    exit 0
  fi
fi

# ── Level 6: agent-fetch (last resort) ───────────────────────────────

if command -v npx &>/dev/null; then
  OUT=$(npx --yes agent-fetch "$URL" --json 2>/dev/null || true)
  if [ -n "$OUT" ]; then
    echo "$OUT"
    exit 0
  fi
fi

echo "ERROR: All fetch methods failed for: $URL" >&2
echo "TIP: Try opening https://archive.today/newest/$URL in your browser manually" >&2
exit 1
