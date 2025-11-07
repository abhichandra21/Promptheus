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

from promptheus.config import Config
from promptheus.utils import sanitize_error_message

PROVIDER_CHOICE_OPTIONS = ['gemini', 'openai', 'groq', 'qwen', 'glm', 'zai', 'all']
TEMPLATE_PROVIDER_OPTIONS = ['gemini', 'openai', 'groq', 'qwen', 'glm', 'zai']

console = Console()


class EnvironmentValidator:
    """Validates environment configuration for Promptheus."""

    def __init__(self):
        self.model_defaults: Dict[str, str] = {}
        self.providers = {
            'gemini': {
                'name': 'Google Gemini',
                'required_vars': {
                    'GEMINI_API_KEY': {
                        'description': 'Your Google Gemini API key',
                        'mask': True
                    }
                },
                'optional_vars': {},
                'default_model_env': 'GEMINI_DEFAULT_MODEL',
                'fallback_model': 'gemini-pro',
            },
            'openai': {
                'name': 'OpenAI',
                'required_vars': {
                    'OPENAI_API_KEY': {
                        'description': 'Your OpenAI API key',
                        'mask': True
                    }
                },
                'optional_vars': {
                    'OPENAI_BASE_URL': {
                        'description': 'Override the API base URL (optional)'
                    },
                    'OPENAI_ORG_ID': {
                        'description': 'Organization ID (optional)'
                    },
                    'OPENAI_PROJECT': {
                        'description': 'Project ID (optional)'
                    }
                },
                'default_model_env': 'OPENAI_DEFAULT_MODEL',
                'fallback_model': 'gpt-4o-mini',
            },
            'groq': {
                'name': 'Groq',
                'required_vars': {
                    'GROQ_API_KEY': {
                        'description': 'Your Groq API key',
                        'mask': True
                    }
                },
                'optional_vars': {},
                'default_model_env': 'GROQ_DEFAULT_MODEL',
                'fallback_model': 'llama-3.1-8b-instant',
            },
            'qwen': {
                'name': 'Qwen (DashScope)',
                'required_vars': {
                    'DASHSCOPE_API_KEY': {
                        'description': 'Your DashScope API key',
                        'mask': True
                    }
                },
                'optional_vars': {
                    'DASHSCOPE_API_KEY_FILE_PATH': {
                        'description': 'Path to file containing DashScope API key'
                    },
                    'DASHSCOPE_LOGGING_LEVEL': {
                        'description': 'DashScope logging level (e.g., info)'
                    }
                },
                'default_model_env': 'QWEN_DEFAULT_MODEL',
                'fallback_model': 'qwen-turbo',
            },
            'glm': {
                'name': 'GLM (Zhipu)',
                'required_vars': {
                    'ZAI_API_KEY': {
                        'description': 'Your Z.ai API key',
                        'mask': True
                    }
                },
                'optional_vars': {
                    'ZAI_BASE_URL': {
                        'description': 'Custom base URL for self-hosted gateways',
                        'default': ''
                    }
                },
                'default_model_env': 'GLM_DEFAULT_MODEL',
                'fallback_model': 'glm-4',
            }
        }
        self.aliases = {'zai': 'glm'}
        self._load_model_defaults()

    def _resolve_provider_key(self, provider: str) -> str:
        return self.aliases.get(provider, provider)

    def _load_model_defaults(self) -> None:
        """Load default models from models.json to align with runtime configuration."""
        try:
            config = Config()
            config_data = config.load_model_config()
        except Exception as exc:
            console.print(
                f"[yellow]Warning: Unable to load models.json defaults: "
                f"{sanitize_error_message(str(exc))}[/yellow]"
            )
            return

        for provider_name, info in config_data.get("providers", {}).items():
            default_model = info.get("default_model")
            if default_model:
                self.model_defaults[provider_name] = default_model

    def _get_test_model(self, provider: str, env_vars: Dict[str, str]) -> Optional[str]:
        """Determine which model to target for connection tests."""
        provider_config = self.providers.get(provider, {})
        env_override_var = provider_config.get("default_model_env")
        if env_override_var and env_vars.get(env_override_var):
            return env_vars[env_override_var]

        return self.model_defaults.get(provider) or provider_config.get("fallback_model")

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
        resolved = self._resolve_provider_key(provider)
        provider_config = self.providers[resolved]
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
        resolved = self._resolve_provider_key(provider)
        if resolved not in self.providers:
            console.print(f"[red]Unknown provider: {provider}[/red]")
            return False
        provider_config = self.providers[resolved]

        try:
            # Set environment variables temporarily
            original_env = {}
            for key, value in env_vars.items():
                if key in os.environ:
                    original_env[key] = os.environ[key]
                os.environ[key] = value

            if resolved == 'gemini':
                try:
                    from google import genai
                    from google.genai import types

                    api_key = env_vars.get('GEMINI_API_KEY') or env_vars.get('GOOGLE_API_KEY')
                    if not api_key:
                        console.print("[red]Connection test failed: Missing GEMINI_API_KEY[/red]")
                        return False

                    model_name = self._get_test_model(resolved, env_vars) or 'gemini-2.5-flash'
                    is_vertex_ai_key = api_key.startswith("AQ.")

                    client = genai.Client(api_key=api_key, vertexai=is_vertex_ai_key)
                    config = types.GenerateContentConfig(max_output_tokens=8)

                    client.models.generate_content(
                        model=model_name,
                        contents="Ping",
                        config=config,
                    )
                    return True
                except ImportError:
                    console.print(
                        "[yellow]Warning: google-genai package not installed. "
                        "Install with: pip install google-genai[/yellow]"
                    )
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

            if resolved == 'openai':
                try:
                    from openai import OpenAI
                    client_kwargs = {
                        'api_key': env_vars.get('OPENAI_API_KEY'),
                    }
                    if env_vars.get('OPENAI_BASE_URL'):
                        client_kwargs['base_url'] = env_vars['OPENAI_BASE_URL']
                    if env_vars.get('OPENAI_ORG_ID'):
                        client_kwargs['organization'] = env_vars['OPENAI_ORG_ID']
                    if env_vars.get('OPENAI_PROJECT'):
                        client_kwargs['project'] = env_vars['OPENAI_PROJECT']
                    client = OpenAI(**client_kwargs)
                    client.chat.completions.create(
                        model=self._get_test_model(resolved, env_vars) or 'gpt-4o-mini',
                        messages=[{'role': 'user', 'content': 'Ping'}],
                        max_tokens=8,
                    )
                    return True
                except ImportError:
                    console.print("[yellow]Warning: openai package not installed. Install with: pip install openai[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

            if resolved == 'groq':
                try:
                    from groq import Groq
                    client = Groq(api_key=env_vars.get('GROQ_API_KEY'))
                    client.chat.completions.create(
                        model=self._get_test_model(resolved, env_vars) or 'llama-3.1-8b-instant',
                        messages=[{'role': 'user', 'content': 'Ping'}],
                        max_tokens=8,
                    )
                    return True
                except ImportError:
                    console.print("[yellow]Warning: groq package not installed. Install with: pip install groq[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

            if resolved == 'qwen':
                try:
                    import dashscope
                    from dashscope import Generation
                    dashscope.api_key = env_vars.get('DASHSCOPE_API_KEY')
                    Generation.call(
                        model=self._get_test_model(resolved, env_vars) or 'qwen-turbo',
                        prompt='Ping',
                        max_tokens=16,
                    )
                    return True
                except ImportError:
                    console.print("[yellow]Warning: dashscope package not installed. Install with: pip install dashscope[/yellow]")
                    return False
                except Exception as e:
                    console.print(f"[red]Connection test failed: {sanitize_error_message(str(e))}[/red]")
                    return False

            if resolved == 'glm':
                try:
                    from zai import ZaiClient
                    client = ZaiClient(
                        api_key=env_vars.get('ZAI_API_KEY'),
                        base_url=env_vars.get('ZAI_BASE_URL') or None,
                    )
                    client.chat.completions.create(
                        model=self._get_test_model(resolved, env_vars) or 'glm-4',
                        messages=[{'role': 'user', 'content': 'Ping'}],
                        max_tokens=16,
                    )
                    return True
                except ImportError:
                    console.print("[yellow]Warning: zai package not installed. Install with: pip install zai[/yellow]")
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
        resolved = self._resolve_provider_key(provider)
        if resolved not in self.providers:
            console.print(f"[red]Unknown provider: {provider}[/red]")
            return
        provider_config = self.providers[resolved]
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
        choices=PROVIDER_CHOICE_OPTIONS,
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
        choices=TEMPLATE_PROVIDER_OPTIONS,
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
