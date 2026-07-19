// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"encoding/json"
	"os"
	"slices"
	"strings"
	"testing"
)

type engineFixture struct {
	Catalog   Catalog   `json:"catalog"`
	PolicySet PolicySet `json:"policy_set"`
}

func TestEngineDecisionContract(t *testing.T) {
	fixture := loadEngineFixture(t)
	engine := NewEngine(&fixture.PolicySet, fixture.Catalog)
	request := testRequest("certificate.read", "certificate")

	tests := []struct {
		name         string
		subject      *Subject
		request      AuthorizationRequest
		wantResult   DecisionResult
		wantReason   ReasonCode
		wantApproval ApprovalRequirement
	}{
		{"reader read", testSubject("reader"), request, DecisionAllow, ReasonAllowed, ApprovalNone},
		{"reader write", testSubject("reader"), testRequest("certificate.issue", "certificate"), DecisionDeny, ReasonNoMatchingAllow, ApprovalNone},
		{"support operator inventory", testSubject("support"), testRequest("operator.inventory.read", "operator_inventory"), DecisionAllow, ReasonAllowed, ApprovalNone},
		{"explicit deny overrides allow", testSubjectWithAttributes("operator", map[string]string{"issuer_status": "suspended"}), testRequest("certificate.issue", "certificate"), DecisionDeny, ReasonExplicitDeny, ApprovalNone},
		{"single approval", testSubject("operator"), testRequest("certificate.revoke", "certificate"), DecisionApprovalRequired, ReasonApprovalRequired, ApprovalSingle},
		{"dual approval", testSubject("operator"), testRequest("issuer.rotate", "issuer"), DecisionApprovalRequired, ReasonApprovalRequired, ApprovalDual},
		{"role mismatch", testSubject("reader"), testRequest("operator.inventory.read", "operator_inventory"), DecisionDeny, ReasonNoMatchingAllow, ApprovalNone},
		{"attribute mismatch", testSubjectWithAttributes("operator", map[string]string{"team": "app"}), testRequest("certificate.reissue", "certificate"), DecisionDeny, ReasonContextMismatch, ApprovalNone},
		{"unknown action", testSubject("reader"), testRequest("certificate.unknown", "certificate"), DecisionDeny, ReasonActionUnknown, ApprovalNone},
		{"unknown resource", testSubject("reader"), testRequest("certificate.read", "unknown"), DecisionDeny, ReasonResourceUnknown, ApprovalNone},
		{"unknown environment", testSubject("reader"), withEnvironment(request, "moon"), DecisionDeny, ReasonContextMismatch, ApprovalNone},
		{"unknown product profile", testSubject("reader"), withProfile(request, "community"), DecisionDeny, ReasonContextMismatch, ApprovalNone},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			decision := engine.Decide(test.subject, test.request)
			if decision.Result != test.wantResult || decision.ReasonCode != test.wantReason || decision.ApprovalRequirement != test.wantApproval {
				t.Fatalf("decision = %#v, want result=%q reason=%q approval=%q", decision, test.wantResult, test.wantReason, test.wantApproval)
			}
			if decision.PolicySetSHA256 == "" {
				t.Fatal("valid engine decision omitted policy set fingerprint")
			}
		})
	}
}

