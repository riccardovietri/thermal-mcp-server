#!/bin/bash
# Thermal MCP Server - Test Runner Script
# Runs comprehensive validation suite including published case studies

set -e  # Exit on error

echo "======================================================================="
echo "THERMAL MCP SERVER - COMPREHENSIVE TEST SUITE"
echo "======================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
    fi
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing test dependencies..."
    pip install -q pytest numpy
fi

echo -e "${BLUE}Running Unit Tests...${NC}"
echo "---"
if python -m pytest tests/test_coldplate.py -v --tb=short; then
    unit_tests_result=0
else
    unit_tests_result=1
fi
echo ""

echo -e "${BLUE}Running Validation Tests (First Principles)...${NC}"
echo "---"
if python -m pytest tests/test_validation.py -v --tb=short; then
    validation_tests_result=0
else
    validation_tests_result=1
fi
echo ""

echo -e "${BLUE}Running Published Case Study Validation...${NC}"
echo "---"
if python -m pytest tests/test_published_case_studies.py -v --tb=short; then
    case_study_result=0
else
    case_study_result=1
fi
echo ""

echo "======================================================================="
echo "TEST SUMMARY"
echo "======================================================================="
print_status $unit_tests_result "Unit Tests (49 tests)"
print_status $validation_tests_result "Validation Tests (First Principles)"
print_status $case_study_result "Published Case Studies (10 tests)"
echo "---"

# Count total tests
total_tests=$(python -m pytest tests/ --collect-only -q 2>/dev/null | grep "test" | wc -l)
echo "Total: $total_tests tests"
echo ""

# Exit with error if any test suite failed
if [ $unit_tests_result -ne 0 ] || [ $validation_tests_result -ne 0 ] || [ $case_study_result -ne 0 ]; then
    echo -e "${RED}BUILD FAILED${NC}: Some tests did not pass"
    echo "======================================================================="
    exit 1
else
    echo -e "${GREEN}BUILD SUCCESSFUL${NC}: All tests passed!"
    echo "======================================================================="
    exit 0
fi
