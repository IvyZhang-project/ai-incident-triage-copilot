# Payment API Runbook

## Symptom: external provider timeout

If payment authorization latency increases and logs mention provider or downstream timeout:

1. Check external payment gateway status.
2. Confirm whether timeout errors are concentrated in one region.
3. Review retry and circuit breaker behavior.
4. Reduce retry amplification if the provider is degraded.
5. Route traffic to a secondary provider if available.

## Symptom: payment latency without recent deployment

Likely causes:

- External provider degradation
- Network path issue to provider
- Retry storm increasing queue depth
- Provider rate limiting

Recommended mitigation:

- Enable circuit breaker or lower retry count temporarily.
- Notify customer support of payment authorization delays.
- Escalate to the provider if timeout rate remains elevated.
