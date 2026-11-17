[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root '.env'
$templatePath = Join-Path $root '.env.example'

if (Test-Path -LiteralPath $envPath -PathType Leaf) {
    Write-Host 'Found the existing .env. Use it with the existing PostgreSQL volume.'
    return
}

$template = [IO.File]::ReadAllText($templatePath)
if (-not [regex]::IsMatch($template, '(?m)^POSTGRES_PASSWORD=\r?$')) {
    throw 'Expected an empty POSTGRES_PASSWORD in .env.example.'
}

$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $rng.GetBytes($bytes)
} finally {
    $rng.Dispose()
}
$password = [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
$settings = $template.Replace('POSTGRES_PASSWORD=', "POSTGRES_PASSWORD=$password")

$stream = [IO.File]::Open($envPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
    $content = [Text.Encoding]::UTF8.GetBytes($settings)
    $stream.Write($content, 0, $content.Length)
} finally {
    $stream.Dispose()
}

Write-Host 'Created .env with a generated PostgreSQL password. Keep this file local.'
