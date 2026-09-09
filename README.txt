PG-DSL — ACSAC 2026 artifact (paper #151)
Huan Bui and Chenglong Fu, University of North Carolina at Charlotte
https://github.com/huuhuannt1998/pg-dsl

This plain-text file exists because the ACSAC artifact evaluator guide asks
for README.txt, license.txt and use.txt at the top level. The full
documentation is in Markdown beside it:

  ARTIFACT.md   evaluator entry point: what the artifact contains, the
                requirements, three time-boxed evaluation paths, and a
                claim -> script -> result-JSON mapping for every number in
                the paper. START HERE.
  README.md     system documentation: architecture, module layout, and the
                commands that reproduce every paper number.
  LICENSE       MIT.

QUICK START
  ./install.sh --no-model     deps only; enough for claims 3-7 (~2 min)
  ./install.sh                deps + qwen3:14b, 9.3 GB; needed for 1, 2, 8
  ./claims/claim5/run.sh      run one claim, prints PASS/FAIL per field

LAYOUT
  claims/          one folder per reproducible claim: claim.txt, run.sh,
                   expected/. Eight claims, matching metadata.toml.
  infrastructure/  url, resources, allocation — what an evaluator needs to
                   run this on public research infrastructure.
  artifact/        see artifact/README.txt. The code deliberately stays at
                   the repository root; that file explains why and maps the
                   guide's expected layout onto the real one.
  mission_1a/ ..   the artifact proper: plant, MCP server, admission
  mission_3b/      pipeline, baselines, agent harness, campaign scripts.
  rebuttal_experiments/
                   the 19 revision-pass experiments, their pre-registration
                   registers, and every result JSON.
