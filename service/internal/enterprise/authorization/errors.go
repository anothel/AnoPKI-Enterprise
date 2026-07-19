// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package authorization

import (
	"errors"
	"strings"
)

var (
	ErrSubjectInvalid    = errors.New("invalid authorization subject")
	ErrRequestInvalid    = errors.New("invalid authorization request")
	ErrPolicyInvalid     = errors.New("invalid authorization policy")
	ErrPolicySetMissing  = errors.New("authorization policy set is missing")
	ErrCatalogInvalid    = errors.New("invalid authorization catalog")
	ErrActionUnknown     = errors.New("unknown authorization action")
	ErrResourceUnknown   = errors.New("unknown authorization resource type")
	ErrContextMismatch   = errors.New("authorization context mismatch")
	ErrCanonicalEncoding = errors.New("canonical authorization encoding failed")
)

var forbiddenEvidenceKeys = map[string]struct{}{
	"api_key":          {},
	"api_key_hash":     {},
	"api_key_token":    {},
	"certificate":      {},
	"cookie":           {},
	"credential":       {},
	"csr":              {},
	"full_certificate": {},
	"full_csr":         {},
	"jwt":              {},
	"key_ref":          {},
	"key_reference":    {},
	"local_path":       {},
	"password":         {},
	"path":             {},
	"pin":              {},
	"private_key":      {},
	"raw_api_key":      {},
	"raw_request_body": {},
	"request_body":     {},
	"saml_assertion":   {},
	"session_id":       {},
	"token":            {},
	"token_hash":       {},
}

func normalizedKey(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	value = strings.NewReplacer("-", "_", " ", "_").Replace(value)
	return value
}

func forbiddenEvidenceKey(value string) bool {
	_, forbidden := forbiddenEvidenceKeys[normalizedKey(value)]
	return forbidden
}
