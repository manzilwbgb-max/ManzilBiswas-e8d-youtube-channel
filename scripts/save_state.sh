#!/usr/bin/env bash
# Saves the agent's memory (the state/ folder) back to this repo.
# Retries when another job saved at the same moment.
set -u
msg="${1:-agent state}"
branch="${GITHUB_REF_NAME:-main}"
git config user.name "history-agent"
git config user.email "history-agent@users.noreply.github.com"
git add -A state
git add -A commands 2>/dev/null || true  # commands the app sent, once carried out
if git diff --cached --quiet; then
  echo "nothing new to save"
  exit 0
fi
git commit -q -m "$msg"
for i in 1 2 3 4 5 6; do
  if git pull -q --rebase origin "$branch" && git push -q origin "HEAD:$branch"; then
    echo "memory saved"
    exit 0
  fi
  git rebase --abort 2>/dev/null || true
  sleep $((i * 7))
done
echo "could not save the agent's memory"
exit 1
