# OJ 作业自动化（多助手版）

把「**一句话 → 检测老师有没有发新作业 → 写 C/C++ 代码 → 本地样例测试 → 自动提交 OJ → 整理收尾文件夹 → 汇报结果**」
这条流水线，装到你自己的 AI 助手里。适合 HUSTOJ 一类的课程 OJ。

> **本仓库不含任何账号密码。** 学号、登录密码、作业密码、老师姓名全部由使用者自己在本地 `config.json` 里填，
> 这些文件已被 `.gitignore` 排除。仓库里默认的 OJ 地址只是作者学校的站点，请换成你自己的。

**支持的 AI 助手（装的时候任选一个，功能一致）**

| 助手 | 技能包装到哪 | 怎么触发 |
|---|---|---|
| **DSH**（DeepSeek Harness） | `~\.dsh\skills\` | 说一句「用 oj-homework-checker 技能看看有没有新作业」，或 `/oj-homework-checker` |
| **WorkBuddy**（腾讯） | `~\.workbuddy\skills\` | 说一句话，或在技能面板点「运行技能」 |
| **TRAE CN**（字节） | `~\.trae-cn\skills\` | 同上，或 `/oj-homework-checker` |

---

## 一、它到底做了什么

1. **检测新作业**：抓 OJ 的作业列表，按 `config.json` 里的老师姓名过滤，和 `state.json` 比对去重，只报新发布的。
2. **写码 + 本地测试**：每题一份源码，按 OJ 的 A/B/C/D/E 顺序命名；用 MSVC 或 g++ 编译，
   把题面样例逐一 diff 比对，**样例全过才允许提交**。
3. **自动提交**：每题完整走一遍图形验证码流程（把验证码图片交给 AI 用视觉读出来），
   提交语言必须和本地编译语言一致。
4. **盯结果**：读 OJ 判定，不是 Accepted 就换一种做法重来；**单题最多 3 遍**，
   三遍都不过就停手并明确警告，不会无声无息地反复重试烧 token。
5. **整理收尾文件夹**：按 OJ 上的题号把代码整理好，方便直接交作业：

   ```
   桌面\OJ作业\<作业目录>\
       1-1-a.cpp      ← 题号照抄 OJ 上的编号
       1-1-b.cpp
       汇报.md        ← 每题一行 + OJ 状态链接
   ```

6. **汇报**：对话里报一次，同时写成 `汇报.md`。

## 二、快速开始（推荐：一个 exe 搞定）

1. 下载本仓库，双击 **`启动器.bat`**（或直接双击 `OJ作业自动化配置助手.exe`，效果一样）。
2. 先选你用的 AI 助手：`1) DSH` / `2) WorkBuddy` / `3) TRAE CN`
   （没装 WorkBuddy 可以在这一屏按 `d` 让它去官网下载安装包）。
3. 回菜单选 **`2. 一键配置`**：先检测环境（助手 / Python / C++ 编译器 / 能否连上 OJ），
   再按提示填学号、密码、老师姓名、收尾文件夹位置。
4. 它会自动生成 `config.json`、部署脚本、把技能包装进你那个助手的技能目录，并打印一句**触发口令**。
5. 回到助手，说那句话（或把我上一轮那类任务内容整段粘进去），它就开始干活。

配置助手菜单：

| 选项 | 作用 |
|---|---|
| 1 检测本机环境 | 看助手 / Python / C++ 编译器 / 网络齐不齐 |
| 2 一键配置 | 检测 + 填信息 + 部署脚本 + 装技能包 |
| 3 立刻跑一次检测 | **不开 AI**，直接跑 `oj_checker.py` 看有没有新作业 |
| 4 查看当前配置 | 看 `config.json`（密码打码） |
| 5 打开脚本目录 / 收尾文件夹 | 直接跳到文件位置 |
| 6 查看软件安装指引 | 缺什么装什么的链接 |
| 7 更换 AI 助手 | 换宿主 |
| 8 下载 WorkBuddy 安装包 | 单独入口 |

> `启动器.bat` 必须和 exe 放在同一个文件夹里，且**必须保持 CRLF 行尾**。
> 如果被编辑器改成了 LF，`cmd.exe` 会报 `'utomation' is not recognized` 这类错——
> 用记事本另存，或重新复制一份即可。

## 三、手动安装（想自己折腾的话）

```bash
# 1. 技能包放到你所选助手的技能目录，例如 DSH：
#    xcopy /E /I oj_share\oj-homework-checker  %USERPROFILE%\.dsh\skills\oj-homework-checker

# 2. 脚本目录放到你希望 AI 干活的地方，例如：
#    xcopy /E /I oj_share\oj_homework  %USERPROFILE%\dsh-oj\oj_homework

