# Issue tracker workflow

The implementation issues for this repository live in `ADISAK-PORNCHAROEN/ocr-backend`. Issue #1 is the parent product specification; its acceptance details and child issues define the implementation scope.

## Read the source of truth

Use the authenticated GitHub CLI. Do not copy issue bodies into this file because GitHub remains canonical.

```powershell
gh issue list --repo ADISAK-PORNCHAROEN/ocr-backend --state open --limit 100
gh issue view ISSUE_NUMBER --repo ADISAK-PORNCHAROEN/ocr-backend --json title,body,comments,url
```

At the start of a multi-issue run, record the open issue numbers and inspect each issue's acceptance criteria and dependency links. Preserve that initial set even if issue status changes during implementation.

## Update completion

Work on `develop`, make focused commits, and merge through a pull request into `main`. After the merged change proves an issue's acceptance criteria, add a concise issue comment with the PR, relevant commits and verification commands, then close that issue. Do not close an issue because code was merely written or because a related issue was merged. Close parent issue #1 after all child work is merged and its product-level requirements have evidence.
