# git-backup

**Vibe coded with Cursor.**

Back up all public repositories of a user from **GitHub**, **GitLab**, or **Codeberg**.

- First run clones every repo into a `<username>/` subfolder.
- Subsequent runs pull new changes instead of re-cloning.
- Forks are skipped by default (opt in with `--include-forks`).

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- git

## Usage

```bash
# Via the bash wrapper (recommended — handles uv run automatically)
./backup.sh https://github.com/louaaron
./backup.sh https://codeberg.org/lucidrains
./backup.sh https://gitlab.com/users/lucidrains/projects

# Or directly via uv
uv run main.py https://github.com/louaaron

# Custom output directory
./backup.sh -o ~/backups https://github.com/louaaron

# Include forked repos
./backup.sh --include-forks https://github.com/louaaron
```
