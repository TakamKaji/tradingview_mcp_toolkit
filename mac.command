#!/bin/bash
# macOS /bin/bash 3.2 compatible. All paths are relative to this launcher.
set -u
cd -- "$(dirname -- "$0")" || exit 1

if ! command -v docker >/dev/null 2>&1; then
    printf '%s\n' 'Docker Desktopをインストールして起動してください。' >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    printf '%s\n' 'Docker DesktopとDocker Composeを利用できません。Docker Desktopの起動状態を確認してください。' >&2
    exit 1
fi

compose=(docker compose -f compose.mac.yml)
no_args=false
if [ "$#" -eq 0 ]; then
    no_args=true
    set -- --help
fi

# Build progress belongs on stderr; CLI stdout remains machine-readable JSON.
"${compose[@]}" build app >&2 || exit $?
if [ "$#" -eq 2 ] && [ "$1" = mcp ] && [ "$2" = auth ]; then
    if [ -x /usr/sbin/lsof ] && /usr/sbin/lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
        printf '%s\n' 'localhost:8765が使用中です。別の認証処理が終了してから再実行してください。' >&2
        exit 1
    fi
    # Open only the fixed local entry point. The provider URL/state stays in memory.
    (
        for ((attempt=0; attempt<120; attempt++)); do
            if curl --silent --fail --max-time 1 --output /dev/null http://127.0.0.1:8765/oauth/authorize; then
                if [ -x /usr/bin/open ]; then
                    /usr/bin/open http://127.0.0.1:8765/oauth/authorize
                else
                    printf '%s\n' 'ブラウザで http://127.0.0.1:8765/oauth/authorize を開いてください。' >&2
                fi
                exit 0
            fi
            sleep 1
        done
    ) &
    browser_pid=$!
    trap 'kill "$browser_pid" 2>/dev/null || true' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    "${compose[@]}" run --rm --service-ports app "$@"
    status=$?
else
    "${compose[@]}" run --rm app "$@"
    status=$?
fi

if [ "$no_args" = true ] && [ -t 0 ]; then
    if [ "$status" -eq 0 ]; then
        printf '\n%s\n' '認証: ./mac.command mcp auth' \
            '操作例: ./mac.command screen public_japan_value' >&2
    fi
    printf '%s\n' '終了するにはEnterを押してください。' >&2
    read -r _reply
fi
exit "$status"
