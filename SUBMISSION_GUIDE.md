# MCP Registry Submission Guide for Promptheus

This guide walks you through submitting Promptheus to all major MCP registries and lists. Most of the work has been automated - you just need to complete the authentication and submission steps below.

**Estimated time: 15-20 minutes total**

---

## Prerequisites

Before starting, ensure you have:
- ✅ GitHub account with access to `abhichandra21/Promptheus`
- ✅ `server.json` file (already created ✓)
- ✅ Submission descriptions (see `SUBMISSION_DESCRIPTIONS.md` ✓)

---

## Step 1: Official MCP Registry (PRIORITY 1)

**Time: ~5 minutes**
**URL**: https://registry.modelcontextprotocol.io

### 1.1 Install the MCP Publisher CLI

```bash
# Option A: Download from releases
# Visit: https://github.com/modelcontextprotocol/registry/releases
# Download the appropriate binary for your OS

# Option B: Build from source
git clone https://github.com/modelcontextprotocol/registry.git
cd registry
make publisher
./bin/mcp-publisher --help
```

### 1.2 Verify server.json

```bash
# Make sure you're in the Promptheus directory
cd /path/to/Promptheus

# Verify the file exists and is valid JSON
cat server.json | python -m json.tool
```

Expected namespace: `io.github.abhichandra21/promptheus`

### 1.3 Authenticate with GitHub

```bash
# The publisher will prompt you to authenticate
./bin/mcp-publisher login github
```

This will:
- Open a browser window for GitHub OAuth
- Request permission to verify your GitHub identity
- Allow you to publish to the `io.github.abhichandra21/*` namespace

### 1.4 Publish to Registry

```bash
# From the Promptheus directory
./bin/mcp-publisher publish server.json
```

If successful, you'll see:
```
✓ Published io.github.abhichandra21/promptheus@0.3.0
  View at: https://registry.modelcontextprotocol.io/server/io.github.abhichandra21/promptheus
```

### 1.5 Verify Publication

Visit: https://registry.modelcontextprotocol.io/server/io.github.abhichandra21/promptheus

Check that:
- ✓ Server name and description appear correctly
- ✓ Version is 0.3.0
- ✓ Tools are listed (refine_prompt, tweak_prompt, list_models, etc.)
- ✓ Installation instructions are present

---

## Step 2: mcpservers.org (PRIORITY 2)

**Time: ~3 minutes**
**Covers**: punkpeye/awesome-mcp-servers AND wong2/awesome-mcp-servers

### 2.1 Visit Submission Portal

Go to: **https://mcpservers.org/submit**

### 2.2 Fill Out the Form

Use the content from `SUBMISSION_DESCRIPTIONS.md` (Section: "For mcpservers.org Web Form"):

**Server Name**: `Promptheus`

**Repository URL**: `https://github.com/abhichandra21/Promptheus`

**Description** (copy from SUBMISSION_DESCRIPTIONS.md):
```
AI-powered prompt refinement tool with adaptive questioning and multi-provider support. Intelligently refines prompts through clarifying questions, supports 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM), and provides comprehensive prompt engineering capabilities.
```

**Installation**:
```
pip install promptheus
promptheus mcp
```

**Categories**:
- AI Tools
- Developer Productivity
- Prompt Engineering

**Additional Info** (if requested):
- **5 MCP Tools**: refine_prompt, tweak_prompt, list_models, list_providers, validate_environment
- **Features**: Adaptive task detection, multi-provider support, interactive/structured modes
- **PyPI**: https://pypi.org/project/promptheus/

### 2.3 Submit

Click **Submit** and wait for confirmation email/notification.

**Note**: This will automatically add Promptheus to both punkpeye's and wong2's awesome-mcp-servers lists.

---

## Step 3: TensorBlock/awesome-mcp-servers (PRIORITY 3)

**Time: ~3 minutes**
**URL**: https://mcp.so

### Option A: Via Website (Recommended)

1. Visit: **https://mcp.so**
2. Click the **Submit** button in navigation
3. Fill out the form with content from `SUBMISSION_DESCRIPTIONS.md` (Section: "For mcp.so (TensorBlock)")
4. Submit

### Option B: Via GitHub Issue

1. Go to: https://github.com/TensorBlock/awesome-mcp-servers/issues/new
2. Title: `[Submission] Promptheus - AI-powered prompt refinement tool`
3. Body (copy from `SUBMISSION_DESCRIPTIONS.md` - Section: "GitHub Issue Template for TensorBlock"):
   ```markdown
   ## Server Information

   **Name**: Promptheus
   **Repository**: https://github.com/abhichandra21/Promptheus
   **PyPI Package**: https://pypi.org/project/promptheus/

   ## Description

   AI-powered prompt refinement tool with adaptive questioning and multi-provider support. Intelligently refines prompts through clarifying questions, supports 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM), and provides comprehensive prompt engineering capabilities via MCP.

   ## Installation

   ```bash
   pip install promptheus
   promptheus mcp
   ```

   ## Features

   - **5 MCP Tools**: refine_prompt, tweak_prompt, list_models, list_providers, validate_environment
   - **Multi-provider support**: Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM
   - **Adaptive task detection**: Automatically detects analysis vs generation tasks
   - **Interactive & structured modes**: Supports both interactive questioning and structured JSON responses
   - **Session history**: Automatic prompt history tracking and reuse

   ## Categories

   - AI Tools
   - Developer Productivity
   - Prompt Engineering
   - LLM Utilities

   ## Additional Links

   - Documentation: https://github.com/abhichandra21/Promptheus#readme
   - PyPI: https://pypi.org/project/promptheus/
   - License: MIT
   ```
4. Submit the issue

---

