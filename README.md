# Prompt Evaluation Harness

Run JSONL prompt cases with exact text, regex, JSON shape, and word-count checks. Responses can come from a fixture file or an OpenAI-compatible chat completions endpoint. The runner limits concurrency, caches responses by prompt version and case, and writes per-case results to JSON.

```sh
python evaluate.py examples/cases.jsonl --responses examples/responses.json --version baseline --output baseline.json
python compare.py baseline.json candidate.json --seed 7
python -m unittest discover -s tests -v
```

For an endpoint, pass `--endpoint URL --model MODEL --api-key-env ENV_NAME`; the environment variable holds the key. `compare.py` reports paired win/loss counts and a bootstrap interval for the pass-rate difference. Fixture mode makes scoring reproducible without an external service.

