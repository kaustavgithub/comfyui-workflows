"""Tests for llm_restore.py (run: python3 -m unittest test_llm_restore, in this folder).
ComfyUI only imports the pack's __init__.py, so this file is never loaded there."""
import time
import unittest

import llm_restore


class FakeGate(llm_restore.Restorer):
    """A Restorer whose gate is a list: loading a model replaces what's loaded."""
    def __init__(self, loaded, delay=0.05):
        super().__init__("http://gate", "admin", delay=delay, log=lambda *a: None)
        self.loaded, self.loads = list(loaded), []

    def running(self):
        return list(self.loaded)

    def load(self, model):
        self.loads.append(model)
        self.loaded = [model]


class Queue:
    def __init__(self):
        self.remaining = 0

    def get_tasks_remaining(self):
        return self.remaining


def run_job(gate, queue, models):
    """A Documentary run: its LLM calls swap the loaded model."""
    queue.remaining = 1
    for m in models:
        gate.remember(m)
        gate.loaded = [m]
    queue.remaining = 0
    gate.after_job(queue)


def settle(gate):
    for _ in range(100):
        if not gate.waiting:
            return
        time.sleep(0.01)


class RestoreAfterRun(unittest.TestCase):
    def test_reloads_what_was_loaded_before(self):
        g, q = FakeGate(["qwen3.8:27b"]), Queue()
        run_job(g, q, ["qwen2.5vl:7b", "mistral-nemo:12b"])
        settle(g)
        self.assertEqual(g.loads, ["qwen3.8:27b"])
        self.assertIsNone(g.before)

    def test_nothing_loaded_before_nothing_reloaded(self):
        g, q = FakeGate([]), Queue()
        run_job(g, q, ["qwen2.5vl:7b"])
        settle(g)
        self.assertEqual(g.loads, [])

    def test_still_loaded_is_not_reloaded(self):
        g, q = FakeGate(["qwen3:14b"]), Queue()
        run_job(g, q, [])  # a run that only freed the GPU, 14b untouched
        settle(g)
        self.assertEqual(g.loads, [])

    def test_back_to_back_runs_keep_the_first_before(self):
        g, q = FakeGate(["qwen3.8:27b"]), Queue()
        run_job(g, q, ["mistral-nemo:12b"])
        run_job(g, q, ["mistral-nemo:12b"])  # second film within DELAY
        settle(g)
        self.assertEqual(g.loads, ["qwen3.8:27b"])

    def test_waits_while_another_job_runs(self):
        g, q = FakeGate(["qwen3.8:27b"]), Queue()
        g.delay = 0.3
        run_job(g, q, ["mistral-nemo:12b"])
        q.remaining = 1  # next job started during the delay
        settle(g)
        self.assertEqual(g.loads, [])
        self.assertEqual(g.before, ["qwen3.8:27b"])  # kept for that job's end
        run_job(g, q, ["mistral-nemo:12b"])
        settle(g)
        self.assertEqual(g.loads, ["qwen3.8:27b"])

    def test_someone_elses_model_is_left_alone(self):
        g, q = FakeGate(["qwen3.8:27b"]), Queue()
        g.delay = 0.2
        run_job(g, q, ["mistral-nemo:12b"])
        g.loaded = ["qwen3-coder:30b"]  # an admin loaded the coder after the run
        settle(g)
        self.assertEqual(g.loads, [])

    def test_no_token_does_nothing(self):
        g, q = FakeGate(["qwen3.8:27b"]), Queue()
        g.token = ""
        run_job(g, q, ["mistral-nemo:12b"])
        settle(g)
        self.assertIsNone(g.before)
        self.assertEqual(g.loads, [])


if __name__ == "__main__":
    unittest.main()
