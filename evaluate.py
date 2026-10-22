"""Prompt case runner with caching and structured checks."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen


def score(response: str, checks: list[dict]) -> list[dict]:
    results = []
    for check in checks:
        kind, value = check["type"], check["value"]
        if kind == "contains":
            passed = str(value).casefold() in response.casefold()
        elif kind == "regex":
            passed = re.search(value, response) is not None
        elif kind == "max_words":
            passed = len(response.split()) <= int(value)
        elif kind == "json_keys":
            try:
                parsed = json.loads(response)
                passed = isinstance(parsed, dict) and all(key in parsed for key in value)
            except json.JSONDecodeError:
                passed = False
        else:
            raise ValueError(f"Unsupported check: {kind}")
        results.append({"type": kind, "passed": passed})
    return results


def read_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Case IDs must be unique")
    return cases


def endpoint_call(endpoint: str, model: str, key: str, prompt: str) -> str:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST")
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload["choices"][0]["message"]["content"]


async def evaluate(cases: list[dict], version: str, cache_dir: Path, responses: dict[str, str] | None = None,
                   endpoint: str = "", model: str = "", key: str = "", concurrency: int = 4) -> list[dict]:
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    cache_dir.mkdir(parents=True, exist_ok=True)
    gate = asyncio.Semaphore(concurrency)

    async def one(case: dict) -> dict:
        identity = json.dumps([version, model, endpoint, case["id"], case["input"]], sort_keys=True)
        cache = cache_dir / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
        async with gate:
            started = time.perf_counter()
            if cache.exists():
                answer = json.loads(cache.read_text(encoding="utf-8"))["response"]
                cached = True
            else:
                if responses is not None:
                    answer = responses[case["id"]]
                else:
                    answer = await asyncio.to_thread(endpoint_call, endpoint, model, key, case["input"])
                cache.write_text(json.dumps({"response": answer}, ensure_ascii=False), encoding="utf-8")
                cached = False
            checks = score(answer, case.get("checks", []))
            return {"id": case["id"], "version": version, "response": answer, "passed": all(x["passed"] for x in checks),
                    "checks": checks, "cached": cached, "latency_ms": round((time.perf_counter()-started)*1000, 2)}

    return await asyncio.gather(*(one(case) for case in cases))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument("--model")
    parser.add_argument("--api-key-env")
    parser.add_argument("--version", required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path(".response_cache"))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.responses and not all((args.endpoint, args.model, args.api_key_env)):
        parser.error("provide --responses or an endpoint, model, and key environment name")
    key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    if not args.responses and not key:
        parser.error("API key environment variable is empty")
    fixture = json.loads(args.responses.read_text(encoding="utf-8")) if args.responses else None
    records = asyncio.run(evaluate(read_cases(args.cases), args.version, args.cache_dir, fixture, args.endpoint or "", args.model or "", key, args.concurrency))
    args.output.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{sum(row['passed'] for row in records)}/{len(records)} passed")
    raise SystemExit(0 if all(row["passed"] for row in records) else 1)

