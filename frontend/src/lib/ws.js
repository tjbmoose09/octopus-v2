// Octopus V2.2 — resilient /ws client with auto-reconnect + backoff.
// Consumers subscribe via `connect(onEvent, onStatus)`; the returned
// `close()` stops the connection and cancels pending reconnects.

export function connect(onEvent, onStatus) {
  let ws = null;
  let closed = false;
  let retry = 0;

  function open() {
    if (closed) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws`;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      onStatus?.({ state: "error", error: String(e) });
      schedule();
      return;
    }

    ws.onopen = () => {
      retry = 0;
      onStatus?.({ state: "open" });
    };
    ws.onmessage = (m) => {
      try {
        const payload = JSON.parse(m.data);
        onEvent?.(payload);
      } catch (_) {
        onEvent?.({ event_type: "raw", message: String(m.data) });
      }
    };
    ws.onerror = () => onStatus?.({ state: "error" });
    ws.onclose = () => {
      onStatus?.({ state: "closed" });
      if (!closed) schedule();
    };
  }

  function schedule() {
    const delay = Math.min(1000 * 2 ** retry, 10_000);
    retry += 1;
    setTimeout(open, delay);
  }

  open();

  return {
    close() {
      closed = true;
      try { ws?.close(); } catch (_) { /* noop */ }
    },
    send(obj) {
      try { ws?.send(JSON.stringify(obj)); } catch (_) { /* noop */ }
    },
  };
}
