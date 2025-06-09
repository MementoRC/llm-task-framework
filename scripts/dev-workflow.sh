#!/bin/bash
# Development workflow helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Function to create a new feature branch
create_feature() {
    local feature_name="$1"
    if [ -z "$feature_name" ]; then
        print_error "Feature name is required"
        echo "Usage: $0 feature <feature-name>"
        exit 1
    fi
    
    print_status "Creating feature branch: feature/$feature_name"
    
    # Ensure we're on development branch and up to date
    git checkout development
    git pull origin development
    
    # Create and checkout feature branch
    git checkout -b "feature/$feature_name"
    
    print_success "Created and switched to feature/$feature_name"
    print_status "You can now start developing your feature!"
    print_status "When ready, push with: git push -u origin feature/$feature_name"
}

# Function to create a hotfix branch
create_hotfix() {
    local hotfix_name="$1"
    if [ -z "$hotfix_name" ]; then
        print_error "Hotfix name is required"
        echo "Usage: $0 hotfix <hotfix-name>"
        exit 1
    fi
    
    print_status "Creating hotfix branch: hotfix/$hotfix_name"
    
    # Ensure we're on main branch and up to date
    git checkout main || git checkout master
    git pull origin $(git branch --show-current)
    
    # Create and checkout hotfix branch
    git checkout -b "hotfix/$hotfix_name"
    
    print_success "Created and switched to hotfix/$hotfix_name"
    print_warning "Remember: hotfix branches should be merged to BOTH main and development"
}

# Function to finish a feature (merge to development)
finish_feature() {
    local current_branch=$(git branch --show-current)
    
    if [[ ! "$current_branch" =~ ^feature/ ]]; then
        print_error "Not on a feature branch"
        exit 1
    fi
    
    print_status "Finishing feature branch: $current_branch"
    
    # Run local checks first
    print_status "Running pre-merge checks..."
    pixi run check || {
        print_error "Quality checks failed. Please fix issues before merging."
        exit 1
    }
    
    # Push feature branch if not already pushed
    if ! git ls-remote --exit-code --heads origin "$current_branch" > /dev/null 2>&1; then
        print_status "Pushing feature branch to remote..."
        git push -u origin "$current_branch"
    fi
    
    print_success "Feature branch is ready!"
    print_status "Next steps:"
    echo "  1. Create a PR: gh pr create --base development --title 'Your PR Title'"
    echo "  2. Or visit: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^/]*\/[^.]*\).*/\1/')/pull/new/$current_branch"
}

# Function to sync development branch
sync_dev() {
    print_status "Syncing development branch with remote..."
    
    local current_branch=$(git branch --show-current)
    git checkout development
    git pull origin development
    
    if [ "$current_branch" != "development" ]; then
        git checkout "$current_branch"
        print_status "Rebasing current branch on updated development..."
        git rebase development
    fi
    
    print_success "Development branch synced!"
}

# Function to run quality checks
check() {
    print_status "Running comprehensive quality checks..."
    
    echo "🔍 Formatting check..."
    pixi run format-check
    
    echo "🔍 Linting..."
    pixi run lint
    
    echo "🔍 Type checking..."
    pixi run typecheck
    
    echo "🧪 Running tests..."
    pixi run test-cov
    
    echo "🔒 Security checks..."
    pixi run -e security security-all || print_warning "Some security checks failed"
    
    print_success "All quality checks completed!"
}

# Function to fix common issues
fix() {
    print_status "Fixing common code issues..."
    
    echo "🔧 Formatting code..."
    pixi run format
    
    echo "🔧 Fixing linting issues..."
    pixi run lint-fix
    
    print_success "Code fixes applied!"
    print_status "Run 'pixi run check' to verify all issues are resolved"
}

# Main script logic
case "$1" in
    "feature")
        create_feature "$2"
        ;;
    "hotfix")
        create_hotfix "$2"
        ;;
    "finish")
        finish_feature
        ;;
    "sync")
        sync_dev
        ;;
    "check")
        check
        ;;
    "fix")
        fix
        ;;
    "help"|"--help"|"-h"|"")
        echo "Development Workflow Helper"
        echo ""
        echo "Usage: $0 <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  feature <name>    Create a new feature branch from development"
        echo "  hotfix <name>     Create a new hotfix branch from main"
        echo "  finish            Finish current feature branch and prepare for PR"
        echo "  sync              Sync development branch with remote"
        echo "  check             Run comprehensive quality checks"
        echo "  fix               Fix common formatting and linting issues"
        echo "  help              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 feature add-user-auth"
        echo "  $0 hotfix critical-security-fix"
        echo "  $0 finish"
        echo "  $0 check"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac