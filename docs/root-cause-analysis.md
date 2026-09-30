# Root-Cause Write-Up: The Debugger Oscillation

*Virginia Tech Agentic AI System Design — Lesson 2, Demo 1 (Automated Code Testing and Debugging)*

## Overview

Built and ran the AutoGen CodeGen → Tester → Debugger agent chain from the Lesson 2 demo, connected to a personally deployed Azure OpenAI gpt-4o model (deployment name `gpt4o-chat`) rather than the shared credentials shown in the course material. Along the way, resolved several environment-level issues (VS Code/Jupyter Run behavior, missing virtual environment, Azure credential retrieval), then used the working pipeline to investigate a genuine failure: the Debugger loop exhausted its retry budget and reported failure. Root-causing that failure was the most valuable part of the exercise — it traced back not to a CodeGen or Debugger reasoning error, but to a flawed test case authored by the Tester agent itself.

## Environment Setup

- Deployed a `gpt-4o` model in Azure AI Foundry under a personal Azure subscription, to validate token allocation independent of the course-provided demo credentials
- Set up a project folder, Python virtual environment, and installed `autogen-agentchat`, `autogen-ext[openai]`, and `python-dotenv`
- Diagnosed and resolved a VS Code Run-button conflict where the Jupyter extension intercepted script execution and prompted for a kernel
- Stored Azure credentials (endpoint, API key, deployment name, model name, API version) in a local `.env` file rather than hardcoding them, consistent with existing API key hygiene practice

## Configuration Note: Deployment Name vs. Model Family

Unlike the course PDF's example (where the deployment name and model name were identical strings), this deployment used a custom deployment name (`gpt4o-chat`) distinct from the underlying model family (`gpt-4o`). AutoGen's client needs both: `azure_deployment` routes the API call to the correct Azure resource, while `model` tells AutoGen which model family it's talking to (for capability/tokenizer lookups). Configuring these as two separate values avoided a subtle mismatch that the course's own example didn't need to handle.

## The Script

The orchestrator is in [`agent_chain.py`](../agent_chain.py). It runs CodeGen, then Tester, then the test runner, and loops in the Debugger for up to `MAX_DEBUG_ROUNDS` rounds if the tests fail. Each run's events are logged to `runs/<timestamp>/log.jsonl`.

## Troubleshooting Log

Issues encountered while standing this up locally, their root cause, and how each was resolved:

| Issue | Root Cause | Resolution |
|---|---|---|
| VS Code prompted for a kernel instead of just running the script | The Run dropdown routed through the Jupyter extension's "Run in Interactive Window," which requires a kernel even for a `.py` file | Ran the script from the integrated terminal (`python agent_chain.py`) instead of the Run menu/button |
| `ModuleNotFoundError: No module named 'autogen_agentchat'` | No virtual environment had actually been created for this project folder; packages were installed into the wrong (or no) environment | Created the venv (`python -m venv venv`), activated it, and reinstalled packages inside it |
| `venv\Scripts\activate` — "module 'venv' could not be loaded" | Terminal's working directory was not the project folder containing the venv | `cd` into the correct folder; used the explicit relative-path form `.\venv\Scripts\Activate.ps1` |
| Friction retrieving/storing the Azure OpenAI key | Azure guidance pointed toward Key Vault / managed-identity patterns not needed for a local script | Retrieved the key directly from the deployment and stored it in a local `.env` file |
| Deployment name vs. model family mismatch risk | Azure deployment name (`gpt4o-chat`) differs from the underlying model family (`gpt-4o`) AutoGen needs for capability lookup | Set `model="gpt-4o"` and `azure_deployment="gpt4o-chat"` as two distinct config values |
| Debugger exhausted retries and reported failure | Root cause below (a mislabeled Tester-generated test case) — not a code or environment defect | Investigated via added debug logging; confirmed independently by computation |

## Root Cause Investigation: The Debugger Oscillation

### Symptom

On one run, the Test Runner reported a failing assertion (a specific long-string test case). The Debugger's first fix attempt introduced an unrelated change (an empty-string guard) that fixed nothing about the reported failure and broke a previously-passing test. The Debugger's second fix attempt reverted that change entirely, landing back on CodeGen's original code — which of course still failed the original assertion. The retry cap (2 rounds) was reached and the run correctly aborted with "STOPPED WITH FAILURES."

### Investigation

