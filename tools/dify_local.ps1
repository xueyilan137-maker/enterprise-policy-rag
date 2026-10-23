param([ValidateSet('Status','Start','Stop')][string]$Action='Status')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$composeDir=Join-Path $root '.local\vendor\dify-1.17.1\docker'
if(-not(Test-Path -LiteralPath (Join-Path $composeDir 'project.override.yaml'))){throw 'Run tools/setup_dify.py after obtaining the official archive'}
Push-Location $composeDir
try {
    $base=@('compose','--parallel','2','--progress','quiet','-p','policy-rag','-f','docker-compose.yaml','-f','project.override.yaml')
    $rulesOverride=Join-Path $root 'deploy\dify.rules.override.yml'
    if(Test-Path -LiteralPath $rulesOverride){$base+=@('-f',$rulesOverride)}
    switch($Action){
        'Status' { & docker @base ps }
        'Start' {
            & docker volume create policy-rag_plugin_runtime | Out-Null
            if($LASTEXITCODE -ne 0){throw 'Cannot prepare plugin runtime volume'}
            & docker @base up -d
        }
        'Stop' { & docker @base stop }
    }
    if($LASTEXITCODE -ne 0){throw 'Dify command failed; inspect output'}
} finally { Pop-Location }
