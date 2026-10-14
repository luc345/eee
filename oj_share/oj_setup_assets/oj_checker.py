#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OJ 填老师姓名作业检测器
- 从 contest.php 公开列表识别老师"填老师姓名"发布的作业（标题含"填老师姓名"）
- 用竞赛密码进入作业，拉取题目列表与每道题的题目描述、输入输出、样例
- 与 state.json 中已记录的 cid 对比，发现新作业后输出结构化报告
- 纯标准库，无需 requests/bs4 等第三方包
"""
import sys
import os
import re
import json
import html
import hashlib
import argparse
from datetime import datetime
from urllib import request, parse, error
from http.cookiejar import CookieJar

def _setup_console():
    """把标准输出锁成 UTF-8，避免在 GBK 控制台下打印中文/特殊字符时崩。

    OJ 页面里常有不换行空格(\xa0)之类的字符；Windows 控制台默认 GBK，
    直接 print 会 UnicodeEncodeError 并以退出码 1 结束——那会让 AI 误判成
    "脚本失败"然后重试，所以这里兜底成 UTF-8。
    """
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_setup_console()



def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch(url, cookie_jar=None, data=None, headers=None, timeout=25):
    """带统一 UA 与 cookie 的 GET/POST。"""
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
    if headers:
        h.update(headers)
    cj = cookie_jar if cookie_jar is not None else CookieJar()
    opener = request.build_opener(request.HTTPCookieProcessor(cj))
    req = request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except error.URLError as e:
        return f"<!-- FETCH_ERROR: {e} -->"


def strip_tags(text):
    """去掉 script/style/标签，做 html unescape 并压缩空白。"""
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


# ---------- contest list ----------

def parse_contest_list(html_text):
    """解析 contest.php 列表页，返回所有竞赛/作业条目。"""
    results = []
    # 匹配每一行 <tr ...> ... </tr>
    for row_m in re.finditer(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
        row_html = row_m.group(1)
        # 找是否包含 contest.php?cid= 的链接
        link_m = re.search(r"<a\s+href=['\"]contest\.php\?cid=(\d+)['\"][^>]*>(.*?)</a>", row_html, re.S | re.I)
        if not link_m:
            continue
        cid = link_m.group(1)
        title = strip_tags(link_m.group(2))
        # 提取所有 <td> 单元格
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)
        if len(cells) < 5:
            # 有些行可能把多个 td 合并在一行，尝试用更宽容的方式
            # 若链接所在 td 后还有 td，我们按顺序提取文本
            cells = [strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)]
            if len(cells) < 4:
                continue
        else:
            cells = [strip_tags(c) for c in cells]
        status = cells[2] if len(cells) > 2 else ""
        private = cells[3] if len(cells) > 3 else ""
        creator = cells[4] if len(cells) > 4 else ""
        results.append({
            "cid": cid,
            "title": title,
            "status": status,
            "private": private,
            "creator": creator,
        })
    return results


def fetch_contest_list(base_url, page=1):
    url = f"{base_url}/contest.php" if page == 1 else f"{base_url}/contest.php?page={page}"
    html_text = fetch(url)
    return parse_contest_list(html_text)


# ---------- contest detail & problems ----------

def enter_contest(base_url, cid, contest_password):
    """向 contest.php?cid= 提交竞赛密码，返回可查看题目的页面 HTML。"""
    url = f"{base_url}/contest.php?cid={cid}"
    jar = CookieJar()
    # 先 GET 拿到 session
    fetch(url, cookie_jar=jar)
    # POST 密码（字段名 password）
    post_data = parse.urlencode({"password": contest_password}).encode()
    return fetch(url, cookie_jar=jar, data=post_data), jar


def parse_problem_links(contest_html, cid):
    """从进入竞赛后的页面提取题目链接。"""
    pattern = re.compile(
        r"<a\s+href=['\"]problem\.php\?cid=" + re.escape(str(cid)) + r"&pid=(\d+)['\"][^>]*>(.*?)</a>",
        re.S | re.I,
    )
    probs = []
    for m in pattern.finditer(contest_html):
        pid = m.group(1)
        title = strip_tags(m.group(2))
        # 去重，保留第一次出现的 pid
        if not any(p["pid"] == pid for p in probs):
            probs.append({"pid": pid, "title": title})
    return probs


def fetch_problem(base_url, cid, pid, cookie_jar):
    url = f"{base_url}/problem.php?cid={cid}&pid={pid}"
    return fetch(url, cookie_jar=cookie_jar)


# ---------- problem detail parsing ----------

SECTION_HEADS = [
    ("Description", r"^Description"),
    ("Input", r"^Input$"),
    ("Output", r"^Output$"),
    ("Sample Input", r"^Sample\s+Input"),
    ("Sample Output", r"^Sample\s+Output"),
    ("Hint", r"^Hint"),
    ("Source", r"^Source"),
]


def parse_problem_detail(html_text):
    """解析题目页为结构化的题目信息。直接从 Bootstrap panel 结构提取。"""
    info = {"raw_text": html_text}

    # 1) 标题：在 panel-heading 的 <h3> 里
    h3_m = re.search(r"<h3[^>]*>(.*?)</h3>", html_text, re.S | re.I)
    if h3_m:
        h3_text = strip_tags(h3_m.group(1)).strip()
        m = re.match(r"Problem\s+([A-Z0-9]+)\s*[:：]\s*(.+)", h3_text)
        if m:
            info["label"] = m.group(1).strip()
            info["title"] = m.group(2).strip()
        else:
            info["label"] = ""
            info["title"] = h3_text
    else:
        info["label"] = ""
        info["title"] = ""

    # 2) 时间/内存限制：在 panel-heading 的文本里
    heading_m = re.search(r"<div[^>]*class=['\"]panel-heading['\"][^>]*>.*?<h3[^>]*>.*?</h3>(.*?)</div>", html_text, re.S | re.I)
    if heading_m:
        heading_text = strip_tags(heading_m.group(1))
        tl = re.search(r"Time\s+Limit[:：]?\s*(\d+(?:\.\d+)?)\s*Sec", heading_text, re.I)
        ml = re.search(r"Memory\s+Limit[:：]?\s*(\d+)\s*MB", heading_text, re.I)
        info["time_limit"] = tl.group(1) + " Sec" if tl else ""
        info["memory_limit"] = ml.group(1) + " MB" if ml else ""
    else:
        info["time_limit"] = ""
        info["memory_limit"] = ""

    # 3) 各章节：每个 <h4> 标题后面紧跟一个 panel-body div
    sections = {}
    sec_pattern = re.compile(
        r"<h4[^>]*>(.*?)</h4>.*?<div[^>]*class=['\"]panel-body(?:\s+content)?['\"][^>]*>(.*?)</div>",
        re.S | re.I,
    )
    for m in sec_pattern.finditer(html_text):
        sec_name = strip_tags(m.group(1)).strip()
        sec_content = strip_tags(m.group(2)).strip()
        # 规范化章节名
        for canonical, pat in SECTION_HEADS:
            if re.search(pat, sec_name, re.I):
                if canonical not in sections or len(sec_content) > len(sections[canonical]):
                    sections[canonical] = sec_content
                break
    info["sections"] = sections
    return info


# ---------- state & config ----------

def _normalize_state(state):
    """把 state 规范成 {"seen": {cid: 标题}, "last_check": ...}。

    历史遗留/别处生成的 state.json 里 seen 可能是 list 或缺失，
    直接用会让 setdefault(...)[cid] = ... 抛 TypeError，所以这里兜一下。
    """
    if not isinstance(state, dict):
        state = {}
    seen = state.get("seen")
    if isinstance(seen, list):
        # 旧格式：只存了 cid 列表，转成 dict（标题留空）
        state["seen"] = {str(c): "" for c in seen}
    elif not isinstance(seen, dict):
        state["seen"] = {}
    else:
        state["seen"] = {str(k): v for k, v in seen.items()}
    state.setdefault("last_check", None)
    return state


def load_state(path):
    if not os.path.exists(path):
        return {"seen": {}, "last_check": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _normalize_state(json.load(f))
    except Exception:
        return {"seen": {}, "last_check": None}


def save_state(path, state):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- main ----------

def build_report(cfg, state_path):
    base_url = cfg["base_url"].rstrip("/")
    # 老师：优先用列表 teachers，兼容单个 teacher_filter
    teachers = cfg.get("teachers")
    if isinstance(teachers, str):
        teachers = [teachers]
    if not teachers:
        teachers = [cfg.get("teacher_filter", "填老师姓名")]
    teachers = [t for t in teachers if t]
    contest_password = cfg.get("contest_password", "")
    max_pages = int(cfg.get("max_pages", 3))
    fetch_problems = cfg.get("fetch_problems", True)

    state = load_state(state_path)

    # 拉取列表
    all_contests = []
    for page in range(1, max_pages + 1):
        try:
            contests = fetch_contest_list(base_url, page)
            if not contests:
                break
            all_contests.extend(contests)
        except Exception as e:
            print(f"[!] 拉取第 {page} 页失败: {e}", file=sys.stderr)
            break

    # 过滤老师
    teacher_contests = [c for c in all_contests
                        if any(t in c.get("title", "") for t in teachers)]

    # 去重并排序（cid 大的最新）
    seen_cids = set(c["cid"] for c in teacher_contests)
    teacher_contests = sorted(teacher_contests, key=lambda x: int(x["cid"]), reverse=True)

    # 找新作业：state["seen"] 中没有的 cid
    new_contests = [c for c in teacher_contests if c["cid"] not in state.get("seen", {})]

    report = {
        "checked_at": now_str(),
        "teacher": "、".join(teachers),
        "teachers": teachers,
        "total_found": len(teacher_contests),
        "new_count": len(new_contests),
        "new": [],
        "known": [c for c in teacher_contests if c["cid"] in state.get("seen", {})],
    }

    for c in new_contests:
        cid = c["cid"]
        detail = {"contest": c, "problems": []}
        if fetch_problems and contest_password:
            try:
                contest_html, jar = enter_contest(base_url, cid, contest_password)
                probs = parse_problem_links(contest_html, cid)
                detail["problem_count"] = len(probs)
                for p in probs:
                    ph = fetch_problem(base_url, cid, p["pid"], jar)
                    pinfo = parse_problem_detail(ph)
                    detail["problems"].append({
                        "pid": p["pid"],
                        "title": p["title"],
                        "info": pinfo,
                    })
            except Exception as e:
                detail["error"] = str(e)
        report["new"].append(detail)
        # 标记为已见
        state.setdefault("seen", {})[cid] = c["title"]

    state["last_check"] = now_str()
    save_state(state_path, state)
    return report


def print_report(report, fmt="text"):
    if fmt == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"【OJ 作业检测】{report['checked_at']}  老师：{report['teacher']}")
    print(f"本轮共发现 {report['total_found']} 条相关作业，其中 {report['new_count']} 条为新发布。\n")

    if report["new_count"] == 0:
        print("暂无新作业。\n")
        print("已记录的作业：")
        for k in report["known"]:
            print(f"  - cid={k['cid']} {k['title']} [{k['status']}]")
        return

    for idx, item in enumerate(report["new"], 1):
        c = item["contest"]
        print(f"#{idx} 新作业")
        print(f"  链接：contest.php?cid={c['cid']}")
        print(f"  标题：{c['title']}")
        print(f"  状态：{c['status']}")
        print(f"  可见性：{c['private']}  创建者：{c['creator']}")
        if "error" in item:
            print(f"  [拉取题目失败：{item['error']}]")
            continue
        print(f"  题目数：{item.get('problem_count', len(item['problems']))}")
        for p in item["problems"]:
            info = p["info"]
            title = info.get("title") or p["title"]
            print(f"\n  [Problem {info.get('label','?')}] {title}")
            print(f"  时间/内存限制：{info.get('time_limit','?')} / {info.get('memory_limit','?')}")
            for sec_name in ["Description", "Input", "Output", "Sample Input", "Sample Output"]:
                sec = info.get("sections", {}).get(sec_name)
                if sec:
                    print(f"\n  --- {sec_name} ---")
                    for line in sec.splitlines():
                        print(f"  {line}")
        print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="OJ 填老师姓名作业检测器")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--state", default="state.json", help="状态文件路径")
    parser.add_argument("--report", default="text", choices=["text", "json"], help="报告格式")
    parser.add_argument("--teacher", help="覆盖老师姓名过滤")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.teacher:
        cfg["teacher_filter"] = args.teacher

    report = build_report(cfg, args.state)
    print_report(report, args.report)


if __name__ == "__main__":
    main()
