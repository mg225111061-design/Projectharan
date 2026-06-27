"""
VERIFIED GPU ENGINE (§M) — self-built cuBLAS/cuDNN-class kernels + hidden-structure fold, each PROVED.
=====================================================================================================
Three moves: (1) our OWN dense GEMM/conv kernels lowered HARAN→PTX (public ISA, tensor-core wmma/mma.sync),
depending ONLY on the driver, each TRANSLATION-VALIDATED (exact residual=0 or a proved FP error bound) — the one
thing cuBLAS/cuDNN cannot give; (2) hidden-structure fold ON TOP, z3-proving latent low-rank/circulant/Toeplitz/
Kronecker/recurrence inside matrices that LOOK dense and collapsing to O(N²r) where cuBLAS computes the full cube
blind; (3) soul-deep A/B/C/D optimization to each domain's provable limit. Honest framing: dense = TIE cuBLAS (a
measured fraction) + a proof; structured = WIN on op-count + a proof. We never claim to beat cuBLAS on dense.

Zero library deps — HARAN→PTX→driver only, NO cuBLAS/cuDNN/external BLAS (audit forbidden_present == []). Where no
GPU/ptxas is present, kernels are correctness-validated (spec-equivalence + CPU reference) and throughput is reported
device-pending — the correctness proof NEVER depends on a device. Modules under gpu/ + soul/, never imported by
test_build.
"""
