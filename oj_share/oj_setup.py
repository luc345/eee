#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OJ 作业自动化 · 环境检测与配置助手（多宿主版）

双击运行后：
  0. 先选你用的 AI 助手：DSH / WorkBuddy / TRAE CN（没装 WorkBuddy 可在这里下载）
  1. 检测本机是否装了对应的助手 / Python / C++ 编译器，并能访问 OJ
  2. 缺什么就给出下载地址和安装指引
  3. 环境齐全后，引导填写个人信息，生成 config.json、部署脚本与技能包，
     并按所选宿主输出可直接使用的定时任务内容

宿主差异只影响三件事：技能包放哪、SKILL.md 里怎么写、定时任务怎么建。
检测 / 填信息 / 写配置 / 放脚本 / 生成 prompt 这几步三个宿主完全一样。

本脚本只用 Python 标准库，可直接运行，也可用 PyInstaller 打包成单文件 exe。
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request

# ---------------------------------------------------------------------------
# 终端输出
# ---------------------------------------------------------------------------

LINE = "=" * 62


def _force_utf8_streams():
    """把三个标准流尽量锁成 UTF-8。

    打包成 exe 后，若控制台代码页 / 区域不是 UTF-8，中文输入会在读取时
    被按 GBK 解码成代理字符，写 JSON 时就炸（surrogates not allowed）。
    这里统一成 UTF-8，交互和管道两种用法都安全。
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_force_utf8_streams()

if platform.system() == "Windows":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass


def ask_input(prompt=""):
    """先刷新提示，再读输入。

    直接用 input() 时，Windows 上提示串可能留在缓冲里，导致
    提示顺序和实际读取顺序错位（管道输入时尤其明显），所以统一走这里。
    """
    try:
        sys.stdout.write(prompt)
        sys.stdout.flush()
    except Exception:
        pass
    try:
        line = sys.stdin.readline()
    except Exception:
        line = ""
    if not line:
        raise EOFError
    # 去掉行尾和可能混进来的 BOM（从文件/别的程序喂输入时常见）
    return line.rstrip("\r\n").lstrip("\ufeff").strip()


def clear():
    """进入新界面前清掉上一屏。"""
    try:
        os.system("cls" if platform.system() == "Windows" else "clear")
    except Exception:
        print("\n" * 3)


def title(text):
    clear()
    print(LINE)
    print("  " + text)
    print(LINE)


def ok(msg):
    print("  [正常] " + msg)


def bad(msg):
    print("  [缺少] " + msg)


def warn(msg):
    print("  [提示] " + msg)


def info(msg):
    print("        " + msg)


def pause(msg="按回车返回菜单..."):
    try:
        ask_input("\n  " + msg)
    except (KeyboardInterrupt, EOFError):
        pass


# ---------------------------------------------------------------------------
# 宿主（AI 助手）定义 —— 本文件的核心扩展点
# ---------------------------------------------------------------------------
#
# 要再加一个宿主，只需在 HOSTS 里加一条；其余流程会自动适配。

HOSTS = {
    "dsh": {
        "order": 1,
        "name": "DSH",
        "full": "DeepSeek Harness",
        "desc": "命令行/Web 的编码智能体（就是当前这个）",
        "home_dir": ".dsh",              # 用户目录下的配置目录
        "skills_sub": "skills",          # 用户级技能包目录
        "project_skills": os.path.join(".dsh", "skills"),   # 项目级技能包目录
        "workdir_name": "dsh-oj",        # 建议的脚本工作目录名
        "site": "https://github.com/deepseek-ai",
        "install_tip": [
            "安装 DSH（三选一）：",
            "  a) 桌面端：到 https://github.com/deepseek-ai 下载 DeepSeek Harness",
            "  b) 免安装：npx @deepseek-ai/dsh web",
            "  c) 已装 Node 的话：npm i -g @deepseek-ai/dsh",
            "装好后在终端敲 dsh --help 能看到帮助就说明好了。",
        ],
    },
    "workbuddy": {
        "order": 2,
        "name": "WorkBuddy",
        "full": "腾讯 WorkBuddy",
        "desc": "带定时任务的 AI Agent 办公客户端",
        "home_dir": ".workbuddy",
        "skills_sub": os.path.join("skills"),
        "project_skills": os.path.join(".workbuddy", "skills"),
        "workdir_name": "WorkBuddy",
        "site": "https://www.workbuddy.cn/",
        "download_page": "https://www.codebuddy.cn/docs/workbuddy/Download-History",
        "download_fallback": "https://www.workbuddy.cn/",
        "install_tip": [
            "安装 WorkBuddy：",
            "  到 https://www.workbuddy.cn/ 下载 Windows 版并安装。",
            "  装好后重启一次，让它在用户目录生成 .workbuddy 文件夹。",
            "  本向导的宿主选择界面里也可以直接选 d 让它帮你下载安装包。",
        ],
    },
    "trae": {
        "order": 3,
        "name": "TRAE CN",
        "full": "字节 TRAE CN / TraeWork",
        "desc": "带自动化定时任务的 AI IDE",
        "home_dir": ".trae-cn",
        "skills_sub": "skills",
        "project_skills": os.path.join(".trae", "skills"),
        "workdir_name": "trae-oj",
        "site": "https://www.trae.cn/",
        "download_page": "https://www.trae.cn/ide/download",
        "install_tip": [
            "安装 TRAE CN：",
            "  到 https://www.trae.cn/ide/download 下载 Windows 版并安装。",
            "  装好后打开一次，让它在用户目录生成 .trae-cn 文件夹。",
        ],
    },
}

HOST_ORDER = sorted(HOSTS, key=lambda k: HOSTS[k]["order"])


def host_root(host):
    """该宿主在用户目录下的配置根。"""
    return os.path.join(os.path.expanduser("~"), HOSTS[host]["home_dir"])


def host_skills_dir(host):
    return os.path.join(host_root(host), HOSTS[host]["skills_sub"])


# ---------------------------------------------------------------------------
# 随包资源（打包成 exe 后从 _MEIPASS 里找）
# ---------------------------------------------------------------------------

ASSET_FILES = [
    "config.example.json",
    "oj_checker.py",
    "oj_submit.py",
    "oj_config.py",
    "make_vs_solution.py",
    "fetch_cid.py",
    "fetch1766.py",
    "build_and_test.bat",
    "SKILL.md",
]

# 释放到脚本目录时改成 .example 的名字（避免被误当成可直接跑的脚本）
AS_EXAMPLE = {"build_and_test.bat": "build_and_test.example.bat"}


def asset_base():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _asset_bases():
    """资源搜索顺序：打包时在 _MEIPASS；直接跑 .py 时先看几个随包目录。"""
    bases = []
    if not getattr(sys, "frozen", False):
        here = os.path.dirname(os.path.abspath(__file__))
        bases += [
            os.path.join(here, "oj_setup_assets"),
            os.path.join(here, "oj-homework-checker", "assets"),
            here,
        ]
    bases.append(asset_base())
    return bases


def asset_path(name):
    """返回随包资源的真实路径，找不到返回 None。"""
    for b in _asset_bases():
        p = os.path.join(b, name)
        if os.path.isfile(p):
            return p
    return None


def read_asset(name):
    p = asset_path(name)
    if not p:
        raise FileNotFoundError(f"随包资源缺失：{name}（找过 {_asset_bases()}）")
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 宿主适配：把 WorkBuddy 版技能包改写成目标宿主版
# ---------------------------------------------------------------------------

RE_WB_HOME = re.compile(r"%userprofile%[\\/]\.workbuddy|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]\.workbuddy", re.I)
RE_WB_BARE = re.compile(r"(?<![\w.])\.workbuddy(?![\w])")
RE_WB_WORKDIR = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]WorkBuddy[\\/][^\\/\s]+", re.I)
RE_WB_WORKDIR_BARE = re.compile(r"C:[\\/]Users[\\/]<[^>]+>[\\/]WorkBuddy", re.I)
RE_WB_SKILLDIR = re.compile(r"C:[\\/]Users[\\/]<你的用户名>[\\/]\.workbuddy[\\/]skills", re.I)
RE_WB_PY = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]\.workbuddy[\\/]binaries[\\/]python[\\/]versions[\\/][\d.]+[\\/]python\.exe", re.I)
RE_WORKBUDDY_WORD = re.compile(r"WorkBuddy")
RE_VS_MCP_OPEN = re.compile(r"open Visual Studio via the configured MCP connector")
RE_VS_MCP_FILE = re.compile(r"VS MCP (`?[a-z_]+`?) tool")
RE_VS_MCP_TERM = re.compile(r"VS MCP `terminal_run` tool")
RE_WB_AUTOMATION_BLOCK = re.compile(
    r"5\. \*\*Create the scheduled automation\*\*.*?(?=\n\d+\. \*\*)", re.S
)
RE_DATE_DIR = re.compile(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}")


def adapt_skill(name, text, host):
    """把技能包里的 WorkBuddy 措辞/路径改写成目标宿主。"""
    h = HOSTS[host]
    skills = host_skills_dir(host).replace("\\", "/")
    home_tilde = "~/" + h["home_dir"]

    if name == "SKILL.md":
        t = text
        if host != "workbuddy":
            # 路径：换成目标宿主的真实位置
            t = RE_WB_PY.sub(lambda m: "<PYTHON>", t)
            t = RE_WB_SKILLDIR.sub(lambda m: skills, t)
            t = RE_WB_WORKDIR.sub(lambda m: "<WORKDIR>", t)
            t = RE_WB_HOME.sub(home_tilde, t)
            t = RE_WB_BARE.sub(h["home_dir"], t)
            t = RE_DATE_DIR.sub("<会话目录>", t)
        # 触发方式（原来那句"建定时任务/打开 Visual Studio"统一改掉）
        t = t.replace(
            "Use this skill when the user wants to automatically monitor an Online Judge (HUSTOJ-style) "
            "for new homework from a specific teacher and, on confirmation, open Visual Studio to write "
            "and test the solution.",
            "Use this skill when the user asks (in one sentence) to check whether a specific teacher "
            "posted new homework on an Online Judge (HUSTOJ-style) and to write, locally test, and "
            "submit the solutions.",
        )
        t = t.replace("on confirmation, ", "")
        if host != "workbuddy":
            # Visual Studio / MCP 措辞：DSH 与 TRAE 走编辑器自带终端
            t = RE_VS_MCP_OPEN.sub("用编辑器打开源码目录", t)
            t = RE_VS_MCP_FILE.sub(r"编辑器工具（\1）", t)
            t = RE_VS_MCP_TERM.sub("编辑器自带的终端工具", t)
            t = t.replace("open Visual Studio to write and test the solution", "写并本地测试解法")
            t = t.replace("start coding in Visual Studio", "开始写代码")
            t = RE_WORKBUDDY_WORD.sub("DSH" if host == "dsh" else "TRAE CN", t)
        return t

    if name == "build_and_test.bat":
        # 只改目录；%~dp0 指向 bat 自己所在目录，最稳
        t = text
        t = RE_WB_WORKDIR.sub(lambda m: r"%~dp0", t)
        t = RE_WB_HOME.sub(home_tilde, t)
        t = RE_WB_BARE.sub(h["home_dir"], t)
        return t

    if name in ("make_vs_solution.py",):
        # 这里保留 \oj_homework 一层，脚本是按 oj_homework 为用户工作根写的
        target = os.path.join(os.path.expanduser("~"), h["workdir_name"], "oj_homework", "code", "cid1766")
        t = text
        t = RE_WB_WORKDIR.sub(lambda m: target, t)
        t = RE_WB_HOME.sub(home_tilde, t)
        t = RE_WB_BARE.sub(h["home_dir"], t)
        return t

    # 其余脚本与配置模板：只改路径措辞
    t = text
    t = RE_WB_HOME.sub(home_tilde, t)
    t = RE_WB_BARE.sub(h["home_dir"], t)
    return t


def workflow_section(host):
    """技能包里的工作流章节：跟 automation-prompt.txt 的四步保持一致。"""
    term = "编辑器自带的终端" if host != "workbuddy" else "terminal_run 工具"
    return f"""## Workflow