## Step 4: appcypher/awesome-mcp-servers (PRIORITY 4)

**Time: ~5 minutes**
**URL**: https://github.com/appcypher/awesome-mcp-servers

### 4.1 Fork the Repository

1. Go to: https://github.com/appcypher/awesome-mcp-servers
2. Click **Fork** button (top-right)
3. Wait for fork to complete

### 4.2 Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/awesome-mcp-servers.git
cd awesome-mcp-servers
```

### 4.3 Create a Branch

```bash
git checkout -b add-promptheus
```

### 4.4 Edit README.md

Find the appropriate category section. Based on the repository structure, add Promptheus under one of these categories:
- **Developer Tools**
- **AI & Machine Learning**
- **Productivity Tools**

Add this entry (in alphabetical order):

```markdown
- [Promptheus](https://github.com/abhichandra21/Promptheus) - AI-powered prompt refinement tool with adaptive questioning and multi-provider support (Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM). Provides 5 MCP tools for intelligent prompt engineering.
```

Example placement:
```markdown
## Developer Tools

- [Other Server](https://github.com/example/other) - Description
- [Promptheus](https://github.com/abhichandra21/Promptheus) - AI-powered prompt refinement tool with adaptive questioning and multi-provider support (Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM). Provides 5 MCP tools for intelligent prompt engineering.
- [Another Server](https://github.com/example/another) - Description
```

### 4.5 Commit and Push

```bash
git add README.md
git commit -m "Add Promptheus - AI-powered prompt refinement tool"
git push origin add-promptheus
```

### 4.6 Create Pull Request

1. Go to: https://github.com/YOUR_USERNAME/awesome-mcp-servers
2. Click **Contribute** → **Open pull request**
3. Title: `Add Promptheus - AI-powered prompt refinement tool`
4. Description:
   ```markdown
   Adding Promptheus, an AI-powered prompt refinement MCP server.

   **Repository**: https://github.com/abhichandra21/Promptheus
   **PyPI**: https://pypi.org/project/promptheus/

   ## Features:
   - 5 MCP tools (refine_prompt, tweak_prompt, list_models, list_providers, validate_environment)
   - Multi-provider support (Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM)
   - Adaptive questioning workflow
   - Interactive and structured modes

   ## Installation:
   ```bash
   pip install promptheus
   promptheus mcp
   ```

   Follows contribution guidelines: alphabetical ordering, clear description, proper formatting.
   ```
5. Click **Create pull request**

---

## Step 5: Additional Registries (Optional)

### Other Community Lists

If you have extra time, consider submitting to:

1. **PipedreamHQ/awesome-mcp-servers**
   - https://github.com/PipedreamHQ/awesome-mcp-servers
   - Similar PR process as appcypher

2. **habitoai/awesome-mcp-servers**
   - https://github.com/habitoai/awesome-mcp-servers
   - Similar PR process as appcypher

3. **MobinX/awesome-mcp-list**
   - https://github.com/MobinX/awesome-mcp-list
   - Similar PR process as appcypher

---

## Verification Checklist

After completing all submissions, verify:

- [ ] Official Registry: https://registry.modelcontextprotocol.io/server/io.github.abhichandra21/promptheus
- [ ] mcpservers.org: Search for "Promptheus" at https://mcpservers.org
- [ ] TensorBlock: Search at https://mcp.so or check GitHub issue status
- [ ] appcypher: Check PR status at https://github.com/appcypher/awesome-mcp-servers/pulls

---

## Troubleshooting

### Official Registry Issues

**Problem**: `mcp-publisher` command not found
**Solution**: Use full path `./bin/mcp-publisher` or add to PATH

**Problem**: Authentication fails
**Solution**: Ensure you're logged into GitHub and have access to the abhichandra21 organization/account

**Problem**: Namespace validation fails
**Solution**: Verify you're using `io.github.abhichandra21/promptheus` exactly

### Web Form Issues

**Problem**: 403 Forbidden on mcpservers.org
**Solution**: Try a different browser or clear cookies. Some regions may have rate limiting.

**Problem**: Form submission doesn't work
**Solution**: Check browser console for errors. Try incognito mode.

### Pull Request Issues

**Problem**: Merge conflicts
**Solution**: Sync your fork with upstream before creating PR:
```bash
git remote add upstream https://github.com/appcypher/awesome-mcp-servers.git
git fetch upstream
git rebase upstream/main
git push origin add-promptheus --force
```

**Problem**: PR rejected for formatting
**Solution**: Ensure alphabetical ordering and consistent formatting with existing entries

---

## Timeline & Expectations

| Registry | Review Time | Visibility |
|----------|-------------|------------|
| Official MCP Registry | Instant | High - official discovery |
| mcpservers.org | 1-3 days | High - most popular list |
| TensorBlock (mcp.so) | 1-7 days | High - largest collection |
| appcypher | 1-14 days | Medium - active community |

---

## Success Metrics

After 1 week, you should see:
- ✓ Promptheus listed on official registry
- ✓ Promptheus discoverable via search on major lists
- ✓ Installation instructions available to MCP clients
- ✓ Increased GitHub stars/traffic from MCP community

---

## Questions or Issues?

If you encounter any problems:
1. Check the troubleshooting section above
2. Review registry-specific documentation:
   - Official: https://github.com/modelcontextprotocol/registry/tree/main/docs
   - mcpservers.org: Contact form on website
3. Create an issue in this repository

---

## What's Already Done ✅

- ✅ `server.json` created and validated
- ✅ Submission descriptions prepared (see `SUBMISSION_DESCRIPTIONS.md`)
- ✅ MCP server tested and working
- ✅ All documentation committed to repository

You only need to do the 4 manual submission steps above!

---

**Good luck with the submissions! 🚀**
