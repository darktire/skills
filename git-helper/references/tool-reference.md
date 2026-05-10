# Git 工具参考

本文档说明随附脚本支持的本地 Git 操作。脚本使用 Git CLI 参数数组执行命令，不使用 shell 字符串插值。

## 通用参数

- `repo_path` / `--repo`：现有 Git 仓库路径。
- `context_lines` / `--context-lines`：统一 diff 的上下文行数，默认值为 `3`。

## 操作

### git_status

显示工作区状态。

```bash
python scripts/git_tool.py status --repo <repo_path>
```

等效 Git 命令：`git status`。

### git_diff_unstaged

显示工作目录中尚未暂存的变更。

```bash
python scripts/git_tool.py diff-unstaged --repo <repo_path> --context-lines 3
```

等效 Git 命令：`git diff --unified=<context_lines>`。

### git_diff_staged

显示已暂存、准备提交的变更。

```bash
python scripts/git_tool.py diff-staged --repo <repo_path> --context-lines 3
```

等效 Git 命令：`git diff --unified=<context_lines> --cached`。

### git_diff

显示工作区与目标分支、标签或提交之间的差异。

```bash
python scripts/git_tool.py diff --repo <repo_path> --target <revision> --context-lines 3
```

等效 Git 命令：`git diff --unified=<context_lines> <target>`。先使用 `git rev-parse --verify <target>` 验证目标，并拒绝以 `-` 开头的目标。

### git_add

暂存文件内容。

```bash
python scripts/git_tool.py add --repo <repo_path> --files <path1> <path2>
```

等效 Git 命令：`git add -- <paths...>`。特殊文件列表 `.` 会暂存仓库根目录。

### git_commit

将已暂存变更记录为提交。

```bash
python scripts/git_tool.py commit --repo <repo_path> --message "Commit message"
```

等效 Git 命令：`git commit -m <message>`。仅在检查 status 和已暂存 diff 后提交，并且必须是用户明确要求提交时才提交。

### git_reset

取消暂存所有已暂存变更。

```bash
python scripts/git_tool.py reset --repo <repo_path>
```

等效 Git 命令：`git reset`。这不是 hard reset；工作区变更会保留。

### git_log

显示提交历史，可按日期过滤。

```bash
python scripts/git_tool.py log --repo <repo_path> --max-count 10
python scripts/git_tool.py log --repo <repo_path> --start-timestamp "2024-01-15" --end-timestamp "2024-02-01"
```

等效 Git 命令：`git log --max-count=<n> --format=...`，提供日期过滤时额外使用 `--since` 和 `--until`。拒绝以 `-` 开头的时间戳值。

### git_create_branch

基于当前分支或可选基准分支创建新分支。

```bash
python scripts/git_tool.py create-branch --repo <repo_path> --branch-name <name>
python scripts/git_tool.py create-branch --repo <repo_path> --branch-name <name> --base-branch <base>
```

等效 Git 命令：`git branch <branch_name> [base_branch]`。拒绝以 `-` 开头的分支名和基准分支名。

### git_checkout

切换分支。

```bash
python scripts/git_tool.py checkout --repo <repo_path> --branch-name <name>
```

等效 Git 命令：`git checkout <branch_name>`。先验证分支或修订版本，并拒绝以 `-` 开头的值。

### git_show

显示某个提交或修订版本的元数据和补丁内容。

```bash
python scripts/git_tool.py show --repo <repo_path> --revision <revision>
```

等效 Git 命令：`git show --format=fuller --patch <revision>`。拒绝以 `-` 开头的修订版本。

### git_branch

列出分支。

```bash
python scripts/git_tool.py branch --repo <repo_path> --branch-type local
python scripts/git_tool.py branch --repo <repo_path> --branch-type remote
python scripts/git_tool.py branch --repo <repo_path> --branch-type all
python scripts/git_tool.py branch --repo <repo_path> --branch-type all --contains <sha>
python scripts/git_tool.py branch --repo <repo_path> --branch-type all --not-contains <sha>
```

等效 Git 命令：`git branch`、`git branch -r` 或 `git branch -a`，可附加 `--contains` / `--no-contains`。拒绝以 `-` 开头的包含关系值。

## 运行时说明

- 仓库访问受本地文件系统和工具权限控制。
- 脚本依赖 PATH 中可用的 `git` 可执行文件。