# Branch Management and PR Guidelines

## Branch Lifecycle

### 1. Branch Creation

- Create branches with descriptive names following the pattern:
  - `feature/` - for new features
  - `fix/` - for bug fixes
  - `refactor/` - for code refactoring
  - `docs/` - for documentation updates
  - Example: `fix/file-system-sync`

### 2. Development

- Keep branches focused on a single task/issue
- Commit regularly with clear messages
- Keep commits atomic and well-documented

### 3. Pull Request Creation

- Create PR when feature/fix is complete
- Include comprehensive description:

  ```markdown
  ## Changes

  - List of specific changes

  ## Testing

  - How changes were tested

  ## Related Issues

  - Link to related issues
  ```

- Add appropriate labels
- Request reviews from relevant team members

### 4. PR Review Process

- Address all review comments
- Keep discussion focused in PR comments
- Update branch with main if needed
- Ensure all checks pass

### 5. Merging

```bash
# Update main
git checkout main
git pull origin main

# Merge feature branch
git merge feature/branch-name

# Push changes
git push origin main

# Delete local branch
git branch -d feature/branch-name

# Delete remote branch
git push origin --delete feature/branch-name
```

### 6. Post-Merge Cleanup

- Delete merged branches both locally and remotely
- Update related issues/tickets
- Update documentation if needed

## Best Practices

### Branch Management

1. **Regular Cleanup**

   ```bash
   # List merged branches
   git branch --merged main

   # Delete multiple merged branches
   git branch --merged main | grep -v '^* main$' | xargs git branch -d

   # Delete remote branches
   git remote prune origin
   ```

2. **Branch Protection**
   - Protect main branch
   - Require PR reviews
   - Enable status checks

### PR Guidelines

1. **Size**

   - Keep PRs small and focused
   - Split large changes into multiple PRs
   - Aim for < 500 lines changed

2. **Documentation**

   - Update relevant docs
   - Include screenshots for UI changes
   - Document breaking changes

3. **Testing**
   - Add/update tests
   - Test edge cases
   - Verify in different environments

## Common Commands

### Branch Management

```bash
# List all branches
git branch -a

# Create and switch to new branch
git checkout -b feature/new-feature

# Delete branch locally
git branch -d branch-name

# Delete branch remotely
git push origin --delete branch-name

# Clean up deleted remote branches
git fetch --prune
```

### PR Management

```bash
# Update PR branch with main
git checkout feature/branch
git fetch origin
git rebase origin/main

# Squash commits before merge
git rebase -i HEAD~N  # N is number of commits

# Force push after rebase
git push --force-with-lease origin feature/branch
```

## Troubleshooting

### Common Issues

1. **Merge Conflicts**

   ```bash
   # Update branch with main
   git checkout feature/branch
   git fetch origin
   git rebase origin/main

   # Resolve conflicts
   # Edit conflicted files
   git add .
   git rebase --continue
   ```

2. **Accidental Commits**

   ```bash
   # Undo last commit
   git reset --soft HEAD^

   # Undo commits but keep changes
   git reset --mixed HEAD~N
   ```

3. **Branch Cleanup Errors**

   ```bash
   # Force delete branch
   git branch -D branch-name

   # Clean up refs
   git gc --prune=now
   ```

## Review Checklist

### Before Creating PR

- [ ] Branch is up to date with main
- [ ] All tests pass
- [ ] Code is properly formatted
- [ ] Documentation is updated
- [ ] Commit messages are clear

### Before Merging

- [ ] All review comments addressed
- [ ] CI checks pass
- [ ] No merge conflicts
- [ ] Changes tested in development environment
- [ ] Related issues updated

### After Merging

- [ ] Delete feature branch locally
- [ ] Delete feature branch remotely
- [ ] Update project documentation
- [ ] Close related issues
- [ ] Notify team of significant changes

## Emergency Procedures

### Reverting Merged Changes

```bash
# Find merge commit
git log --merges

# Create revert branch
git checkout -b fix/revert-feature

# Revert merge commit
git revert -m 1 <merge-commit-hash>

# Push and create PR
git push origin fix/revert-feature
```

### Recovering Deleted Branches

```bash
# List all refs including deleted
git reflog

# Recover branch
git checkout -b recovered-branch <commit-hash>
```

Remember: Always prioritize code quality and maintainability over speed. Take time to properly review and test changes before merging.
