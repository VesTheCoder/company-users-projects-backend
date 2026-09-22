param([int]$DurationSeconds = 30)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskImage = 'grafana/k6@sha256:e66db15b860113878fa74670e31f5e274830b7b6e42c8bff28b2f2d86a257603'
$taskFailed = $false
$taskRuns = @(
    @{ Name = 'companies'; Script = 'business_flows'; Rate = 100; Flow = 'companies' },
    @{ Name = 'employees'; Script = 'business_flows'; Rate = 150; Flow = 'employees' },
    @{ Name = 'projects'; Script = 'business_flows'; Rate = 14; Flow = 'projects' },
    @{ Name = 'assignments'; Script = 'business_flows'; Rate = 10; Flow = 'assignments' },
    @{ Name = 'mixed'; Script = 'mixed'; Rate = 200; Flow = '' }
)
foreach ($taskRun in $taskRuns) {
    docker run --rm --user 0 --add-host host.docker.internal:host-gateway `
        -v "${taskRoot}/load/k6:/scripts:ro" -v "${taskRoot}/.local:/data:ro" `
        -v "${taskRoot}/docs/benchmarks:/results" `
        -e "RATE=$($taskRun.Rate)" -e "FLOW=$($taskRun.Flow)" -e "DURATION=${DurationSeconds}s" `
        $taskImage run --quiet --summary-export "/results/$($taskRun.Name).json" "/scripts/$($taskRun.Script).js"
    Write-Output "$($taskRun.Name) exit code: $LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { $taskFailed = $true }
}
if ($taskFailed) { exit 1 }
