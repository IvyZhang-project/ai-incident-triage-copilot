# System Boundaries

## Allowed Data Sources

The system may use:

- Synthetic application logs
- Synthetic infrastructure logs
- Synthetic metrics
- Synthetic deployment events
- Synthetic runbooks
- Synthetic incident reports

## Disallowed Data Sources

The system must not use:

- Proprietary AWS logs
- Real customer data
- Internal company documents
- Private production incidents
- Any data copied from a previous employer

## Data Trust Levels

High trust:

- User-provided logs
- User-provided metrics
- Deployment events
- Runbooks owned by the service team

Medium trust:

- Historical synthetic incident reports
- Similar incident summaries

Low trust:

- User guesses
- Broad natural-language descriptions without evidence

## Answer Boundary

The system may:

- Summarize evidence
- Identify likely correlations
- Propose root-cause hypotheses
- Recommend mitigation steps from runbooks
- Ask for missing data

The system must not:

- Claim certainty without evidence
- Invent logs or metrics
- Cite data that was not retrieved
- Pretend synthetic data is real production data

