# Promptheus: Sample Prompts

This file contains sample prompts to test and demonstrate Promptheus capabilities, particularly the adaptive interaction model that detects task types (analysis vs generation).

## How to Use These Prompts

Promptheus intelligently detects task types:
- **Analysis tasks** (research, exploration, debugging): Skip questions by default
- **Generation tasks** (writing, creating content): Offer clarifying questions

Each prompt below indicates the expected behavior for testing purposes.

---

## Generation Tasks (Triggers Clarifying Questions)

These prompts should trigger the question-answer workflow because they involve creating new content.

### 1. Futuristic Story
```
Write a short, futuristic story for a young adult audience about a teenager who discovers an AI that can dream. The story should have a hopeful tone and be around 500 words.
```
**Expected**: Asks about protagonist details, dream themes, conflict type, ending preference

### 2. Marketing Campaign Slogan
```
Generate five catchy slogans for a new brand of eco-friendly coffee.
```
**Expected**: Asks about brand personality, target audience, key differentiators, tone

### 3. Ambiguous Prompt
```
Social media post about AI.
```
**Expected**: Asks about platform, audience, tone, length, key message

### 4. Poetry with Constraints
```
Write a haiku about a bustling city at night.
```
**Expected**: May ask about specific city, mood, imagery preferences

### 5. Screenplay Dialogue
```
Write a tense dialogue scene between a detective and a suspect who knows more than they are letting on. The scene should be no more than 200 words.
```
**Expected**: Asks about setting, character backgrounds, revelation level

### 6. Blog Post Outline
```
Create an outline for a technical blog post about microservices architecture.
```
**Expected**: Asks about target audience, depth level, specific topics, post length

### 7. Python Function with Requirements
```
Create a Python function named calculate_ema that calculates the Exponential Moving Average of a list of numbers. The function should take two arguments: a list of prices and a span (integer). It must include type hints, a docstring explaining its usage, and handle potential errors like an empty input list.
```
**Expected**: Asks about error handling strategy, return type format, validation requirements

### 8. Product Description
```
Write a compelling product description for a smart home security system targeting tech-savvy homeowners.
```
**Expected**: Asks about key features, price range, competitive advantages, tone

### 9. Newsletter Content
```
Create engaging content for a weekly tech newsletter covering recent AI developments.
```
**Expected**: Asks about audience level, content format, specific topics, length

---

## Analysis Tasks (Skip Questions by Default)

These prompts should skip the question phase and directly enhance/analyze because they're about understanding, debugging, or explanation.

### 10. Debug JavaScript Code
```
My JavaScript code isn't working as expected. When I click the button, the text content doesn't update. Can you tell me why?

<p id='my-text'>Hello World</p>
<button id='my-button'>Change Text</button>

const button = document.getElementById('my-button');
button.addEventListener('click', () => {
  const text = document.getElementById('my-text');
  text.innerHtml = 'Hello, New World!';
});
```
**Expected**: Skip questions, directly identifies the typo (`innerHtml` vs `innerHTML`)

### 11. Performance Analysis
```
I have a Python script that is running slower than expected. Analyze this code for performance bottlenecks and suggest specific optimizations.

def process_data(data_list):
    results = []
    for item in data_list:
        processed_item = item * item
        time.sleep(0.1)
        results.append(processed_item)
    return results
```
**Expected**: Skip questions, analyzes bottlenecks (sleep, list append), suggests optimizations

### 12. Git Command Explanation
```
Explain the git rebase -i HEAD~3 command. What does it do, and what are some common use cases for it in a development workflow?
```
**Expected**: Skip questions, provides direct explanation with examples

### 13. Concept Explanation
```
Explain the concept of blockchain to someone with no technical background.
```
**Expected**: Skip questions, provides simplified explanation with analogies

### 14. Architecture Comparison
```
Compare and contrast the architectural patterns of microservices and a monolithic backend. Focus on scalability, development speed, and operational complexity.
```
**Expected**: Skip questions, provides direct comparative analysis

### 15. Customer Feedback Analysis
```
Analyze the following customer reviews for a fictional product and identify the top 3 most common complaints and top 2 most praised features.

Review 1: "The battery life is amazing! But the screen is too dim."
Review 2: "I love how fast it is, but it keeps crashing."
Review 3: "Super fast and reliable. Best purchase ever."
Review 4: "The screen is hard to see outdoors. Battery is great though."
```
**Expected**: Skip questions, directly provides sentiment analysis and categorization

