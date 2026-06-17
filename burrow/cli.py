"""burrow — 陋居共享引擎同步器 CLI。

把包内引擎母本（burrow/core/）+ 各库 `<vault>/.burrow/config.json` 渲染成
**具体文件**写回各库（仍进各库 git · self-contained · pull 即得）。

vault 定位（不再假设「紧挨 _burrow-core」）：
  · 显式路径（含 .burrow/config.json）直接用；
  · 裸名字 → 在 workspace 下找：--workspace > 环境变量 BURROW_WORKSPACE > 当前目录(CWD)；
  · --all → 扫 workspace 下所有 `*/.burrow/config.json`。

用法：
    burrow sync <vault> [<vault> ...]      # 渲染并写回
    burrow sync --all [--workspace PATH]
    burrow check <vault> | --all            # 只比对差异、不写
    burrow version
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__

PKG = Path(__file__).resolve().parent          # burrow/（内含 core/ 与 manifest.json）
MANIFEST = PKG / "manifest.json"


# ── 定位 ───────────────────────────────────────────────────────────
def workspace_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("BURROW_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd()


def resolve_vault(name: str, ws: Path) -> Path:
    p = Path(name).expanduser()
    if (p / ".burrow" / "config.json").exists():
        return p.resolve()
    return (ws / name).resolve()


def discover_vaults(ws: Path) -> list[Path]:
    return sorted({c.parent.parent for c in ws.glob("*/.burrow/config.json")})


# ── 渲染 ───────────────────────────────────────────────────────────
def build_tokens(cfg: dict) -> dict:
    dash = cfg.get("dashboard", {})
    nd = cfg.get("new_domain", {})
    return {
        "CFG_JSON": json.dumps(dash, ensure_ascii=False),
        "VAULT_TITLE": dash.get("title", "VAULT"),
        "VAULT_TITLE_PROPER": cfg.get("title_proper", dash.get("title", "Vault")),
        "MOTHER_ONTOLOGY_LINK": nd.get("mother_ontology_link", ""),
        "MOTHER_REF": nd.get("mother_ref", "母本"),
    }


def render(src: Path, mode: str, tokens: dict) -> str:
    text = src.read_text(encoding="utf-8")
    if mode == "copy":
        return text
    # 只替换 {{TOKEN}} 双花括号，绝不碰单花括号（new_domain.py 的 .format 占位）
    for k, v in tokens.items():
        text = text.replace("{{" + k + "}}", str(v))
    leftover = [ln for ln in text.splitlines() if "{{" in ln and "}}" in ln]
    if leftover:
        print(f"  [!] {src.name}: 仍有未替换的 {{{{token}}}}：")
        for ln in leftover[:5]:
            print(f"      {ln.strip()[:90]}")
    return text


def process(vault: Path, write: bool) -> int:
    cfg_path = vault / ".burrow" / "config.json"
    if not cfg_path.exists():
        print(f"[burrow] 跳过 {vault.name}：缺 .burrow/config.json")
        return 0
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    tokens = build_tokens(cfg)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    action = "sync" if write else "check"
    title = cfg.get("dashboard", {}).get("title", "?")
    print(f"\n══ {action}  {vault.name}  ({title}) ══")
    changed = unchanged = 0
    touched = []
    for item in manifest["files"]:
        src = PKG / item["src"]
        dst = vault / item["dst"]
        if not src.exists():
            print(f"  [!] 缺 core 文件：{item['src']}")
            continue
        new = render(src, item.get("mode", "copy"), tokens)
        old = dst.read_text(encoding="utf-8") if dst.exists() else None
        if old == new:
            unchanged += 1
            continue
        changed += 1
        touched.append(item["dst"])
        tag = "改" if old is not None else "新建"
        print(f"  {'✎' if write else '·'} {tag}  {item['dst']}")
        if write:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new, encoding="utf-8")
    if write and changed:
        stamp = {
            "burrow_version": __version__,
            "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": touched,
        }
        (vault / ".burrow" / "last-sync.json").write_text(
            json.dumps(stamp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suffix = "" if write else "（check 模式未写）"
    print(f"  → {changed} 变更 · {unchanged} 一致{suffix}")
    return changed


# ── CLI ────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="burrow", description="陋居共享引擎同步器 v" + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("sync", "渲染并写回各库"), ("check", "只比对差异、不写")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("vaults", nargs="*", help="库名或路径（裸名字按 workspace 解析）")
        sp.add_argument("--all", action="store_true", help="扫 workspace 下所有带 .burrow/config.json 的库")
        sp.add_argument("--workspace", help="库所在根目录（默认 BURROW_WORKSPACE 或 CWD）")
    sub.add_parser("version", help="打印版本")
    a = ap.parse_args(argv)

    if a.cmd == "version":
        print("burrow-core " + __version__)
        return 0

    ws = workspace_root(getattr(a, "workspace", None))
    if a.all:
        targets = discover_vaults(ws)
        if not targets:
            print(f"[burrow] workspace 下没找到任何 */.burrow/config.json：{ws}")
            return 1
    elif a.vaults:
        targets = [resolve_vault(v, ws) for v in a.vaults]
    else:
        print("[burrow] 需指定 <vault> 或 --all")
        return 1

    write = a.cmd == "sync"
    total = 0
    for v in targets:
        if not v.is_dir():
            print(f"[burrow] 跳过 {v}：目录不存在")
            continue
        total += process(v, write)
    print(f"\n[burrow] 完成 · 共 {total} 处" + ("写入" if write else "差异"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
