# Get ngrok URL script
try {
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 3
    $httpsTunnel = $response.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1

    if ($httpsTunnel) {
        Write-Host "========================================"
        Write-Host "ngrok HTTPS URL: $($httpsTunnel.public_url)"
        Write-Host ""
        Write-Host "Add to Google Cloud Console:"
        Write-Host "$($httpsTunnel.public_url)/oauth-callback"
        Write-Host "========================================"
    } else {
        Write-Host "No HTTPS tunnel found"
    }
} catch {
    Write-Host "Error: Cannot access ngrok API at http://localhost:4040"
    Write-Host "Make sure ngrok is running with: ngrok http 3000"
    Write-Host ""
    Write-Host "Alternative: Visit http://localhost:4040 in your browser"
}
