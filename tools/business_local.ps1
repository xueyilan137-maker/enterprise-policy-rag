param([ValidateSet('Start','Status','Stop')][string]$Action='Status')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$stateFile=Join-Path $root '.local\business-process.json'
$python=Join-Path $root '.venv\Scripts\python.exe'
function Get-ManagedProcess {
    if(-not(Test-Path -LiteralPath $stateFile)){return $null}
    $state=Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $candidate=Get-CimInstance Win32_Process -Filter "ProcessId = $($state.process_id)" -ErrorAction SilentlyContinue
    if($candidate -and $candidate.ExecutablePath -eq $python -and $candidate.CommandLine -match 'src\.business_api:create_app' -and $candidate.CommandLine -match '18082'){
        return $candidate
    }
    return $null
}
$managed=Get-ManagedProcess
switch($Action){
    'Status' {
        if($managed){Write-Output 'Managed business API process is running; verify /health and a protected request'}
        else{Write-Output 'Managed business API process is not running'}
    }
    'Start' {
        if($managed){Write-Output 'Existing business API process preserved';break}
        if(Get-NetTCPConnection -LocalPort 18082 -State Listen -ErrorAction SilentlyContinue){throw 'Port 18082 is already occupied; preserved existing process'}
        foreach($name in @('business-auth.json','precheck-app-api.json')){
            if(-not(Test-Path -LiteralPath (Join-Path $root ".local\$name"))){throw "Missing private configuration: $name"}
        }
        $args=@('-m','uvicorn','src.business_api:create_app','--factory','--host','127.0.0.1','--port','18082','--workers','1','--no-access-log')
        $process=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.local\business.out.log') -RedirectStandardError (Join-Path $root '.local\business.err.log')
        @{process_id=$process.Id;port=18082;mode='synthetic_demo'} | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8
        Write-Output 'Started local business API; verify /health before use'
    }
    'Stop' {
        if($managed){
            # Windows venv python.exe may be a launcher with the actual server as a child.
            $children=@(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($managed.ProcessId)")
            foreach($child in $children){
                if($child.Name -eq 'conhost.exe' -and $child.ExecutablePath -eq (Join-Path $env:SystemRoot 'System32\conhost.exe')){continue}
                if($child.CommandLine -notmatch 'src\.business_api:create_app' -or $child.CommandLine -notmatch '18082'){
                    throw 'Unexpected child process; nothing stopped'
                }
            }
            foreach($child in $children){
                if($child.CommandLine -match 'src\.business_api:create_app' -and $child.CommandLine -match '18082'){
                    Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                }
            }
            Stop-Process -Id $managed.ProcessId -ErrorAction SilentlyContinue
            Write-Output 'Stopped only the recorded business API launcher and verified server child'
        }
        else{Write-Output 'No matching managed process; nothing stopped'}
    }
}
exit 0
