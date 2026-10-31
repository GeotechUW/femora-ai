# Femora

Use the bundled references as the source of truth. Never invent an API or rely on remembered keyword arguments.

1. Open [the reference index](references/index.md). Load only topics needed for the request.
2. Read the relevant concepts to establish dependencies and build order.
3. Before writing each call, read its exact signature, return value, and accepted arguments in the corresponding API reference. Verify helper-object methods too.
4. Read a matching example when useful, then verify its calls against the API. Example summaries link to full scripts; they are not themselves complete executable scripts.
5. When a signature or important behavior is missing, explain the gap instead of inventing it. API contracts take precedence over examples; report unresolved conflicts.

For new models, start with `references/concepts/index.md`, `references/concepts/building-blocks.md`, and `references/api/model-core.md`. For follow-ups, reuse already read references when current.

For HPC jobs, read the jobs and workflows concepts and the jobs, tasks, and runtime APIs. Load assembly and partitioning topics when changing partitions. Verify cluster-specific settings against current cluster documentation before claiming a configuration works on Stampede3.

For results, begin with the results API and load recorders or runtime as needed. Model construction uses a `Model` instance. Documented non-model jobs, runtime, tasks, and results entry points are allowed exactly as their API specifies.

## Modeling rules

{{RULES}}

## Reference version

These references are a generated snapshot, not a live API lookup. Consult `references/provenance.json` for the exact Femora source commit. Check the user's installed version when compatibility matters. Source links can require network access; if unavailable, state that limitation.
