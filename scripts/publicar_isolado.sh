#!/usr/bin/env bash
set -euo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly GH_ACCOUNT="gabrisantoss"
readonly GH_CONFIG_DIR_PATH="${HOME}/.config/gh-gabrisantoss"
readonly EXPECTED_GIT_USER_NAME="Gabriel Barbosa"
readonly EXPECTED_GIT_USER_EMAIL="39058710+gabrisantoss@users.noreply.github.com"

usage() {
    cat <<'EOF'
Uso:
  ./scripts/publicar_isolado.sh "Mensagem do commit" --all
  ./scripts/publicar_isolado.sh "Mensagem do commit" [--skip-tests] arquivo1 arquivo2 ...

Regras:
  - Usa apenas a configuracao local deste repositorio.
  - Usa a conta GitHub isolada 'gabrisantoss'.
  - Exige --all ou caminhos explicitos para evitar stage acidental.
EOF
}

git_isolado() {
    env \
        GH_CONFIG_DIR="${GH_CONFIG_DIR_PATH}" \
        GIT_CONFIG_GLOBAL=/dev/null \
        GIT_CONFIG_SYSTEM=/dev/null \
        GIT_TERMINAL_PROMPT=0 \
        git -C "${REPO_ROOT}" "$@"
}

gh_isolado() {
    env GH_CONFIG_DIR="${GH_CONFIG_DIR_PATH}" gh "$@"
}

require_local_identity() {
    local current_name current_email
    current_name="$(git_isolado config --local --get user.name || true)"
    current_email="$(git_isolado config --local --get user.email || true)"

    if [[ "${current_name}" != "${EXPECTED_GIT_USER_NAME}" ]]; then
        echo "Configuracao local user.name divergente: '${current_name}'" >&2
        exit 1
    fi

    if [[ "${current_email}" != "${EXPECTED_GIT_USER_EMAIL}" ]]; then
        echo "Configuracao local user.email divergente: '${current_email}'" >&2
        exit 1
    fi
}

stage_changes() {
    local stage_all="$1"
    shift

    if [[ "${stage_all}" == "1" ]]; then
        git_isolado add -A
        return
    fi

    git_isolado add -- "$@"
}

run_checks() {
    local -a staged_python_files=()

    while IFS= read -r file_path; do
        [[ -n "${file_path}" ]] && staged_python_files+=("${file_path}")
    done < <(git_isolado diff --cached --name-only -- '*.py')

    if [[ ${#staged_python_files[@]} -gt 0 ]]; then
        python3 -m py_compile "${staged_python_files[@]}"
    fi

    if [[ -d "${REPO_ROOT}/tests" ]]; then
        python3 -m unittest discover -s "${REPO_ROOT}/tests" -p 'test*.py'
    fi
}

main() {
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    local commit_message="${1:-}"
    local run_tests="1"
    local stage_all="0"
    shift || true

    if [[ -z "${commit_message}" ]]; then
        usage
        exit 1
    fi

    local -a target_paths=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                stage_all="1"
                ;;
            --skip-tests)
                run_tests="0"
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                target_paths+=("$1")
                ;;
        esac
        shift
    done

    if [[ "${stage_all}" == "1" && ${#target_paths[@]} -gt 0 ]]; then
        echo "Use --all ou caminhos especificos, nao os dois ao mesmo tempo." >&2
        exit 1
    fi

    if [[ "${stage_all}" == "0" && ${#target_paths[@]} -eq 0 ]]; then
        echo "Passe --all ou informe os caminhos que deseja publicar." >&2
        exit 1
    fi

    require_local_identity
    gh_isolado auth status >/dev/null

    git_isolado status --short --branch
    stage_changes "${stage_all}" "${target_paths[@]}"

    if git_isolado diff --cached --quiet; then
        echo "Nenhuma alteracao foi adicionada ao commit." >&2
        exit 1
    fi

    if [[ "${run_tests}" == "1" ]]; then
        run_checks
    fi

    git_isolado commit -m "${commit_message}"

    local current_branch
    current_branch="$(git_isolado rev-parse --abbrev-ref HEAD)"

    if git_isolado rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1; then
        git_isolado push
    else
        git_isolado push -u origin "${current_branch}"
    fi

    echo
    echo "Publicado com isolamento usando a conta '${GH_ACCOUNT}' na branch '${current_branch}'."
}

main "$@"
