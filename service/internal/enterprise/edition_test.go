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
}
