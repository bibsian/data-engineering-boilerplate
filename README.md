# data-engineering-boilerplate
This is a boilerplate repository of containerized services. I have repurposed this from a company's take home exercise whom I will not mention. I plan to explore different explore different architectures as well as explore agent driven development starting with this boilerplate.

## Worktree Helper (`wt`)

`scripts/wt` is a git worktree helper that works from any git repo on your machine.

**Install** (one-time):
```bash
cp scripts/wt ~/.local/bin/wt && chmod +x ~/.local/bin/wt
```

**Shell wrapper** (add to `~/.zshrc` or `~/.bashrc`):
```bash
wt() {
  local out status
  out="$(command wt "$@")"
  status=$?
  if [[ "$out" == EVAL:* ]]; then eval "${out#EVAL:}"; else [[ -n "$out" ]] && echo "$out"; fi
  return $status
}
```

The `EVAL:` sentinel is how the script signals "run this in your shell" — used by `switch` (to cd) and `create --go` (to cd + launch claude).

**Commands:**
| Command | Description |
|---|---|
| `wt create <branch>` | Create a new worktree + branch |
| `wt create <branch> --go` | Create worktree, cd in, and launch `claude` |
| `wt list` | List all worktrees |
| `wt switch <branch>` | cd into a worktree |
| `wt delete <branch>` | Remove worktree + local branch |
