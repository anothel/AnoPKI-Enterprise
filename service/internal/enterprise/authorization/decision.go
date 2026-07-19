// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import "sort"

type DecisionResult string

const (
	DecisionAllow            DecisionResult = "allow"
	DecisionDeny             DecisionResult = "deny"
	DecisionApprovalRequired DecisionResult = "approval_required"
)

type ReasonCode string

const (
	ReasonAllowed          ReasonCode = "authz.allowed"
	ReasonApprovalRequired ReasonCode = "authz.approval_required"
	ReasonSubjectMissing   ReasonCode = "authz.subject_missing"
	ReasonSubjectInvalid   ReasonCode = "authz.subject_invalid"
	ReasonActionUnknown    ReasonCode = "authz.action_unknown"
	ReasonResourceUnknown  ReasonCode = "authz.resource_unknown"
	ReasonPolicyInvalid    ReasonCode = "authz.policy_invalid"
	ReasonExplicitDeny     ReasonCode = "authz.explicit_deny"
	ReasonNoMatchingAllow  ReasonCode = "authz.no_matching_allow"
	ReasonContextMismatch  ReasonCode = "authz.context_mismatch"
)

type Decision struct {
	Result              DecisionResult      `json:"result"`
	ReasonCode          ReasonCode          `json:"reason_code"`
	SubjectID           string              `json:"subject_id,omitempty"`
	Action              string              `json:"action,omitempty"`
	ResourceType        string              `json:"resource_type,omitempty"`
	ResourceID          string              `json:"resource_id,omitempty"`
	MatchedPolicyIDs    []string            `json:"matched_policy_ids"`
	PolicySetID         string              `json:"policy_set_id,omitempty"`
	PolicySetVersion    string              `json:"policy_set_version,omitempty"`
	PolicySetSHA256     string              `json:"policy_set_sha256,omitempty"`
	ApprovalRequirement ApprovalRequirement `json:"approval_requirement"`
	RequestID           string              `json:"request_id,omitempty"`
}

// DecisionEvidence is the stable, secret-free DTO reserved for future audit
// integration. It is correlation evidence, not a signature or tamper proof.
type DecisionEvidence struct {
	SubjectID            string               `json:"subject_id"`
	SubjectKind          SubjectKind          `json:"subject_kind"`
	AuthenticationMethod AuthenticationMethod `json:"authentication_method"`
	Action               string               `json:"action"`
	ResourceType         string               `json:"resource_type"`
	ResourceID           string               `json:"resource_id,omitempty"`
	Decision             DecisionResult       `json:"decision"`
	ReasonCode           ReasonCode           `json:"reason_code"`
	MatchedPolicyIDs     []string             `json:"matched_policy_ids"`
	PolicySetID          string               `json:"policy_set_id"`
	PolicySetVersion     string               `json:"policy_set_version"`
	PolicySetSHA256      string               `json:"policy_set_sha256"`
	ApprovalRequirement  ApprovalRequirement  `json:"approval_requirement"`
	RequestID            string               `json:"request_id,omitempty"`
}

func (decision Decision) Evidence(subject Subject) DecisionEvidence {
	matched := append([]string(nil), decision.MatchedPolicyIDs...)
	sort.Strings(matched)
	return DecisionEvidence{
		SubjectID:            decision.SubjectID,
		SubjectKind:          subject.Kind,
		AuthenticationMethod: subject.AuthenticationMethod,
		Action:               decision.Action,
		ResourceType:         decision.ResourceType,
		ResourceID:           decision.ResourceID,
		Decision:             decision.Result,
		ReasonCode:           decision.ReasonCode,
		MatchedPolicyIDs:     matched,
		PolicySetID:          decision.PolicySetID,
		PolicySetVersion:     decision.PolicySetVersion,
		PolicySetSHA256:      decision.PolicySetSHA256,
		ApprovalRequirement:  decision.ApprovalRequirement,
		RequestID:            decision.RequestID,
	}
}
