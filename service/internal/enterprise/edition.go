// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package enterprise

const EditionName = "AnoPKI Enterprise"
const OverlayVersion = "unreleased"
const OverlayStatus = "private-alpha"
const ActiveCryptoBackend = "openssl"
const ExperimentalCryptoBackend = "anocrypto-c"
const ExperimentalCryptoBackendStatus = "external_sdk_not_configured"
const AnoCryptoSDKPackage = "AnoCryptoC::AnoCryptoC"
const AnoCryptoCapabilityStatus = "sdk_capabilities_unverified"
const PKIParityStatus = "unsupported_pending"
const ValidatedMode = false
const CryptoBackendDirection = ExperimentalCryptoBackend

func EnabledFeatures() []string {
	return []string{
		"authorization-decision-contract",
		"external-anocrypto-sdk-adapter-boundary",
		"commercial-license-boundary",
		"future-sso-rbac",
		"future-deploy-adapters",
		"future-siem-export",
	}
}
