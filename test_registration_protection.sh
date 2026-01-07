#!/bin/bash
# TR-023: Registration Protection - Test Script
# Tests all security features of the registration endpoint

set -e  # Exit on error

echo "=========================================="
echo "TR-023: Registration Protection Tests"
echo "=========================================="
echo ""

API_URL="http://localhost:8000"
ADMIN_EMAIL="mrskwiw@gmail.com"
ADMIN_PASS="Random!1Pass"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Helper functions
function test_passed() {
    echo -e "${GREEN}✓ PASSED${NC}: $1"
    ((PASSED++))
}

function test_failed() {
    echo -e "${RED}✗ FAILED${NC}: $1"
    echo -e "  ${RED}Expected:${NC} $2"
    echo -e "  ${RED}Got:${NC} $3"
    ((FAILED++))
}

function test_info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Get admin token
function login_admin() {
    echo ""
    echo "==> Logging in as admin..."
    ADMIN_TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}" \
        | jq -r '.access_token // empty')

    if [ -z "$ADMIN_TOKEN" ]; then
        echo -e "${RED}ERROR: Could not login as admin${NC}"
        echo "Make sure the API is running and admin credentials are correct:"
        echo "  Email: $ADMIN_EMAIL"
        echo "  Password: $ADMIN_PASS"
        exit 1
    fi

    test_info "Admin token obtained"
}

# Test 1: Rate Limiting
function test_rate_limiting() {
    echo ""
    echo "==> Test 1: Rate Limiting (3/hour)"

    # Generate unique emails with timestamp
    TIMESTAMP=$(date +%s)

    # First 3 registrations should succeed
    for i in 1 2 3; do
        RESPONSE=$(curl -s -X POST "$API_URL/api/auth/register" \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"test${i}_${TIMESTAMP}@example.com\",\"password\":\"Test1234\",\"full_name\":\"Test User $i\"}")

        if echo "$RESPONSE" | grep -q '"access_token"'; then
            test_info "Registration $i/3 succeeded"
        else
            test_failed "Registration $i/3" "Success" "Failed: $RESPONSE"
        fi
    done

    # 4th registration should be blocked
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"test4_${TIMESTAMP}@example.com\",\"password\":\"Test1234\",\"full_name\":\"Test User 4\"}")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "429" ]; then
        test_passed "Rate limit enforced (4th registration blocked)"
    else
        test_failed "Rate limit" "HTTP 429" "HTTP $HTTP_CODE"
    fi
}

# Test 2: Password Strength Validation
function test_password_strength() {
    echo ""
    echo "==> Test 2: Password Strength Validation"

    TIMESTAMP=$(date +%s)

    # Weak password (no uppercase)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"weak1_${TIMESTAMP}@example.com\",\"password\":\"test1234\",\"full_name\":\"Weak User\"}")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "422" ]; then
        test_passed "Weak password rejected (no uppercase)"
    else
        test_failed "Password validation" "HTTP 422" "HTTP $HTTP_CODE"
    fi

    # Short password
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"weak2_${TIMESTAMP}@example.com\",\"password\":\"Test12\",\"full_name\":\"Weak User\"}")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "422" ]; then
        test_passed "Weak password rejected (too short)"
    else
        test_failed "Password validation" "HTTP 422" "HTTP $HTTP_CODE"
    fi
}

# Test 3: Mass Assignment Protection
function test_mass_assignment() {
    echo ""
    echo "==> Test 3: Mass Assignment Protection"

    TIMESTAMP=$(date +%s)

    # Attempt to inject is_superuser
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"hacker_${TIMESTAMP}@example.com\",\"password\":\"Hack1234\",\"full_name\":\"Hacker\",\"is_superuser\":true}")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "422" ]; then
        test_passed "Admin field injection blocked (is_superuser)"
    else
        test_failed "Mass assignment protection" "HTTP 422" "HTTP $HTTP_CODE"
    fi
}

