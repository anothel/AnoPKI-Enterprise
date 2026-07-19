// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"sort"
	"strings"
)

type SubjectKind string

const (
	SubjectKindHuman   SubjectKind = "human"
	SubjectKindService SubjectKind = "service"
)

type AuthenticationMethod string

const (
	AuthenticationMethodDev             AuthenticationMethod = "dev"
	AuthenticationMethodAPIKey          AuthenticationMethod = "api_key"
	AuthenticationMethodOIDC            AuthenticationMethod = "oidc"
	AuthenticationMethodSAML            AuthenticationMethod = "saml"
	AuthenticationMethodServiceIdentity AuthenticationMethod = "service_identity"
)

type Subject struct {
	ID                   string               `json:"id"`
	Kind                 SubjectKind          `json:"kind"`
	AuthenticationMethod AuthenticationMethod `json:"authentication_method"`
	Roles                []string             `json:"roles"`
	Attributes           map[string]string    `json:"attributes"`
}

func NormalizeSubject(subject Subject) (Subject, error) {
	subject.ID = strings.TrimSpace(subject.ID)
	subject.Kind = SubjectKind(strings.ToLower(strings.TrimSpace(string(subject.Kind))))
	subject.AuthenticationMethod = AuthenticationMethod(strings.ToLower(strings.TrimSpace(string(subject.AuthenticationMethod))))
	if subject.ID == "" || (subject.Kind != SubjectKindHuman && subject.Kind != SubjectKindService) || !knownAuthenticationMethod(subject.AuthenticationMethod) {
		return Subject{}, ErrSubjectInvalid
	}

	roles, err := normalizedList(subject.Roles, true, false)
	if err != nil {
		return Subject{}, ErrSubjectInvalid
	}
	subject.Roles = roles
	subject.Attributes, err = normalizedAttributes(subject.Attributes)
	if err != nil {
		return Subject{}, ErrSubjectInvalid
	}
	return subject, nil
}

func knownAuthenticationMethod(method AuthenticationMethod) bool {
	switch method {
	case AuthenticationMethodDev, AuthenticationMethodAPIKey, AuthenticationMethodOIDC, AuthenticationMethodSAML, AuthenticationMethodServiceIdentity:
		return true
	default:
		return false
	}
}

func normalizedAttributes(attributes map[string]string) (map[string]string, error) {
	normalized := make(map[string]string, len(attributes))
	for key, value := range attributes {
		key = normalizedKey(key)
		if key == "" || forbiddenEvidenceKey(key) {
			return nil, ErrSubjectInvalid
		}
		if _, exists := normalized[key]; exists {
			return nil, ErrSubjectInvalid
		}
		normalized[key] = value
	}
	return normalized, nil
}

func normalizedList(values []string, lower bool, allowEmpty bool) ([]string, error) {
	seen := make(map[string]struct{}, len(values))
	normalized := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if lower {
			value = strings.ToLower(value)
		}
		if value == "" {
			if allowEmpty {
				continue
			}
			return nil, ErrPolicyInvalid
		}
		if strings.Contains(value, "*") {
			return nil, ErrPolicyInvalid
		}
		if _, exists := seen[value]; exists {
			continue
		}
		seen[value] = struct{}{}
		normalized = append(normalized, value)
	}
	sort.Strings(normalized)
	return normalized, nil
}
