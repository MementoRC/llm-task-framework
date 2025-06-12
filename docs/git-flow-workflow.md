# Git Flow Development Workflow

## Overview

This project uses a **Git Flow** branching strategy designed for collaborative development with robust CI/CD integration. The workflow provides fast feedback for feature development while maintaining production stability.

## Branch Structure

```
main/master     ←── Production-ready releases
     ↑
development     ←── Integration branch (your daily work)
     ↑
feature/*       ←── Feature development branches
hotfix/*        ←── Critical production fixes
```

### Branch Purposes

| Branch | Purpose | Protection | Deployment |
|--------|---------|------------|------------|
| `main/master` | Production releases | ✅ PR required + reviews | 🚀 Auto-deploy to production |
| `development` | Integration testing | ⚠️ Status checks required | 🧪 Development environment |
| `feature/*` | Feature development | ℹ️ Quality checks | 💻 Local/preview only |
| `hotfix/*` | Critical fixes | ✅ PR to main + development | 🚨 Emergency deployment |

## Development Workflow

### 🚀 **Quick Start**

```bash
# Setup project
git clone <repository>
cd llm-task-framework
pixi install

# Setup development workflow helper
chmod +x scripts/dev-workflow.sh
```

### 🔄 **Daily Development Cycle**

#### 1. **Start New Feature**
```bash
# Using helper script (recommended)
./scripts/dev-workflow.sh feature add-user-authentication

# Or manually
git checkout development
git pull origin development
git checkout -b feature/add-user-authentication
```

#### 2. **Develop and Test**
```bash
# Make your changes
# ... coding ...

# Quick local checks
pixi run format-check    # Check formatting
pixi run lint           # Check linting
pixi run test-fast      # Quick tests

# Full quality check before commit
./scripts/dev-workflow.sh check
# OR: pixi run check
```

#### 3. **Commit and Push**
```bash
git add .
git commit -m "feat: add user authentication system"
git push -u origin feature/add-user-authentication
```

#### 4. **Create Pull Request**
```bash
# Using GitHub CLI (recommended)
gh pr create --base development --title "feat: add user authentication system"

# Or use the helper script
./scripts/dev-workflow.sh finish
```

#### 5. **Merge and Cleanup**
```bash
# After PR is approved and merged
git checkout development
git pull origin development
git branch -d feature/add-user-authentication
```

### 🚨 **Hotfix Workflow**

For critical production fixes:

```bash
# Create hotfix branch from main
./scripts/dev-workflow.sh hotfix critical-security-patch

# Make the fix
# ... fix the issue ...

# Test thoroughly
pixi run check

# Create PR to main
gh pr create --base main --title "hotfix: critical security patch"

# After merge to main, also merge to development
gh pr create --base development --title "hotfix: critical security patch (sync)"
```

## CI/CD Integration

### 🔄 **Automated Workflows**

| Workflow | Triggers | Purpose | Duration |
|----------|----------|---------|----------|
| **Feature Branch** | PR to development | Quick validation | ~5 min |
| **Development Integration** | Push to development | Comprehensive testing | ~15 min |
| **Production Release** | Push to main | Full validation + release | ~25 min |
| **Security Scanning** | All branches | Security checks | ~10 min |

### ✅ **Quality Gates**

#### Feature Branch (PR to development)
- ✅ Code formatting check
- ✅ Linting validation
- ✅ Type checking
- ✅ Test suite execution
- ✅ Security scanning

#### Development Integration
- ✅ All feature checks +
- ✅ Integration tests
- ✅ Package building
- ✅ Multi-environment testing

#### Production Release (main)
- ✅ All development checks +
- ✅ Multi-platform testing
- ✅ Comprehensive security validation
- ✅ Automated versioning
- ✅ PyPI publishing
- ✅ GitHub release creation

## Local Development Commands

### 🛠️ **Development Helper Script**

```bash
# Create feature branch
./scripts/dev-workflow.sh feature <name>

# Create hotfix branch
./scripts/dev-workflow.sh hotfix <name>

# Finish feature (prepare for PR)
./scripts/dev-workflow.sh finish

# Sync with development
./scripts/dev-workflow.sh sync

# Run quality checks
./scripts/dev-workflow.sh check

# Fix common issues
./scripts/dev-workflow.sh fix
```

### ⚡ **Pixi Commands**

