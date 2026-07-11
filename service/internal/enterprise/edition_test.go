// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package enterprise

import "testing"

func TestEnterpriseEditionMetadata(t *testing.T) {
	if EditionName != "AnoPKI Enterprise" {
		t.Fatalf("unexpected edition name: %q", EditionName)
	}
	if len(EnabledFeatures()) == 0 {
		t.Fatal("expected Enterprise feature metadata")
	}
	if OverlayVersion != "unreleased" || OverlayStatus != "private-alpha" {
		t.Fatalf("unexpected overlay metadata: %q %q", OverlayVersion, OverlayStatus)
	}
	if ActiveCryptoBackend != "openssl" || ExperimentalCryptoBackend != "anocrypto" || ExperimentalCryptoBackendStatus != "skeleton_pending" {
		t.Fatalf("unexpected backend metadata: %q %q %q", ActiveCryptoBackend, ExperimentalCryptoBackend, ExperimentalCryptoBackendStatus)
	}
}
