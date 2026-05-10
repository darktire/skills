#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CONTEXT_LINES = 3


class GitToolError(Exception):
    pass


def reject_option_like(value: str, label: str) -> None:
    if value.startswith("-"):
        raise GitToolError(f"Invalid {label}: {value!r} cannot start with '-'")


def has_worktree_changes(repo: Path) -> bool:
    return bool(run_git(repo, ["status", "--porcelain"]))


def ensure_clean_worktree(repo: Path) -> None:
    if has_worktree_changes(repo):
        raise GitToolError("Working tree must be clean for this operation")


def stash_worktree(repo: Path, message: str) -> str | None:
    if not has_worktree_changes(repo):
        return None
    run_git(repo, ["stash", "push", "--include-untracked", "-m", message])
    return "stash@{0}"


def restore_stash(repo: Path, stash_ref: str | None) -> None:
    if stash_ref:
        run_git(repo, ["stash", "pop", "--index", stash_ref])


def ensure_local_commit(repo: Path, revision: str) -> None:
    reject_option_like(revision, "revision")
    run_git(repo, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    branches = run_git(repo, ["branch", "-r", "--contains", revision])
    if branches.strip():
        raise GitToolError(f"Revision {revision!r} is contained in a remote branch")


def ensure_head_not_pushed(repo: Path) -> None:
    ensure_local_commit(repo, "HEAD")


def commit_env(repo: Path, commit_hash: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": run_git(repo, ["show", "-s", "--format=%an", commit_hash]),
            "GIT_AUTHOR_EMAIL": run_git(repo, ["show", "-s", "--format=%ae", commit_hash]),
            "GIT_AUTHOR_DATE": run_git(repo, ["show", "-s", "--format=%aI", commit_hash]),
            "GIT_COMMITTER_NAME": run_git(repo, ["show", "-s", "--format=%cn", commit_hash]),
            "GIT_COMMITTER_EMAIL": run_git(repo, ["show", "-s", "--format=%ce", commit_hash]),
            "GIT_COMMITTER_DATE": run_git(repo, ["show", "-s", "--format=%cI", commit_hash]),
        }
    )
    return env


def commit_message(repo: Path, commit_hash: str) -> str:
    return run_git(repo, ["log", "-1", "--format=%B", commit_hash])


def format_commit_messages(repo: Path, commits: list[str]) -> str:
    entries = []
    for commit_hash in commits:
        summary = run_git(repo, ["log", "-1", "--format=%h %s", commit_hash])
        entries.append(f"--- {summary} ---\n{commit_message(repo, commit_hash)}")
    return "\n\n".join(entries)


