# Manual Enrollment Lifecycle Demo

This demo walks through the MVP lifecycle:

1. Create an issuer.
2. Create an identity.
3. Submit a CSR enrollment.
4. Approve the enrollment.
5. Issue a certificate through `anopki-core`.
6. List certificate inventory.
7. Revoke the certificate.
8. List audit events.

The repository owner runs all commands.

## Build Core CLI

```powershell
cmake -S . -B build
cmake --build build
```

Use the produced executable path for `ANOPKI_CORE_BIN`. On the default Windows multi-config generator this is usually:

```powershell
..\build\Debug\anopki-core.exe
```

## Create Demo Key Material

Run from the repository root:

```powershell
New-Item -ItemType Directory -Force .tmp-demo | Out-Null
openssl ecparam -name prime256v1 -genkey -noout -out .tmp-demo\issuer.key
openssl req -new -x509 -key .tmp-demo\issuer.key -days 365 -subj "/CN=AnoPKI-demo-ca" -out .tmp-demo\issuer.crt
openssl ecparam -name prime256v1 -genkey -noout -out .tmp-demo\leaf.key
@'
[req]
prompt = no
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = edge-01

[req_ext]
subjectAltName = DNS:edge-01.example.test,IP:127.0.0.1
'@ | Set-Content -Encoding ascii -ErrorAction Stop .tmp-demo\leaf.cnf
openssl req -new -key .tmp-demo\leaf.key -config .tmp-demo\leaf.cnf -out .tmp-demo\leaf.csr
if ($LASTEXITCODE -ne 0) { throw "Could not generate the leaf CSR." }
```

The explicit request config keeps the leaf SANs independent of the default OpenSSL request configuration.

## Start Service

Run from `service\` in a separate terminal:

```powershell
$env:ANOPKI_ADDR = ":8080"
$env:ANOPKI_DB_DRIVER = "sqlite"
$env:ANOPKI_DB_DSN = "anopki.db"
$env:ANOPKI_CORE_BIN = "..\build\Debug\anopki-core.exe"
go run .\cmd\anopki-service
```

## Run Lifecycle Flow

Run from the repository root:

```powershell
$base = "http://localhost:8080"
$headers = @{ "X-Actor" = "demo-admin" }
$dnsName = "edge-01.example.test"
$ipAddress = "127.0.0.1"

# Inspect the same PEM that will be submitted, before any POST.
$csrPem = Get-Content -Raw -ErrorAction Stop .tmp-demo\leaf.csr
if ([string]::IsNullOrWhiteSpace($csrPem)) { throw "The leaf CSR is empty." }
$csrPem | openssl req -noout
if ($LASTEXITCODE -ne 0) { throw "Could not inspect the leaf CSR." }
$csrAsn1 = $csrPem | openssl asn1parse -inform PEM
if ($LASTEXITCODE -ne 0) { throw "Could not read the leaf CSR extensions." }
$extensionRequest = @($csrAsn1 | Select-String '^\s*\d+:d=4\s+.*prim:\s+OBJECT\s+:(?:Microsoft )?Extension Request\s*$')
if ($extensionRequest.Count -ne 1) { throw "The leaf CSR must contain exactly one extension request." }
$sanExtension = @($csrAsn1 | Select-String '^\s*\d+:d=7\s+.*prim:\s+OBJECT\s+:X509v3 Subject Alternative Name\s*$' -Context 0,2)
if ($sanExtension.Count -ne 1) { throw "The leaf CSR must contain exactly one SAN extension." }
$sanFields = $sanExtension[0].Context.PostContext
$sanValue = $sanFields[0]
if ($sanValue -match '^\s*\d+:d=7\s+.*prim:\s+BOOLEAN\s*:') { $sanValue = $sanFields[1] }
if ($sanValue -cnotmatch '^\s*\d+:d=7\s+.*prim:\s+OCTET STRING\s+\[HEX DUMP\]:([0-9A-F]+)\s*$') {
    throw "Could not read the leaf CSR SAN values."
}
$actualSan = $Matches[1]

# Compare the DER GeneralNames for this demo's DNS name and IPv4 address in either order.
$dnsBytes = [Text.Encoding]::ASCII.GetBytes($dnsName)
$ipBytes = ([Net.IPAddress]::Parse($ipAddress)).GetAddressBytes()
$dnsHex = '82{0:X2}{1}' -f $dnsBytes.Length, ([BitConverter]::ToString($dnsBytes) -replace '-')
$ipHex = '87{0:X2}{1}' -f $ipBytes.Length, ([BitConverter]::ToString($ipBytes) -replace '-')
$sequence = '30{0:X2}' -f ($dnsBytes.Length + $ipBytes.Length + 4)
if ($actualSan -cnotin @("$sequence$dnsHex$ipHex", "$sequence$ipHex$dnsHex")) {
    throw "The leaf CSR SANs must match the enrollment request. Regenerate the leaf CSR."
}

$issuer = Invoke-RestMethod -Method Post -Uri "$base/issuers" -Headers $headers -ContentType "application/json" -Body (@{
    name = "demo-intermediate"
    kind = "intermediate_ca"
    certificate_pem = Get-Content -Raw .tmp-demo\issuer.crt
    key_ref = (Resolve-Path .tmp-demo\issuer.key).Path
} | ConvertTo-Json)

$identity = Invoke-RestMethod -Method Post -Uri "$base/identities" -Headers $headers -ContentType "application/json" -Body (@{
    type = "machine"
    name = "edge-01"
    external_id = "asset-edge-01"
} | ConvertTo-Json)

$enrollment = Invoke-RestMethod -Method Post -Uri "$base/enrollments" -Headers $headers -ContentType "application/json" -Body (@{
    identity_id = $identity.id
    issuer_id = $issuer.id
    csr_pem = $csrPem
    requested_subject = "CN=edge-01"
    requested_dns_names = @($dnsName)
    requested_ip_addresses = @($ipAddress)
    requested_not_after = (Get-Date).ToUniversalTime().AddDays(30).ToString("o")
} | ConvertTo-Json)

$approved = Invoke-RestMethod -Method Post -Uri "$base/enrollments/$($enrollment.id)/approve" -Headers $headers

$certificate = Invoke-RestMethod -Method Post -Uri "$base/certificates" -Headers $headers -ContentType "application/json" -Body (@{
    enrollment_id = $approved.id
} | ConvertTo-Json)

Invoke-RestMethod -Method Get -Uri "$base/certificates"

$revoked = Invoke-RestMethod -Method Post -Uri "$base/certificates/$($certificate.id)/revoke" -Headers $headers -ContentType "application/json" -Body (@{
    reason = "key_compromise"
} | ConvertTo-Json)

Invoke-RestMethod -Method Get -Uri "$base/audit-events"
```

Expected result: the certificate status starts as `valid`, revocation changes it to `revoked`, and audit events include issuer, identity, enrollment, approval, issuance, and revocation actions.

Audit metadata field semantics are documented in [audit-metadata.md](../reference/audit-metadata.md).
