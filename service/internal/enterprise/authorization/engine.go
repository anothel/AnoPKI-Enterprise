// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"errors"
	"sort"
	"strings"
)

type Engine struct {
	catalog     Catalog
	policySet   PolicySet
	fingerprint string
	initErr     error
}

// NewEngine never panics. Invalid or missing configuration is retained so all
// subsequent decisions fail closed with authz.policy_invalid.
func NewEngine(policySet *PolicySet, catalog Catalog) *Engine {
	engine := &Engine{}
	normalizedCatalog, err := normalizeCatalog(catalog)
	if err != nil {
		engine.initErr = err
		return engine
	}
	engine.catalog = normalizedCatalog
	if policySet == nil {
		engine.initErr = ErrPolicySetMissing
		return engine
	}
	normalizedSet, err := normalizePolicySet(*policySet, &normalizedCatalog)
	if err != nil {
		engine.policySet = PolicySet{ID: strings.TrimSpace(policySet.ID), Version: strings.TrimSpace(policySet.Version)}
		engine.initErr = err
		return engine
	}
	engine.policySet = normalizedSet
	engine.fingerprint, err = PolicySetFingerprint(normalizedSet)
	if err != nil {
		engine.initErr = err
	}
	return engine
}

func (engine *Engine) Decide(subject *Subject, request AuthorizationRequest) Decision {
	decision := Decision{
		Result:              DecisionDeny,
		ReasonCode:          ReasonPolicyInvalid,
		Action:              strings.ToLower(strings.TrimSpace(request.Action)),
		ResourceType:        strings.ToLower(strings.TrimSpace(request.ResourceType)),
		ResourceID:          strings.TrimSpace(request.ResourceID),
		MatchedPolicyIDs:    []string{},
		ApprovalRequirement: ApprovalNone,
		RequestID:           strings.TrimSpace(request.RequestID),
	}
	if engine != nil {
		decision.PolicySetID = engine.policySet.ID
		decision.PolicySetVersion = engine.policySet.Version
		decision.PolicySetSHA256 = engine.fingerprint
	}
	if subject == nil {
		decision.ReasonCode = ReasonSubjectMissing
		return decision
	}
	decision.SubjectID = strings.TrimSpace(subject.ID)
	normalizedSubject, err := NormalizeSubject(*subject)
	if err != nil {
		decision.ReasonCode = ReasonSubjectInvalid
		return decision
	}
	decision.SubjectID = normalizedSubject.ID
	normalizedRequest, err := NormalizeRequest(request)
	if err != nil {
		decision.ReasonCode = requestReason(err)
		return decision
	}
	decision.Action = normalizedRequest.Action
	decision.ResourceType = normalizedRequest.ResourceType
	decision.ResourceID = normalizedRequest.ResourceID
	decision.RequestID = normalizedRequest.RequestID

	if engine == nil || engine.initErr != nil {
		return decision
	}
	resource, known := engine.catalog.Actions[normalizedRequest.Action]
	if !known {
		decision.ReasonCode = ReasonActionUnknown
		return decision
	}
	if !contains(engine.catalog.ResourceTypes, normalizedRequest.ResourceType) || resource != normalizedRequest.ResourceType {
		decision.ReasonCode = ReasonResourceUnknown
		return decision
	}

	var denyIDs, approvalIDs, allowIDs []string
	approval := ApprovalNone
	contextMismatch := false
	for _, policy := range engine.policySet.Policies {
		if !policyTargetMatches(policy, normalizedSubject, normalizedRequest) {
			continue
		}
		conditionsMatch, conditionErr := policyConditionsMatch(policy, normalizedSubject, normalizedRequest)
		if conditionErr != nil {
			decision.ReasonCode = ReasonContextMismatch
			return decision
		}
		if !conditionsMatch {
			contextMismatch = true
			continue
		}
		if policy.Effect == EffectDeny {
			denyIDs = append(denyIDs, policy.ID)
			continue
		}
		if policy.ApprovalRequirement != ApprovalNone {
			approvalIDs = append(approvalIDs, policy.ID)
			approval = strongestApproval(approval, policy.ApprovalRequirement)
			continue
		}
		allowIDs = append(allowIDs, policy.ID)
	}

	switch {
	case len(denyIDs) > 0:
		decision.ReasonCode = ReasonExplicitDeny
		decision.MatchedPolicyIDs = sortedUnique(denyIDs)
	case len(approvalIDs) > 0:
		decision.Result = DecisionApprovalRequired
		decision.ReasonCode = ReasonApprovalRequired
		decision.MatchedPolicyIDs = sortedUnique(approvalIDs)
		decision.ApprovalRequirement = approval
	case len(allowIDs) > 0:
		decision.Result = DecisionAllow
		decision.ReasonCode = ReasonAllowed
		decision.MatchedPolicyIDs = sortedUnique(allowIDs)
	case contextMismatch:
		decision.ReasonCode = ReasonContextMismatch
	default:
		decision.ReasonCode = ReasonNoMatchingAllow
	}
	return decision
}

func requestReason(err error) ReasonCode {
	switch {
	case errors.Is(err, ErrActionUnknown):
		return ReasonActionUnknown
	case errors.Is(err, ErrResourceUnknown):
		return ReasonResourceUnknown
	default:
		return ReasonContextMismatch
	}
}

func policyTargetMatches(policy Policy, subject Subject, request AuthorizationRequest) bool {
	if len(policy.Subjects) > 0 && !contains(policy.Subjects, subject.ID) {
		return false
	}
	if len(policy.Roles) > 0 && !intersects(policy.Roles, subject.Roles) {
		return false
	}
	return contains(policy.Actions, request.Action) && contains(policy.ResourceTypes, request.ResourceType)
}

func policyConditionsMatch(policy Policy, subject Subject, request AuthorizationRequest) (bool, error) {
	for key, expected := range policy.Conditions {
		actual, exists := conditionValue(key, subject, request)
		if !exists || actual != expected {
			return false, nil
		}
	}
	return true, nil
}

func conditionValue(key string, subject Subject, request AuthorizationRequest) (string, bool) {
	switch key {
	case "environment":
		return string(request.Environment), true
	case "product_profile":
		return string(request.ProductProfile), true
	case "subject.id":
		return subject.ID, true
	case "subject.kind":
		return string(subject.Kind), true
	case "subject.authentication_method":
		return string(subject.AuthenticationMethod), true
	}
	prefix, attribute, ok := strings.Cut(key, ".")
	if !ok {
		return "", false
	}
	if prefix == "subject" {
		value, exists := subject.Attributes[attribute]
		return value, exists
	}
	if prefix == "request" {
		value, exists := request.Attributes[attribute]
		return value, exists
	}
	return "", false
}

func intersects(left, right []string) bool {
	for _, value := range left {
		if contains(right, value) {
			return true
		}
	}
	return false
}

func strongestApproval(left, right ApprovalRequirement) ApprovalRequirement {
	if left == ApprovalDual || right == ApprovalDual {
		return ApprovalDual
	}
	if left == ApprovalSingle || right == ApprovalSingle {
		return ApprovalSingle
	}
	return ApprovalNone
}

func sortedUnique(values []string) []string {
	sort.Strings(values)
	unique := values[:0]
	for _, value := range values {
		if len(unique) == 0 || unique[len(unique)-1] != value {
			unique = append(unique, value)
		}
	}
	return unique
}
