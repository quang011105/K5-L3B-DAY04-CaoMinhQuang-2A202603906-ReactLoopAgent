# Run in the current terminal: . .\setup-openrouter.ps1
$openrouterModel = Read-Host 'Nhap OpenRouter model ID ho tro tool calling (dang provider/model)'
if ([string]::IsNullOrWhiteSpace($openrouterModel) -or
    $openrouterModel.Trim() -notmatch '^[^\s/]+/[^\s/]+$') {
    throw 'Can nhap model ID day du dang provider/model tu OpenRouter.'
}
$openrouterSecret = Read-Host 'Nhap OpenRouter API key (an noi dung)' -AsSecureString
$openrouterCredential = New-Object System.Management.Automation.PSCredential('openrouter', $openrouterSecret)
$openrouterKey = $openrouterCredential.GetNetworkCredential().Password.Trim()
if ([string]::IsNullOrWhiteSpace($openrouterKey) -or $openrouterKey -match '[\s\p{C}]') {
    Remove-Variable openrouterSecret, openrouterCredential, openrouterKey
    throw 'API key rong hoac chua ky tu an/khoang trang. Hay sao chep lai chi API key.'
}
$env:OPENROUTER_API_KEY = $openrouterKey
$env:PROVIDER = 'openrouter'
$env:MODEL = $openrouterModel.Trim()
# Keep the default judge on the same provider/model for comparable eval runs.
$env:JUDGE_PROVIDER = 'openrouter'
$env:JUDGE_MODEL = $env:MODEL
$env:PYTHONUTF8 = '1'
Remove-Variable openrouterSecret, openrouterCredential, openrouterKey, openrouterModel
Write-Host "Da cau hinh OpenRouter: $env:MODEL (agent va judge)."
Write-Host 'API key chi duoc luu trong terminal hien tai, khong ghi vao file.'
