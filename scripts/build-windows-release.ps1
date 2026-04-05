#Requires -Version 5.1
<#
.SYNOPSIS
  在仓库根目录一键构建：前端静态资源 → PyInstaller 后端 → Electron NSIS 安装包。

.DESCRIPTION
  产物：electron/release/ 下的 *-Setup.exe（名称与 electron/package.json 中 version、productName 一致）。

.PARAMETER SkipPyInstaller
  跳过 PyInstaller；请事先将 novel-backend.exe 放到 electron/resources/backend/（仅重打 Electron 壳时可用）。

.PARAMETER SkipFrontendBuild
  跳过 webapp/frontend 的 npm run build（需已有 webapp/frontend/dist）。

.EXAMPLE
  .\scripts\build-windows-release.ps1

.EXAMPLE
  .\scripts\build-windows-release.ps1 -SkipPyInstaller
#>

[CmdletBinding()]
param(
    [switch] $SkipPyInstaller,
    [switch] $SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Test-Command([string] $Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "npm")) {
    throw "未找到 npm，请先安装 Node.js 18+。"
}
if (-not $SkipPyInstaller -and -not (Test-Command "py") -and -not (Test-Command "python")) {
    throw "未找到 py/python；若要用 -SkipPyInstaller，请显式传入该开关。"
}

# --- 1) 前端 dist（PyInstaller 与运行时静态资源依赖）---
$frontendDir = Join-Path $RepoRoot "webapp/frontend"
$distDir = Join-Path $frontendDir "dist"
if (-not $SkipFrontendBuild) {
    Write-Host "[1/4] webapp/frontend: npm install && npm run build" -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        npm install
        npm run build
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path (Join-Path $distDir "index.html"))) {
    throw "缺少 webapp/frontend/dist/index.html，请先构建前端或去掉 -SkipFrontendBuild。"
}

# --- 2) PyInstaller ---
$backendDest = Join-Path $RepoRoot "electron/resources/backend/novel-backend.exe"
if (-not $SkipPyInstaller) {
    Write-Host "[2/4] PyInstaller: novel-backend.exe" -ForegroundColor Cyan
    $py = if (Test-Command "py") { "py" } else { "python" }
    & $py -m pip install -q pyinstaller
    $pyArgs = @(
        "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        "--name", "novel-backend",
        "packaging/pyinstaller/run_uvicorn.py",
        "--paths", ".",
        "--add-data", "webapp/frontend/dist;webapp/frontend/dist",
        "--add-data", "webapp/static;webapp/static",
        "--add-data", "webapp/templates;webapp/templates",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-submodules", "agents",
        "--collect-submodules", "webapp"
    )
    & $py @pyArgs
    $built = Join-Path $RepoRoot "dist/novel-backend.exe"
    if (-not (Test-Path $built)) {
        throw "未生成 dist/novel-backend.exe，请根据终端报错补充 --hidden-import / --collect-all（见 packaging/pyinstaller/README.md）。"
    }
    $destDir = Split-Path $backendDest -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Force $built $backendDest
    Write-Host "已复制到 $backendDest" -ForegroundColor Green
} else {
    Write-Host "[2/4] 跳过 PyInstaller" -ForegroundColor Yellow
    if (-not (Test-Path $backendDest)) {
        throw "未找到 $backendDest，无法 -SkipPyInstaller。"
    }
}

# --- 3) Electron ---
Write-Host "[3/4] electron: npm install && npm run dist" -ForegroundColor Cyan
$electronDir = Join-Path $RepoRoot "electron"
Push-Location $electronDir
try {
    npm install
    npm run dist
} finally {
    Pop-Location
}

Write-Host "[4/4] 完成。安装包目录: electron/release/" -ForegroundColor Green
$releaseDir = Join-Path $RepoRoot "electron/release"
if (Test-Path $releaseDir) {
    Get-ChildItem $releaseDir -Filter "*.exe" | ForEach-Object { Write-Host "  $($_.FullName)" }
}
