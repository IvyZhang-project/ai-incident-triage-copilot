# Checkout API Runbook

## Symptom: p95 latency spike after deployment

If p95 latency increases within 10 minutes of a deployment:

1. Check whether error logs include database timeouts.
2. Compare the current deployment with the previous version.
3. Review database connection pool settings.
4. Check active database connections and pool exhaustion metrics.
5. Roll back if timeout rate exceeds 5% for more than 10 minutes.

## Symptom: database connection timeout

Likely causes:

- Connection pool size too small
- Database max connections reached
- Slow queries holding connections too long
- Network path issue between service and database
