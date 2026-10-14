---
name: oj-homework-checker
description: Build a scheduled checker that detects when a specific teacher posts new homework on a HUSTOJ-style OJ, fetches problem descriptions and samples, and asks the user whether to start coding in Visual Studio.
agent_created: true
---

# OJ Homework Checker

## When to Use

Use this skill when the user wants to automatically monitor an Online Judge (HUSTOJ-style) for new homework from a specific teacher and, on confirmation, open Visual Studio to write and test the solution.

## Workflow

1. **Probe the OJ structure**
   - Fetch `contest.php` without credentials. Most HUSTOJ instances expose the contest/homework list publicly.
   - Inspect the list HTML to find `cid`, contest title, status, visibility, and creator numeric ID.
   - Identify the teacher's assignments by a substring in the title (e.g., `填老师姓名教学班`).

2. **Decide how to view private contest problems**
   - For Private contests, visiting `contest.php?cid=<cid>` shows a password form. The field name is `password`.
   - POST the contest password to `contest.php?cid=<cid>`; the response contains problem links like `problem.php?cid=<cid>&pid=<pid>`.
   - Problem detail pages are reachable with the same session cookie after entering the contest password.

3. **Build the checker script** (`oj_checker.py`)
   - Use only the Python standard library (`urllib.request`, `http.cookiejar`, `re`, `html`, `json`).
   - Fetch the contest list, filter by teacher name, compare `cid` values against a persisted `state.json`.
   - For newly discovered contests, enter the contest with the password, parse problem links, fetch each problem, and extract title, time/memory limits, Description, Input, Output, Sample Input, Sample Output.
   - Write a human-readable or JSON report.

4. **Avoid the empty-CookieJar pitfall**
   - `http.cookiejar.CookieJar` has `__len__`, so `bool(empty_cookie_jar)` is `False`. Never use `cookie_jar or CookieJar()`; use `cookie_jar if cookie_jar is not None else CookieJar()`.

5. **Create the scheduled automation**
   - Use `automation_update` with `scheduleType: recurring` and an appropriate `rrule` (e.g., every 4 hours).
   - Prompt the automation to run the checker, summarize any new assignments, and ask the user "Y/N" to start coding in Visual Studio.

6. **Handle the Y/N response in chat**
   - If the user replies `Y`, open Visual Studio via the configured MCP connector, create/write the C/C++ project, and run local tests against the sample input/output.
   - Open each source file with the VS MCP `file_create` tool (existing files are just opened in the editor).

7. **Generate a VS solution for multi-problem contests**
   - One contest usually has several problems, each with its own `main()`. Put them in separate console projects inside one `.sln`.
   - Write a small Python generator (`make_vs_solution.py`) that emits `X.sln` plus one `<ProjName>/<ProjName>.vcxproj` and `.vcxproj.filters` per problem, referencing the shared source as `..\X.cpp`.
   - Use `PlatformToolset` matching the installed MSVC (check `cl.exe` version: 14.5x ⇒ `v145`), x64 only, `LanguageStandard` = `stdcpp17`.
   - Then `solution_open` → `build_solution` → poll `build_status` → verify with `errors_list` (severity Error, source build).

8. **Build and test locally with MSVC**
   - The VS MCP `terminal_run` tool may be unavailable ("integrated terminal component is unavailable"). Fall back to a `.bat` file invoked with the PowerShell tool.
   - In the bat: `call "D:\<vs>\VC\Auxiliary\Build\vcvarsall.bat" amd64` first, otherwise `cl.exe` fails with `C1034: iostream 不包括路径集`.
   - Compile: `cl /nologo /utf-8 /EHsc /std:c++17 /Fo"bin\" /Fe"bin\X.exe" X.cpp`
   - Run: `bin\X.exe < tests\X.in > tests\X.actual`, then `fc /N tests\X.expected tests\X.actual` to diff, and log everything to `tests\result.txt` (the PowerShell tool often does not echo stdout, so always redirect to a file and read it back).
   - Keep sample data in `tests/`: one `.in` + one `.expected` per problem; share a single `.in` when several problems use the same sample.

## Pitfalls

