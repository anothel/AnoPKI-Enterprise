// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package enterprise

import (
	"slices"
	"testing"
)

func TestEnterpriseEditionMetadata(t *testing.T) {
	if EditionName != "AnoPKI Enterprise" {
		t.Fatalf("unexpected edition name: %q", EditionName)
	}
	if len(EnabledFeatures()) == 0 {
		t.Fatal("expected Enterprise feature metadata")
	}
	if !slices.Contains(EnabledFeatures(), "authorization-decision-contract") {
		t.Fatal("expected authorization decision contract feature metadata")
	}
	if OverlayVersion != "unreleased" || OverlayStatus != "private-alpha" {
		t.Fatalf("unexpected overlay metadata: %q %q", OverlayVersion, OverlayStatus)
	}
	if ActiveCryptoBackend != "openssl" || ExperimentalCryptoBackend != "anocrypto-c" || ExperimentalCryptoBackendStatus != "external_sdk_not_configured" {
		t.Fatalf("unexpected backend metadata: %q %q %q", ActiveCryptoBackend, ExperimentalCryptoBackend, ExperimentalCryptoBackendStatus)
	}
	if AnoCryptoSDKPackage != "AnoCryptoC::AnoCryptoC" || AnoCryptoCapabilityStatus != "sdk_capabilities_unverified" || PKIParityStatus != "unsupported_pending" || ValidatedMode {
		t.Fatalf("unexpected SDK metadata: %q %q %q %t", AnoCryptoSDKPackage, AnoCryptoCapabilityStatus, PKIParityStatus, ValidatedMode)
	}
}
