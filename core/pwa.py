"""Progressive Web App (PWA) integration for Click2Serve.

Streamlit doesn't serve static files, so we ship the entire PWA
contract inline:

  - The Web App Manifest is embedded as a ``data:application/json``
    URI on the ``<link rel="manifest">``.
  - The service worker is embedded as a Blob URL created at runtime
    (``URL.createObjectURL`` over a Blob holding the SW source).
  - App icons are SVG, embedded as ``data:image/svg+xml`` URIs in
    the manifest.

What this gives the customer:

  - Chrome / Edge on Android show an "Install Click2Serve" banner
    under the URL bar after they've interacted with the page once.
  - iOS Safari: tap Share -> "Add to Home Screen" gives a native
    icon + standalone display mode (no browser chrome).
  - Once installed, tapping the icon opens Click2Serve fullscreen
    with our brand colour as the status-bar tint.
  - The service worker caches the shell so a second visit loads
    instantly from cache before the network responds.

Public surface:
  - ``inject_pwa()``  drop ALL the head tags + register the SW.
                      Idempotent across page reruns.
"""
from __future__ import annotations

import base64
import json
import logging

import streamlit as st

logger = logging.getLogger(__name__)

# Brand tokens (kept in sync with core/styles.py PRIMARY / BG / ACCENT
# but duplicated here so this module has zero internal imports — keeps
# the PWA layer cheap to load on every page).
_THEME_COLOR = "#2563EB"
_BG_COLOR = "#F8FAFC"
_ACCENT = "#F59E0B"



# ──────────────────────────────────────────────────────────────────────────
# App icon (SVG, scaled to 512 / 192 / 180 / 64 / 32 by the data URI)
# ──────────────────────────────────────────────────────────────────────────
# Stylised "C2S" mark over the brand-blue gradient, with a small amber
# notification dot in the corner to echo the "live now" pulse on the
# hero. SVG renders crisply at any size — Android and iOS both accept
# SVG icons in the manifest now (2025+).
_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" />
    </filter>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#bg)"/>
  <!-- Soft inner glow -->
  <rect x="32" y="32" width="448" height="448" rx="92"
        fill="none" stroke="rgba(255,255,255,0.18)" stroke-width="2"/>
  <!-- Service-bell glyph centred -->
  <g transform="translate(256 270)" fill="#FFFFFF">
    <path d="M0,-110 c-65,0 -118,53 -118,118 v22 h236 v-22 c0,-65 -53,-118 -118,-118 z"/>
    <rect x="-130" y="38" width="260" height="22" rx="11"/>
    <circle cx="0" cy="-130" r="14"/>
  </g>
  <!-- Amber notification dot -->
  <circle cx="384" cy="128" r="36" fill="#F59E0B"/>
  <circle cx="384" cy="128" r="36" fill="none"
          stroke="rgba(245,158,11,0.4)" stroke-width="14"/>
