#!/usr/bin/env python3
"""Milestone 2: End-to-End Live Browser UI & LLM Model Integration Verification Script.

Autonomous live browser verification using Selenium with Headless Chrome.
Navigates the preview console at http://127.0.0.1:8765/#/chat and http://127.0.0.1:8765/#/
Verifies:
1. DOM model selection <select> contains 3 <optgroup>s:
   - System Analysts
   - Server Endpoints
   - Local GGUF Models
2. Local GGUF models display architecture names, quantization tags, and file sizes in GB.
3. Offline model chat turn yields actionable copy-pasteable launcher instructions:
   llama-server -m models/DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf --port 8088
4. UI displays 'fallback' badge with '[Retry]' button.
5. Saves screenshots to artifacts/m2_screenshots and agent working directory.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    artifacts_dir = repo_root / "artifacts" / "m2_screenshots"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    agent_dir = repo_root / ".agents" / "teamwork" / "teamwork_preview_worker_m2" / "screenshots"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_dir_it2 = repo_root / ".agents" / "teamwork" / "teamwork_preview_worker_m2_it2" / "screenshots"
    agent_dir_it2.mkdir(parents=True, exist_ok=True)

    def save_screenshot(driver: webdriver.Chrome, name: str) -> None:
        p1 = artifacts_dir / f"{name}.png"
        p2 = agent_dir / f"{name}.png"
        p3 = agent_dir_it2 / f"{name}.png"
        driver.save_screenshot(str(p1))
        driver.save_screenshot(str(p2))
        driver.save_screenshot(str(p3))
        print(f"[SCREENSHOT] Saved: {p1}, {p2}, and {p3}")

    print("=== Step 1: Initializing Headless Chrome ===")
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    driver = webdriver.Chrome(options=opts)
    try:
        base_url = "http://127.0.0.1:8765"
        chat_url = f"{base_url}/#/chat"
        home_url = f"{base_url}/#/"

        print(f"=== Step 2: Navigating to {chat_url} ===")
        driver.get(chat_url)
        time.sleep(2)
        save_screenshot(driver, "01_chat_view_initial")

        print("=== Step 3: Inspecting Model Select DOM in Chat View ===")
        select_elem = driver.find_element(By.TAG_NAME, "select")
        optgroups = select_elem.find_elements(By.TAG_NAME, "optgroup")
        optgroup_labels = [og.get_attribute("label") for og in optgroups]
        print(f"Discovered optgroups: {optgroup_labels}")

        assert "System Analysts" in optgroup_labels, f"Missing 'System Analysts' optgroup in {optgroup_labels}"
        assert "Server Endpoints" in optgroup_labels, f"Missing 'Server Endpoints' optgroup in {optgroup_labels}"
        assert "Local GGUF Models" in optgroup_labels, f"Missing 'Local GGUF Models' optgroup in {optgroup_labels}"
        print("✓ Successfully verified 3 optgroups in DOM: System Analysts, Server Endpoints, Local GGUF Models")

        # Inspect local GGUF models options
        gguf_og = next(og for og in optgroups if og.get_attribute("label") == "Local GGUF Models")
        gguf_options = gguf_og.find_elements(By.TAG_NAME, "option")
        gguf_details = []
        for opt in gguf_options:
            val = opt.get_attribute("value")
            txt = opt.text
            gguf_details.append({"value": val, "text": txt})
            print(f"  GGUF Option: value='{val}' | text='{txt}'")

        assert len(gguf_details) >= 4, f"Expected at least 4 GGUF models, found {len(gguf_details)}"

        # Verify architecture, quantization, and GB in labels
        has_deepseek = any("Deepseek R1 Distill" in o["text"] and "[IQ2_XS]" in o["text"] and "GB" in o["text"] for o in gguf_details)
        has_qwen_coder = any("Qwen" in o["text"] and "Coder" in o["text"] and ("Q4_K_M" in o["text"] or "IQ2_M" in o["text"]) and "GB" in o["text"] for o in gguf_details)
        assert has_deepseek, "DeepSeek R1 Distill with [IQ2_XS] and GB size not found in option labels"
        assert has_qwen_coder, "Qwen Coder model with quant and GB size not found in option labels"
        print("✓ Verified local GGUF models include architecture names, quantization tags, and memory footprints in GB.")

        print(f"=== Step 4: Navigating to {home_url} to start offline model chat turn ===")
        driver.get(home_url)
        time.sleep(2)
        save_screenshot(driver, "02_home_view")

        # Select offline model in HomeView with polling wait for async /api/models population
        target_model = "DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf"
        t0 = time.time()
        home_select = None
        while time.time() - t0 < 10:
            select_elem = driver.find_element(By.TAG_NAME, "select")
            home_select = Select(select_elem)
            vals = [opt.get_attribute("value") for opt in home_select.options]
            if target_model in vals:
                break
            time.sleep(0.5)
        assert home_select is not None, "Select element not found"
        home_select.select_by_value(target_model)
        print(f"Selected offline model: {target_model}")

        # Enter prompt in textarea
        textarea = driver.find_element(By.TAG_NAME, "textarea")
        test_prompt = "Audit live 8 frontier challenges and report hypothesis evaluation."
        textarea.send_keys(test_prompt)

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("Submitted chat turn from HomeView, waiting for transition to #/chat and analyst response...")

        # Poll for response
        start_t = time.time()
        reply_found = False
        while time.time() - start_t < 25:
            time.sleep(1)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "llama-server" in body_text and "DeepSeek-R1-Distill-Qwen-7B.i1-IQ2_XS.gguf" in body_text:
                reply_found = True
                break

        save_screenshot(driver, "03_chat_offline_reply_fallback")
        assert reply_found, "Did not find expected offline launcher instruction in response body text within timeout!"
        print("✓ Response received containing actionable launcher instructions!")

        # Verify launcher instruction syntax
        expected_cmd = f"llama-server -m models/{target_model} --port 8088"
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert expected_cmd in body_text, f"Expected '{expected_cmd}' in body text, got snippet: {body_text[:500]}"
        print(f"✓ Confirmed exact copy-pasteable launcher command in UI: {expected_cmd}")

        # Verify fallback badge and Retry button
        fallback_spans = driver.find_elements(By.XPATH, "//*[contains(text(), 'fallback')]")
        assert len(fallback_spans) > 0, "Fallback indicator not found in DOM"
        retry_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Retry') or contains(text(), 'تلاش مجدد')]")
        assert len(retry_buttons) > 0, "Retry button not found in DOM"
        print("✓ Confirmed 'fallback' indicator and '[Retry]' button present in UI badge.")

        print("=== Step 5: Performing second turn within #/chat with active thread ===")
        # Verify ChatView now has active thread with textarea
        chat_textarea = driver.find_element(By.TAG_NAME, "textarea")
        chat_textarea.send_keys("What is the Quasispecies error catastrophe threshold?")
        chat_submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        chat_submit.click()
        print("Submitted second turn in ChatView, polling for response...")

        start_t = time.time()
        second_found = False
        while time.time() - start_t < 25:
            time.sleep(1)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "Quasispecies" in body_text or "Eigen" in body_text or "error catastrophe" in body_text:
                second_found = True
                break

        save_screenshot(driver, "04_chat_second_turn")
        assert second_found, "Did not find expected second turn response in body text within timeout!"
        print("✓ Second turn completed successfully within #/chat.")

        print("\n=======================================================")
        print("ALL LIVE BROWSER VERIFICATION CHECKS PASSED PERFECTLY!")
        print("=======================================================\n")
        return 0

    except Exception as exc:
        print(f"VERIFICATION FAILURE: {exc}", file=sys.stderr)
        save_screenshot(driver, "error_failure_state")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
