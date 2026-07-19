// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"bytes"
	"regexp"
	"slices"
	"testing"
)

func TestCanonicalSubjectIgnoresRoleAndAttributeOrder(t *testing.T) {
	left := Subject{ID: "subject-1", Kind: SubjectKindHuman, AuthenticationMethod: AuthenticationMethodAPIKey, Roles: []string{"Writer", "reader", "writer"}, Attributes: map[string]string{"Team": "pki", "region": "kr"}}
	right := Subject{ID: "subject-1", Kind: SubjectKindHuman, AuthenticationMethod: AuthenticationMethodAPIKey, Roles: []string{"reader", "writer"}, Attributes: map[string]string{"region": "kr", "team": "pki"}}
	leftJSON, err := CanonicalSubject(left)
	if err != nil {
		t.Fatal(err)
	}
	rightJSON, err := CanonicalSubject(right)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(leftJSON, rightJSON) {
		t.Fatalf("canonical subjects differ:\n%s\n%s", leftJSON, rightJSON)
	}
}

func TestPolicyFingerprintIgnoresPolicyAndConditionOrder(t *testing.T) {
	fixture := loadEngineFixture(t)
	left := fixture.PolicySet
	right := fixture.PolicySet
	right.Policies = slices.Clone(right.Policies)
	slices.Reverse(right.Policies)
	right.Policies[0].Conditions = map[string]string{"request.zone": "internal", "subject.team": "pki"}
	left.Policies[len(left.Policies)-1].Conditions = map[string]string{"subject.team": "pki", "request.zone": "internal"}
	leftHash, err := PolicySetFingerprint(left)
	if err != nil {
		t.Fatal(err)
	}
	rightHash, err := PolicySetFingerprint(right)
	if err != nil {
		t.Fatal(err)
	}
	if leftHash != rightHash || !regexp.MustCompile(`^[0-9a-f]{64}$`).MatchString(leftHash) {
		t.Fatalf("fingerprints = %q %q", leftHash, rightHash)
	}
}

func TestCanonicalRequestIgnoresAttributeOrder(t *testing.T) {
	left := testRequest("certificate.read", "certificate")
	right := left
	left.Attributes = map[string]string{"zone": "internal", "team": "pki"}
	right.Attributes = map[string]string{"team": "pki", "zone": "internal"}
	leftJSON, err := CanonicalRequest(left)
	if err != nil {
		t.Fatal(err)
	}
	rightJSON, err := CanonicalRequest(right)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(leftJSON, rightJSON) {
		t.Fatalf("canonical requests differ:\n%s\n%s", leftJSON, rightJSON)
	}
}

func TestCanonicalDecisionSortsMatchedPolicyIDs(t *testing.T) {
	decision := Decision{Result: DecisionDeny, ReasonCode: ReasonExplicitDeny, MatchedPolicyIDs: []string{"z", "a"}, ApprovalRequirement: ApprovalNone}
	encoded, err := CanonicalDecision(decision)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(encoded, []byte(`"matched_policy_ids":["a","z"]`)) || bytes.Contains(encoded, []byte("\n")) {
		t.Fatalf("decision is not canonical: %s", encoded)
	}
}