### 16. Research Summary
```
Summarize the key findings from recent research papers on transformer architectures in natural language processing.
```
**Expected**: Skip questions, provides direct summary (or may ask for specific papers if too broad)

### 17. SQL Query Analysis
```
Write a SQL query to find all users who have signed up in the last 30 days and made at least one purchase. Assume the tables are users (with id, name, signup_date) and purchases (with id, user_id, purchase_date, amount).
```
**Expected**: May skip questions or ask minimal clarifications about database engine/performance needs

---

## Edge Cases & Testing Scenarios

### 18. Minimal Context (Should Trigger Questions)
```
Write something interesting.
```
**Expected**: Asks about topic, format, audience, length, purpose

### 19. Technical with Context (May Skip)
```
Create a Dockerfile for a Node.js application that uses Express and PostgreSQL.
```
**Expected**: May ask about Node version, optimization needs, or skip and provide standard solution

### 20. Code Refactoring (Analysis)
```
Refactor this nested callback code into async/await syntax while maintaining error handling.
```
**Expected**: Skip questions, provides direct refactoring

### 21. Business Writing (Generation)
```
Draft a polite and concise email to a colleague asking for an update on a project that is past its deadline.
```
**Expected**: Asks about relationship with colleague, urgency level, project context

### 22. Study Guide (Generation)
```
Create a study guide for learning Python programming from scratch over 4 weeks.
```
**Expected**: Asks about time commitment, learning goals, resources available, prior experience

---

## Testing Skip Mode Flag

Use the `-s` or `--skip-questions` flag to force skipping questions regardless of task type.

### 23. Force Skip on Generation Task
```
promptheus -s "Write a blog post about async programming"
```
**Expected**: Skips questions, directly enhances the prompt

### 24. Force Skip on Analysis Task
```
promptheus -s "Explain Docker containers"
```
**Expected**: Skips questions (consistent with normal behavior for analysis tasks)

---

## Testing Refine Mode Flag

Use the `-r` flag to force clarifying questions even for analysis tasks.

### 25. Force Questions on Analysis Task
```
promptheus -r "Explain recursion"
```
**Expected**: Forces questions despite being an analysis task

---

## Multi-Modal Task Detection

These prompts blend analysis and generation to test classification accuracy.

### 26. Analysis + Generation
```
Review this function for security issues and rewrite it to be more secure.
```
**Expected**: May ask about security requirements, context, or skip for direct analysis+fix

### 27. Tutorial Creation (Generation)
```
Create a beginner-friendly tutorial explaining how HTTP requests work, including GET and POST methods.
```
**Expected**: Asks about prior knowledge assumptions, depth, examples needed, format

### 28. Documentation (Generation)
```
Write comprehensive API documentation for a user management service with authentication endpoints.
```
**Expected**: Asks about API structure, authentication method, example requirements

---

## Testing Notes

- **Task classification** is the key feature being tested
- **Generation tasks** should ask clarifying questions to gather requirements
- **Analysis tasks** should skip questions and provide direct analysis/explanation
- **Edge cases** test the boundary between task types
- Use **skip mode** (`-s`) when you want to bypass questions for any task
- Use **refine mode** (`-r`) to force questions on any task

---

## MCP Server Testing Examples

These examples demonstrate how to test the Promptheus MCP server integration with MCP-compatible clients.

### Basic MCP Tool Testing

**Test 1: List Available Providers**
```bash
# MCP client call
mcp-client call list_providers

# Expected response format
{
  "type": "success",
  "providers": {
    "google": {"configured": true, "model": "gemini-2.0-flash-exp"},
    "openai": {"configured": false, "error": "No API key found"}
  }
}
```

**Test 2: Validate Environment**
```bash
# MCP client call with connection test
mcp-client call validate_environment --test-connection true

# Expected response shows provider status
{
  "type": "success", 
  "validation": {
    "google": {"configured": true, "connection_test": "passed"}
  }
}
```

### MCP Refinement Workflow Testing

**Test 3: Direct Refinement (No Questions)**
```bash
# MCP client call for analysis task
mcp-client call refine_prompt --prompt "Explain Docker containers"

# Expected: Direct refinement without questions
{
  "type": "refined",
  "prompt": "Provide a comprehensive explanation of Docker containers...",
  "next_action": "This refined prompt is now ready to use..."
}
```

