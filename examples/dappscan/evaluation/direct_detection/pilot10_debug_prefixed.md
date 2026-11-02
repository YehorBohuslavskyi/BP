# pilot10_debug_prefixed — debugging evidence only

The original `pilot10/` directory is preserved byte-for-byte. Do not use its
recall as a thesis result or present it as a clean final evaluation.

Two independent validity problems affect this pre-fix run:

1. Only 3 of 10 selected files were analyzed (72 function sessions); 7 failed preparation.
2. SWC/category annotations in original Solidity comments could reach the model
   through synthetic/full-source fragments, including `slitherConstructorVariables()`.

An offline-only interpretation using the corrected coverage semantics gives:

- Selected files: 10; analyzed files: 3; failed preparation: 7.
- Selected ground-truth labels: 21.
- Evaluable labels: 3; UNEVALUABLE labels: 18; coverage: 14.285714285714285%.
- Debug classifications: DETECTED 0, MISSED 3, INCONCLUSIVE 0.
- Additional unlabeled findings: 16 (not adjudicated false positives).
- Historical API calls: 149; historical tokens: 610343.

These counts describe the saved run; they do not repair contaminated inference.
No model calls were made to produce this interpretation. Original results,
prompt journals, preparation files and evaluation reports were not rewritten.
A clean experiment must use newly sanitized preparation in a separate output
directory and explicitly installed compatible compilers/dependencies.
