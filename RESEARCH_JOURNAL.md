# Research Journal

## 2026-03-07

I first asked the wrong question. I was comparing teleportation fidelity across dimensions as if `d` alone were changing, even though moving from `d=2` to `d=3` also changes the physical encoding and the number of places noise can act.

## 2026-03-15

The fixed-`n` comparison fixed the project. Once I treated `d=3` versus `d=4` at `n=2` as the clean experiment, leakage stopped being a side note and became the main observable that made the whole setup worth doing.

## 2026-04-22

The hardware process-tomography result on `ibm_fez` was the one that really forced me to slow down. I expected the full-occupancy `d=4` channel to look cleaner because it has no unused leakage subspace by definition, and instead it came back worse than `d=3`.

## 2026-04-29

I started keeping the hardware run notes in plain language because the saved metrics were not enough on their own. The reruns, suspicious outputs, and missing queue metadata are part of the scientific record here, not embarrassing implementation details to hide.

## 2026-05-05

This repo is the cleanest deformation experiment in the set. FieldLine and SpinMesh made me suspicious of output metrics; TeleportDim is where I tried to build one experiment where the confound I cared about was finally controlled on purpose.
