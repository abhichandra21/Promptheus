# Changelog

All notable changes to Promptheus are documented in this file.

## [0.3.1] - 2025-12-10

### Added
- MCP registry metadata to README for PyPI validation
- Updated server.json to latest schema (2025-10-17)

### Fixed
- Repository URL format for MCP registry compatibility
- Environment variables format for MCP registry validation

## [0.3.0] - 2025-12-05

### Added
- **Telemetry System**: Anonymous usage and performance metrics tracking
  - Token usage tracking across all providers
  - Performance latency metrics for API calls
  - Task type classification metrics (analysis vs generation)
  - Local JSONL storage with configurable sampling
  - Summary reporting via `promptheus telemetry summary`
  - Privacy-preserving design (no prompts or API keys stored)
  - Telemetry data visualization and analytics
- **MCP Server Enhancements**: Extended question handling in `refine_prompt` tool
  - Improved clarification workflow with better answer mapping
  - Enhanced error handling and response formatting
- **Shell Completions**: Added `mcp` and `telemetry` subcommands to bash/zsh completions
- **Web API Token Tracking**: Prompt refinement endpoint now returns token usage statistics
- **Test Coverage**: Comprehensive telemetry test suite
  - End-to-end telemetry tests (`test_telemetry_e2e.py`)
  - Extended telemetry unit tests (`test_telemetry_extended.py`)
  - Summary generation tests (`test_telemetry_summary.py`)
  - Telemetry testing script (`scripts/test-telemetry.sh`)

### Changed
- **Provider Token Tracking**: All providers now report input/output/total token usage
  - Added `last_input_tokens`, `last_output_tokens`, `last_total_tokens` attributes
  - Best-effort token tracking with graceful fallbacks for providers without usage data
- **History Management**: Added telemetry directory configuration support
  - `PROMPTHEUS_HISTORY_DIR` environment variable for custom location
  - Unified history and telemetry file management
- **MCP Server**: Enhanced `refine_prompt` tool with better question/answer workflow
- **Documentation**:
  - Updated CLAUDE.md with telemetry architecture details
  - Enhanced usage.md with telemetry commands and configuration
  - Added telemetry test script documentation

### Fixed
- Token counting for providers with inconsistent response formats
- Provider error handling for missing token usage metadata
- **Critical bug**: Fixed indentation issue in telemetry summary aggregation (src/promptheus/telemetry_summary.py:228)
  - Interface and provider metrics were not being collected due to incorrect indentation
  - Updated test assertions to match actual formatted output

### Environment Variables
- `PROMPTHEUS_TELEMETRY_ENABLED`: Enable/disable telemetry (default: 1)
- `PROMPTHEUS_TELEMETRY_FILE`: Custom telemetry file path (optional)
- `PROMPTHEUS_TELEMETRY_SAMPLE_RATE`: Sampling rate 0.0-1.0 (default: 1.0)
- `PROMPTHEUS_HISTORY_DIR`: Custom history directory location (optional)

### Technical Details
- Telemetry events stored in platform-specific directories
- JSONL format for efficient append-only logging
- Atomic file writes with file locking
- Comprehensive event schema with timestamps and metadata
- Provider-agnostic token tracking implementation

## [0.2.4] - 2025-11-25

### Added
- **CI/CD Workflow Badges**: Added status badges for GitHub Pages deployment, Docker builds, and package publishing
- **Web UI Guide**: Comprehensive web interface documentation with interactive examples
- **Sample Prompts Documentation**: Enhanced test prompts demonstrating adaptive task detection (analysis vs generation)
- **Version Display System**: Dev build tracking in web UI with automatic version detection
- **Docker Test Workflow**: Automated Docker container testing in CI pipeline

### Changed
- **Web UI Improvements**:
  - Redesigned message and error help styles
  - Improved mobile responsive layout and dropdown styling
  - Enhanced provider selection with better error handling
  - Added cache-busting for JavaScript and CSS files
  - Consistent dropdown styling with footer navigation
  - Improved About section design matching existing design system
- **Provider Configuration**: Fixed provider model selection to properly handle environment variables on manual switches
- **JSON Output**: Changed output key from 'prompt' to 'refined_prompt' for consistency
- **Dependency Management**: Standardized dependency specifications across configuration files
- **Documentation**: Renamed sample_prompts.txt to sample_prompts.md with improved formatting

