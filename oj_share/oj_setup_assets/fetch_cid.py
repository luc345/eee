#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取指定 cid 的题面（Description / Input / Output / 样例），存成 json。

用法：
    python fetch_cid.py <cid> [config.json]

例：
    python fetch_cid.py 1778
    python fetch_cid.py 1778 D:\\我的\\oj_homework\\config.json

结果写到脚本同目录的 cid<cid>_problems.json，并在屏幕上打印每道题。
比写死 cid 的 fetch1766.py 通用——检测到新作业后直接用它抓题面即可。
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oj_checker import (  # noqa: E402
    enter_contest,
    parse_problem_links,
    fetch_problem,
    parse_problem_detail,
    load_config,
)


def main():
    cid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cfg_path = sys.argv[2] if len(sys.argv) > 2 else "config.json"
    if cid <= 0:
        print(__doc__)
        return 2

    cfg = load_config(cfg_path)
    base = cfg["base_url"]

    print(f"进入作业 cid={cid} ...")
    html, jar = enter_contest(base, cid, cfg["contest_password"])
    links = parse_problem_links(html, cid)
    if not links:
        print("没抓到题目：检查 cid 是否存在、作业密码是否正确。")
        return 1
    print("找到题目:", [(p["pid"], p["title"]) for p in links])

    out = {}
    for p in links:
        pid = p["pid"]
        h = fetch_problem(base, cid, pid, jar)
        d = parse_problem_detail(h)
        d["title"] = p["title"]
        d["url"] = f"{base}/problem.php?cid={cid}&pid={pid}"
        out[str(pid)] = d

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"cid{cid}_problems.json")
    with io.open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已保存:", dest)

    for pid, d in out.items():
        print("=" * 70)
        print(f"pid={pid}  {d.get('title')}")
        print("LIMIT:", d.get("limit"))
        for k in ("Description", "Input", "Output", "Sample Input", "Sample Output"):
            print(f"--{k}--")
            print(d.get("sections", {}).get(k, ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
