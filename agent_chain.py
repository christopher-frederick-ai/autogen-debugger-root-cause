"""
AutoGen Agent Chain — CodeGen -> Tester -> Debugger
Connects to Azure OpenAI (gpt-4o) using credentials from a .env file.

Adapted from a Virginia Tech Agentic AI System Design course demo.
"""

import os
import re
import tempfile
import subprocess
import textwrap
import json
import datetime
import pathlib
import sys
import asyncio
from typing import Tuple

from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

load_dotenv()

# --- Azure OpenAI configuration (from .env) ---
model_client = AzureOpenAIChatCompletionClient(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    model=os.environ["AZURE_OPENAI_MODEL"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
)

# --- Light rate limit and retry caps ---
SLEEP_BETWEEN_CALLS_SEC = float(os.environ.get("RATE_SLEEP_SEC", "1.0"))
MAX_DEBUG_ROUNDS = int(os.environ.get("MAX_DEBUG_ROUNDS", "2"))

# --- Logging and run artifacts ---
RUN_DIR = pathlib.Path("runs") / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = RUN_DIR / "log.jsonl"

def log_event(kind: str, payload: dict):
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "kind": kind, **payload}
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# --- Helpers ---
CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_code_block(text: str) -> str:
    m = CODE_BLOCK_RE.search(text or "")
    return textwrap.dedent(m.group(1).strip()) if m else textwrap.dedent(text or "").strip()

def run_py_tests(solution_code: str, test_code: str, timeout_sec: int = 10) -> Tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        sol = pathlib.Path(tmp) / "solution.py"
        tst = pathlib.Path(tmp) / "test_solution.py"
        sol.write_text(solution_code, encoding="utf-8")
        tst.write_text(test_code, encoding="utf-8")

        cmd = [sys.executable, str(tst)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, cwd=tmp)
            out = (proc.stdout or "") + (proc.stderr or "")
            passed = proc.returncode == 0
            return passed, out.strip()
        except subprocess.TimeoutExpired as e:
            return False, f"TIMEOUT after {timeout_sec}s\n{e}"
        except Exception as e:
            return False, f"EXEC_ERROR: {e}"

async def _ask_async(agent: AssistantAgent, message: str, label: str) -> str:
    await asyncio.sleep(SLEEP_BETWEEN_CALLS_SEC)
    result = await agent.on_messages(
        messages=[TextMessage(content=message, source="user")],
        cancellation_token=None,
    )

    content = ""
    if hasattr(result, "chat_message") and getattr(result.chat_message, "content", None) is not None:
        content = result.chat_message.content
    elif hasattr(result, "messages") and result.messages:
        content = getattr(result.messages[-1], "content", "") or ""
    else:
        content = str(result)

    log_event("llm_reply", {"agent": getattr(agent, "name", "assistant"), "label": label, "content": content})
    return content

# --- Define the three agents ---
codegen = AssistantAgent(
    name="CodeGen",
    system_message=(
        "You are CodeGen. Write Python code for solution.py with a SINGLE function:\n"
        "def is_palindrome(text: str) -> bool\n"
        "- Return True if text is a palindrome.\n"
        "- Ignore non-alphanumeric characters and case.\n"
        "- Do not print; no comments; no extra text.\n"
        "Reply with ONLY a Python fenced code block for solution.py."
    ),
    model_client=model_client,
)

tester = AssistantAgent(
    name="Tester",
    system_message=(
        "You are Tester. Write tests in test_solution.py using Python asserts.\n"
        "Import from solution import is_palindrome.\n"
        "Cover typical and edge cases (empty, punctuation, mixed case, long string).\n"
        "Reply with ONLY a Python fenced code block for test_solution.py."
    ),
    model_client=model_client,
)

debugger = AssistantAgent(
    name="Debugger",
    system_message=(
        "You are Debugger. Given failing test output and the current solution.py, "
        "produce a FIXED solution.py that passes tests. Keep the same signature:\n"
        "def is_palindrome(text: str) -> bool\n"
        "Reply with ONLY a Python fenced code block for solution.py."
    ),
    model_client=model_client,
)

# --- Orchestrator ---
async def main():
    print("== AutoGen Code Testing and Debugging Chain (Azure OpenAI) ==")
    print(f"Deployment: {os.environ['AZURE_OPENAI_DEPLOYMENT']}")
    log_event("start", {"deployment": os.environ["AZURE_OPENAI_DEPLOYMENT"]})

    # 1) CodeGen creates solution.py
    cg_out = await _ask_async(codegen, "Write solution.py as specified. Return ONLY the code block.", "codegen")
    solution = extract_code_block(cg_out)
    if "def is_palindrome" not in solution:
        cg_out = await _ask_async(codegen, "Please include def is_palindrome(text: str) -> bool", "codegen_retry")
        solution = extract_code_block(cg_out)
    log_event("solution", {"code": solution})
    print("\n[CodeGen] Generated solution.py")
    print(solution)

    # 2) Tester creates test_solution.py
    tt_out = await _ask_async(tester, "Create test_solution.py for is_palindrome; ONLY code block.", "tester")
    tests = extract_code_block(tt_out)
    log_event("tests", {"code": tests})
    print("[Tester] Generated test_solution.py")

    # 3) Execute tests
    passed, output = run_py_tests(solution, tests, timeout_sec=10)
    print("\n[Test Runner] First run passed? ", passed)
    print(output)
    log_event("test_run", {"passed": passed, "output": output})

    # 4) If failed, loop with Debugger
    rounds = 0
    while not passed and rounds < MAX_DEBUG_ROUNDS:
        rounds += 1
        print(f"\n[Debugger] Fix attempt #{rounds}")
        dbg_prompt = (
            "Tests failed with output below. Current solution.py is also provided.\n\n"
            f"=== FAIL LOG ===\n{output}\n=== CURRENT solution.py ===\n```python\n{solution}\n```"
        )
        dbg_out = await _ask_async(debugger, dbg_prompt, f"debugger_round_{rounds}")
        fixed = extract_code_block(dbg_out)
        changed = bool(fixed) and fixed != solution
        print(f"[Debugger] Code changed from previous version? {changed}")
        if changed:
            solution = fixed
        print(solution)
        log_event("debug_fix", {"round": rounds, "code": solution, "changed": changed})
        passed, output = run_py_tests(solution, tests, timeout_sec=10)
        print("[Test Runner] Passed after fix? ", passed)
        print(output)
        log_event("test_rerun", {"round": rounds, "passed": passed, "output": output})

    # 5) Save artifacts and finish
    (RUN_DIR / "solution.py").write_text(solution, encoding="utf-8")
    (RUN_DIR / "test_solution.py").write_text(tests, encoding="utf-8")
    status = "ALL TESTS PASSED" if passed else "STOPPED WITH FAILURES (see logs)"
    print("\n== RESULT:", status)
    print("Artifacts saved to:", RUN_DIR)
    log_event("end", {"status": status, "artifacts_dir": str(RUN_DIR)})

if __name__ == "__main__":
    asyncio.run(main())