### Fixed
- **Mobile Responsiveness**: Fixed horizontal scroll issues and layout problems on mobile devices
- **Web UI Streaming**: Added retry logic to stream endpoint test in CI
- **JSON Formatting**: Fixed JSON output formatting for CLI commands
- **Dropdown Sync**: Improved mobile dropdown synchronization and accessibility
- **No-cache Headers**: Added proper cache headers to index.html responses

### Technical Details
- Improved Docker test scripts and configuration
- Enhanced CI workflow with environment variable support
- Better error handling in web API endpoints
- Accessibility improvements in mobile UI components

## [0.2.0] - 2025-11-21

### Added
- **Web UI**: Full-featured web interface for prompt refinement and history management
  - FastAPI-based web server accessible via `promptheus web`
  - Browser-based interactive session with real-time feedback
  - History tracking and prompt management in web interface
  - API key validation and provider selection UI
- **Keyboard Shortcuts**: Enhanced CLI experience with custom key bindings
  - Enter to submit prompts
  - Shift+Enter for multiline input
  - Ctrl+C for graceful cancellation
- **Dynamic Model Discovery**: API-driven provider and model discovery
  - Provider normalization for consistent IDs across platforms
  - Automatic model fetching from provider endpoints
  - Enhanced provider configuration with validation
- **Docker Support**: Containerized deployment
  - Dockerfile for easy container builds
  - Support for running CLI and web UI in containers
- **GitHub Pages Documentation**: Comprehensive online documentation
  - Live documentation site for all features
  - Interactive examples and usage guides
  - Deployment workflow automation

### Changed
- **Refactored Help System**: Redesigned tooltip and help information
  - Improved CLI help text visibility and clarity
  - Better organized command documentation
  - Enhanced interactive help in web UI
- **Provider Configuration Precedence**: Improved config hierarchy
  - Support for provider-scoped environment variables
  - Better handling of model fallbacks
  - Clearer precedence rules for configuration
- **UI/UX Improvements**:
  - Enhanced interactive mode with better formatting
  - Improved error messages and user feedback
  - Better transient message handling in TUI
- **Updated Dependencies**:
  - Added `aiohttp` for async HTTP support
  - Added `fastapi` and `uvicorn` for web server
  - Updated Google Genai SDK for model compatibility

### Fixed
- **GitHub Pages Deployment**: Fixed deployment workflow and action configuration
- **Environment Loading**: Improved `.env` file detection and loading
- **API Response Handling**: Better error handling and sanitization across all providers
- **History Management**: Improved session persistence and history access

### Technical Details
- Implemented Textual-based TUI for interactive mode
- Added comprehensive logging throughout application
- Improved asyncio support for concurrent API calls
- Enhanced test coverage with pytest configuration
- Support for Python 3.10, 3.11, 3.12, and 3.13+

### Supported Providers
- Google Gemini (gemini-2.0-flash, gemini-1.5-pro, and more)
- Anthropic Claude (claude-3-5-sonnet, claude-3-opus)
- OpenAI (gpt-4o, gpt-4-turbo)
- Groq (llama-3.3-70b, mixtral-8x7b)
- Alibaba Qwen (qwen-max, qwen-plus)
- Zhipu GLM (glm-4-plus, glm-4-air)

## [0.1.2] - 2025-10-15

### Added
- Multi-provider support framework
- Session history and persistence
- Interactive refinement workflow
- Adaptive task detection (analysis vs generation)
- Question-answer-refinement pipeline
- Tab completion for interactive commands

### Changed
- Improved error handling and messages
- Enhanced provider abstraction layer
- Better configuration management

### Fixed
- API timeout handling
- Token limit validation
- Error message sanitization

## [0.1.1] - 2025-09-10

### Initial Features
- CLI interface for prompt refinement
- Support for multiple AI providers
- Basic question generation
- Session management
- Interactive mode (REPL)

---

## Release Process Notes

For future releases:
1. Update version in `pyproject.toml` and `src/promptheus/constants.py`
2. Update CHANGELOG.md with detailed changes
3. Run tests: `pytest -q`
4. Create commit: `git commit -m "Release v{VERSION}"`
5. Tag release: `git tag v{VERSION}`
6. Push: `git push origin main && git push origin v{VERSION}`
7. Build: `poetry build`
8. Publish: `poetry publish`
9. Create GitHub release with changelog
