# User Action Logging with Cloudflare Authentication

This document describes the user action logging feature that captures which Cloudflare-authenticated user performs which action in the Promptheus web application.

## Overview

When the Promptheus web application is deployed behind Cloudflare Zero Trust (formerly Cloudflare Access), all user actions are automatically logged with the authenticated user's identity. This provides audit trails and accountability without requiring any built-in session management in the application.

## How It Works

### Cloudflare Authentication Headers

When a user authenticates through Cloudflare Zero Trust, Cloudflare automatically adds the following headers to every request:

- `Cf-Access-Authenticated-User-Email`: The email address of the authenticated user
- `Cf-Access-Jwt-Assertion`: JWT token containing user details

The Promptheus application extracts the user's email from these headers and includes it in all action logs.

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

All user action logs are written in structured JSON format with the following fields:

```json
{
  "timestamp": "2025-12-02T10:30:45.123456",
  "user": "user@example.com",
  "action": "prompt_submit",
  "path": "/api/prompt/submit",
  "method": "POST",
  "success": true,
  "ip_address": "192.168.1.100",
  "details": {
    "provider": "google",
    "model": "gemini-2.0-flash-exp",
    "task_type": "analysis",
    "prompt_length": 150,
    "skip_questions": false,
    "refine": false
  }
}
```

For failed actions:

```json
{
  "timestamp": "2025-12-02T10:35:20.789012",
  "user": "user@example.com",
  "action": "prompt_submit",
  "path": "/api/prompt/submit",
  "method": "POST",
  "success": false,
  "ip_address": "192.168.1.100",
  "error": "No provider configured",
  "details": {
    "provider": "unknown",
    "prompt_length": 150
  }
}
```

## Configuration

### Environment Variables

To enable user action logging, set the following environment variable:

```bash
# Path to the user action log file
export PROMPTHEUS_USER_ACTION_LOG_FILE="/var/log/promptheus/user_actions.log"
```

If this environment variable is not set, user actions will still be logged to the standard application log (if configured), but they won't be written to a separate file.

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

```json
{
  "action": "settings_update",
  "details": {
    "key": "GOOGLE_API_KEY",
    "value": "●●●●●●●●●●●●●●●●1234"
  }
}
```

This prevents sensitive API keys from being exposed in log files.

### Log File Permissions

Ensure that the user action log file has appropriate permissions:

```bash
# Create the log directory
sudo mkdir -p /var/log/promptheus

# Set appropriate ownership
sudo chown promptheus-user:promptheus-group /var/log/promptheus

# Set restrictive permissions
sudo chmod 750 /var/log/promptheus
sudo chmod 640 /var/log/promptheus/user_actions.log
```

### No Session Management Required

This logging approach has several security benefits:

1. **No session state**: The application doesn't need to maintain session state or cookies
2. **Cloudflare handles authentication**: All authentication is managed by Cloudflare Zero Trust
3. **Tamper-resistant**: User identity comes from Cloudflare headers, not client-provided data
4. **Audit trail**: Every action is logged with the authenticated user's email

## Log Analysis

### Example Queries

To analyze user action logs, you can use standard JSON log processing tools:

**1. View all actions by a specific user:**
```bash
grep '"user": "user@example.com"' /var/log/promptheus/user_actions.log | jq .
```

**2. View failed actions:**
```bash
grep '"success": false' /var/log/promptheus/user_actions.log | jq .
```

**3. Count actions by type:**
```bash
jq -r '.action' /var/log/promptheus/user_actions.log | sort | uniq -c
```

**4. View recent API key validation attempts:**
```bash
grep '"action": "api_key_validation"' /var/log/promptheus/user_actions.log | jq .
```

**5. View all actions in the last hour:**
```bash
# Requires jq and date utilities
HOUR_AGO=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)
jq -r "select(.timestamp > \"$HOUR_AGO\")" /var/log/promptheus/user_actions.log
```

### Log Rotation

It's recommended to set up log rotation for the user action log file:

```bash
# /etc/logrotate.d/promptheus
/var/log/promptheus/user_actions.log {
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

During development, when the application is not behind Cloudflare Zero Trust, the logs will show `user: unknown`:

```json
{
  "timestamp": "2025-12-02T10:40:15.123456",
  "user": "unknown",
  "action": "prompt_submit",
  "cloudflare_authenticated": false
  ...
}
```

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

The user action logging feature is implemented in the following modules:

1. **`src/promptheus/web/user_logging.py`**
   - Core user logging functions
   - Cloudflare header extraction
   - User context management

2. **`src/promptheus/logging_config.py`**
   - Logging configuration setup
   - User action logger configuration
   - JSON log formatting

3. **API Routers**
   - `src/promptheus/web/api/prompt_router.py`
   - `src/promptheus/web/api/history_router.py`
   - `src/promptheus/web/api/settings_router.py`
   - `src/promptheus/web/api/providers_router.py`
   - `src/promptheus/web/api/questions_router.py`

Each router imports and uses the `log_user_action()` function to log actions.

### Adding New Actions

To add logging for new actions:

1. Import the logging function:
```python
from promptheus.web.user_logging import log_user_action
```

2. Add the `Request` parameter to your endpoint:
```python
from fastapi import Request

@router.post("/your/endpoint")
async def your_endpoint(data: YourModel, request: Request):
    ...
```

3. Call `log_user_action()` after the action completes:
```python
# On success
log_user_action(
    request=request,
    action="your_action_name",
    details={"key": "value"},
    success=True
)

# On failure
log_user_action(
    request=request,
    action="your_action_name",
    details={"key": "value"},
    success=False,
    error=str(exception)
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

1. Check that `PROMPTHEUS_USER_ACTION_LOG_FILE` is set
2. Verify the directory exists and has proper permissions
3. Check application logs for errors related to file creation

### Missing Log Entries

If some actions are not being logged:

1. Check that the endpoint has been updated with the `Request` parameter
2. Verify that `log_user_action()` is being called in both success and error paths
3. Check for exceptions that might be preventing log writes

## Compliance and Privacy

### GDPR Considerations

User action logs contain personally identifiable information (email addresses). Ensure compliance with GDPR and other privacy regulations:

1. **Data Retention**: Implement appropriate log retention policies
2. **Right to Access**: Provide mechanisms for users to access their logs
3. **Right to Erasure**: Implement procedures to remove user data from logs when requested
4. **Disclosure**: Update your privacy policy to inform users about action logging

### Audit Compliance

This logging system can help meet various audit and compliance requirements:

- **SOC 2**: Provides audit trails for user actions
- **HIPAA**: Logs access to sensitive data (if applicable)
- **ISO 27001**: Supports information security management
- **PCI DSS**: Tracks access to systems handling payment data (if applicable)

## Support

For questions or issues related to user action logging, please:

1. Check the troubleshooting section above
2. Review the implementation in `src/promptheus/web/user_logging.py`
3. Open an issue on the GitHub repository with log samples (redacted of sensitive information)