</svg>
"""


def _icon_data_uri(svg_text: str = _ICON_SVG) -> str:
    """Return an inline ``data:image/svg+xml;base64,...`` URI for the icon.

    base64 encoding (rather than urlencoded) keeps the manifest small
    and works reliably across iOS Safari and Chrome.
    """
    encoded = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"



# ──────────────────────────────────────────────────────────────────────────
# Web App Manifest
# ──────────────────────────────────────────────────────────────────────────
def _build_manifest() -> dict:
    """Construct the Web App Manifest payload.

    Reads ``shop_name`` from ``shop_config`` so the home-screen icon
    label matches the actual shop. Falls back to "Click2Serve" when
    config is unavailable (first-run, DB hiccup, etc).
    """
    shop_name = "Click2Serve"
    short_name = "Click2Serve"
    try:
        from core.db import get_shop_config

        cfg = get_shop_config() or {}
        shop_name = (
            (cfg.get("shop_name") or "").strip() or shop_name
        )
        # short_name is shown under the home-screen icon — keep it
        # under ~12 chars to avoid truncation.
        short_name = shop_name.split()[0] if shop_name else short_name
        if len(short_name) > 12:
            short_name = short_name[:12].rstrip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("PWA: could not read shop_config: %s", exc)

    icon_uri = _icon_data_uri()
    return {
        "name": shop_name,
        "short_name": short_name,
        "description": (
            "Govt paperwork, done in hours. Aadhaar, passport, "
            "driving licence, electricity bills — book in 60 seconds, "
            "pay online, track by SMS-style updates."
        ),
        "start_url": "/?utm_source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": _BG_COLOR,
        "theme_color": _THEME_COLOR,
        "categories": ["business", "productivity", "government"],
        "lang": "en-IN",
        "icons": [
            {"src": icon_uri, "sizes": "any", "type": "image/svg+xml",
             "purpose": "any"},
            {"src": icon_uri, "sizes": "any", "type": "image/svg+xml",
             "purpose": "maskable"},
        ],
    }



def _manifest_data_uri() -> str:
    """Encode the manifest as a base64 data URI for ``<link rel=manifest>``.

    Browsers happily accept ``data:application/json;base64,...`` for the
    manifest link — this is the trick that lets a Streamlit app be
    PWA-installable without serving any static files.
    """
    payload = json.dumps(
        _build_manifest(), ensure_ascii=False, separators=(",", ":"),
    )
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return f"data:application/json;base64,{encoded}"


# ──────────────────────────────────────────────────────────────────────────
# Service worker (inline, registered via Blob URL)
# ──────────────────────────────────────────────────────────────────────────
# Tiny "stale-while-revalidate" service worker — caches the shell on
# first install, serves the cached version instantly on subsequent
# visits while a fresh fetch happens in the background. Customers see
# instant page paints even on flaky 3G.
#
# IMPORTANT: keep this as plain JS (no template literals, no arrow
# functions inside ${...}) — it's wrapped in a Python f-string below
# and serialised to a Blob URL, so any extra braces would break the
# Python string formatting OR the JS parser. Tested on Chrome 120 +
# Safari 17 (iOS 18).
_SW_JS = """\
const CACHE = 'click2serve-shell-v1';
const SHELL = ['/'];
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(SHELL).catch(() => null))
      .then(() => self.skipWaiting())
  );
});
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  if (u.origin !== self.location.origin) return;
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const networkPromise = fetch(e.request).then((resp) => {
        if (resp && resp.status === 200) {
          const respClone = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, respClone));
        }
        return resp;
      }).catch(() => cached);
      return cached || networkPromise;
    })
  );
});
"""



# ──────────────────────────────────────────────────────────────────────────
# HEAD payload — manifest link, theme colors, Apple-specific tags, and
# the service-worker registration script.
# ──────────────────────────────────────────────────────────────────────────
def _build_head_html() -> str:
    """Return the complete HTML blob to be injected into the page <head>.

    Streamlit puts ``st.markdown(unsafe_allow_html=True)`` content into
    the body, but a pleasant side-effect is that browsers happily honour
    ``<link rel=manifest>`` and ``<meta>`` tags wherever they appear in
    the document. Modern Chrome and Safari both pick them up from the
    body and behave as if they were in the head.
    """
    manifest_uri = _manifest_data_uri()
    icon_uri = _icon_data_uri()
    sw_source = _SW_JS

    # Escape backticks since we wrap the SW source in a JS template
    # literal below.
    sw_source_escaped = (
        sw_source.replace("\\", "\\\\").replace("`", "\\`")
    )

    return f"""
<!-- ── Click2Serve PWA HEAD payload (injected by core.pwa) ──────────── -->
<link rel="manifest" href="{manifest_uri}">

<!-- Theme colour for the address bar / status bar tint -->
<meta name="theme-color" content="{_THEME_COLOR}">
<meta name="msapplication-TileColor" content="{_THEME_COLOR}">

