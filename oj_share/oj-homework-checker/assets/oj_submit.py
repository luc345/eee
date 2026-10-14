"""HUSTOJ 登录 + 提交 + 查询结果。

用法（验证码是必填项，缺了 OJ 会静默丢弃提交，本脚本会先在本地拦住）：
  python oj_submit.py prepare                  # ① 登录 + 下载验证码到 vcode.gif
                                               # ② 用 Read 工具看 vcode.gif，读出 4 位数字
  python oj_submit.py submit <pid> <src> <vcode> [lang]   # ③ 带验证码提交
  python oj_submit.py langs                    # 列出 OJ 实际支持的语言编号，供核对
  python oj_submit.py status [top_n]           # 查询本人最近提交结果

每题提交都要重新走一遍 prepare -> 读图 -> submit，验证码一次性用完即废。

提交语言的选择顺序（保证与本地编译所用语言一致）：
  1) 命令行显式指定的 lang（数字或语言名）
  2) config.json 的 submit_language
  3) 源码文件扩展名推断（.c->C, .cpp/.cc/.cxx->C++, .java->Java, .py->Python）
  4) config.json 的 language（如 "C/C++"）结合扩展名消歧
"""
import urllib.request as request, urllib.parse as parse, http.cookiejar, hashlib, re, sys, time, json, random, os


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

_HERE = os.path.dirname(os.path.abspath(__file__))
_CFG = {}
try:
    _CFG = json.load(open(os.path.join(_HERE, "config.json"), encoding="utf-8"))
except Exception:
    pass

# 账号信息一律从 config.json 读取，脚本里不内置任何凭据（便于分享、避免泄露）
BASE = _CFG.get("base_url", "")
USER = _CFG.get("student_id", "")
PW = _CFG.get("student_password", "")
CID = int(_CFG.get("contest_cid", 0))
CONTEST_PW = _CFG.get("contest_password", "")
SESSION_FILE = os.path.join(_HERE, "session.txt")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*", "Accept-Language": "zh-CN,zh;q=0.9",
     "Origin": BASE, "Upgrade-Insecure-Requests": "1"}

# HUSTOJ 默认语言编号；实际编号以 OJ 为准（用 `langs` 命令核对）
DEFAULT_LANGS = {
    "c": 0, "c++": 1, "pascal": 2, "java": 3, "ruby": 4, "bash": 5, "python": 6,
    "php": 7, "perl": 8, "c#": 9, "obj-c": 10, "freebasic": 11, "scheme": 12,
    "clang": 13, "clang++": 14, "lua": 15, "javascript": 16, "go": 17,
    "sql(sqlite3)": 18, "fortran": 19, "matlab(octave)": 20,
}
# 本地编译标准 -> OJ 语言名
STD_TO_LANG = {"c++17": "c++", "c++14": "c++", "c++11": "c++", "c++20": "c++",
               "c++": "c++", "c17": "c", "c11": "c", "c99": "c", "c": "c"}
# 源码扩展名 -> OJ 语言名
EXT_TO_LANG = {".c": "c", ".cpp": "c++", ".cc": "c++", ".cxx": "c++", ".c++": "c++",
               ".java": "java", ".py": "python", ".py3": "python"}


def norm(name):
    return str(name).strip().lower().replace("＋", "+")


