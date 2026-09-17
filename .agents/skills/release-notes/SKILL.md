---
name: release-notes
description: "根据 git commit 历史整理版本更新内容，并调用项目脚本打包 beta/prod 在线更新包。用于发布、打包测试版或正式版、编写 latest.json notes、README 发布说明、版本公告，或让 Codex 在发版前总结从上一个 tag/版本到当前 HEAD 的改动并执行 npm/Tauri updater 打包上传。"
---

# Release Notes Skill

## 常用请求

生成本次版本更新内容：

```text
Use $release-notes to summarize commits from the latest tag to HEAD for version 1.1.8-beta.1.
```

打包 Windows beta：

```text
Use $release-notes to package Windows beta version 1.1.8-beta.1 and create a tag.
```

打包 macOS beta：

```text
Use $release-notes to package macOS beta version 1.1.8-beta.1 for darwin-aarch64 and create a tag.
```

## 工作流

### 1. 确认版本范围

优先使用用户给出的范围，例如：

```bash
git log --oneline v1.1.7..HEAD
```

如果用户没有给范围，先找最近 tag：

```bash
git describe --tags --abbrev=0
git log --oneline <latest-tag>..HEAD
```

发布打包脚本默认使用 `v<version>` 作为 tag，例如 `v1.1.8-beta.1`、`v1.1.8`。如果仓库已有多个 tag，优先选择最近的版本 tag 作为本次更新范围起点。

如果没有 tag，用最近 20 条 commit 作为候选，并说明这是推断范围：

```bash
git log --oneline -20
```

### 2. 读取 commit 详情

用非交互命令收集信息：

```bash
git log --no-merges --date=short --pretty=format:"%h%x09%ad%x09%s" <range>
git show --stat --oneline --no-renames <commit>
```

只在需要判断影响面时查看 diff。不要把内部敏感信息、密钥、调试路径写进发布说明。

### 3. 分类整理

按用户可感知价值分组，优先这些栏目：

- 新增功能
- 优化体验
- 问题修复
- 更新与发布
- 内部改进

合并同类 commit，避免逐条机械复述。把技术细节翻译成用户能理解的结果，但保留关键模块名。

### 4. 输出格式

默认输出中文 Markdown：

```markdown
## 版本更新内容

### 新增功能
- ...

### 优化体验
- ...

### 问题修复
- ...

### 更新与发布
- ...
```

如果用于 Tauri updater `latest.json` 的 `notes/body` 字段，输出更短的纯 Markdown，不包含代码块。

### 5. 打包更新包

优先使用本 skill 的包装脚本，它会调用项目现有 npm/Tauri updater 脚本，并自动设置 beta/prod 上传目录。

- Windows 使用 `.agents/skills/release-notes/scripts/package-updater.ps1`。
- macOS 使用 `.agents/skills/release-notes/scripts/package-updater.sh`。

推荐流程：

1. 先按上面的 commit 范围整理一份面向用户的中文 Markdown notes。
2. 将 notes 写入临时或项目约定的 Markdown 文件。
3. 打包时传 `-NotesFile <file>` / `--notes-file <file>`，确保远端 `latest.json.notes` 与整理后的版本说明一致。
4. 如果用户只想快速打包，可传 `-AutoNotes` / `--auto-notes`，或不传 notes 参数让脚本自动从最近 tag 到 `HEAD` 生成简版 notes。

打包分支是强制规则，不能通过参数绕过：

- `prod` / 正式版只能在 `release` 分支执行。
- `beta` / 测试版只能在 `test` 或 `release` 分支执行。

执行前先检查：

```bash
git branch --show-current
```

如果当前分支不符合当前通道的允许分支，拒绝打包，不要自动切分支。包装脚本也会做同样校验。

Windows beta：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -AutoNotes -CreateTag
```

Windows prod：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8 -Channel prod -Platform windows-x86_64 -AutoNotes -CreateTag
```

macOS beta：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --auto-notes --create-tag
```

macOS prod：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8 --channel prod --platform darwin-aarch64 --auto-notes --create-tag
```

Windows 预览命令但不执行：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -AutoNotes -PrintOnly
```

macOS 预览命令但不执行：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --auto-notes --print-only
```

Windows 只构建不上传：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -NoUpload
```

macOS 只构建不上传：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --no-upload
```

脚本规则：

- `-Channel beta` / `--channel beta` 自动使用 `--prefix bytecp-plus/beta`。
- `-Channel prod` / `--channel prod` 自动使用 `--prefix bytecp-plus/prod`。
- beta 使用 beta profile updater 构建，保留登录页的生产/测试授权环境切换；prod 使用 prod profile 构建，并将授权环境锁定为 production。
- 包装脚本默认把 release notes 写入 `latest.json.notes`；未传 notes 时会自动从最近 tag 到 `HEAD` 生成。显式传 `-AutoNotes` / `--auto-notes` 让意图更清楚。
- 需要手写更新内容时用 `-Notes "..."` / `--notes "..."`；需要从文件读取时用 `-NotesFile notes.md` / `--notes-file notes.md`。
- 需要临时禁用自动 notes 时用 `-NoAutoNotes` / `--no-auto-notes`，此时上传脚本会回退到默认文案。
- beta 版本号必须类似 `1.1.8-beta.1`。
- prod 版本号必须类似 `1.1.8`，不能带 `-beta`。
- `-CreateTag` / `--create-tag` 会在打包命令成功后创建 annotated tag，默认 tag 名是 `v<version>`。
- tag 已存在且指向 HEAD 时视为成功；tag 已存在但指向其他 commit 时停止，不能自动移动 tag。
- 需要推送 tag 时显式加 `-PushTag` / `--push-tag`。
- 分支规则强制执行：`prod` 只能在 `release`，`beta` 只能在 `test` 或 `release`。
- `-RequiredBranch <branch>` / `--required-branch <branch>` 只能在当前通道允许分支内做更严格限制，不能扩大允许分支。
- 需要绕过版本/通道校验时显式加 `-AllowVersionChannelMismatch` / `--allow-version-channel-mismatch`。

### 6. 打包前检查

生成更新内容后提醒用户确认：

- 版本号是否正确，例如 `1.1.8-beta.1` 或 `1.1.8`
- beta 是否上传到 `bytecp-plus/beta`
- prod 是否上传到 `bytecp-plus/prod`
- 当前分支是否符合通道要求：`prod` 在 `release`；`beta` 在 `test` 或 `release`
- release notes 是否覆盖了本次范围内所有面向用户的改动
- 如果执行打包，先用 `-PrintOnly` 复核命令；正式上传前确认当前 git 状态和版本号。
- 打包成功后是否已经创建 `v<version>` tag；下一次整理更新内容时从这个 tag 到 HEAD。

## 规则

- 不编造 commit 中没有体现的功能。
- 不暴露内部 token、账号、机器路径、临时日志。
- 优先总结“对用户有什么变化”，其次才是“代码怎么改”。
- 如果 commit message 太粗略，结合 `git show --stat` 和相关文件名推断，并明确这是根据文件影响面整理。
