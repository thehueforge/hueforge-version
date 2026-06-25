# Signs trusted_publishers.json into a detached CMS/PKCS#7 (.p7s) using the
# Horn & Rhode code-signing certificate from the current user's store (token-backed).
# The cert is selected by subject explicitly (not signtool /a), so it always uses
# the Horn & Rhode token cert. Usage:
#   .\sign_trusted_publishers.ps1 [-Json trusted_publishers.json]
param(
    [string]$Json = "trusted_publishers.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Json)) { throw "List file not found: $Json" }

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -match "Horn & Rhode" } |
        Select-Object -First 1
if (-not $cert) { throw "No Horn & Rhode code-signing certificate found in CurrentUser\My." }

$bytes  = [System.IO.File]::ReadAllBytes((Resolve-Path $Json))
$ci     = New-Object System.Security.Cryptography.Pkcs.ContentInfo (,$bytes)
$cms    = New-Object System.Security.Cryptography.Pkcs.SignedCms ($ci, $true)   # $true = detached
$signer = New-Object System.Security.Cryptography.Pkcs.CmsSigner ($cert)
$signer.DigestAlgorithm = New-Object System.Security.Cryptography.Oid "2.16.840.1.101.3.4.2.1"  # SHA-256
$signer.IncludeOption   = [System.Security.Cryptography.X509Certificates.X509IncludeOption]::EndCertOnly

$cms.ComputeSignature($signer)        # token may prompt here (cached after first PIN)
$out = "$Json.p7s"
[System.IO.File]::WriteAllBytes((Join-Path (Get-Location) $out), $cms.Encode())

Write-Host "Wrote detached CMS signature: $out"
Write-Host ("Signer: " + $cert.Subject)
Write-Host ("Thumbprint: " + $cert.Thumbprint)
