# AIResearch Cluster Review Packet

Generated: 2026-06-10T07:02:37+00:00
Papers: 202
Facts: 1553
Mode: token
Clusters: 85
Review items: 85
Accept candidates: 37
Needs review: 48

## Review Items

### Backbone Language Vision Action

`method:backbone-language-vision-action` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 3 | Facts: 3 | Average confidence: 0.98
Tokens: backbone, language, vision, action, continuous
Rationale: Accept candidate because it has cross-paper support: 3 facts across 3 papers with average confidence 0.98.

- `lara` LARA: Latent Action Representation Alignment for Vision-Language-Action Models | 2026:  - The VLA policy in LARA uses Eagle-2 as the vision-language backbone and models the diffusion process with a 16-layer Diffusion Transformer (DiT). (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/source.tex
- `openeai-platform` OpenEAI-Platform: An Open-source Embodied Artificial Intelligence Hardware-Software Unified Platform | 2026:  - OpenEAI-VLA uses Qwen3-VL-4B as the backbone vision-language model and employs a diffusion-transformer-based action head for continuous action generation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex
- `3dthinkvla` 3DThinkVLA: Endowing Vision-Language-Action Models with Latent 3D Priors via 3D-Thinking-Guided Co-training | 2026:  - The implementation adopts the StarVLA framework with Qwen3-VL 2B as the vision-language backbone and attaches an OFT-style action head to predict continuous robot control actions. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Action Asynchronous Chunk Current

`method:action-asynchronous-chunk-current` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, asynchronous, chunk, current, inference
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `ct-vam` CT-VAM: A Cerebello-Thalamic-Inspired Vision-Action Model for Efficient Visuomotor Control | 2026:  - CT-VAM employs flow-consistent inpainting for asynchronous chunk execution, enabling next-chunk inference to overlap with current execution while preserving action continuity. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/source.tex
- `kairos` Kairos: A Scalable Serving System for Physical AI | 2026:  - To reduce robot idling between inference rounds, existing physical AI systems use asynchronous inference, which launches the next inference while the robot is still executing the current action chunk. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex

### Action Control Language Steer

`method:action-control-language-steer` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, control, language, steer, time
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_00269` Closed-Loop Neural Activation Control in Vision-Language-Action Models | 2026:  - The paper proposes CTRL-STEER, a closed-loop framework that replaces static intervention strength with adaptive, time-varying control signals for steering Vision-Language-Action (VLA) models. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- `flow-control` Flow Control: Steering Vision-Language-Action Models with Simple Real-Time Inputs | 2026:  - Flow control is a technique to steer vision-language-action (VLA) models in real-time using generic inputs like a keyboard, without requiring retraining or fine-tuning. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex

### Any Fine Pretrained Requiring

`method:any-fine-pretrained-requiring` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: any, fine, pretrained, requiring, tuning
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `c-genreg` C-GenReg: Training-Free 3D Point Cloud Registration by Multi-View-Consistent Geometry-to-Image Generation with Probabilistic Modalities Fusion | 2026:  - The C-GenReg pipeline is fully zero-shot and plug-and-play, relying entirely on pretrained modules without requiring any fine-tuning or additional learning. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- `clasp` CLASP: Language-Driven Robot Skill Selection and Composition using Task-Parameterized Learning | 2026:  - The framework operates without requiring any fine-tuning of the pretrained vision-language model. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex

### Autoencoder Quantized Representation Vae

`method:autoencoder-quantized-representation-vae` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: autoencoder, quantized, representation, vae, vector
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `chexanatomy` CheXanatomy: Anatomy-Aware Vision-Language Modeling for Chest Radiographs | 2026:  - Segmentation masks are encoded into a discrete 16-dimensional latent representation using a vector-quantized variational autoencoder (VQ-VAE) for autoregressive prediction. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- `editssc` EditSSC: Toward Editable Semantic Occupancy Scenes with Unconditional Diffusion Models | 2026:  - The pilot study evaluates a vector-quantized VAE (VQ-VAE) using BEV representation as an alternative to the original SemCity autoencoder. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex

### Beyond Characterize Conventional Failure

`method:beyond-characterize-conventional-failure` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: beyond, characterize, conventional, failure, level
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_08881` Benchmarking Vision-Language-Action Models on SO-101: Failure and Recovery Analysis | 2026:  - The evaluation framework incorporates a structured failure taxonomy, semantic- and execution-level failure decomposition, and recovery-aware evaluation metrics to characterize policy robustness beyond conventional task success rates. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- `fate-vla` FATE-VLA:Failue-aware test generation for vision-language-action models | 2026:  - The approach introduces trajectory-level and object-level failure diversity metrics to characterize the heterogeneity of discovered weaknesses beyond conventional success rates. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex

### Designed Fine Framework Online

`method:designed-fine-framework-online` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: designed, fine, framework, online, policies
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `modip` MODIP: Efficient Model-Based Optimization for Diffusion Policies | 2026:  - MODIP is a framework designed for the offline-to-online fine-tuning of diffusion policies. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - ReinFlow is an online reinforcement learning framework designed to fine-tune flow matching policies for continuous robotic control. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex

### Distillation Level Policy Reverse

`method:distillation-level-policy-reverse` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: distillation, level, policy, reverse, student
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_09091` Stabilizing On-Policy Distillation for MLLM Reasoning with Global Normalization | 2026:  - In the on-policy distillation setup, the token-level reward is defined as the negative reverse KL divergence between the student and teacher model distributions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex
- `2606_09059` Stage-1 Controls the Entropy Regime, Not the Outcome | 2026:  - The on-policy distillation (OPD) method uses a same-modality 72B teacher model to train a 7B student model using reverse-KL, token-level distillation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex

### Flow Matching Objective Trained

`method:flow-matching-objective-trained` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: flow, matching, objective, trained, action
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `mive` MiVE: Multiscale Vision-language features for reference-guided video Editing | 2026:  - The MiVE model is trained using the flow matching objective. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- `torl-vla` TORL-VLA: Tactile Guided Online Reinforcement Learning for Contact-Rich Manipulation | 2026:  - The model's output head jointly predicts the action chunk and the co-predicted future wrench sequence, trained with a joint action-wrench flow matching objective. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex

### Framework Generative Training Vision

`method:framework-generative-training-vision` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: framework, generative, training, vision, world
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `c-genreg` C-GenReg: Training-Free 3D Point Cloud Registration by Multi-View-Consistent Geometry-to-Image Generation with Probabilistic Modalities Fusion | 2026:  - C-GenReg is a training-free framework for 3D point cloud registration that leverages world-scale generative priors and Vision Foundation Models (VFMs). (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- `world2vlm` World2VLM: Distilling World Model Imagination into VLMs for Dynamic Spatial Reasoning | 2026:  - World2VLM is a training framework that distills spatial imagination from a generative world model into a vision-language model. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Language Study Vision Autoregressive

`method:language-study-vision-autoregressive` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: language, study, vision, autoregressive, evaluates
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `mmbu` MMBU: A Massive Multi-modal Biomedical Understanding Benchmark to Probe the Perception Capabilities of Vision-Language Models | 2026:  - The study evaluates 15 open-weight and 2 frontier Vision-Language Models (VLMs). (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex
- `2606_01503` On the Limits of Token Reduction for Efficient Unified Vision Language Training | 2026:  - The study uses the VILA-U (7B) model paradigm as the testbed for the unified autoregressive vision-language model. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Action Expert Flow Matching

`method:action-expert-flow-matching` | Method
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 0.97
Tokens: action, expert, flow, matching, parameter
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 0.97.

- `flow-control` Flow Control: Steering Vision-Language-Action Models with Simple Real-Time Inputs | 2026:  - The π_0.5 VLA generates actions using a flow matching action expert implemented with a downsized 300M-parameter Gemma transformer. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex
- `2606_09009` Scaling by Diversified Experience for Vision-Language-Action Models | 2026:  - The Action Expert in SyVLA is a 0.69B parameter Flow Matching model based on a 15-layer decoder-only transformer with a hidden size of 1408 and 32 attention heads. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex

### Action Actionmap Head Heatmap

`method:action-actionmap-head-heatmap` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, actionmap, head, heatmap, voxel
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `actionmap` ActionMap: Robot Policy Learning via Voxel Action Heatmap | 2026:  - ActionMap is a voxel heatmap action head designed to replace the native action decoder in existing Vision-Language-Action (VLA) models. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- `actionmap` ActionMap: Robot Policy Learning via Voxel Action Heatmap | 2026:  - The ActionMap head predicts a voxel heatmap over the action space for each new action, with each voxel storing the probability of the corresponding action. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md

### Action Actions Distribution Future

`method:action-actions-distribution-future` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, actions, distribution, future, generation
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `world-action-models` World Action Models: The Next Frontier in Embodied AI | 2026:  - Joint World Action Models directly model the joint distribution of future states and actions, co-optimizing state prediction and action generation within a shared representational space. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex
- `world-action-models` World Action Models: The Next Frontier in Embodied AI | 2026:  - World Action Models (WAMs) are defined as embodied foundation models that unify predictive state modeling with action generation to target a joint distribution over future states and actions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/summary.md

### Action Atomic Event Events

`method:action-atomic-event-events` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, atomic, event, events, grounded
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `wall-wm` WALL-WM: Carving World Action Modeling at the Event Joints | 2026:  - WALL-WM shifts video-action learning from chunk-centric optimization to event-grounded Vision-Language-Action pretraining, using semantically coherent action events as the atomic unit of learning. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- `wall-wm` WALL-WM: Carving World Action Modeling at the Event Joints | 2026:  - WALL-WM treats action-grounded semantic events as the atomic training unit, pairing them with event captions to train a video-action denoiser. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/source.tex

### Action Controller Conventions Executable

`method:action-controller-conventions-executable` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, controller, conventions, executable, learned
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_03724` Same Weights, Different Robot: A Deployment Safety View of VLA Policies | 2026:  - An executable VLA policy is formally defined as a tuple comprising the learned model, image and language processor, normalized action representation, metadata-selected unnormalizer, and controller conventions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex
- `2606_03724` Same Weights, Different Robot: A Deployment Safety View of VLA Policies | 2026:  - The authors formalize the deployment-safety gap as an executable policy specification problem, defining a VLA policy to include the learned model, action representation, metadata-selected unnormalizer, and controller-facing conventions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex

### Action Dynamics Embodiment Idm

`method:action-dynamics-embodiment-idm` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, dynamics, embodiment, idm, inverse
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2605_27817` Turning Video Models into Generalist Robot Policies | 2026:  - The paper proposes the Video-to-Embodied Robot Action Model (VERA), a closed-loop policy that decouples an action-free video world model from an embodiment-specific inverse dynamics model (IDM) based on the robot embodiment Jacobian. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/summary.md
- `2605_27817` Turning Video Models into Generalist Robot Policies | 2026:  - The proposed inverse dynamics model, termed Jacobian IDM (J-IDM), translates visual plans into low-level action chunks by inverting the robot embodiment Jacobian. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

### Admissible Fixed Framework Local

`method:admissible-fixed-framework-local` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: admissible, fixed, framework, local, path
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_08953` Self-Consistent Generative Paths via Admissible Random Variational Transport | 2026:  - The framework utilizes a random fixed-point path residual (R-FPR) to measure the gap between the actual generated path and an admissible local correction. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/summary.md
- `2606_08953` Self-Consistent Generative Paths via Admissible Random Variational Transport | 2026:  - The paper introduces Self-Consistent Generative Paths (SCGP), a framework that defines a self-consistent generative path as a random fixed point of admissible local variational transport corrections. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/summary.md

### Agent Atomic Cocosi Commits

`method:agent-atomic-cocosi-commits` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: agent, atomic, cocosi, commits, cross
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `cocosi` CoCoSI: Collaborative Cognitive Map Construction for Spatial Intelligence | 2026:  - CoCoSI introduces atomic commits for controlled map updates and cross-agent verification for reconciling inconsistent object localization and layout estimation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- `cocosi` CoCoSI: Collaborative Cognitive Map Construction for Spatial Intelligence | 2026:  - The CoCoSI framework features local-global agent coordination, cognitive map construction with atomic commits, and cross-agent verification. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex

### Alignment Maskalign Representation Subsets

`method:alignment-maskalign-representation-subsets` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: alignment, maskalign, representation, subsets, token
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `maskalign` MaskAlign: Token-Subset Representation Alignment for Efficient Diffusion Training | 2026:  - MaskAlign is a token-subset representation alignment method that applies alignment to randomly sampled token subsets during training. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/summary.md
- `maskalign` MaskAlign: Token-Subset Representation Alignment for Efficient Diffusion Training | 2026:  - MaskAlign uses a shared random mask to compute representation alignment on token subsets while preserving the class token. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex

### Attention Boosted Ddim Denoising

`method:attention-boosted-ddim-denoising` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: attention, boosted, ddim, denoising, inversion
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `freeanimate` FreeAnimate: Training-Free Human Image Animation with Preview-Guided Denoising | 2026:  - FreeAnimate introduces Inversion-Boosted Attention, which leverages preview-frame attention maps from DDIM inversion to guide the denoising process. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- `freeanimate` FreeAnimate: Training-Free Human Image Animation with Preview-Guided Denoising | 2026:  - Inversion-Boosted Attention (IBA) stores and reuses self-attention and cross-attention maps generated during the DDIM inversion process of preview frames to compute attention during the denoising process. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex

### Brightness Centroid Frequency Fundamental

`method:brightness-centroid-frequency-fundamental` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: brightness, centroid, frequency, fundamental, pitch
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `speakerllm` SpeakerLLM: A Speaker-Specialized Audio-LLM for Speaker Understanding and Verification Reasoning | 2026:  - Acoustic feature extraction derives pitch from the per-utterance mean fundamental frequency using librosa.pyin, and timbral brightness from the per-utterance mean spectral centroid over STFT frames. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- `speakerllm` SpeakerLLM: A Speaker-Specialized Audio-LLM for Speaker Understanding and Verification Reasoning | 2026:  - Pitch attributes are discretized using gender-conditioned fundamental frequency (F0) percentile cutoffs, while timbral brightness uses gender-shared spectral-centroid percentile cutoffs. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex

### Capability Structural Structure Suc

`method:capability-structural-structure-suc` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: capability, structural, structure, suc, understanding
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `tabverse` TABVERSE: Benchmarking Cross-Format Table Understanding in LLMs and VLMs | 2026:  - TABVERSE evaluates LLMs and VLMs across three tasks: Question Answering (QA), Structural Understanding Capability (SUC), and Structure Reconstruction (SR). (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex
- `tabverse` TABVERSE: Benchmarking Cross-Format Table Understanding in LLMs and VLMs | 2026:  - The Structural Understanding Capability (SUC) task probes structure understanding through boundary detection, size estimation, and index-based retrieval. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex

### Chunk Decoding Event Inference

`method:chunk-decoding-event-inference` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: chunk, decoding, event, inference, mode
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `wall-wm` WALL-WM: Carving World Action Modeling at the Event Joints | 2026:  - In the unified inference mode, a VLM with Staircase Decoding supplies event-structured latent reasoning over task progress to guide the next local chunk while maintaining a gradient-continuous VLA path. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/source.tex
- `wall-wm` WALL-WM: Carving World Action Modeling at the Event Joints | 2026:  - WALL-WM supports two complementary inference modes: an event mode that consumes next-event descriptions for variable-length execution chunks, and a unified mode that uses a VLM with Staircase Decoding for fixed-length chunk inference. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md

### Cloud Fitting Orientation Plane

`method:cloud-fitting-orientation-plane` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: cloud, fitting, orientation, plane, point
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `rog-grasp` ROG-Grasp: Root-Oriented Geometry for Robotic Grasping and Placement | 2026:  - ROG-Grasp estimates produce orientation from root surface geometry using RGB-D perception, employing a YOLO-based root detector and point cloud plane fitting to infer the root normal. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex
- `rog-grasp` ROG-Grasp: Root-Oriented Geometry for Robotic Grasping and Placement | 2026:  - The orientation of the root surface is estimated by applying a least-squares plane fitting method to the extracted 3D root point cloud. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex

### Conditioning Diffusion Dps Explicit

`method:conditioning-diffusion-dps-explicit` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: conditioning, diffusion, dps, explicit, guidance
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_05751` Multi-Condition Guided Diffusion Model for Controllable Elastic Parameter Synthesis | 2026:  - For explicit conditioning, a DPS-projection hybrid guidance strategy is developed by introducing an additional projection step into diffusion posterior sampling (DPS) to enhance the enforcement of conditions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex
- `2606_05751` Multi-Condition Guided Diffusion Model for Controllable Elastic Parameter Synthesis | 2026:  - The unified multi-condition guided diffusion framework incorporates implicit and explicit conditioning information using iterative latent variable refinement, Adapter-based conditioning, and a diffusion posterior sampling (DPS)-projection guidance strategy. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex

### Control Cot Reasoning Textual

`method:control-cot-reasoning-textual` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: control, cot, reasoning, textual, tokens
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - The TVI-CoT framework enables the explicit interleaving of textual reasoning and visual feature access using learnable control tokens <THINK>, <LOOK>, and <ANSWER>. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - The control tokens in TVI-CoT allow the model to dynamically switch between textual reasoning and visual grounding, attending to relevant image regions based on the evolving reasoning state. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/source.tex

### Convert Discrete Markov Noise

`method:convert-discrete-markov-noise` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: convert, discrete, markov, noise, process
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - ReinFlow injects learnable noise into a flow policy's deterministic path to convert it into a discrete-time Markov Process for exact likelihood computation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex
- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - ReinFlow utilizes a noise injection network to convert flows into a discrete-time Markov process with Gaussian transition probabilities. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex

### Cross Heterogeneous Image Interleaved

`method:cross-heterogeneous-image-interleaved` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: cross, heterogeneous, image, interleaved, modal
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `omni123` Omni123: Exploring 3D Native Foundation Models with Limited 3D Data by Unifying Text to 2D and 3D Generation | 2026:  - The authors introduce an interleaved X-to-X training paradigm to coordinate cross-modal tasks over heterogeneous paired datasets without needing fully aligned text-image-3D triplets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- `omni123` Omni123: Exploring 3D Native Foundation Models with Limited 3D Data by Unifying Text to 2D and 3D Generation | 2026:  - The training process consists of three stages: cross-modal pre-training over heterogeneous pairs, continued training with learnable view tokens, and Text-Image-3D interleaved fine-tuning. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/source.tex

### Denoising Diffusion Global Skipping

`method:denoising-diffusion-global-skipping` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: denoising, diffusion, global, skipping, strategy
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `less-is-more` Less Is More: Training-Free Acceleration Framework of 3D Diffusion Models for Low-Count PET Denoising via Global-Local Trajectory Reduction | 2026:  - The global denoising step skipping strategy initializes the reverse diffusion process from an intermediate denoising step using a noise-consistent transformation of the low-count input. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex
- `less-is-more` Less Is More: Training-Free Acceleration Framework of 3D Diffusion Models for Low-Count PET Denoising via Global-Local Trajectory Reduction | 2026:  - The paper proposes a training-free Global-Local Skipping Strategy to accelerate diffusion model-based 3D PET denoising. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex

### Diff2Sp Downstream Incorporates Optimization

`method:diff2sp-downstream-incorporates-optimization` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: diff2sp, downstream, incorporates, optimization, stochastic
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `diff2sp` Diff2SP: Diffusion Models for Correlated Scenario Generation in Stochastic Programming | 2026:  - Diff2SP incorporates the downstream stochastic optimization problem into training through a differentiable optimization layer. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- `diff2sp` Diff2SP: Diffusion Models for Correlated Scenario Generation in Stochastic Programming | 2026:  - Diff2SP is a diffusion-based generative framework that incorporates downstream optimization objectives directly into scenario generation for stochastic programming. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex

### Diffusion Guided Modip Mpc

`method:diffusion-guided-modip-mpc` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: diffusion, guided, modip, mpc, planner
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `modip` MODIP: Efficient Model-Based Optimization for Diffusion Policies | 2026:  - MODIP employs a DP-guided MPC planner that uses the diffusion policy as a multi-modal action sequence prior and refines the proposed trajectories through latent MPC. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/source.tex
- `modip` MODIP: Efficient Model-Based Optimization for Diffusion Policies | 2026:  - MODIP fine-tunes the diffusion policy using behavioral cloning on the improved trajectories generated by the DP-guided MPC planner. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/source.tex

### Diffusion Level Low Policy

`method:diffusion-level-low-policy` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: diffusion, level, low, policy, subgoals
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_08775` Unifying Object-Centric World Models and Diffusion Policy: A Hierarchical Framework for Multi-Stage Robotic Tasks | 2026:  - A low-level, goal-conditioned diffusion policy sequentially tracks and executes the subgoals optimized by the object-centric world model. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- `2606_08775` Unifying Object-Centric World Models and Diffusion Policy: A Hierarchical Framework for Multi-Stage Robotic Tasks | 2026:  - The paper introduces WorldDP, a hierarchical framework that uses a high-level world model to optimize feasible subgoals during runtime, which are then executed by a low-level Diffusion Policy. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex

### Fine Fire Generation Grained

`method:fine-fire-generation-grained` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: fine, fire, generation, grained, image
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `fire` FiRe: Fine-grained Multimodal Reasoning for Enhanced Image Generation | 2026:  - FiRe is a fine-grained multimodal reasoning method for text-to-image generation that decomposes prompts into visual requirements, self-judges their satisfaction, and applies localized refinement. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex
- `fire` FiRe: Fine-grained Multimodal Reasoning for Enhanced Image Generation | 2026:  - The FiRe method consists of six reasoning steps: Initial T2I Generation, Prompt Summarization, Tuple Decomposition, Tuple VQA, Fine-grained Feedback Generation, and Localized Image Correction. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex

### Global Guided Learnable Meta

`method:global-guided-learnable-meta` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: global, guided, learnable, meta, token
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `unicompress` UniCompress: Token Compression for Unified Vision-Language Understanding and Generation | 2026:  - UniCompress introduces a plug-in compression and decompression mechanism guided by learnable global meta tokens to reduce visual token count. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- `unicompress` UniCompress: Token Compression for Unified Vision-Language Understanding and Generation | 2026:  - UniCompress uses a compressor to convert a dense token grid into a short sequence of compressed tokens augmented by learnable global meta tokens, and a global-guided decompressor to reconstruct the token grid. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex

### Image Mask Rea2Seg Segmentation

`method:image-mask-rea2seg-segmentation` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: image, mask, rea2seg, segmentation, selection
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `reason-twice` Reason Twice: Segmentation via Candidate Discovery and Comparative Reasoning | 2026:  - Rea2Seg reformulates image segmentation as candidate discovery followed by discriminative mask selection. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md
- `reason-twice` Reason Twice: Segmentation via Candidate Discovery and Comparative Reasoning | 2026:  - The paper proposes a two-stage framework called Rea2Seg for mask generation and selection in reasoning-based image segmentation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

### Architecture Attention Recurrence Transformer

`method:architecture-attention-recurrence-transformer` | Method
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 0.96
Tokens: architecture, attention, recurrence, transformer, convolution
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 0.96.

- `1706_03762` Attention Is All You Need | 2017:  - The Transformer is a network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
- `1706_03762` Attention Is All You Need | 2017: Transformer attention architecture - The Transformer replaces recurrence and convolution with attention-based sequence modeling. (confidence: 0.92)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md

### Evaluated Proposed Dataset Datasets

`dataset:evaluated-proposed-dataset-datasets` | Dataset
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 3 | Facts: 4 | Average confidence: 1.00
Tokens: evaluated, proposed, dataset, datasets, 256x256
Rationale: Accept candidate because it has cross-paper support: 4 facts across 3 papers with average confidence 1.00.

- `2606_06186` Adversarial Attacks Already Tell the Answer: Directional Bias-Guided Test-time Defense for Vision-Language Models | 2026:  - The proposed DBD method is evaluated across 15 datasets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md
- `2407_21243` Informed Correctors for Discrete Diffusion Models | 2024:  - The proposed method is evaluated on the text8 dataset. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- `2407_21243` Informed Correctors for Discrete Diffusion Models | 2024:  - The proposed method is evaluated on the tokenized ImageNet 256x256 dataset. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- `2606_06682` Spatiotemporal Imputation with Graph-Informed Flow Matching | 2026:  - The proposed GiFlow model is evaluated on both synthetic and real-world datasets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex

### Authors Dataset Plan Release

`dataset:authors-dataset-plan-release` | Dataset
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: authors, dataset, plan, release, 000
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `homeworld` HomeWorld: A Unified Floorplan-to-Furnished Framework for Generating Controllable, Densely Interactive Whole-Home Scenes | 2026:  - The authors plan to release their floorplan dataset and 5,000 fully furnished scenes to the public. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md
- `speakerllm` SpeakerLLM: A Speaker-Specialized Audio-LLM for Speaker Understanding and Verification Reasoning | 2026:  - The authors plan to release the metadata-enriched supervision dataset and the target-construction code to ensure reproducibility. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex

### Available Dataset Publicly Code

`dataset:available-dataset-publicly-code` | Dataset
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: available, dataset, publicly, code, face
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `omnivl-guard` OmniVL-Guard: Towards Unified Vision-Language Forgery Detection and Grounding via Balanced RL | 2026:  - The dataset and code for the OmniVL-Guard framework are publicly available on GitHub. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- `world2vlm` World2VLM: Distilling World Model Imagination into VLMs for Dynamic Spatial Reasoning | 2026:  - The World2VLM dataset is publicly available on Hugging Face. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Dataset Evaluates Performance Mauve

`dataset:dataset-evaluates-performance-mauve` | Dataset
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 0.95
Tokens: dataset, evaluates, performance, mauve, openwebtext
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 0.95.

- `mllm-for3d` MLLM-For3D: Adapting Multimodal Large Language Model for 3D Reasoning Segmentation | 2025:  - The pilot study evaluates the performance of 2D reasoning segmentation models on the ScanNet++ dataset. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex
- `2503_00307` Remasking Discrete Diffusion Models with Inference-Time Scaling | 2025:  - The paper evaluates model performance using MAUVE scores on the OpenWebText dataset. (confidence: 0.90)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex

### 000 Assets Over Scenes

`dataset:000-assets-over-scenes` | Dataset
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: 000, assets, over, scenes, simple
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `simple` SIMPLE: Simulation-Based Policy Learning and Evaluation for Humanoid Loco-manipulation | 2026:  - The SIMPLE environment consists of 60 diverse whole-body loco-manipulation tasks, 50 indoor scenes, and over 1,000 object assets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex
- `simple` SIMPLE: Simulation-Based Policy Learning and Evaluation for Humanoid Loco-manipulation | 2026:  - The dataset curated for SIMPLE includes over 1,000 Objaverse assets and 50 HSSD scenes. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex

### Arena Dataset Gr1 Manipulation

`dataset:arena-dataset-gr1-manipulation` | Dataset
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: arena, dataset, gr1, manipulation, nvidia
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `mirabench` MiraBench: Evaluating Action-Conditioned Reliability in Robotic World Models | 2026:  - The NVIDIA Arena-GR1-Manipulation-Task dataset is an open-source benchmark released under the CC-BY-4.0 license, focusing on a microwave door opening task with the Fourier GR-1 humanoid robot. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/source.tex
- `mirabench` MiraBench: Evaluating Action-Conditioned Reliability in Robotic World Models | 2026:  - The study utilizes the NVIDIA Arena-GR1-Manipulation-Task dataset and the PsiBot SynData dataset for training and evaluation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/source.tex

### Attention Collect Dataset Statistics

`dataset:attention-collect-dataset-statistics` | Dataset
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: attention, collect, dataset, statistics, tasks
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_01503` On the Limits of Token Reduction for Efficient Unified Vision Language Training | 2026:  - The JournyDB dataset is used to collect attention statistics for visual generation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- `2606_01503` On the Limits of Token Reduction for Efficient Unified Vision Language Training | 2026:  - The ShareGPT-4v dataset is used to collect attention statistics for visual understanding tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Choice Commonsense Covers Mathematical

`dataset:choice-commonsense-covers-mathematical` | Dataset
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: choice, commonsense, covers, mathematical, rsb
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `robosemanticbench` RoboSemanticBench: Diagnosing Semantic Grounding in Action Prediction for VLA Models | 2026:  - RSB covers controlled arithmetic, grade-school mathematical understanding, and commonsense or factual understanding under four-choice and ten-choice suites. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- `robosemanticbench` RoboSemanticBench: Diagnosing Semantic Grounding in Action Prediction for VLA Models | 2026:  - RSB-General covers non-mathematical semantic understanding, including commonsense QA and MMLU-derived multiple-choice questions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex

### Evaluated Manipulation Benchmarks Real

`benchmark:evaluated-manipulation-benchmarks-real` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 4 | Facts: 4 | Average confidence: 1.00
Tokens: evaluated, manipulation, benchmarks, real, tasks
Rationale: Accept candidate because it has cross-paper support: 4 facts across 4 papers with average confidence 1.00.

- `coarse-to-control` Coarse-to-Control: Action-Token Planning for Vision-Language-Action Models | 2026:  - The proposed method is evaluated on the LIBERO and SimplerEnv-WidowX benchmarks, as well as real-world manipulation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/summary.md
- `2606_01151` Lagrangian Perturbation Diffusion Steering: Latent Reinforcement Learning for Generative Policies | 2026:  - The proposed method is evaluated on RoboMimic manipulation, OpenAI Gym locomotion, and Adroit dexterous manipulation benchmarks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- `occupancy-reward-shaping` Occupancy Reward Shaping: Improving Credit Assignment for Offline Goal-Conditioned Reinforcement Learning | 2026:  - The method is evaluated on 13 long-horizon locomotion and manipulation tasks, as well as 3 real-world Tokamak control tasks for nuclear fusion. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/summary.md
- `vista` VISTA: Vision-Grounded and Physics-Validated Adaptation of UMI data for VLA Training | 2026:  - VISTA is evaluated on UMI-style simulation benchmarks, including RoboTwin-UMI and LIBERO-UMI, as well as 20 diverse real-world manipulation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/source.tex

### Benchmark Evaluated Libero Four

`benchmark:benchmark-evaluated-libero-four` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 4 | Facts: 4 | Average confidence: 0.99
Tokens: benchmark, evaluated, libero, four, suites
Rationale: Accept candidate because it has cross-paper support: 4 facts across 4 papers with average confidence 0.99.

- `actionmap` ActionMap: Robot Policy Learning via Voxel Action Heatmap | 2026:  - ActionMap is evaluated on the LIBERO simulation benchmark, specifically across four suites with 10 tasks per suite. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- `2606_00269` Closed-Loop Neural Activation Control in Vision-Language-Action Models | 2026:  - The method is evaluated on four task suites from the LIBERO benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- `ct-vam` CT-VAM: A Cerebello-Thalamic-Inspired Vision-Action Model for Efficient Visuomotor Control | 2026:  - CT-VAM is evaluated on the LIBERO benchmark for simulation experiments to assess its visuomotor performance. (confidence: 1.00)
- `3dthinkvla` 3DThinkVLA: Endowing Vision-Language-Action Models with Latent 3D Priors via 3D-Thinking-Guided Co-training | 2026:  - The method is evaluated on the LIBERO benchmark, which tests knowledge transfer and policy generalization across four task suites: LIBERO-Spatial, LIBERO-Object, LIBERO-Goal, and LIBERO-Long. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Benchmark Evaluated Framework Proposed

`benchmark:benchmark-evaluated-framework-proposed` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 3 | Facts: 3 | Average confidence: 1.00
Tokens: benchmark, evaluated, framework, proposed, bridgedata
Rationale: Accept candidate because it has cross-paper support: 3 facts across 3 papers with average confidence 1.00.

- `2606_00269` Closed-Loop Neural Activation Control in Vision-Language-Action Models | 2026:  - The method is also evaluated on the BridgeData V2 benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/source.tex
- `colavla` ColaVLA: Leveraging Cognitive Latent Reasoning for Hierarchical Parallel Trajectory Planning in Autonomous Driving | 2025:  - The proposed ColaVLA framework is evaluated on the nuScenes benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- `magis` MAGIS: Evidence-Based Multi-Agent Reasoning for Interpretable Strabismus Clinical Decision-Making | 2026:  - The study evaluates the proposed framework on a fine-grained strabismus benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md

### Benchmark Evaluated Proposed Abc

`benchmark:benchmark-evaluated-proposed-abc` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 3 | Facts: 3 | Average confidence: 1.00
Tokens: benchmark, evaluated, proposed, abc, calvin
Rationale: Accept candidate because it has cross-paper support: 3 facts across 3 papers with average confidence 1.00.

- `pre-vla` Pre-VLA: Preemptive Runtime Verification for Reliable Vision-Language-Action and World-Model Rollouts | 2026:  - The proposed method is evaluated on the LIBERO robotic manipulation benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex
- `stediff` STEDiff: Strengthening Text Embedding for Text-to-Image Alignment in Diffusion Model | 2026:  - STEDiff is evaluated using the T2I-CompBench benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/summary.md
- `2606_01847` The Lie We Tell: Correcting the Euclidean Fallacy in Vision Language Action Policies via Score Matching on Tangent Space | 2026:  - The proposed method is evaluated on the CALVIN ABC->D benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex

### Achieves Benchmark Blue Rate

`benchmark:achieves-benchmark-blue-rate` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 3 | Average confidence: 1.00
Tokens: achieves, benchmark, blue, rate, success
Rationale: Accept candidate because it has cross-paper support: 3 facts across 2 papers with average confidence 1.00.

- `blue` BLUE: Toward Better Language Use in Efficient Vision-Language-Action Models for Autonomous Driving | 2026:  - BLUE achieves a 76.2% success rate on the Bench2Drive benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/summary.md
- `blue` BLUE: Toward Better Language Use in Efficient Vision-Language-Action Models for Autonomous Driving | 2026:  - BLUE achieves a driving score of 36 on the Longest6 v2 benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- `2606_03784` Revisiting Embodied Chain-of-Thought for Generalizable Robot Manipulation | 2026:  - ERVLA achieves state-of-the-art performance on the LIBERO-Plus benchmark with an 86.9% success rate and reaches a 53.2% success rate on VLABench. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md

### Action Benchmark Language Policies

`benchmark:action-benchmark-language-policies` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, benchmark, language, policies, real
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_08881` Benchmarking Vision-Language-Action Models on SO-101: Failure and Recovery Analysis | 2026:  - The paper introduces a standardized real-world benchmark for evaluating Vision-Language-Action (VLA) and imitation learning policies on the low-cost SO-101 robotic platform. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- `phail` PhAIL: A Real-Robot VLA Benchmark and Distributional Methodology | 2026:  - PhAIL (Physical AI Leaderboard) is an open real-robot benchmark on a Franka FR3 that evaluates vision-language-action (VLA) policies using a distributional evaluation methodology. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md

### Action Benchmark Language Vision

`benchmark:action-benchmark-language-vision` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, benchmark, language, vision, vla
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_04046` Dive into the Scene: Breaking the Perceptual Bottleneck in Vision-Language Decision Making via Focus Plan Generation | 2026:  - The LIBERO-plus benchmark is used in the study to evaluate the robustness of Vision-Language-Action (VLA) models against environmental interference. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- `robosemanticbench` RoboSemanticBench: Diagnosing Semantic Grounding in Action Prediction for VLA Models | 2026:  - RoboSemanticBench (RSB) is an embodied benchmark designed to diagnose semantic grounding in action prediction for vision-language-action (VLA) models. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/summary.md

### Authors Benchmark Evaluating Introduce

`benchmark:authors-benchmark-evaluating-introduce` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: authors, benchmark, evaluating, introduce, 696
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_10833` Do VLMs Reason Like Engineers? A Benchmark and a Stage-wise Evaluation | 2026:  - The authors introduce EngVQA, a multimodal benchmark for evaluating engineering reasoning across 5 engineering subjects containing 696 problems. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/summary.md
- `2606_10543` Flexible Flows for Biological Sequence Design | 2026:  - The authors introduce a novel peptide-MHC II benchmark for generating and evaluating MHC-conditioned peptide sequences. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex

### Authors Benchmark Fine Grained

`benchmark:authors-benchmark-fine-grained` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: authors, benchmark, fine, grained, introduce
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `reason-twice` Reason Twice: Segmentation via Candidate Discovery and Comparative Reasoning | 2026:  - The authors introduce a new benchmark called ReasonSeg-SGDR that evaluates a model's perception, grounding, and reasoning abilities across discriminative recognition, spatial reasoning, geometric reasoning, and multi-step reasoning with fine-grained mask generation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md
- `2606_07861` The Last Visible Pixel: Probing Fine-Scale Perception in Vision-Language Models | 2026:  - The authors introduce FineSightBench, a new benchmark that systematically probes the limit of fine-grained visual perception in VLMs by separating perception tasks from reasoning tasks across controlled scales of 4-48px. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

### Behavior Evaluated Manipulation Proposed

`benchmark:behavior-evaluated-manipulation-proposed` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: behavior, evaluated, manipulation, proposed, tasks
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_00985` Make Your VLA More Robust Without More Data By Interleaving Motion Planning | 2026:  - The proposed MPVI approach is evaluated on the BEHAVIOR-1K benchmark, which involves long-horizon mobile manipulation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex
- `2606_04968` Potential-Guided Flow Matching for Vision-Language-Action Policy Improvement | 2026:  - The proposed method is evaluated across five BEHAVIOR-1K simulation tasks and five real-world bimanual manipulation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md

### Benchmark Evaluate Libero Used

`benchmark:benchmark-evaluate-libero-used` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: benchmark, evaluate, libero, used, capabilities
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_07217` Robotic Policy Adaptation via Weight-Space Meta-Learning | 2026:  - The LIBERO benchmark is used to evaluate the performance and generalization capabilities of the WIZARD framework. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md
- `2606_10501` Uncovering Vulnerability of Vision-Language-Action Models under Joint-Level Physical Faults | 2026:  - The LIBERO benchmark is used to evaluate the success rates of VLA models under joint fault conditions. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex

### Benchmarks Evaluated Framework Exdet

`benchmark:benchmarks-evaluated-framework-exdet` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: benchmarks, evaluated, framework, exdet, lvis
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `exdet` ExDet: Open-Domain Open-Vocabulary Detection with Cross-modal Extrapolation and Rectification | 2026:  - The ExDet framework is evaluated on the OD-LVIS, OV-LVIS, Objects365, and MSOSB benchmarks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- `2606_10348` Rethinking Embodied Navigation via Relational Inductive Bias | 2026:  - The proposed DB-Nav framework is evaluated on standard ObjectNav benchmarks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

### Evaluates Libero Pro Proposed

`benchmark:evaluates-libero-pro-proposed` | Benchmark
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: evaluates, libero, pro, proposed, ablations
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_05737` Let It Be Simple: One-Step Action Generation for Vision-Language-Action Models | 2026:  - The paper evaluates the proposed method on the standard LIBERO, LIBERO-Plus, and LIBERO-Pro benchmarks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex
- `2606_02735` See Less, Specify More: Visual Evidence Budgets for Generalizable VLAs | 2026:  - The paper evaluates the proposed method using the LIBERO-PRO benchmark, including object and goal ablations. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

### 2014 Bleu English Task

`benchmark:2014-bleu-english-task` | Benchmark
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: 2014, bleu, english, task, transformer
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `1706_03762` Attention Is All You Need | 2017:  - The Transformer model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over existing best results by over 2 BLEU. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
- `1706_03762` Attention Is All You Need | 2017:  - The Transformer model establishes a single-model state-of-the-art BLEU score of 41.8 on the WMT 2014 English-to-French translation task after training for 3.5 days on eight GPUs. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md

### Bench Conditional Generation Pai

`benchmark:bench-conditional-generation-pai` | Benchmark
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: bench, conditional, generation, pai, physical
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `pai-bench` PAI-Bench: A Comprehensive Benchmark For Physical AI | 2025:  - PAI-Bench is a unified benchmark designed to evaluate perception and prediction capabilities across video generation, conditional video generation, and video understanding for Physical AI. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex
- `pai-bench` PAI-Bench: A Comprehensive Benchmark For Physical AI | 2025:  - PAI-Bench is divided into three tracks: PAI-Bench-G for video generation, PAI-Bench-C for conditional video generation, and PAI-Bench-U for physical video understanding. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex

### Achieves Benchmark Rate Success

`claim:achieves-benchmark-rate-success` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 3 | Average confidence: 1.00
Tokens: achieves, benchmark, rate, success, coarse
Rationale: Accept candidate because it has cross-paper support: 3 facts across 2 papers with average confidence 1.00.

- `coarse-to-control` Coarse-to-Control: Action-Token Planning for Vision-Language-Action Models | 2026:  - Coarse-to-Control achieves a 97.90% average success rate on the LIBERO benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex
- `coarse-to-control` Coarse-to-Control: Action-Token Planning for Vision-Language-Action Models | 2026:  - Coarse-to-Control achieves an 83.3% success rate on the SimplerEnv-WidowX benchmark. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex
- `2606_04046` Dive into the Scene: Breaking the Perceptual Bottleneck in Vision-Language Decision Making via Focus Plan Generation | 2026:  - On the LIBERO-plus benchmark, SceneDiver achieves up to a 9.6% improvement in success rate while adding only a 2.64% computational overhead. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex

### Achieves Art Dna Generation

`claim:achieves-art-dna-generation` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: achieves, art, dna, generation, performance
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `2606_10543` Flexible Flows for Biological Sequence Design | 2026:  - FlexFlow achieves state-of-the-art performance across diverse biological sequence tasks, including density estimation, unconditional and conditional DNA sequence generation, and peptide sequence generation. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex
- `2606_06303` Plug-and-Play Guidance for Discrete Diffusion Models via Gradient-Informed Logit Correction | 2026:  - GILC achieves state-of-the-art performance without additional training across DNA, protein sequence, and molecular generation tasks, frequently outperforming fine-tuning approaches. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex

### Achieves Art Performance State

`claim:achieves-art-performance-state` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: achieves, art, performance, state, academic
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `exdet` ExDet: Open-Domain Open-Vocabulary Detection with Cross-modal Extrapolation and Rectification | 2026:  - ExDet achieves state-of-the-art performance on the OD-LVIS, OV-LVIS, Objects365, and MSOSB datasets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- `mive` MiVE: Multiscale Vision-language features for reference-guided video Editing | 2026:  - MiVE achieves state-of-the-art performance, ranking highest in human preference and outperforming academic and commercial systems. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex

### Action Better Environments Modeling

`claim:action-better-environments-modeling` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, better, environments, modeling, novel
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `c3ache` C$^3$ache: Accelerating World Action Models with Cross Inference Chunk Cache | 2026:  - World Action Models (WAMs) generalize better to novel motions and environments than standard Vision-Language-Action (VLA) policies because they use a video-modeling objective to learn from abundant unlabeled video. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex
- `world-action-models` World Action Models: The Next Frontier in Embodied AI | 2026:  - Integrating world modeling into embodied policies enables stronger physical understanding, better generalization across novel environments, and the use of large-scale human video data lacking action annotations. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

### Action Language Physical Robot

`claim:action-language-physical-robot` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: action, language, physical, robot, vision
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `c3ache` C$^3$ache: Accelerating World Action Models with Cross Inference Chunk Cache | 2026:  - Vision-Language-Action (VLA) models are limited in their physical behaviors because they are bounded by the specific robot demonstrations they were fine-tuned on. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex
- `2606_10501` Uncovering Vulnerability of Vision-Language-Action Models under Joint-Level Physical Faults | 2026:  - Vision-Language-Action (VLA) models exhibit vulnerability to joint-level physical faults when their predicted actions are executed through a perturbed robot body. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex

### Average Compared Improves Libero

`claim:average-compared-improves-libero` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: average, compared, improves, libero, rate
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `phaser` PHASER: Phase-Aware and Semantic Experience Replay for Vision-Language-Action Models | 2026:  - PHASER improves the Average Success Rate by up to 31% compared to matched-budget experience replay and achieves an 87.8% final ASR on the LIBERO-Goal continual learning setting. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/summary.md
- `pre-vla` Pre-VLA: Preemptive Runtime Verification for Reliable Vision-Language-Action and World-Model Rollouts | 2026:  - Pre-VLA improves the average closed-loop success rate across four LIBERO suites from 30.79% to 37.62% compared to RynnVLA-002. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex

### Existing Experimental Generation Methods

`claim:existing-experimental-generation-methods` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 1.00
Tokens: existing, experimental, generation, methods, quality
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 1.00.

- `freeanimate` FreeAnimate: Training-Free Human Image Animation with Preview-Guided Denoising | 2026:  - Experimental results show that FreeAnimate outperforms existing training-free competitors and training-based baseline methods, achieving generation quality comparable to state-of-the-art methods and offering robust generalization across diverse datasets. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- `native3d` Native3D: End-to-End 3D Scene Generation via Unified Mesh-Texture Modeling and Semantic Alignment | 2026:  - Experimental results indicate that Native3D surpasses existing methods in both generation quality and editing flexibility for 3D scenes. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex

### Achieves Art Performance Real

`claim:achieves-art-performance-real` | Claim
Recommended status: `accept_candidate`
Review status: `pending`
Review notes: 
Papers: 2 | Facts: 2 | Average confidence: 0.97
Tokens: achieves, art, performance, real, state
Rationale: Accept candidate because it has cross-paper support: 2 facts across 2 papers with average confidence 0.97.

- `wall-wm` WALL-WM: Carving World Action Modeling at the Event Joints | 2026:  - WALL-WM achieves state-of-the-art performance in large-scale real-world generalization evaluation, demonstrating broad generalization across language, scenes, and tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- `3dthinkvla` 3DThinkVLA: Endowing Vision-Language-Action Models with Latent 3D Priors via 3D-Thinking-Guided Co-training | 2026:  - 3DThinkVLA achieves state-of-the-art performance on LIBERO, LIBERO-PLUS, SimplerEnv, and challenging real-world manipulation tasks. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Achieves Baseline Benchmark Compared

`claim:achieves-baseline-benchmark-compared` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 4 | Average confidence: 1.00
Tokens: achieves, baseline, benchmark, compared, cot
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 4 facts across 1 papers with average confidence 1.00.

- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - TVI-CoT achieves a 3.4% performance improvement on the MathVista benchmark compared to the baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - TVI-CoT achieves a 3.4% performance improvement on the ScienceQA benchmark compared to the baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - TVI-CoT achieves a 3.8% performance improvement on the MathVerse benchmark compared to the baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- `tvi-cot` TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding | 2026:  - TVI-CoT achieves a 6.1% performance improvement on the MMMU benchmark compared to the baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md

### 2048 Context Gpu H100

`claim:2048-context-gpu-h100` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: 2048, context, gpu, h100, length
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2605_30571` Memory-Bound but Not Bandwidth-Limited: The Physical AI Inference Gap in Batch-1 LLM Decode | 2026:  - For the Qwen-2.5-7B model at a context length of 2048, the L4 GPU reaches about 81% of its analytic memory floor, whereas the H100 GPU reaches only 27%. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- `2605_30571` Memory-Bound but Not Bandwidth-Limited: The Physical AI Inference Gap in Batch-1 LLM Decode | 2026:  - Using CUDA Graphs on an H100 GPU at a context length of 2048 improves decode latency by 1.259x, while on an L4 GPU it only improves latency by 1.028x. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md

### Action Higher Noise Prior

`claim:action-higher-noise-prior` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: action, higher, noise, prior, space
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_01151` Lagrangian Perturbation Diffusion Steering: Latent Reinforcement Learning for Generative Policies | 2026:  - LP-DS achieves return improvements of up to 25% over prior baselines while maintaining higher action-space entropy than unconstrained noise-space steering. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- `2606_01151` Lagrangian Perturbation Diffusion Steering: Latent Reinforcement Learning for Generative Policies | 2026:  - LP-DS mitigates mode collapse compared to prior-replacing noise-space steering methods, thereby preserving higher action-space diversity. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex

### Actionmap Baseline Compared Produces

`claim:actionmap-baseline-compared-produces` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: actionmap, baseline, compared, produces, better
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `actionmap` ActionMap: Robot Policy Learning via Voxel Action Heatmap | 2026:  - ActionMap produces better spatial precision at contact and placement compared to the flow-matching baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- `actionmap` ActionMap: Robot Policy Learning via Voxel Action Heatmap | 2026:  - ActionMap produces noticeably smoother end-effector trajectories throughout execution compared to the baseline. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

### Alignment Full Loss Maskalign

`claim:alignment-full-loss-maskalign` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: alignment, full, loss, maskalign, token
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `maskalign` MaskAlign: Token-Subset Representation Alignment for Efficient Diffusion Training | 2026:  - MaskAlign lowers the full-token alignment loss during training. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex
- `maskalign` MaskAlign: Token-Subset Representation Alignment for Efficient Diffusion Training | 2026:  - MaskAlign narrows the alignment-loss gap between randomly masked and full-token inputs, indicating improved stability under token-subset perturbations. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex

### Aura Benchmark Fewer Matches

`claim:aura-benchmark-fewer-matches` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: aura, benchmark, fewer, matches, mem
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `aura` AURA: Action-Gated Memory for Robot Policies at Constant VRAM | 2026:  - On a controlled synthetic benchmark, AURA-Mem matches the best O(1) baseline in accuracy while using 5.19 to 6.13 times fewer memory writes. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md
- `aura` AURA: Action-Gated Memory for Robot Policies at Constant VRAM | 2026:  - On the LIBERO-Long benchmark, AURA-Mem matches the ungated base policy success rate of 0.233 and exceeds the always-write KV arm's 0.217, while using 7.0 times fewer writes. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md

### Average Fine Manipulation Policies

`claim:average-fine-manipulation-policies` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: average, fine, manipulation, policies, reinflow
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - ReinFlow's performance in manipulation tasks is comparable to fine-tuned DDIM policies while saving an average of 23.20% in computation time. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md
- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - Shortcut Model policies fine-tuned with ReinFlow achieved a 40.34% average net increase in success rate in state and visual manipulation tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md

### Base Degradation Largely Reasoning

`claim:base-degradation-largely-reasoning` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: base, degradation, largely, reasoning, robustness
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_08894` Are Reasoning Vision-Language Models Robust to Semantic Visual Distractions? | 2026:  - Reasoning VLMs show consistently lower robustness to semantic distractions compared to perceptual degradation, where they largely track their non-reasoning base models. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex
- `2606_08894` Are Reasoning Vision-Language Models Robust to Semantic Visual Distractions? | 2026:  - Under vision corruptions, reasoning VLMs largely inherit their base models' robustness patterns, whereas semantic distraction produces sharply different degradation behaviors. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex

### Cdt Framework Mbpo Ppo

`claim:cdt-framework-mbpo-ppo` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: cdt, framework, mbpo, ppo, respectively
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2605_16547` World Model-Enabled Causal Digital Twins for Semantic Communications in Physical AI Systems | 2026:  - The WM-CDT framework achieves up to 17.3%, 55.4%, 30.7%, and 33.7% higher return-per-kbit than AC-based recurrent reinforcement learning (AC-RRL), model-based policy optimization (MBPO), AC, and proximal policy optimization (PPO), respectively. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex
- `2605_16547` World Model-Enabled Causal Digital Twins for Semantic Communications in Physical AI Systems | 2026:  - The WM-CDT framework improves the navigation success rate by up to 9.6%, 26.3%, 16.1%, and 18.0% compared to AC-RRL, MBPO, AC, and PPO, respectively. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex

### Deeper Details Early Encode

`claim:deeper-details-early-encode` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: deeper, details, early, encode, layers
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `mive` MiVE: Multiscale Vision-language features for reference-guided video Editing | 2026:  - Early layers of VLMs exhibit higher Attention Mask Ratios, confirming they capture spatial details, while deeper layers have lower ratios, indicating they encode holistic semantics. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- `mive` MiVE: Multiscale Vision-language features for reference-guided video Editing | 2026:  - VLM layers encode complementary information hierarchically, with early layers capturing localized spatial details and deeper layers encoding global semantics. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/summary.md

### Fine Legged Locomotion Reinflow

`claim:fine-legged-locomotion-reinflow` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: fine, legged, locomotion, reinflow, tasks
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - Fine-tuning Rectified Flow policies with ReinFlow in legged locomotion tasks resulted in an average net episode reward growth of 135.36%. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md
- `reinflow` ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning | 2025:  - ReinFlow saves 82.63% of wall time compared to the DPPO diffusion RL fine-tuning method in legged locomotion tasks. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md

### For3D Methods Mllm Reasoning

`claim:for3d-methods-mllm-reasoning` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: for3d, methods, mllm, reasoning, segmentation
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `mllm-for3d` MLLM-For3D: Adapting Multimodal Large Language Model for 3D Reasoning Segmentation | 2025:  - MLLM-For3D achieves approximately 55% higher mIoU compared to previous methods in 3D reasoning segmentation tasks without 3D annotations. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex
- `mllm-for3d` MLLM-For3D: Adapting Multimodal Large Language Model for 3D Reasoning Segmentation | 2025:  - MLLM-For3D outperforms existing 3D reasoning segmentation methods on indoor scene benchmarks without using any labeled 3D training data. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md

### Framework Improves Integrated Proposed

`claim:framework-improves-integrated-proposed` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: framework, improves, integrated, proposed, spiral
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `sarm2` SARM2: Multi-Task Stage Aware Reward Modeling for Self Improving Robotic Manipulation | 2026:  - When integrated into the SPIRAL framework, the proposed method improves task success on the Cleaning Whiteboard task from 50% to 90%. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md
- `sarm2` SARM2: Multi-Task Stage Aware Reward Modeling for Self Improving Robotic Manipulation | 2026:  - When integrated into the SPIRAL framework, the proposed method improves task success on the Folding Shorts task from 58% to 100%. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md

### Image Late Layer Tasks

`claim:image-late-layer-tasks` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: image, late, layer, tasks, tokens
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2606_01503` On the Limits of Token Reduction for Efficient Unified Vision Language Training | 2026:  - In visual understanding tasks, attention to image tokens drops from roughly 30% in the first layer to below 10% in middle and late layers. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- `2606_01503` On the Limits of Token Reduction for Efficient Unified Vision Language Training | 2026:  - There is a fundamental asymmetry in token utilization between visual understanding and generation tasks, where understanding exhibits late-layer visual redundancy and generation maintains persistent dependence on image tokens. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Language Large Mllms Multimodal

`claim:language-large-mllms-multimodal` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: language, large, mllms, multimodal, date
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `2506_18504v2` Generalizing vision-language models to novel domains: A comprehensive survey | 2025:  - Multimodal large language models (MLLMs) enhance the generalizability of vision-language systems by leveraging powerful large language models. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/source.tex
- `2506_18504v2` Generalizing vision-language models to novel domains: A comprehensive survey | 2025:  - The survey discusses the relations and differences between VLMs and up-to-date multimodal large language models (MLLMs), such as DeepSeek-VL. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/summary.md

### Diffusion Latent Performance Reconstruction

`claim:diffusion-latent-performance-reconstruction` | Claim
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 0.95
Tokens: diffusion, latent, performance, reconstruction, space
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 0.95.

- `editssc` EditSSC: Toward Editable Semantic Occupancy Scenes with Unconditional Diffusion Models | 2026:  - High reconstruction fidelity paired with an unstructured latent space, such as that produced by a simple MLP, is detrimental to diffusion performance. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- `editssc` EditSSC: Toward Editable Semantic Occupancy Scenes with Unconditional Diffusion Models | 2026:  - The organization and structure of the latent space are more critical for diffusion quality than autoencoder reconstruction performance alone. (confidence: 0.95)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex

### Evidence Faithfulness Joint Linguistic

`limitation:evidence-faithfulness-joint-linguistic` | Limitation
Recommended status: `needs_review`
Review status: `pending`
Review notes: 
Papers: 1 | Facts: 2 | Average confidence: 1.00
Tokens: evidence, faithfulness, joint, linguistic, multimodal
Rationale: Needs review because support is narrow or confidence is below the accept threshold: 2 facts across 1 papers with average confidence 1.00.

- `look-on-demand` Look on Demand: A Cognitive Scheduling Framework for Visual Evidence Acquisition in Multimodal Reasoning | 2026:  - In unified multimodal models, dominant linguistic priors from joint training objectives can bias visual representations toward the language space, leading to hallucinations and reduced faithfulness to image evidence. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
- `look-on-demand` Look on Demand: A Cognitive Scheduling Framework for Visual Evidence Acquisition in Multimodal Reasoning | 2026:  - The unified multimodal representation paradigm suffers from linguistic dominance caused by joint optimization and attention mechanisms, weakening faithfulness to visual evidence. (confidence: 1.00)
  Evidence source: /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
