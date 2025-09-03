# Chrome Cleanup Script
# This script kills all Chrome processes and cleans up temp files to prevent startup issues

Write-Host "Cleaning up Chrome processes..." -ForegroundColor Yellow

# Kill all Chrome processes
Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "chromedriver" -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait a moment for processes to fully terminate
Start-Sleep -Seconds 2

# Clean up Chrome temp files that might cause issues
$chromeTempPaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache\*",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\ShaderCache\*",
    "$env:LOCALAPPDATA\Temp\chrome*",
    "$env:TEMP\chrome*"
)

foreach ($path in $chromeTempPaths) {
    try {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    } catch {
        # Silently continue if files are in use
    }
}

Write-Host "Chrome cleanup completed!" -ForegroundColor Green
Write-Host "You can now run your LinkedIn automation script." -ForegroundColor Cyan
