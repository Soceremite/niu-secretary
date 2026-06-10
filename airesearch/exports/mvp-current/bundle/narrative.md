# AIResearch Narrative Report

Generated: 2026-06-10T07:02:42+00:00
Papers: 202
Facts: 1553

## Executive Summary

- The current corpus contains 202 papers and 1553 extracted research facts.
- Strongly represented fact types: Method, Claim. Moderately represented: Benchmark, Limitation. Under-covered: Dataset.
- Follow-up work should prioritize 188 extraction targets, 118 papers without code links, and 20 missing evidence source paths.

## What Is Well Supported

- Method is represented in 177/202 papers; use it as a backbone for corpus-level reading.
- Claim is represented in 179/202 papers; use it as a backbone for corpus-level reading.

## What Is Provisional

- Benchmark is represented in 105/202 papers; keep paper-level caveats attached.
- Limitation is represented in 129/202 papers; keep paper-level caveats attached.
- Dataset is represented in 97/202 papers; treat broad conclusions as provisional.

## Representative Findings

- Method | `2606_10366` | The evaluation consists of 11,800 simulated rollouts and 1,115 real-world rollouts across policies, tasks, and perturbation dimensions. (confidence: 1.00)
  Evidence: In total, our evaluation includes 11,800 simulated rollouts and 1,115 real-world rollouts. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Method | `2606_10366` | The evaluation introduces controlled perturbations along four complementary dimensions: vision, language, layout, and behavior. (confidence: 1.00)
  Evidence: For each task, we introduce controlled perturbations along four complementary dimensions: \textit{vision}, \textit{language}, \textit{layout}, and \textit{behavior}. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Dataset | `2606_10366` | The authors instantiate the nine-task suite on real hardware using the DROID embodiment to enable direct comparison between simulated and real-world policy behavior. (confidence: 1.00)
  Evidence: We instantiate the same nine-task suite on real hardware using the DROID embodiment~\cite{khazatsky2024droid}, enabling direct comparison between simulated and real-world policy behavior. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Dataset | `actionmap` | ActionMap is evaluated on real-world Franka manipulation tasks, including Block, Cup, and Sweep tasks. (confidence: 1.00)
  Evidence: We evaluate $\pi_{0.5}$ on a separate set of three real-world Franka tasks, distinct from the OpenVLA-OFT tasks of Section~\ref{sec:real_world_franka_setup}: ... \item \textbf{Block} ... \item \textbf{Cup} ... \item \textbf{Sweep} /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- Benchmark | `2606_10366` | The authors construct a unified evaluation platform spanning nine tabletop manipulation tasks to systematically measure simulations for VLA policy evaluation. (confidence: 1.00)
  Evidence: we construct a unified evaluation platform spanning nine tabletop manipulation tasks as shown in Figure \ref{platform}. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Benchmark | `2606_10366` | The study compares three representative simulated VLA benchmarks: VLA-Arena, SIMPLER, and REALM. (confidence: 1.00)
  Evidence: We first compare three representative simulated VLA benchmarks: VLA-Arena, SIMPLER, and REALM across five recent VLA policies /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Claim | `2606_10366` | Post-training with an adequate amount of data strengthens proxy reliability, but excessive fine-tuning may cause the model to overfit to fixed behavior trajectories and obscure true generalization ability. (confidence: 1.00)
  Evidence: post-training with an adequate amount of data could strengthen proxy reliability, whereas excessive fine-tuning may cause the model fit to fixed behavior trajectories, thereby obscuring its true generalization ability under distribution shifts. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Claim | `2606_10366` | Simulator proxies should be visually and physically realistic and reflect how policies fail under different perturbations in the real world. (confidence: 1.00)
  Evidence: Our analysis shows that simulator proxies should be visually and physically realistic, and should reflect how policies fail under different perturbations in the real world. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Limitation | `actionmap` | A dominant remaining error mode for ActionMap across tasks is mistimed gripper actuation rather than positioning error. (confidence: 1.00)
  Evidence: Despite the above gains, the dominant remaining error mode across all three tasks is mistimed gripper actuation rather than positioning error. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- Limitation | `amvicc` | The study was limited to evaluating only 3 image generation models due to access and availability constraints of state-of-the-art models. (confidence: 1.00)
  Evidence: Due to a smaller selection of state-of-the-art image generation models due to access and availability, we were only able to choose 3 models with variance across providers, training data, architecture, and size. /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex

## Priority Follow-Up Actions

- AgenticNav: Zero-Shot Vision-and-Language Navigation as a Tool-Calling Harness | priority 55: Review `agenticnav` for missing fact types: Method, Dataset, Benchmark, Claim, Limitation; repair 0 missing evidence source paths; code links missing.
- Comparative Analysis of Inference-Time Defense Methods for Multimodal Large Language Models | priority 55: Review `2606_10904` for missing fact types: Method, Dataset, Benchmark, Claim, Limitation; repair 0 missing evidence source paths; code links missing.
- DisCo: World Models with Discrete Camera Motion Control | priority 55: Review `disco` for missing fact types: Method, Dataset, Benchmark, Claim, Limitation; repair 0 missing evidence source paths; code links missing.
- FlyMirage: A Fully Automated Generation Pipeline for Diverse and Scalable UAV Flight Data via Generative World Model | priority 55: Review `flymirage` for missing fact types: Method, Dataset, Benchmark, Claim, Limitation; repair 0 missing evidence source paths; code links missing.
- GEM-4D: Geometry-Enhanced Video World Models for Robot Manipulation | priority 55: Review `gem-4d` for missing fact types: Method, Dataset, Benchmark, Claim, Limitation; repair 0 missing evidence source paths; code links missing.

## Evidence Cautions

- 20 facts lack evidence source paths; do not quote them downstream until repaired.
- 118 papers have no extracted code links; implementation availability is incomplete.
- 165 papers are missing at least one required fact type.