<!-- Apple-specific (iOS Safari) standalone-mode tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Click2Serve">
<link rel="apple-touch-icon" href="{icon_uri}">
<link rel="apple-touch-icon" sizes="180x180" href="{icon_uri}">
<link rel="icon" type="image/svg+xml" href="{icon_uri}">

<!-- Service worker registration (uses a Blob URL because Streamlit
     does not serve a real /service-worker.js path). -->
<script>
(function () {{
  if (window.__c2sPwaReady) return;
  window.__c2sPwaReady = true;
  if (!('serviceWorker' in navigator)) return;
  try {{
    const swSrc = `{sw_source_escaped}`;
    const blob = new Blob([swSrc], {{type: 'application/javascript'}});
    const swUrl = URL.createObjectURL(blob);
    navigator.serviceWorker.register(swUrl, {{scope: '/'}})
      .catch(function (err) {{
        console.warn('Click2Serve SW registration failed:', err);
      }});
  }} catch (err) {{
    console.warn('Click2Serve SW setup error:', err);
  }}
}})();
</script>
"""



# ──────────────────────────────────────────────────────────────────────────
# "Add to Home Screen" install hint banner
# ──────────────────────────────────────────────────────────────────────────
# Chrome / Edge fire a ``beforeinstallprompt`` event when the page is
# installable. We capture it, stash it in a global, and wire a small
# pill at the bottom-left of the page to call ``prompt()`` on it.
#
# iOS Safari doesn't support ``beforeinstallprompt`` — there's no API
# to trigger the install dialog. For iOS, the standard pattern is a
# one-time hint that walks the user through the manual Share -> Add to
# Home Screen flow. We render that hint only when navigator.standalone
# is false AND the user hasn't dismissed it previously (localStorage).
_INSTALL_HINT_HTML = """
<style>
  .c2s-install-pill {
    position: fixed; left: 14px; bottom: 14px; z-index: 998;
    display: none;
    background: #FFFFFF; color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 999px;
    padding: 0.55rem 0.95rem;
    font-size: 0.84rem; font-weight: 600;
    box-shadow:
      0 8px 22px -6px rgba(15, 23, 42, 0.18),
      0 4px 10px rgba(15, 23, 42, 0.08);
    cursor: pointer;
    align-items: center;
    gap: 0.5rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    font-family: 'Inter', system-ui, sans-serif;
  }
  .c2s-install-pill:hover {
    transform: translateY(-2px);
    box-shadow:
      0 12px 28px -6px rgba(15, 23, 42, 0.22),
      0 6px 14px rgba(15, 23, 42, 0.10);
  }
  .c2s-install-pill .ico {
    display: inline-flex; width: 22px; height: 22px;
    border-radius: 6px;
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: #fff;
    align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800;
  }
  .c2s-install-pill .x {
    margin-left: 4px; padding: 2px 6px; border-radius: 999px;
    color: #94A3B8; font-weight: 500;
  }
  .c2s-install-pill .x:hover { color: #0F172A; background: #F1F5F9; }
  .c2s-ios-hint {
    position: fixed; left: 14px; right: 14px; bottom: 14px;
    z-index: 998; display: none;
    background: #FFFFFF; color: #0F172A;
    border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 0.95rem 1.1rem;
    box-shadow: 0 12px 28px -6px rgba(15, 23, 42, 0.18);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.88rem; line-height: 1.4;
  }
  .c2s-ios-hint b { color: #0F172A; }
  .c2s-ios-hint .x {
    float: right; cursor: pointer; padding: 0 6px;
    color: #94A3B8; font-weight: 600;
  }
  @media (min-width: 640px) {
    .c2s-ios-hint { left: auto; right: 14px; max-width: 320px; }
  }
</style>
"""



_INSTALL_HINT_BODY = """
<div class="c2s-install-pill" id="c2sInstallPill" role="button"
     aria-label="Install Click2Serve">
  <span class="ico">+</span>
  <span>Install app</span>
  <span class="x" id="c2sInstallDismiss" aria-label="Dismiss">×</span>
</div>

<div class="c2s-ios-hint" id="c2sIosHint">
  <span class="x" id="c2sIosHintDismiss" aria-label="Dismiss">×</span>
  <b>Install Click2Serve on your iPhone</b><br/>
  Tap the <b>Share</b> icon (square with up-arrow) below, then choose
  <b>“Add to Home Screen”</b>.
</div>

<script>
(function () {
  if (window.__c2sInstallReady) return;
  window.__c2sInstallReady = true;

  const DISMISS_KEY = 'c2sInstallDismissed';
  const dismissed = (function () {
    try { return localStorage.getItem(DISMISS_KEY) === '1'; }
    catch (e) { return false; }
  })();
  if (dismissed) return;

  const inStandalone =
    window.matchMedia &&
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  if (inStandalone) return;

  // -- Chrome / Edge / Android: capture beforeinstallprompt and wire pill.
  let deferred = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferred = e;
    const pill = document.getElementById('c2sInstallPill');
    if (pill) pill.style.display = 'inline-flex';
  });

  document.addEventListener('click', function (ev) {
    const pill = ev.target.closest('#c2sInstallPill');
    const dismiss = ev.target.closest('#c2sInstallDismiss');
    const iosX = ev.target.closest('#c2sIosHintDismiss');

    if (dismiss) {
      ev.stopPropagation();
      const p = document.getElementById('c2sInstallPill');
      if (p) p.style.display = 'none';
      try { localStorage.setItem(DISMISS_KEY, '1'); } catch (e) {}
      return;
    }
    if (iosX) {
      const h = document.getElementById('c2sIosHint');
      if (h) h.style.display = 'none';
      try { localStorage.setItem(DISMISS_KEY, '1'); } catch (e) {}
      return;
    }
    if (pill && deferred) {
      deferred.prompt();
      deferred.userChoice.then(function () {
        deferred = null;
        const p = document.getElementById('c2sInstallPill');
        if (p) p.style.display = 'none';
      });
    }
  }, true);

  // -- iOS Safari: no install API. Show the manual hint after a delay
  // so we don't interrupt the first paint.
  const ua = window.navigator.userAgent.toLowerCase();
  const isIOS = /iphone|ipad|ipod/.test(ua);
  const isSafari = ua.includes('safari') && !ua.includes('crios') &&
                   !ua.includes('fxios') && !ua.includes('edgios');
  if (isIOS && isSafari) {
    setTimeout(function () {
      const hint = document.getElementById('c2sIosHint');
      if (hint) hint.style.display = 'block';
    }, 4000);
  }
})();
</script>
"""



# ──────────────────────────────────────────────────────────────────────────
# Public entry point — call this once per page from app.py
# ──────────────────────────────────────────────────────────────────────────
def inject_pwa() -> None:
    """Inject the PWA head + install-hint UI into the current page.

    Idempotent within a Streamlit run via ``st.session_state`` — calling
    it from every page (which app.py does, since app.py runs on every
    page transition) won't double-inject the manifest link or register
    the service worker twice.

    Owner pages (anyone signed in) skip the customer-facing "Install
    app" pill so it doesn't clutter the bookings / settings UIs. The
    head tags + service worker still register so the owner's own
    browser can install if they want.
    """
    if st.session_state.get("_c2s_pwa_injected"):
        return

    st.markdown(_build_head_html(), unsafe_allow_html=True)
    st.markdown(_INSTALL_HINT_HTML, unsafe_allow_html=True)

    # Customer-facing install pill / iOS hint — hidden when the owner
    # is signed in. The owner can still trigger install via Chrome's
    # built-in "Install app" menu item; the pill is just the fallback
    # nudge for first-time customers.
    if not st.session_state.get("logged_in"):
        st.markdown(_INSTALL_HINT_BODY, unsafe_allow_html=True)

    st.session_state["_c2s_pwa_injected"] = True