def fetch_langs(op):
    """从 OJ 提交页抓取真实的语言编号表。"""
    try:
        b = op.open(f"{BASE}/submitpage.php?cid={CID}&pid=0", timeout=25).read().decode("utf-8", "ignore")
        m = re.search(r'<select id="language".*?</select>', b, re.S)
        if not m:
            return {}
        out = {}
        for opt in re.finditer(r"<option value=(\d+)[^>]*>(.*?)</option>", m.group(0), re.S):
            out[norm(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", opt.group(2))).strip())] = int(opt.group(1))
        return out
    except Exception:
        return {}


def resolve_lang(srcfile, explicit=None, oj_langs=None):
    """按优先级决定 OJ 语言编号，返回 (lang_id, lang_name, 说明)。"""
    langs = oj_langs or DEFAULT_LANGS
    ext = os.path.splitext(srcfile)[1].lower()

    def to_id(name_or_id):
        if isinstance(name_or_id, int):
            name_or_id = str(name_or_id)
        s = norm(name_or_id)
        if s.isdigit():
            vid = int(s)
            rev = {v: k for k, v in langs.items()}
            return vid, rev.get(vid, str(vid))
        if s in langs:
            return langs[s], s
        # 别名消歧：C/C++ 这种组合值按扩展名决定
        if "c++" in s or "cpp" in s:
            return langs.get(EXT_TO_LANG.get(ext, "c++"), langs.get("c++", 1)), "c++"
        if s in ("c", "c/c++"):
            return langs.get(EXT_TO_LANG.get(ext, "c++"), langs.get("c++", 1)), EXT_TO_LANG.get(ext, "c++")
        return None, None

    if explicit not in (None, ""):
        lid, lname = to_id(explicit)
        if lid is not None:
            return lid, (lname or str(explicit)), "命令行显式指定"

    if _CFG.get("submit_language"):
        lid, lname = to_id(_CFG["submit_language"])
        if lid is not None:
            return lid, (lname or str(_CFG["submit_language"])), "config.submit_language"

    if _CFG.get("build_standard"):
        nm = STD_TO_LANG.get(norm(_CFG["build_standard"]))
        if nm in langs:
            return langs[nm], nm, f"本地编译标准 {_CFG['build_standard']}"

    if ext in EXT_TO_LANG:
        nm = EXT_TO_LANG[ext]
        if nm in langs:
            return langs[nm], nm, f"源码扩展名 {ext}"

    if _CFG.get("language"):
        lid, lname = to_id(_CFG["language"])
        if lid is not None:
            return lid, (lname or str(_CFG["language"])), "config.language + 扩展名消歧"

    return langs.get("c++", 1), "c++", "兜底默认值"


class NoRed(request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None


def new_op(save=False):
    jar = http.cookiejar.MozillaCookieJar()
    if not save:
        try: jar.load(SESSION_FILE, ignore_discard=True, ignore_expires=True)
        except Exception: pass
    op = request.build_opener(request.HTTPCookieProcessor(jar))
    op.addheaders = list(H.items())
    return op, jar


def csrf(op):
    h = op.open(BASE + "/csrf.php", timeout=25).read().decode("utf-8", "ignore")
    m = re.search(r'value="([^"]+)"', h)
    return m.group(1) if m else ""


def enter(op):
    u = f"{BASE}/contest.php?cid={CID}"
    op.open(u, timeout=25).read()
    op.open(u, data=parse.urlencode({"password": CONTEST_PW}).encode(), timeout=25).read()


VCODE_PATH = os.path.join(_HERE, "vcode.gif")


def prepare():
    op, jar = new_op(save=True)
    op.open(BASE + "/login.php", data=parse.urlencode(
        {"user_id": USER, "password": hashlib.md5(PW.encode()).hexdigest(), "csrf": csrf(op)}).encode(), timeout=25).read()
    enter(op)
    img = op.open(BASE + "/vcode.php", timeout=25).read()
    open(VCODE_PATH, "wb").write(img)
    jar.save(SESSION_FILE, ignore_discard=True, ignore_expires=True)
    print("OK 验证码已刷新:", VCODE_PATH, f"({len(img)} bytes, 修改时间 {time.strftime('%H:%M:%S')})")
    print("NEXT 请用 Read 工具查看该图片，把里面的 4 位数字作为 vcode 参数传给 submit")


def langs():
    op, _ = new_op()
    got = fetch_langs(op)
    if not got:
        print("(无法从 OJ 抓取，使用内置默认表)")
        for k, v in sorted(DEFAULT_LANGS.items(), key=lambda x: x[1]):
            print(f"  {v:>2} = {k}")
    else:
        for k, v in sorted(got.items(), key=lambda x: x[1]):
            print(f"  {v:>2} = {k}")
    lid, lname, why = resolve_lang("x.cpp", None, got or DEFAULT_LANGS)
    print(f"\n当前将使用: {lname} (id={lid}) —— 依据: {why}")


def submit(pid, srcfile, vcode, lang=None):
    # ---- 验证码强校验：OJ 缺码/错码时不报错而是静默拒绝，所以必须在本地拦住 ----
    if vcode is None or not str(vcode).strip():
        print("ABORT 缺少验证码，已取消本次提交（不带验证码提交会被 OJ 静默丢弃）。")
        print("      请先运行: python oj_submit.py prepare")
        print("      再用 Read 工具查看 vcode.gif 读出 4 位数字后重试。")
        return False
    vcode = str(vcode).strip()
    if not re.fullmatch(r"\d{4,8}", vcode):
        print(f"WARN 验证码 '{vcode}' 不是 4 位数字格式，仍将尝试提交（看不清就先重新 prepare）。")
    if not os.path.exists(VCODE_PATH):
        print("WARN 未找到 vcode.gif，会话里的验证码可能不是你读的这一张；建议先 prepare 再读图。")

    op, jar = new_op()
    oj_langs = fetch_langs(op) or DEFAULT_LANGS
    lid, lname, why = resolve_lang(srcfile, lang, oj_langs)
    head = f"LANG: {lname} (id={lid}) <- {why}; src={os.path.basename(srcfile)}"
    ext = os.path.splitext(srcfile)[1].lower()
    if ext in EXT_TO_LANG and EXT_TO_LANG[ext] != norm(lname):
        head += f"\nWARN: 源码扩展名 {ext} 通常对应 {EXT_TO_LANG[ext]}，与提交语言 {lname} 不一致，请确认本地是用哪种语言编译的"
    print(head)
    src = open(srcfile, encoding="utf-8").read()
    d = parse.urlencode({"cid": CID, "pid": pid, "language": lid, "source": src,
                         "vcode": vcode, "csrf": csrf(op)}).encode()
    hdrs = dict(H); hdrs["Referer"] = f"{BASE}/submitpage.php?cid={CID}&pid={pid}"
    hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        r = request.build_opener(NoRed, request.HTTPCookieProcessor(jar)).open(
            request.Request(BASE + "/submit.php", data=d, headers=hdrs, method="POST"), timeout=30)
        code, loc = r.status, r.headers.get("Location")
        body = r.read().decode("utf-8", "ignore")
    except request.HTTPError as e:
        code, loc = e.code, e.headers.get("Location")
        body = e.read().decode("utf-8", "ignore") if e.fp else ""
    print("HTTP", code, "| Location:", loc)
    if loc and "status.php" in loc:
        m = re.search(r"top=(\d+)", loc)
        print("SUBMIT_OK run_id=", m.group(1) if m else "?")
        try:                       # 验证码一次性，用完即废，防止误用旧图
            os.remove(VCODE_PATH)
        except Exception:
            pass
        if os.path.exists(VCODE_PATH):
            try:
                open(VCODE_PATH, "wb").close()   # 删不掉就清空
            except Exception:
                pass
        print("NOTE 本次验证码已消费；下一题请重新 prepare 取新码")
        return True
    m = re.search(r'<div class="jumbotron">\s*<p>(.*?)</p>', body, re.S)
    msg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""
    if not msg:
        # OJ 对验证码错误/缺失的返回就是一个没有任何提示的空页，必须显式点出来
        msg = ("提交被 OJ 静默拒绝 —— 99% 是验证码错误或已失效"
               f"（本次使用的 vcode='{vcode}'）。OJ 不会给出明确报错。")
    print("FAIL", msg)
    print("FIX  重新取验证码: python oj_submit.py prepare -> Read 查看 vcode.gif -> 再 submit")
    return False


def status(top=6):
    op, _ = new_op()
    url = f"{BASE}/status.php?cid={CID}&user_id={USER}&zz={random.randint(1,999999)}"
    b = op.open(url, timeout=30).read().decode("utf-8", "ignore")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", b, re.S)
    out = []
    for r in rows[1:1 + int(top)]:
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if cells: out.append(cells)
    for c in out: print(" | ".join(c))
    return out


if __name__ == "__main__":
    missing = [k for k, v in (("base_url", BASE), ("student_id", USER), ("student_password", PW)) if not v]
    if missing:
        print("ERROR config.json 缺少:", "、".join(missing))
        print("      先填好再用，例如: python oj_config.py set student_id 你的学号")
        sys.exit(1)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "prepare": prepare()
    elif cmd == "langs": langs()
    elif cmd == "submit": submit(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "status": status(sys.argv[2] if len(sys.argv) > 2 else 6)
    else: print(__doc__)
