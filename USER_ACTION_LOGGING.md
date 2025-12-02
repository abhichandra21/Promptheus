# User Action Logging with Cloudflare Authentication

This document describes the user action logging feature that captures which Cloudflare-authenticated user performs which action in the Promptheus web application.

## Overview

When the Promptheus web application is deployed behind Cloudflare Zero Trust (formerly Cloudflare Access), all user actions are automatically logged with the authenticated user's identity using Python's standard logging framework.

## How It Works

### Cloudflare Authentication Headers

When a user authenticates through Cloudflare Zero Trust, Cloudflare automatically adds headers to every request:

- `Cf-Access-Authenticated-User-Email`: The email address of the authenticated user

The Promptheus application extracts the user's email from this header and includes it in all action logs.

### Logged Actions

The following user actions are logged:

1. **Prompt Actions**
   - `prompt_submit`: When a user submits a prompt for refinement
   - `prompt_tweak`: When a user tweaks/modifies an existing prompt

2. **History Actions**
   - `history_delete`: When a user deletes a specific history entry
   - `history_clear`: When a user clears all history

3. **Settings Actions**
   - `settings_update`: When a user updates application settings (provider, model, API keys, etc.)
   - `api_key_validation`: When a user validates an API key

4. **Provider Actions**
   - `provider_select`: When a user selects a different AI provider
   - `model_select`: When a user selects a different model

5. **Question Actions**
   - `questions_generate`: When a user generates clarifying questions for a prompt

### Log Format

All user action logs are written using Python's standard logging with extra fields:

```python
logger.info(
    "User submitted prompt",
    extra={
        "user": "user@example.com",
        "action": "prompt_submit",
        "provider": "google",
        "model": "gemini-2.0-flash-exp",
        "task_type": "analysis",
        "prompt_length": 150,
        "skip_questions": False,
        "refine": False,
        "success": True,
    }
)
```

For failed actions:

```python
logger.error(
    "User prompt submission failed",
    extra={
        "user": "user@example.com",
        "action": "prompt_submit",
        "provider": "unknown",
        "prompt_length": 150,
        "success": False,
    },
    exc_info=True
)
```

## Configuration

### Environment Variables

To enable logging to a file, set the standard logging environment variable:

```bash
# Path to the application log file
export PROMPTHEUS_LOG_FILE="/var/log/promptheus/app.log"

# Optional: Use JSON format for structured logging
export PROMPTHEUS_LOG_FORMAT="json"
```

User actions will be logged to the same file as other application logs, with the `user` field in the extra data.

### Cloudflare Zero Trust Setup

1. **Set up Cloudflare Zero Trust Access**:
   - Create an Access application for your Promptheus deployment
   - Configure authentication policies (e.g., require email authentication, SAML SSO, etc.)
   - Ensure the application is configured to pass user identity headers

2. **Deploy Promptheus behind Cloudflare**:
   - Configure your web server (nginx, Apache, etc.) to proxy requests through Cloudflare
   - Ensure the `Cf-Access-Authenticated-User-Email` header is passed to the application
   - Do not strip or modify Cloudflare authentication headers

3. **Verify Headers**:
   You can verify that Cloudflare headers are being passed correctly by checking the logs. When a user is not authenticated through Cloudflare (e.g., during development), the logs will show `user: unknown`.

## Security Considerations

### API Key Protection

When logging settings updates, API keys are automatically masked in the logs. Only the last 4 characters of the API key are shown:

```python
# API key value is masked before logging
masked_value = "●" * (len(update.value) - 4) + update.value[-4:] if len(update.value) > 4 else "●" * len(update.value)

logger.info(
    "User updated settings",
    extra={
        "user": get_user_email(request),
        "action": "settings_update",
        "key": "GOOGLE_API_KEY",
        "value": "●●●●●●●●●●●●●●●●1234",
        "success": True,
    }
)
```

This prevents sensitive API keys from being exposed in log files.

### Log File Permissions

Ensure that the log file has appropriate permissions:

