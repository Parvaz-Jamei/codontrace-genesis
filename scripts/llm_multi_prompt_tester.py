#!/usr/bin/env python3
"""Multi-Prompt Test Suite for Local LLMs."""

import json
import urllib.error
import urllib.request
from pathlib import Path

PROMPTS = [
    "Explain the relationship between the Price Equation and the evolution of altruism in structured populations.",
    "How does the Eigen error catastrophe define the maximum genome size for a given mutation rate?",
    "Describe Hazen functional information and its application in measuring complexity in artificial life.",
    "What is Bedau's OEE (Open-Ended Evolution) activity metric and how do we measure evolutionary novelty?",
    "Explain Fisher's Geometric Model of adaptation and its implications for mutational step sizes."
]

MODELS = [
    "local_analyst",
    "board_model",
    "deepseek_r1_distill_7b",
    "qwen2.5_coder_1.5b",
    "qwen2.5_coder_3b"
]

API_URL = "http://127.0.0.1:8765/api/chat"

def analyze_empirical_data() -> str:
    root = Path(__file__).resolve().parents[2]
    exec_path = root / "Genesis_local_research_suite_5209c87/evidence/engine_1x100/execution.json"
    if exec_path.is_file():
        data = json.loads(exec_path.read_text(encoding="utf-8"))
        return f"Analyze this empirical data and extract the hypothesis verdict and rationale: {json.dumps(data)[:1000]}..."
    return "Analyze the empirical execution data (data not found locally)."

def run_test(prompt: str, model: str) -> None:
    print(f"\n--- Testing Model: {model} ---")
    print(f"Prompt: {prompt[:80]}...")
    
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"Status: SUCCESS (source: {result.get('source', 'unknown')})")
    except Exception as e:
        print(f"Status: FAILED ({e})")

def main():
    print("Starting Multi-Prompt Test Suite...")
    empirical_prompt = analyze_empirical_data()
    all_prompts = PROMPTS + [empirical_prompt]
    
    for model in MODELS:
        for prompt in all_prompts:
            run_test(prompt, model)

if __name__ == "__main__":
    main()
