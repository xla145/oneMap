# release-notes skill 使用说明

这个 skill 用来做两件事：

- 根据 git commit/tag 整理本次版本更新内容。
- 调用项目现有打包脚本发布 beta/prod 在线更新包，并在成功后打 tag。

## 基本规则

- prod / 正式版打包只能在 `release` 分支执行。
- beta / 测试版打包只能在 `test` 或 `release` 分支执行。
- 分支规则是强制规则，不能通过 `-RequiredBranch` / `--required-branch` 扩大允许分支。
- beta 版本号使用 `1.1.8-beta.1` 这种格式。
- prod 版本号使用 `1.1.8` 这种格式。
- beta 使用 beta profile 构建并上传到 `bytecp-plus/beta`。
- prod 上传到 `bytecp-plus/prod`。
- `latest.json.notes` 默认从最近 tag 到 `HEAD` 的 commit 自动生成。
- 需要指定更新内容时，用 `-Notes` / `--notes` 或 `-NotesFile` / `--notes-file` 覆盖。
- 打包成功后可创建 `v<version>` tag，例如 `v1.1.8-beta.1`。
- 下一次生成更新内容时，从最近 tag 到 `HEAD` 汇总。

## 常用触发方式

生成更新内容：

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

## 打包前检查

确认当前分支：

```bash
git branch --show-current
```

按通道必须输出：

```text
prod: release
beta: test 或 release
```

如果当前分支不符合当前通道，脚本会拒绝执行。不要在 skill 里自动切分支。

## Windows 用法

预览 beta 打包命令，不执行：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -AutoNotes -PrintOnly
```

打包并上传 Windows beta，成功后创建 tag：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -AutoNotes -CreateTag
```

打包并上传 Windows prod，成功后创建 tag：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8 -Channel prod -Platform windows-x86_64 -AutoNotes -CreateTag
```

使用自己整理好的 notes 文件：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -NotesFile .\release-notes.md -CreateTag
```

只构建不上传：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -NoUpload
```

创建并推送 tag：

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/release-notes/scripts/package-updater.ps1 -Version 1.1.8-beta.1 -Channel beta -Platform windows-x86_64 -CreateTag -PushTag
```

## macOS 用法

首次使用如需可执行权限：

```bash
chmod +x .agents/skills/release-notes/scripts/package-updater.sh
```

预览 macOS beta 打包命令，不执行：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --auto-notes --print-only
```

打包并上传 macOS beta，成功后创建 tag：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --auto-notes --create-tag
```

打包并上传 macOS prod，成功后创建 tag：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8 --channel prod --platform darwin-aarch64 --auto-notes --create-tag
```

使用自己整理好的 notes 文件：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --notes-file ./release-notes.md --create-tag
```

只构建不上传：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --no-upload
```

创建并推送 tag：

```bash
bash .agents/skills/release-notes/scripts/package-updater.sh --version 1.1.8-beta.1 --channel beta --platform darwin-aarch64 --create-tag --push-tag
```

Intel Mac 使用：

```bash
--platform darwin-x86_64
```

## 更新内容生成流程

查看最近 tag：

```bash
git describe --tags --abbrev=0
```

从最近 tag 到当前提交整理：

```bash
git log --no-merges --date=short --pretty=format:"%h%x09%ad%x09%s" <latest-tag>..HEAD
```

输出建议按这些栏目归类：

- 新增功能
- 优化体验
- 问题修复
- 更新与发布
- 内部改进

包装脚本会把最终 notes 通过 `--upload-args --notes` 传给上传脚本，所以上传后远端 `bytecp-plus/<beta|prod>/latest.json` 里的 `notes` 会跟本次版本内容一致。`--print-only` 会打印最终 notes 和 npm 命令，建议正式打包前先跑一次确认。

## 常见问题

prod 非 `release` 分支执行时报错：

```text
Prod packaging is only allowed on branch 'release'.
```

beta 非 `test` / `release` 分支执行时报错：

```text
Beta packaging is only allowed on branches 'test' or 'release'.
```

处理方式：确认当前分支和发布流程，不要让 skill 自动切分支。

beta 版本号写成正式号时报错：

```text
Beta channel requires a prerelease version such as 1.1.8-beta.1.
```

处理方式：beta 使用 `x.y.z-beta.n`，prod 使用 `x.y.z`。

tag 已存在但不在当前提交时报错：

```text
Tag v1.1.8 already exists on another commit. Refusing to move it.
```

处理方式：检查版本号是否重复，或者确认是否需要发布新的 patch/beta 版本。
