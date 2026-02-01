# SECURITY

## Data principles
- Store only metadata required for scan/cleanup
- Never store message bodies
- Sessions are cryptographic material:
  - encrypted at rest
  - decrypted only inside worker at runtime
  - wipe on logout

## Threat model (minimum)
- Session theft -> account takeover risk
- Proxy/IP leakage -> mass bans risk
- Excessive actions -> flood wait / restrictions risk

