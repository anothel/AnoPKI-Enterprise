// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import "strings"

type Environment string

const (
	EnvironmentDevelopment Environment = "development"
	EnvironmentTest        Environment = "test"
	EnvironmentStaging     Environment = "staging"
	EnvironmentProduction  Environment = "production"
)

type ProductProfile string

const ProductProfileEnterpriseOpenSSL ProductProfile = "enterprise-openssl"

type AuthorizationRequest struct {
	Action         string            `json:"action"`
	ResourceType   string            `json:"resource_type"`
	ResourceID     string            `json:"resource_id,omitempty"`
	Environment    Environment       `json:"environment"`
	ProductProfile ProductProfile    `json:"product_profile"`
	RequestID      string            `json:"request_id,omitempty"`
	Attributes     map[string]string `json:"attributes"`
}

func NormalizeRequest(request AuthorizationRequest) (AuthorizationRequest, error) {
	request.Action = strings.ToLower(strings.TrimSpace(request.Action))
	request.ResourceType = strings.ToLower(strings.TrimSpace(request.ResourceType))
	request.ResourceID = strings.TrimSpace(request.ResourceID)
	request.Environment = Environment(strings.ToLower(strings.TrimSpace(string(request.Environment))))
	request.ProductProfile = ProductProfile(strings.ToLower(strings.TrimSpace(string(request.ProductProfile))))
	request.RequestID = strings.TrimSpace(request.RequestID)
	if request.Action == "" {
		return AuthorizationRequest{}, ErrActionUnknown
	}
	if request.ResourceType == "" {
		return AuthorizationRequest{}, ErrResourceUnknown
	}
	if !knownEnvironment(request.Environment) || request.ProductProfile != ProductProfileEnterpriseOpenSSL {
		return AuthorizationRequest{}, ErrContextMismatch
	}
	attributes, err := normalizedRequestAttributes(request.Attributes)
	if err != nil {
		return AuthorizationRequest{}, err
	}
	request.Attributes = attributes
	return request, nil
}

func knownEnvironment(environment Environment) bool {
	switch environment {
	case EnvironmentDevelopment, EnvironmentTest, EnvironmentStaging, EnvironmentProduction:
		return true
	default:
		return false
	}
}

func normalizedRequestAttributes(attributes map[string]string) (map[string]string, error) {
	normalized, err := normalizedAttributes(attributes)
	if err != nil {
		return nil, ErrRequestInvalid
	}
	return normalized, nil
}