**Test 4: Clarification Workflow (With Questions)**
```bash
# MCP client call for generation task
mcp-client call refine_prompt --prompt "Write a blog post"

# Expected: Clarification needed response
{
  "type": "clarification_needed",
  "task_type": "generation",
  "questions_for_ask_user_question": [
    {
      "question": "Who is your target audience?",
      "header": "Q1", 
      "multiSelect": false,
      "options": [
        {"label": "Technical professionals", "description": "Technical professionals"},
        {"label": "Business executives", "description": "Business executives"}
      ]
    }
  ],
  "answer_mapping": {"q0": "Who is your target audience?"}
}
```

**Test 5: Complete Refinement with Answers**
```bash
# MCP client call with answers from AskUserQuestion
mcp-client call refine_prompt \
  --prompt "Write a blog post" \
  --answers '{"q0": "Technical professionals"}' \
  --answer-mapping '{"q0": "Who is your target audience?"}'

# Expected: Final refined prompt
{
  "type": "refined",
  "prompt": "Write a comprehensive technical blog post about... targeted at software engineers...",
  "next_action": "This refined prompt is now ready to use..."
}
```

### MCP Tweak Tool Testing

**Test 6: Prompt Modification**
```bash
# MCP client call for prompt tweaking
mcp-client call tweak_prompt \
  --prompt "Write a technical blog post about Docker" \
  --modification "make it more beginner-friendly"

# Expected: Modified prompt
{
  "type": "refined",
  "prompt": "Write an accessible beginner-friendly blog post about Docker..."
}
```

### MCP Error Handling Testing

**Test 7: Missing Provider Configuration**
```bash
# MCP client call without configured providers
mcp-client call refine_prompt --prompt "Test prompt"

# Expected: Configuration error
{
  "type": "error",
  "error_type": "ConfigurationError",
  "message": "No provider configured. Please set API keys in environment."
}
```

**Test 8: Invalid Provider**
```bash
# MCP client call with invalid provider
mcp-client call refine_prompt \
  --prompt "Test prompt" \
  --provider "invalid_provider"

# Expected: Provider error
{
  "type": "error", 
  "error_type": "ConfigurationError",
  "message": "Provider 'invalid_provider' is not supported."
}
```

### MCP Integration Testing

**Test 9: Model Discovery**
```bash
# MCP client call to list models
mcp-client call list_models --providers "google" --limit 5

# Expected: Model list with metadata
{
  "type": "success",
  "providers": {
    "google": {
      "available": true,
      "models": [
        {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash"},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"}
      ],
      "total_count": 15,
      "showing": 5
    }
  }
}
```

### MCP Workflow Integration Examples

**Example 1: AI Toolchain Integration**
```bash
# Use MCP-refined prompt in larger AI workflow
REFINED_PROMPT=$(mcp-client call refine_prompt --prompt "Create API documentation" | jq -r '.prompt')
echo "$REFINED_PROMPT" | claude exec --generate-docs
```

**Example 2: Batch Processing with MCP**
```bash
# Process multiple prompts through MCP
for prompt in "Write a blog post" "Create a tutorial" "Draft an email"; do
  echo "Processing: $prompt"
  mcp-client call refine_prompt --prompt "$prompt" > "refined_${prompt// /_}.json"
done
```

**Example 3: Interactive MCP Session**
```bash
# Start MCP server for interactive use
promptheus mcp

# In another terminal, use MCP client for interactive refinement
mcp-client interactive
> refine_prompt "Write a technical article"
# Handle clarification questions interactively
# Use refined output with other tools
```

### MCP Testing Checklist

**Basic Functionality:**
- [ ] MCP server starts without errors
- [ ] All five tools are accessible
- [ ] Provider configuration is detected
- [ ] Error handling works correctly

**Refinement Workflow:**
- [ ] Direct refinement works for analysis tasks
- [ ] Clarification workflow triggers for generation tasks
- [ ] AskUserQuestion integration functions properly
- [ ] Answer mapping works correctly

**Integration Testing:**
- [ ] MCP client can connect to server
- [ ] JSON responses are properly formatted
- [ ] Error responses include actionable information
- [ ] Provider fallback behavior works

**Performance Testing:**
- [ ] Response times are reasonable (< 5 seconds)
- [ ] No memory leaks during extended use
- [ ] Concurrent requests are handled properly