Added print statements to show the actual generated code at each stage (not just pass/fail), and pulled the Tester's generated `test_solution.py` directly from the saved run artifacts. The suspect assertion was:

```python
long_palindrome = "A" * 1000000 + "B" + "A" * 1000000
assert is_palindrome(long_palindrome) == False, "Large string that is not a palindrome"
```

Independently computing `s == s[::-1]` on that exact string in a separate Python shell returned `True`. The string is 1,000,000 A's, one B, then 1,000,000 more A's — perfectly symmetric around the single middle character. It **is** a palindrome. The Tester's assertion, and its own comment, were both wrong.

### Why the Tester Likely Got This Wrong

The Tester was almost certainly attempting a standard technique: take a long symmetric string and insert one mismatched character to break the symmetry. That technique is valid — but only if the inserted character lands somewhere off-center. Placed at the exact middle index of an odd-length string, it doesn't break anything, because the middle character of an odd-length palindrome only ever has to equal itself; it isn't compared against any other index. The Tester appears to have conflated "contains a character that doesn't match the others" with "is not symmetric front-to-back" — two different properties that happen to coincide everywhere except the center index.

### Conclusion

CodeGen's original `solution.py` was correct from the first attempt. Every subsequent step — the reported failure, both Debugger fix attempts, and the final abort — was the system correctly following its own retry/self-healing design while chasing a bug that existed only in the test data, not the code. This exposes a systemic risk in the CodeGen/Tester/Debugger pattern as implemented: the Tester acts as both question-writer and answer-key-writer for its own tests, with no independent verification step. A single mislabeled assertion can send an otherwise-correct implementation into a debugging loop with no mechanism, anywhere in the pipeline, capable of catching that the test itself is what's wrong.

## Secondary Observation: Non-Determinism Across Runs

A separate run of the identical script and configuration passed cleanly on the first attempt, with no Debugger rounds needed. Neither `AssistantAgent` has a fixed temperature or seed, so CodeGen and Tester generate different code and different test cases on every invocation — a passing run does not necessarily mean an underlying bug was fixed; it can simply mean the test case that would have caught it wasn't generated that time.

### Addendum: the "passing" run did not actually run any tests

*Added while preparing this repository, after re-checking the saved runs.*

The passing run described above (`sample_runs/run_2_passed_first_try`) is not evidence that the code was verified. Its `test_solution.py` defines `test_is_palindrome()` but never calls it: there is no `if __name__ == "__main__"` block and no call at the bottom of the file. The test runner executes `python test_solution.py`, which defines the function, runs nothing, and exits with code 0. The pipeline treats exit code 0 as "all tests passed."

Calling the function by hand shows it contains the same flawed assertion as the failing runs (`"A" * 1000 + "B" + "A" * 1000` asserted to be *not* a palindrome). So the difference between that run and the two failures was not that the test case was absent; it was that the test never executed. The earlier note that a passing run can simply mean the catching test was not generated is true, but here it is worse: the passing signal itself was empty.

This is a second instance of the same gap, on the other side of the loop. In the failing runs a wrong test blocks correct code. In the passing run a test that never ran approves code without checking it. Either way, nothing in the pipeline independently verifies the tests. A guard that fails the run if zero assertions executed (for example, running the tests with `pytest` and requiring at least one collected test) would catch this.

## Recommendations

- Fail the run if zero tests executed (for example, run `pytest` and require at least one collected, passing test), so an uncalled test function cannot count as a pass
- Add an independent oracle-check: before trusting a Tester-generated expected value, compute it directly (e.g. `s == s[::-1]`) and flag any assertion where the Tester's claimed answer disagrees with the computed one
- Pin `temperature=0` when debugging, to isolate configuration changes from ordinary LLM sampling variance
- Give the Debugger visibility into all failing assertions per round, not just the first one Python's `assert` halts on — e.g. by using a real test framework (`pytest`) that reports every failure rather than stopping at the first
- Externalize agent role definitions and retry policy into a YAML config file, matching what the lesson deck itself describes but the shipped demo code does not actually implement

## Result

Successfully deployed and validated a personal Azure OpenAI gpt-4o resource, connected it to a working three-agent AutoGen chain, and used the exercise to surface and root-cause a genuine, non-obvious failure mode in the code-test-debug pattern — one caused by the test-writer's own flawed reasoning rather than by CodeGen, the Debugger, or the Azure configuration.