```bash
# Create the log directory
sudo mkdir -p /var/log/promptheus

# Set appropriate ownership
sudo chown promptheus-user:promptheus-group /var/log/promptheus

# Set restrictive permissions
sudo chmod 750 /var/log/promptheus
sudo chmod 640 /var/log/promptheus/app.log
```

### No Session Management Required

This logging approach has several security benefits:

1. **No session state**: The application doesn't need to maintain session state or cookies
2. **Cloudflare handles authentication**: All authentication is managed by Cloudflare Zero Trust
3. **Tamper-resistant**: User identity comes from Cloudflare headers, not client-provided data
4. **Audit trail**: Every action is logged with the authenticated user's email

## Log Analysis

### Example Queries

To analyze user action logs, you can use standard log processing tools. If using JSON format:

**1. View all actions by a specific user:**
```bash
grep '"user": "user@example.com"' /var/log/promptheus/app.log | jq .
```

**2. View failed actions:**
```bash
grep '"success": false' /var/log/promptheus/app.log | jq .
```

**3. View specific action types:**
```bash
grep '"action": "prompt_submit"' /var/log/promptheus/app.log | jq .
```

### Log Rotation

It's recommended to set up log rotation for the application log file:

```bash
# /etc/logrotate.d/promptheus
/var/log/promptheus/app.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 promptheus-user promptheus-group
    sharedscripts
    postrotate
        systemctl reload promptheus || true
    endscript
}
```

## Development and Testing

### Testing Without Cloudflare

During development, when the application is not behind Cloudflare Zero Trust, the logs will show `user: unknown`.

### Simulating Cloudflare Headers

For testing, you can simulate Cloudflare authentication headers using curl:

```bash
curl -X POST http://localhost:8000/api/prompt/submit \
  -H "Cf-Access-Authenticated-User-Email: test@example.com" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt", "skip_questions": true}'
```

## Implementation Details

### Code Structure

The user action logging feature is implemented using Python's standard logging:

1. **`src/promptheus/utils.py`**
   - `get_user_email()` function extracts user email from Cloudflare headers

2. **API Routers**
   - `src/promptheus/web/api/prompt_router.py`
   - `src/promptheus/web/api/history_router.py`
   - `src/promptheus/web/api/settings_router.py`
   - `src/promptheus/web/api/providers_router.py`
   - `src/promptheus/web/api/questions_router.py`

Each router uses `logger.info()` or `logger.error()` with extra fields to log user actions.

### Adding New Actions

To add logging for new actions:

1. Import the necessary modules:
```python
import logging
from promptheus.utils import get_user_email

logger = logging.getLogger(__name__)
```

2. Add the `Request` parameter to your endpoint:
```python
from fastapi import Request

@router.post("/your/endpoint")
async def your_endpoint(data: YourModel, request: Request):
    ...
```

3. Log actions using standard logging with extra fields:
```python
# On success
logger.info(
    "User performed action",
    extra={
        "user": get_user_email(request),
        "action": "your_action_name",
        "success": True,
        # ... other relevant fields
    }
)

# On failure
logger.error(
    "User action failed",
    extra={
        "user": get_user_email(request),
        "action": "your_action_name",
        "success": False,
        # ... other relevant fields
    },
    exc_info=True
)
```

## Troubleshooting

### No User Email in Logs

If logs show `user: unknown` in production:

1. Verify Cloudflare Zero Trust is properly configured
2. Check that the `Cf-Access-Authenticated-User-Email` header is being passed through your reverse proxy
3. Ensure your reverse proxy is not stripping Cloudflare headers

### Log File Not Created

If the log file is not being created:

1. Check that `PROMPTHEUS_LOG_FILE` is set
2. Verify the directory exists and has proper permissions
3. Check application logs for errors related to file creation

### Missing Log Entries

If some actions are not being logged:

1. Check that the endpoint has been updated with the `Request` parameter
2. Verify that logging calls are present in both success and error paths
3. Check for exceptions that might be preventing log writes
