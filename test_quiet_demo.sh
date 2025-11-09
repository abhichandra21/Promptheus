#!/bin/bash
# Demonstration script for quiet mode functionality

echo "=== Testing Quiet Mode Flags ==="
echo ""

echo "1. Testing --help shows new flags:"
promptheus --help | grep -E "(quiet-output|force-interactive|output-format)"
echo ""

echo "2. Testing -o flag with plain output format (will fail without API key, but tests parsing):"
promptheus -o plain "test" 2>&1 | head -5
echo ""

echo "3. Testing --quiet-output flag (will fail without API key, but tests parsing):"
promptheus --quiet-output "test" 2>&1 | head -5
echo ""

echo "4. Testing --force-interactive flag (will fail without API key, but tests parsing):"
promptheus --force-interactive "test" 2>&1 | head -5
echo ""

echo "All flag parsing tests completed!"
echo "Note: Full functionality requires API keys to be configured"
