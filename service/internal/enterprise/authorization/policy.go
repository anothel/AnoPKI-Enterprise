// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"sort"
	"strings"
)

type Effect string

const (
	EffectAllow Effect = "allow"
	EffectDeny  Effect = "deny"
)

type ApprovalRequirement string

const (
	ApprovalNone   ApprovalRequirement = "none"
	ApprovalSingle ApprovalRequirement = "single"
	ApprovalDual   ApprovalRequirement = "dual"
)

type Policy struct {
	ID                  string              `json:"id"`
	Version             string              `json:"version"`
	Effect              Effect              `json:"effect"`
	Subjects            []string            `json:"subjects"`
	Roles               []string            `json:"roles"`
	Actions             []string            `json:"actions"`
	ResourceTypes       []string            `json:"resource_types"`
	Conditions          map[string]string   `json:"conditions"`
	ApprovalRequirement ApprovalRequirement `json:"approval_requirement"`
}

type PolicySet struct {
	ID       string   `json:"id"`
	Version  string   `json:"version"`
	Policies []Policy `json:"policies"`
}

// Catalog is supplied by the future integration layer. Actions map to their one
// permitted resource type; no wildcard behavior exists.
type Catalog struct {
	Actions       map[string]string `json:"actions"`
	ResourceTypes []string          `json:"resource_types"`
}

func normalizeCatalog(catalog Catalog) (Catalog, error) {
	resources, err := normalizedList(catalog.ResourceTypes, true, false)
	if err != nil || len(resources) == 0 || len(catalog.Actions) == 0 {
		return Catalog{}, ErrCatalogInvalid
	}
	resourceSet := make(map[string]struct{}, len(resources))
	for _, resource := range resources {
		resourceSet[resource] = struct{}{}
	}
	actions := make(map[string]string, len(catalog.Actions))
	for action, resource := range catalog.Actions {
		action = strings.ToLower(strings.TrimSpace(action))
		resource = strings.ToLower(strings.TrimSpace(resource))
		if action == "" || resource == "" || strings.Contains(action, "*") || strings.Contains(resource, "*") {
			return Catalog{}, ErrCatalogInvalid
		}
		if _, exists := actions[action]; exists {
			return Catalog{}, ErrCatalogInvalid
		}
		if _, known := resourceSet[resource]; !known {
			return Catalog{}, ErrCatalogInvalid
		}
		actions[action] = resource
	}
	return Catalog{Actions: actions, ResourceTypes: resources}, nil
}

func normalizePolicySet(set PolicySet, catalog *Catalog) (PolicySet, error) {
	set.ID = strings.TrimSpace(set.ID)
	set.Version = strings.TrimSpace(set.Version)
	if set.ID == "" || set.Version == "" || len(set.Policies) == 0 {
		return PolicySet{}, ErrPolicyInvalid
	}
	seen := make(map[string]string, len(set.Policies))
	policies := make([]Policy, 0, len(set.Policies))
	for _, policy := range set.Policies {
		normalized, err := normalizePolicy(policy, catalog)
		if err != nil {
			return PolicySet{}, err
		}
		if version, exists := seen[normalized.ID]; exists {
			_ = version // Same ID is invalid whether the version repeats or conflicts.
			return PolicySet{}, ErrPolicyInvalid
		}
		seen[normalized.ID] = normalized.Version
		policies = append(policies, normalized)
	}
	sort.Slice(policies, func(i, j int) bool {
		if policies[i].ID == policies[j].ID {
			return policies[i].Version < policies[j].Version
		}
		return policies[i].ID < policies[j].ID
	})
	set.Policies = policies
	return set, nil
}

func normalizePolicy(policy Policy, catalog *Catalog) (Policy, error) {
	policy.ID = strings.TrimSpace(policy.ID)
	policy.Version = strings.TrimSpace(policy.Version)
	policy.Effect = Effect(strings.ToLower(strings.TrimSpace(string(policy.Effect))))
	policy.ApprovalRequirement = ApprovalRequirement(strings.ToLower(strings.TrimSpace(string(policy.ApprovalRequirement))))
	if policy.ID == "" || policy.Version == "" || (policy.Effect != EffectAllow && policy.Effect != EffectDeny) || !knownApprovalRequirement(policy.ApprovalRequirement) {
		return Policy{}, ErrPolicyInvalid
	}
	if policy.Effect == EffectDeny && policy.ApprovalRequirement != ApprovalNone {
		return Policy{}, ErrPolicyInvalid
	}
	var err error
	if policy.Subjects, err = normalizedList(policy.Subjects, false, false); err != nil {
		return Policy{}, ErrPolicyInvalid
	}
	if policy.Roles, err = normalizedList(policy.Roles, true, false); err != nil {
		return Policy{}, ErrPolicyInvalid
	}
	if len(policy.Subjects) == 0 && len(policy.Roles) == 0 {
		return Policy{}, ErrPolicyInvalid
	}
	if policy.Actions, err = normalizedList(policy.Actions, true, false); err != nil || len(policy.Actions) == 0 {
		return Policy{}, ErrPolicyInvalid
	}
	if policy.ResourceTypes, err = normalizedList(policy.ResourceTypes, true, false); err != nil || len(policy.ResourceTypes) == 0 {
		return Policy{}, ErrPolicyInvalid
	}
	conditions := make(map[string]string, len(policy.Conditions))
	for key, value := range policy.Conditions {
		key = normalizeConditionKey(key)
		if !validConditionKey(key) || strings.Contains(value, "*") {
			return Policy{}, ErrPolicyInvalid
		}
		if _, exists := conditions[key]; exists {
			return Policy{}, ErrPolicyInvalid
		}
		conditions[key] = value
	}
	policy.Conditions = conditions

	if catalog != nil {
		for _, action := range policy.Actions {
			resource, known := catalog.Actions[action]
			if !known {
				return Policy{}, ErrPolicyInvalid
			}
			if !contains(policy.ResourceTypes, resource) {
				return Policy{}, ErrPolicyInvalid
			}
		}
		for _, resource := range policy.ResourceTypes {
			if !contains(catalog.ResourceTypes, resource) {
				return Policy{}, ErrPolicyInvalid
			}
		}
	}
	return policy, nil
}

func knownApprovalRequirement(requirement ApprovalRequirement) bool {
	return requirement == ApprovalNone || requirement == ApprovalSingle || requirement == ApprovalDual
}

func normalizeConditionKey(key string) string {
	key = strings.ToLower(strings.TrimSpace(key))
	if prefix, suffix, ok := strings.Cut(key, "."); ok {
		return normalizedKey(prefix) + "." + normalizedKey(suffix)
	}
	return normalizedKey(key)
}

func validConditionKey(key string) bool {
	switch key {
	case "environment", "product_profile", "subject.id", "subject.kind", "subject.authentication_method":
		return true
	}
	prefix, attribute, ok := strings.Cut(key, ".")
	return ok && (prefix == "subject" || prefix == "request") && attribute != "" && !forbiddenEvidenceKey(attribute)
}

func contains(values []string, value string) bool {
	index := sort.SearchStrings(values, value)
	return index < len(values) && values[index] == value
}
