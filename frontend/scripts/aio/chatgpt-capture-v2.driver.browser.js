// Unattended driver for chatgpt-capture-v2.browser.js. Runs in a chatgpt.com tab and loads each
// queued prompt in a same-origin, full-window iframe, so the driver survives the per-prompt page
// loads that end a normal Runtime.evaluate call. Every prompt still gets a fresh temporary chat.
//
// Start (after smpl_aio_v2_src and smpl_aio_v2_queue are set):
//   new Function(localStorage.getItem("smpl_aio_v2_driver_src"))()
// Poll: window.__aioDriver   Stop after the current prompt: window.__aioDriver.stop = true
return (() => {
  const prev = window.__aioDriver;
  if (prev && prev.running) return { alreadyRunning: true, last: prev.last };
  const capture = new Function(
    'document', 'location', 'innerWidth', 'innerHeight',
    'PointerEvent', 'FocusEvent', 'MouseEvent', 'KeyboardEvent',
    localStorage.getItem('smpl_aio_v2_src'),
  );
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const st = (window.__aioDriver = { running: true, stop: false, startedAt: new Date().toISOString(), last: null, log: [], error: null });
  let f = document.getElementById('__aio_frame');
  if (!f) {
    f = document.createElement('iframe');
    f.id = '__aio_frame';
    document.body.appendChild(f);
  }
  f.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;border:0;z-index:2147483647;background:#fff';
  const load = (url) =>
    new Promise((resolve) => {
      const t = setTimeout(resolve, 30000);
      f.addEventListener('load', () => { clearTimeout(t); resolve(); }, { once: true });
      f.src = url;
    });
  (async () => {
    try {
      while (!st.stop) {
        const q = JSON.parse(localStorage.getItem('smpl_aio_v2_queue'));
        const item = q && q.items[q.idx];
        if (!item) break;
        await load('https://chatgpt.com/?temporary-chat=true&hints=search&q=' + encodeURIComponent(item.query));
        await sleep(2500);
        const w = f.contentWindow;
        // The driver owns navigation; the capture's own location.href writes are ignored.
        const loc = {
          get href() { return w.location.href; },
          set href(_) {},
          get pathname() { return w.location.pathname; },
          get search() { return w.location.search; },
        };
        const res = await capture(w.document, loc, w.innerWidth, w.innerHeight, w.PointerEvent, w.FocusEvent, w.MouseEvent, w.KeyboardEvent);
        st.last = res;
        st.log.push({ at: new Date().toISOString(), ...res });
      }
    } catch (e) {
      st.error = String((e && e.stack) || e);
    }
    st.running = false;
    st.finishedAt = new Date().toISOString();
  })();
  return { started: true };
})();
