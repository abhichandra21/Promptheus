#!/bin/bash
# Test telemetry end-to-end with real CLI commands

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Promptheus Telemetry E2E Tests ===${NC}\n"

# Set up test environment
TEST_DIR=$(mktemp -d)
TELEMETRY_FILE="$TEST_DIR/telemetry.jsonl"
HISTORY_DIR="$TEST_DIR/history"

export PROMPTHEUS_TELEMETRY_FILE="$TELEMETRY_FILE"
export PROMPTHEUS_TELEMETRY_ENABLED=1
export PROMPTHEUS_TELEMETRY_SAMPLE_RATE=1.0
export PROMPTHEUS_ENABLE_HISTORY=1
export PROMPTHEUS_HISTORY_DIR="$HISTORY_DIR"

echo "Test directory: $TEST_DIR"
echo "Telemetry file: $TELEMETRY_FILE"
echo "History directory: $HISTORY_DIR (isolated from ~/.promptheus)"
echo ""

# Function to count events in telemetry file
count_events() {
    if [ -f "$TELEMETRY_FILE" ]; then
        wc -l < "$TELEMETRY_FILE" | tr -d ' '
    else
        echo "0"
    fi
}

# Function to show last N events
show_events() {
    local n=${1:-5}
    if [ -f "$TELEMETRY_FILE" ]; then
        echo -e "${BLUE}Last $n telemetry events:${NC}"
        tail -n "$n" "$TELEMETRY_FILE" | jq -C '.'
    else
        echo "No telemetry file found"
    fi
}

# Function to check for a specific field in events
check_field() {
    local field=$1
    local expected=$2
    if [ -f "$TELEMETRY_FILE" ]; then
        local actual=$(tail -n 1 "$TELEMETRY_FILE" | jq -r ".$field")
        if [ "$actual" = "$expected" ]; then
            echo -e "${GREEN}✓${NC} $field = $expected"
        else
            echo -e "${RED}✗${NC} $field = $actual (expected $expected)"
        fi
    fi
}

# Test 1: Basic CLI with --skip-questions
echo -e "${BLUE}Test 1: CLI with --skip-questions${NC}"
promptheus --skip-questions "Write a function to add two numbers" > /dev/null 2>&1 || true
EVENTS_AFTER_1=$(count_events)
echo "Events recorded: $EVENTS_AFTER_1"
if [ "$EVENTS_AFTER_1" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Telemetry recorded"
    check_field "interface" "cli"
    check_field "skip_questions" "true"
else
    echo -e "${RED}✗${NC} No telemetry recorded"
fi
echo ""

# Test 2: Multiple runs append to same file
echo -e "${BLUE}Test 2: Multiple runs append${NC}"
EVENTS_BEFORE=$(count_events)
for i in {1..3}; do
    promptheus --skip-questions "Test prompt $i" > /dev/null 2>&1 || true
done
EVENTS_AFTER=$(count_events)
NEW_EVENTS=$((EVENTS_AFTER - EVENTS_BEFORE))
echo "New events recorded: $NEW_EVENTS"
if [ "$NEW_EVENTS" -ge 3 ]; then
    echo -e "${GREEN}✓${NC} Multiple runs appended successfully"
else
    echo -e "${RED}✗${NC} Expected at least 3 new events, got $NEW_EVENTS"
fi
echo ""

# Test 3: Telemetry disabled
echo -e "${BLUE}Test 3: Telemetry disabled${NC}"
export PROMPTHEUS_TELEMETRY_ENABLED=0
DISABLED_FILE="$TEST_DIR/disabled.jsonl"
export PROMPTHEUS_TELEMETRY_FILE="$DISABLED_FILE"
promptheus --skip-questions "Should not record" > /dev/null 2>&1 || true
if [ ! -f "$DISABLED_FILE" ] || [ ! -s "$DISABLED_FILE" ]; then
    echo -e "${GREEN}✓${NC} No telemetry when disabled"
else
    echo -e "${RED}✗${NC} Telemetry recorded despite being disabled"
fi
export PROMPTHEUS_TELEMETRY_ENABLED=1
export PROMPTHEUS_TELEMETRY_FILE="$TELEMETRY_FILE"
echo ""

# Test 4: Privacy check - no prompt text
echo -e "${BLUE}Test 4: Privacy - prompt text not stored${NC}"
SECRET="VERY_SECRET_xyz123"
promptheus --skip-questions "This prompt contains $SECRET" > /dev/null 2>&1 || true
if grep -q "$SECRET" "$TELEMETRY_FILE" 2>/dev/null; then
    echo -e "${RED}✗${NC} Secret text found in telemetry!"
    grep "$SECRET" "$TELEMETRY_FILE"
else
    echo -e "${GREEN}✓${NC} Prompt text not stored (privacy preserved)"
fi
echo ""

# Test 5: Schema and required fields
echo -e "${BLUE}Test 5: Required fields present${NC}"
if [ -f "$TELEMETRY_FILE" ]; then
    LAST_EVENT=$(tail -n 1 "$TELEMETRY_FILE")
    echo "Checking last event..."

    for field in "timestamp" "event_type" "schema_version" "session_id" "run_id" "interface"; do
        VALUE=$(echo "$LAST_EVENT" | jq -r ".$field")
        if [ "$VALUE" != "null" ] && [ -n "$VALUE" ]; then
            echo -e "${GREEN}✓${NC} $field: $VALUE"
        else
            echo -e "${RED}✗${NC} Missing or null: $field"
        fi
    done
fi
echo ""

# Test 6: Default telemetry location
echo -e "${BLUE}Test 6: Default telemetry location${NC}"
DEFAULT_PATH="$HOME/.promptheus/telemetry.jsonl"
echo "Default path should be: $DEFAULT_PATH"
if [ -d "$HOME/.promptheus" ]; then
    echo -e "${GREEN}✓${NC} Default directory exists"
else
    echo -e "${BLUE}ℹ${NC}  Default directory doesn't exist yet (created on first use)"
fi
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
show_events 3

echo -e "\n${BLUE}Telemetry file location:${NC} $TELEMETRY_FILE"
echo -e "${BLUE}Total events:${NC} $(count_events)"

# Cleanup
echo -e "\n${BLUE}Cleanup:${NC}"
echo "Test directory: $TEST_DIR"
echo "To inspect manually: cat $TELEMETRY_FILE | jq"
echo "To clean up: rm -rf $TEST_DIR"

echo -e "\n${GREEN}Tests complete!${NC}"
