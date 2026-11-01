# UTF-8 with BOM: Windows PowerShell 5.1 must read Japanese strings without mojibake.
# User-facing orchestration only; setup-runtime.bat contains ASCII-only bootstrap commands.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$App = Join-Path $Root 'app.bat'
$Runtime = Join-Path $PSScriptRoot 'setup-runtime.bat'
$ExitCode = 0
$NoPause = $false
$SkipAuth = $false

foreach ($Option in $args) {
    switch ($Option.ToLowerInvariant()) {
        '--no-pause' { $NoPause = $true; $SkipAuth = $true }
        '--skip-auth' { $SkipAuth = $true }
        default {
            Write-Host "対応していないオプションです: $Option" -ForegroundColor Red
            Write-Host '利用できるオプション: --no-pause / --skip-auth'
            exit 2
        }
    }
}

function Invoke-Application {
    param(
        [string[]]$CommandArgs,
        [switch]$Quiet
    )
    if ($Quiet) {
        & $App @CommandArgs *> $null
    } else {
        & $App @CommandArgs
    }
    return $LASTEXITCODE
}

try {
    Set-Location -LiteralPath $Root
    Write-Host ''
    Write-Host '=============================================================='
    Write-Host '  TradingView MCP Support セットアップ'
    Write-Host '=============================================================='
    Write-Host ''
    Write-Host 'このセットアップは、Pythonの準備からTradingViewへの接続確認まで進めます。'
    Write-Host 'システムPythonの事前インストール・管理者権限は不要です。'
    Write-Host '初回はインターネット接続とTradingView公式MCP対応プランが必要です。'
    Write-Host ''

    Write-Host '[1/3] Python 3.12.8と実行環境を準備します。' -ForegroundColor Cyan
    & $Runtime '--no-pause'
    if ($LASTEXITCODE -ne 0) {
        throw "Pythonや必要なライブラリの導入に失敗しました（終了コード $LASTEXITCODE）。"
    }

    if ($SkipAuth) {
        Write-Host '[2/3] 非対話・セットアップ専用モードのためログインを省略しました。' -ForegroundColor Yellow
        Write-Host '初回利用時はsetup.batをダブルクリックするとログインまで進みます。'
    } else {
        Write-Host ''
        Write-Host '[2/3] TradingViewのログイン状態を確認します。' -ForegroundColor Cyan
        $AuthStatus = Invoke-Application -CommandArgs @('mcp','status') -Quiet

        if ($AuthStatus -eq 0) {
            Write-Host 'ログイン済みです。ブラウザを再度開かず、認証情報を利用します。' -ForegroundColor Green
        } elseif ($AuthStatus -eq 3) {
            Write-Host ''
            Write-Host '初回ログインが必要です。既定ブラウザでTradingViewにログインしてください。' -ForegroundColor Yellow
            Write-Host '表示されたアクセス許可画面で認可すると、こちらの処理を再開します。'
            Write-Host 'OAuth認証コードやトークンは、第三者と共有しないでください。'
            Write-Host ''
            $AuthResult = Invoke-Application -CommandArgs @('mcp','auth')
            if ($AuthResult -ne 0) {
                throw "TradingViewの認証に失敗しました（終了コード $AuthResult）。ブラウザ認可・ネットワーク・利用プランを確認してください。"
            }
        } else {
            throw "MCPの認証状態を確認できません（終了コード $AuthStatus）。通信状況や公式サーバーを確認してください。"
        }

        Write-Host ''
        Write-Host '[3/3] TradingView公式MCPへの接続とTool一覧を確認します。' -ForegroundColor Cyan
        $StatusResult = Invoke-Application -CommandArgs @('mcp','status') -Quiet
        if ($StatusResult -ne 0) {
            throw "TradingViewへの接続を確認できません（終了コード $StatusResult）。"
        }
        $ToolsResult = Invoke-Application -CommandArgs @('mcp','tools') -Quiet
        if ($ToolsResult -ne 0) {
            throw "TradingViewのTool一覧を取得できません（終了コード $ToolsResult）。"
        }
        Write-Host 'ログインと接続確認に成功しました。' -ForegroundColor Green
    }

    Write-Host ''
    Write-Host '=============================================================='
    Write-Host '  セットアップ完了'
    Write-Host '=============================================================='
    Write-Host '詳細な使い方は docs\user\WINDOWS_SETUP.md を参照してください。'
    Write-Host '実際のスクリーニングやWatchlist更新は自動実行しません。'
} catch {
    $ExitCode = 1
    Write-Host ''
    Write-Host '==============================================================' -ForegroundColor Red
    Write-Host '  セットアップが完了しませんでした。' -ForegroundColor Red
    Write-Host '==============================================================' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host '実行環境・保存済み認証・既存データは原則保持されています。'
    Write-Host '詳しい状態は app.bat mcp status から確認できます。'
} finally {
    if (-not $NoPause) {
        Write-Host ''
        [void](Read-Host 'Enterキーを押すと画面を閉じます')
    }
}
exit $ExitCode
