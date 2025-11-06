#!/usr/bin/env python3
"""
Promptheus Environment Validator
Validates environment configuration for different LLM providers.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from promptheus.utils import sanitize_error_message

console = Console()


class EnvironmentValidator:
    """Validates environment configuration for Promptheus."""

    def __init__(self):
        self.providers = {
            'zai': {
                'name': 'Z.ai (GLM)',
                'required_vars': {
                    'ANTHROPIC_AUTH_TOKEN': {
                        'description': 'Your Z.ai API authentication token',
                        'mask': True
                    },
                    'ANTHROPIC_BASE_URL': {
                        'description': 'Z.ai API endpoint (default: https://api.z.ai/api/anthropic)',
                        'default': 'https://api.z.ai/api/anthropic',
                        'mask': False
                    }
                },
                'optional_vars': {
                    'ANTHROPIC_DEFAULT_SONNET_MODEL': {
                        'description': 'Default model for complex tasks',
                        'default': 'glm-4.6'
                    },
                    'ANTHROPIC_DEFAULT_OPUS_MODEL': {
                        'description': 'Default model for advanced tasks',
                        'default': 'glm-4.6'
                    },
                    'ANTHROPIC_DEFAULT_HAIKU_MODEL': {
                        'description': 'Default model for simple tasks',
                        'default': 'glm-4.5-air'
                    },
                    'API_TIMEOUT_MS': {
                        'description': 'API timeout in milliseconds',
                        'default': '300000'
                    }
                },
                'test_command': 'python -c "import anthropic; client = anthropic.Anthropic(api_key=os.getenv(\"ANTHROPIC_AUTH_TOKEN\"), base_url=os.getenv(\"ANTHROPIC_BASE_URL\", \"https://api.z.ai/api/anthropic\")); client.messages.create(model=os.getenv(\"ANTHROPIC_DEFAULT_SONNET_MODEL\", \"glm-4.6\"), max_tokens=10, messages=[{\"role\": \"user\", \"content\": \"Hi\"}])"'
            },
            'gemini': {
                'name': 'Google Gemini',
                'required_vars': {
                    'GEMINI_API_KEY': {
                        'description': 'Your Google Gemini API key',
                        'mask': True
                    }
                },
                'optional_vars': {},
                'test_command': 'python -c "import google.generativeai as genai; genai.configure(api_key=os.getenv(\"GEMINI_API_KEY\")); model = genai.GenerativeModel(\"gemini-pro\"); response = model.generate_content(\"Hi\")"'
            }
        }

    def validate_env_file(self, env_file: Path) -> Tuple[bool, Dict[str, str]]:
        """Load and validate environment file."""
        if not env_file.exists():
            return False, {}

        env_vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('\'"')
                        env_vars[key] = value
            return True, env_vars
        except Exception as e:
            console.print(f"[red]Error reading {env_file}: {sanitize_error_message(str(e))}[/red]")
            return False, {}

    def mask_value(self, value: str, mask: bool = True) -> str:
        """Mask sensitive values for display."""
        if not mask or not value:
            return value
        if len(value) <= 8:
            return '*' * len(value)
        return value[:4] + '*' * (len(value) - 8) + value[-4:]

    def check_provider(self, provider: str, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Check if a provider's environment is properly configured."""
        provider_config = self.providers[provider]
        result = {
            'provider': provider_config['name'],
            'configured': True,
            'missing_required': [],
            'missing_optional': [],
            'test_result': None
        }

        # Check required variables
        for var_name, var_config in provider_config['required_vars'].items():
            if var_name not in env_vars:
                result['missing_required'].append(var_name)
                result['configured'] = False

        # Check optional variables
        for var_name, var_config in provider_config['optional_vars'].items():
            if var_name not in env_vars:
                result['missing_optional'].append(var_name)

        return result

    def test_connection(self, provider: str, env_vars: Dict[str, str]) -> bool:
        """Test API connection for a provider."""
        provider_config = self.providers[provider]

        try:
            # Set environment variables temporarily
            original_env = {}
            for key, value in env_vars.items():
                if key in os.environ:
                    original_env[key] = os.environ[key]
                os.environ[key] = value

            # Import and run test
            test_command = provider_config['test_command']
            if provider == 'zai':
                try:
                    import anthropic
                    client = anthropic.Anthropic(
                        api_key=env_vars.get('ANTHROPIC_AUTH_TOKEN'),
                        base_url=env_vars.get('ANTHROPIC_BASE_URL', 'https://api.z.ai/api/anthropic')
                    )
                    model = env_vars.get('ANTHROPIC_DEFAULT_SONNET_MODEL', 'glm-4.6')
                    client.messages.create(
                        model=model,
                        max_tokens=10,
                        messages=[{"role": "user", "content": "Hi"}]
                    )
                    return True
                except ImportError:
                    console.print("[yellow]Warning: anthropic package not installed. Install with: pip install anthropic[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

            elif provider == 'gemini':
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=env_vars.get('GEMINI_API_KEY'))
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content('Hi')
                    return True
                except ImportError:
                    console.print("[yellow]Warning: google-generativeai package not installed. Install with: pip install google-generativeai[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

        finally:
            # Restore original environment
            for key, value in original_env.items():
                os.environ[key] = value
            for key in env_vars:
                if key not in original_env:
                    os.environ.pop(key, None)

        return False

    def display_results(self, results: List[Dict[str, Any]], env_vars: Dict[str, str], source_label: str):
        """Display validation results in a nice table."""
        table = Table(title="Environment Validation Results")
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Issues", style="yellow")
        table.add_column("Connection", style="green")

        for result in results:
            if result['configured']:
                status = "[green]✓ Ready[/green]"
                issues = "None"
            else:
                status = "[red]✗ Not Ready[/red]"
                missing = result['missing_required']
                issues = f"Missing: {', '.join(missing)}"

            connection = "Not tested" if result['test_result'] is None else \
                        "[green]✓ Connected[/green]" if result['test_result'] else \
                        "[red]✗ Failed[/red]"

            table.add_row(
                result['provider'],
                status,
                issues,
                connection
            )

        console.print(table)

        # Show environment variables
        if env_vars:
            console.print("\n[bold]Environment Variables:[/bold]")
            env_table = Table()
            env_table.add_column("Variable", style="cyan")
            env_table.add_column("Value", style="white")
            env_table.add_column("Source", style="dim")

            for provider in self.providers:
                provider_config = self.providers[provider]
                for var_name, var_config in {**provider_config['required_vars'], **provider_config['optional_vars']}.items():
                    if var_name in env_vars:
                        value = self.mask_value(env_vars[var_name], var_config.get('mask', True))
                        env_table.add_row(var_name, value, source_label)

            console.print(env_table)

    def create_env_template(self, provider: str, output_file: Optional[Path] = None):
        """Create an environment file template for a provider."""
        provider_config = self.providers[provider]
        template_lines = [f"# {provider_config['name']} Environment Configuration", ""]

        template_lines.append("# Required Variables")
        for var_name, var_config in provider_config['required_vars'].items():
            template_lines.append(f"{var_name}='YOUR_{var_name.upper()}_HERE'")

        if provider_config['optional_vars']:
            template_lines.append("\n# Optional Variables")
            for var_name, var_config in provider_config['optional_vars'].items():
                default = var_config.get('default', '')
                template_lines.append(f"{var_name}='{default}'")

        template_content = '\n'.join(template_lines)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(template_content)
            console.print(f"[green]✓ Environment template created: {output_file}[/green]")
        else:
            console.print("\n[bold]Environment Template:[/bold]")
            console.print(Panel(template_content, title=f"{provider_config['name']} Template"))

    def list_providers(self):
        """List all supported providers."""
        console.print("[bold]Supported LLM Providers:[/bold]")
        for provider_id, config in self.providers.items():
            required_count = len(config['required_vars'])
            console.print(f"• [cyan]{provider_id}[/cyan] - {config['name']} ({required_count} required env vars)")


def main():
    """Main entry point for environment validator."""
    parser = argparse.ArgumentParser(
        description='Promptheus Environment Validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current environment
  python env_validator.py

  # Check specific environment file
  python env_validator.py --env-file anthropic.env

  # Test only Z.ai provider
  python env_validator.py --provider zai

  # Create environment template
  python env_validator.py --template zai --output zai.env

  # List all supported providers
  python env_validator.py --list-providers
        """
    )

    parser.add_argument(
        '--env-file', '-f',
        type=Path,
        help='Path to environment file (e.g., .env, anthropic.env)'
    )

    parser.add_argument(
        '--provider', '-p',
        choices=['zai', 'gemini', 'all'],
        default='all',
        help='Provider to validate (default: all)'
    )

    parser.add_argument(
        '--test-connection', '-t',
        action='store_true',
        help='Test API connection (may make actual API calls)'
    )

    parser.add_argument(
        '--template',
        choices=['zai', 'gemini'],
        help='Create environment file template for provider'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for template (if not specified, prints to console)'
    )

    parser.add_argument(
        '--list-providers', '-l',
        action='store_true',
        help='List all supported providers'
    )

    args = parser.parse_args()

    validator = EnvironmentValidator()

    if args.list_providers:
        validator.list_providers()
        return

    if args.template:
        validator.create_env_template(args.template, args.output)
        return

    # Load environment variables
    env_vars = dict(os.environ)
    env_source = "Environment"

    if args.env_file:
        file_exists, file_vars = validator.validate_env_file(args.env_file)
        if not file_exists:
            console.print(f"[red]Error: Environment file not found: {args.env_file}[/red]")
            sys.exit(1)
        env_vars.update(file_vars)
        env_source = f"File ({args.env_file}) + Environment"

    console.print(f"[bold]Promptheus Environment Validator[/bold]")
    console.print(f"[dim]Checking: {env_source}[/dim]\n")

    # Determine which providers to check
    if args.provider == 'all':
        providers_to_check = list(validator.providers.keys())
    else:
        providers_to_check = [args.provider]

    # Validate each provider
    results = []
    for provider in providers_to_check:
        result = validator.check_provider(provider, env_vars)

        if args.test_connection and result['configured']:
            console.print(f"Testing connection to {result['provider']}...", end=" ")
            result['test_result'] = validator.test_connection(provider, env_vars)
            if result['test_result']:
                console.print("[green]✓[/green]")
            else:
                console.print("[red]✗[/red]")

        results.append(result)

    # Display results
    validator.display_results(results, env_vars, env_source)

    # Provide recommendations
    console.print("\n[bold]Recommendations:[/bold]")

    ready_providers = [r for r in results if r['configured']]
    if ready_providers:
        console.print("[green]✓ Ready to use:[/green]")
        for result in ready_providers:
            console.print(f"  • {result['provider']}")
            if args.test_connection and not result['test_result']:
                console.print(f"    [yellow]⚠ Connection test failed - check credentials[/yellow]")

    not_ready = [r for r in results if not r['configured']]
    if not_ready:
        console.print("[red]✓ Configuration needed:[/red]")
        for result in not_ready:
            console.print(f"  • {result['provider']}")
            for var in result['missing_required']:
                console.print(f"    - Set {var}")
            console.print(f"    [dim]Tip: Run: python env_validator.py --template {providers_to_check[0]}[/dim]")

    # Exit with appropriate code
    if any(r['configured'] for r in results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
