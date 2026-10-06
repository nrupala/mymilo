# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""PWA entry points: manifest, service worker, and installability hooks."""


def test_manifest_served_with_correct_type(client):
    r = client.get("/manifest.json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    body = r.json()
    assert body["name"] == "MyMilo"
    assert body["short_name"] == "MyMilo"
    assert body["display"] == "standalone"
    assert body["start_url"] == "/"
    sizes = {i["sizes"] for i in body["icons"]}
    assert "192x192" in sizes and "512x512" in sizes


def test_manifest_icons_exist(client):
    r = client.get("/manifest.json")
    for icon in r.json()["icons"]:
        ir = client.get(icon["src"])
        assert ir.status_code == 200, icon["src"]
        assert ir.headers["content-type"].startswith("image/png")


def test_service_worker_served_from_root_scope(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert r.headers["Service-Worker-Allowed"] == "/"
    assert "mymilo-shell" in r.text
    # Navigations must be network-first so the Cloudflare Access login
    # handshake (redirects + session cookies) is never swallowed by the cache.
    assert "mode === 'navigate'" in r.text
    assert "cloudflareaccess.com" in r.text


def test_base_template_links_pwa(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'rel="manifest" href="/manifest.json"' in html
    assert 'name="theme-color"' in html
    assert "serviceWorker" in html


def test_access_login_detected_plainly(client):
    # Cloudflare Access login HTML on an API call must surface as a clear
    # sign-in message, never a JSON parse error.
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "cloudflareaccess.com" in html
    assert "Sign-in required" in html
    # A backend hiccup (HTML error page, not the login page) must not be
    # mislabeled as a sign-in problem.
    assert "Server hiccup" in html


def test_signout_and_voice_ui_present(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'href="/cdn-cgi/access/logout"' in html  # sign out via Access
    assert 'id="mic"' in html  # voice dictation button
    assert "webkitSpeechRecognition" in html