func TestEngineFailsClosed(t *testing.T) {
	fixture := loadEngineFixture(t)
	validSubject := testSubject("reader")
	validRequest := testRequest("certificate.read", "certificate")

	tests := []struct {
		name       string
		engine     *Engine
		subject    *Subject
		wantReason ReasonCode
	}{
		{"missing subject", NewEngine(&fixture.PolicySet, fixture.Catalog), nil, ReasonSubjectMissing},
		{"empty subject id", NewEngine(&fixture.PolicySet, fixture.Catalog), &Subject{Kind: SubjectKindHuman, AuthenticationMethod: AuthenticationMethodDev}, ReasonSubjectInvalid},
		{"unknown subject kind", NewEngine(&fixture.PolicySet, fixture.Catalog), &Subject{ID: "user-1", Kind: "robot", AuthenticationMethod: AuthenticationMethodDev}, ReasonSubjectInvalid},
		{"unknown authentication method", NewEngine(&fixture.PolicySet, fixture.Catalog), &Subject{ID: "user-1", Kind: SubjectKindHuman, AuthenticationMethod: "magic"}, ReasonSubjectInvalid},
		{"empty role", NewEngine(&fixture.PolicySet, fixture.Catalog), &Subject{ID: "user-1", Kind: SubjectKindHuman, AuthenticationMethod: AuthenticationMethodDev, Roles: []string{""}}, ReasonSubjectInvalid},
		{"raw request body attribute", NewEngine(&fixture.PolicySet, fixture.Catalog), validSubject, ReasonContextMismatch},
		{"missing policy set", NewEngine(nil, fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"empty policy set", NewEngine(&PolicySet{ID: "empty", Version: "1"}, fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"malformed policy", NewEngine(&PolicySet{ID: "bad", Version: "1", Policies: []Policy{{ID: "bad", Version: "1", Effect: EffectAllow, Roles: []string{"reader"}, ResourceTypes: []string{"certificate"}, ApprovalRequirement: ApprovalNone}}}, fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"duplicate policy", NewEngine(duplicatePolicySet(fixture.PolicySet, false), fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"conflicting policy version", NewEngine(duplicatePolicySet(fixture.PolicySet, true), fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"wildcard policy", NewEngine(wildcardPolicySet(), fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"implicit broad policy", NewEngine(implicitBroadPolicySet(), fixture.Catalog), validSubject, ReasonPolicyInvalid},
		{"malformed condition", NewEngine(malformedConditionPolicySet(), fixture.Catalog), validSubject, ReasonPolicyInvalid},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request := validRequest
			if test.name == "raw request body attribute" {
				request.Attributes = map[string]string{"raw_request_body": "do-not-store"}
			}
			decision := test.engine.Decide(test.subject, request)
			if decision.Result != DecisionDeny || decision.ReasonCode != test.wantReason {
				t.Fatalf("decision = %#v, want deny/%s", decision, test.wantReason)
			}
		})
	}
}

func TestPolicyOrderDoesNotChangeDecision(t *testing.T) {
	fixture := loadEngineFixture(t)
	reversed := fixture.PolicySet
	reversed.Policies = slices.Clone(reversed.Policies)
	slices.Reverse(reversed.Policies)
	subject := testSubjectWithAttributes("operator", map[string]string{"issuer_status": "suspended"})
	request := testRequest("certificate.issue", "certificate")
	left := NewEngine(&fixture.PolicySet, fixture.Catalog).Decide(subject, request)
	right := NewEngine(&reversed, fixture.Catalog).Decide(subject, request)
	if !slices.Equal(left.MatchedPolicyIDs, right.MatchedPolicyIDs) || left.Result != right.Result || left.ReasonCode != right.ReasonCode || left.PolicySetSHA256 != right.PolicySetSHA256 {
		t.Fatalf("policy order changed decision:\nleft=%#v\nright=%#v", left, right)
	}
}

func TestDecisionEvidenceRejectsRawIdentityArtifacts(t *testing.T) {
	fixture := loadEngineFixture(t)
	subject := testSubjectWithAttributes("reader", map[string]string{"raw_api_key": "do-not-store"})
	decision := NewEngine(&fixture.PolicySet, fixture.Catalog).Decide(subject, testRequest("certificate.read", "certificate"))
	if decision.ReasonCode != ReasonSubjectInvalid {
		t.Fatalf("decision = %#v, want subject invalid", decision)
	}
	encoded, err := json.Marshal(decision.Evidence(*subject))
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(encoded), "do-not-store") || strings.Contains(string(encoded), "raw_api_key") {
		t.Fatalf("evidence leaked raw identity artifact: %s", encoded)
	}
}

func loadEngineFixture(t *testing.T) engineFixture {
	t.Helper()
	encoded, err := os.ReadFile("testdata/policy-fixtures.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture engineFixture
	if err := json.Unmarshal(encoded, &fixture); err != nil {
		t.Fatal(err)
	}
	return fixture
}

func testSubject(role string) *Subject {
	return testSubjectWithAttributes(role, map[string]string{})
}

func testSubjectWithAttributes(role string, attributes map[string]string) *Subject {
	return &Subject{ID: "subject-1", Kind: SubjectKindHuman, AuthenticationMethod: AuthenticationMethodAPIKey, Roles: []string{role}, Attributes: attributes}
}

func testRequest(action, resourceType string) AuthorizationRequest {
	return AuthorizationRequest{Action: action, ResourceType: resourceType, ResourceID: "resource-1", Environment: EnvironmentProduction, ProductProfile: ProductProfileEnterpriseOpenSSL, RequestID: "request-1", Attributes: map[string]string{}}
}

func withEnvironment(request AuthorizationRequest, environment Environment) AuthorizationRequest {
	request.Environment = environment
	return request
}

func withProfile(request AuthorizationRequest, profile ProductProfile) AuthorizationRequest {
	request.ProductProfile = profile
	return request
}

func duplicatePolicySet(set PolicySet, conflicting bool) *PolicySet {
	duplicate := set.Policies[0]
	if conflicting {
		duplicate.Version = "2"
	}
	set.Policies = append(slices.Clone(set.Policies), duplicate)
	return &set
}

func wildcardPolicySet() *PolicySet {
	return &PolicySet{ID: "wildcard", Version: "1", Policies: []Policy{{ID: "wildcard", Version: "1", Effect: EffectAllow, Roles: []string{"*"}, Actions: []string{"certificate.read"}, ResourceTypes: []string{"certificate"}, ApprovalRequirement: ApprovalNone}}}
}

func implicitBroadPolicySet() *PolicySet {
	return &PolicySet{ID: "broad", Version: "1", Policies: []Policy{{ID: "broad", Version: "1", Effect: EffectAllow, Actions: []string{"certificate.read"}, ResourceTypes: []string{"certificate"}, ApprovalRequirement: ApprovalNone}}}
}

func malformedConditionPolicySet() *PolicySet {
	return &PolicySet{ID: "condition", Version: "1", Policies: []Policy{{ID: "condition", Version: "1", Effect: EffectAllow, Roles: []string{"reader"}, Actions: []string{"certificate.read"}, ResourceTypes: []string{"certificate"}, Conditions: map[string]string{"script": "allow()"}, ApprovalRequirement: ApprovalNone}}}
}
