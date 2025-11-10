#!/bin/bash

_promptheus_complete() {
    local cur prev words cword
    _get_comp_words_by_ref -n : cur prev words cword

    # Helper to find the executable
    _get_promptheus_executable() {
        local alias_value=$(alias promptheus 2>/dev/null | sed "s/^promptheus='//;s/'$//")
        if [[ -n "$alias_value" ]] && [[ -x "$alias_value" ]]; then echo "$alias_value"; return 0; fi
        if [[ -n "$VIRTUAL_ENV" ]] && [[ -x "$VIRTUAL_ENV/bin/promptheus" ]]; then echo "$VIRTUAL_ENV/bin/promptheus"; return; fi
        if command -v poetry &> /dev/null && [[ -f "pyproject.toml" ]]; then echo "poetry run promptheus"; return; fi
        if command -v promptheus &> /dev/null; then echo "promptheus"; return; fi
    }

    local executable=$(_get_promptheus_executable)
    if [[ -z "$executable" ]]; then return 1; fi

    # Dynamic completions
    case "${prev}" in
        --provider|--providers)
            local providers=$(eval "$executable __complete providers 2>/dev/null")
            COMPREPLY=( $(compgen -W "${providers}" -- "${cur}") )
            return 0
            ;;
        --model)
            local provider_val=""
            for i in "${!words[@]}"; do
                if [[ "${words[i]}" == "--provider" || "${words[i]}" == "--providers" ]]; then
                    provider_val="${words[i+1]}"
                    break
                fi
            done
            if [[ -n "$provider_val" ]]; then
                local models=$(eval "$executable __complete models --provider '$provider_val' 2>/dev/null")
                COMPREPLY=( $(compgen -W "${models}" -- "${cur}") )
            fi
            return 0
            ;;
        -o|--output-format)
            COMPREPLY=( $(compgen -W "plain json" -- "${cur}") )
            return 0
            ;;
        -f|--file)
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh" -- "${cur}") )
            return 0
            ;;
    esac

    # Check if we're in a subcommand
    local in_subcommand=""
    local i
    for (( i=0; i < cword; i++ )); do
        if [[ "${words[i]}" =~ ^(history|list-models|validate|template|completion)$ ]]; then
            in_subcommand="${words[i]}"
            break
        fi
    done

    if [[ -n "$in_subcommand" ]]; then
        case "$in_subcommand" in
            history)
                local history_opts="--clear --limit --verbose --help"
                COMPREPLY=( $(compgen -W "${history_opts}" -- "${cur}") )
                return 0
                ;;
            list-models)
                local list_models_opts="--providers --limit --include-nontext --verbose --help"
                COMPREPLY=( $(compgen -W "${list_models_opts}" -- "${cur}") )
                return 0
                ;;
            validate)
                local validate_opts="--test-connection --providers --verbose --help"
                COMPREPLY=( $(compgen -W "${validate_opts}" -- "${cur}") )
                return 0
                ;;
            template)
                local template_opts="--providers --verbose --help"
                COMPREPLY=( $(compgen -W "${template_opts}" -- "${cur}") )
                return 0
                ;;
        esac
        return 0
    fi

    # Static completions for main command
    if [[ "${cur}" == -* ]]; then
        local main_opts="--provider --model --skip-questions --refine --output-format --copy --file --verbose --help"
        COMPREPLY=( $(compgen -W "${main_opts}" -- "${cur}") )
        return 0
    fi

    local subcommands="history list-models validate template completion"
    COMPREPLY=( $(compgen -W "${subcommands}" -- "${cur}") )
    return 0
}

complete -F _promptheus_complete promptheus