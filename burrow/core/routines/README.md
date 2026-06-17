# core/routines · 契约模板（scaffold-only，**不参与 sync**）

## 为什么 routine 不像 dashboard / python 那样被 vendored 同步

抽象边界落在「**无状态共享引擎**」与「**有状态/各库手写内容**」之间：

| | dashboard / auto-wiki python | 08-Ops/routines 实例 |
|---|---|---|
| 状态 | 无状态（纯渲染/纯函数） | **有活状态**：`last-run` / `last-result` 由 routine 运行时回写 |
| 内容 | 逐字共享，差异=配置大小 | **各库手写散文**：答题员的「立场切换 T4 盖章」、研究员的 SEP/IEP vs gangtise、巡检员多一段 expand --scan |
| 进 manifest？ | ✅ 是，`burrow.py sync` 渲染覆盖 | ❌ 否，覆盖会**抹掉活状态**、且散文无法 token 化 |

所以 `manifest.json` **只收 dashboard + python**。routine 实例留在各库 `08-Ops/routines/` 自持，
core 这里只放**脚手架模板**：新建一个库时，从这里 copy 一份、按 `.burrow/config.json` 的
`domains` / 签名边手填，**不要**指望 `sync` 去维护它。

## 跨库共享的「routine 之共性」其实在别处

routine 真正的共性是**契约结构**（trigger/scope/budget/escalation 字段）+ **gate/审批账本模型**——
这些是**机制文档**，写在各库 `CLAUDE.md §7` 与 `08-Ops/README` 里，不是可渲染的代码。
dashboard 引擎已经**泛化地**读 routine frontmatter（`stateOf` / 状态钟），不关心具体是哪几个 routine，
所以加/减 routine 不需要改引擎——这就是 routine 共性被「吸收进引擎」的方式。

## 模板清单

- `心跳员.md.tmpl` — pulse 产出员（仿 ChatGPT Pulse）。`{{DOMAINS}}` / `{{SIGNATURE_EDGE}}` / `{{HUBS}}` 占位。
  valu 已落地实例见 `valu_air/08-Ops/routines/心跳员.md`（金融版，跨域 drives 边）。
