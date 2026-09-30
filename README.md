# When the AI's Own Test Was Wrong: Root-Causing a Multi-Agent Failure

A three-agent code pipeline failed, and the failure wasn't in the code. This repository is a small AutoGen experiment and a write-up of what it showed: **when one AI writes both the tests and the expected answers, nothing in the pipeline checks the tests themselves.**

## What it does

Three AutoGen agents run in a chain against an Azure OpenAI gpt-4o deployment:

1. **CodeGen** writes a Python function (`is_palindrome`).
2. **Tester** writes tests for it.
3. **Debugger** is called if the tests fail. It gets the failure output and the current code and proposes a fix, for up to two rounds.

Every step is logged to a JSON-lines file, so a run can be examined afterward.

## What we found

In two of the three saved runs the pipeline stopped with failures. The code CodeGen wrote first was correct. The failure came from a Tester-written assertion claiming that a string of many `A`s, one `B` in the exact middle, and many more `A`s is **not** a palindrome. It is one. A single character in the exact center of an odd-length string is only ever compared with itself.

So the Debugger was chasing a bug that existed only in the test. In one run it added an unrelated empty-string guard that broke a passing test, then reverted it. In the other it rewrote the function two different ways. Neither could succeed, because the code was already right.

**The passing run was worse.** In the remaining run the tests "passed," but the Tester's file defined its test function and never called it. Running the file executed nothing and exited cleanly, and the pipeline counted that as success. The same flawed assertion was in it. It would have failed if it had actually run.

| Run | Outcome reported | What actually happened |
|---|---|---|
| `run_1_failed_at_retry_cap` | Failed | Wrong assertion (a 20,001-character string that *is* a palindrome). Debugger rewrote correct code twice. |
| `run_2_passed_first_try` | Passed | Test function was never called, so no assertions ran. Same wrong assertion inside. |
| `run_3_failed_at_retry_cap` | Failed | Wrong assertion (a 2,000,001-character string that *is* a palindrome). Debugger's fix broke a passing test, then reverted. |

## Why it matters

Self-correcting agent loops are attractive: generate, test, fix, repeat. But the loop is only as trustworthy as its tests, and here the same model was both the question-writer and the answer-key writer. A wrong test can push correct work into an endless repair loop, and an empty test can approve work that was never checked. Both are easy to miss in a demo and costly in a real workflow.

## What I'd change (not implemented here)

- **Verify the tests independently.** Compute each expected value with trusted code (for example `s == s[::-1]`) and flag any assertion where the Tester's answer disagrees.
- **Fail if no tests ran.** Use a real test framework such as `pytest` and require at least one collected test, so an uncalled test function can't count as a pass.
- **Show the Debugger every failure,** not only the first one an `assert` stops at.
- **Fix the temperature to 0 while debugging,** to separate configuration changes from sampling noise.

The full investigation, including the environment problems hit along the way, is in [`docs/root-cause-analysis.md`](docs/root-cause-analysis.md).

## Repository contents

| Path | What it is |
|---|---|
| `agent_chain.py` | The CodeGen, Tester and Debugger chain and its test runner |
| `sample_runs/` | Three saved runs (code, tests, and event log for each) |
| `docs/root-cause-analysis.md` | The full write-up |
| `.env.example` | Names of the environment variables needed |

## Running it

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your own Azure OpenAI details. The **deployment name** and the **model family** are separate values (for example a deployment called `my-chat` running model `gpt-4o`), and both are needed.
3. Run `python agent_chain.py`. Each run writes to a new `runs/<timestamp>/` folder.

Results vary from run to run because the agents have no fixed temperature or seed.

## Notes

- Keys are read from environment variables and never stored in the code. Do not commit `.env`.
- This is a small experiment on one simple function, based on three saved runs. It shows a failure mode, not how often it happens.
- The sample logs had a local Windows temp path replaced with `<TEMP>`.
- Adapted from a Virginia Tech Agentic AI System Design course demo, run against a personal Azure OpenAI deployment.
