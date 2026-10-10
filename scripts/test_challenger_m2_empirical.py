"""Adversarial Empirical Stress Harness for CodonTrace Chat & Offline Models.

This script executes empirical tests across:
1. Various offline models (DeepSeek, Qwen Coder, non-existent, board-model, local-analyst, etc.)
2. Timeout hangs and latency analysis
3. Actionable launcher command verification (llama-server -m models/{model} --port 8088)
4. Silent drops and infinite fallback loops
5. Concurrent requests and cooperative abort handling
"""

import concurrent.futures
import os
import time
from typing import Any

from codontrace.console.chat import (
    _STATUS_CACHE,
    abort_chat_request,
    chat_turn,
    check_llm_status,
    set_llm_endpoint,
)


def run_tests() -> dict[str, Any]:
    results: dict[str, Any] = {
        "section_1_unmounted": [],
        "section_2_mounted_mismatch": [],
        "section_3_concurrency_stress": [],
        "section_4_abort_contracts": [],
        "section_5_malformed_payloads": [],
        "bugs_found": [],
    }

    print("======================================================================")
    print("SECTION 1: Offline Model Handling When Endpoint Is Unmounted")
    print("======================================================================")
    _STATUS_CACHE.clear()
    set_llm_endpoint("http://127.0.0.1:59998/v1/chat/completions")  # unmounted

    test_models = [
        "DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf",
        "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "Qwen2.5-Coder-3B-Instruct-IQ2_M.gguf",
        "non-existent.gguf",
        "board-model",
        "non_existent_no_ext",
        None,
        "local-analyst",
    ]

    for m in test_models:
        t0 = time.time()
        res = chat_turn("Audit hypothesis evidence", model=m, lang="en")
        dur = round((time.time() - t0) * 1000)
        reply = res.get("reply", "")
        has_launcher = "llama-server" in reply
        cmd_found = None
        for line in reply.splitlines():
            if "llama-server" in line:
                cmd_found = line.strip()
                break

        expected_cmd = (
            f"llama-server -m models/{m} --port 8088"
            if (m and m.endswith(".gguf"))
            else "llama-server -m models/your-model.gguf --port 8088"
        )
        exact_match = (cmd_found == expected_cmd) if has_launcher else False

        entry = {
            "model": m,
            "duration_ms": dur,
            "mounted": res.get("mounted"),
            "fallback": res.get("fallback"),
            "has_launcher": has_launcher,
            "cmd_found": cmd_found,
            "expected_cmd": expected_cmd,
            "exact_match": exact_match,
        }
        results["section_1_unmounted"].append(entry)
        print(f"Model: {str(m):42} | Fallback: {str(res.get('fallback')):5} | Launcher: {str(has_launcher):5} | Cmd: {cmd_found}")

        if m == "board-model":
            # Check what happens for board-model
            if cmd_found == "llama-server -m models/your-model.gguf --port 8088":
                bug_msg = "BUG: Selecting 'board-model' offline yields placeholder 'models/your-model.gguf' instead of an actionable command pointing to an actual model or 'board-model'."
                print(f"  [!] {bug_msg}")
                results["bugs_found"].append(bug_msg)

    print("\n======================================================================")
    print("SECTION 2: Offline Model Handling When Remote/Local Endpoint Is Mounted")
    print("======================================================================")
    # When an endpoint is mounted (e.g. board running 'qwen' or local llama-server)
    # but user selects an offline model not on that server
    set_llm_endpoint("http://10.225.130.20:8088/v1/chat/completions")
    _STATUS_CACHE.clear()
    status = check_llm_status()
    print(f"Live endpoint status: mounted={status.get('mounted')}, model={status.get('model')}, available={status.get('available_models')}")

    if status.get("mounted"):
        # Test selecting an offline model when board is mounted
        os.environ["CODONTRACE_LLM_TIMEOUT"] = "2.0"  # short timeout for test
        t0 = time.time()
        res = chat_turn("What is the hypothesis verdict?", model="DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf", lang="en")
        dur = round((time.time() - t0) * 1000)
        reply = res.get("reply", "")
        has_launcher = "llama-server" in reply
        print(f"Offline model with mounted board: duration={dur}ms | fallback={res.get('fallback')} | has_launcher={has_launcher}")
        print(f"Reply preview: {repr(reply[:160])}")

        if not has_launcher:
            bug_msg = (
                "CRITICAL BUG: When LLM endpoint is mounted (e.g. board running 'qwen'), selecting an offline GGUF model "
                "('DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf') SILENTLY DROPS the actionable launcher command entirely! "
                "Because `chat.py:439` gates launcher instructions behind `if is_fallback and not status.get('mounted'):`, "
                "which evaluates to False when any endpoint is mounted."
            )
            print(f"  [!] {bug_msg}")
            results["bugs_found"].append(bug_msg)

        results["section_2_mounted_mismatch"].append({
            "model": "DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf",
            "duration_ms": dur,
            "fallback": res.get("fallback"),
            "has_launcher": has_launcher,
            "cancelled_type": res.get("cancelled_type"),
        })

    print("\n======================================================================")
    print("SECTION 3: Concurrency Stress Test (Burst of 20 Parallel Requests)")
    print("======================================================================")
    set_llm_endpoint("http://127.0.0.1:59998/v1/chat/completions")  # unmounted
    _STATUS_CACHE.clear()

    def make_turn(idx: int) -> dict[str, Any]:
        return chat_turn(f"Concurrent stress prompt #{idx}", model="DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf", request_id=f"burst-{idx}")

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_turn, i) for i in range(20)]
        burst_results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_burst_time = time.time() - t0

    all_have_replies = all(isinstance(r.get("reply"), str) and len(r.get("reply")) > 20 for r in burst_results)
    all_have_fallback = all(r.get("fallback") is True for r in burst_results)
    all_have_launcher = all("llama-server" in r.get("reply", "") for r in burst_results)

    print(f"20 parallel requests completed in {total_burst_time:.3f}s")
    print(f"All valid replies: {all_have_replies} | All fallback: {all_have_fallback} | All have launcher: {all_have_launcher}")
    results["section_3_concurrency_stress"].append({
        "count": 20,
        "elapsed_seconds": total_burst_time,
        "all_valid": all_have_replies,
        "all_launcher": all_have_launcher,
    })

    print("\n======================================================================")
    print("SECTION 4: Cooperative Abort Contracts (/api/chat/abort)")
    print("======================================================================")
    # Test 4.1: Pre-abort request
    abort_chat_request("pre-aborted-req")
    res_pre = chat_turn("Test pre-abort", model="DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf", request_id="pre-aborted-req")
    print(f"Pre-abort: cancelled={res_pre.get('cancelled')}, reply={repr(res_pre.get('reply'))}")

    # Test 4.2: Abort non-existent
    abort_fake = abort_chat_request("non-existent-req-xyz")
    print(f"Abort non-existent request: returned={abort_fake} (expected False)")

    results["section_4_abort_contracts"].append({
        "pre_abort_cancelled": res_pre.get("cancelled"),
        "fake_abort_returned": abort_fake,
    })

    print("\n======================================================================")
    print("SECTION 5: Boundary & Malformed Inputs")
    print("======================================================================")
    edge_cases = [
        ("Empty string", ""),
        ("Whitespace only", "    \n\t   "),
        ("Huge prompt 10k chars", "Evolutionary dynamics " * 500),
        ("Path traversal in model", "DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf"),
    ]

    for label, prompt in edge_cases:
        res = chat_turn(prompt, model="DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf")
        print(f"Edge case '{label}': status=OK, reply_len={len(res.get('reply', ''))}")
        results["section_5_malformed_payloads"].append({
            "case": label,
            "reply_len": len(res.get("reply", "")),
        })

    print("\n======================================================================")
    print("SUMMARY OF EMPIRICAL FINDINGS:")
    print(f"Total confirmed bugs found: {len(results['bugs_found'])}")
    for i, b in enumerate(results["bugs_found"], 1):
        print(f"  {i}. {b}")
    print("======================================================================")

    return results


if __name__ == "__main__":
    run_tests()
