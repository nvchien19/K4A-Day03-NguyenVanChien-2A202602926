"""
🌐 WEB UI DEMO — REACT AGENT FACILITIES (DAY 03 LAB)
Web server thuần Python (không cần cài thêm thư viện) phục vụ giao diện chat demo.
Chạy:  python src/webui.py            (mở http://127.0.0.1:8000)
Tùy chọn: python src/webui.py --port 8080 --host 0.0.0.0
"""

import json
import os
import sys
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import run_react_agent, MCPFacilitiesServer
from providers import get_llm_provider, MockOfflineProvider, GeminiProvider, OpenAIProvider

MCP_SERVER = MCPFacilitiesServer()

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Facilities AI — ReAct Agent Demo</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Segoe UI", Roboto, Arial, sans-serif; background: #0f172a; color: #e2e8f0; }
  .app { max-width: 860px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; }
  header { padding: 12px 18px; background: #0b1220; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
  .title { font-weight: 700; font-size: 16px; }
  .sub { font-size: 12px; color: #94a3b8; margin-top: 2px; }
  select { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; padding: 6px 8px; font-size: 13px; }
  .chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
  .row { display: flex; }
  .row.user { justify-content: flex-end; }
  .row.assistant { justify-content: flex-start; }
  .bubble { max-width: 78%; padding: 10px 14px; border-radius: 14px; line-height: 1.55; font-size: 14px; white-space: pre-wrap; word-break: break-word; }
  .row.user .bubble { background: #2563eb; color: #fff; border-bottom-right-radius: 4px; }
  .row.assistant .bubble { background: #1e293b; border: 1px solid #334155; border-bottom-left-radius: 4px; }
  .typing { color: #94a3b8; font-style: italic; font-size: 13px; }
  details.trace { margin-top: 8px; background: #0b1220; border: 1px solid #334155; border-radius: 8px; padding: 8px 10px; }
  summary { cursor: pointer; font-size: 12px; color: #7dd3fc; user-select: none; }
  .step { padding: 6px 2px; border-bottom: 1px dashed #1e293b; font-size: 13px; }
  .step:last-child { border-bottom: none; }
  .tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 10px; margin-right: 6px; }
  .tag.thought { background: #f59e0b22; color: #fbbf24; }
  .tag.action { background: #10b98122; color: #34d399; }
  .tag.obs { background: #8b5cf622; color: #a78bfa; }
  .tag.answer { background: #3b82f622; color: #60a5fa; }
  pre { margin: 4px 0 0 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, monospace; font-size: 11px; color: #cbd5e1; background: #111827; padding: 6px; border-radius: 6px; }
  .inputbar { display: flex; gap: 10px; padding: 12px 18px; background: #0b1220; border-top: 1px solid #1e293b; }
  textarea { flex: 1; resize: none; background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 10px; padding: 10px 12px; font-size: 14px; font-family: inherit; max-height: 120px; }
  button { background: #2563eb; color: #fff; border: none; border-radius: 10px; padding: 10px 22px; font-size: 14px; cursor: pointer; }
  button:hover { background: #1d4ed8; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .meta { font-size: 11px; color: #94a3b8; margin-top: 6px; }
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <div class="title">🏢 Facilities AI — ReAct Agent Demo</div>
      <div class="sub">Tra cứu &amp; đặt phòng họp thiết bị (Thought → Action → Observation)</div>
    </div>
    <select id="provider">
      <option value="openai">OpenAI (GPT-4o-mini)</option>
      <option value="gemini">Gemini</option>
      <option value="mock">Mock (Offline, miễn phí)</option>
    </select>
  </header>
  <div class="chat" id="chat"></div>
  <div class="inputbar">
    <textarea id="inp" rows="1" placeholder='VD: "Kiểm tra phòng họp còn trống ngày 22/09/2026 khung giờ 09:00-11:00" — Enter để gửi'></textarea>
    <button id="send">Gửi</button>
  </div>
</div>
<script>
var chat = document.getElementById('chat');
var inp = document.getElementById('inp');
var sendBtn = document.getElementById('send');
var providerSel = document.getElementById('provider');

function addRow(role, html) {
  var row = document.createElement('div');
  row.className = 'row ' + role;
  var b = document.createElement('div');
  b.className = 'bubble';
  b.innerHTML = html;
  row.appendChild(b);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderTrace(trace) {
  var parts = [];
  for (var i = 0; i < trace.length; i++) {
    var t = trace[i];
    if (t.action_type === 'TOOL_EXECUTION') {
      parts.push('<div class="step"><span class="tag action">ACTION</span> ' + esc(t.tool_name) + '(' + esc(JSON.stringify(t.arguments)) + ')</div>');
      parts.push('<div class="step"><span class="tag obs">OBSERVATION</span><pre>' + esc(JSON.stringify(t.observation)) + '</pre></div>');
    } else if (t.action_type === 'FINAL_ANSWER') {
      parts.push('<div class="step"><span class="tag answer">FINAL ANSWER</span><pre>' + esc(t.output) + '</pre></div>');
    }
  }
  return '<details class="trace"><summary>🔎 Xem chuỗi ReAct (' + trace.length + ' bước)</summary>' + parts.join('') + '</details>';
}

var currentXhr = null;

function send() {
  var msg = inp.value.replace(/^\s+|\s+$/g, '');
  if (!msg) return;
  inp.value = '';
  addRow('user', esc(msg));
  var pendingRow = addRow('assistant', '<span class="typing">🤖 Đang suy luận...</span>');
  var typingEl = pendingRow.getElementsByClassName('bubble')[0];
  sendBtn.disabled = true;
  typingEl.textContent = '🤖 Đang suy luận... (0s)';
  var sec = 0;
  var tick = setInterval(function () { sec += 1; typingEl.textContent = '🤖 Đang suy luận... (' + sec + 's)'; }, 1000);
  var timedOut = false;
  var timer = setTimeout(function () { timedOut = true; if (currentXhr) currentXhr.abort(); }, 30000);

  var xhr = new XMLHttpRequest();
  currentXhr = xhr;
  xhr.open('POST', '/api/chat', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) return;
    clearTimeout(timer);
    clearInterval(tick);
    sendBtn.disabled = false;
    currentXhr = null;
    if (typingEl.parentNode) typingEl.parentNode.removeChild(typingEl);
    if (timedOut) {
      addRow('assistant', '⏱️ Quá thời gian chờ (30 giây) — API đang chậm/hết quota. Hãy đổi dropdown sang <b>Mock</b> (chạy offline ngay) hoặc thử lại.');
      return;
    }
    try {
      var data = JSON.parse(xhr.responseText);
      if (xhr.status !== 200) throw new Error(data.error || ('Lỗi server (HTTP ' + xhr.status + ')'));
      var traceHtml = (data.trace && data.trace.length) ? renderTrace(data.trace) : '';
      addRow('assistant', esc(data.answer) + '<div class="meta">Provider: ' + esc(data.provider) + ' · Tools: ' + data.tool_calls + '</div>' + traceHtml);
    } catch (e) {
      addRow('assistant', '❌ ' + esc(e.message || e));
    }
    inp.focus();
  };
  xhr.send(JSON.stringify({ message: msg, provider: providerSel.value }));
}

sendBtn.addEventListener('click', send);
inp.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

addRow('assistant', esc('👋 Chào bạn! Mình là trợ lý đặt phòng họp & thiết bị. Thử hỏi:\n• "Kiểm tra các phòng họp còn trống ngày 20/09/2026 khung giờ 14:00-15:00"\n• "Đặt phòng BR-B202 lúc 09:00-10:30 ngày 21/09/2026 cho Nguyễn Văn Chiến (EMP0003), kèm máy chiếu"\n• "Cần phòng ≥20 người ngày 22/09/2026 09:00-11:00, đặt giúp Chị Lan (EMP0002)"'));

window.onerror = function (msg, src, line) {
  var d = document.createElement('div');
  d.className = 'row assistant';
  d.innerHTML = '<div class="bubble">❌ Lỗi JavaScript: ' + esc(msg) + ' (dòng ' + line + ')</div>';
  chat.appendChild(d);
  return false;
};

(function () {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/health', true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState === 4) {
      var badge = document.createElement('span');
      badge.style.cssText = 'font-size:11px;padding:3px 9px;border-radius:10px;color:#fff;';
      if (xhr.status === 200) { badge.textContent = '● Server OK'; badge.style.background = '#166534'; }
      else { badge.textContent = '● Mất kết nối server'; badge.style.background = '#7f1d1d'; }
      var headerRight = document.createElement('div');
      headerRight.style.cssText = 'display:flex;align-items:center;gap:8px;';
      headerRight.appendChild(providerSel);
      headerRight.appendChild(badge);
      var header = document.querySelector('header');
      header.appendChild(headerRight);
    }
  };
  xhr.send();
})();
</script>
</body>
</html>
"""


def extract_result(trace_logs):
    final_answer = ""
    tool_calls = 0
    for item in trace_logs:
        if item.get("action_type") == "FINAL_ANSWER":
            final_answer = item.get("output", "")
        elif item.get("action_type") == "TOOL_EXECUTION":
            tool_calls += 1
    if not final_answer:
        final_answer = "Không nhận được phản hồi từ Agent. Vui lòng thử lại câu hỏi khác."
    return final_answer, tool_calls


def build_provider(name):
    if name == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider(model="gpt-4o-mini")
        return MockOfflineProvider()
    if name == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            g = GeminiProvider()
            # Tắt chuỗi retry dài khi API bị giới hạn/quota: lỗi sẽ fallback Mock ngay lập tức
            g._max_retries = 0
            g._retry_delay = 1
            return g
        return MockOfflineProvider()
    if name == "mock":
        return MockOfflineProvider()
    return get_llm_provider()


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_html(INDEX_HTML)
        elif self.path == "/health":
            self._send_json(200, {"ok": True, "server": "vinuni-facilities-mcp-server"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = (payload.get("message") or "").strip()
            provider = (payload.get("provider") or "openai").lower()
            if not message:
                self._send_json(400, {"error": "Thiếu nội dung câu hỏi."})
                return
            llm = build_provider(provider)
            trace = run_react_agent(message, llm, MCP_SERVER)
            answer, tool_calls = extract_result(trace)
            self._send_json(200, {
                "answer": answer,
                "provider": llm.__class__.__name__,
                "tool_calls": tool_calls,
                "trace": trace,
            })
        except Exception as e:
            self._send_json(500, {"error": f"Lỗi xử lý: {e}"})

    def log_message(self, format, *args):
        sys.stdout.write("[webui] " + format % args + "\n")


def main():
    parser = argparse.ArgumentParser(description="ReAct Agent Web UI Demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print("=" * 62)
    print("🏢 FACILITIES AI — REACT AGENT WEB UI DEMO (DAY 03)")
    print(f"   Truy cập:  http://{args.host}:{args.port}")
    print("   Nhấn Ctrl+C để dừng server.")
    print("=" * 62)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Đã dừng Web UI.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()