"""Give the GPUs back to the LLMs after a Documentary run.

A run swaps LLMs in and out: the Story loads its vision and writer models,
and every GPU step (_free_gpu) unloads the LLMs on ComfyUI's GPU. Without
this, a model someone was using (e.g. qwen3.8 in OpenCode or Open WebUI)
stays unloaded until its next request.

  - remember(model): called before every LLM call of a run. The first call
    of a run reads which LLMs the gate has loaded ("before"); later calls only
    note the models the run itself uses. Back-to-back runs share one "before".
  - after_job(queue): called when ComfyUI finishes a job (success or error).
    Once the queue has stayed empty for DELAY seconds, the "before" models
    are loaded again, unless someone loaded a model the run didn't use
    meanwhile (then their choice stands).

No torch or ComfyUI imports, so it can be tested on its own (test_llm_restore.py).
"""
import json
import threading
import time
import urllib.error
import urllib.request

DELAY = 60  # s the queue must stay empty: the cron jobs queue films back to back


class Restorer:
    def __init__(self, url, token, delay=DELAY, log=print):
        self.url, self.token, self.delay, self.log = url.rstrip("/"), token, delay, log
        self.lock = threading.Lock()
        self.before = None  # LLMs loaded before the current run(s); None: no run yet
        self.used = set()   # models the run(s) asked for
        self.waiting = False

    # --- gate calls (admin token: ComfyUI's own) -------------------------
    def _call(self, path, body=None, timeout=10):
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers, method="POST" if body is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def running(self):
        return list(self._call("/gate/status").get("running", []))

    def load(self, model):
        """A 1-token request: llama-swap starts the model (the gate frees ComfyUI's VRAM first)."""
        self._call("/v1/chat/completions", {"model": model, "max_tokens": 1,
                                            "messages": [{"role": "user", "content": "hi"}]}, timeout=600)

    # --- hooks ----------------------------------------------------------
    def remember(self, model=None):
        if not self.token:
            return  # no admin token: can't read the state or switch models
        with self.lock:
            if self.before is None:
                try:
                    self.before = self.running()
                    self.log(f"[documentary] LLMs loaded before this run: {', '.join(self.before) or 'none'}")
                except (urllib.error.URLError, OSError, ValueError) as e:
                    self.before = []
                    self.log(f"[documentary] could not read the loaded LLMs ({e}); nothing to reload after the run")
            if model:
                self.used.add(model)

    def after_job(self, queue):
        """`queue` has get_tasks_remaining() (ComfyUI's PromptQueue)."""
        with self.lock:
            if self.before is None or self.waiting:
                return
            self.waiting = True
        threading.Thread(target=self._restore_when_idle, args=(queue,), daemon=True).start()

    def _restore_when_idle(self, queue):
        try:
            deadline = time.monotonic() + self.delay
            while time.monotonic() < deadline:
                if queue.get_tasks_remaining():
                    return  # another job runs: it keeps this "before"; its end tries again
                time.sleep(min(1.0, self.delay))
            with self.lock:
                if queue.get_tasks_remaining():
                    return
                before, used = self.before or [], set(self.used)
                self.before, self.used = None, set()
            self.restore(before, used)
        finally:
            with self.lock:
                self.waiting = False

    def restore(self, before, used):
        try:
            now = self.running()
        except (urllib.error.URLError, OSError, ValueError) as e:
            return self.log(f"[documentary] could not read the loaded LLMs ({e}); not reloading {before}")
        other = [m for m in now if m not in used and m not in before]
        if other:
            return self.log(f"[documentary] {', '.join(other)} was loaded during the run: leaving it, "
                            f"not reloading {', '.join(before)}")
        for m in before:
            if m in now:
                continue
            self.log(f"[documentary] run done: loading {m} again (it was loaded before the run)")
            try:
                self.load(m)
            except (urllib.error.URLError, OSError, ValueError) as e:
                self.log(f"[documentary] reloading {m} failed: {e}")
