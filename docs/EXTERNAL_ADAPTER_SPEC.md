# External Adapter Specification — Manual First

- Status: DESIGN APPROVED
- Default mode: `MANUAL`
- Network calls: DISABLED

## Supported boundaries

- Maritime Authority reporting adapter.
- Vessel registry/registration verification adapter.

## Current behavior

- The application continues local/manual operation when no external API exists.
- Operators can prepare and export payloads/reports for manual submission.
- Registry verification remains a clearly labelled local certificate-date check.
- No missing endpoint or credential may block core declaration workflows.

## Future configuration

Environment names are reserved without storing secrets:

```text
MARITIME_AUTHORITY_MODE
MARITIME_AUTHORITY_ENABLED
MARITIME_AUTHORITY_BASE_URL
MARITIME_AUTHORITY_CREDENTIAL_REF

VESSEL_REGISTRY_MODE
VESSEL_REGISTRY_ENABLED
VESSEL_REGISTRY_BASE_URL
VESSEL_REGISTRY_CREDENTIAL_REF
```

`CREDENTIAL_REF` points to a future secret-manager entry; it is not a raw key.

## Activation rule

Adding values alone does not enable sending. A network-capable implementation,
official contract tests, security/privacy review and human release approval are
still required. Until then the adapter factory always returns `ManualAdapter`.

## Claim boundary

This scaffold proves only that the application has a replaceable integration
boundary and manual fallback. It does not prove connectivity, authority
acceptance, provider readiness or CVF governance behavior.
