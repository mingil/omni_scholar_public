"""
Patches Streamlit 1.34.0 server & static frontend bundle to prevent:
1. 1-second WebSocket ping timeouts behind Cloudflare Tunnel / Reverse Proxies
   (which caused buttons to repeatedly disable/grey out on reconnect loops).
2. Uncaught 'Bad message format: Tried to use SessionInfo before it was initialized'
   when in-flight messages arrive before newSession during WebSocket reconnection.
"""
import glob
import os
import streamlit
import streamlit.web.server.server as st_server


def apply_streamlit_patches() -> None:
    # 1. Patch server.py TORNADO_SETTINGS (websocket_ping_interval: 20s, timeout: 60s)
    srv_path = st_server.__file__
    with open(srv_path, "r", encoding="utf-8") as fp:
        srv_src = fp.read()

    updated_srv = srv_src.replace(
        '"websocket_ping_interval": 1,',
        '"websocket_ping_interval": 20,',
    ).replace(
        '"websocket_ping_timeout": 30,',
        '"websocket_ping_timeout": 60,',
    )
    if updated_srv != srv_src:
        with open(srv_path, "w", encoding="utf-8") as fp:
            fp.write(updated_srv)
        print(f"[patch_streamlit_runtime] Patched TORNADO_SETTINGS in {srv_path}")
    else:
        print(f"[patch_streamlit_runtime] TORNADO_SETTINGS already patched in {srv_path}")

    # 2. Patch static frontend JS bundle so SessionInfo.current falls back gracefully
    st_dir = os.path.dirname(streamlit.__file__)
    js_files = glob.glob(os.path.join(st_dir, "static", "static", "js", "main.*.js"))
    old_snippet = 'get current(){if(!this._current)throw new Error("Tried to use SessionInfo before it was initialized");return this._current}'
    new_snippet = 'get current(){if(!this._current)return this._last||{appId:"",sessionId:"",streamlitVersion:"1.34.0",pythonVersion:"",installationId:"",installationIdV3:"",maxCachedMessageAge:2,commandLine:"",isHello:!1};return this._current}'

    for jpath in js_files:
        with open(jpath, "r", encoding="utf-8", errors="ignore") as fp:
            js_src = fp.read()
        if old_snippet in js_src:
            js_updated = js_src.replace(old_snippet, new_snippet)
            with open(jpath, "w", encoding="utf-8") as fp:
                fp.write(js_updated)
            print(f"[patch_streamlit_runtime] Patched SessionInfo.current guard in {jpath}")
        else:
            print(f"[patch_streamlit_runtime] SessionInfo.current guard already active in {jpath}")


if __name__ == "__main__":
    apply_streamlit_patches()
