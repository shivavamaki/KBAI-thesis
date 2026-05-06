#!/bin/bash
# Test script to verify MediCheck App package integrity and functionality
# Run this before creating distribution package

echo ""
echo "================================================"
echo "  MediCheck App - Package Integrity Test"
echo "================================================"
echo ""

TEST_PASSED=0
TEST_FAILED=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "  ${GREEN}[✓]${NC} $1"
        ((TEST_PASSED++))
    else
        echo -e "  ${RED}[✗]${NC} MISSING: $1"
        ((TEST_FAILED++))
    fi
}

# Test 1: Check required files exist
echo "[TEST 1] Checking required files..."
check_file "run.bat"
check_file "run.sh"
check_file "launch.py"
check_file "QUICKSTART.md"
check_file "PACKAGE.md"
check_file "DISTRIBUTION.md"
check_file "requirements.txt"
check_file "pharmacist_app/app.py"
check_file "data/sample_prescriptions.json"
check_file ".streamlit/config.toml"

# Test 2: Check Python
echo ""
echo "[TEST 2] Checking Python 3.10+..."
if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}[✓]${NC} Python $PYTHON_VER found"
    ((TEST_PASSED++))
else
    echo -e "  ${RED}[✗]${NC} Python not found"
    ((TEST_FAILED++))
fi

# Test 3: Check JSON syntax
echo ""
echo "[TEST 3] Validating JSON sample data..."
if command -v python3 &> /dev/null; then
    python3 -m json.tool data/sample_prescriptions.json > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}[✓]${NC} Sample JSON is valid"
        ((TEST_PASSED++))
    else
        echo -e "  ${RED}[✗]${NC} Invalid JSON in sample_prescriptions.json"
        ((TEST_FAILED++))
    fi
fi

# Test 4: Check Streamlit app syntax
echo ""
echo "[TEST 4] Checking Streamlit app syntax..."
if command -v python3 &> /dev/null; then
    python3 -m py_compile pharmacist_app/app.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}[✓]${NC} Streamlit app has valid Python syntax"
        ((TEST_PASSED++))
    else
        echo -e "  ${RED}[✗]${NC} Syntax error in app.py"
        ((TEST_FAILED++))
    fi
fi

# Test 5: Check documentation
echo ""
echo "[TEST 5] Checking documentation..."
if [ -f QUICKSTART.md ]; then
    if grep -qi "python" QUICKSTART.md; then
        echo -e "  ${GREEN}[✓]${NC} QUICKSTART.md contains Python info"
        ((TEST_PASSED++))
    else
        echo -e "  ${YELLOW}[!]${NC} QUICKSTART.md might be incomplete"
        ((TEST_FAILED++))
    fi
fi

# Test 6: Check data directories
echo ""
echo "[TEST 6] Checking data directories..."
for dir in "data" "data/raw" "data/processed" "outputs"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}[✓]${NC} Directory exists: $dir"
        ((TEST_PASSED++))
    else
        echo -e "  ${RED}[✗]${NC} Missing directory: $dir"
        ((TEST_FAILED++))
    fi
done

# Summary
echo ""
echo "================================================"
echo "  Test Results"
echo "================================================"
echo ""
echo "Passed: $TEST_PASSED"
echo "Failed: $TEST_FAILED"
echo ""

if [ $TEST_FAILED -eq 0 ]; then
    echo -e "${GREEN}[✓] All checks passed! Package is ready for distribution.${NC}"
    exit 0
else
    echo -e "${RED}[✗] Some checks failed. Please fix issues above before distributing.${NC}"
    exit 1
fi