```bash
# Quick development
pixi run test-fast      # Fast tests
pixi run format-check   # Check formatting
pixi run lint          # Check linting

# Quality assurance
pixi run check         # Full quality check
pixi run test-cov      # Tests with coverage
pixi run typecheck     # Type validation

# Security
pixi run -e security security-all  # All security checks

# Documentation
pixi run -e docs docs-serve  # Serve docs locally

# Building
pixi run build         # Build packages
```

## Best Practices

### 📝 **Commit Messages**

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add user authentication system
fix: resolve memory leak in data processing
docs: update API documentation
test: add integration tests for auth flow
refactor: simplify error handling logic
```

### 🔀 **Pull Request Guidelines**

**Feature PRs (to development):**
- ✅ Small, focused changes
- ✅ Comprehensive tests
- ✅ Updated documentation
- ✅ All CI checks passing

**Production PRs (to main):**
- ✅ Batched features from development
- ✅ Thoroughly tested
- ✅ Release notes prepared
- ✅ Breaking changes documented

### 🧪 **Testing Strategy**

```bash
# Local testing pyramid
pixi run test-fast        # Unit tests (< 1 min)
pixi run test            # Full test suite (< 5 min)
pixi run test-integration # Integration tests (< 10 min)
```

**Test Categories:**
- **Unit tests**: Fast, isolated component testing
- **Integration tests**: Component interaction testing
- **MCP tests**: MCP server functionality
- **LLM tests**: AI provider integration (requires API keys)

## Troubleshooting

### 🔧 **Common Issues**

#### **"CI checks failing"**
```bash
# Run same checks locally
./scripts/dev-workflow.sh check

# Fix formatting/linting
./scripts/dev-workflow.sh fix

# Check specific issues
pixi run lint           # See linting errors
pixi run typecheck      # See type errors
pixi run test -v        # See test failures
```

#### **"Merge conflicts with development"**
```bash
# Sync and rebase
./scripts/dev-workflow.sh sync

# If conflicts persist
git checkout development
git pull origin development
git checkout feature/your-branch
git rebase development
# Resolve conflicts and continue
```

#### **"Branch protection preventing push"**
- ✅ Ensure all CI checks pass
- ✅ Get required PR approvals
- ✅ Use PR workflow instead of direct push

#### **"Environment setup issues"**
```bash
# Reinstall environment
rm -rf .pixi
pixi install

# Check environment
pixi info
pixi list
```

## Advanced Workflows

### 🏗️ **Release Management**

Releases are automatically created when changes are merged to main:

1. **Automatic Versioning**: Based on conventional commits
   - `feat:` → Minor version bump
   - `fix:` → Patch version bump
   - `BREAKING CHANGE:` → Major version bump

2. **Manual Release**: Use workflow dispatch
   ```bash
   gh workflow run "Production Release" -f release_type=minor
   ```

3. **Release Assets**: Automatically includes
   - 📦 Python wheel and source distribution
   - 📝 Auto-generated changelog
   - 🏷️ Git tag and GitHub release

### 🔄 **Branch Synchronization**

The workflow automatically:
- ✅ Syncs development branch after production releases
- ✅ Updates version numbers across branches
- ✅ Maintains changelog consistency

## Monitoring and Metrics

### 📊 **CI/CD Metrics**
- Build success rates
- Test execution times
- Security scan results
- Deployment frequency

### 🔍 **Quality Metrics**
- Code coverage trends
- Linting violation counts
- Security vulnerability tracking
- Dependency health status

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **Start feature** | `./scripts/dev-workflow.sh feature <name>` |
| **Local checks** | `./scripts/dev-workflow.sh check` |
| **Fix issues** | `./scripts/dev-workflow.sh fix` |
| **Create PR** | `./scripts/dev-workflow.sh finish` |
| **Sync development** | `./scripts/dev-workflow.sh sync` |
| **Emergency fix** | `./scripts/dev-workflow.sh hotfix <name>` |

**🔗 Useful Links:**
- [Repository](https://github.com/MementoRC/llm-task-framework)
- [CI/CD Pipelines](https://github.com/MementoRC/llm-task-framework/actions)
- [Release Notes](https://github.com/MementoRC/llm-task-framework/releases)
- [Security Advisories](https://github.com/MementoRC/llm-task-framework/security)
