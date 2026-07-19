// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
)

func CanonicalSubject(subject Subject) ([]byte, error) {
	normalized, err := NormalizeSubject(subject)
	if err != nil {
		return nil, err
	}
	return canonicalJSON(normalized)
}

func CanonicalRequest(request AuthorizationRequest) ([]byte, error) {
	normalized, err := NormalizeRequest(request)
	if err != nil {
		return nil, err
	}
	return canonicalJSON(normalized)
}

func CanonicalPolicySet(set PolicySet) ([]byte, error) {
	normalized, err := normalizePolicySet(set, nil)
	if err != nil {
		return nil, err
	}
	return canonicalJSON(normalized)
}

func CanonicalDecision(decision Decision) ([]byte, error) {
	if !knownDecisionResult(decision.Result) || !knownReasonCode(decision.ReasonCode) || !knownApprovalRequirement(decision.ApprovalRequirement) {
		return nil, ErrCanonicalEncoding
	}
	decision.MatchedPolicyIDs = append([]string(nil), decision.MatchedPolicyIDs...)
	sort.Strings(decision.MatchedPolicyIDs)
	return canonicalJSON(decision)
}

func PolicySetFingerprint(set PolicySet) (string, error) {
	encoded, err := CanonicalPolicySet(set)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(encoded)
	return hex.EncodeToString(sum[:]), nil
}

func canonicalJSON(value any) ([]byte, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrCanonicalEncoding, err)
	}
	return encoded, nil
}

func knownDecisionResult(result DecisionResult) bool {
	return result == DecisionAllow || result == DecisionDeny || result == DecisionApprovalRequired
}

func knownReasonCode(reason ReasonCode) bool {
	switch reason {
	case ReasonAllowed, ReasonApprovalRequired, ReasonSubjectMissing, ReasonSubjectInvalid, ReasonActionUnknown, ReasonResourceUnknown, ReasonPolicyInvalid, ReasonExplicitDeny, ReasonNoMatchingAllow, ReasonContextMismatch:
		return true
	default:
		return false
	}
}
