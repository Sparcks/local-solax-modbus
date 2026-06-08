---
description: Mandatory git workflow — never push to main, always use a release branch + PR
---

# Release branch workflow (MANDATORY for all agents/models)

NEVER commit or push directly to `main`. Every change set MUST go through a
branch and a Pull Request that the user reviews and merges.

Follow these steps for any code change in this repository:

1. Make sure the working tree is clean and `main` is up to date:
   ```
   git checkout main
   git pull origin main
   ```

2. Create a branch BEFORE making any commits. Use:
   - `release/vX.Y.Z` for version releases
   - `fix/<short-desc>` for bug fixes
   - `feat/<short-desc>` for features
   ```
   git checkout -b release/vX.Y.Z
   ```

3. Make the code changes, then stage and commit on the branch:
   ```
   git add -A
   git commit -m "<conventional commit message>"
   ```

4. Push the BRANCH (never `main`):
   ```
   git push -u origin <branch-name>
   ```

5. Open a Pull Request into `main` and STOP. The user reviews and merges.
   Do not merge to `main` yourself unless the user explicitly asks.

## Hard rules
- Do NOT run `git push origin main` or `git commit` while `main` is checked out.
- If you find yourself on `main` with staged changes, create a branch first:
  `git switch -c fix/<short-desc>` (this carries the changes over), then commit.
- Bump `custom_components/local_solax_modbus/manifest.json` version and update
  `CHANGELOG.md` as part of the release branch when shipping a new version.
</CodeContent>
<parameter name="EmptyFile">false