# 3. 填自己的信息（不要直接改 example）
copy oj_share\oj_homework\config.example.json  %USERPROFILE%\dsh-oj\oj_homework\config.json
python %USERPROFILE%\dsh-oj\oj_homework\oj_config.py set student_id 你的学号
python %USERPROFILE%\dsh-oj\oj_homework\oj_config.py set student_password 你的OJ登录密码
python %USERPROFILE%\dsh-oj\oj_homework\oj_config.py set contest_password 你的作业密码
python %USERPROFILE%\dsh-oj\oj_homework\oj_config.py set teachers 老师姓名
python %USERPROFILE%\dsh-oj\oj_homework\oj_config.py show      # 核对（密码打码）
```

详细说明见 [`oj_share/安装与使用说明.md`](oj_share/安装与使用说明.md)。

## 四、包内结构

```
.
├── 启动器.bat                      # 一键启动（双击它，或直接双击 exe）
├── OJ作业自动化配置助手.exe         # 单文件，接收方不用装 Python
├── 功能自查表.html                 # 功能清单 + 本机安装位置，浏览器打开即可
├── 先看这里.txt                    # 快速说明
├── OJ作业自动化-分享包.zip          # 打包好的成品，直接转发给别人用
└── oj_share/
    ├── oj_setup.py                 # 配置助手源码（exe 就是它打包出来的）
    ├── oj_setup_assets/            # 助手随包资源（脚本、技能包、模板）
    ├── 安装与使用说明.md
    ├── 自动化任务内容-模板.md        # 任务内容模板，照抄即可
    ├── oj-homework-checker/        # 技能包（AI 读的工作流说明 + 脚本）
    │   ├── SKILL.md
    │   └── assets/
    │       ├── oj_checker.py       # 检测：拉作业列表、按老师过滤、抓题面
    │       ├── fetch_cid.py        # 抓指定作业的题面，存成 json
    │       ├── oj_submit.py        # 提交：登录、验证码、查评测结果
    │       ├── oj_config.py        # 配置查看 / 修改命令
    │       ├── config.example.json # 配置模板（已脱敏）
    │       ├── make_vs_solution.py # 生成 VS 解决方案（一题一项目，可选）
    │       └── build_and_test.bat  # MSVC 编译 + 样例比对
    └── oj_homework/                # 脚本副本（不含状态文件）
```

## 五、需要按自己电脑改的地方

| 位置 | 说明 |
|---|---|
| Python 路径 | 填你自己助手的 Python 绝对路径（或系统 `python`） |
| 脚本目录 `DIR` | 你放 `oj_homework` 的实际目录 |
| VS 编译器路径 | `build_and_test.bat` 里的 `vcvarsall.bat` 路径 |

没装 Visual Studio 也能用：装 VS 时勾选「使用 C++ 的桌面开发」，
或者改用 g++（把 `cl /nologo /utf-8 /EHsc /std:c++17` 换成 `g++ -std=c++17 -o`）。

## 六、踩过的坑（都写进 SKILL.md 了）

- **验证码是必填的**：HUSTOJ 在验证码缺失/错误时**不报错**，而是静默丢弃提交（返回空页面）。
  所以每次提交前都要重新取一张验证码图，**绝不复用旧图、绝不猜数字**。
- **MSVC 要加 `/utf-8`**：源码里有中文注释时，代码页 936 下 `cl.exe` 会报 C4819 并把后面的代码解析乱，
  冒出 `"cin": 未声明的标识符` 这种假错误。g++ 用 `-std=c++17` 即可。
- **题面解析**：HUSTOJ 用 Bootstrap 面板渲染，得从 `<h3>` 取标题、`panel-heading` 取时限、
  `<h4>` + `panel-body` 取各段；直接按纯文本正则抓不可靠。
- **竞赛密码 ≠ 登录密码**：进私有作业用竞赛密码，提交代码用账号登录（CSRF token + hex MD5）。
- **`CookieJar` 空时为假值**：`cookie_jar or CookieJar()` 会静默新建一个 jar 把会话丢掉，
  必须写 `cookie_jar if cookie_jar is not None else CookieJar()`。
- **提交间隔**：两次提交至少 10 秒，避免触发 OJ 的提交冷却。

## 七、隐私与免责

- 转发或提交代码前，请确认 `config.json` / `state.json` **没有**你的学号和密码（本仓库已排除这两个文件）。
- 只想检测、不想自动提交：把配置里的 `auto_submit` 设为 `false`。
- 本工具只做自动化的「检测 + 编译 + 提交」，**作业内容与提交行为由使用者自己负责**，
  请遵守所在学校与课程的规定，别拿它做违反学术诚信的事。

## 八、许可

仓库暂未指定开源协议。需要的话（例如 MIT）可以自行添加 `LICENSE` 文件。