一句话触发后，按下面六步一次跑完，中间不用问用户（除了第 4 步那种要警告的情况）。

### 1. 检测新作业

- 运行 `oj_checker.py`：拉取作业列表 → 按 `config.json` 里的 `teachers` 过滤 → 对比 `state.json` 去重。
- 若输出「暂无新作业」或新发布数为 0，只回一句「暂无新作业。」就结束。
- 有新作业时记下新 `cid`，用 `oj_config.py set contest_cid <cid>` 写回配置；
  然后直接跑 `fetch_cid.py <cid>` 抓题面（Description / Input / Output / Sample Input / Sample Output），
  它会存成 `cid<cid>_problems.json`，不用临时写脚本。

### 2. 写码与本地测试

- 每题一份源码，先放 `code\\cid<cid>\\`，命名 `A_xxx.cpp`、`B_xxx.cpp`（与 OJ 的 A/B/C/D/E 对应，pid 从 0 开始）。
- 参照 `build_and_test.example.bat` 复制一份并改题目清单：先用 `vcvarsall.bat amd64` 初始化 MSVC，
  再 `cl /nologo /utf-8 /EHsc /std:c++17`（`/utf-8` 不能省，否则中文注释会让 MSVC 解析错乱）；
  用 g++ 的话换成 `g++ -std=c++17`。
- 每题样例放 `tests\\` 下逐一比对（`fc /N` 或 `diff`），结果写进 `tests\\result.txt` 再读回来。
- 只有本地样例全过的题才允许提交；没过的题在汇报里说明原因，不要硬提。

### 3. 自动提交（每题完整走验证码流程）

- 提交语言必须与本地编译用的语言一致：先跑 `oj_submit.py langs` 核对编号表，
  `config.json` 的 `submit_language` 要和编译标准对上（`cl /std:c++17` → OJ「C++」= 1）。
  submit 会打印 `LANG: ... (id=N)`；出现 `WARN: 源码扩展名 ... 不一致` 时先确认本地编译语言，别盲目提交。
- 每题依次执行，缺一不可：
  1. `oj_submit.py prepare` —— 登录并把新验证码刷到 `vcode.gif`（确认修改时间是新的）；
  2. 用 Read 工具看图，读出 4 位数字（看不清就重新 prepare，**不要猜**）；
  3. `oj_submit.py submit <pid> <源码绝对路径> <4位数字> [语言编号]`
     - `SUBMIT_OK` = 成功，随后会打印 `NOTE 本次验证码已消费`
     - `FAIL 提交被 OJ 静默拒绝` = 验证码不对，回到第 1 小步重取（每题最多 3 次）
     - `ABORT 缺少验证码` = 流程错误，回到第 2 小步重新读图
  4. `oj_submit.py status 6` 查结果（显示「等待/编译中」就等 10 秒再查，「正确100」= Accepted）
- 每题提交间隔至少 10 秒，避免触发提交冷却。

### 4. 每题盯结果：不过就换方法重来，最多 3 遍

提交完**不是结束**，必须看 OJ 给的判定，错了就换思路重来。每题最多 3 遍：

```
第 1 遍：写码 → 本地样例过 → submit → status 看结果
  ├─ Accepted（正确100）→ 记「一次通过」，下一题
  └─ 不是 Accepted → 按第 2 遍换方法重来
第 2 / 第 3 遍：换一种做法（换算法、换边界处理、换数据类型、换输入输出方式…）
  ├─ Accepted → 记「第 N 遍通过」，下一题
  └─ 仍不是 Accepted → 进入下一遍；第 3 遍还是不过 → 停手，警告用户（见下）
```

**硬性约束，防止无限重试烧 token：**

