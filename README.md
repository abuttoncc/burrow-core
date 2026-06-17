# burrow-core · 陋居共享引擎（single source of truth）

`valu_air`（金融）与 `philo_air`（哲学）两个姊妹库的**共享引擎母本**，打成私有 pip 包 `burrow-core`，装好后用 `burrow` 命令同步。
解决的问题：两库 95% 的 dashboard / auto-wiki 引擎逐字相同，过去靠手工 diff-and-port 同步，会漂移。
现在 **引擎收在这里一份、版本化发布，个性化下沉到各库 `.burrow/config.json`**，`burrow sync` 渲染回各库。

## 安装

```bash
# 开发用（editable：改 burrow/core/ 即时生效，无需重装）
pip install -e .            # 在本仓库根目录

# 版本发布用（构建 wheel → 任意机器装）
python -m build             # 产物在 dist/burrow_core-X.Y.Z-py3-none-any.whl
pip install dist/burrow_core-*.whl

# 私有 git 发布（推到私有 repo 打 tag 后）
pip install "git+https://github.com/<you>/burrow-core.git@v0.1.0"
```

> 装好后 `burrow` 脚本在 `~/Library/Python/3.x/bin/`（macOS user install）。若不在 PATH，
> 要么把该目录加进 PATH，要么用 `python -m burrow …` 等价调用。
> 版本号单一源：`burrow/__init__.py` 的 `__version__`；发布即 bump 它 + 打同名 git tag。

## 用法

```bash
# vault 定位：--workspace > 环境变量 BURROW_WORKSPACE > 当前目录(CWD)；--all 扫 workspace 下 */.burrow/config.json
cd "/path/to/文稿…"          # workspace = 两库的父目录
burrow check --all           # 预检：只看差异不写（幂等验证）
burrow sync --all            # 渲染写回所有库
burrow sync valu_air         # 只同步一个库（裸名字按 workspace 解析）
burrow sync /abs/path/to/vault   # 也接绝对路径
burrow version
```

每次 `sync`（有改动时）在各库写 `.burrow/last-sync.json`（记录 burrow 版本 + 时间 + 改了哪些文件）。

## 机制：vendored sync（不是 runtime require）

```
burrow/core/*  +  <vault>/.burrow/config.json   ──burrow sync──▶   <vault>/ 里的具体文件
（引擎母本，带 {{token}}）   （个性化：title/order/labels/…）            （进各库 git，self-contained · pull 即得）
```

各库拿到的是**渲染后的具体文件**，仍进各自 git、仍 `pull 即得`——不依赖父目录或本包在场。
代价：改完 core 要跑一次 `sync`（确定性、单向、自动，比手工 diff 强）。

## 抽象边界：无状态引擎 vendored，有状态内容各库自持

| 层 | 在哪 | 同步方式 |
|---|---|---|
| Dashboard.md / dashboard.css | `burrow/core/dashboard/*.tmpl` | ✅ sync 渲染（CFG 注入 + token） |
| auto-wiki python（schema/store/position/expand/new_domain） | `burrow/core/auto-wiki/references/` | ✅ sync（前三个逐字拷，expand 读 config 词表，new_domain token） |
| **08-Ops/routines 实例** | **各库自持** | ❌ 不 sync（有活状态 `last-run` + 各库手写散文）。`burrow/core/routines/` 只放 scaffold 模板，见其 README |
| wiki 本体 / 07-QA / Inbox / runs | 各库自持 | ❌ 纯数据，从不 sync |

## config.json 能调什么（个性化全集）

```jsonc
{
  "title_proper": "Air Vault",              // 散文里的库名
  "dashboard": {
    "title": "AIR VAULT",                    // 品牌/footer，空格分词后首词外 <em>
    "order":  ["机构","工具",…],             // 节点类型目录顺序（=图谱着色）
    "labels": ["价格型","数量型","结构性"],   // classified_as 标签（边非页，断链检查跳过）
    "navOntology": "wiki/_index",            // 顶栏「知识本体」指向
    "features": { "pulse": true }            // 今日 Pulse 启发束开关
  },
  "new_domain":  { "mother_ontology_link": "[[_ontology|macro 本体]]", "mother_ref": "macro" },
  "relations":   { "anchor": [...], "idea": [...], "attrib_only": [...] }  // expand.py --scan 判洞词表
}
```

## 改东西的正确姿势

- 改**引擎/布局/交互**（两库都该变）→ 改 `burrow/core/`，跑 `burrow sync --all`。**不要**直接改库里 `00-Dashboard/Dashboard.md`（会被下次 sync 覆盖；文件头已标「勿手改」）。
- 改**某库的个性**（标题/类型表/开关）→ 改那个库的 `.burrow/config.json`，跑 `burrow sync <vault>`。
- 加**新库**→ 建 `<vault>/.burrow/config.json`，`burrow sync <vault>`（`--all` 会自动发现它，无需登记）；routine 从 `burrow/core/routines/*.tmpl` 手工 scaffold。
- **发版**→ bump `burrow/__init__.py` 的 `__version__`，`python -m build`，`git tag vX.Y.Z`。

## 包结构

```
burrow-core/                  仓库根（git repo）
  pyproject.toml  LICENSE  README.md  .gitignore
  burrow/                     pip 包
    __init__.py  cli.py  __main__.py     ← CLI（仅标准库）
    manifest.json                         ← 引擎文件映射表
    core/                                 ← 引擎母本（随包分发的 package-data）
      dashboard/  auto-wiki/references/  routines/
```
