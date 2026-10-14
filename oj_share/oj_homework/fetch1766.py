import json, sys
sys.path.insert(0, ".")
from oj_checker import enter_contest, parse_problem_links, fetch_problem, parse_problem_detail, load_config

cfg = load_config("config.json")
base = cfg["base_url"]
cid = 1766
html, jar = enter_contest(base, cid, cfg["contest_password"])
links = parse_problem_links(html, cid)
print("links:", links)
out = {}
for p in links:
    pid = p["pid"]
    h = fetch_problem(base, cid, pid, jar)
    d = parse_problem_detail(h)
    d["title"] = p["title"]
    d["url"] = f"{base}/problem.php?cid={cid}&pid={pid}"
    out[pid] = d
json.dump(out, open("cid1766_problems.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for pid, d in out.items():
    print("="*60)
    print(pid, d.get("title"))
    print("LIMIT:", d.get("limit"))
    for k in ("Description", "Input", "Output", "Sample Input", "Sample Output"):
        print(f"--{k}--")
        print(d.get("sections", {}).get(k, ""))
