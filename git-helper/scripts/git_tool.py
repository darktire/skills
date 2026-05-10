#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_CONTEXT_LINES = 3


class GitToolError(Exception):
    pass


def reject_option_like(value: str, label: str) -> None:
    if value.startswith("-"):
        raise GitToolError(f"Invalid {label}: {value!r} cannot start with '-'")


def run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
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