- **Empty `CookieJar` is falsy** — `http.cookiejar.CookieJar` defines `__len__`, so `bool(jar)` is `False` when empty. `cookie_jar or CookieJar()` silently creates a new jar every call and drops the session. Use `cookie_jar if cookie_jar is not None else CookieJar()`.
- **UTF-8 sources without BOM break MSVC** — with code page 936, `cl.exe` emits `C4819` and then misparses everything after the non-ASCII characters, producing bogus errors like `"cin": 未声明的标识符`. Add `/utf-8` to `cl.exe`, or `/utf-8 %(AdditionalOptions)` in the vcxproj `ClCompile` block.
- **Problem detail parsing** — HUSTOJ renders Bootstrap panels. Extract the title from `<h3>`, limits from `<div class="panel-heading">`, and each section from an `<h4>` followed by `<div class="panel-body">`. Plain-text regexes are unreliable.
- **Contest password ≠ login password** — entering a private contest only needs the contest password; submitting code needs account login (CSRF token from `csrf.php` + hex MD5). Never persist the account password.

## Auto-submitting to the OJ (HUSTOJ)

Logging in and submitting is scriptable, but the submit form uses a **CAPTCHA**, which must be solved with vision (the agent can read the image with the Read tool).

Protocol (see `assets/oj_submit.py`):

1. **Login** — GET `csrf.php` for the token, then POST `login.php` with `user_id`, `password=hex_md5(plaintext)`, `csrf`. Success returns `history.go(-2)` (no "Wrong" alert). Session is a `PHPSESSID` cookie — persist it with `MozillaCookieJar.save()` so the captcha fetch and the submit share a session.
2. **Enter the private contest** — GET then POST `password=<contest_password>` to `contest.php?cid=<cid>`.
3. **Fetch the captcha (MANDATORY, one-time use)** — GET `vcode.php` (a small GIF) and save it; it also stores the answer in the session. Read the image with the Read tool and transcribe the 4 digits. **Never submit without it and never reuse a previous image**: HUSTOJ silently discards a submission with a missing/wrong captcha — no error page, no redirect, no row in `status.php`. Treat that silent empty response as a captcha failure. A captcha is consumed on successful submit; always `prepare` again for the next problem, and if the image is unreadable, fetch a new one instead of guessing.
4. **Submit** — POST `submit.php` with `cid`, `pid` (0 = problem A), `language`, `source`, `vcode`, `csrf`. A `302 Location: status.php?...` means success; catch `HTTPError 302` and read the `Location` header (urllib raises instead of following when redirects are disabled). Note: `urllib` keeps the same URL even on success, so judge success by the `Location` header, not by the body.
   - **The `language` id must match what the code was actually compiled with locally** (e.g. local `cl /std:c++17` ⇒ OJ `C++`, id 1; a `.c` file built as C ⇒ id 0). Never hardcode the id: scrape the real `<select id="language">` options from `submitpage.php` (ids are OJ-specific), and resolve the language in this priority order — explicit CLI arg → `config.submit_language` → `config.build_standard` → source extension → `config.language`. Print the resolved `LANG: <name> (id=N)` line and emit a **WARN when the source extension contradicts the chosen language** (e.g. `x.c` but submitting as C++) so a mismatched submission is caught before it hits the judge.
5. **Read results** — `status.php?cid=<cid>&user_id=<uid>&<random>`; append a random parameter, because HUSTOJ caches status pages on disk and you may otherwise see stale rows. `正确100` = Accepted.
6. Keep ≥10 s between submissions (`$OJ_SUBMIT_COOLDOWN_TIME` defaults to 5 s).
7. Keep the account id/password in `config.json` (`student_id` / `student_password` / `contest_cid`); the contest password is separate from the login password.

## Central configuration (single source of truth for personal data)

Put everything the user might want to change — teacher name(s), student id, login password, contest/homework password, submit language, current contest cid, auto-submit toggle — into **one `config.json`**, never into the automation prompt or hardcoded in scripts. See `assets/config.example.json` and `assets/oj_config.py`.

- Support **multiple teachers**: read a `teachers` list (fall back to the scalar `teacher_filter` for compatibility) and match a contest if any teacher name appears in its title.
- Ship a tiny config CLI so the user can change settings from chat instead of editing JSON by hand: `show` (passwords masked, `--reveal` to show them), `get <key>`, `set <key> <value>` with type coercion (comma-separated → list, digits → int, true/false → bool).
- Make the automation prompt read the config at runtime and state explicitly that personal info lives only in `config.json`, so changing a password never means rewriting the workflow.

## Assets

- `assets/oj_checker.py`: a working boilerplate checker script that implements the workflow above.
- `assets/oj_submit.py`: login + captcha-aware submit + status reader.
- `assets/make_vs_solution.py`: generates a multi-project `.sln` for a contest.
- `assets/build_and_test.bat`: MSVC build + sample-diff test harness.