# Test 4: Inactive by Default
function test_inactive_by_default() {
    echo ""
    echo "==> Test 4: New Users Inactive by Default"

    TIMESTAMP=$(date +%s)
    TEST_EMAIL="inactive_${TIMESTAMP}@example.com"
    TEST_PASS="Test1234"

    # Register new user
    RESPONSE=$(curl -s -X POST "$API_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\",\"full_name\":\"Inactive User\"}")

    IS_ACTIVE=$(echo "$RESPONSE" | jq -r '.user.is_active // empty')
    USER_ID=$(echo "$RESPONSE" | jq -r '.user.id // empty')

    if [ "$IS_ACTIVE" = "false" ]; then
        test_passed "New user created as inactive"
    else
        test_failed "User activation status" "is_active=false" "is_active=$IS_ACTIVE"
    fi

    # Attempt to login (should fail)
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")

    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "403" ]; then
        test_passed "Inactive user cannot login"
    else
        test_failed "Inactive user login" "HTTP 403" "HTTP $HTTP_CODE"
    fi

    # Store for next test
    export TEST_USER_ID="$USER_ID"
    export TEST_USER_EMAIL="$TEST_EMAIL"
    export TEST_USER_PASS="$TEST_PASS"
}

# Test 5: Admin Activation
function test_admin_activation() {
    echo ""
    echo "==> Test 5: Admin User Activation"

    if [ -z "$TEST_USER_ID" ]; then
        test_failed "Admin activation" "User ID from previous test" "No user ID"
        return
    fi

    # List inactive users
    RESPONSE=$(curl -s "$API_URL/api/admin/users/inactive" \
        -H "Authorization: Bearer $ADMIN_TOKEN")

    if echo "$RESPONSE" | jq -e ".[] | select(.id == \"$TEST_USER_ID\")" > /dev/null; then
        test_passed "Inactive user found in admin list"
    else
        test_failed "Admin list inactive users" "User in list" "User not found"
    fi

    # Activate user
    RESPONSE=$(curl -s -X POST "$API_URL/api/admin/users/$TEST_USER_ID/activate" \
        -H "Authorization: Bearer $ADMIN_TOKEN")

    IS_ACTIVE=$(echo "$RESPONSE" | jq -r '.is_active // empty')

    if [ "$IS_ACTIVE" = "true" ]; then
        test_passed "Admin activated user successfully"
    else
        test_failed "Admin activation" "is_active=true" "is_active=$IS_ACTIVE"
    fi

    # User can now login
    RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASS\"}")

    if echo "$RESPONSE" | grep -q '"access_token"'; then
        test_passed "Activated user can now login"
    else
        test_failed "Activated user login" "Success" "Failed: $RESPONSE"
    fi
}

# Test 6: Admin-Only Operations
function test_admin_only_operations() {
    echo ""
    echo "==> Test 6: Admin-Only Operation Protection"

    # Try to access admin endpoint without token
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/api/admin/users")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
        test_passed "Admin endpoint requires authentication"
    else
        test_failed "Admin endpoint protection" "HTTP 401/403" "HTTP $HTTP_CODE"
    fi

    # Get non-admin token (if user was created in previous test)
    if [ ! -z "$TEST_USER_EMAIL" ]; then
        USER_TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASS\"}" \
            | jq -r '.access_token // empty')

        if [ ! -z "$USER_TOKEN" ]; then
            # Try to access admin endpoint with non-admin token
            RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/api/admin/users" \
                -H "Authorization: Bearer $USER_TOKEN")
            HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

            if [ "$HTTP_CODE" = "403" ]; then
                test_passed "Non-admin cannot access admin endpoints"
            else
                test_failed "Admin privilege check" "HTTP 403" "HTTP $HTTP_CODE"
            fi
        fi
    fi
}

# Test 7: Self-Protection (Cannot deactivate/demote self)
function test_self_protection() {
    echo ""
    echo "==> Test 7: Self-Protection (Cannot deactivate/demote self)"

    # Get admin user ID
    ADMIN_USER_ID=$(curl -s -X POST "$API_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}" \
        | jq -r '.user.id // empty')

    # Try to deactivate self
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/admin/users/$ADMIN_USER_ID/deactivate" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "400" ]; then
        test_passed "Admin cannot deactivate themselves"
    else
        test_failed "Self-deactivation protection" "HTTP 400" "HTTP $HTTP_CODE"
    fi

    # Try to demote self
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/admin/users/$ADMIN_USER_ID/demote" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$HTTP_CODE" = "400" ]; then
        test_passed "Admin cannot demote themselves"
    else
        test_failed "Self-demotion protection" "HTTP 400" "HTTP $HTTP_CODE"
    fi
}

# Main execution
echo "Starting tests..."
echo ""

# Login as admin first
login_admin

# Run all tests
test_rate_limiting
test_password_strength
test_mass_assignment
test_inactive_by_default
test_admin_activation
test_admin_only_operations
test_self_protection

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}PASSED: $PASSED${NC}"
echo -e "${RED}FAILED: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
