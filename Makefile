PYTHON ?= python3
MPLCONFIGDIR ?= /tmp/mpl
CLI = MPLCONFIGDIR=$(MPLCONFIGDIR) PYTHONPATH=src $(PYTHON) -m teleportdim

.PHONY: theory nonmarkovian nonmarkovian-calibration channel-body body-fingerprint aer figures test hardware-prelim hardware-live hardware-process-live three-lane-report

theory:
	$(CLI) markovian-fixed-n-sweep --n-values 2 --delays 0,2048,4096,8192 --t1 540540 --t2 360360 --t-dep 360360 --bootstrap-samples 200 --confidence-level 0.95 --output-stem results/fixed_n2/markovian_n2
	$(CLI) compare-fixed-n --input-json results/fixed_n2/markovian_n2.json --n-physical 2 --output-stem results/fixed_n2/n2_compare

nonmarkovian:
	$(CLI) blp-random-telegraph-scan --dimensions 2,3,4 --n-physical 2 --switching-probabilities 0.005,0.0125,0.025,0.05,0.1,0.2 --coupling-strength 0.4 --steps 16 --samples 2048 --output-stem results/non_markovian/random_telegraph_blp_n2

nonmarkovian-calibration:
	$(CLI) calibrate-random-telegraph --input-json results/hardware/ibm_fez_process_d3_n2_delay0_64_128.json --dimension 3 --n-physical 2 --metric process_fidelity --dt-ns-per-step 4.0 --fit-mode first_nonzero --output-stem results/non_markovian/ibm_fez_rtn_calibration_d3_n2

channel-body:
	$(CLI) channel-body-sweep --n-values 2 --dimensions 2,3,4 --bodies ideal,dephasing,amplitude_damping,leakage_mixing,random_telegraph,coherent_z_drift --strengths 0,0.001,0.005,0.01 --delays 0,64,128 --shots 4096 --samples 1024 --output-stem results/channel_body/n2_body_sweep

body-fingerprint:
	$(CLI) compare-body-fingerprints --input-json results/channel_body/n2_body_sweep.json --hardware-json results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json --metrics process_fidelity,average_gate_fidelity,leakage,in_subspace_fidelity,anisotropy,nonunitality --output-stem results/channel_body/ibm_fez_body_match

hardware-prelim:
	$(CLI) hardware-delay-sweep --dimension 2 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0 --output-stem results/hardware/ibm_fez_d2_n2_delay0
	$(CLI) hardware-delay-sweep --dimension 3 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0 --output-stem results/hardware/ibm_fez_d3_n2_delay0
	$(CLI) hardware-delay-sweep --dimension 4 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0 --output-stem results/hardware/ibm_fez_d4_n2_delay0

hardware-live:
	$(CLI) hardware-fixed-n-sweep --n-values 2 --backend-name ibm_fez --shots 256 --delays 0,64,128 --bootstrap-samples 100 --confidence-level 0.95 --output-stem results/hardware/ibm_fez_fixed_n2_delay0_64_128_live
	$(CLI) compare-fixed-n --input-json results/hardware/ibm_fez_fixed_n2_delay0_64_128_live.json --n-physical 2 --output-stem results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare

hardware-process-live:
	$(CLI) hardware-process-tomography --dimension 2 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0,64,128 --bootstrap-samples 100 --confidence-level 0.95 --output-stem results/hardware/ibm_fez_process_d2_n2_delay0_64_128
	$(CLI) hardware-process-tomography --dimension 3 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0,64,128 --bootstrap-samples 100 --confidence-level 0.95 --output-stem results/hardware/ibm_fez_process_d3_n2_delay0_64_128
	$(CLI) hardware-process-tomography --dimension 4 --n-physical 2 --backend-name ibm_fez --shots 256 --delays 0,64,128 --bootstrap-samples 100 --confidence-level 0.95 --output-stem results/hardware/ibm_fez_process_d4_n2_delay0_64_128
	$(CLI) compare-fixed-n --input-json results/hardware/ibm_fez_process_d2_n2_delay0_64_128.json,results/hardware/ibm_fez_process_d3_n2_delay0_64_128.json,results/hardware/ibm_fez_process_d4_n2_delay0_64_128.json --n-physical 2 --output-stem results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare
	$(CLI) aer-process-tomography --dimension 3 --n-physical 2 --delays 0,64,128 --shots 8192 --correction-mode dynamic --depolarizing-1q 0.001 --depolarizing-2q 0.01 --bootstrap-samples 200 --confidence-level 0.95 --dt-ns-per-dt 4.0 --output-stem results/fixed_n2/aer_process_d3_delay0_64_128_fezdt

three-lane-report:
	$(CLI) compare-three-lanes --theory-json results/fixed_n2/n2_compare.json --aer-json results/fixed_n2/aer_n2_compare.json --hardware-json results/hardware/ibm_fez_fixed_n2_delay0_64_128_compare.json,results/hardware/ibm_fez_process_fixed_n2_delay0_64_128_compare.json --n-physical 2 --output-stem results/fixed_n2/three_lane_n2_compare

aer:
	$(CLI) aer-fixed-n-sweep --n-values 2 --delays 0,2048,4096,8192 --shots 8192 --correction-mode dynamic --depolarizing-1q 0.001 --depolarizing-2q 0.01 --bootstrap-samples 200 --confidence-level 0.95 --output-stem results/fixed_n2/aer_fixed_n2
	$(CLI) aer-process-tomography --dimension 2 --n-physical 2 --delays 0,2048,4096,8192 --shots 8192 --correction-mode dynamic --depolarizing-1q 0.001 --depolarizing-2q 0.01 --bootstrap-samples 200 --confidence-level 0.95 --output-stem results/fixed_n2/aer_process_d2
	$(CLI) aer-process-tomography --dimension 3 --n-physical 2 --delays 0,2048,4096,8192 --shots 8192 --correction-mode dynamic --depolarizing-1q 0.001 --depolarizing-2q 0.01 --bootstrap-samples 200 --confidence-level 0.95 --output-stem results/fixed_n2/aer_process_d3
	$(CLI) aer-process-tomography --dimension 4 --n-physical 2 --delays 0,2048,4096,8192 --shots 8192 --correction-mode dynamic --depolarizing-1q 0.001 --depolarizing-2q 0.01 --bootstrap-samples 200 --confidence-level 0.95 --output-stem results/fixed_n2/aer_process_d4
	$(CLI) compare-fixed-n --input-json results/fixed_n2/aer_fixed_n2.json,results/fixed_n2/aer_process_d2.json,results/fixed_n2/aer_process_d3.json,results/fixed_n2/aer_process_d4.json --n-physical 2 --output-stem results/fixed_n2/aer_n2_compare

figures:
	$(CLI) plot-records --input-json results/fixed_n2/markovian_n2.json --metric fidelity --mode delay --output-path results/fixed_n2/markovian_n2_fidelity.png
	$(CLI) plot-records --input-json results/fixed_n2/markovian_n2.json --metric leakage --mode delay --output-path results/fixed_n2/markovian_n2_leakage.png

test:
	MPLCONFIGDIR=$(MPLCONFIGDIR) PYTHONPATH=src $(PYTHON) -m pytest -q