def run_git_process(repo: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def run_git(repo: Path, args: list[str], env: dict[str, str] | None = None) -> str:
    proc = run_git_process(repo, args, env=env)
    output = proc.stdout.rstrip()
    error = proc.stderr.rstrip()
    if proc.returncode != 0:
        message = error or output or f"git {' '.join(args)} failed"
        raise GitToolError(message)
    return output


def validate_repo(repo_path: str) -> Path:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists():
        raise GitToolError(f"Repository path does not exist: {repo}")
    if not repo.is_dir():
        raise GitToolError(f"Repository path is not a directory: {repo}")
    run_git(repo, ["rev-parse", "--show-toplevel"])
    return repo


def status(args: argparse.Namespace) -> str:
    return "Repository status:\n" + run_git(args.repo_path, ["status"])


def diff_unstaged(args: argparse.Namespace) -> str:
    diff = run_git(args.repo_path, [f"--no-pager", "diff", f"--unified={args.context_lines}"])
    return "Unstaged changes:\n" + diff


def diff_staged(args: argparse.Namespace) -> str:
    diff = run_git(args.repo_path, ["--no-pager", "diff", f"--unified={args.context_lines}", "--cached"])
    return "Staged changes:\n" + diff


def diff(args: argparse.Namespace) -> str:
    reject_option_like(args.target, "target")
    run_git(args.repo_path, ["rev-parse", "--verify", args.target])
    output = run_git(args.repo_path, ["--no-pager", "diff", f"--unified={args.context_lines}", args.target])
    return f"Diff with {args.target}:\n{output}"


def add(args: argparse.Namespace) -> str:
    if args.files == ["."]:
        run_git(args.repo_path, ["add", "."])
    else:
        run_git(args.repo_path, ["add", "--", *args.files])
    return "Files staged successfully"


def commit(args: argparse.Namespace) -> str:
    output = run_git(args.repo_path, ["commit", "-m", args.message])
    return "Changes committed successfully\n" + output


def reset(args: argparse.Namespace) -> str:
    run_git(args.repo_path, ["reset"])
    return "All staged changes reset"


def log(args: argparse.Namespace) -> str:
    command = [
        "--no-pager",
        "log",
        f"--max-count={args.max_count}",
        "--format=Commit: %H%nAuthor: %an%nDate: %ad%nMessage: %s%n",
    ]
    if args.start_timestamp:
        reject_option_like(args.start_timestamp, "start_timestamp")
        command.extend(["--since", args.start_timestamp])
    if args.end_timestamp:
        reject_option_like(args.end_timestamp, "end_timestamp")
        command.extend(["--until", args.end_timestamp])
    return "Commit history:\n" + run_git(args.repo_path, command)


def create_branch(args: argparse.Namespace) -> str:
    reject_option_like(args.branch_name, "branch_name")
    command = ["branch", args.branch_name]
    if args.base_branch:
        reject_option_like(args.base_branch, "base_branch")
        run_git(args.repo_path, ["rev-parse", "--verify", args.base_branch])
        command.append(args.base_branch)
    run_git(args.repo_path, command)
    base = args.base_branch or run_git(args.repo_path, ["branch", "--show-current"])
    return f"Created branch '{args.branch_name}' from '{base}'"


def checkout(args: argparse.Namespace) -> str:
    reject_option_like(args.branch_name, "branch_name")
    run_git(args.repo_path, ["rev-parse", "--verify", args.branch_name])
    run_git(args.repo_path, ["checkout", args.branch_name])
    return f"Switched to branch '{args.branch_name}'"


def show(args: argparse.Namespace) -> str:
    reject_option_like(args.revision, "revision")
    run_git(args.repo_path, ["rev-parse", "--verify", args.revision])
    return run_git(args.repo_path, ["--no-pager", "show", "--format=fuller", "--patch", args.revision])


def branch(args: argparse.Namespace) -> str:
    command = ["branch"]
    if args.branch_type == "remote":
        command.append("-r")
    elif args.branch_type == "all":
        command.append("-a")
    elif args.branch_type != "local":
        raise GitToolError(f"Invalid branch type: {args.branch_type}")
    if args.contains:
        reject_option_like(args.contains, "contains")
        command.extend(["--contains", args.contains])
    if args.not_contains:
        reject_option_like(args.not_contains, "not_contains")
        command.extend(["--no-contains", args.not_contains])
    return run_git(args.repo_path, command)


def stash_push(args: argparse.Namespace) -> str:
    command = ["stash", "push"]
    if args.include_untracked:
        command.append("--include-untracked")
    if args.message:
        command.extend(["-m", args.message])
    output = run_git(args.repo_path, command)
    return output or "No local changes to save"


def stash_list(args: argparse.Namespace) -> str:
    output = run_git(args.repo_path, ["stash", "list"])
    return output or "No stashes found"


def stash_apply(args: argparse.Namespace) -> str:
    reject_option_like(args.stash_ref, "stash_ref")
    output = run_git(args.repo_path, ["stash", "apply", args.stash_ref])
    return "Stash applied successfully\n" + output


def stash_pop(args: argparse.Namespace) -> str:
    reject_option_like(args.stash_ref, "stash_ref")
    output = run_git(args.repo_path, ["stash", "pop", args.stash_ref])
    return "Stash popped successfully\n" + output


def stash_drop(args: argparse.Namespace) -> str:
    reject_option_like(args.stash_ref, "stash_ref")
    output = run_git(args.repo_path, ["stash", "drop", args.stash_ref])
    return output or "Stash dropped successfully"


def amend_message(args: argparse.Namespace) -> str:
    ensure_local_commit(args.repo_path, args.revision)
    target = run_git(args.repo_path, ["rev-parse", "--verify", f"{args.revision}^{{commit}}"])
    if not args.message:
        return f"Original commit message for {args.revision}:\n{commit_message(args.repo_path, target)}"

    stashed = stash_worktree(args.repo_path, "git-helper amend-message temporary stash")
    try:
        if target == run_git(args.repo_path, ["rev-parse", "HEAD"]):
            output = run_git(args.repo_path, ["commit", "--amend", "-m", args.message])
            return "Commit message amended successfully\n" + output

        base = f"{target}^"
        commits = run_git(args.repo_path, ["rev-list", "--reverse", f"{base}..HEAD"]).splitlines()
        if target not in commits:
            raise GitToolError(f"Revision {args.revision!r} is not in the current HEAD history")
        for commit_hash in commits:
            ensure_local_commit(args.repo_path, commit_hash)

        parent = run_git(args.repo_path, ["rev-parse", f"{target}^"])
        rewritten = ""
        for commit_hash in commits:
            tree = run_git(args.repo_path, ["show", "-s", "--format=%T", commit_hash])
            message = args.message if commit_hash == target else commit_message(args.repo_path, commit_hash)
            rewritten = run_git(args.repo_path, ["commit-tree", tree, "-p", parent, "-m", message], env=commit_env(args.repo_path, commit_hash))
            parent = rewritten

        run_git(args.repo_path, ["update-ref", "refs/heads/" + run_git(args.repo_path, ["branch", "--show-current"]), rewritten])
        return f"Commit message amended successfully for {args.revision}"
    finally:
        restore_stash(args.repo_path, stashed)


def squash_local(args: argparse.Namespace) -> str:
    stashed = stash_worktree(args.repo_path, "git-helper squash-local temporary stash")
    try:
        ensure_local_commit(args.repo_path, args.from_revision)
        ensure_local_commit(args.repo_path, args.to_revision)
        from_commit = run_git(args.repo_path, ["rev-parse", "--verify", f"{args.from_revision}^{{commit}}"])
        to_commit = run_git(args.repo_path, ["rev-parse", "--verify", f"{args.to_revision}^{{commit}}"])
        base = f"{from_commit}^"
        commits_from_start = run_git(args.repo_path, ["rev-list", "--reverse", f"{base}..HEAD"]).splitlines()
        if from_commit not in commits_from_start or to_commit not in commits_from_start:
            raise GitToolError("from/to revisions must be in current HEAD history")
        to_index = commits_from_start.index(to_commit)
        if commits_from_start[0] != from_commit or to_index < 1:
            raise GitToolError("from/to revisions must describe at least two consecutive commits, ordered oldest to newest")
        squash_commits = commits_from_start[: to_index + 1]
        trailing_commits = commits_from_start[to_index + 1 :]

        for commit_hash in trailing_commits:
            ensure_local_commit(args.repo_path, commit_hash)
        if not args.message:
            return "Original commit messages for squash range:\n" + format_commit_messages(args.repo_path, squash_commits)

        parent = run_git(args.repo_path, ["rev-parse", f"{squash_commits[0]}^"])
        tree = run_git(args.repo_path, ["show", "-s", "--format=%T", squash_commits[-1]])
        rewritten = run_git(args.repo_path, ["commit-tree", tree, "-p", parent, "-m", args.message], env=commit_env(args.repo_path, squash_commits[-1]))
        parent = rewritten
        for commit_hash in trailing_commits:
            tree = run_git(args.repo_path, ["show", "-s", "--format=%T", commit_hash])
            message = commit_message(args.repo_path, commit_hash)
            rewritten = run_git(args.repo_path, ["commit-tree", tree, "-p", parent, "-m", message], env=commit_env(args.repo_path, commit_hash))
            parent = rewritten

        run_git(args.repo_path, ["update-ref", "refs/heads/" + run_git(args.repo_path, ["branch", "--show-current"]), rewritten])
        return f"Squashed {len(squash_commits)} local commits successfully"
    finally:
        restore_stash(args.repo_path, stashed)


def add_common_repo(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", dest="repo_path", required=True, type=validate_repo, help="Path to a Git repository")


def add_context(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--context-lines", type=int, default=DEFAULT_CONTEXT_LINES, help="Unified diff context lines")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Git repository operation wrapper")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    commands = {
        "status": status,
        "diff-unstaged": diff_unstaged,
        "diff-staged": diff_staged,
        "diff": diff,
        "add": add,
        "commit": commit,
        "reset": reset,
        "log": log,
        "create-branch": create_branch,
        "checkout": checkout,
        "show": show,
        "branch": branch,
        "stash-push": stash_push,
        "stash-list": stash_list,
        "stash-apply": stash_apply,
        "stash-pop": stash_pop,
        "stash-drop": stash_drop,
        "amend-message": amend_message,
        "squash-local": squash_local,
    }

    for name, handler in commands.items():
        sub = subparsers.add_parser(name)
        add_common_repo(sub)
        sub.set_defaults(handler=handler)

    subparsers.choices["diff-unstaged"].set_defaults(handler=diff_unstaged)
    add_context(subparsers.choices["diff-unstaged"])

    subparsers.choices["diff-staged"].set_defaults(handler=diff_staged)
    add_context(subparsers.choices["diff-staged"])

    diff_parser = subparsers.choices["diff"]
    add_context(diff_parser)
    diff_parser.add_argument("--target", required=True)

    add_parser = subparsers.choices["add"]
    add_parser.add_argument("--files", nargs="+", required=True)

    commit_parser = subparsers.choices["commit"]
    commit_parser.add_argument("--message", required=True)

    log_parser = subparsers.choices["log"]
    log_parser.add_argument("--max-count", type=int, default=10)
    log_parser.add_argument("--start-timestamp")
    log_parser.add_argument("--end-timestamp")

    create_branch_parser = subparsers.choices["create-branch"]
    create_branch_parser.add_argument("--branch-name", required=True)
    create_branch_parser.add_argument("--base-branch")

    checkout_parser = subparsers.choices["checkout"]
    checkout_parser.add_argument("--branch-name", required=True)

    show_parser = subparsers.choices["show"]
    show_parser.add_argument("--revision", required=True)

    branch_parser = subparsers.choices["branch"]
    branch_parser.add_argument("--branch-type", choices=["local", "remote", "all"], default="local")
    branch_parser.add_argument("--contains")
    branch_parser.add_argument("--not-contains")

    stash_push_parser = subparsers.choices["stash-push"]
    stash_push_parser.add_argument("--message")
    stash_push_parser.add_argument("--include-untracked", action="store_true")

    stash_apply_parser = subparsers.choices["stash-apply"]
    stash_apply_parser.add_argument("--stash-ref", default="stash@{0}")

    stash_pop_parser = subparsers.choices["stash-pop"]
    stash_pop_parser.add_argument("--stash-ref", default="stash@{0}")

    stash_drop_parser = subparsers.choices["stash-drop"]
    stash_drop_parser.add_argument("--stash-ref", required=True)

    amend_message_parser = subparsers.choices["amend-message"]
    amend_message_parser.add_argument("--message")
    amend_message_parser.add_argument("--revision", required=True)

    squash_local_parser = subparsers.choices["squash-local"]
    squash_local_parser.add_argument("--from-revision", required=True)
    squash_local_parser.add_argument("--to-revision", required=True)
    squash_local_parser.add_argument("--message")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        print(args.handler(args))
        return 0
    except GitToolError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