- **单题最多 3 遍**，每遍都必须真正换一种方法，不要原样重交（原样重交只会再错一次）；
- 每一遍之间**不要重复贴已经贴过的代码**，只说明这遍改了什么；
- **同一道题连续 3 遍都不对，立即停手**，不要再试第 4 遍，也不要去猜 OJ 的隐藏用例；
- 遇到这几类情况**当遍就停手**，不必凑满 3 遍：
  - 提交被 OJ 拒绝且原因不是代码（验证码 3 次都取不对、账号/密码错、作业密码错、考试已结束、OJ 报错）；
  - 本地编译/环境坏了（编译器找不到、磁盘满、网络不通）；
  - 题目本身读不明白（题面抓取失败或语义有歧义）。

**停手时要在对话里给出明确警告**（同时写进 `汇报.md`），至少包含：

- 哪道题、题号、文件路径；
- 已经试了哪几种方法、每种的结果（Wrong Answer / Time Limit / Runtime Error / Compile Error …）；
- 当前判断：是思路不对、还是数据规模没考虑、还是题意理解有偏差；
- 建议用户怎么处理（例如：把题面发我给你分析、检查是否时限很紧、换个输入方式）。

> 宁可交一份"3 题过 2 题 + 1 题明确警告"的汇报，也不要无声无息地反复重试耗掉 token。

### 5. 整理收尾文件夹（必做）

作业做完后，把每道题的代码和汇报按下面的结构整理好，方便直接交：

```
<config.json 里的 deliver_dir>\\<作业目录>\\
    1-1-a.cpp       <- 题号照抄 OJ 上的题号，扩展名跟源码一致
    1-1-b.cpp
    ...
    汇报.md
```

- 收尾文件夹位置从 `config.json` 的 `deliver_dir` 读（默认是桌面上的 `OJ作业`，用户可以自己改）；
- **`deliver_dir` 和 `<作业目录>` 这两层如果不存在，先自己新建出来再写文件**（配置助手第一次配置时会把 `deliver_dir` 建好，但用户可能后来又删了、或者换成了移动硬盘/U 盘上的路径）；
- `<作业目录>` 就是 OJ 上这份作业的编号/序号，例如第一份作业的第 1 题就是 `1-1-a.cpp`；
  **题号直接用 OJ 页面上显示的题号**，不要自己重编；
- 每道题的源码各存一份到该目录，文件名里的题号要能一眼对上题目；
- 把**最终通过的那一版**存进去；没过的那题也存当前最好的一版，并在 `汇报.md` 里标明未通过。

### 6. 汇报

- 在对话里用简洁中文报结果，同时把同样内容写成 `<deliver_dir>\\<作业目录>\\汇报.md`：
  每题一行 `题号 / 文件名 / 语言 / 第几遍通过或未通过 / 评测结果`，末尾附状态链接
  `<base_url>/status.php?cid=<cid>&user_id=<student_id>`。
- 有没过的题，汇报里要**显式标出警告**，别只写"已完成"。
- 不要删除 `state.json` 里的记录（下次靠它去重）。若全部 AC，结尾加「全部通过 ✅」。

