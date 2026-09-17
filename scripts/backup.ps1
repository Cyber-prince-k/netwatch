param([string]$OutputDirectory = "./backups")
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
docker compose exec -T db pg_dump -U netwatch -d netwatch | Out-File -Encoding utf8 "$OutputDirectory/netwatch-$stamp.sql"
Write-Output "Backup written to $OutputDirectory/netwatch-$stamp.sql"
