#!/bin/bash
# Setup branch protection rules for Git Flow workflow

set -e

REPO="MementoRC/llm-task-framework"

echo "🔒 Setting up branch protection rules for $REPO..."

# Protect main/master branch
echo "🛡️  Protecting main branch..."
gh api repos/$REPO/branches/master/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"checks":[{"context":"Production Validation"},{"context":"Production Test - ubuntu-latest"},{"context":"Production Test - windows-latest"},{"context":"Production Test - macos-latest"}]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"require_last_push_approval":false}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field block_creations=false \
  --field required_conversation_resolution=true \
  --field lock_branch=false \
  --field allow_fork_syncing=true \
  || echo "⚠️  Could not set main branch protection (may need admin rights)"

# Protect development branch
echo "🛡️  Protecting development branch..."
gh api repos/$REPO/branches/development/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"checks":[{"context":"Development Status"},{"context":"Feature Branch Status"},{"context":"Quick Development Checks"}]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":0,"dismiss_stale_reviews":false,"require_code_owner_reviews":false,"require_last_push_approval":false}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field block_creations=false \
  --field required_conversation_resolution=false \
  --field lock_branch=false \
  --field allow_fork_syncing=true \
  || echo "⚠️  Could not set development branch protection (may need admin rights)"

echo "✅ Branch protection rules setup complete!"
echo ""
echo "📋 Summary:"
echo "  • main/master: Requires PR approval + status checks"
echo "  • development: Requires status checks (no approval needed for faster iteration)"
echo ""
echo "🔧 Manual setup required (if script failed):"
echo "  1. Go to: https://github.com/$REPO/settings/branches"
echo "  2. Add protection rules as configured in the script"
