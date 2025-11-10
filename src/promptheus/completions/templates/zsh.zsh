#compdef promptheus

_promptheus() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _get_promptheus_executable() {
        # Check if there's an alias for promptheus
        local alias_value=$(alias promptheus 2>/dev/null | sed "s/^promptheus='//;s/'$//")
        if [[ -n "$alias_value" ]] && [[ -x "$alias_value" ]]; then
            echo "$alias_value"
            return 0
        fi

        if [[ -n "$VIRTUAL_ENV" ]] && [[ -x "$VIRTUAL_ENV/bin/promptheus" ]]; then
            echo "$VIRTUAL_ENV/bin/promptheus"
        elif command -v poetry &> /dev/null && [[ -f "pyproject.toml" ]]; then
            echo "poetry run promptheus"
        elif command -v promptheus &> /dev/null; then
            echo "promptheus"
        else
            return 1
        fi
    }

    local executable=$(_get_promptheus_executable)
    if [[ -z "$executable" ]]; then return 1; fi

    _arguments -C \
        '(- *)'{-h,--help}'[Show help message]' \
        '(- *)'{-v,--verbose}'[Enable verbose debug output]' \
        '1: :->cmds' \
        '*::arg:->args' && return 0

    case "$state" in
        cmds)
            local -a commands providers models
            commands=(
                'history:View and manage prompt history'
                'list-models:List available models from providers'
                'validate:Validate environment configuration'
                'template:Generate a .env file template'
                'completion:Generate shell completion script'
            )
            _describe 'command' commands

            # Get provider list for dynamic completion
            local provider_list=$(eval "$executable __complete providers 2>/dev/null")
            providers=(${=provider_list})

            # Check if --provider was specified to get models
            local selected_provider=""
            for ((i=1; i<$#words; i++)); do
                if [[ "${words[i]}" == "--provider" ]]; then
                    selected_provider="${words[i+1]}"
                    break
                fi
            done

            if [[ -n "$selected_provider" ]]; then
                local model_list=$(eval "$executable __complete models --provider '$selected_provider' 2>/dev/null")
                models=(${=model_list})
                _arguments \
                    '--provider[LLM provider to use]:provider:($providers)' \
                    '--model[Specific model to use]:model:($models)' \
                    '(-s --skip-questions)'{-s,--skip-questions}'[Skip clarifying questions]' \
                    '(-r --refine)'{-r,--refine}'[Force clarifying questions]' \
                    '(-o --output-format)'{-o,--output-format}'[Output format]:format:(plain json)' \
                    '(-c --copy)'{-c,--copy}'[Copy to clipboard]' \
                    '(-f --file)'{-f,--file}'[Read from file]:file:_files'
            else
                _arguments \
                    '--provider[LLM provider to use]:provider:($providers)' \
                    '--model[Specific model to use]:model:' \
                    '(-s --skip-questions)'{-s,--skip-questions}'[Skip clarifying questions]' \
                    '(-r --refine)'{-r,--refine}'[Force clarifying questions]' \
                    '(-o --output-format)'{-o,--output-format}'[Output format]:format:(plain json)' \
                    '(-c --copy)'{-c,--copy}'[Copy to clipboard]' \
                    '(-f --file)'{-f,--file}'[Read from file]:file:_files'
            fi
            ;;
        args)
            local -a providers
            local provider_list=$(eval "$executable __complete providers 2>/dev/null")
            providers=(${=provider_list})

            case ${words[1]} in
                history)
                    _arguments \
                        '--clear[Clear all history]' \
                        '--limit[Number of entries to display]:limit:' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                list-models)
                    _arguments \
                        '--providers[Comma-separated list of providers]:providers:($providers)' \
                        '--limit[Number of models to display]:limit:' \
                        '--include-nontext[Include non-text models]' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                validate)
                    _arguments \
                        '--test-connection[Test API connection]' \
                        '--providers[Comma-separated list of providers]:providers:($providers)' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                template)
                    _arguments \
                        '--providers[Comma-separated list of providers]:providers:($providers)' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                completion)
                    _arguments -s \
                        '--install[Automatically install completion]' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]' \
                        '*: :(bash zsh)'
                    ;;
            esac
            ;;
    esac
}

_promptheus "$@"