"""OJ 作业助手的集中配置读写。

所有个人信息（老师、学号、账号密码、作业密码）都在 config.json 里，
改这一个文件即可，也可以用命令行：
  python oj_config.py show                # 查看当前配置（密码默认打码）
  python oj_config.py show --reveal       # 查看当前配置（显示明文密码）
  python oj_config.py get <字段>          # 查看单个字段
  python oj_config.py set <字段> <值>     # 修改字段（自动识别 数字/布尔/列表/字符串）
  python oj_config.py set teachers 填老师姓名,王老师   # 多个老师用逗号分隔
"""
import json, os, sys

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
CONFIG = os.path.join(_HERE, "config.json")

# 字段 -> (中文名, 是否敏感)
FIELDS = {
    "base_url": ("OJ 站点地址", False),
    "teachers": ("老师姓名列表", False),
    "teacher_filter": ("老师姓名(单个,兼容旧字段)", False),
    "contest_password": ("作业/竞赛密码", True),
    "student_id": ("学号(OJ 登录账号)", False),
    "student_password": ("OJ 登录密码", True),
    "student_name": ("姓名(备注)", False),
    "contest_cid": ("当前作业编号 cid", False),
    "submit_language": ("提交语言", False),
    "build_standard": ("本地编译标准", False),
    "language": ("作业语言大类", False),
    "max_pages": ("检测翻页数", False),
    "fetch_problems": ("抓取题目详情", False),
    "auto_submit": ("自动提交", False),
    "host": ("使用的 AI 助手", False),
    "deliver_dir": ("收尾文件夹(作业代码与汇报)", False),
    "deliver_layout": ("收尾命名约定(说明用)", False),
}
LIST_FIELDS = {"teachers"}
INT_FIELDS = {"contest_cid", "max_pages"}
BOOL_FIELDS = {"fetch_problems", "auto_submit"}


def load():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def coerce(key, raw):
    if key in LIST_FIELDS:
        return [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]
    if key in INT_FIELDS:
        return int(raw)
    if key in BOOL_FIELDS:
        return str(raw).strip().lower() in ("1", "true", "yes", "y", "是", "开", "on")
    return raw


def mask(v):
    s = str(v)
    if not s:
        return "(空)"
    return "*" * len(s) + f"  (共{len(s)}位)"


def show(reveal=False):
    cfg = load()
    print(f"配置文件: {CONFIG}\n")
    for key, (label, secret) in FIELDS.items():
        if key not in cfg:
            continue
        val = cfg[key]
        if secret and not reveal:
            val = mask(val)
        print(f"  {key:<18} {label:<22} = {val}")
    print("\n改法示例:")
    print("  python oj_config.py set student_password 新密码")
    print("  python oj_config.py set teachers 填老师姓名,王老师")
    print("  python oj_config.py set contest_password 新作业密码")
    print("  python oj_config.py set submit_language C")


def get(key):
    cfg = load()
    if key not in cfg:
        print(f"没有这个字段: {key}\n可用字段: {', '.join(FIELDS)}")
        return None
    v = cfg[key]
    print(mask(v) if FIELDS.get(key, ("", False))[1] else v)
    return v


def set_(key, raw):
    if key not in FIELDS:
        print(f"未知字段: {key}\n可用字段: {', '.join(FIELDS)}")
        return False
    cfg = load()
    old = cfg.get(key)
    cfg[key] = coerce(key, raw)
    save(cfg)
    secret = FIELDS[key][1]
    print(f"已更新 {key} ({FIELDS[key][0]}): "
          f"{mask(old) if secret else old}  ->  {mask(cfg[key]) if secret else cfg[key]}")
    print("下次检测/提交自动生效。")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        show(reveal="--reveal" in sys.argv)
    elif cmd == "get":
        get(sys.argv[2])
    elif cmd == "set":
        if len(sys.argv) < 4:
            print("用法: python oj_config.py set <字段> <值>")
        else:
            set_(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        print(__doc__)
