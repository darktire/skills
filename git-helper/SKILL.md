---
name: git-helper
description: 当用户要求检查、比较、暂存、提交、重置、搁置更改、创建分支、切换分支、查看 Git 历史、修改本地提交消息或压缩本地提交时，应使用此技能。
license: MIT
---

# Git Helper

## 概述

使用此技能执行 Git 仓库检查和自动化任务。优先执行只读检查；仅在用户明确要求且操作安全时，再修改本地仓库状态或本地提交历史。

## 工作流程

1. 确定仓库路径。当前工作目录是 Git 仓库时使用当前目录；否则询问或推断目标 `repo_path`。
2. 修改前先检查。在暂存、提交、重置、搁置、切换分支、创建分支、修改提交消息或压缩提交前，先运行 status 和相关 diff。
3. 优先使用明确路径。除非用户明确要求暂存全部内容，否则只暂存具体文件。
4. 将 `reset`、`checkout`、stash apply/pop/drop、大范围暂存和任何历史改写视为影响较高的操作。当操作可能丢弃、隐藏、冲突或改写未推送工作时，先确认。
5. 仅对明确未推送的本地提交执行提交消息修改或压缩提交；如果提交已包含在远程分支中，停止并说明原因。
6. 根据任务简洁报告结果，包括提交哈希、分支名、stash 引用、变更文件或简短 diff 摘要。

## 脚本操作

需要确定性的命令封装时，使用随附脚本：

```bash
python scripts/git_tool.py <operation> --repo <repo_path> [options]
```

可用操作：

- `status`：显示工作区状态。
- `diff-unstaged`：显示未暂存变更，可配置上下文行数。
- `diff-staged`：显示已暂存变更，可配置上下文行数。
- `diff`：比较工作区与目标分支、标签或提交。
- `add`：暂存一个或多个路径。
- `commit`：将已暂存变更提交为一个提交。
- `reset`：取消暂存所有已暂存变更。
- `log`：显示近期提交，可按开始/结束时间过滤。
- `create-branch`：基于当前分支或指定基准分支创建新分支。
- `checkout`：切换到已有分支或修订版本。
- `show`：显示某个修订版本的提交元数据和补丁内容。
- `branch`：列出本地、远程或全部分支，可按包含关系过滤。
- `stash-push`：搁置当前工作区变更，可包含未跟踪文件并添加说明。
- `stash-list`：列出 stash 记录。
- `stash-apply`：应用指定 stash，默认 `stash@{0}`。
- `stash-pop`：应用并移除指定 stash，默认 `stash@{0}`。
- `stash-drop`：移除指定 stash。
- `amend-message`：修改指定未推送本地提交的提交消息，必须传入修订版本；未提供新消息时仅返回原消息供用户修改；工作区有变更时会自动临时搁置并恢复。
- `squash-local`：将首尾修订版本指定的连续未推送本地提交压缩为一个新提交；未提供新消息时仅返回原消息列表供用户修改；工作区有变更时会自动临时搁置并恢复。

参数、示例和安全说明见 `references/tool-reference.md`。

## 常见任务

### 检查仓库状态

先运行 `status`，再根据用户问题选择 `diff-unstaged`、`diff-staged` 或 `diff`。摘要使用较少上下文行；审查精确变更时使用更多上下文行。

### 查看历史

使用 `log` 查看近期提交。用户要求按日期范围查看提交时，使用 `--start-timestamp` 和 `--end-timestamp`。用户询问某个提交改了什么时，使用 `show` 查看指定修订版本。

### 暂存和提交

暂存或提交前，检查 status、已暂存 diff 和未暂存 diff。只暂存用户要求的文件或明显相关的文件。仅在用户明确要求创建提交时提交，并使用能反映变更原因的简洁提交信息。

### 搁置更改

用户要求“搁置”“stash”“保存当前改动以后再恢复”时，先检查 status。需要保留未跟踪文件时使用 `stash-push --include-untracked`。恢复前先用 `stash-list` 确认目标 stash；用户只想应用但保留 stash 时使用 `stash-apply`，用户想应用后删除 stash 时使用 `stash-pop`，删除 stash 前确认目标引用。

### 分支操作

存在歧义时，先使用 `branch` 列出分支，再切换或创建分支。`checkout` 前检查 status，避免与未提交工作产生意外交互。用户要求创建新分支时使用 `create-branch`；只有在用户指定基准时才传入 `--base-branch`。

### 修改本地提交消息

先用 `amend-message --revision <revision>` 读取原消息；用户确认新消息后再加 `--message <message>` 执行修改。仅修改未推送提交；脚本会自动临时 stash 并恢复工作区变更。

### 压缩本地提交

使用 `squash-local --from-revision <oldest> --to-revision <newest>` 指定连续范围。先不传 `--message` 读取原消息列表；用户确认新消息后再加 `--message <message>` 执行压缩。仅压缩未推送提交；脚本会自动临时 stash 并恢复工作区变更。

## 安全约束

拒绝或避免以 `-` 开头的 ref 类参数，包括目标、分支名、修订版本、stash 引用和包含关系过滤器。暂存具体文件时，将文件路径放在 `--` 之后传递。避免执行不属于此技能范围的破坏性 Git 命令，例如 hard reset、force push、删除分支或清理仓库；除非用户在此技能之外明确授权。