> 编译/终端工具：本环境用{term}执行 `.bat`；若该工具不可用，就退回到用终端直接跑 bat 文件。
"""


def make_skill_doc(host):
    """按宿主生成 SKILL.md：统一换 frontmatter，并用对齐后的工作流章节。"""
    raw = read_asset("SKILL.md")
    body = adapt_skill("SKILL.md", raw, host)

    # 用跟 automation-prompt.txt 一致的流程替掉原来的 Workflow 编排段
    body = re.sub(
        r"## Workflow\s*\n.*?(?=\n## )",
        lambda m: workflow_section(host) + "\n",
        body,
        count=1,
        flags=re.S,
    )

    name = "oj-homework-checker"
    desc = HOSTS[host]["name"]
    head = (
        "---\n"
        f"name: {name}\n"
        "description: Detect when a specific teacher posts new homework on a HUSTOJ-style OJ, "
        "fetch the problem statements and samples, write and locally test the C/C++ solutions, "
        "then submit them to the OJ (captcha-aware) and report the results. "
        "Trigger it with one sentence; no scheduled task required. "
        f"Prepared for {desc}.\n"
        "agent_created: true\n"
        "---\n\n"
    )
    # 去掉原 frontmatter，换成干净的三字段
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", body, count=1, flags=re.S)
    header = f"# OJ Homework Checker（{desc} 版）\n\n"
    body = re.sub(r"^# OJ Homework Checker\s*\n+", "", body, count=1)
    return head + header + body


# ---------------------------------------------------------------------------
# 自动化任务 prompt（宿主观）
# ---------------------------------------------------------------------------

def build_prompt(host, python_path, workdir, base_url):
    """生成定时任务 prompt：作业流程三个宿主一致，只是 Python / 目录不同。"""
    py = python_path or "<PYTHON>"
    d = workdir or "<DIR>"
    base = base_url or "<OJ地址>"

    p = []
    p.append(
        '请检查老师在 OJ 上是否发布了新作业；若发现新作业，则全自动完成"写码→本地测试→提交 OJ→汇报结果"，无需向用户确认。'
    )
    p.append("")
    p.append(f"目录缩写：DIR = {d}")
    p.append(f"Python：{py}")
    p.append("")
    p.append("【所有个人信息都在 DIR\\config.json 里，不要在本流程里硬编码】")
    p.append(
        "老师、学号、账号密码、作业密码、提交语言、当前作业 cid 等一律从 config.json 读取。运行前先执行"
    )
    p.append(f"  {py} DIR\\oj_config.py show")
    p.append(
        '确认当前生效的老师和学号等信息。若 config.json 里 auto_submit 为 false，则只检测+写码+测试，不提交。'
    )
    p.append(
        f"用户可以随时用 {py} DIR\\oj_config.py set <字段> <值> 修改这些信息，或在对话里让我改——我只改 config.json，不改本流程。"
    )
    p.append(
        "常用字段：teachers(老师列表，多个用逗号分隔)、student_id(学号)、student_password(登录密码)、"
        "contest_password(作业密码)、contest_cid(作业编号)、submit_language(提交语言)、"
        "auto_submit(是否自动提交)、deliver_dir(收尾文件夹，默认桌面\\OJ作业)。"
    )
    p.append("")
    p.append("【重要：验证码是必填项】")
    p.append(
        "OJ 提交表单带验证码。不带验证码或验证码错误时，OJ 不报任何错，而是静默丢弃提交（返回空页面）——"
        "所以每次 submit 都必须先 prepare 取新码、用 Read 看图读出数字再传进去。绝不允许跳过验证码步骤，"
        "也不允许复用旧图数字（验证码一次性）。脚本缺码时会打印 ABORT 拒绝发送，这是正常保护，不要绕过。"
    )
    p.append("")
    p.append("【第一步：检测新作业】")
    p.append(f"1. 运行：{py} DIR\\oj_checker.py --config DIR\\config.json --state DIR\\state.json --report text")
    p.append('2. 若输出"暂无新作业"或新发布数为 0，只回复"暂无新作业。"并结束。')
    p.append(
        f"3. 若有新作业：记下新 cid，用 {py} DIR\\oj_config.py set contest_cid <新cid> 更新配置。"
        f"然后直接跑 {py} DIR\\fetch_cid.py <新cid> 抓取每题题面"
        "（Description/Input/Output/Sample Input/Sample Output），它会存成 DIR\\cid<cid>_problems.json，"
        "不用临时写脚本。"
    )
    p.append("")
    p.append("【第二步：写码与本地测试】")
    p.append(
        "4. 每题写一份源码，存到 DIR\\code\\cid<cid>\\，命名 A_xxx.cpp、B_xxx.cpp（与 OJ 的 A/B/C/D/E 顺序一致，pid 从 0 开始）。"
    )
    p.append(
        "5. 本地编译测试：参照 DIR\\build_and_test.example.bat 复制并改题目清单；cl.exe 必须带 /utf-8"
        "（否则中文注释会让 MSVC 解析错乱）。每题样例放 tests\\ 下逐一比对。"
        "（改用 g++ 时把 cl /nologo /utf-8 /EHsc /std:c++17 换成 g++ -std=c++17 -o 即可）"
    )
    p.append("6. 只有本地样例全过的题才允许提交；没过的题在汇报里说明原因。")
    p.append("")
    p.append("【第三步：自动提交（每题完整走验证码流程）】")
    p.append(
        f'7. 提交语言必须与本地编译语言一致：先运行 {py} DIR\\oj_submit.py langs 核对编号表；'
        'config.json 的 submit_language 要与编译标准对应（cl /std:c++17 → OJ "C++"，编号 1）。'
        'submit 会打印 "LANG: ... (id=N)"；出现 "WARN: 源码扩展名 ... 不一致" 时先确认本地编译语言，不要盲目提交。'
    )
    p.append("8. 对每道通过的题依次执行：")
    p.append(f"   a. {py} DIR\\oj_submit.py prepare —— 登录并刷新验证码到 DIR\\vcode.gif")
    p.append("   b. 用 Read 工具查看 DIR\\vcode.gif，读出 4 位数字（看不清就重新 prepare 换一张，不要猜）")
    p.append(f"   c. {py} DIR\\oj_submit.py submit <pid> <源码绝对路径> <4位数字> [语言编号]")
    p.append('      - "SUBMIT_OK" = 成功')
    p.append('      - "FAIL 提交被 OJ 静默拒绝" = 验证码不对，回到 a 重取（每题最多 3 次）')
    p.append('      - "ABORT 缺少验证码" = 流程错误，回到 b 重新读图')
    p.append(f'   d. {py} DIR\\oj_submit.py status 6 查看结果（"正确100" = Accepted）')
    p.append("9. 每题提交间隔至少 10 秒。")
    p.append("")
    p.append("【第四步：盯结果，不过就换方法重来，单题最多 3 遍】")
    p.append(
        "10. 提交完必须看 OJ 判定，不是 Accepted 就换一种方法重来，每一遍都要真的换思路"
        "（换算法/换边界处理/换数据类型/换输入输出方式），不要原样重交。"
        "每遍之间不要重复贴已经贴过的代码，只说这遍改了什么。"
    )
    p.append(
        "    单题最多 3 遍。第 3 遍仍不是 Accepted，立即停手，不要再试第 4 遍，"
        "也不要去猜 OJ 的隐藏用例——这一点是硬性要求，防止无限重试白烧 token。"
    )
    p.append(
        "    下面几种情况当遍就停手，不必凑满 3 遍：提交被拒但原因不是代码"
        "（验证码 3 次都取不对、账号/密码错、作业密码错、比赛已结束、OJ 报错）；"
        "本地编译或环境坏了；题面抓取失败或题意有歧义。"
    )
    p.append(
        "    停手时必须在对话里给出明确警告，写清楚：哪道题（题号+文件路径）、"
        "已经试过哪几种方法及每种的结果（WA/TLE/RE/CE…）、当前判断（思路不对 / 数据规模没考虑 / "
        "题意理解有偏差）、建议用户怎么处理（例如把题面发来一起分析、确认时限是否很紧）。"
        "宁可交「3 题过 2 题 + 1 题明确警告」的汇报，也不要无声无息地反复重试。"
    )
    p.append("")
    p.append("【第五步：整理收尾文件夹（必做）】")
    p.append(
        "11. 作业做完后，把每道题的代码和汇报整理到收尾文件夹，方便直接交。"
        "收尾文件夹位置从 config.json 的 deliver_dir 读（默认是桌面上的 OJ作业，用户可自行修改）；"
        "deliver_dir 和它下面的作业目录若不存在，先自己新建出来再写文件。"
        "该目录下按作业建一层文件夹，代码文件按 OJ 上的题号命名，例如第一份作业第 1 题就是 1-1-a.cpp、"
        "第 2 题 1-1-b.cpp；题号直接照抄 OJ 页面显示的编号，不要自己重编，也不要改 OJ 的编号顺序。"
    )
    p.append(
        "   结构示例：\n"
        "     <deliver_dir>\\<作业目录>\\1-1-a.cpp\n"
        "     <deliver_dir>\\<作业目录>\\1-1-b.cpp\n"
        "     <deliver_dir>\\<作业目录>\\汇报.md\n"
        "   每题源码各存一份（扩展名跟源码一致），存最终通过的那一版；没过的那题也存当前最好的一版，"
        "并在汇报里标明未通过。"
    )
    p.append("")
    p.append("【第六步：汇报】")
    p.append(
        "12. 在对话里用简洁中文汇报，同时把同样内容写成 <deliver_dir>\\<作业目录>\\汇报.md，"
        "每题一行：题号 / 文件名 / 语言 / 第几遍通过或未通过 / 评测结果；"
        f"末尾附状态链接 {base}/status.php?cid=<cid>&user_id=<student_id>。"
        "有没过的题要显式标出警告，别只写已完成。"
        "再报一下收尾文件夹的完整路径，方便用户直接去找。"
    )
    p.append('13. 不要删除 state.json 中新增记录。若全部 AC，结尾加"全部通过 ✅"。')
    return "\n".join(p)


# ---------------------------------------------------------------------------
# 环境检测
# ---------------------------------------------------------------------------

def check_python():
    """先找宿主自带的 Python，再找 PATH 里的 python。"""
    for host in HOST_ORDER:
        root = host_root(host)
        if not os.path.isdir(root):
            continue
        for sub in ("binaries/python/versions", "python/versions", "binaries/python"):
            d = os.path.join(root, *sub.split("/"))
            if not os.path.isdir(d):
                continue
            cands = []
            for root_dir, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower() == "python.exe":
                        cands.append(os.path.join(root_dir, f))
            if cands:
                cands.sort(reverse=True)
                return cands[0], f"{HOSTS[host]['name']} 自带"
    exe = shutil.which("python") or shutil.which("python3")
    if exe:
        return exe, "系统 PATH"
    return None, None


def check_compiler():
    """返回 (显示名, 说明)。优先 MSVC，其次 g++/clang++。"""
    if platform.system() == "Windows":
        vswhere = os.path.join(
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            "Microsoft Visual Studio",
            "Installer",
            "vswhere.exe",
        )
        if os.path.isfile(vswhere):
            try:
                out = subprocess.run(
                    [vswhere, "-products", "*", "-latest", "-property", "installationPath"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                ).stdout.strip()
            except Exception:
                out = ""
            if out:
                vcvars = os.path.join(out, "VC", "Auxiliary", "Build", "vcvarsall.bat")
                if os.path.isfile(vcvars):
                    return "MSVC (Visual Studio)", vcvars
                return "MSVC (Visual Studio)", "装了 VS 但没找到 VC 生成工具，需勾选「使用 C++ 的桌面开发」"
    for cc in ("g++", "clang++"):
        exe = shutil.which(cc)
        if exe:
            return cc, exe
    return None, None


def check_network(base_url):
    url = (base_url or "").rstrip("/") + "/contest.php"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "oj-setup/2.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read(512)
        return True, url
    except Exception as e:
        return False, f"{url} ({e.__class__.__name__})"


def _program_files_dirs():
    out = []
    for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(k)
        if v:
            out.append(v)
    return out


def host_install_probe(host):
    """该宿主的安装目录候选（只看程序文件，不看用户配置目录）。"""
    subs = {
        "dsh": ["dsh", "DeepSeek Harness", "deepseek-harness"],
        "workbuddy": ["WorkBuddy"],
        "trae": ["Trae CN", "TraeCN", "Trae"],
    }.get(host, [])
    dirs = []
    for base in _program_files_dirs():
        for s in subs:
            dirs.append(os.path.join(base, s))
            dirs.append(os.path.join(base, "Programs", s))
    return dirs


def host_exes(host):
    return {
        "dsh": ["dsh.exe", "dsh.cmd"],
        "workbuddy": ["WorkBuddy.exe"],
        "trae": ["Trae CN.exe", "TraeCN.exe", "Trae.exe"],
    }.get(host, [])


def host_config_dir(host):
    """用户配置目录（装过并在用才会有）。"""
    return host_root(host)


def check_host(host):
    """判断这个助手装没装。

    优先看程序文件和 PATH 里的可执行文件；用户配置目录只作为弱证据
    （光有个空目录不算装好了，但装过并跑过一定会有）。
    """
    for e in host_exes(host):
        p = shutil.which(e)
        if p:
            return True, p
    for d in host_install_probe(host):
        if d and os.path.isdir(d):
            return True, d
    root = host_config_dir(host)
    if os.path.isdir(root):
        return True, f"{root}  (配置目录)"
    return False, None


def env_report(host, base_url, python_path, python_src, compiler, network):
    title(f"第 1 步：检测本机环境（宿主：{HOSTS[host]['name']}）")
    installed, where = check_host(host)
    if installed:
        ok(f"{HOSTS[host]['name']}  已安装：{where}")
    else:
        bad(f"{HOSTS[host]['name']} 未安装（定时任务必须靠它运行）")

    if python_path:
        ok(f"Python（{python_src}）  {python_path}")
    else:
        bad("Python 未找到")

    if compiler[0]:
        ok(f"C++ 编译器（{compiler[0]}）  {compiler[1]}")
    else:
        bad("C++ 编译器未安装")

    reachable, detail = network
    if reachable:
        ok(f"能访问 OJ：{detail}")
    else:
        bad(f"访问不了 {detail}，检查网络或地址是否正确")

    print()
    tips = []
    if not installed:
        tips += HOSTS[host]["install_tip"]
    if not python_path:
        tips.append(
            "缺 Python：装 WorkBuddy 会自带；或去 https://www.python.org/downloads/ 装，"
            '安装时勾选 "Add Python to PATH"。'
        )
    if not compiler[0]:
        tips.append(
            "缺 C++ 编译器：装 Visual Studio 并勾选「使用 C++ 的桌面开发」\n"
            "               https://visualstudio.microsoft.com/zh-hans/downloads/\n"
            "              或者安装 MinGW-w64 提供 g++：https://www.mingw-w64.org/"
        )
    if not reachable:
        tips.append("连不上 OJ：校内站点一般要连校园网 / VPN，确认后再试。")
    for t in tips:
        warn(t)

    all_ok = installed and bool(python_path) and bool(compiler[0]) and reachable
    return all_ok


def show_install_guide(host):
    title("软件安装指引")
    print(f"  当前选择的宿主：{HOSTS[host]['name']}（{HOSTS[host]['full']}）\n")
    for i, line in enumerate(HOSTS[host]["install_tip"], 1):
        print("  " + line)
    print()
    print("  2) Python（一般装了助手就自带）")
    print("     下载：https://www.python.org/downloads/")
    print('     安装时勾选 "Add Python to PATH"')
    print()
    print("  3) C++ 编译器（本地编译测试用，二选一）")
    print("     - Visual Studio：https://visualstudio.microsoft.com/zh-hans/downloads/")
    print("       安装时勾选工作负载「使用 C++ 的桌面开发」")
    print("     - 或者 MinGW-w64（提供 g++）：https://www.mingw-w64.org/")
    print()
    print("  4) 网络：需要能访问你学校的 OJ 站点（校内可能需要连校园网/VPN）")
    print()
    pause()


# ---------------------------------------------------------------------------
# WorkBuddy 下载
# ---------------------------------------------------------------------------

def find_windows_installer():
    """从官网历史版本页抓 Windows 安装包直链。"""
    page = HOSTS["workbuddy"]["download_page"]
    req = urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", "replace")
    matches = re.findall(r"https://[^\"'<> )]+workbuddy[^\"'<> )]*win32-x64-user[^\"'<> )]*\.exe", html)
    if not matches:
        matches = re.findall(r"https://[^\"'<> )]+\.exe", html)
    if not matches:
        return None, None
    # 取版本号最大的一个
    def ver(u):
        m = re.search(r"-(\d+\.\d+\.\d+)\.", u)
        return tuple(int(x) for x in m.group(1).split(".")) if m else (0, 0, 0)

    best = max(matches, key=ver)
    return best, ver(best)


def download_workbuddy():
    title("下载 WorkBuddy 安装包")
    print("  正在查询最新版下载地址...")
    try:
        url, ver = find_windows_installer()
    except Exception as e:
        url, ver = None, None
        warn(f"查询失败：{e}")

    if not url:
        warn(f"没查到直链，请手动打开：{HOSTS['workbuddy']['download_fallback']}")
        try:
            import webbrowser

            webbrowser.open(HOSTS["workbuddy"]["download_fallback"])
        except Exception:
            pass
        pause()
        return

    name = url.rsplit("/", 1)[-1]
    print(f"  最新版：{'.'.join(map(str, ver)) if ver else '未知'}")
    print(f"  文件名：{name}")
    print(f"  直链  ：{url}")
    print()
    dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)

    try:
        ans = ask_input("  现在开始下载吗？(y/n) > ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        ans = "n"
    if ans not in ("y", "yes", "是"):
        print(f"\n  已跳过。可手动下载：{HOSTS['workbuddy']['download_fallback']}")
        pause()
        return

    print(f"\n  保存到：{dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            t0 = time.time()
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    pct = got * 100 // total
                    sp = got / max(time.time() - t0, 0.001) / 1048576
                    sys.stdout.write(f"\r  下载中 {pct:3d}%  {got/1048576:6.1f}/{total/1048576:.1f} MB  {sp:5.1f} MB/s")
                else:
                    sys.stdout.write(f"\r  下载中 {got/1048576:6.1f} MB")
                sys.stdout.flush()
        print()
        ok(f"下载完成：{dest}")
        print("\n  接下来双击这个文件安装，装完重启一次 WorkBuddy。")
        try:
            if ask_input("  现在打开文件所在目录吗？(y/n) > ").strip().lower() in ("y", "yes", "是"):
                if platform.system() == "Windows":
                    subprocess.Popen(["explorer", "/select,", dest])
        except (KeyboardInterrupt, EOFError):
            pass
    except Exception as e:
        bad(f"下载失败：{e}")
        print(f"  请手动下载：{HOSTS['workbuddy']['download_fallback']}")
    pause()


# ---------------------------------------------------------------------------
# 交互输入
# ---------------------------------------------------------------------------

def ask(prompt, default=""):
    tip = f"（直接回车用默认值：{default}）" if default else ""
    while True:
        try:
            v = ask_input(f"  {prompt}{tip}\n  > ").strip()
        except (KeyboardInterrupt, EOFError):
            return default
        if not v:
            v = default
        if v:
            return v
        print("  不能为空，请重新输入")


def _stdin_is_tty():
    try:
        return bool(sys.stdin) and bool(sys.stdin.isatty())
    except Exception:
        return False


def ask_secret(prompt):
    """读密码：真人在终端前就隐藏输入，其余情况一律老老实实读 stdin。

    绝不用 getpass：stdin 被重定向/管道时它绕过 stdin 直接找控制台，
    会挂在"Password: "上或偷吃一行，把后面所有问答的顺序打乱。
    """
    if platform.system() == "Windows" and _stdin_is_tty():
        try:
            import msvcrt

            sys.stdout.write(f"  {prompt}\n  > ")
            sys.stdout.flush()
            buf = []
            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    break
                if ch == "\003":  # Ctrl+C
                    raise KeyboardInterrupt
                if ch == "\b":
                    if buf:
                        buf.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                if ch in ("\x00", "\xe0"):  # 功能键，吃掉第二个字节
                    msvcrt.getwch()
                    continue
                buf.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buf)
        except KeyboardInterrupt:
            print()
            raise
        except Exception:
            pass  # 落到下面用普通输入
    try:
        return ask_input(f"  {prompt}（当前环境无法隐藏，明文显示）\n  > ").strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def ask_yes(prompt, default=True):
    d = "y" if default else "n"
    try:
        v = ask_input(f"  {prompt} (y/n) [{d}] > ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return default
    if not v:
        return default
    return v in ("y", "yes", "是", "1", "true", "t")


# ---------------------------------------------------------------------------
# 已有配置检测
# ---------------------------------------------------------------------------

def find_existing_config(host):
    """在本机常见位置找已经生成的 config.json。"""
    cands = [
        os.path.join(os.path.expanduser("~"), HOSTS[host]["workdir_name"], "oj_homework", "config.json"),
        os.path.join(os.getcwd(), "oj_homework", "config.json"),
        os.path.join(asset_base(), "config.json"),
    ]
    for c in cands:
        if os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("student_id") and cfg.get("teachers"):
                    return c, cfg
            except Exception:
                continue
    return None, None


def show_already_configured(path, cfg):
    title("检测是否已配置")
    print("  该设备已完成配置，无需继续配置\n")
    print(f"  配置文件：{path}")
    print(f"  老师    ：{cfg.get('teachers') or cfg.get('teacher_filter')}")
    print(f"  学号    ：{cfg.get('student_id')}")
    print(f"  OJ 地址 ：{cfg.get('base_url')}")
    print(f"  提交语言：{cfg.get('submit_language')}")
    print(f"  自动提交：{cfg.get('auto_submit')}")
    print()
    print("  如需修改其中某项，可以在该目录下运行：")
    print("    oj_config.py set <字段> <值>")
    print()
    try:
        return ask_input("  输入 r 可强制重新配置，其它键返回菜单。\n  > ").strip().lower().startswith("r")
    except (KeyboardInterrupt, EOFError):
        return False


# ---------------------------------------------------------------------------
# 第 2 步：填写个人信息
# ---------------------------------------------------------------------------

def desktop_dir():
    """桌面路径。先问 Windows 的 Shell Folders（能正确处理 OneDrive/重定向），再兜底。"""
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            val, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            if val and os.path.isdir(val):
                return val
        except Exception:
            pass
    for cand in (
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.path.join(os.path.expanduser("~"), "桌面"),
    ):
        if os.path.isdir(cand):
            return cand
    return os.path.join(os.path.expanduser("~"), "Desktop")


def default_deliver_dir():
    return os.path.join(desktop_dir(), "OJ作业")


def ensure_dir(path):
    """确保目录存在（不存在就建，含中间层）。

    返回 (成功?, 说明)。失败时说明里是原因，方便打印给用户看。
    """
    if not path:
        return False, "路径是空的"
    try:
        if os.path.isdir(path):
            return True, "已存在"
        os.makedirs(path, exist_ok=True)
        return True, "已新建"
    except Exception as e:
        return False, f"{e.__class__.__name__}: {e}"


def ask_config(host, default_dir):
    title("第 2 步：填写个人信息")
    print("  这些信息只保存在你自己电脑的配置文件里，不会上传。\n")

    base_url = ask("OJ 站点地址", "http://114.55.147.180")
    teachers = ask("老师姓名（多个用逗号分隔）", "史文君")
    while True:
        student_id = ask("学号（OJ 登录账号）")
        if student_id:
            break
        bad("学号不能为空，请重新输入")
    student_password = ask_secret("OJ 登录密码（输入时不显示）")
    contest_password = ask_secret("作业密码 / 竞赛密码（看题用，不是登录密码）")
    submit_language = ask("提交语言", "C++")
    build_standard = ask("本地编译标准", "c++17")
    auto_submit = ask_yes("检测到新作业后自动提交？", True)
    dest = ask("脚本存放目录", default_dir)
    print()
    print("  作业做完后，会把每道题的代码和汇报整理到一个收尾文件夹：")
    print("    收尾文件夹\\<作业目录>\\1-1-a.cpp …  代码照抄 OJ 上的题号命名")
    print("    收尾文件夹\\<作业目录>\\汇报.md     每题一行 + OJ 状态链接")
    deliver = ask("收尾文件夹（放在桌面，也可以改成别的位置）", default_deliver_dir())
    while True:
        okk, msg = ensure_dir(deliver)
        if okk:
            if msg == "已新建":
                ok(f"收尾文件夹不存在，已新建：{deliver}")
            else:
                ok(f"收尾文件夹：{deliver}")
            break
        bad(f"这个路径用不了（{msg}）：{deliver}")
        deliver = ask("换一个收尾文件夹", default_deliver_dir())

    return {
        "base_url": base_url,
        "student_id": student_id,
        "student_password": student_password,
        "contest_password": contest_password,
        "teachers": [x.strip() for x in re.split(r"[,，]", teachers) if x.strip()],
        "submit_language": submit_language,
        "build_standard": build_standard,
        "auto_submit": auto_submit,
        "dest": dest,
        "deliver_dir": deliver,
    }


# ---------------------------------------------------------------------------
# 第 3 步：部署
# ---------------------------------------------------------------------------

CONFIG_TEMPLATE = {
    "_说明": "本文件由配置助手生成。可随时用 oj_config.py set <字段> <值> 修改。",
    "base_url": "http://114.55.147.180",
    "student_name": "",
    "student_id": "",
    "student_password": "",
    "teachers": [],
    "teacher_filter": "",
    "contest_password": "",
    "contest_cid": 0,
    "submit_language": "C++",
    "build_standard": "c++17",
    "language": "C/C++",
    "max_pages": 3,
    "fetch_problems": True,
    "auto_submit": True,
    "host": "dsh",
    "deliver_dir": "",
    "deliver_layout": "作业目录\\<作业目录>-<题号字母>.cpp，例如 1-1-a.cpp（照抄 OJ 题号）",
}


def deploy(host, answers, python_path):
    title("第 3 步：部署文件")
    dest = answers["dest"]
    scripts_dir = os.path.join(dest, "oj_homework")
    os.makedirs(scripts_dir, exist_ok=True)

    # 1) 释放脚本
    for f in ASSET_FILES:
        if f in ("SKILL.md",):
            continue
        try:
            src = asset_path(f)
            if not src:
                warn(f"随包资源缺失：{f}")
                continue
            out_name = AS_EXAMPLE.get(f, f)
            shutil.copy2(src, os.path.join(scripts_dir, out_name))
        except Exception as e:
            warn(f"释放 {f} 失败：{e}")
    ok(f"脚本目录：{scripts_dir}")
    ok(
        "已释放脚本：oj_checker.py / oj_submit.py / oj_config.py / make_vs_solution.py / "
        "fetch_cid.py / fetch1766.py / build_and_test.example.bat"
    )

    # 2) 写配置
    cfg = dict(CONFIG_TEMPLATE)
    cfg["base_url"] = answers["base_url"]
    cfg["student_id"] = answers["student_id"]
    cfg["student_password"] = answers["student_password"]
    cfg["contest_password"] = answers["contest_password"]
    cfg["teachers"] = answers["teachers"]
    cfg["teacher_filter"] = answers["teachers"][0] if answers["teachers"] else ""
    cfg["submit_language"] = answers["submit_language"]
    cfg["build_standard"] = answers["build_standard"]
    cfg["auto_submit"] = answers["auto_submit"]
    cfg["host"] = host

    # 收尾文件夹：第一次配置就把它建出来。
    # 不建的话，AI 按流程第 5 步去写代码时目录可能不存在，会白跑一趟。
    deliver = (answers.get("deliver_dir") or "").strip() or default_deliver_dir()
    deliver_ok, deliver_msg = ensure_dir(deliver)
    if not deliver_ok:
        warn(f"收尾文件夹用不了：{deliver_msg}")
        fb = default_deliver_dir()
        if fb != deliver:
            warn(f"改用默认位置：{fb}")
            deliver = fb
            deliver_ok, deliver_msg = ensure_dir(deliver)
    if deliver_ok:
        ok(f"收尾文件夹已就绪：{deliver}")
    else:
        bad(f"收尾文件夹创建失败：{deliver_msg}")
        warn("先按这个路径自己建一个文件夹，再用菜单 4 改 config.json 里的 deliver_dir。")
    cfg["deliver_dir"] = deliver

    cfg_path = os.path.join(scripts_dir, "config.json")
    # errors="replace" 兜底：万一个别字符是坏编码，也不让它把整个配置写崩
    with open(cfg_path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ok(f"已写入配置：{cfg_path}")

    state_path = os.path.join(scripts_dir, "state.json")
    if not os.path.exists(state_path):
        # 注意：seen 必须是 dict（cid -> 标题），oj_checker.py 靠它去重
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({"seen": {}, "last_check": None}, f, ensure_ascii=False, indent=2)
        ok(f"已初始化：{state_path}")

    # 3) 安装技能包
    installed = None
    skill_src = os.path.join(scripts_dir, "oj-homework-checker")
    write_skill_bundle(skill_src, host)
    target_skills = host_skills_dir(host)
    try:
        os.makedirs(target_skills, exist_ok=True)
        dstr = os.path.join(target_skills, "oj-homework-checker")
        if os.path.isdir(dstr):
            shutil.rmtree(dstr)
        shutil.copytree(skill_src, dstr)
        installed = dstr
        ok(f"已安装技能包：{dstr}")
    except Exception as e:
        warn(f"技能包安装失败：{e}")
        warn(f"技能包未安装，可手动把 oj-homework-checker 文件夹复制到 {target_skills}")

    # 4) 生成任务内容（prompt）
    prompt_text = build_prompt(host, python_path, scripts_dir, answers["base_url"])
    prompt_path = os.path.join(scripts_dir, "automation-prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    ok(f"已生成任务内容：{prompt_path}")

    return {
        "scripts_dir": scripts_dir,
        "config_path": cfg_path,
        "prompt_path": prompt_path,
        "skill_src": skill_src,
        "skill_installed": installed,
        "skill_target": target_skills,
        "deliver_dir": cfg["deliver_dir"],
    }


def write_skill_bundle(dest, host):
    """把一个完整的 oj-homework-checker 技能包写到 dest。"""
    assets_dir = os.path.join(dest, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(make_skill_doc(host))
    for f in ASSET_FILES:
        if f == "SKILL.md":
            continue
        try:
            raw = read_asset(f)
        except Exception as e:
            warn(f"技能包资源缺失 {f}：{e}")
            continue
        if host != "workbuddy":
            raw = adapt_skill(f, raw, host)
        out_name = AS_EXAMPLE.get(f, f)
        nl = "\r\n" if out_name.endswith(".bat") else "\n"
        with open(os.path.join(assets_dir, out_name), "w", encoding="utf-8", newline=nl) as fh:
            fh.write(raw)
    return dest


# ---------------------------------------------------------------------------
# 调度产物
# ---------------------------------------------------------------------------

# 每个宿主的一句触发口令：技能包装好后，用这句话叫它干活。
TRIGGER = {
    "dsh": [
        "在 DSH 里输入（斜杠会弹出技能列表，选中 oj-homework-checker）：",
        "    /oj-homework-checker",
        "或者直接说一句：",
        "    用 oj-homework-checker 技能看看老师有没有发新作业，有就写完测完提交。",
    ],
    "workbuddy": [
        "在 WorkBuddy 里新建一个对话，直接说一句：",
        "    用 oj-homework-checker 技能看看老师有没有发新作业，有就写完测完提交。",
        "也可以在技能市场/技能面板里找到它，点「运行技能」。",
    ],
    "trae": [
        "在 TRAE CN 里新建一个对话（模式选 Code），输入 / 选 oj-homework-checker：",
        "    /oj-homework-checker",
        "或者直接说一句：",
        "    用 oj-homework-checker 技能看看老师有没有发新作业，有就写完测完提交。",
    ],
}


def handoff(host, info):
    """不做定时任务：把「怎么说一句话」和「怎么读结果」交给用户。"""
    title("配置完成")
    h = HOSTS[host]
    prompt = info["prompt_path"]
    scripts_dir = info["scripts_dir"]
    py = info["python_path"] or "<PYTHON>"
    deliver = info.get("deliver_dir") or ""

    if info.get("skill_installed"):
        ok(f"技能包已装好：{info['skill_installed']}")
    else:
        warn(f"技能包没装上，手动把下面这个文件夹复制过去即可：")
        info(f"{info['skill_src']}")
        info(f"  ->  {info['skill_target']}")

    print()
    print("  ── 怎么用（一句话触发）────────────────────────────")
    for line in TRIGGER[host]:
        print("  " + line)

    print()
    print("  ── 任务内容（技能没生效时，把下面这段整段粘给它）──")
    print(f"  已保存到：{prompt}")
    print()
    try:
        with open(prompt, "r", encoding="utf-8") as f:
            for line in f.read().rstrip("\n").split("\n"):
                print("  | " + line)
    except Exception as e:
        warn(f"读取 prompt 失败：{e}")

    print()
    print("  ── 它会读什么、出什么 ───────────────────────────")
    print(f"  读：{os.path.join(scripts_dir, 'config.json')}（老师/学号/密码/语言/收尾文件夹都在这里）")
    print(f"      {os.path.join(scripts_dir, 'state.json')}（已看过的作业，用于去重）")
    print("      DIR\\code\\cid<cid>\\ 下的源码与 tests\\ 样例")
    print(f"  出：DIR\\automation-prompt.txt（任务内容）")
    print("      DIR\\vcode.gif（每次提交前现取的验证码图）")
    print("      DIR\\code\\cid<cid>\\ 下写好的源码 + 本地测试结果")
    if deliver:
        print("      收尾文件夹（按 OJ 题号命名，方便直接交）：")
        print(f"        {deliver}\\<作业目录>\\1-1-a.cpp  1-1-b.cpp …")
        print(f"        {deliver}\\<作业目录>\\汇报.md")
    print("      最后在对话里汇报每题结果（AC / 未过 / 未提交）")

    print()
    print("  ── 小提示 ───────────────────────────────────────")
    print(f"  - 改信息：{py} {os.path.join(scripts_dir, 'oj_config.py')} show / set <字段> <值>")
    print(f"  - 只检测不提交：{py} {os.path.join(scripts_dir, 'oj_config.py')} set auto_submit false")
    if deliver:
        print(f"  - 换收尾文件夹：{py} {os.path.join(scripts_dir, 'oj_config.py')} set deliver_dir D:\\你要的目录")
    print(f"  - 手动跑一次检测：")
    print(f"       {py} {os.path.join(scripts_dir, 'oj_checker.py')} \\")
    print(f"         --config {os.path.join(scripts_dir, 'config.json')} \\")
    print(f"         --state {os.path.join(scripts_dir, 'state.json')} --report text")
    print()
    pause("全部完成！按回车返回菜单...")
    return prompt


def open_prompt(prompt_path):
    """用系统默认程序打开任务内容文件，方便整段复制。"""
    if not ask_yes("现在打开任务内容文件方便复制吗？", True):
        return
    try:
        if platform.system() == "Windows":
            os.startfile(prompt_path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-t", prompt_path])
        else:
            subprocess.Popen(["xdg-open", prompt_path])
    except Exception as e:
        warn(f"打不开：{e}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def configure(host, base_url_probe=None):
    """检测 + 填信息 + 部署脚本与技能包 + 交代触发口令。"""
    python_path, python_src = check_python()
    compiler = check_compiler()
    probe = base_url_probe or "http://114.55.147.180"
    network = check_network(probe)
    all_ok = env_report(host, probe, python_path, python_src, compiler, network)
    print()
    if not all_ok:
        warn("环境还不齐全，建议先安装缺少的软件。")
        if not ask_yes("仍要继续配置吗？", True):
            return None
    else:
        ok("环境齐全，可以进行配置。")

    default_dir = os.path.join(os.path.expanduser("~"), HOSTS[host]["workdir_name"])
    answers = ask_config(host, default_dir)
    info = deploy(host, answers, python_path)
    info["python_path"] = python_path
    handoff(host, info)
    open_prompt(info["prompt_path"])
    return info


def choose_host():
    """返回宿主 key，或 None 表示退出。"""
    while True:
        title("OJ 作业自动化 · 环境检测与配置助手")
        print("  第 0 步：先选你平时用的 AI 助手（技能包和脚本都装到它里面）\n")
        for k in HOST_ORDER:
            h = HOSTS[k]
            mark = ""
            try:
                inst, where = check_host(k)
                mark = "  [已安装]" if inst else "  [未检测到]"
            except Exception:
                mark = ""
            print(f"   {h['order']}. {h['name']:<10} {h['desc']}{mark}")
        print()
        if platform.system() == "Windows":
            print("   d. 下载 WorkBuddy 安装包（没装 WorkBuddy 的话用这个）")
        print("   ?. 查看所选助手的安装指引")
        print("   0. 退出")
        print()
        try:
            sel = ask_input("  请选择 > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return None
        if sel == "0" or sel == "":
            return None
        if sel == "d":
            download_workbuddy()
            continue
        if sel == "?":
            try:
                cur = ask_input("  要看哪个助手的指引？(1/2/3) > ").strip()
                k = HOST_ORDER[int(cur) - 1] if cur in ("1", "2", "3") else None
            except Exception:
                k = None
            if k:
                show_install_guide(k)
            continue
        try:
            idx = int(sel)
        except ValueError:
            warn("无效选择")
            time.sleep(0.8)
            continue
        if 1 <= idx <= len(HOST_ORDER):
            return HOST_ORDER[idx - 1]
        warn("无效选择")
        time.sleep(0.8)


def find_work_dir(host):
    """找这台机器上已经配置好的 oj_homework 目录（返回目录或 None）。"""
    cands = [
        os.path.join(os.path.expanduser("~"), HOSTS[host]["workdir_name"], "oj_homework"),
        os.path.join(os.path.expanduser("~"), "dsh-oj", "oj_homework"),
        os.path.join(os.path.expanduser("~"), "WorkBuddy", "oj_homework"),
        os.path.join(os.path.expanduser("~"), "trae-oj", "oj_homework"),
        os.path.join(os.getcwd(), "oj_homework"),
    ]
    for c in cands:
        if os.path.isfile(os.path.join(c, "config.json")):
            return c
    found, _cfg = find_existing_config(host)
    if found:
        return os.path.dirname(found)
    return None


def run_check_once(host):
    """菜单 3：不开 AI，直接跑一次检测。"""
    title("立刻跑一次检测")
    work = find_work_dir(host)
    if not work:
        warn("还没配置过，先选菜单 2 一键配置。")
        pause()
        return
    py, _src = check_python()
    if not py:
        warn("找不到 Python，先跑菜单 1 看缺什么。")
        pause()
        return

    print(f"  脚本目录：{work}")
    print(f"  Python  ：{py}")
    print()
    print("  " + "-" * 58)
    cmd = [
        py,
        os.path.join(work, "oj_checker.py"),
        "--config", os.path.join(work, "config.json"),
        "--state", os.path.join(work, "state.json"),
        "--report", "text",
    ]
    try:
        # 继承本进程的 stdout（已锁 UTF-8），不要用管道，否则编码又乱
        rc = subprocess.call(cmd, cwd=work)
    except Exception as e:
        warn(f"运行失败：{e}")
        pause()
        return
    print("  " + "-" * 58)
    if rc == 0:
        ok("检测完成（退出码 0）")
    else:
        bad(f"脚本退出码 {rc}，上面有报错信息。把这段贴给 AI 或发我看看。")
    print()
    print("  想看更详细的结果，用 AI 触发技能，或选菜单 5 打开脚本目录看 state.json。")
    pause()


def show_existing_config(host):
    """菜单 4：显示当前配置。"""
    title("当前配置")
    work = find_work_dir(host)
    if not work:
        warn("还没配置过，先选菜单 2 一键配置。")
        pause()
        return
    py, _src = check_python()
    cfg_path = os.path.join(work, "config.json")
    if py and os.path.isfile(os.path.join(work, "oj_config.py")):
        try:
            subprocess.call([py, os.path.join(work, "oj_config.py"), "show"], cwd=work)
        except Exception as e:
            warn(f"运行 oj_config.py 失败：{e}")
    else:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in cfg.items():
                print(f"  {k:<18} = {v}")
        except Exception as e:
            warn(f"读配置失败：{e}")
    print()
    info(f"配置文件：{cfg_path}")
    print()
    print("  改法：在本目录下运行  oj_config.py set <字段> <值>")
    print("  也可以直接让 AI 帮你改——它只改 config.json，不改流程。")
    pause()


def open_work_dirs(host):
    """菜单 5：打开脚本目录 / 收尾文件夹 / 技能包目录。"""
    title("打开目录")
    work = find_work_dir(host)
    opts = []
    if work:
        opts.append(("脚本目录", work))
        cfg_path = os.path.join(work, "config.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                dd = json.load(f).get("deliver_dir") or ""
            if dd:
                os.makedirs(dd, exist_ok=True)
                opts.append(("收尾文件夹", dd))
        except Exception:
            pass
    for i, h in enumerate(HOST_ORDER[:3]):
        p = os.path.join(host_skills_dir(h), "oj-homework-checker")
        if os.path.isdir(p):
            opts.append((f"{HOSTS[h]['name']} 技能包", p))

    if not opts:
        warn("还没配置过，先选菜单 2 一键配置。")
        pause()
        return
    for i, (label, path) in enumerate(opts, 1):
        print(f"   {i}. {label}")
        print(f"      {path}")
    print("   0. 返回")
    print()
    try:
        sel = ask_input("  请选择 > ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if sel.isdigit() and 1 <= int(sel) <= len(opts):
        target = opts[int(sel) - 1][1]
        try:
            if platform.system() == "Windows":
                os.startfile(target)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
            ok(f"已打开：{target}")
        except Exception as e:
            warn(f"打不开：{e}")
        time.sleep(1)


def main():
    try:
        host = choose_host()
        if not host:
            print("\n  再见！")
            return

        # 选完宿主直接进菜单，不再强制先跑一遍环境检测——
        # 想检测就选 1，想配置就选 2（配置里本来就会检测）。
        while True:
            title("OJ 作业自动化 · 环境检测与配置助手")
            h = HOSTS[host]
            work = find_work_dir(host)
            print(f"  当前宿主：{h['name']}（可以换）")
            if work:
                print(f"  已配置  ：{work}")
            else:
                print("  已配置  ：还没配置过（选 2 开始）")
            print()
            print("   1. 检测本机环境")
            print("   2. 一键配置（检测 + 填信息 + 部署脚本与技能包）")
            print("   3. 立刻跑一次检测（不开 AI，直接看有没有新作业）")
            print("   4. 查看当前配置")
            print("   5. 打开脚本目录 / 收尾文件夹")
            print("   6. 查看软件安装指引")
            print("   7. 更换 AI 助手（宿主）")
            if platform.system() == "Windows":
                print("   8. 下载 WorkBuddy 安装包")
            print("   0. 退出")
            print()
            try:
                sel = ask_input("  请选择 > ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if sel == "0":
                break
            if sel == "1":
                _py, _py_src = check_python()
                env_report(
                    host,
                    "http://114.55.147.180",
                    _py,
                    _py_src,
                    check_compiler(),
                    check_network("http://114.55.147.180"),
                )
                pause()
            elif sel == "2":
                existing_path, cfg = find_existing_config(host)
                reconfig = True
                if existing_path:
                    reconfig = show_already_configured(existing_path, cfg)
                    if reconfig:
                        warn("将重新配置（原有文件会被覆盖）。")
                        print()
                        if not ask_yes("确定继续吗？", False):
                            continue
                if reconfig:
                    configure(host, base_url_probe=(cfg or {}).get("base_url"))
            elif sel == "3":
                run_check_once(host)
            elif sel == "4":
                show_existing_config(host)
            elif sel == "5":
                open_work_dirs(host)
            elif sel == "6":
                show_install_guide(host)
            elif sel == "7":
                new = choose_host()
                if new:
                    host = new
            elif sel == "8" and platform.system() == "Windows":
                download_workbuddy()
            else:
                warn("无效选择")
                time.sleep(0.8)
        print("\n  已退出")
    except KeyboardInterrupt:
        print("\n\n  已退出")
    except EOFError:
        print("\n\n  已退出（输入结束）")


if __name__ == "__main__":
    main()
