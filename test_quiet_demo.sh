#!/bin/bash
# Demonstration script for Promptheus CLI functionality

echo "=== Testing Promptheus CLI Flags and Commands ==="
echo ""

echo "1. Testing --help shows current flags:"
poetry run promptheus --help | head -10
echo ""

echo "2. Testing -o flag with plain output format (will fail without API key, but tests parsing):"
echo "test" | poetry run promptheus -o plain 2>&1 | head -5
echo ""

echo "3. Testing -o flag with json output format (will fail without API key, but tests parsing):"
echo "test" | poetry run promptheus -o json 2>&1 | head -5
echo ""

echo "4. Testing --skip-questions flag (will fail without API key, but tests parsing):"
echo "test" | poetry run promptheus --skip-questions 2>&1 | head -5
echo ""

echo "5. Testing --refine flag (will fail without API key, but tests parsing):"
echo "test" | poetry run promptheus --refine 2>&1 | head -5
echo ""

echo "6. Testing subcommand help:"
echo "  history subcommand:"
poetry run promptheus history --help | head -5
echo ""
echo "  validate subcommand:"
poetry run promptheus validate --help | head -5
echo ""

echo "7. Testing template generation:"
echo "  Gemini template:"
poetry run promptheus template --providers gemini | head -5
echo ""
echo "  Multiple providers template:"
poetry run promptheus template --providers gemini,openai | head -8
echo ""

echo "All CLI parsing tests completed!"
echo "Note: Full functionality requires API keys to be configured"
