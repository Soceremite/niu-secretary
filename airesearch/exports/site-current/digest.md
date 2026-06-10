# AIResearch Digest

Generated: 2026-06-10T07:02:38+00:00
Papers: 202
Facts: 1553

## 3DThinkVLA: Endowing Vision-Language-Action Models with Latent 3D Priors via 3D-Thinking-Guided Co-training

`3dthinkvla` | authors: Jiaxin Shi, Xidong Zhang, Fucai Zhu, Zhe Li, Siyu Zhu, Weihao Yuan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- 3DThinkVLA utilizes a latent 3D geometry perception module to align intermediate visual features with a 3D foundation model, acquiring low-level geometric cues without modifying the VLM backbone architecture. (confidence: 0.95)
  Evidence: To gain geometric priors, a \textbf{latent 3D geometry perception module} aligns intermediate visual features with a 3D foundation model, acquiring low-level geometric cues without requiring architectural modifications to the VLM backbone. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- The framework employs an online 3D reasoning distillation module that uses a shared reasoning anchor token to mitigate the prompt-induced reasoning gap. (confidence: 0.95)
  Evidence: Complementing this perception, an \textbf{online 3D reasoning distillation module} mitigates the prompt-induced reasoning gap via a shared reasoning anchor token. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- A spatially augmented action integration component unites disentangled geometric and reasoning features, injecting them into action-query tokens as hierarchical spatial conditions to prevent action shortcuts. (confidence: 0.95)
  Evidence: These disentangled geometric and reasoning features are then united by a \textbf{spatially augmented action integration}, which jointly injects them into the action-query tokens as hierarchical spatial conditions to prevent action shortcuts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- During deployment, 3DThinkVLA retains only lightweight adapters for implicit 3D reasoning, discarding the 3D foundation model and teacher branch to operate purely on 2D images without 3D sensors or explicit text generation. (confidence: 0.95)
  Evidence: At deployment, our method retains only its lightweight adapters to perform implicit 3D reasoning, discarding the 3D foundation model and the teacher branch used for supervision. Consequently, it operates purely on 2D images without requiring 3D sensors, external foundation models, or explicit text generation [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- The implementation adopts the StarVLA framework with Qwen3-VL 2B as the vision-language backbone and attaches an OFT-style action head to predict continuous robot control actions. (confidence: 0.95)
  Evidence: We adopt the StarVLA~\cite{ye2026starvla} framework with Qwen3-VL 2B~\cite{bai2025qwen3vltechnicalreport} as the vision-language backbone. We attach an OFT-style action head to predict continuous robot control actions [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- The training objective combines VLA loss (L1 distance, weight 1.0) and VLM loss (cross-entropy, weight 0.1), with optional alignment and distillation objectives weighted at 0.5. (confidence: 0.95)
  Evidence: The training objective is a weighted combination of VLA loss and VLM loss, where the VLA loss is implemented as L1 distance and the VLM loss is standard cross-entropy, with weights of $1.0$ and $0.1$, respectively. We optionally include alignment and distillation objectives with weights of $0.5$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Dataset

- The 3D reasoning data for joint training is derived from the Spatial Reasoner dataset, which uses OpenImages and extracts explicit 3D representations using foundation models like SAM2 and Depth Anything V2. (confidence: 0.95)
  Evidence: The 3D reasoning data used for our joint training is derived from the Spatial Reasoner~\cite{ma2025spatialreasonerexplicitgeneralizable3d}. The primary purpose of incorporating this data is to help the model develop stable and accurate explicit 3D perception and spatial reasoning capabilities. This dataset selects unlabeled natural images from the OpenImages dataset [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- To prevent catastrophic forgetting in the pretrained vision-language model, the training mixes 24,000 SR-CoT samples with 24,000 randomly sampled general image-text instruction data from LLaVA. (confidence: 0.95)
  Evidence: In our joint training setup, to prevent catastrophic forgetting in the pretrained general vision-language model, we mix 24,000 carefully selected SR-CoT samples with 24,000 randomly sampled general image-text instruction data from LLaVA during training. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Benchmark

- The method is evaluated on the LIBERO benchmark, which tests knowledge transfer and policy generalization across four task suites: LIBERO-Spatial, LIBERO-Object, LIBERO-Goal, and LIBERO-Long. (confidence: 0.95)
  Evidence: \item\textbf{LIBERO}~\cite{liu2023libero}: This benchmark is designed to evaluate knowledge transfer and policy generalization across four distinct task suites: LIBERO-Spatial, LIBERO-Object, LIBERO-Goal, and LIBERO-Long. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- The method is evaluated on LIBERO-PLUS, a benchmark with 10,030 tasks spanning variations in object layout, camera viewpoints, robot initial states, language instructions, light conditions, background textures, and sensor noise. (confidence: 0.95)
  Evidence: \item \textbf{LIBERO-PLUS}~\cite{fei2025libero}: This benchmark is designed to evaluate the generalization ability of the model with 10,030 tasks spanning the following: (1) Objects Layout [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- The method is evaluated on SimplerEnv, training on SimplerFractal and Simpler-Bridge datasets and testing on Simpler-Bridge for real-to-sim transfer. (confidence: 0.95)
  Evidence: \item \textbf{SimplerEnv}~\cite{li24simpler}: Following previous methods~\cite{ye2026starvla}, we train the model on SimplerFractal (Google Robot) and Simpler-Bridge (WidowX) datasets and test our model on Simpler-Bridge. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Claim

- 3DThinkVLA achieves state-of-the-art performance on LIBERO, LIBERO-PLUS, SimplerEnv, and challenging real-world manipulation tasks. (confidence: 0.95)
  Evidence: achieving state-of-the-art performance on LIBERO, LIBERO-PLUS, SimplerEnv, and challenging real-world manipulation tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex
- Implicit modeling of 3D relationships within the VLM's latent space provides more robust priors for robotic manipulation than injecting raw explicit geometric features. (confidence: 0.95)
  Evidence: Experimental results indicate that injecting explicit 3D geometry is less effective than our implicit reasoning approach. This suggests that the implicit modeling of 3D relationships within the VLM's latent space provides more robust priors for robotic manipulation than raw geometric features. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

### Limitation

- The integrated co-training and self-distillation mechanisms require a 50% increase in computational overhead during training, making it 1.5x slower than a vanilla VLA model of the same size. (confidence: 0.95)
  Evidence: Due to the integrated co-training and self-distillation mechanisms, our method requires a 50\% increase in computational overhead during training. Specifically, When using 8 A100 GPUs with a batch size of $32$, the training time is $1.5\text{x}$ that of a vanilla VLA model of the same size. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/3dthinkvla/source.tex

## A Practical Recipe Towards Improving Sim-and-Real Correlation for VLA Evaluation

`2606_10366` | authors: Shuo Wang, Hanyuan Xu, Yingdong Hu, Fanqi Lin, Yang Gao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The evaluation introduces controlled perturbations along four complementary dimensions: vision, language, layout, and behavior. (confidence: 1.00)
  Evidence: For each task, we introduce controlled perturbations along four complementary dimensions: \textit{vision}, \textit{language}, \textit{layout}, and \textit{behavior}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- The evaluation consists of 11,800 simulated rollouts and 1,115 real-world rollouts across policies, tasks, and perturbation dimensions. (confidence: 1.00)
  Evidence: In total, our evaluation includes 11,800 simulated rollouts and 1,115 real-world rollouts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- The study evaluates five recent VLA policies: pi_0, pi_0-FAST, pi_0.5, GR00T N1.6, and GR00T N1.7. (confidence: 1.00)
  Evidence: five recent VLA policies: $\pi_0$, $\pi_0$-FAST, $\pi_{0.5}$, GR00T N1.6, and GR00T N1.7. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex

### Dataset

- The authors instantiate the nine-task suite on real hardware using the DROID embodiment to enable direct comparison between simulated and real-world policy behavior. (confidence: 1.00)
  Evidence: We instantiate the same nine-task suite on real hardware using the DROID embodiment~\cite{khazatsky2024droid}, enabling direct comparison between simulated and real-world policy behavior. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex

### Benchmark

- The authors construct a unified evaluation platform spanning nine tabletop manipulation tasks to systematically measure simulations for VLA policy evaluation. (confidence: 1.00)
  Evidence: we construct a unified evaluation platform spanning nine tabletop manipulation tasks as shown in Figure \ref{platform}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- The study compares three representative simulated VLA benchmarks: VLA-Arena, SIMPLER, and REALM. (confidence: 1.00)
  Evidence: We first compare three representative simulated VLA benchmarks: VLA-Arena, SIMPLER, and REALM across five recent VLA policies [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex

### Claim

- Post-training with an adequate amount of data strengthens proxy reliability, but excessive fine-tuning may cause the model to overfit to fixed behavior trajectories and obscure true generalization ability. (confidence: 1.00)
  Evidence: post-training with an adequate amount of data could strengthen proxy reliability, whereas excessive fine-tuning may cause the model fit to fixed behavior trajectories, thereby obscuring its true generalization ability under distribution shifts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex
- Simulator proxies should be visually and physically realistic and reflect how policies fail under different perturbations in the real world. (confidence: 1.00)
  Evidence: Our analysis shows that simulator proxies should be visually and physically realistic, and should reflect how policies fail under different perturbations in the real world. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10366/source.tex

## AMVICC: A Novel Benchmark for Cross-Modal Failure Mode Profiling for VLMs and IGMs

`amvicc` | authors: Aahana Basappa, Pranay Goel, Anusri Karra, Anish Karra, Asa Gilmore, Kevin Zhu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/AahanaB24/AMVICC

### Method

- AMVICC was constructed by adapting 300 original MMVP benchmark questions into 600 additional explicit and implicit prompts to evaluate image generation models. (confidence: 1.00)
  Evidence: we used 300 original MMVP benchmark questions, and 600 additional prompts were created [found in Appendix A] to probe specific failure modes. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- The study evaluated 11 multimodal large language models (MLLMs) and 3 image generation models (IGMs) across nine categories of visual reasoning. (confidence: 1.00)
  Evidence: After testing 11 MLLMs and 3 IGMs in nine categories of visual reasoning, our results show that failure modes are often shared between models and modalities [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- Vision language model (VLM) answers were graded by GPT-4o to determine accuracy. (confidence: 1.00)
  Evidence: For VLMs, the benchmark questions were paired with MMVP images, and resulting answers were graded by GPT-4o to determine model accuracy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- Images generated by image generation models were evaluated by human evaluators and double-checked to ensure correct grading and check for bias. (confidence: 1.00)
  Evidence: Each image is scored by human evaluators and double-checked for accuracy in order to check for bias and ensure correct grading for each image. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex

### Benchmark

- The authors introduce AMVICC (Assessment of Modality-Specific Visual Intelligence Comprehension and Creation), a novel benchmark designed to profile and compare failure modes across image-to-text and text-to-image tasks. (confidence: 1.00)
  Evidence: In this paper, we introduce a novel benchmark, \textbf{Assessment} of \textbf{Modality-Specific} \textbf{Visual} \textbf{Intelligence} \textbf{Comprehension} and \textbf{Creation} (AMVICC), to evaluate the failure modes of image generation models and MLLMs with the same contextual input [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- The AMVICC benchmark evaluates models across nine categories of visual reasoning. (confidence: 1.00)
  Evidence: Accuracy scores depict the model’s accuracy across the 9 categories of visual reasoning questions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex

### Claim

- The evaluation revealed that while failure modes are often shared between models and modalities, certain failures are specific to particular models or modalities. (confidence: 1.00)
  Evidence: our results show that failure modes are often shared between models and modalities, but certain failures are model-specific and modality-specific, and this can potentially be attributed to various factors. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- Image generation models consistently struggled to manipulate specific visual components in response to explicit prompts, indicating poor control over fine-grained visual attributes. (confidence: 1.00)
  Evidence: IGMs consistently struggled to manipulate specific visual components in response to prompts, especially in explicit prompts, suggesting poor control over fine-grained visual attributes. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex
- Most MLLMs fail in similar contexts, particularly in Positional and Relational Context and Quantity and Count, but model-specific failure modes also occurred, such as Grok 4 failing on Color and Appearance. (confidence: 1.00)
  Evidence: Furthermore, most MLLMs fail in similar contexts, particularly in Positional and Relational Context and Quantity and Count. Additional common failure modes include Viewpoint and Perspective as well as Orientation and Direction. However, model-specific failure modes occurred as well, with only Grok 4 failing on Color and Appearance [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex

### Limitation

- The study was limited to evaluating only 3 image generation models due to access and availability constraints of state-of-the-art models. (confidence: 1.00)
  Evidence: Due to a smaller selection of state-of-the-art image generation models due to access and availability, we were only able to choose 3 models with variance across providers, training data, architecture, and size. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/amvicc/source.tex

## AURA: Action-Gated Memory for Robot Policies at Constant VRAM

`aura` | authors: Josef Chen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- AURA-Mem wraps a frozen vision-language-action backbone with a constant-size recurrent memory and a learned gate that writes only when the current observation would change the next action. (confidence: 1.00)
  Evidence: It wraps a frozen vision-language-action backbone with a constant-size recurrent memory and a learned gate that writes only when the current observation would change the next action [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md
- The AURA-Mem gate is trained using an action-information-bottleneck (action-IB) objective that back-propagates the closed-loop action-chunk loss through the gate decision. (confidence: 1.00)
  Evidence: an action-information-bottleneck (action-IB) training objective that back-propagates the closed-loop action-chunk loss through the gate decision, directly aligning write selection with decision quality [artifact:source_tex]
- AURA-Mem features a training-time write-rate control parameter that allows placing the model anywhere on the write-bandwidth and accuracy frontier. (confidence: 1.00)
  Evidence: a training-time write-rate control ($\rho$, the target write rate, with $\gamma$ its penalty weight) that places the model anywhere on the write-bandwidth/accuracy frontier by selecting a target at train time [artifact:source_tex]

### Benchmark

- AURA-Mem was evaluated on the LIBERO-Long benchmark using a trained closed-loop OpenVLA-OFT 7B panel with 60 episodes per arm. (confidence: 1.00)
  Evidence: On a trained closed-loop OpenVLA-OFT 7B panel on LIBERO-Long (n=60 episodes per arm) [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md

### Claim

- AURA-Mem's inference state is fixed at 4,224 bytes regardless of the horizon length. (confidence: 1.00)
  Evidence: Its inference state is fixed at 4,224 bytes regardless of horizon, while a KV-cache grows to 6,061 times larger at 100,000 steps. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md
- On a controlled synthetic benchmark, AURA-Mem matches the best O(1) baseline in accuracy while using 5.19 to 6.13 times fewer memory writes. (confidence: 1.00)
  Evidence: On a controlled synthetic benchmark, AURA-Mem matches the best O(1) baseline in accuracy while using 5.19-6.13 times fewer writes, and up to 9.19 times fewer writes on easier configurations. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md
- On the LIBERO-Long benchmark, AURA-Mem matches the ungated base policy success rate of 0.233 and exceeds the always-write KV arm's 0.217, while using 7.0 times fewer writes. (confidence: 1.00)
  Evidence: AURA-Mem matches the ungated base policy (0.233) and slightly exceeds an always-write KV arm (0.217), while using 7.0 times fewer writes and constant memory. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/summary.md

### Limitation

- The instantiated approximate-information-state (AIS) value-loss bound is vacuous at the current scale and does not serve as a formal guarantee. (confidence: 1.00)
  Evidence: at this scale the bound is vacuous, not a guarantee. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/aura/source.tex

## ActionMap: Robot Policy Learning via Voxel Action Heatmap

`actionmap` | authors: Pei Yang, Hai Ci, Yanzhe Chen, Qi Lv, Han Cai, Mike Zheng Shou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/showlab/ActionMap

### Method

- ActionMap is a voxel heatmap action head designed to replace the native action decoder in existing Vision-Language-Action (VLA) models. (confidence: 1.00)
  Evidence: we introduce ActionMap, a voxel heatmap action head that drops into an existing VLA in place of its native action decoder. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- The ActionMap head predicts a voxel heatmap over the action space for each new action, with each voxel storing the probability of the corresponding action. (confidence: 1.00)
  Evidence: For each new action, the head predicts a voxel heatmap over the action space, where each voxel directly stores the probability of the corresponding action. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- ActionMap is integrated into OpenVLA-OFT by replacing its L1 regression head while keeping the rest of the backbone, including bidirectional attention and parallel-decoding. (confidence: 1.00)
  Evidence: We integrate our voxel heatmap action head into OpenVLA-OFT by replacing its L1 regression head while preserving the rest of the backbone, including the bidirectional attention over action-token positions and the parallel-decoding output of T actions per forward pass. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- In pi_0.5 experiments, the ActionMap heatmap head replaces the flow-matching action expert while preserving the rest of the backbone. (confidence: 1.00)
  Evidence: Our heatmap head replaces \pi_{0.5}'s flow-matching action expert while preserving the rest of the backbone. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- The ActionMap heatmap head uses a 64x64x64 translation grid and a 48x48x48 rotation grid with a Gaussian-blob sigma of 0.15. (confidence: 1.00)
  Evidence: Our heatmap head uses a $64 \times 64 \times 64$ translation grid and a $48 \times 48 \times 48$ rotation grid with Gaussian-blob $\sigma = 0.15$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- ActionMap decodes actions via top-k soft-argmax with k=10 during inference. (confidence: 1.00)
  Evidence: and decodes by top-$k$ soft-argmax with $k = 10$ at inference [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

### Dataset

- ActionMap is evaluated on real-world Franka manipulation tasks, including Block, Cup, and Sweep tasks. (confidence: 1.00)
  Evidence: We evaluate $\pi_{0.5}$ on a separate set of three real-world Franka tasks, distinct from the OpenVLA-OFT tasks of Section~\ref{sec:real_world_franka_setup}: ... \item \textbf{Block} ... \item \textbf{Cup} ... \item \textbf{Sweep} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

### Benchmark

- ActionMap is evaluated on the LIBERO simulation benchmark, specifically across four suites with 10 tasks per suite. (confidence: 1.00)
  Evidence: We evaluate $\pi_{0.5}$ on the four LIBERO suites following the protocol of Section~\ref{sec:libero_experiments}: LIBERO seed 7, 10 tasks per suite, 50 trials per task, for 500 episodes per suite. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

### Claim

- ActionMap surpasses OpenVLA-OFT's L1 regression head by 8.2% on the LIBERO four-suite average at matched training steps. (confidence: 1.00)
  Evidence: our heatmap head surpasses two architecturally distinct backbones at matched training steps (e.g., +8.2% over OpenVLA-OFT's L1 regression head on the LIBERO four-suite average) [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- ActionMap is markedly more data-efficient at low training data compared to baseline action decoders. (confidence: 1.00)
  Evidence: and remains markedly more data-efficient at low training data. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- ActionMap converges at comparable or faster rates on both OpenVLA-OFT and pi_0.5 backbones. (confidence: 1.00)
  Evidence: converges at comparable or faster rates on both backbones [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/summary.md
- In the 50% partial-data setting for real-world Franka tasks, the ActionMap heatmap head outperforms the flow-matching baseline with a pooled success rate of 34/45 compared to 29/45. (confidence: 1.00)
  Evidence: Our heatmap head wins on every task at the partial-data setting (pooled 34/45 vs.\ 29/45 for the flow-matching baseline, +5 trials). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- ActionMap produces better spatial precision at contact and placement compared to the flow-matching baseline. (confidence: 1.00)
  Evidence: The most consistent behavioral difference between our voxel heatmap head and the flow-matching baseline is spatial precision at contact and placement. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex
- ActionMap produces noticeably smoother end-effector trajectories throughout execution compared to the baseline. (confidence: 1.00)
  Evidence: Our method produces noticeably smoother end-effector trajectories throughout execution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

### Limitation

- A dominant remaining error mode for ActionMap across tasks is mistimed gripper actuation rather than positioning error. (confidence: 1.00)
  Evidence: Despite the above gains, the dominant remaining error mode across all three tasks is mistimed gripper actuation rather than positioning error. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/actionmap/source.tex

## Adversarial Attacks Already Tell the Answer: Directional Bias-Guided Test-time Defense for Vision-Language Models

`2606_06186` | authors: Liangsheng Liu, Si Chen, Jiamin Wu, Weiwei Feng, Zhixin Cheng, Xiaotian Yin, Wenfei Yang, Tianzhu Zhang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/goodfeli/dlbook_notation, https://github.com/liuls2002/DBD

### Method

- The paper proposes Directional Bias-guided Defense (DBD), a test-time framework that estimates the Defense Direction and uses a DB-score-based two-stream reconstruction strategy to recover robust representations for Vision-Language Models. (confidence: 1.00)
  Evidence: we propose Directional Bias-guided Defense (DBD), a test-time framework that estimates the Defense Direction and employs a DB-score-based two-stream reconstruction strategy to recover robust representations. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md
- The Directional Bias (DB) score is introduced to measure the directional concentration of transformed features, which exhibits a bimodal distribution to distinguish adversarial from clean images. (confidence: 1.00)
  Evidence: we further introduce a Directional Bias (DB) score to measure the directional concentration of transformed features. As shown in Fig. 1(b), the DB-score exhibits a clear bimodal distribution, effectively distinguishing adversarial from clean ones [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/source.tex
- The dominant shift direction of adversarial features is termed the Defense Direction, which is hypothesized to oppose the adversarial shift and point features back toward their correct class centers. (confidence: 1.00)
  Evidence: We hypothesize that this dominant shift, termed the Defense Direction, opposes the adversarial shift, pointing features back toward their correct class centers. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md

### Dataset

- The proposed DBD method is evaluated across 15 datasets. (confidence: 1.00)
  Evidence: Experiments on 15 datasets demonstrate that DBD not only achieves SOTA adversarial robustness [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md

### Claim

- Under diverse input transformations, adversarial images in CLIP's feature space consistently shift along a dominant direction, whereas clean images exhibit dispersed patterns. (confidence: 1.00)
  Evidence: under diverse input transformations, adversarial images in CLIP's feature space consistently shift along a dominant direction, in contrast to the dispersed patterns of clean images. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md
- The DBD framework achieves state-of-the-art adversarial robustness while preserving clean accuracy, and can even result in adversarial accuracy surpassing clean accuracy. (confidence: 1.00)
  Evidence: Experiments on 15 datasets demonstrate that DBD not only achieves SOTA adversarial robustness while preserving clean accuracy, but also reveals the counterintuitive result that adversarial accuracy can even surpass clean accuracy. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md
- Adversarial perturbations inherently encode directional priors about the true decision boundary, which can be leveraged for effective defense. (confidence: 1.00)
  Evidence: This demonstrates that adversarial perturbations inherently encode directional priors about the true decision boundary. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06186/summary.md

## AgenticNav: Zero-Shot Vision-and-Language Navigation as a Tool-Calling Harness

`agenticnav` | authors: Yijian Li, Changze Li, Hantian Shi, Jiaying Luo, Jiyuan Cai, Ming Yang, Tong Qin | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## An Effective Router for Vision-Language Model Selection

`2606_08970` | authors: Can Wang, Shengwei Wang, Bolin Zhang, Zhiying Tu, Dianhui Chu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/withmartian/routerbench

### Method

- The authors propose ARMS, a router for VLM selection that enhances input signals with VLM profiles and employs an architecture to improve representations of queries and VLM capabilities. (confidence: 1.00)
  Evidence: We then propose ARMS, a router for VLM selection. ARMS enhances input signals with VLM profiles, employs a simple but effective architecture to improve representations of queries and VLM capabilities. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/summary.md
- To improve the adaptation of the ARMS router to new VLMs, the authors propose two extension training strategies: incremental training and independent training. (confidence: 1.00)
  Evidence: To improve ARMS’ adaptation to new VLMs, we propose two extension training strategies: incremental training and independent training. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/source.tex

### Dataset

- The authors construct a multimodal dataset for VLM selection containing the outputs of seven mainstream VLMs on 32,626 unique image-text queries. (confidence: 1.00)
  Evidence: In this paper, we construct a multimodal dataset for VLM selection, containing the outputs of seven mainstream VLMs on 32,626 unique image-text queries. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/summary.md

### Claim

- The authors conducted an empirical study and found that the performance paradox, where larger models do not always outperform smaller ones, also exists among Vision-language models. (confidence: 1.00)
  Evidence: Building on this insight, we conduct an empirical study on the VHELM benchmark \cite{VHELM} and find that the performance paradox also exists among Vision-language models (VLMs). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/source.tex
- Using the proposed training strategy, the 800M parameter ARMS model can adapt to a broader VLM space and outperform commercial models like GPT-4o that are hundreds of times larger. (confidence: 1.00)
  Evidence: In particular, using our training strategy, ARMs (only 800M in size) can adapt to a broader VLM space and defeat commercial models like GPT-4o that are hundreds of times larger in scale. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/summary.md

### Limitation

- Existing router methods fail to adapt to the VLM selection problem due to a lack of specialized multimodal datasets, ineffective feature representations relying on general-purpose embeddings, and rigid model spaces that make adaptation to new VLMs costly. (confidence: 1.00)
  Evidence: However, these works fail to adapt to the VLM selection problem, which primarily faces three major obstacles: 
1) Lack of specialized data: existing router research lacks a large-scale multimodal dataset to to train VLM router and fairly assess its performance. 
2) Ineffective feature representation: existing routers typically rely on general-purpose semantic embeddings, which are not specifically designed for VLM selection. As a result, they may fail to fully utilize multimodal inputs and model-related information when making selection decisions, leading to suboptimal performance.
3) Rigid model space and costly adaptation: existing routers are trained over a fixed set of VLMs and learn model-specific decision boundaries, which restricts the selection space to seen models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08970/source.tex

## Are Reasoning Vision-Language Models Robust to Semantic Visual Distractions?

`2606_08894` | authors: Yizheng Sun, Mochuan Zhan, Yanan Ma, Jia Tong See, Yifan Wang, Ziyi Wang, Hao Li, Yang Cui, Wenhao Cai, Jingyu Sun, Chenghua Lin, Riza Batista-Navarro, Jingyuan Sun | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Yizheng-Sun/Distract-Bench

### Method

- Seed distractors for Distract-Bench are designed by human annotators to fulfill four criteria: containing obvious semantic information, being factually correct and visually plausible, being irrelevant to the query, and optionally leading to dead ends or plausible wrong answers. (confidence: 1.00)
  Evidence: The distractor is required to fulfil four criteria: (1) Contain obvious semantic information; (2) Factually correct and visually plausible. (3) Be irrelevant to the query and therefore not affect the correct answer; (4) Optionally lead to dead ends or plausible wrong answers. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex

### Dataset

- The construction of Distract-Bench follows a four-stage pipeline consisting of raw sample collection, expert-designed seed distractors, scalable synthetic editing, and human quality verification. (confidence: 1.00)
  Evidence: Its construction follows a four-stage pipeline: (i) raw sample collection, (ii) expert-designed seed distractors, (iii) scalable synthetic editing, and (iv) human quality verification. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex
- Distract-Bench collects 800 raw image-question samples from reasoning-heavy benchmarks including MathVision, MathVista, and the general-domain benchmark MMMU. (confidence: 1.00)
  Evidence: Since distraction robustness primarily concerns failures in the reasoning process, we focus on reasoning-heavy benchmarks, including MathVision and MathVista, and further include samples from the general-domain benchmark MMMU to improve coverage and diversity~\citep{wang2024measuring, lu2024mathvista, yue2024mmmu}. In total, we collect 800 raw samples, each consisting of an image and its corresponding textual query. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex

### Benchmark

- The authors introduce Distract-Bench, a benchmark for evaluating VLM robustness to semantic visual distractions, which are meaningful but task-irrelevant visual cues added to inputs while preserving the ground-truth answer. (confidence: 1.00)
  Evidence: To address this gap, we introduce \textbf{Distract-Bench}, a benchmark for evaluating VLM robustness to \textbf{semantic visual distractions}, defined as meaningful but task-irrelevant visual cues added to inputs while preserving the ground-truth answer. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex

### Claim

- Reasoning VLMs show consistently lower robustness to semantic distractions compared to perceptual degradation, where they largely track their non-reasoning base models. (confidence: 1.00)
  Evidence: Our results show that Distract-Bench exposes a robustness failure distinct from vision corruptions: reasoning VLMs largely track their non-reasoning base models under perceptual degradation, but show consistently lower robustness to semantic distractions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex
- Semantic distractions often enter the reasoning process of VLMs, are treated as evidence, and lead to incorrect answers. (confidence: 1.00)
  Evidence: Further analysis shows that these distractions often enter the reasoning process of VLMs, are treated as evidence, and lead to incorrect answers. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex
- Under vision corruptions, reasoning VLMs largely inherit their base models' robustness patterns, whereas semantic distraction produces sharply different degradation behaviors. (confidence: 1.00)
  Evidence: Under vision corruptions, reasoning VLMs largely inherit their base models' robustness patterns, whereas Distract-Bench produces sharply different degradation behaviors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08894/source.tex

## AudioProcessBench: Benchmark for Identifying Process Errors in Audio-Grounded Reasoning

`audioprocessbench` | authors: Xiangyu Zhao, Junyu Yan, Yaling Shen, Zimu Wang, Yiwen Jiang, Stephanie Fong, Qingyang Xu, Jiahe Liu, Dominic Dwyer, Zongyuan Ge | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The benchmark evaluates models using three paradigms: step correctness identification, error-type-conditioned detection, and chain-level aggregation. (confidence: 1.00)
  Evidence: Our benchmark evaluates models under three complementary paradigms: (1) step correctness identification, (2) error-type-conditioned detection for diagnosing audio-specific verifier capacities, and (3) chain-level aggregation, where verifiers select or aggregate among multiple reasoning traces for the same question. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/summary.md
- The benchmark includes an annotation scheme with six fine-grained audio-specific error types: existence, semantic, temporal, acoustic-attribute, cross-modal binding, and reasoning errors. (confidence: 1.00)
  Evidence: We develop an audio-specific process annotation scheme with step-level correctness labels and six fine-grained error types: existence, semantic, temporal, acoustic-attribute, cross-modal binding, and reasoning errors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex

### Dataset

- AudioProcessBench contains 3,872 reasoning traces and 23,497 annotated steps generated by 6 audio and omni language models. (confidence: 1.00)
  Evidence: We introduce \textsc{AudioProcessBench}, the first benchmark designed for step-level process verification in audio-grounded reasoning, containing 3,872 reasoning traces and 23,497 annotated steps from 6 audio and omni generators. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex
- AudioProcessBench is constructed using data from three audio reasoning benchmarks: MMAR, MMSU, and MMAU-Pro. (confidence: 1.00)
  Evidence: We construct \textsc{AudioProcessBench} from three challenging audio reasoning benchmarks: MMAR \cite{ma2026mmar}, MMSU \citep{dingdong2026mmsu}, and MMAU-Pro \citep{kumar2026mmau}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex
- The reasoning chains in the benchmark are generated by six models: Qwen2.5-Omni-7B, Gemma-3n-E4B, Phi-4-Multimodal, Gemma-4-E4B, Qwen3-Omni-30B-A3B, and Step-Audio-R1. (confidence: 1.00)
  Evidence: The generator set includes both instruction-following and reasoning-oriented models: Qwen2.5-Omni-7B \citep{xu2025qwen2}, Gemma-3n-E4B \citep{google_deepmind_gemma3n_2025}, Phi-4-Multimodal \citep{abdin2024phi}, Gemma-4-E4B \citep{google_deepmind_gemma4_2026}, Qwen3-Omni-30B-A3B \citep{xu2025qwen3}, and Step-Audio-R1 \citep{tian2025step}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex

### Benchmark

- AudioProcessBench is a comprehensive benchmark designed for step-level process error identification in audio-grounded reasoning. (confidence: 1.00)
  Evidence: In this paper, we present AudioProcessBench, a comprehensive benchmark for step-level process error identification in audio reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/summary.md

### Claim

- Experiments show that while newer and reasoning-oriented models perform better as critics, there is still a significant performance gap between open-source models and closed-source frontier models. (confidence: 1.00)
  Evidence: The results show that newer and reasoning-oriented models achieve stronger critic performance, but a substantial gap remains between open-source models and the closed-source frontier model. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex
- The study finds that a model's ability to critique reasoning is not fully predicted by its generation accuracy, and models exhibit bias when evaluating their own reasoning traces. (confidence: 1.00)
  Evidence: We also find that critic ability is not fully predicted by generation accuracy, and that models may be biased when judging their own reasoning traces. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/audioprocessbench/source.tex

## AutoMoT: A Unified Vision-Language-Action Model with Asynchronous Mixture-of-Transformers for End-to-End Autonomous Driving

`automot` | authors: Wenhui Huang, Songyan Zhang, Qihang Huang, Zhidong Wang, Zhiqi Mao, Collister Chua, Zhan Chen, Long Chen, Chen Lv | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- AutoMoT is an end-to-end autonomous driving framework that unifies reasoning and action generation within a single vision-language-action (VLA) model using a mixture-of-transformer (MoT) architecture with joint attention sharing. (confidence: 1.00)
  Evidence: we propose AutoMoT in this work, an end-to-end AD framework that unifies reasoning and action generation within a single vision-language-action (VLA) model. Our approach leverages a mixture-of-transformer (MoT) architecture with joint attention sharing [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/summary.md
- AutoMoT enables efficient fast-slow inference through asynchronous execution of tasks at different frequencies. (confidence: 1.00)
  Evidence: enabling efficient fast-slow inference through asynchronous execution at different task frequencies. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/summary.md
- AutoMoT includes a VLA-oriented action refiner that enhances driving performance via diffusion-based fine-tuning. (confidence: 1.00)
  Evidence: Additionally, we explore a VLA-oriented action refiner that further enhances driving performance via diffusion-based fine-tuning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/source.tex
- The understanding expert in AutoMoT uses the Qwen3-VL-4B dense model as its vision-language backbone. (confidence: 1.00)
  Evidence: The UE adopts Qwen3-VL-4B dense model as its vision--language backbone [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/source.tex
- The understanding expert in AutoMoT is kept frozen during the entire training process to preserve general knowledge and avoid catastrophic degradation. (confidence: 1.00)
  Evidence: To fully leverage the general knowledge of the pretrained Qwen3-VL model and avoid catastrophic degradation of reasoning performance, we freeze the understanding expert throughout the entire training process. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/source.tex

### Claim

- Pre-trained VLMs can achieve competitive multi-task scene understanding performance through semantic prompting alone without fine-tuning. (confidence: 1.00)
  Evidence: pre-trained VLMs can achieve competitive multi-task scene understanding performance through semantic prompting alone [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/summary.md
- Fine-tuning remains essential for action-level tasks such as decision-making and trajectory planning in autonomous driving. (confidence: 1.00)
  Evidence: while fine-tuning remains essential for action-level tasks such as decision-making and trajectory planning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/summary.md

### Limitation

- Existing VLM integration strategies in autonomous driving struggle with distribution misalignment between reasoning and action spaces, underexploit general reasoning capabilities, or incur substantial inference latency. (confidence: 1.00)
  Evidence: existing integration strategies suffer from several limitations: they either struggle to resolve distribution misalignment between reasoning and action spaces, underexploit the general reasoning capabilities of pretrained VLMs, or incur substantial inference latency during action policy generation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/summary.md
- Tightly coupling action policy execution with high-level reasoning at a synchronized temporal frequency causes substantial inference latency, making it impractical for real-world autonomous driving. (confidence: 1.00)
  Evidence: tightly coupling action policy execution with high-level reasoning at a synchronized temporal frequency is impractical for real-world autonomous driving. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/automot/source.tex

## BLUE: Toward Better Language Use in Efficient Vision-Language-Action Models for Autonomous Driving

`blue` | authors: George Ling, Lijin Yang, Hao Yang, Zhongzhan Huang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/George-Ling3/BLUE

### Method

- BLUE trains a lightweight gate on frozen VLA hidden states to decide per frame whether to activate language generation or predict actions directly, without modifying the backbone. (confidence: 1.00)
  Evidence: BLUE trains a lightweight gate on frozen VLA hidden states to decide per frame whether to activate language generation or predict actions directly, without modifying the backbone or requiring additional human annotation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- The gate in BLUE is designed as a single-hidden-layer MLP trained with binary cross-entropy loss. (confidence: 1.00)
  Evidence: The gate is a single-hidden-layer MLP with negligible parameter count, trained with binary cross-entropy loss. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- BLUE uses SimLingo as the base VLA driving model for its experiments. (confidence: 1.00)
  Evidence: We study SimLingo \cite{renz2025simlingo}, a VLA driving model that generates natural language reasoning before predicting actions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- To address temporal redundancy, BLUE groups consecutive frames with cosine similarity above 0.99 and downsamples them. (confidence: 1.00)
  Evidence: To address temporal redundancy (e.g., near-identical features when the vehicle is stopped), we group consecutive frames with cosine similarity above 0.99 into redundant segments and downsample each segment [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex

### Benchmark

- BLUE achieves a 76.2% success rate on the Bench2Drive benchmark. (confidence: 1.00)
  Evidence: achieving 76.2% success rate on Bench2Drive [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/summary.md
- BLUE achieves a driving score of 36 on the Longest6 v2 benchmark. (confidence: 1.00)
  Evidence: and 36 driving score on Longest6 v2 [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex

### Claim

- In closed-loop analysis, generated language statistically improves driving on only 14.5% of routes, actively degrades it on 23.6%, and has no clear effect on the majority. (confidence: 1.00)
  Evidence: the generated language statistically improves driving on only 14.5% of routes, actively degrades it on 23.6%, and has no clear effect on the remaining majority. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- Pretrained VLA hidden states already encode a signal indicating whether language generation will benefit a given frame, which scene complexity and kinematic features alone struggle to predict. (confidence: 1.00)
  Evidence: We further show that pretrained VLA hidden states potentially already encode whether language will benefit a given frame, even though scene complexity and kinematic features alone struggle to predict this. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/source.tex
- BLUE delivers a 2.54x inference speedup and an 8.9% success rate improvement over the VLA backbone. (confidence: 1.00)
  Evidence: while delivering 2.54x inference speedup and 8.9% success rate improvement over the backbone. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/blue/summary.md

## BehaviorVLM: Unified Finetuning-Free Behavioral Understanding with Vision-Language Reasoning

`behaviorvlm` | authors: Jingyang Ke, Weihan Li, Amartya Pradhan, Jeffrey Markowitz, Anqi Wu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- BehaviorVLM is a unified vision-language framework for pose estimation and behavioral understanding that requires no task-specific finetuning and minimal human labeling. (confidence: 1.00)
  Evidence: We present BehaviorVLM, a unified vision-language framework for pose estimation and behavioral understanding that requires no task-specific finetuning and minimal human labeling by guiding pretrained Vision-Language Models (VLMs) through detailed, explicit, and verifiable reasoning steps. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/summary.md
- The pose estimation pipeline leverages quantum-dot-grounded behavioral data and integrates temporal, spatial, and cross-view reasoning. (confidence: 1.00)
  Evidence: For pose estimation, we leverage quantum-dot-grounded behavioral data and propose a multi-stage pipeline that integrates temporal, spatial, and cross-view reasoning. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex
- The behavioral understanding pipeline integrates deep embedded clustering for over-segmented behavior discovery, VLM-based per-clip video captioning, and LLM-based reasoning to merge and semantically label behavioral segments. (confidence: 1.00)
  Evidence: For behavioral understanding, we propose a pipeline that integrates deep embedded clustering for over-segmented behavior discovery, VLM-based per-clip video captioning, and LLM-based reasoning to merge and semantically label behavioral segments. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex
- In the first stage of pose estimation, the 12 body keypoints are partitioned into four anatomical regions (ears, back, paws, tail), and a VLM predicts the bounding box of each region. (confidence: 1.00)
  Evidence: The 12 body keypoints are partitioned into four anatomical regions: \textit{ears} (\texttt{ear\_L}, \texttt{ear\_R}), \textit{back} (\texttt{back\_top}, \texttt{back\_middle}, \texttt{back\_bottom}), \textit{paws} (\texttt{forepaw\_L}, \texttt{forepaw\_R}, \texttt{hindpaw\_L}, \texttt{hindpaw\_R}), and \textit{tail} (\texttt{tail\_base}, \texttt{tail\_middle}, \texttt{tail\_tip}). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex
- The final stage of pose estimation applies a RANSAC-based triangulation and cross-view consistency correction to refine potentially erroneous centroid assignments across the camera views. (confidence: 1.00)
  Evidence: Given the per-camera 2D keypoint predictions across all six views, we apply a RANSAC-based triangulation \citep{fischler1981random} and cross-view consistency correction to refine potentially erroneous centroid assignments. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex
- The pose estimation pipeline requires only three manually labeled seed frames to begin generating labels automatically. (confidence: 1.00)
  Evidence: The pipeline requires only three manually labeled seed frames. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex

### Dataset

- The pose estimation experimental data consists of 500 synchronized timepoints from six cameras recording a freely moving mouse injected with near-infrared fluorescent nanoparticles at 12 anatomical keypoints. (confidence: 1.00)
  Evidence: We use a dataset of 500 synchronized timepoints from six cameras recording a freely moving mouse.
The mouse was injected with near-infrared fluorescent nanoparticles (quantum dots, QDs) at 12 anatomical keypoints [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex

### Benchmark

- BehaviorVLM is evaluated on a custom six-view quantum-dot mouse dataset and the MABe2022 Mouse Triplets benchmark. (confidence: 1.00)
  Evidence: Evaluation on a custom six-view quantum-dot mouse dataset~\citep{QD} and the MABe2022 Mouse Triplets benchmark~\citep{sun2023mabe22} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex

### Claim

- The behavioral understanding pipeline can operate directly from visual information and does not require keypoints to segment behavior. (confidence: 1.00)
  Evidence: The behavioral pipeline can operate directly from visual information and does not require keypoints to segment behavior. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex

### Limitation

- Unsupervised behavioral understanding approaches like MotionMapper, MoSeq, and Keypoint-MoSeq often produce segments that are difficult to interpret, switch too rapidly, or do not align cleanly with human-understandable behavioral categories. (confidence: 1.00)
  Evidence: unsupervised approaches such as MotionMapper \citep{berman2014mapping}, MoSeq \citep{wiltschko2015mapping}, and Keypoint-MoSeq~\citep{weinreb2024keypoint} scale well, but they often produce segments that are difficult to interpret, switch too rapidly, or do not align cleanly with human-understandable behavioral categories. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/behaviorvlm/source.tex

## Benchmarking Vision-Language-Action Models on SO-101: Failure and Recovery Analysis

`2606_08881` | authors: Yi Yu, Xinchuan Qiu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The evaluation framework incorporates a structured failure taxonomy, semantic- and execution-level failure decomposition, and recovery-aware evaluation metrics to characterize policy robustness beyond conventional task success rates. (confidence: 1.00)
  Evidence: Beyond conventional task success rates, the benchmark incorporates a structured failure taxonomy, semantic- and execution-level failure decomposition, and recovery-aware evaluation metrics to characterize policy robustness. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- The study fine-tunes and evaluates pi_0.5, SmolVLA, Wall-X, and ACT using real-world teleoperated demonstrations directly on the physical SO-101 platform. (confidence: 1.00)
  Evidence: Using real-world teleoperated demonstrations, we fine-tune and evaluate $\pi_{0.5}$, SmolVLA, Wall-X, and ACT directly on the physical platform. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex

### Dataset

- The study uses real-world teleoperated demonstrations collected on the SO-101 platform for task-specific fine-tuning of the evaluated policies. (confidence: 1.00)
  Evidence: Teleoperated demonstrations collected on the platform are used for task-specific fine-tuning, and all policies are subsequently evaluated under identical deployment conditions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex

### Benchmark

- The paper introduces a standardized real-world benchmark for evaluating Vision-Language-Action (VLA) and imitation learning policies on the low-cost SO-101 robotic platform. (confidence: 1.00)
  Evidence: We present a standardized real-world benchmark for evaluating representative VLA and imitation learning policies on the low-cost SO-101 robotic platform. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- The SO-101 benchmark comprises four representative manipulation tasks designed to evaluate execution properties such as control fidelity, grounding robustness, temporal consistency, and robustness under embodiment noise. (confidence: 1.00)
  Evidence: the benchmark consists of four representative manipulation tasks spanning distinct execution dimensions, including control fidelity, grounding robustness, temporal consistency, and robustness under embodiment noise. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- The SO-101 robotic platform introduces stochasticity into the perception-action loop through actuator noise, joint backlash, control latency, trajectory jitter, limited positional repeatability, and imperfect calibration. (confidence: 1.00)
  Evidence: The platform introduces stochasticity into the perception-action loop through actuator noise, joint backlash, control latency, trajectory jitter, limited positional repeatability, and imperfect calibration between visual observations and executed actions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex

### Claim

- Stronger pretrained VLA policies generally outperform the imitation learning baseline under low-cost robotic deployment conditions, although performance remains highly task-dependent. (confidence: 1.00)
  Evidence: Experimental results show that stronger pretrained VLA policies generally outperform the imitation learning baseline, although performance remains highly task-dependent under low-cost robotic deployment conditions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex
- Execution instability emerges as the dominant source of failure across all evaluated methods on the low-cost robotic platform, while recovery capability varies substantially across architectures. (confidence: 1.00)
  Evidence: Execution instability emerges as the dominant failure source, while recovery capability varies substantially across architectures. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex

### Limitation

- Organizing benchmark tasks according to increasing semantic complexity has a limitation where successful task completion does not necessarily indicate that the intended semantic capability has been acquired, as tasks may be solved through learned visuomotor correlations. (confidence: 1.00)
  Evidence: preliminary experiments revealed a potential limitation of this formulation: successful task completion does not necessarily indicate that the intended semantic capability has been acquired. For example, tasks involving object attributes or spatial relations may sometimes be solved through learned visuomotor correlations that are sufficient for successful execution under specific environmental conditions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08881/source.tex

## Beyond Consistency: Preserving Temporal Structure in Zero-Shot Video Editing

`beyond-consistency` | authors: Deyin Liu, Yisheng Ding, Zhe Jin, Xiatian Zhu, Anjan Dutta, Lin Wu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed method adaptively partitions the source video into semantically distinct clips based on feature similarity and selects a representative anchor frame for each clip to preserve temporal structure. (confidence: 1.00)
  Evidence: We achieve this by adaptively partitioning the video into semantically distinct clips based on feature similarity and selecting a representative anchor frame for each clip. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex
- The method employs a clip-adaptive token merging strategy that leverages the anchor frame's semantic dominance to stabilize editing and enhance intra-clip fidelity and computational efficiency. (confidence: 1.00)
  Evidence: To enhance both intra-clip fidelity and computational efficiency, we design a clip-adaptive token merging strategy which leverages the anchor's semantic dominance to stabilize the editing. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex
- An alternating combination strategy is used to perform joint self-attention of merged tokens from adjacent clips at later diffusion timesteps to ensure seamless inter-clip transitions. (confidence: 1.00)
  Evidence: Furthermore, we employ an alternating combination strategy that ensures seamless inter-clip transitions while maintaining semantic distinction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex
- The core image generation component is Stable Diffusion version 1.5, utilizing a DDIM scheduler with 50 sampling steps, and integrating Plug and Play (PnP) and ControlNet for spatial control. (confidence: 1.00)
  Evidence: Specifically, we select Stable Diffusion (SD) version 1.5 as the core image generation component and use DDIM scheduler for sampling and inversion, with the sampling steps set as T=50... Our approach integrates two different image control techniques including Plug and Play (PnP) and ControlNet architecture [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex
- DIFT features are extracted from each frame of the source video at t=0 from the intermediate layer of the 2D U-Net Decoder to measure inter-frame similarity. (confidence: 1.00)
  Evidence: For extracting DIFT from each frame of the source video, we select the features corresponding to t=0 , which are extracted from the intermediate layer of the 2D U-Net Decoder. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex

### Dataset

- The method is evaluated using videos from the LongV-EVAL dataset, which contains 75 videos of approximately 1 minute in length with a frame rate of 20-30 fps. (confidence: 1.00)
  Evidence: The LongV-EVAL dataset contains 75 videos, each approximately 1 minute long, with a frame rate of 20-30 fps. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex
- The MiraData dataset is also used for evaluation, featuring long videos with an average duration of 72 seconds and structured subtitles. (confidence: 1.00)
  Evidence: The MiraData features long videos with an average duration of 72 seconds and structured subtitles of 6 types, averaging 318 words. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex

### Benchmark

- The evaluation metrics include Peak Signal-to-Noise Ratio (PSNR) for pixel-wise fidelity, Interpolation Error for motion interpolation discrepancies, Warp Error for optical flow-based frame warping, and Structural Similarity Index (SSIM). (confidence: 1.00)
  Evidence: The Peak Signal-to-Noise Ratio (PSNR) quantifies pixel-wise fidelity by comparing edited frames against ground-truth sequences. Interpolation Error is employed to measure discrepancies in motion interpolation between consecutive frames. Additionally, Warp Error measures the optical flow-based frame warping, ensuring consistent motion dynamics across the video timeline. The Structural Similarity Index (SSIM) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex

### Claim

- The proposed method achieves state-of-the-art results in zero-shot video editing, successfully balancing the preservation of the original temporal structure with computational efficiency. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that our method achieves state-of-the-art results, successfully balancing the preservation of original temporal structure with computational efficiency, and setting a new benchmark for zero-shot video editing fidelity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex

### Limitation

- The current work is limited by its empirical-based adaptive clip partitioning and the lack of multi-level structure preservation. (confidence: 1.00)
  Evidence: However, we acknowledge the limitations of our current work, such as the empirical-based adaptive clip partitioning and lack of multi-level structure preservation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-consistency/source.tex

## Beyond Task Success: Behavioral and Representational Diagnostics for WAM and VLA

`beyond-task-success` | authors: Hung Mai, Bin Zhu, Tuan Do | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces a model-agnostic diagnostic framework that compares World-Action Models (WAMs) and Vision-Language-Action (VLA) policies using behavioral rollout analysis and sparse-autoencoder-based feature analysis. (confidence: 1.00)
  Evidence: We introduce a model-agnostic diagnostic framework that compares WAMs and VLAs through two complementary lenses: behavioral rollout analysis and sparse-autoencoder-based feature analysis. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex
- The behavioral protocol evaluates action dynamics consistency, target-object progress, distractor disturbance, and runtime cost. (confidence: 1.00)
  Evidence: The behavioral protocol measures action dynamics consistency, target-object progress, distractor disturbance, and runtime cost. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex
- The feature-space protocol uses sparse autoencoders to characterize internal representations as memorized, reactive, or predictive to determine if models encode future-oriented structure. (confidence: 1.00)
  Evidence: The feature-space protocol characterizes internal representations as memorized, reactive, or predictive, revealing whether models encode future-oriented structure. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex
- The authors categorize World-Action Models into three families: joint/parallel WAMs, sequential WAMs, and auxiliary/training-only WAMs. (confidence: 1.00)
  Evidence: we organize WAM-style methods into joint or parallel WAMs, which predict future observations and actions together... sequential WAMs, which imagine future visual states before inferring actions... and auxiliary or training-only WAMs, which use future prediction or alignment during training but remove explicit future rollout at inference [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex

### Benchmark

- The evaluation of the 7 policies spanning direct VLAs and various WAM architectures is conducted across the LIBERO and RoboTwin2.0 benchmarks. (confidence: 1.00)
  Evidence: Across LIBERO and RoboTwin2.0, we evaluate 7 policies spanning direct VLAs and joint, sequential, and auxiliary WAMs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex

### Claim

- Relying solely on task success rates obscures key differences between models, as WAMs often improve object-level behavior and target selectivity depending on their architecture. (confidence: 1.00)
  Evidence: Our results show that success alone hides key differences: WAMs often improve object-level behavior and target selectivity, but their gains depend on architecture and incur higher inference cost. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex
- Sequential WAMs exhibit the clearest predictive structure, whereas auxiliary WAMs compress future information and joint WAMs entangle it. (confidence: 1.00)
  Evidence: Sequential WAMs show the clearest predictive structure, while auxiliary and joint WAMs respectively compress or entangle future information. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex

### Limitation

- Explicit future modeling in WAMs introduces significant deployment and inference costs, particularly when relying on inference-time imagination. (confidence: 1.00)
  Evidence: At the same time, explicit future modeling introduces a non-trivial deployment cost, especially for inference-time imagination. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/beyond-task-success/source.tex

## Blockchain Infrastructure for Intelligent Cyber--Physical--Social Systems:Post-Quantum Security, Interoperability, and Trustworthy Data Economies in the Era of Embodied AI

`2606_06895` | authors: Song Guo, Huawei Huang, Dongping Liu, Aoyu Zhang, Luyao Zhang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/QuantBlockchain/ieee-icbc-tutorial-qbe

### Method

- The tutorial includes an AWS Braket demonstration using superconducting, trapped-ion, and neutral-atom hardware to assess cryptographic threat timelines and observe ECDSA-to-post-quantum signature transitions. (confidence: 0.95)
  Evidence: The session opens with an immersive AWS Braket demonstration engaging participants with superconducting, trapped-ion, and neutral-atom hardware to assess cryptographic threat timelines and witness ECDSA-to-post-quantum signature transitions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/summary.md
- Empirical threat assessment for post-quantum security is conducted via Amazon Braket by measuring coherence times, gate fidelities, and error rates. (confidence: 0.95)
  Evidence: Post-Quantum Security: Empirical threat assessment via Amazon Braket (coherence times, gate fidelities, error rates) and crypto-agility mechanisms enabling hybrid migration and long-lived verification [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/source.tex
- BrokerChain cross-shard protocols and bridge security are proposed for heterogeneous cross-ledger communication required for CPSS-scale deployment. (confidence: 0.95)
  Evidence: Interoperability: BrokerChain cross-shard protocols and bridge security for heterogeneous cross-ledger communication required for CPSS-scale deployment [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/source.tex
- The tutorial covers scalable cross-shard architectures utilizing BrokerChain protocols. (confidence: 0.90)
  Evidence: Five integrated modules progress from embodied AI and world-model requirements through quantum hardware reality and evidence-based security migration, to scalable cross-shard architectures via BrokerChain protocols [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/summary.md
- The tutorial addresses trustworthy data economies by implementing Croissant metadata standards and robotic learning provenance. (confidence: 0.90)
  Evidence: trustworthy data economies implementing Croissant metadata standards and robotic learning provenance [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/summary.md

### Dataset

- LET and Kuavo are utilized as robotic datasets for demonstrating blockchain provenance. (confidence: 0.95)
  Evidence: Croissant metadata standards, blockchain provenance for robotic datasets (LET, Kuavo), and incentive-compatible mechanisms ensuring high-quality data sharing with open standards and reproducibility [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/source.tex

### Claim

- The deployment of embodied AI via world-model-based robotics creates an urgent demand for trustworthy data provenance, cross-organizational governance, and incentive-compatible sharing in decentralized ecosystems. (confidence: 0.95)
  Evidence: The deployment of embodied artificial intelligence via world-model-based robotics presents a transformative opportunity for blockchain infrastructure, establishing urgent demand for trustworthy data provenance, cross-organizational governance, and incentive-compatible sharing across decentralized ecosystems. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/summary.md
- Advances in quantum computing threaten the cryptographic primitives securing data economies, necessitating crypto-agile architectures capable of withstanding quantum adversaries for long-lived verification. (confidence: 0.95)
  Evidence: Simultaneously, quantum computing advances recognized by the 2025 Nobel Prize in Physics and the Turing Award threaten the cryptographic primitives securing these data economies, creating an interdependent imperative: long-lived verification for embodied AI depends on crypto-agile architectures capable of withstanding quantum adversaries. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/summary.md
- Blockchain infrastructure must evolve to connect cyber services, physical devices, and social governance by providing post-quantum security, interoperability, and trustworthy data economies. (confidence: 0.95)
  Evidence: Blockchain must therefore evolve as the trust and coordination layer connecting cyber services, physical devices, and social governance, simultaneously providing: (1) Post-Quantum Security via crypto-agility and hybrid migration; (2) Interoperability for cross-ledger coordination; and (3) Trustworthy Data Economies enabling open datasets with rights management, interoperability, and reproducibility. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/source.tex

### Limitation

- Open challenges in the field include governance for cryptographic transitions, standards-aware interoperability, and incentive alignment to sustain long-term collaboration in Intelligent CPSS. (confidence: 0.95)
  Evidence: Open challenges include governance for cryptographic transitions, standards-aware interoperability, and incentive alignment, sustaining long-term collaboration in Intelligent CPSS. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06895/source.tex

## Boosting Omni-Modal Language Models: Staged Post-Training with Visually Debiased Evaluation

`2605_12034` | authors: Che Liu, Lichao Ma, Xiangyu Tony Zhang, Yuxin Zhang, Haoyang Zhang, Xuerui Yang, Fei Tian | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- OmniBoost is a three-stage post-training recipe for omni-modal models that consists of mixed bi-modal supervised fine-tuning (SFT), mixed-modality reinforcement learning with verifiable rewards (RLVR), and SFT on self-distilled data. (confidence: 1.00)
  Evidence: we study OmniBoost, a three-stage post-training recipe based on Qwen2.5-Omni-3B: mixed bi-modal SFT, mixed-modality RLVR, and SFT on self-distilled data. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex
- To identify visual leakage in omni-modal benchmarks, the authors employ a visual-only probing method that withholds audio input and tests whether a model can correctly answer the query using only the visual input and text question. (confidence: 1.00)
  Evidence: For each evaluation query, we keep the image or video together with the text question, withhold the audio input, and test whether a strong model can still recover the correct verifiable answer. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex
- Synthetic omni-modal queries for self-distillation are generated using an entity-based procedure that extracts spatial and temporal relations from various seed clips and captions, converts them into hard-matchable questions, and filters model-generated reasoning traces without using a stronger external omni-modal teacher. (confidence: 1.00)
  Evidence: an entity-based procedure derives spatial and temporal relations from LLaVA-Video seed clips, Step-Audio-R1 audio captions, Qwen3-VL video captions, and gpt-oss-120b entity scaffolds, then converts them into hard-matchable audio-visual-text questions before filtering model-generated reasoning traces. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex

### Dataset

- OmniClean is a visually debiased evaluation dataset constructed by auditing 16,968 queries from nine omni-modal benchmarks using visual-only probing, resulting in 8,551 retained queries where visual evidence alone is insufficient. (confidence: 1.00)
  Evidence: This protocol audits 16,968 queries and yields OmniClean, a visually debiased evaluation view with 8,551 retained queries. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex

### Benchmark

- The authors audit nine recent audio-visual-language benchmarks to construct OmniClean, including Daily-Omni, WorldSense, OmniBench, IntentBench, AV-Odyssey, Video-Holmes, UNO-Bench, CG-AV-Counting, and OmniVideoBench. (confidence: 0.90)
  Evidence: Recent audio-visual-language benchmarks aim to measure whether a model can jointly understand audio-visual events and answer language queries grounded in omni-modal evidence, as in Daily-Omni, WorldSense, OmniBench, IntentBench, AV-Odyssey, Video-Holmes, UNO-Bench, CG-AV-Counting, and OmniVideoBench. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex

### Claim

- In the OmniBoost study, balanced bi-modal SFT yields limited and uneven improvements, while mixed-modality RLVR provides the first broad improvement, and self-distillation further reshapes the benchmark performance profile. (confidence: 1.00)
  Evidence: The staged results show that balanced bi-modal SFT alone yields limited and uneven gains, whereas RLVR provides the first broad improvement and self-distillation further reshapes the benchmark profile. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex
- After undergoing SFT on self-distilled data, the 3B parameter model achieves performance comparable to and slightly exceeding Qwen3-Omni-30B-A3B-Instruct on OmniClean aggregate summaries, without relying on a stronger omni-modal teacher for distillation. (confidence: 1.00)
  Evidence: after SFT on self-distilled data, the 3B model becomes comparable to larger open-source references and slightly exceeds Qwen3-Omni-30B-A3B-Instruct under both OmniClean aggregate summaries, without distilling answers from a stronger omni-modal teacher. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex

### Limitation

- OmniClean operates as a debiased evaluation view that reduces visual shortcuts under a specific protocol, but it does not definitively prove that the retained queries are causally dependent on audio in every possible setting. (confidence: 1.00)
  Evidence: OmniClean is therefore an operational evaluation view: it reduces visual shortcuts under a fixed protocol rather than proving that the retained queries are causally audio-dependent in every possible setting. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_12034/source.tex

## C$^3$ache: Accelerating World Action Models with Cross Inference Chunk Cache

`c3ache` | authors: Weisen Zhao, Lam Nguyen, Zhicong Lu, Yuzhang Shang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- C$^3$ache (Cross Inference Chunk Cache) is a training-free acceleration method that caches and reuses denoising residuals across inference chunks at the same denoising step. (confidence: 1.00)
  Evidence: We introduce C$^3$ache, a training-free method that caches and reuses these residuals across inference chunks at the same denoising step. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/summary.md
- Fast-WAM is a World Action Model backbone that disentangles representation learning during training from explicit future generation during inference, allowing it to produce actions directly without synthesizing future frames at test time. (confidence: 0.90)
  Evidence: Fast-WAM~\cite{yuan2026fastwam} disentangles the two roles a video objective provides---representation learning during training and explicit future generation during inference---and finds that the benefit comes overwhelmingly from the former. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex

### Benchmark

- The authors evaluate their method using the LIBERO and RoboTwin benchmarks. (confidence: 1.00)
  Evidence: We show on LIBERO and RoboTwin~\cite{liu2023libero,mu2025robotwin}, with a Fast-WAM\cite{yuan2026fastwam} backbone, that \ours \ achieves up to a $2.5\times$ wall clock inference speedup [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex

### Claim

- World Action Models (WAMs) generalize better to novel motions and environments than standard Vision-Language-Action (VLA) policies because they use a video-modeling objective to learn from abundant unlabeled video. (confidence: 1.00)
  Evidence: World Action Models (WAMs) generalize better than standard Vision-Language-Action (VLA) policies to novel motions and environments, because a video-modeling objective lets them learn from abundant unlabeled video rather than scarce labeled robot demonstrations. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex
- Existing acceleration methods for diffusion models in WAMs overlook the redundancy that exists across different inference chunks. (confidence: 1.00)
  Evidence: Our empirical analysis reveals a substantial source of redundancy they overlook: redundancy across chunks. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex
- During smooth robot behaviors, the intermediate residuals computed at a specific denoising step are highly correlated between consecutive inference chunks. (confidence: 1.00)
  Evidence: When a robot executes a smooth behavior, the residuals computed at a given denoising step are strongly correlated from one chunk to the next. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex
- C$^3$ache achieves up to a 2.5x speedup in total wall-clock inference time with negligible degradation in task success rate when using a Fast-WAM backbone. (confidence: 1.00)
  Evidence: Experiments on benchmarks with a Fast-WAM backbone show that C$^3$ache achieves up to a $2.5\times$ speedup in total wall-clock inference time, with negligible degradation in task success rate. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/summary.md
- Vision-Language-Action (VLA) models are limited in their physical behaviors because they are bounded by the specific robot demonstrations they were fine-tuned on. (confidence: 1.00)
  Evidence: Because a VLA is ultimately trained to regress actions directly from observations, the physical behaviors it can produce are bounded by the robot demonstrations it was fine-tuned on. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c3ache/source.tex

## C-GenReg: Training-Free 3D Point Cloud Registration by Multi-View-Consistent Geometry-to-Image Generation with Probabilistic Modalities Fusion

`c-genreg` | authors: Yuval Haitman, Amit Efraim, Joseph M. Francos | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit, https://github.com/yuvalH9/CGenReg

### Method

- C-GenReg is a training-free framework for 3D point cloud registration that leverages world-scale generative priors and Vision Foundation Models (VFMs). (confidence: 1.00)
  Evidence: We introduce C-GenReg, a training-free framework for 3D point cloud registration that leverages the complementary strengths of world-scale generative priors and registration-oriented Vision Foundation Models (VFMs). [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- C-GenReg uses a World Foundation Model to synthesize multi-view-consistent RGB representations from the input geometry to transfer the matching problem into an auxiliary image domain. (confidence: 1.00)
  Evidence: C-GenReg augments the geometric point cloud registration branch by transferring the matching problem into an auxiliary image domain, where VFMs excel, using a World Foundation Model to synthesize multi-view-consistent RGB representations from the input geometry. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- A Vision Foundation Model (VFM) pretrained for finding dense correspondences extracts matches from the generated RGB views, which are then lifted back to 3D using the original depth maps. (confidence: 1.00)
  Evidence: From these generated views, a VFM pretrained for finding dense correspondences extracts matches. The resulting pixel correspondences are lifted back to 3D via the original depth maps. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- C-GenReg introduces a "Match-then-Fuse" probabilistic cold-fusion scheme to combine independent correspondence posteriors from the generated-RGB branch and the raw geometric branch. (confidence: 1.00)
  Evidence: To further enhance robustness, we introduce a "Match-then-Fuse" probabilistic cold-fusion scheme that combines two independent correspondence posteriors, that of the generated-RGB branch with that of the raw geometric branch. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/summary.md
- The C-GenReg pipeline is fully zero-shot and plug-and-play, relying entirely on pretrained modules without requiring any fine-tuning or additional learning. (confidence: 1.00)
  Evidence: C-GenReg is zero-shot and plug-and-play: all modules are pretrained and operate without fine-tuning. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- The geometric branch of C-GenReg extracts dense geometric features directly from the raw point clouds using a pretrained geometric feature extractor. (confidence: 1.00)
  Evidence: (2) \textbf{Geometric Branch} - extracts dense geometric features directly from the raw point clouds using a pretrained geometric feature extractor. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex
- The generated RGB views in C-GenReg are processed by a frozen World Foundation Model, and a subset of frames is fed to a frozen, task-specific Vision Foundation Model. (confidence: 1.00)
  Evidence: temporally concatenated and processed by a frozen \textit{World Foundation Model} to generate RGB views that are geometrically aligned and appearance-consistent across views. A subset of $K$ frames per domain is fed to a frozen, task-specific \textit{Vision Foundation Model} (VFM) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex

### Benchmark

- C-GenReg is evaluated on the indoor benchmarks 3DMatch and ScanNet, as well as the outdoor benchmark Waymo. (confidence: 1.00)
  Evidence: Extensive experiments on indoor (3DMatch, ScanNet) and outdoor (Waymo) benchmarks demonstrate strong zero-shot performance and superior cross-domain generalization. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex

### Claim

- C-GenReg is the first generative registration framework to successfully operate on real outdoor LiDAR data where no imagery data is available. (confidence: 1.00)
  Evidence: For the first time, we demonstrate a generative registration framework that operates successfully on real outdoor LiDAR data, where no imagery data is available. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/summary.md
- Current learning-based 3D point cloud registration methods struggle to generalize across different sensing modalities, sampling differences, and environments. (confidence: 1.00)
  Evidence: Current learning-based 3D point cloud registration methods struggle to generalize across sensing modalities, sampling differences, and environments. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/c-genreg/source.tex

## CLASP: Language-Driven Robot Skill Selection and Composition using Task-Parameterized Learning

`clasp` | authors: Markus Knauer, Valentin Gieraths, Tai Mai, Samuel Bustamante, Alin Albu-Schäffer, Freek Stulp, João Silvério | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- CLASP uses a modular architecture that combines task-parameterized kernelized movement primitives (TP-KMPs) with pretrained vision-language models (VLMs). (confidence: 1.00)
  Evidence: This work bridges this gap through a modular architecture combining task-parameterized kernelized movement primitives (TP-KMPs) with pretrained VLMs. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/summary.md
- Robot skills in the CLASP framework are acquired from 2 to 5 kinesthetic demonstrations. (confidence: 1.00)
  Evidence: During learning, skills are acquired from 2 to 5 kinesthetic demonstrations [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/summary.md
- The VLM automatically generates JSON schemas that describe each skill's task parameters, preconditions, and semantic properties based on detected object types and positions. (confidence: 1.00)
  Evidence: the VLM automatically analyzes detected object types/positions to generate JSON schemas describing each skill's task parameters (object poses), preconditions, and semantic properties. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex
- The system creates novel continuous behaviors by fusing local trajectory distributions from compatible skills through covariance-weighted composition. (confidence: 1.00)
  Evidence: the framework can synthesize novel continuous behaviors that were never individually demonstrated, by fusing local trajectory distributions from compatible skills through covariance-weighted composition. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex
- A formal compatibility constraint ensures that skill composition is only attempted when the confidence regions of the skills do not conflict. (confidence: 1.00)
  Evidence: A formal compatibility constraint (\cref{eq:compatibility_constraint}) guarantees that composition is only attempted when the skills' confidence regions do not conflict [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex
- The system includes an active skill acquisition loop that detects capability gaps and autonomously requests targeted demonstrations when existing skills or compositions are insufficient. (confidence: 1.00)
  Evidence: When neither existing skills nor valid compositions satisfy a user request, the system detects this capability gap and autonomously requests targeted demonstrations [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex
- The framework operates without requiring any fine-tuning of the pretrained vision-language model. (confidence: 1.00)
  Evidence: enabling data-efficient skill generation without VLM fine-tuning [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex

### Benchmark

- The approach is validated on a 7-DoF torque-controlled robot across four evaluation dimensions: object-type and pose generalization, skill composition, and active capability gap detection. (confidence: 1.00)
  Evidence: We validate our approach on a 7-DoF torque-controlled robot across four evaluation dimensions: object-type and pose generalization, skill composition, and active capability gap detection [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex

### Claim

- The CLASP framework achieves success rates between 73.3% and 100% in scenarios requiring skill selection, composition, and active learning. (confidence: 1.00)
  Evidence: Validation on a 7-DoF manipulator shows success rates of 73.3%-100% in scenarios requiring skill selection, composition, and active learning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/summary.md

### Limitation

- Existing language-grounded skill systems are limited to symbolic composition, meaning they select and sequence discrete primitives without modifying their underlying trajectories. (confidence: 1.00)
  Evidence: Existing language-grounded skill systems compose skills \textit{symbolically}: selecting and sequencing discrete primitives without modifying their trajectories [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/clasp/source.tex

## CP4D: Compositional Physics-aware 4D Scene Generation

`cp4d` | authors: Hanxin Zhu, Cong Wang, Tianyu He, Long Chen, Xin Jin, Chen Gao, Zhibo Chen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- CP4D reformulates 4D generation as the integration of a static 3D environment with physically grounded dynamic objects. (confidence: 1.00)
  Evidence: CP4D reformulates 4D generation as the integration of a static 3D environment with physically grounded dynamic objects. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex
- The CP4D framework follows a three-stage pipeline: generating 3D representations, simulating physically plausible motions, and automatically composing the scene. (confidence: 1.00)
  Evidence: our framework follows a three-stage pipeline: 	extbf{1)} Firstly, we leverage pre-trained expert models to generate high-fidelity 3D representations of the environment and foreground objects respectively. 	extbf{2)} Subsequently, to produce physically plausible trajectories and realistic interactions for these objects, we propose a hybrid motion synthesis strategy that integrates priors from physical simulators with the common sense embedded in video diffusion models. 	extbf{3)} Finally, we develop an automated composition mechanism that seamlessly fuses the static environment and dynamic objects into coherent, physically consistent 4D scenes. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex
- In the first stage, CP4D uses a text-to-image model for the background and an image editing model for the foreground, reconstructing both into 3D using pre-trained expert models. (confidence: 1.00)
  Evidence: we first synthesize a background image using a text-to-image generative model, after which an image editing model, conditioned on this background, is employed to generate foregrounds that are visually compatible with it. Both the background and the foregrounds are then reconstructed into their respective 3D representations using pre-trained expert models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex
- CP4D employs a hybrid motion synthesis strategy that uses physical simulators for coarse trajectories and refines them using commonsense knowledge from video generative models. (confidence: 1.00)
  Evidence: we first leverage physical simulators to produce coarse object trajectories that comply with fundamental physical laws. These initial dynamics are subsequently refined using the commonsense knowledge embedded in video generative models [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex
- The automated composition mechanism uses monocular depth estimation and a depth-aware heuristic rule to estimate and calibrate the spatial attributes of foreground objects within the background. (confidence: 1.00)
  Evidence: By leveraging monocular depth estimation and a depth-aware heuristic rule, this mechanism first estimates the relative spatial attributes of foreground objects (	extit{e.g.}, positions and scales) within the background, which are subsequently calibrated through optimization [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex
- CP4D's compositional design allows users to edit different scene elements such as foreground objects, background environments, and motion trajectories. (confidence: 1.00)
  Evidence: users are afforded the flexibility to edit different scene elements, such as foreground objects, background environments, and motion trajectories, thus facilitating diverse 4D generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex

### Claim

- CP4D generates explorable and interactive 4D scenes with high visual fidelity, strong physical plausibility, and fine-grained controllability, outperforming existing methods. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that CP4D can generate explorable and interactive 4D scenes with high visual fidelity, strong physical plausibility, and fine-grained controllability, significantly outperforming existing methods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex

### Limitation

- Existing 4D generation approaches typically fail to capture underlying physical principles, resulting in physically inconsistent and visually implausible outputs. (confidence: 1.00)
  Evidence: existing approaches typically fail to capture the underlying physical principles, producing results that are both physically inconsistent and visually implausible. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cp4d/source.tex

## CT-VAM: A Cerebello-Thalamic-Inspired Vision-Action Model for Efficient Visuomotor Control

`ct-vam` | authors: Jiacheng Li, Yize Guo, Jiabin Guo, Qingchen Liu, Jiahu Qin | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- CT-VAM is a cerebello-thalamic-inspired vision-action model that acts as a compact local execution policy predicting action chunks from dual-view visual observations, proprioception, and a lightweight task condition. (confidence: 1.00)
  Evidence: we propose a cerebello-thalamic-inspired vision-action model (CT-VAM) for efficient task-conditioned visuomotor control. CT-VAM acts as a compact local execution policy that predicts action chunks from dualview visual observations, proprioception, and a lightweight task condition [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/summary.md
- CT-VAM introduces TARS (Thalamic Action Routing Stream), a stream-separated conditional attention decoder that independently routes action, visual, and task streams to prevent dense sensory tokens from overwhelming task-relevant conditions. (confidence: 1.00)
  Evidence: CT-VAM introduces TARS (Thalamic Action Routing Stream), a stream-separated conditional attention decoder that independently routes action, visual and task streams, preventing dense sensory tokens from overwhelming compact task-relevant conditions. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/source.tex
- CT-VAM employs flow-consistent inpainting for asynchronous chunk execution, enabling next-chunk inference to overlap with current execution while preserving action continuity. (confidence: 1.00)
  Evidence: We introduce flow-consistent inpainting for asynchronous chunk execution, enabling next-chunk inference to overlap with current execution while preserving action continuity. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/source.tex
- The asynchronous chunk execution method is built on rectified flow action decoding, which uses noise-to-data interpolation from flow-based generative modeling. (confidence: 1.00)
  Evidence: The method is built on rectified flow action decoding, which follows the noise-to-data interpolation used in flow-based generative modeling [artifact:source_tex]

### Benchmark

- CT-VAM is evaluated on the LIBERO benchmark for simulation experiments to assess its visuomotor performance. (confidence: 1.00)
  Evidence: Simulation experiments use standard robot learning benchmarks such as LIBERO and related language-conditioned manipulation settings [artifact:source_tex]

### Claim

- With only 68M parameters, CT-VAM achieves LIBERO success rates competitive with substantially larger VLA models while reducing inference latency. (confidence: 1.00)
  Evidence: With only 68M parameters, CT-VAM achieves LIBERO success rates competitive with substantially larger VLA models, while reducing inference latency. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/source.tex
- CT-VAM supports efficient fully onboard deployment on resource-constrained edge devices like the Jetson Orin NX, running at over 10 Hz without repeatedly invoking a large language-conditioned policy. (confidence: 1.00)
  Evidence: The results show that CT-VAM achieves strong visuomotor performance while running fully onboard on Jetson Orin NX at over 10 Hz, without repeatedly invoking a large language-conditioned policy during low-level execution. [artifact:source_tex]
- CT-VAM separates high-level language grounding from high-frequency visual feedback control, converting raw language into an intent representation to avoid repeated language processing during execution. (confidence: 1.00)
  Evidence: We formulate grounded visuomotor execution, which separates semantic language grounding from high-frequency visual feedback control. Raw language is converted into an intent representation, while the low-level policy still uses visual-proprioceptive observations for closed-loop action generation, avoiding repeated language processing during execution. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ct-vam/source.tex

## CapRL++: Unified Reinforcement Learning with Verifiable Rewards for Dense Image and Video Captioning

`caprl` | authors: Penghui Yang, Long Xing, Xiaoyi Dong, Yuhang Zang, Yuhang Cao, Yibin Wang, Yujie Zhou, Jiazi Bu, Jianze Liang, Qidong Huang, Jiaqi Wang, Feng Wu, Dahua Lin | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/InternLM/CapRL

### Method

- CapRL++ is a reference-free training framework that employs a decoupled two-stage pipeline where an LVLM generates a caption, and the objective reward is derived from the accuracy of a separate, vision-free LLM answering Multiple-Choice Questions based solely on that caption. (confidence: 1.00)
  Evidence: We introduce Captioning Reinforcement Learning++ (CapRL++), a novel reference-free training framework that redefines caption quality through its utility: 
a high-quality caption should enable a non-visual language model to accurately answer questions about the corresponding visual content. 
CapRL++ employs a decoupled two-stage pipeline where an LVLM generates a caption, and the objective reward is derived from the accuracy of a separate, vision-free LLM answering Multiple-Choice Questions based solely on that caption. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex
- The paper proposes applying Reinforcement Learning with Verifiable Rewards (RLVR) to the open-ended task of multimodal captioning to overcome the limitations of SFT. (confidence: 1.00)
  Evidence: To overcome these limitations, we propose applying the Reinforcement Learning with Verifiable Rewards (RLVR) paradigm to the open-ended task of multimodal captioning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex

### Benchmark

- The Prism Framework is used for caption quality evaluation. (confidence: 1.00)
  Evidence: within the Prism Framework for caption quality evaluation [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex

### Claim

- Evaluations on more than 20 image and video benchmarks show that CapRL++ improves dense caption quality and strengthens caption-based pretraining across tasks such as spatial and temporal understanding. (confidence: 1.00)
  Evidence: Evaluations on more than 20 image and video benchmarks show that CapRL++ improves dense caption quality and strengthens caption-based pretraining across various tasks such as spatial and temporal understanding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex
- Within the Prism Framework for caption quality evaluation, compact models trained with CapRL++ achieve dense captioning performance comparable to, and in some cases surpassing, substantially larger models like Qwen2.5-VL-72B and Qwen3-VL-235B-A22B. (confidence: 1.00)
  Evidence: Furthermore, within the Prism Framework for caption quality evaluation, compact models trained with CapRL++ achieve dense captioning performance comparable to, 
and in some cases surpassing, substantially larger models (e.g., Qwen2.5-VL-72B and Qwen3-VL-235B-A22B). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex

### Limitation

- Supervised Fine-Tuning (SFT) for captioning relies on expensive, non-scalable annotations and often causes models to memorize specific ground-truth answers, limiting their generality and ability to generate diverse, creative descriptions. (confidence: 1.00)
  Evidence: Current state-of-the-art captioning models are typically trained with Supervised Fine-Tuning (SFT), 
a paradigm that relies on expensive, non-scalable annotations and often causes models to memorize specific ground-truth answers, limiting their generality and
ability to generate diverse, creative descriptions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex
- Using reward models or LLM-as-a-judge for captioning feedback is vulnerable to reward hacking, where the captioning model exploits evaluator biases such as a preference for verbose or brief outputs. (confidence: 1.00)
  Evidence: Using \textbf{reward models} \cite{liu2025inference,su2025crossing,lu2025writing} or \textbf{LLM-as-a-judge} \cite{gunjal2025rubrics} as feedback is vulnerable to \textit{reward hacking}, where the captioning model exploits evaluator biases (e.g., a preference for verbose or brief outputs) instead of producing a high-quality response. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/caprl/source.tex

## Causal Physics Steering in Video World Models via Concept Activation Vectors

`2605_24322` | authors: Nahid Alam | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- The paper introduces 'physics steering', a training-free method that uses the weight vector of a linear probe at a Physics Emergence Zone (PEZ) layer as a Concept Activation Vector (CAV) and injects it into hidden states during inference to shift the model's physical expectations without altering model weights. (confidence: 1.00)
  Evidence: We present physics steering, a training-free method that uses the weight vector of a linear probe at a PEZ layer as a Concept Activation Vector (CAV) and injects it into hidden states during inference. This shifts the model's physical expectations without changing any model weights. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/summary.md

### Benchmark

- The IntPhys benchmark is used to evaluate the physics steering intervention, showing that it reliably shifts the model's plausibility judgment in either direction based on the steering sign. (confidence: 1.00)
  Evidence: On the IntPhys benchmark, this intervention reliably shifts the model's plausibility judgment in either direction, depending on the steering sign. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/summary.md

### Claim

- The steering effect on physical plausibility is localized to the Physics Emergence Zone (PEZ), as the intervention only works when applied within these specific middle transformer layers of VideoMAE. (confidence: 1.00)
  Evidence: The effect appears only when the intervention is applied within the Physics Emergence Zone, suggesting that the relevant physics representation is localized there. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/summary.md
- In VideoMAE, physical reasoning is encoded separately from motion direction, and different intuitive physics principles occupy distinct directions within the representation space. (confidence: 1.00)
  Evidence: We further find that physics is encoded separately from motion direction, and that different intuitive physics principles occupy distinct directions within this representation space. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/summary.md

### Limitation

- The current method applies the steering intervention uniformly to all patch tokens across time, lacking the ability to vary steering strength over time to model physics violations that emerge at specific moments. (confidence: 1.00)
  Evidence: The current method applies the same $\alpha \cdot \mathbf{v}_{l^*}$ to all $N$ patch tokens uniformly across time. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/source.tex
- It is currently unknown whether the VideoMAE decoder is sensitive enough to Physics Emergence Zone (PEZ) perturbations to successfully reconstruct steered latents into physically altered videos in pixel space. (confidence: 1.00)
  Evidence: Whether the decoder is sufficiently sensitive to PEZ perturbations remains an empirical question. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24322/source.tex

## CheXanatomy: Anatomy-Aware Vision-Language Modeling for Chest Radiographs

`chexanatomy` | authors: Sergios Gatidis, Curtis Langlotz, Christian Bluethgen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/sergiosgatidis/CheXanatomy, https://github.com/sergiosgatidis/CheXsynth

### Method

- CheXanatomy trains a pretrained vision-language model to generate anatomical segmentations autoregressively via next-token prediction without using task-specific pixel-space decoder heads. (confidence: 1.00)
  Evidence: We introduce CheXanatomy, a framework that trains a pretrained VLM to generate anatomical segmentations autoregressively via next-token prediction, without introducing task-specific pixel-space decoder heads. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- The framework synthesizes realistic chest radiographs from 3D CT volumes and forward-projects CT segmentation labels to create anatomically consistent 2D masks for scalable supervision. (confidence: 1.00)
  Evidence: To enable scalable supervision, we synthesize realistic chest radiographs from CT volumes and forward-project CT segmentation labels to obtain anatomically consistent 2D masks. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Segmentation masks are encoded into a discrete 16-dimensional latent representation using a vector-quantized variational autoencoder (VQ-VAE) for autoregressive prediction. (confidence: 1.00)
  Evidence: Mask prediction is implemented through a vector-quantized variational autoencoder (VQ-VAE) trained to encode binary masks into a discrete 16-dimensional latent representation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- The base vision-language model used is PaliGemma 2, which combines a SigLIP-So400m vision encoder with a Gemma 2 large language model. (confidence: 1.00)
  Evidence: PaliGemma 2 consists of a SigLIP-So400m vision encoder with a linear projection into the language token space and a Gemma 2 large language model for autoregressive prediction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Model adaptation is performed using Low-Rank Adaptation (LoRA) for parameter-efficient fine-tuning. (confidence: 1.00)
  Evidence: Model adaptation was performed using Low-Rank Adaptation (LoRA). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex

### Dataset

- The CT-RATE dataset, comprising 12,984 training and 683 test non-contrast CT volumes, is used to generate synthetic projection radiographs. (confidence: 1.00)
  Evidence: We used non-contrast CT scans from the CT-RATE dataset, consisting of 12,984 training CT volumes and 683 randomly selected test CT volumes. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- The CheXmask and VinDr-RibCXR datasets are used to evaluate out-of-distribution segmentation performance on real chest radiographs. (confidence: 1.00)
  Evidence: Segmentation performance was evaluated on three datasets: synthetic CT-RATE test projections (1,366 images from posterior--anterior and lateral views), CheXmask (200 randomly selected posterior--anterior radiographs with heart and lung masks), and VinDr-RibCXR (198 posterior–anterior radiographs with bilateral rib segmentations). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex

### Benchmark

- The RadVLM visual grounding dataset is used to evaluate data-efficient transfer to novel localization tasks. (confidence: 1.00)
  Evidence: To evaluate transfer to novel localization tasks, few-shot experiments were conducted on visual grounding tasks from the RadVLM dataset. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex

### Claim

- The proposed autoregressive anatomical supervision achieves in-distribution segmentation performance comparable to a specialized U-Net baseline in overlap-based metrics. (confidence: 1.00)
  Evidence: The best PaliGemma configuration (10B, 448x448) approached the performance of the specialized U-Net baseline in overlap-based metrics, achieving comparable Dice and IoU values. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Under domain shift to real chest radiographs, the anatomy-pretrained VLM maintains comparable overlap metrics to U-Net while demonstrating superior geometric stability and reduced boundary errors. (confidence: 1.00)
  Evidence: The best PaliGemma models achieved Dice and IoU comparable to the U-Net baseline while consistently outperforming it on boundary and shape-based metrics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Explicit anatomical pretraining improves sample efficiency and provides a stronger spatial prior when adapting to novel localization tasks with limited supervision. (confidence: 1.00)
  Evidence: When fine-tuned with limited or no supervision (0%, 1%, and 3% of the training data), anatomy-pretrained models consistently outperformed their non-pretrained counterparts in bounding box IoU [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Increasing the model scale and using a higher input resolution consistently improves segmentation performance. (confidence: 1.00)
  Evidence: Larger models and higher input image resolution improve performance, while vision encoder fine-tuning has limited effect. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex
- Fine-tuning the vision encoder during training has no measurable influence on the model's segmentation performance. (confidence: 1.00)
  Evidence: Fine-tuning the vision encoder had no measurable influence on performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex

### Limitation

- While the VLM achieves better boundary and shape metrics, the specialized U-Net baseline still achieves slightly higher overall Dice and IoU overlap metrics in-distribution. (confidence: 1.00)
  Evidence: While U-Net achieved slightly higher Dice and IoU overall, the high-resolution 10B PaliGemma model obtained lower Hausdorff distance and lower Fourier descriptor distance [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chexanatomy/source.tex

## ChronoPhyBench: Do MLLMs Truly Understand the World or Merely Exploit Language Priors?

`chronophybench` | authors: Bin Zhu, Yanhao Jia, Kexin Zhao, Jie Wang, Munan Ning, Hao Li, Yuwei Niu, Tanqing Sun, Huangchong Yan, Mingjun Pan, Xinyi Wu, Qishen Yin, Yunyang Ge, Shuai Zhao, Li Yuan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- ChronoPhyBench unifies next state prediction with Visual Question Answering (VQA) paradigms by conditioning on historical video context and textual captions to enforce models to deduce subsequent physical states. (confidence: 1.00)
  Evidence: which unifies next state prediction with Visual Question Answering (VQA) paradigms by conditioning on historical video context and textual captions to enforce models to deduce subsequent physical states through both single image selection and the inherently more complex task of multiple frame chronological sorting. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chronophybench/summary.md

### Dataset

- The authors constructed a large-scale multimodal reasoning dataset containing over 10,000 long-form videos with annotated captions, totaling 5 million tokens. (confidence: 1.00)
  Evidence: we construct a large-scale multimodal reasoning dataset curated using the ChronoPhyBench criteria, comprising over 10,000 long-form videos paired with meticulously annotated captions, totaling 5M tokens. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chronophybench/summary.md

### Benchmark

- The paper introduces ChronoPhyBench, a novel multimodal chronological physical dynamics reasoning benchmark. (confidence: 1.00)
  Evidence: we propose a novel multimodal Chrono}logical Physical Dynamics Reasoning Benchmark ChronoPhyBench [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chronophybench/summary.md

### Claim

- Current open-source models have a very limited capacity for performing physically grounded multimodal reasoning. (confidence: 1.00)
  Evidence: The capacity of current open-source models to perform physically grounded multimodal reasoning remains in its infancy. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chronophybench/summary.md
- There is a critical ambiguity regarding whether Multimodal Large Language Models (MLLMs) genuinely synthesize cross-modal information or merely exploit language priors to mask single-modality reliance. (confidence: 1.00)
  Evidence: it remains unclear whether these models genuinely synthesize cross-modal information to construct physically grounded reasoning chains, or if they merely exploit strong language priors to mask single-modality reliance, thereby hallucinating advanced multimodal capabilities. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/chronophybench/summary.md

## Closed-Loop Neural Activation Control in Vision-Language-Action Models

`2606_00269` | authors: Abhijith Babu, Ramneet Kaur, Nathaniel D. Bastian, Olivera Kotevska, Susmit Jha, Yanzhao Wu, Sumit Kumar Jha, Anirban Roy | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes CTRL-STEER, a closed-loop framework that replaces static intervention strength with adaptive, time-varying control signals for steering Vision-Language-Action (VLA) models. (confidence: 1.00)
  Evidence: We propose CTRL-STEER, a closed-loop framework that replaces static intervention strength with adaptive, time-varying control signals. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- CTRL-STEER decouples representation from regulation by steering along motion-aligned residual directions while a feedback controller adjusts intervention magnitude online. (confidence: 1.00)
  Evidence: The key idea is to decouple representation from regulation: rather than assuming temporal concepts are directly controlled by individual neurons, we steer along motion-aligned residual directions while a feedback controller adjusts intervention magnitude online. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- The CTRL-STEER framework is instantiated with both PID and reinforcement learning (RL) based controllers. (confidence: 1.00)
  Evidence: We instantiate this framework with both PID and reinforcement learning based controllers. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- The method identifies feature-aligned neurons by projecting FFN value vectors into token space and selecting neurons whose semantic embeddings align with representative control features. (confidence: 1.00)
  Evidence: First, we identify feature-aligned neurons by projecting FFN value vectors into token space and selecting neurons whose semantic embeddings align with representative control features. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md

### Dataset

- The experiments utilize a fine-tuned OpenVLA policy. (confidence: 1.00)
  Evidence: Experiments with a fine-tuned OpenVLA policy on four LIBERO task suites show that CTRL-STEER achieves more stable concept regulation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md

### Benchmark

- The method is evaluated on four task suites from the LIBERO benchmark. (confidence: 1.00)
  Evidence: Experiments with a fine-tuned OpenVLA policy on four LIBERO task suites show that CTRL-STEER achieves more stable concept regulation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md
- The method is also evaluated on the BridgeData V2 benchmark. (confidence: 1.00)
  Evidence: We evaluate our method on the LIBERO benchmark and BridgeData V2 [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/source.tex

### Claim

- CTRL-STEER achieves more stable concept regulation and a better steering-task success trade-off than fixed-coefficient baselines without modifying or retraining the base model. (confidence: 1.00)
  Evidence: CTRL-STEER achieves more stable concept regulation and a better steering-task success trade-off than fixed-coefficient baselines, without modifying or retraining the base model. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/summary.md

### Limitation

- A limitation of the approach is that the RL controller must be trained separately for each task. (confidence: 1.00)
  Evidence: Our approach has limitations: the RL controller is trained per task, neuron identification still involves partial manual filtering, and evaluation is limited to a small set of steering concepts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/source.tex
- Neuron identification in the proposed approach still requires partial manual filtering. (confidence: 1.00)
  Evidence: Our approach has limitations: the RL controller is trained per task, neuron identification still involves partial manual filtering, and evaluation is limited to a small set of steering concepts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/source.tex
- The evaluation of the proposed method is limited to a small set of steering concepts. (confidence: 1.00)
  Evidence: Our approach has limitations: the RL controller is trained per task, neuron identification still involves partial manual filtering, and evaluation is limited to a small set of steering concepts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00269/source.tex

## Co-training with Ego-centric Video and Demonstration for Robot Navigation Task

`2606_01951` | authors: Shoya Kuno, Yumo Ouchi, Kanata Suzuki | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed framework converts egocentric walking videos into mobile robot imitation learning datasets by estimating camera motion and transforming it into robot-compatible action representations. (confidence: 1.00)
  Evidence: In this paper, we propose a framework that converts egocentric walking videos into datasets for mobile robot imitation learning. The proposed method estimates camera motion from human videos and transforms it into action representations compatible with ground mobile robots. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/summary.md
- The system estimates 6-DoF camera motion from egocentric videos using a monocular visual odometry pipeline based on SuperPoint and LightGlue. (confidence: 1.00)
  Evidence: We estimate camera motion from egocentric videos using a monocular visual odometry (VO) pipeline based on SuperPoint and LightGlue. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/source.tex
- The estimated camera trajectory is smoothed and projected into 2-DoF velocity commands using kinematic projection and Kalman filtering to match ground mobile robot constraints. (confidence: 1.00)
  Evidence: The estimated camera trajectory is then transformed into 2-DoF velocity commands via kinematic projection and Kalman filtering, ensuring consistency with the motion constraints of ground mobile robots. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/source.tex

### Benchmark

- The proposed method is evaluated using a fruit-search navigation task to demonstrate the effectiveness of human egocentric videos for mobile robot learning. (confidence: 1.00)
  Evidence: Experiments on a fruit-search navigation task demonstrate that human egocentric videos provide an effective and scalable data source for mobile robot learning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/summary.md

### Claim

- The performance of Vision-Language-Action (VLA) models heavily relies on large-scale, high-quality training data, which is expensive and time-consuming to collect on real robots. (confidence: 1.00)
  Evidence: Vision-language-action (VLA) models are promising for diverse robotic tasks, but their performance heavily depends on large-scale high-quality training data, whose collection on real robots is costly and time-consuming. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/summary.md
- Jointly training a VLA model on both human-derived and robot-collected datasets results in better language understanding and more robust action generation compared to using either data source alone. (confidence: 1.00)
  Evidence: By jointly training a VLA model on human-derived and robot-collected datasets, the model achieves improved language understanding and more robust action generation than training with either data source alone. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/summary.md

### Limitation

- Applying egocentric human video data augmentation to mobile robot navigation is difficult because human walking causes large viewpoint changes and unstable camera motion. (confidence: 1.00)
  Evidence: In navigation-oriented mobile robot tasks, however, large viewpoint changes and unstable camera motion caused by human walking frequently occur, making it difficult to directly apply existing approaches. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01951/source.tex

## CoCoSI: Collaborative Cognitive Map Construction for Spatial Intelligence

`cocosi` | authors: Yiming Zhang, Ruoxuan Cao, Zhihang Zhong | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- CoCoSI proposes a plug-and-play multi-agent framework that collaboratively constructs cognitive maps as structured spatial memory to enhance the spatial understanding of pretrained MLLMs without architectural modification or additional training. (confidence: 1.00)
  Evidence: we propose a plug-and-play multi-agent framework that collaboratively constructs cognitive maps as structured spatial memory, enhancing the spatial understanding of arbitrary pretrained MLLMs without architectural modification or additional training. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- The CoCoSI framework features local-global agent coordination, cognitive map construction with atomic commits, and cross-agent verification. (confidence: 1.00)
  Evidence: Our framework features local-global agent coordination, cognitive map construction with atomic commits, and cross-agent verification. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- The framework decomposes long videos into shorter segments, assigns them to multiple agents for local spatial reasoning, and coordinates their partial observations into a unified cognitive map. (confidence: 1.00)
  Evidence: It decomposes long videos into shorter segments, assigns them to multiple agents for local spatial reasoning, and coordinates their partial observations into a unified cognitive map. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- CoCoSI introduces atomic commits for controlled map updates and cross-agent verification for reconciling inconsistent object localization and layout estimation. (confidence: 1.00)
  Evidence: To improve reliability, we introduce atomic commits for controlled map updates and cross-agent verification for reconciling inconsistent object localization and layout estimation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- During local-global coordination, a summary agent identifies persistent objects that appear throughout the video and constructs a global anchor cognitive map over these objects. (confidence: 1.00)
  Evidence: a summary agent $v_s$ identifies a set of persistent objects $O_c$ that appear throughout the video and constructs a global anchor cognitive map $C_a$ over these objects. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- Each cognitive map in the CoCoSI framework is represented as a continuous 10x10 spatial grid, where object positions are defined over the range [0,10]^2. (confidence: 1.00)
  Evidence: We represent each cognitive map as a continuous $10 \times 10$ spatial grid, where object positions are defined over $[0,10]^2$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex

### Claim

- Extensive experiments demonstrate that CoCoSI achieves superior performance on spatial understanding tasks while remaining fully training-free. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that our method achieves superior performance on spatial understanding tasks while remaining fully training-free. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- The framework consistently improves over single-agent methods, general multi-agent baselines, and other training-free alternatives on spatial understanding benchmarks. (confidence: 1.00)
  Evidence: Experiments show that our framework consistently improves over single-agent methods, general multi-agent baselines, and other training-free alternatives, demonstrating its effectiveness for video spatial reasoning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex

### Limitation

- Existing methods for spatial understanding, such as long-context modeling and external memory, often require architectural changes, memory modules, or finetuning, which limits their applicability to off-the-shelf pretrained MLLMs. (confidence: 1.00)
  Evidence: existing methods, such as long-context modeling and external memory, often require architectural changes, memory modules, or finetuning, limiting their applicability to off-the-shelf pretrained MLLMs. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex
- A single MLLM processing a long video for spatial understanding is prone to object mislocalization and inconsistent layout construction due to context limitations. (confidence: 1.00)
  Evidence: a single MLLM understanding a long video's spatial understanding is prone to object mislocalization and inconsistent layout construction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cocosi/source.tex

## Coarse-to-Control: Action-Token Planning for Vision-Language-Action Models

`coarse-to-control` | authors: Jinhao Wu, Shiduo Zhang, Yicheng Liu, Xiaopeng Yu, Sixian Li, Siyin Wang, Hang Zhao, Jing Huo, Yang Gao, Jingjing Gong, Xipeng Qiu, Yu-Gang Jiang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- Coarse-to-Control is a vision-language-action model that introduces planning natively in the action-token space by first predicting coarse action tokens and then executable action tokens. (confidence: 1.00)
  Evidence: We propose Coarse-to-Control, a plan-execute VLA that introduces planning natively in the action-token space. The key idea is to let the policy first predict a compact sequence of coarse action tokens that summarize the intended future trajectory, and then generate executable action tokens conditioned on this plan. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/summary.md
- The approach utilizes a joint plan-execute tokenizer that maps both planning and execution into a shared residual-VQ action vocabulary. (confidence: 1.00)
  Evidence: The key enabler is a joint plan-execute tokenizer that maps both planning and execution into a shared residual-VQ action vocabulary, so the plan remains close to the control manifold [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex
- Coarse action plans are created by compressing a long-horizon future action sequence into a shorter trajectory to capture stage-level motion intent. (confidence: 1.00)
  Evidence: To represent a coarse action plan, we summarize long-horizon future behavior into a shorter trajectory that captures stage-level motion intent rather than high-frequency executable control. Concretely, for each time step $t$ we take a long-horizon future action sequence $A_{t:t+H_p-1}$ and compress it into a coarse planning trajectory $\bar{A}_t$ with $K$ plan steps. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex

### Benchmark

- The proposed method is evaluated on the LIBERO and SimplerEnv-WidowX benchmarks, as well as real-world manipulation tasks. (confidence: 1.00)
  Evidence: Experiments on LIBERO, SimplerEnv-WidowX, and real-world manipulation tasks show that action-token planning consistently improves over direct action generation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/summary.md

### Claim

- Coarse-to-Control achieves a 97.90% average success rate on the LIBERO benchmark. (confidence: 1.00)
  Evidence: Coarse-to-Control reaches 97.90\% average success on LIBERO [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex
- Coarse-to-Control achieves an 83.3% success rate on the SimplerEnv-WidowX benchmark. (confidence: 1.00)
  Evidence: and 83.3\% on SimplerEnv-WidowX [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex
- Action-token planning outperforms direct action generation as well as textual, visual, and spatial Chain-of-Thought baselines. (confidence: 1.00)
  Evidence: We demonstrate on LIBERO, SimplerEnv-WidowX, and real-world manipulation tasks that action-token planning consistently improves over direct action generation and outperforms textual, visual, and spatial CoT baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/coarse-to-control/source.tex

## Comparative Analysis of Inference-Time Defense Methods for Multimodal Large Language Models

`2606_10904` | authors: Bulat Nutfullin, Vladimir Evgrafov, Dmitry Namiot | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Cosmos 3: Omnimodal World Models for Physical AI

`cosmos-3` | authors:  NVIDIA,  :,  Aditi, Niket Agarwal, Arslan Ali, Jon Allen, Martin Antolini, Adeline Aubame, Alisson Azzolini, Junjie Bai, Maciej Bala, Yogesh Balaji, Josh Bapst, Aarti Basant, Mukesh Beladiya, Mohammad Qazim Bhat, Zaid Pervaiz Bhat, Dan Blick, Vanni Brighella, Han Cai, Tiffany Cai, Eric Cameracci, Jiaxin Cao, Yulong Cao, Mark Carlson, Carlos Casanova, Ting-Yun Chang, Yan Chang, Yu-Wei Chao, Prithvijit Chattopadhyay, Roshan Chaudhari, Chieh-Yun Chen, Junyu Chen, Ke Chen, Qizhi Chen, Wenkai Chen, Xiaotong Chen, Yu Chen, An-Chieh Cheng, Click Cheng, Xiu Chia, Jeana Choi, Chaeyeon Chung, Wenyan Cong, Yin Cui, Magdalena Dadela, Nalin Dadhich, Wenliang Dai, Joyjit Daw, Alperen Degirmenci, Rodrigo Vieira Del Monte, Robert Denomme, Sameer Dharur, Marco Di Lucca, Ke Ding, Wenhao Ding, Yifan Ding, Yuzhu Dong, Nicole Drumheller, Yilun Du, Aigul Dzhumamuratova, Aleksandr Efitorov, Hamid Eghbalzadeh, Naomi Eigbe, Imad El Hanafi, Hassan Eslami, Benedikt Falk, Jiaojiao Fan, Jim Fan, Amol Fasale, Sergiy Fefilatyev, Liang Feng, Francesco Ferroni, Sanja Fidler, Xiao Fu, Vikram Fugro, Prashant Gaikwad, TJ Galda, Katelyn Gao, Yihuai Gao, Wenhang Ge, Sreyan Ghosh, Arushi Goel, Vivek Goel, Akash Gokul, Rama Govindaraju, Jinwei Gu, Miguel Guerrero, Elfie Guo, Aryaman Gupta, Siddharth Gururani, Hugo Hadfield, Song Han, Ankur Handa, Zekun Hao, Mohammad Harrim, Ali Hassani, Nathan Hayes-Roth, Yufan He, Chris Helvig, Cyrus Hogg, Madison Huang, Michael Huang, Sophia Huang, Yufan Huang, Jacob Huffman, DeLesley Hutchins, Suneel Indupuru, Boris Ivanovic, Arihant Jain, Joel Jang, Ryan Ji, Yanan Jian, Dongfu Jiang, Jingyi Jin, Atharva Joshi, Nikhilesh Joshi, Pranjali Joshi, Andy Ju, Jaehun Jung, Weiwei Kang, Scott Kassekert, Jan Kautz, Ashna Khetan, Julia Kiczka, Slawek Kierat, Gwanghyun Kim, Kuno Kim, Sunny Kim, Kezhi Kong, Xin Kong, Zhifeng Kong, Tomasz Kornuta, Egor Krivov, Hui Kuang, Saurav Kumar, Chia-Wen Kuo, George Kurian, Wojciech Kutak, JF Lafleche, Himangshu Lahkar, Omar Laymoun, Jayjun Lee, Sanggil Lee, Gabriele Leone, Boyi Li, Freya Li, Jiajun Li, Jinfeng Li, Ling Li, Pengcheng Li, Shangru Li, Tingle Li, Xiaolong Li, Xuan Li, Zhaoshuo Li, Zhiqi Li, Hao Liang, Maosheng Liao, Chen-Hsuan Lin, Tsung-Yi Lin, Ming-Yu Liu, Sifei Liu, Zihan Liu, Hai Loc Lu, Xiangyu Lu, Alice Luo, Ruipu Luo, Wenjie Luo, Jiangran Lyu, Martin Ding Ma, Nic Ma, Qianli Ma, Dawid Majchrowski, Louis Marcoux, Miguel Martin, Qing Miao, Ashkan Mirzaei, Shreyas Misra, Kaichun Mo, Durra Mohsin, Hyejin Moon, Pawel Morkisz, Saeid Motiian, Kirill Motkov, Seungjun Nah, Yashraj Narang, Deepak Narayanan, Thabang Ngazimbi, Julian Ouyang, Shubham Pachori, David Page, Yatian Pang, Sehwi Park, Mahesh Patekar, Mostofa Patwary, Marco Pavone, Trung Pham, Wei Ping, Soha Pouya, Shrimai Prabhumoye, Varun Praveen, Delin Qu, Hesam Rabeti, Morteza Ramezanali, Marilyn Reeb, Xuanchi Ren, Kristen Rumley, Wojciech Rymer, Jun Saito, Yeongho Seol, John Shao, Piyush Shekdar, Tianwei Shen, Humphrey Shi, Min Shi, Stella Shi, Kevin Shih, Mohammad Shoeybi, Mateusz Sieniawski, Shuran Song, Alexander Sotelo, Amir Sotoodeh, Sunil Srinivasa, Vignesh Srinivasakumar, Bartosz Stefaniak, Rahul Heinrich Steiger, Shangkun Sun, Jiaxiang Tang, Shitao Tang, Yangyang Tang, Yue Tang, Tolou Tavakkoli, Kayley Ting, Krzysztof Tomala, Wei-Cheng Tseng, Jibin Varghese, Sergei Vasilev, Thomas Volk, Raju Wagwani, Roger Waleffe, Andrew Z. Wang, Boxiang Wang, Haoxiang Wang, Qiao Wang, Shihao Wang, Shijie Wang, Ting-Chun Wang, Yan Wang, Yu Wang, Rohit Watve, David Wehr, Fangyin Wei, Xinshuo Weng, Jay Zhangjie Wu, Kedi Wu, Hongchi Xia, Summer Xiao, Tianjun Xiao, Kevin Xie, Daguang Xu, Jiashu Xu, Mengyao Xu, Ruqing Xu, Xingqian Xu, Yao Xu, Dinghao Yang, Dong Yang, Hans Yang, Xiaodong Yang, Xuning Yang, Yichu Yang, Yurong You, Zhiding Yu, Hao Yuan, Simon Yuen, Xiaohui Zeng, Pengcuo Zeren, Cindy Zha, Haotian Zhang, Jenny Zhang, Jing Zhang, Liangkai Zhang, Paris Zhang, Shun Zhang, Xuanmeng Zhang, Zhizheng Zhang, Ann Zhao, Yilin Zhao, Yuliya Zhautouskaya, Charles Zhou, Fengzhe Zhou, Shilin Zhu, Yuke Zhu, Dima Zhylko, Artur Zolkowski | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/nvidia/cosmos, https://github.com/nvidia/cosmos-framework

### Method

- Cosmos 3 utilizes a unified mixture-of-transformers architecture to jointly process and generate language, image, video, audio, and action sequences. (confidence: 1.00)
  Evidence: We introduce Cosmos 3, a family of omnimodal world models designed to jointly process and generate language, image, video, audio, and action sequences within a unified mixture-of-transformers architecture. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex
- The Cosmos 3 Generator conditions video generation on a target frame rate using a combination of Text Control and MRoPE FPS Modulation. (confidence: 1.00)
  Evidence: Based on these results, we adopt the Text Control + MRoPE FPS Modulation configuration for Cosmos 3 Generator. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex
- Cosmos 3 supports three distinct action generation modes: forward dynamics (FD), inverse dynamics (ID), and joint video-action prediction (policy). (confidence: 1.00)
  Evidence: Cosmos 3 supports three action generation modes: forward dynamics (FD), inverse dynamics (ID), and joint video-action prediction (policy). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex

### Dataset

- The authors release curated synthetic datasets and an evaluation benchmark for Physical AI under the OpenMDW-1.1 License. (confidence: 1.00)
  Evidence: we make our code, model checkpoints, curated synthetic datasets, and evaluation benchmark available under the Linux Foundation's OpenMDW-1.1 License [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/summary.md

### Claim

- Cosmos 3 models achieved top rankings as the best open-source Text-to-Image and Image-to-Video models by Artificial Analysis, and the best policy model by RoboArena. (confidence: 1.00)
  Evidence: Our post-trained Cosmos 3 models were ranked as the best open-source Text-to-Image and Image-to-Video models by Artificial Analysis, and the best policy model by RoboArena at the time the technical report was written. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex
- Using the Cosmos3-Nano Reasoner in the understanding tower instead of Qwen3-VL-8B improves domain scores, especially in Physical AI domains such as Robot, Physics, AV, and Industry. (confidence: 1.00)
  Evidence: replacing Qwen3-VL-8B with our Cosmos3-Nano Reasoner in the understanding tower yields consistent improvements in domain scores, particularly in Physical AI domains. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex
- Including audio data during continued pre-training does not degrade video generation quality and may slightly improve video-centric metrics. (confidence: 1.00)
  Evidence: suggesting that joint video-audio pre-training does not degrade video generation quality and may provide a modest benefit even when evaluated purely on video-centric metrics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex
- Training a joint checkpoint for forward dynamics, inverse dynamics, and policy modes improves inverse dynamics accuracy and policy coverage compared to single-mode checkpoints, with only a modest tradeoff in forward dynamics reconstruction fidelity. (confidence: 1.00)
  Evidence: The joint FD/ID/policy checkpoint improves the action-side metrics while preserving comparable forward-dynamics quality. ... ID MSE decreases ... and policy coverage increases ... FD PSNR decreases ... indicating a modest tradeoff in reconstruction fidelity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/cosmos-3/source.tex

## DB-3DME: From Dataset to Benchmark for Human-aligned Automatic 3D Mesh Evaluation

`db-3dme` | authors: Nanshan Jia, Zhenyu Zhao, Sui Huang, Jingshen Wang, Zeyu Zheng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit, https://github.com/nsjia/DB-3DME

No research facts available.

## Diff-CA: Separating Common and Salient Factors with Diffusion Models

`diff-ca` | authors: Michaël Soumm, Alexandre Fournier Montgieux, Yunlong He, Pietro Gori, Alasdair Newson | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/konpatp/diffae

### Method

- The proposed method applies Contrastive Analysis directly to the conditioning token sequence of a latent diffusion architecture, decomposing it into common and salient factors. (confidence: 1.00)
  Evidence: Our method applies CA directly to the conditioning token sequence $Z$ of a latent diffusion architecture.
We learn a decomposition $Z \mapsto (\hat{Z}_C, \hat{Z}_S)$ such that $\hat{Z}_C$ captures the common factor shared across distributions ($C$), while $\hat{Z}_S$ isolates the salient factor specific to the target distribution ($S$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/source.tex
- The framework first trains a prompt-free, image-conditioned diffusion model and then uses weak supervision to decompose the conditioning into common and salient factors. (confidence: 1.00)
  Evidence: We first train a prompt-free, image-conditioned diffusion model, and then learn to decompose the conditioning into a common and a salient factor, using weak supervision. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/summary.md

### Claim

- The authors prove that the additive contrastive factorization, commonly assumed in prior work, is identifiable under mild conditions. (confidence: 1.00)
  Evidence: We prove that the additive contrastive factorization, commonly assumed in prior work, is identifiable under mild conditions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/summary.md
- Existing contrastive methods based on generative models like VAEs or GANs often suffer from limited reconstruction and image quality, which hampers effective latent factor separation. (confidence: 1.00)
  Evidence: Existing contrastive methods are based on generative models (e.g., VAEs or GANs) that often suffer from limited reconstruction and image quality, which hampers effective latent factor separation and limits their applicability to high-fidelity image generation and edition. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/summary.md
- The learned factorization enables targeted operations such as swapping or interpolating only the salient factor. (confidence: 1.00)
  Evidence: This factorization enables targeted operations by swapping or interpolating only the salient factor. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/summary.md

### Limitation

- Text-driven diffusion editors often rely on heuristics that are sensitive to prompt choices, can introduce unintended changes, and cannot be applied when salient patterns are difficult to describe or unknown. (confidence: 1.00)
  Evidence: CA thus provides an alternative to text-driven diffusion editors, which often rely on prompt/inversion/attention heuristics
\cite{hertzprompt,brooks2023instructpix2pix,mokady2023null,parmar2023zero} that can be sensitive to prompt/guidance choices, introduce unintended changes
%outside the intended factor 
, %or be impractical in certain settings, 
or that cannot be applied when salient patterns are difficult to describe or are unknown. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff-ca/source.tex

## Diff2SP: Diffusion Models for Correlated Scenario Generation in Stochastic Programming

`diff2sp` | authors: Haixiang Sun, Andrew Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/PERFORM-Forecasts/documentation

### Method

- Diff2SP is a diffusion-based generative framework that incorporates downstream optimization objectives directly into scenario generation for stochastic programming. (confidence: 1.00)
  Evidence: To address these limitations, we introduce Diff2SP, a diffusion-based generative framework that incorporates downstream optimization objectives directly into scenario generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- Diff2SP combines conditional diffusion models with transformer-based architectures to capture temporal dependencies and cross-variable correlations. (confidence: 1.00)
  Evidence: Diff2SP combines conditional diffusion models with transformer-based architectures to learn structured uncertainty distributions directly from data. By incorporating self-attention within the denoising process, the framework captures temporal dependencies and cross-variable correlations [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- Diff2SP incorporates the downstream stochastic optimization problem into training through a differentiable optimization layer. (confidence: 1.00)
  Evidence: A distinguishing feature of Diff2SP is that the downstream stochastic optimization problem is incorporated into training through a differentiable optimization layer. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex

### Dataset

- The empirical results of Diff2SP are validated on both synthetic and power-system datasets. (confidence: 1.00)
  Evidence: Empirical results on both synthetic and power-system datasets validate these theoretical insights [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex

### Claim

- The authors establish regret bounds that link distributional accuracy to decision quality to formally justify the optimization-aware design. (confidence: 1.00)
  Evidence: To formally justify this optimization-aware design, we establish a regret bounds that link distributional accuracy to decision quality [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- The authors establish sample complexity guarantees showing faster convergence for optimization-aware scenario generation than traditional generative models such as GANs. (confidence: 1.00)
  Evidence: and establish sample complexity guarantees showing faster convergence than traditional generative models such as GANs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex

### Limitation

- Sampling-based techniques for scenario generation often struggle to capture complex dependencies and rare but plausible events. (confidence: 1.00)
  Evidence: Sampling-based techniques often struggle to capture complex dependencies and rare but plausible events [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- Supervised learning for scenario generation requires fixed input-output pairs for training and is limited in generating a wide variety of realistic scenarios not restricted by predefined patterns. (confidence: 1.00)
  Evidence: while supervised learning requires fixed input-output pairs for training and is limited in its ability to generate a wide variety of realistic scenarios that are not restricted by predefined patterns or rules. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- GANs provide no explicit likelihood or density estimate, making it difficult to assess if generated scenarios represent tail events, and adversarial training is often unstable. (confidence: 1.00)
  Evidence: First, GANs provide no explicit likelihood or density estimate, making it difficult to assess whether the generated scenarios faithfully represent tail events and cross-variable dependence. Second, adversarial training is often unstable [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex
- Sampling in diffusion models is iterative and therefore more expensive at inference than a single forward pass. (confidence: 1.00)
  Evidence: sampling is iterative and therefore more expensive at inference than a single forward pass [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/diff2sp/source.tex

## DisCo: World Models with Discrete Camera Motion Control

`disco` | authors: Hongrui Huang, Junke Wang, Quanhao Li, Yu-Gang Jiang, Zuxuan Wu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Dive into the Scene: Breaking the Perceptual Bottleneck in Vision-Language Decision Making via Focus Plan Generation

`2606_04046` | authors: Boyuan Xiao, Bohong Chen, Yumeng Li, Ji Feng, Yao-Xiang Ding, Kun Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- SceneDiver is a coarse-to-fine focus plan generation method for VLMs that constructs a holistic scene graph for initial comprehension and progressively decomposes tasks into simpler sub-problems through an iterative cycle of recognition, understanding, and analysis. (confidence: 1.00)
  Evidence: we propose {\it SceneDiver}, a coarse-to-fine focus plan generation method for VLMs leveraging their long-term planning abilities, that first constructs a holistic scene graph to establish initial comprehension, then progressively decomposes the task into simpler sub-problems through an iterative cycle of recognition, understanding, and analysis. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- The authors designed a lightweight adapter to distill the deliberate focus ability of SceneDiver into Vision-Language-Action (VLA) models to enable reactive control while maintaining inference efficiency. (confidence: 1.00)
  Evidence: To enable reactive control, we also design a lightweight adapter for distilling the deliberate focus ability into VLAs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- In the coarse-grained plan stage of SceneDiver, raw image data is converted into structured scene graphs, and graph reasoning is performed to decompose the global scene into simpler local sub-scenes. (confidence: 1.00)
  Evidence: At the first coarse-grained plan stage, we convert raw image data into structured graph representations by constructing scene graphs. Graph reasoning is then performed over the constructed graph, decomposing the complex global scene into a series of simpler local sub-scenes corresponding to individual nodes in the graph. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- In the fine-grained plan stage of SceneDiver, VLMs autonomously explore each local sub-scene to discover task-relevant objects, and the visual input is refined using these identified objects before the final decision. (confidence: 1.00)
  Evidence: At the second fine-grained plan stage, VLMs are requested to autonomously explore each local sub-scene in agentic manner to discover task-relevant objects. Finally, the visual input is refined using the objects identified and fed to the VLM for the final decision. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex

### Benchmark

- The LIBERO-plus benchmark is used in the study to evaluate the robustness of Vision-Language-Action (VLA) models against environmental interference. (confidence: 1.00)
  Evidence: we also evaluate our method on the LIBERO-plus benchmark~\citep{fei2025liberoplusindepthrobustnessanalysis} (which is employed to evaluate the robustness of the VLA against environmental interference). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex

### Claim

- SceneDiver achieves a 10% to 15% performance gain in robotic manipulation tasks and up to a 16% improvement in room navigation tasks compared to existing visual focus approaches. (confidence: 1.00)
  Evidence: The results demonstrate that our method achieves a 10\%–15\% performance gain in manipulation tasks and up to a 16\% improvement in navigation, outperforming existing visual focus approaches. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- On the LIBERO-plus benchmark, SceneDiver achieves up to a 9.6% improvement in success rate while adding only a 2.64% computational overhead. (confidence: 1.00)
  Evidence: Experimental results demonstrate that our method achieves up to a 9.6\% improvement in success rate, enhancing decision-making robustness while incurring a marginal computational overhead of only 2.64\%. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex

### Limitation

- The performance of Vision-Language Models (VLMs) and Vision-Language-Action Models (VLAs) in embodied decision making is limited by a perceptual bottleneck where visual hallucinations occur because the models cannot distinguish task-relevant objects from distractors. (confidence: 1.00)
  Evidence: However, their performance is limited by the same perceptual bottleneck: visual hallucinations arise due to the models’ inability to distinguish task-relevant objects from distractors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex
- A straightforward one-step focus approach, which directly attends to essential objects, is ineffective for embodied decision making because effective focus inherently requires deep scene understanding. (confidence: 1.00)
  Evidence: A straightforward solution is one-step focus: directly attending to essential objects. However, this approach proves ineffective because effective focus inherently requires deep scene understanding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04046/source.tex

## Do VLMs Reason Like Engineers? A Benchmark and a Stage-wise Evaluation

`2606_10833` | authors: Syed Wasiq, Syed Mohamad Tawseeq, Yashwant Pravinrao Bangde, Debaditya Roy | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors introduce an 8-stage automatic evaluation framework for assessing VLM-generated solutions, which independently evaluates each stage to enable fine-grained analysis of reasoning failures. (confidence: 1.00)
  Evidence: We introduce an 8-stage automatic evaluation framework for assessing VLM-generated solutions. The framework independently evaluates each stage of the solution, enabling fine-grained analysis of reasoning failures. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex
- Before designing the evaluation framework, the authors conducted a systematic pilot error analysis across three engineering subjects: Fluid Mechanics, Heat and Mass Transfer (HMT), and Mechanics of Materials (MOM). (confidence: 1.00)
  Evidence: Before designing the evaluation framework, we conducted a systematic pilot error analysis across three engineering subjects: Fluid Mechanics, Heat and Mass Transfer (HMT), and Mechanics of Materials (MOM). [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex

### Benchmark

- The authors introduce EngVQA, a multimodal benchmark for evaluating engineering reasoning across 5 engineering subjects containing 696 problems. (confidence: 1.00)
  Evidence: We introduce EngVQA, a multimodal benchmark for evaluating engineering reasoning across 5 engineering subjects containing 696 problems. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/summary.md

### Claim

- Human evaluation shows strong agreement with the automated framework, achieving a Pearson correlation of 0.975 and a mean absolute error of 0.67 on a 10-point grading scale. (confidence: 1.00)
  Evidence: Human evaluation shows strong agreement with our automated framework, achieving a Pearson correlation of 0.975 and a mean absolute error of 0.67 on a 10-point grading scale. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex
- Arithmetic-related failures were among the most frequent observed error categories across the pilot subjects, occurring 49 times in Fluid Mechanics, 45 times in HMT, and 80 times in MOM. (confidence: 1.00)
  Evidence: Across all three pilot subjects, arithmetic-related failures were among the most frequent observed error categories, occurring 49 times in Fluid Mechanics, 45 times in HMT, and 80 times in MOM [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex
- Visual misinterpretation is a structurally independent failure mode requiring its own evaluation step, as several topics scored above 0.55 on the visual error susceptibility score. (confidence: 1.00)
  Evidence: This led us to concluding that visual misinterpretation is a structurally independent failure mode requiring its own evaluation step. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex

### Limitation

- The authors cannot fully rule out benchmark contamination from model pretraining data, though the benchmark's emphasis on multimodal understanding and multi-step reasoning makes direct memorization insufficient. (confidence: 1.00)
  Evidence: We cannot fully rule out benchmark contamination from model pretraining data. However, the benchmark emphasizes multimodal understanding and multi-step engineering reasoning, making direct memorization alone insufficient. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex
- The evaluation framework requires 11 LLM judge calls per solution, making it significantly more computationally expensive and potentially limiting scalability in resource-constrained settings. (confidence: 1.00)
  Evidence: Our framework requires 11 LLM judge calls per solution, making evaluation significantly more computationally expensive. Although KV caching can reduce redundant computation \citep{pope2022efficientlyscalingtransformerinference}, evaluation cost may still limit scalability in large-scale or resource-constrained settings. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex
- EngJudge inherits known limitations of LLM-as-a-judge evaluation, including potential biases and imperfect alignment with human judgment. (confidence: 1.00)
  Evidence: EngJudge inherits known limitations of LLM-as-a-judge evaluation, including potential biases and imperfect alignment with human judgment. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10833/source.tex

## Do Vision-Language Models See Dwarf Galaxies the Way We Do?

`2606_07779` | authors: Dimitrios Tanoglidis, Chin Yi Tan, Kate Overdeck, Alex Drlica-Wagner | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/dtanoglidis/Zooniverse-Dwarf-Multimodal

### Method

- The researchers used the multimodal GPT-5-mini model for all experiments. (confidence: 1.00)
  Evidence: In this work, we use the multimodal GPT-5-mini model for all experiments. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- The study employed a zero-shot prompting setup using text-only instructions to distinguish genuine dwarf galaxies from artifacts. (confidence: 1.00)
  Evidence: We focus on a zero-shot prompting setup, using text-only instructions that describe how to distinguish genuine dwarf galaxies from artifacts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex

### Dataset

- The study uses images and annotations from a Zooniverse campaign aimed at discovering ultra-faint Milky Way satellite galaxies in the wide-field DELVE survey. (confidence: 1.00)
  Evidence: We use images and annotations from a recently completed Zooniverse campaign aimed at discovering ultra-faint Milky Way satellite galaxies in the wide-field DELVE survey, which covers $\sim 20{,}000,\mathrm{deg}^2$ of the southern sky [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- The Zooniverse campaign presented 46,334 subjects to over 1,650 human volunteers, resulting in over 1.1 million classifications. (confidence: 1.00)
  Evidence: The campaign presented 46,334 subjects to more than 1,650 human volunteers. Each subject received multiple (25) independent votes, resulting in over 1.1 million classifications. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex

### Claim

- Zero-shot VLMs closely reproduce aggregate human calibration and perform well on less ambiguous cases. (confidence: 1.00)
  Evidence: We find that zero-shot VLMs closely reproduce aggregate human calibration and perform well on less ambiguous cases. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- The VLM correctly identified 55 out of 57 known dwarf galaxies. (confidence: 1.00)
  Evidence: Furthermore, the model correctly identifies 55/57 known dwarfs, with the two failures corresponding to challenging cases, even for humans. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- On a high-confidence subset of human votes, the VLM achieved 95% precision and 89% recall. (confidence: 1.00)
  Evidence: On this subset, the VLM achieves $95\%$ precision and $89\%$ recall (Fig. \ref{fig:figure3}a), consistent with prior work on clear, less-ambiguous astronomical classification problems. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex

### Limitation

- There is significant variability at the level of individual examples, and attempts to obtain uncertainty estimates fail to yield reliable measures. (confidence: 1.00)
  Evidence: However, there is significant variability at the level of individual examples, and attempts to obtain uncertainty estimates (via self-reported confidence or repeated inference) fail to yield reliable and practically useful measures. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- The model's self-reported confidence assigned 'High' confidence to only a small fraction of examples classified as Dwarf, limiting practical utility. (confidence: 1.00)
  Evidence: However, only a small fraction (135 of those classified as Dwarf) of the examples are assigned High confidence, limiting their practical utility. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex
- Estimating uncertainty via repeated inference is poorly calibrated, as each VLM bin contains a broad spread of human votes. (confidence: 1.00)
  Evidence: Here, while the mean human vote fraction increases with VLM "Dwarf" classification frequency, the mapping is not well calibrated: each VLM bin contains a broad spread of human votes (low $\%$ and high $\%$), reducing its usefulness as a probabilistic estimate. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07779/source.tex

## Do Vision-Language Models See or Guess? Measuring and Reducing Textual-Prior Reliance with a Phrasing-Controlled Benchmark

`2606_10400` | authors: Pratham Singla, Shivank Garg, Vihan Singh, Paras Chopra | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The benchmark generates four question variants for each image: Question-Guided, Subquestion-Guided, Multi-Signal, and Vision-Grounded, ordered by decreasing reliance on the source text. (confidence: 1.00)
  Evidence: Question-Guided    & Rewrite the source question into a harder, image-dependent form \\
Subquestion-Guided & Synthesize perceptual sub-questions in a single pass \\
Multi-Signal       & Fuse the source question with chat-elicited sub-questions \\
Vision-Grounded    & Generate directly from the image, with no source text \\ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- The study uses a no-image ablation as a central diagnostic to measure VLMs' reliance on textual priors, which collapses open-weight models to a 1 to 9 percent text-only floor. (confidence: 1.00)
  Evidence: Our central diagnostic is a no-image ablation, which collapses the open-weight models to their text-only floor (1 to 9 percent). [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- The researchers applied GRPO post-training to a small VLM, which yielded consistent accuracy gains across all four question variants and transferred to a held-out out-of-distribution set. (confidence: 1.00)
  Evidence: GRPO post-training of a small VLM yields consistent gains across all four variants that transfer to a held-out out-of-distribution set. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex

### Benchmark

- The authors built a 540-image benchmark across six reasoning categories, generating four question variants over the same images to control for phrasing rather than image content. (confidence: 1.00)
  Evidence: we build a 540-image benchmark across six reasoning categories and generate four question variants over the same images, so that phrasing rather than image content is the controlled variable. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- The benchmark includes 540 samples per variant, distributed across OCR, Chart/Graphic Understanding, Common Sense & Physics, Spatial & Scene Reasoning, Visual Reasoning, and Visual Math Reasoning. (confidence: 1.00)
  Evidence: OCR & 72 \\
Chart / Graphic Understanding & 120 \\
Common Sense \& Physics & 79 \\
Spatial \& Scene Reasoning & 94 \\
Visual Reasoning & 155 \\
Visual Math Reasoning & 20 \\
\midrule
\textbf{Total (per variant)} & \textbf{540} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex

### Claim

- Vision-language models often rely on textual priors, such as the question's phrasing and memorized world knowledge, rather than the image itself, which inflates benchmark scores. (confidence: 1.00)
  Evidence: they often answer from textual priors, the question's phrasing together with memorized world knowledge, rather than from the image itself, which inflates benchmark scores and yields confident but ungrounded answers. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- Every evaluated model degrades on the hardest, image-derived Vision-Grounded variant, with open-weight models falling to 10-16% accuracy while proprietary models maintain 27-38%. (confidence: 1.00)
  Evidence: Vision-Grounded is uniformly the hardest variant; open models fall to 10--16\% on it while proprietary models stay at 27--38\%. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- In-context exemplars recover the most accuracy when their type matches how a specific question variant was constructed. (confidence: 1.00)
  Evidence: In-context exemplars help most when their \emph{type matches} how a variant was constructed [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex
- Textual-prior reliance in vision-language models is a measurable trait that can be partially reduced through training. (confidence: 1.00)
  Evidence: Textual-prior reliance is measurable and partly trainable away. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10400/source.tex

## EasyLens: A Training-Free Plug-and-Play Subtle-Lesion Representation Amplifier for Medical Vision-Language Models

`easylens` | authors: Qiwei Zeng, Hao Wang, Jinghao Lin, Shuchang Ye, Yuezhe Yang, Yige Peng, Haoyuan Che, Jinman Kim, Lei Bi | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- EasyLens is a training-free plug-and-play subtle-lesion representation amplifier designed for medical vision-language models. (confidence: 1.00)
  Evidence: we propose EasyLens, a training-free plug-and-play subtle-lesion representation amplifier for medical VLMs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex
- EasyBank is a pathology-anatomy prototype space constructed by EasyLens that provides lesion-related prototypes and anatomy-aware normal references for patch-level comparison. (confidence: 1.00)
  Evidence: EasyLens first constructs EasyBank, a pathology-anatomy prototype space that provides lesion-related prototypes and anatomy-aware normal references for comparing suspicious patches against both pathological and normal anatomical patterns. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex
- EasyTag is a module that selects lesion-relevant patches through counterfactual prototype reasoning to prevent the blind amplification of normal tissues. (confidence: 1.00)
  Evidence: To avoid blindly amplifying normal tissues, EasyTag selects lesion-relevant patches through counterfactual prototype reasoning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex
- EasyAmplifier strengthens selected lesion-relevant patch representations using morphology-guided residual enhancement to increase their contribution to the global image embedding. (confidence: 1.00)
  Evidence: EasyAmplifier strengthens the selected lesion-relevant patch representations through morphology-guided residual enhancement, thereby increasing their contribution to the global image embedding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex

### Benchmark

- EasyLens is validated on a unified subtle-lesion benchmark constructed from the ReXGroundingCT, LIDC-IDRI, and AbdomenAtlas 3.0 Mini datasets. (confidence: 1.00)
  Evidence: We validate EasyLens on a unified subtle-lesion benchmark built from ReXGroundingCT, LIDC-IDRI, and AbdomenAtlas 3.0 Mini. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex

### Claim

- Experiments across multiple frozen medical VLM backbones demonstrate that EasyLens consistently improves subtle-lesion detection and report generation, outperforming existing encoder-enhancement baselines without requiring model fine-tuning. (confidence: 1.00)
  Evidence: Experiments across multiple frozen medical VLM backbones show that EasyLens consistently improves subtle-lesion detection and report generation, and outperforms existing encoder-enhancement baselines without model fine-tuning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex

### Limitation

- Existing approaches to improve lesion sensitivity in medical VLMs typically require additional training or model-specific adaptation, and may overfit to specific disease morphologies, which limits their applicability to frozen models. (confidence: 1.00)
  Evidence: Although effective, these approaches usually require additional training or model-specific adaptation and may overfit to particular disease morphologies, limiting their applicability to frozen medical VLMs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex
- Subtle lesions provide weak local evidence that can become underrepresented when local visual tokens are aggregated into global image representations, causing medical VLMs to miss them. (confidence: 1.00)
  Evidence: As local visual tokens are aggregated into global image representations, these weak lesion cues may become underrepresented, causing medical VLMs to miss or under-recognize subtle abnormalities [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/easylens/source.tex

## EditSSC: Toward Editable Semantic Occupancy Scenes with Unconditional Diffusion Models

`editssc` | authors: Fatima Balde, Raoul de Charette, Alexandre Boulch | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- EditSSC generates 3D semantic scenes using 2D Bird's Eye View (BEV) representations and an off-the-shelf latent diffusion network. (confidence: 1.00)
  Evidence: We propose EditSSC, an editing-ready method for 3D semantic scene generation using 2D Bird's Eye View (BEV) representations and off-the-shelf latent diffusion network. [sec/0_abstract.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/summary.md
- The method reshapes 3D semantic occupancy grids into multi-channel BEV images and uses the quantized autoencoder and UNet from Stable Diffusion. (confidence: 1.00)
  Evidence: Our approach reshapes 3D semantic occupancy grids into multi-channel BEV images and leverages the quantized autoencoder and UNet from Stable Diffusion with minimal modifications. [sec/0_abstract.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- EditSSC performs diffusion on latents after quantization, enabling training-free editing capabilities like sketch-guided generation, inpainting, and outpainting. (confidence: 1.00)
  Evidence: We perform diffusion on the latents after quantization, which enables training-free editing capabilities. By exploiting class-to-code correspondences in the codebook, our method supports sketch-guided generation, inpainting, and outpainting without any retraining. [sec/0_abstract.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- The pilot study evaluates a vector-quantized VAE (VQ-VAE) using BEV representation as an alternative to the original SemCity autoencoder. (confidence: 1.00)
  Evidence: We then replace the original SemCity autoencoder with a vector-quantized VAE (VQ-VAE), using BEV representation. [sec/3_method.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex

### Dataset

- EditSSC is evaluated on the SemanticKITTI dataset for unconditional scene generation. (confidence: 1.00)
  Evidence: On SemanticKITTI, EditSSC outperforms existing 3D-specific baselines on unconditional generation [sec/0_abstract.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/summary.md

### Claim

- Well-established 2D architectures can be effectively repurposed for 3D scene generation and editing. (confidence: 0.95)
  Evidence: demonstrating that well-established 2D architectures can be effectively repurposed for 3D scene generation and editing. [sec/0_abstract.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- The organization and structure of the latent space are more critical for diffusion quality than autoencoder reconstruction performance alone. (confidence: 0.95)
  Evidence: our observations suggest that the organization of the latent space is more crucial for better diffusion than reconstruction performance alone [sec/1_intro.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- Bird's Eye View (BEV) is a natural representation choice for editing driving scenes because objects are rarely stacked and scenes are mainly spread along two axes. (confidence: 0.95)
  Evidence: Instead, Bird's Eye View (BEV) appears to be a natural choice, since driving scenes are mainly spread along two axes as objects are rarely stacked. [sec/3_method.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex
- High reconstruction fidelity paired with an unstructured latent space, such as that produced by a simple MLP, is detrimental to diffusion performance. (confidence: 0.95)
  Evidence: This confirms that high reconstruction fidelity with an unstructured latent space is detrimental to diffusion [sec/3_method.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex

### Limitation

- The SemanticKITTI dataset has limited diversity, as its training set contains only 10 sequences from the same German neighborhoods. (confidence: 1.00)
  Evidence: SemanticKITTI~\cite{semantickitti}, the most popular SSC dataset, is no exception since its training set consists of only  10 sequences from the same German neighborhoods. [sec/3_method.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/editssc/source.tex

## ExDet: Open-Domain Open-Vocabulary Detection with Cross-modal Extrapolation and Rectification

`exdet` | authors: Yupeng Zhang, Yuzhong Feng, Ruize Han, Zhiwei Chen, Wei Feng, Liang Wan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- ExDet is a lightweight category-domain collaborative generalization framework for Open-Domain Open-Vocabulary Detection (ODOVD) that consists of Text-Guided Extrapolation (TGE), Detector-Compatible Rectification (DCR), and ExRPN. (confidence: 1.00)
  Evidence: we propose ExDet, a lightweight category-domain collaborative generalization framework for ODOVD that enhances the cross-category and cross-domain generalization of existing detectors. ExDet consists of Text-Guided Extrapolation (TGE), a lightweight Detector-Compatible Rectification (DCR) module, and ExRPN. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- Text-Guided Extrapolation (TGE) leverages the DeltaSpace property of vision-language models to infer proxy visual prototypes that are aware of both category and domain directly from text. (confidence: 1.00)
  Evidence: Specifically, TGE exploits the DeltaSpace property of vision-language models (VLMs) to infer category- and domain-aware proxy visual prototypes from text. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- Detector-Compatible Rectification (DCR) is trained without real data or detector training using TGE-generated prototypes, and is applied after the classification head during inference to align representations to a detector-compatible source-domain visual distribution. (confidence: 1.00)
  Evidence: DCR is learned from the TGE-generated prototypes in a detector training-free and real-data-free manner, and is inserted after the classification head at inference to rectify representations toward a detector-compatible source-domain visual distribution [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- ExRPN improves the recall of novel and domain-shifted objects by recalibrating proposal scores through a combination of semantic similarity and RPN confidence. (confidence: 1.00)
  Evidence: ExRPN recalibrates proposal scores by combining semantic similarity with RPN confidence, improving recall for novel and domain-shifted objects while providing better support for subsequent classification and DCR. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex

### Benchmark

- The ExDet framework is evaluated on the OD-LVIS, OV-LVIS, Objects365, and MSOSB benchmarks. (confidence: 1.00)
  Evidence: ExDet achieves SOTA performance on OD-LVIS, OV-LVIS, Objects365, and MSOSB. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex

### Claim

- ExDet achieves state-of-the-art performance on the OD-LVIS, OV-LVIS, Objects365, and MSOSB datasets. (confidence: 1.00)
  Evidence: ExDet achieves SOTA performance on OD-LVIS, OV-LVIS, Objects365, and MSOSB. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex

### Limitation

- Existing open-domain open-vocabulary detection methods incur high training costs because they typically require training open-vocabulary detectors and domain generalization modules jointly from scratch. (confidence: 1.00)
  Evidence: Existing methods typically train open-vocabulary detectors together with domain generalization modules from scratch, leading to high training cost. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex
- In two-stage detectors, the Region Proposal Network (RPN) struggles to generate high-quality, high-confidence proposals for novel or domain-shifted objects because it is trained exclusively on base-category annotations from the source domain. (confidence: 1.00)
  Evidence: In practice, the Region Proposal Network (RPN) is trained only on base-category annotations from the source domain, and thus often struggles to produce high-quality, high-confidence proposals for novel or domain-shifted objects. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/exdet/source.tex

## Explicit Representation Alignment for Multimodal Sentiment Analysis

`2606_09148` | authors: Baode Wang, Ziming Wang, Huacan Wang, Ronghao Chen, Biao Wu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed framework leverages vision-language models (VLMs) to convert visual content into structured textual descriptions, projecting heterogeneous modalities into a shared linguistic space for interpretable text-centric reasoning. (confidence: 0.95)
  Evidence: we propose a unified multimodal affective analysis framework that leverages vision-language models (VLMs) to convert visual content into structured textual descriptions, projecting heterogeneous modalities into a shared linguistic space and enabling interpretable text-centric reasoning. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/summary.md
- To improve robustness and mitigate noise from VLM-generated descriptions, the authors introduce a hybrid learning strategy combining semantic token selection with a batch-level uniformity regularization objective. (confidence: 0.95)
  Evidence: we introduce a hybrid learning strategy that combines semantic token selection with a batch-level uniformity regularization objective, encouraging a more dispersed and stable global feature space while mitigating noise introduced by VLM-generated descriptions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex

### Benchmark

- The paper references several influential benchmarks for multimodal affective computing, including MOSI and MOSEI for sentiment analysis, MELD and IEMOCAP for emotion recognition, and Multi-ZOL and MUStARD for fine-grained sentiment and sarcasm detection. (confidence: 0.90)
  Evidence: several influential benchmarks have been released, including MOSI/MOSEI~\citep{jia2022beyond,zadeh2018multimodal} for sentiment analysis, MELD/IEMOCAP~\citep{poria2019meld,busso2008iemocap} for emotion recognition in multi-party conversations, and task-specific datasets such as Multi-ZOL and MUStARD [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex

### Claim

- Multimodal models often fail to consistently outperform strong text-only baselines, and their performance varies significantly depending on the fusion strategy used. (confidence: 0.95)
  Evidence: multimodal models often fail to consistently outperform strong text-only baselines, with performance varying significantly across fusion strategies. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex
- Representation misalignment between independently pretrained modality encoders is identified as a key bottleneck for effective multimodal learning, making alignment prior to fusion often more important than fusion complexity. (confidence: 0.95)
  Evidence: we identify representation misalignment between independently pretrained modality encoders as a key bottleneck for effective multimodal learning, and show through controlled experiments that alignment prior to fusion is often more important than fusion complexity. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex
- The proposed method achieves state-of-the-art performance and consistently outperforms strong unimodal and multimodal baselines on multiple multimodal sentiment and emotion benchmarks. (confidence: 0.95)
  Evidence: Experiments on multiple multimodal sentiment and emotion benchmarks show that our method consistently outperforms strong unimodal and multimodal baselines, achieving state-of-the-art performance. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex
- Feature misalignment between modalities can lead to modality bias, which consequently degrades the overall performance of multimodal models. (confidence: 0.90)
  Evidence: offering empirical evidence that feature misalignment can lead to \textbf{modality bias} and consequently degrade model performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09148/source.tex

## FATE-VLA:Failue-aware test generation for vision-language-action models

`fate-vla` | authors: Arusa Kanwal, Pablo Valle, Shaukat Ali, Aitor Arrieta | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- FATE-VLA proposes a failure-aware test-generation approach combining diversity-driven exploration with surrogate models learned from observed executions. (confidence: 1.00)
  Evidence: We reframe VLA evaluation as an active failure-discovery problem and propose a failure-aware test-generation approach that combines diversity-driven exploration with surrogate models learned from observed executions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex
- The approach introduces trajectory-level and object-level failure diversity metrics to characterize the heterogeneity of discovered weaknesses beyond conventional success rates. (confidence: 1.00)
  Evidence: Beyond failure rate, we introduce trajectory-level and object-level failure diversity metrics to characterize the heterogeneity of discovered weaknesses. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex
- The first test-generation algorithm augments FSCS-ART with a surrogate model to prioritize candidates predicted to fail, while the second uses Random Forest failure probabilities within an adaptive exploration-exploitation scoring function. (confidence: 1.00)
  Evidence: The first augments FSCS-ART with a surrogate model that prioritizes candidates predicted to fail in subsection ~\ref{sec:algo1}, while the second uses Random Forest failure probabilities within an adaptive exploration–exploitation scoring function in subsection ~\ref{sec:algo2}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex
- The Hybrid Sorted Surrogate Assisted FSCS-ART algorithm uses the Euclidean distance metric to compute the minimum distance to previously executed scenes to promote test input diversity. (confidence: 1.00)
  Evidence: For each candidate $c \in C$, the minimum distance to previously executed scenes in $S$ is computed using the Euclidean distance metric, $dist(c,s) = \sqrt{\sum_{j=1}^{m}(c_j - s_j)^2}$, where $m$ denotes the number of scene features. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex

### Claim

- FATE-VLA uncovers up to 29.7% more failures over selected baselines across four state-of-the-art VLA models while revealing more diverse failure modes. (confidence: 1.00)
  Evidence: Across four state-of-the-art VLA models, it uncovers substantially more failures (up to +29.7 % over selected baselines) while revealing more diverse failure modes. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/summary.md
- When evaluated with FATE-VLA, the success rate of the GR00T-N1.6 model dropped from 64.4% to 34.7%. (confidence: 1.00)
  Evidence: This means that, for instance, in the case of GR00T-N1.6, success rate dropped from 64.4\% to 34.7\%. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex
- Static benchmarking is limited in high-dimensional embodied spaces because failures are sparse, non-uniform, and clustered, meaning naive sampling can underestimate robustness risks. (confidence: 1.00)
  Evidence: Such static benchmarking is limited in high-dimensional embodied interaction spaces, where scene configurations vary across object identities, spatial layouts, orientations, and instruction semantics. Failures in such spaces are often sparse, non-uniform, and clustered in specific regions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fate-vla/source.tex

## FMRFusion: Frequency-Aware Multi-View Representation Learning for Heterogeneous Image Fusion

`fmrfusion` | authors: Tao Zhoua, Yunlong Liu, Qinghui Chen, Zekai Zhang, Minlong Sun, Changlin Biana, Dagang Li, Wenmin Wang, Jinglin Zhang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- FMRFusion is a frequency-aware multi-view representation learning network designed for heterogeneous image fusion. (confidence: 1.00)
  Evidence: To address these challenges, we propose FMRFusion, a frequency-aware multi-view representation learning network for Heterogeneous Image Fusion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- The method introduces a Multi-Scale Structural Perception Module to capture discriminative structures, extracting fine-grained local structures and contextual information. (confidence: 1.00)
  Evidence: A Multi-Scale Structural Perception Module is introduced to effectively capture discriminative structures, extracting fine-grained local structures and essential contextual information. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- FMRFusion employs a bilinear frequency decomposition mechanism to separate features into high and low-frequency components for joint modeling of local details and global representations. (confidence: 1.00)
  Evidence: A bilinear frequency decomposition mechanism is employed to separate features into high-frequency and low-frequency components, enabling joint modeling of local details and global representations across different frequency domains. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- The network incorporates a Cross-View Complementary Interaction to fuse complementary characteristics between reflected light information and radiative intensity responses. (confidence: 1.00)
  Evidence: Moreover, a Cross-View Complementary Interaction is incorporated to explicitly model and fuse the complementary characteristics between reflected light information and radiative intensity responses, facilitating effective cross-view interaction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- FMRFusion uses flow matching to progressively refine fused features by learning the transformation from coarse data to high-quality representations. (confidence: 1.00)
  Evidence: We further improve the performance of the fused results by flow matching, which progressively refines the fused features by learning the transformation from coarse data to high-quality representations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- The proposed approach utilizes a Dual-Branch Hybrid Architecture that combines the efficiency of CNNs with the global modeling capabilities of Transformers to form independent branches for different modalities. (confidence: 1.00)
  Evidence: This work combines the efficiency of CNNs with the global modeling capabilities of Transformers to form independent branches for different modalities, thus avoiding feature interference during encoding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex

### Claim

- Experiments on multiple benchmark datasets show that FMRFusion achieves superior and consistent performance across various fusion tasks, particularly in nighttime scenarios. (confidence: 1.00)
  Evidence: Extensive experiments conducted on multiple benchmark datasets demonstrate that FMRFusion achieves superior and consistent performance across a range of fusion tasks, especially in nighttime scenarios. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex

### Limitation

- Previous image fusion methods often use a single-module stacking approach, which leads to incomplete learning of distinct modality characteristics and limits robustness in real-world scenarios. (confidence: 1.00)
  Evidence: Previous image fusion methods typically adopt a single-module stacking approach to extract features from the two modalities. However, these approaches may result in incomplete learning of their distinct characteristics, thereby limiting the fusion effectiveness and constraining robustness in real-world heterogeneous data scenarios. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- CNN-based methods struggle to model long-range dependencies due to their small receptive fields, limiting their ability to capture deep and global features. (confidence: 1.00)
  Evidence: although CNNs excel at extracting local features, their small receptive fields make it challenging to model long-range dependencies, thereby limiting their ability to capture deep and global features of the source image [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex
- Single-path deep learning architectures that concatenate inputs prematurely cause information interference between modalities and lead to the loss of unique information. (confidence: 1.00)
  Evidence: most deep learning-based algorithms first connect the source images and feed them into a single-path network, without a separate feature extraction branch for each input image, leading to the loss of unique information [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fmrfusion/source.tex

## Few-step Generative Models as Lossy Compression

`2606_10450` | authors: Fuma Kimishima, Jinjia Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Kim-Dongjun/ctm-cifar10, https://github.com/openai/guided-diffusion, https://github.com/openai/improved-diffusion, https://github.com/sangyun884/rfpp, https://github.com/sony/ctm, https://github.com/zhuyu-cs/MeanFlow

### Method

- The paper investigates casting few-step generative models, specifically Rectified Flow, Consistency Trajectory Models (CTM), and MeanFlow, as codecs within the reverse channel coding (RCC) framework. (confidence: 1.00)
  Evidence: We study whether few-step generative models -- Rectified Flow, Consistency Trajectory Models (CTM), and MeanFlow -- can be cast as codecs within the same reverse channel coding (RCC) framework. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- For Rectified Flow and MeanFlow, the method derives the quantities required by RCC using the equivalence between velocity parameterization and diffusion-style denoising parameterization. (confidence: 1.00)
  Evidence: For Rectified Flow and MeanFlow, we use the equivalence between velocity parameterization and diffusion-style denoising parameterization to derive the quantities required by RCC. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- For CTM, the method adopts the EDM noise parameterization along with local Gaussian approximations of the sender and shared distributions at intermediate states. (confidence: 1.00)
  Evidence: For CTM, which is distilled from EDM, we adopt the EDM noise parameterization together with local Gaussian approximations of the sender and shared distributions at intermediate states. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- To apply Rectified Flow models within the DiffC framework, the noise schedule is aligned to DDPM by adjusting time steps to match the signal-to-noise ratio and scaling the input to match the expected scale. (confidence: 1.00)
  Evidence: To apply Rectified Flow models (e.g., Flux~\cite{labs2025flux1kontextflowmatching}) within the DiffC framework, Vonderfecht et al.~\cite{vonderfecht2025lossy} aligned the Rectified Flow noise schedule to that of DDPM. Specifically, they performed the following two operations: 1. \textbf{Adjusting the Time Steps} ... 2. \textbf{Scaling $\bx_t$} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/source.tex

### Dataset

- The experiments utilize the ImageNet 64x64 and ImageNet 256x256 datasets. (confidence: 1.00)
  Evidence: ImageNet 64$\times$64 ... ImageNet 256$\times$256 [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/source.tex

### Claim

- The proposed probabilistic formulation allows for compression using pre-trained few-step generative models without the need for retraining. (confidence: 1.00)
  Evidence: This yields a proof-of-concept probabilistic formulation that enables compression with pre-trained few-step generative models without retraining. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- On low-resolution benchmarks, the proposed codecs reduce encoding and decoding time while improving realism in the low-bit-rate regime. (confidence: 1.00)
  Evidence: On low-resolution benchmarks, the resulting codecs reduce encoding and decoding time and improve realism in the low-bit-rate regime. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- Increasing the number of forward steps generally increases encoding and decoding time but improves reconstruction quality (PSNR) across methods. (confidence: 1.00)
  Evidence: Increasing $T$ generally increases both encoding and decoding time. ... Across methods, larger $T$ improves reconstruction quality (PSNR) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/source.tex
- CTMC does not always show a monotonic increase in encoding time with more forward steps because the RCC implementation estimates KL divergence, which can slow down the process when divergence is large. (confidence: 1.00)
  Evidence: However, CTMC does not necessarily exhibit a monotonic increase in encoding time with larger $T$. This behavior is influenced by the RCC implementation, which explicitly estimates the KL divergence between the sender distribution $q$ and the shared distribution $p$ and can become slower when the divergence is large [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/source.tex

### Limitation

- A limitation of DiffC is that its encoding and decoding procedures are slow due to the requirement of many discretized forward and reverse steps. (confidence: 1.00)
  Evidence: DiffC provides a principled way to reuse pre-trained diffusion models for lossy compression, but its encoding and decoding procedures remain slow because they require many discretized forward and reverse steps. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- A key challenge in using few-step models for RCC is that RCC requires posterior and shared distribution parameters, which these models do not explicitly parameterize for intermediate conditional distributions. (confidence: 1.00)
  Evidence: The main challenge is that RCC requires posterior and shared distribution parameters, whereas these models do not explicitly parameterize intermediate conditional distributions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/summary.md
- A limitation of DiffC (RF) is that its denoising quality remains suboptimal despite achieving competitive performance compared to existing methods. (confidence: 1.00)
  Evidence: Although DiffC (RF) achieves competitive performance compared to existing methods, its denoising quality remains suboptimal, as demonstrated in results sections. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10450/source.tex

## FiRe: Fine-grained Multimodal Reasoning for Enhanced Image Generation

`fire` | authors: Yongjin Kim, Yoonjin Oh, Yerin Kim, Hyomin Kim, Jeeyoung Yun, Yujung Heo, Minjun Kim, Sungwoong Kim | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- FiRe is a fine-grained multimodal reasoning method for text-to-image generation that decomposes prompts into visual requirements, self-judges their satisfaction, and applies localized refinement. (confidence: 1.00)
  Evidence: we propose FiRe, a Fine-grained Multimodal Reasoning method for enhanced image generation by MLLM. In specific, FiRe performs a fine-grained multi-step reasoning by first decomposing the prompt into key visual requirements and then self-judging their satisfaction in the generated image, followed by localized refinement according to self-generated precise feedback. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex
- FiRe-GRPO is a reinforcement learning method that formulates the FiRe reasoning process as a step-level decision-making problem with step-specific rewards and step-level advantages for granular credit assignment. (confidence: 1.00)
  Evidence: we introduce FiRe-GRPO, a reinforcement learning method tailored to FiRe. Since standard Group Relative Policy Optimization (GRPO) suffers from sparse, outcome-based rewards in multi-step reasoning, we formulate our reasoning process as a step-level decision-making problem, design step-specific rewards, and compute step-level advantages for granular credit assignment within GRPO. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex
- The FiRe method consists of six reasoning steps: Initial T2I Generation, Prompt Summarization, Tuple Decomposition, Tuple VQA, Fine-grained Feedback Generation, and Localized Image Correction. (confidence: 1.00)
  Evidence: FiRe consists of six reasoning steps: \textbf{(1) Initial T2I Generation}, \textbf{(2) Prompt Summarization}, \textbf{(3) Tuple Decomposition}, \textbf{(4) Tuple VQA}, \textbf{(5) Fine-grained Feedback Generation}, and \textbf{(6) Localized Image Correction}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex

### Benchmark

- The paper evaluates the proposed method on compositional text-to-image benchmarks including GenEval, GenEval++, and DPG-Bench. (confidence: 1.00)
  Evidence: Experiments on representative compositional T2I benchmarks, including GenEval~\citep{ghosh2023geneval}, GenEval++~\citep{ye2025echo}, and DPG-Bench~\citep{hu2024ella}, demonstrate that FiRe consistently outperforms existing baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex

### Claim

- FiRe consistently outperforms competitive text-to-image baselines and existing reasoning-based methods, showing substantial gains on compositional text-to-image benchmarks. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that FiRe consistently outperforms competitive text-to-image baselines, including existing reasoning-based methods, with particularly substantial gains on compositional text-to-image benchmarks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex

### Limitation

- Standard Group Relative Policy Optimization (GRPO) suffers from sparse, outcome-based rewards in multi-step reasoning, failing to capture fine-grained signals from individual intermediate reasoning steps. (confidence: 1.00)
  Evidence: The standard Group Relative Policy Optimization (GRPO)~\citep{shao2024deepseekmath} treats the entire generation trajectory as a single action and assigns rewards only based on the quality of the final outcome. This outcome-based formulation often suffers from sparse feedback, as it fails to capture fine-grained signals from individual intermediate reasoning steps within the same trajectory. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/source.tex
- Existing multimodal reasoning-based image generation methods rely mostly on prompt augmentation or holistic image-text alignment judgments, which limits their fine-grained control over detailed prompt attributes. (confidence: 1.00)
  Evidence: existing multimodal reasoning-based image generation methods mostly rely on prompt augmentation or holistic image-text alignment judgments, without fine-grained reflection and refinement of detailed prompt attributes, leading to limited fine-grained control. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/fire/summary.md

## FlashTTS: Fast Streaming TTS with MTP Acceleration and X-pred Mean Flow Distillation

`flashtts` | authors: Hanke Xie, Xiaming Ren, Dake Guo, Ruonan You, Wenhao Li, Jingbin Hu, Guobin Ma, Huakang Chen, Kejie Xu, Rui Huang, Weiguo Tan, Xianrong Wang, Lei Xi | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/ASLP-lab/FlashTTS, https://github.com/BytedanceSpeech/seed-tts-eval, https://github.com/modelscope/FunASR

### Method

- FlashTTS introduces a lagged multi-track architecture that natively processes streaming text and speech inputs to eliminate sentence-level buffering. (confidence: 1.00)
  Evidence: FlashTTS introduces a lagged multi-track architecture that natively processes streaming text and speech inputs, thereby eliminating the need for sentence-level buffering. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- FlashTTS integrates parallel Multi-Token Prediction (MTP) with an X-pred mean flow matching decoder to accelerate acoustic generation. (confidence: 1.00)
  Evidence: To accelerate acoustic generation, we integrate parallel Multi-Token Prediction (MTP) with an X-pred mean flow matching decoder. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- FlashTTS is based on the Qwen2-0.5B architecture. (confidence: 1.00)
  Evidence: Based on the Qwen2-0.5B architecture, FlashTTS combines lagged multi-track streaming with parallel Multi-Token Prediction (MTP). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- The acoustic decoder adopts an X-pred mean flow strategy with block-level chunked attention to directly predict the mel-spectrogram. (confidence: 1.00)
  Evidence: For the acoustic decoder, we adopt an X-pred mean flow~\cite{geng2025mean,li2025back} strategy with block-level chunked attention, which directly predicts the mel-spectrogram, enabling high-fidelity token-to-mel generation in 2 inference steps. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- FlashTTS uses a stacked and lagged track structure consisting of three parallel information streams: a speech track, a text track, and a language track. (confidence: 1.00)
  Evidence: the stacked configuration consists of three parallel information streams: a speech track, a text track, and a language track. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- Stage 2 of FlashTTS training incorporates Multiple Token Prediction (MTP) using a frozen LLM and supplementary trainable transformer blocks to predict multiple tokens simultaneously. (confidence: 1.00)
  Evidence: Stage 2 (Figure \ref{fig:flashtts}b) incorporates Multiple Token Prediction (MTP) training. By leveraging a frozen LLM and supplementary trainable transformer blocks, this stage optimizes the system to predict multiple tokens simultaneously, effectively accelerating inference without compromising the generation quality. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex

### Claim

- The FlashTTS configuration achieves high-fidelity token-to-mel generation in exactly two function evaluations (2-NFE). (confidence: 1.00)
  Evidence: This configuration achieves high-fidelity token-to-mel generation in exactly two function evaluations (2-NFE). [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- FlashTTS reduces First-Packet Latency to 325ms compared to robust streaming baselines while preserving zero-shot voice cloning and cross-lingual intelligibility. (confidence: 1.00)
  Evidence: Experiments show that FlashTTS substantially reduces First-Packet Latency to 325ms compared to robust streaming baselines, all while preserving strong zero-shot voice cloning and cross-lingual intelligibility. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex

### Limitation

- Most existing single-codebook LLM-based TTS methods rely on multi-stage pipelines that lack native streaming capabilities and suffer from high end-to-end latency. (confidence: 1.00)
  Evidence: However, most existing single-codebook LLM-based TTS methods rely on multi-stage pipelines that lack native streaming capabilities. These systems typically suffer from high end-to-end latency due to slow autoregressive prediction and multi-step flow matching. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex
- CosyVoice2's chunk-aware causal flow matching does not address the core bottleneck of slow autoregressive token prediction and typically requires more than ten inference steps during decoding. (confidence: 1.00)
  Evidence: CosyVoice2 introduces chunk-aware causal flow matching with a pretrained vocoder to accelerate waveform generation, but it does not address the core bottleneck of slow autoregressive token prediction and typically requires more than ten inference steps during decoding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flashtts/source.tex

## Flexible Flows for Biological Sequence Design

`2606_10543` | authors: Yogesh Verma, Dani Korpela, Harri Lähdesmäki, Vikas Garg | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors propose FlexFlow, a Discrete Flow Matching method for biological sequence design that incorporates a biologically informed structured coupling, an edit-based reverse flow for flexible-length generation, and a latent guidance scheme. (confidence: 1.00)
  Evidence: To address these gaps, we propose \textbf{FlexFlow}, a Discrete Flow Matching method for biological sequence design. FlexFlow incorporates a biologically informed structured coupling, an edit-based reverse flow for flexible-length generation with post-hoc operation control, and a latent guidance scheme for fine-grained conditional control. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex
- FlexFlow introduces a structured coupling that replaces standard couplings with a domain-specific, biologically informed prior to steer the generative path toward preferred functional neighborhoods. (confidence: 1.00)
  Evidence: \textbf{Structured Coupling}. We introduce a structured coupling that replaces standard couplings with a domain-specific, biologically informed prior to steer the generative path toward preferred functional neighborhoods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex
- To support variable-length sequence design, FlexFlow parameterizes rates via edit operations and incorporates Dirichlet priors for post-hoc, temperature-controlled operation mixing. (confidence: 1.00)
  Evidence: \textbf{Latent Edit-based rates with controllable edits}. To support variable-length sequence design, we parameterize rates via edit operations and incorporate Dirichlet priors for post-hoc, temperature-controlled operation mixing, enabling granular control during inference. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex
- FlexFlow proposes latent guidance that operates entirely within the continuous latent space as an alternative to rate-space classifier-free guidance, ensuring global structural consistency. (confidence: 1.00)
  Evidence: \textbf{Latent Guidance}. As an alternative to rate-space classifier-free guidance (CFG), 
    % (\V{need to define CFG. ``... classifier-free guidance (CFG)...'' })
    we propose latent guidance that operates entirely within the continuous latent space, ensures global structural consistency, and enhances downstream performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex

### Benchmark

- The authors introduce a novel peptide-MHC II benchmark for generating and evaluating MHC-conditioned peptide sequences. (confidence: 1.00)
  Evidence: \textbf{New Benchmark for peptide sequence generation}. We introduce a novel peptide-MHC II benchmark for generating and evaluating MHC-conditioned peptide sequences. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex

### Claim

- FlexFlow achieves state-of-the-art performance across diverse biological sequence tasks, including density estimation, unconditional and conditional DNA sequence generation, and peptide sequence generation. (confidence: 1.00)
  Evidence: Our method achieves state-of-the-art performance across diverse biological sequence tasks, including density estimation, unconditional and conditional DNA sequence generation, and peptide sequence generation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex

### Limitation

- Existing discrete methods for biological applications suffer from limited flexibility in variable length sequence generation, rely on uniform or masked couplings that ignore structured relationships, and rely on independent token-wise adjustments for guidance that fail to capture global dependencies. (confidence: 1.00)
  Evidence: Despite these advances, existing discrete methods for biological applications suffer from key limitations: (i) they offer limited flexibility in flexible length sequence generation with limited fine grained control; (ii) they rely on uniform or masked couplings that ignore the structured relationships between biological sequence elements; and (iii) guiding them toward specific functional properties relies on independent, token-wise adjustments \citep{nisonoff2024unlocking} that fail to capture the global dependencies required for complex regulatory or binding motifs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex
- Autoregressive methods suffer from compounding errors, slow sequential sampling, and limited global coherence, which worsen for long or structurally complex sequences. (confidence: 1.00)
  Evidence: However, autoregressive methods suffer from compounding errors, slow sequential sampling, and limited global coherence, which worsen for long or structurally complex sequences. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10543/source.tex

## Flow Control: Steering Vision-Language-Action Models with Simple Real-Time Inputs

`flow-control` | authors: Jonathan C. Kao, Jason Chan, Andy Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- Flow control is a technique to steer vision-language-action (VLA) models in real-time using generic inputs like a keyboard, without requiring retraining or fine-tuning. (confidence: 1.00)
  Evidence: We introduce flow control of vision-language-action (VLA) models, a simple and effective way to steer VLA actions in real-time through generic inputs, such as a keyboard.
This method can be used out-of-the-box and does not require retraining or fine-tuning VLAs. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex
- Flow control steers the VLA by modifying the initial condition of the flow matching ordinary differential equation (ODE) rather than using additional guidance gradients. (confidence: 1.00)
  Evidence: As we detail in the Methods, in flow control, we find that simply modifying the initial condition of the flow ODE is sufficient to align the VLA with user intent, requiring no additional guidance gradients. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex
- The π_0.5 VLA generates actions using a flow matching action expert implemented with a downsized 300M-parameter Gemma transformer. (confidence: 1.00)
  Evidence: $\pi_{0.5}$ generates actions with a flow matching action expert, implemented by a downsized $300$M-parameter Gemma transformer \cite{Gemma-Team2024-yf}. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex
- In the π_0.5 model, the flow matching ODE is integrated using the Euler method over 10 steps with a time step of 0.1. (confidence: 1.00)
  Evidence: In $\pi_{0.5}$, $\Delta t = 0.1$, meaning the Euler integration takes $10$ steps for inference. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex

### Dataset

- The π_0.5-DROID vision-language-action model used in the study was fine-tuned on the DROID dataset. (confidence: 1.00)
  Evidence: We use the VLA $\pi_{0.5}$-DROID, which was fine-tuned on the DROID dataset \cite{Khazatsky2024-bw}. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex

### Claim

- Flow control enables users to achieve significantly higher success rates and faster task completion, is robust to suboptimal inputs, and fine-tuning on its trajectories improves the autonomous policy. (confidence: 1.00)
  Evidence: We demonstrate that flow control has many desirable properties: (1) flow control accurately and responsively steers robot actions with user inputs, (2) it is robust to suboptimal user inputs, (3) it enables users to steer VLAs to achieve significantly higher success rates and faster task completion, and (4) fine-tuning a VLA on flow control trajectories improves the autonomous policy. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex
- Unlike diffusion models that lose initial condition information due to injected noise, flow matching preserves information about the initial condition in the final action because it follows a deterministic path. (confidence: 1.00)
  Evidence: Flow matching therefore \textit{preserves} information about the IC $\x_0$ in the eventual action $\x_1$. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex

### Limitation

- Existing VLA steering methods such as language corrections are coarse and intermittent, while spatial or visual goals like sketches require high-bandwidth inputs and additional data collection and fine-tuning. (confidence: 1.00)
  Evidence: But language corrections are coarse and intermittent, while sketches and goal images require high-bandwidth.
These steering methods furthermore involve additional data collection and fine-tuning. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/flow-control/source.tex

## FlyMirage: A Fully Automated Generation Pipeline for Diverse and Scalable UAV Flight Data via Generative World Model

`flymirage` | authors: Jinhan Li, Xijie Huang, Zhaoqi Wang, Yijin Wang, Weiqi Ge, Qiyi He, Mo Zhu, Fei Gao, Yuze Wu, Xin Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## FreeAnimate: Training-Free Human Image Animation with Preview-Guided Denoising

`freeanimate` | authors: Yuan Zeng, Yujia Shi, Zongqing Lu, QingMin Liao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Flode-Labs/vid2densepose, https://github.com/MooreThreads/Moore-AnimateAnyone

### Method

- FreeAnimate is a training-free framework for human image animation that leverages the inherent capabilities of image diffusion models to enable temporal consistency, identity preservation, and background stability. (confidence: 1.00)
  Evidence: In this work, we introduce \emph{FreeAnimate}, a training-free framework that leverages the inherent capabilities of image diffusion models to enable temporal consistency, identity preservation, and background stability. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- FreeAnimate incorporates a Preview Generation Strategy that uses pretrained models like Grounded-SAM, image editing, and inpainting models to produce preview frames that provide temporal priors aligned with target frames. (confidence: 1.00)
  Evidence: we introduce a \emph{Preview Generation Strategy} that leverages pretrained models such as Grounded-SAM \cite{GroundedSAM}, editing \cite{Masactrl, T2iAdapter}, and inpainting \cite{Mat} to produce preview frames, providing temporal priors aligned with target frames. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- The FreeAnimate framework uses only a pose ControlNet and U-Net for pose-guided synthesis, avoiding the use of CLIP encoders or AppearanceNet. (confidence: 1.00)
  Evidence: Unlike methods that add CLIP encoders or AppearanceNet, our framework uses only a pose ControlNet and U-Net for pose-guided synthesis. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- FreeAnimate introduces Inversion-Boosted Attention, which leverages preview-frame attention maps from DDIM inversion to guide the denoising process. (confidence: 1.00)
  Evidence: We also introduce \emph{Inversion-Boosted Attention}, which leverages preview-frame attention maps from DDIM inversion \cite{DDIM} to guide denoising [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- FreeAnimate integrates Reference-Anchored Self-Attention to preserve identity by allowing each latent to attend to the reference latent. (confidence: 1.00)
  Evidence: and \emph{Reference-Anchored Self-Attention}, which preserves identity by letting each latent attend to the reference latent. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- Inversion-Boosted Attention (IBA) stores and reuses self-attention and cross-attention maps generated during the DDIM inversion process of preview frames to compute attention during the denoising process. (confidence: 1.00)
  Evidence: at each step $t$ of the inversion process, we store the generated self-attention maps $\textit{s}_{t}^{\text{ pre}}$ and cross-attention maps $\textit{c}_{t}^{\text{ pre}}$ from the preview frames $z_{0}^{\text{pre}}$ as follows: [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex

### Claim

- Experimental results show that FreeAnimate outperforms existing training-free competitors and training-based baseline methods, achieving generation quality comparable to state-of-the-art methods and offering robust generalization across diverse datasets. (confidence: 1.00)
  Evidence: Experimental results demonstrate that FreeAnimate outperforms existing training-free competitors and training-based baseline methods, achieving generation quality comparable to state-of-the-art methods and offering robust generalization across diverse datasets. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex

### Limitation

- Existing human image animation methods typically require large-scale training data and resources, and their generated results often inherit biases from the training datasets. (confidence: 1.00)
  Evidence: However, existing methods still rely on large-scale training and resources, and their results often inherit dataset biases. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- The prior training-free approach, PoseAnimate, mainly demonstrates cartoon examples and employs a complex architecture, which limits its applicability to real-world scenarios and hinders further research. (confidence: 1.00)
  Evidence: Yet PoseAnimate mainly demonstrates cartoon examples and employs a complex architecture, limiting its applicability to real-world scenarios and further research. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex
- Directly injecting image features into the U-Net via cross-attention without further training yields suboptimal results due to a domain gap and the compact nature of semantic-level CLIP image embeddings. (confidence: 1.00)
  Evidence: However, we observe that directly injecting image features without further training yields suboptimal results. 
We attribute this to two primary factors: (1) a domain gap, as the SD model's cross-attention was well-trained with CLIP text embeddings, and (2) semantic-level CLIP image embeddings being too compact to capture fine-grained details. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/freeanimate/source.tex

## From Senses to Decisions: The Information Flow of Auditory and Visual Perception in Multimodal LLMs

`2606_10147` | authors: Wish Suharitdamrong, Muhammad Awais, Xiatian Zhu, Sara Atito | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The research evaluates information flow using Qwen2.5-Omni and Video-SALMONN2 Plus models at 3B and 7B parameter scales. (confidence: 0.95)
  Evidence: These findings hold across multiple models and scales, Qwen2.5-Omni and Video-SALMONN2 Plus at 3B and 7B scales [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/summary.md
- The study analyzes information flow by inspecting the attention allocation of the first generated token (the answer letter) in multiple-choice question-answering tasks. (confidence: 0.90)
  Evidence: We do this on multiple-choice question-answering (MCQ) tasks, where the prediction is a single token (the answer letter), using Qwen2.5-Omni~\cite{xu2025qwen2} at 3B scale as our subject model. We inspect the attention allocation of this last token which is the first generated token where the prediction is formed. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/source.tex

### Dataset

- The study utilizes AV-SpeakerBench and WorldSense for audio-visual video tasks, and AV-Odyssey for multi-input audio-visual interleaved tasks. (confidence: 0.90)
  Evidence: AV-SpeakerBench (audio-visual video)
- WorldSense (audio-visual video)
- AV-Odyssey (multi-input audio-visual interleaved) [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/summary.md

### Claim

- For audio-visual video inputs, AVLLMs follow a sequential information flow pathway similar to VLMs and VideoLLMs, with modality contribution proportional to task reliance. (confidence: 0.95)
  Evidence: We find that for audio-visual video, AVLLMs follow the sequential information flow pathway established for VLMs and VideoLLMs, with audio and visual contribution flowing along this pathway in proportion to the task's reliance on each modality. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/summary.md
- When processing multiple interleaved audio-visual items, AVLLMs shift from sequential routing to different parallel streams. (confidence: 0.95)
  Evidence: In settings with multiple interleaved audio-visual items, this routing shifts to different parallel streams. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/summary.md
- Audio-visual and other token types can be discarded after their information is transferred to the LLM, resulting in minimal impact or slight improvement in predictions and enabling more efficient inference. (confidence: 0.95)
  Evidence: Furthermore, we demonstrate that audio-visual and other token types can be discarded once their information is transferred to LLM, with minimal impact on the model's prediction or even slight improvement, generalizing across multiple tasks and datasets, enabling more efficient inference. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/summary.md
- In later layers, video attention is dominated by attention artifacts, making attention allocation an unreliable indicator of information flow. (confidence: 0.95)
  Evidence: Video attention in later layers is dominated by attention artifacts that disproportionately attract attention, making attention allocation an unreliable indicator of information flow. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/source.tex
- The contribution of each modality and the strength of audio-video interaction vary depending on the specific requirements of the task. (confidence: 0.95)
  Evidence: Task requirements steer the model's audio-visual flow: The contribution of each modality to the prediction and the strength of interaction between audio and video vary with what the task requires [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10147/source.tex

## GEM-4D: Geometry-Enhanced Video World Models for Robot Manipulation

`gem-4d` | authors: Kaichen Zhou, Yuzhen Chen, Fangneng Zhan, Hang Hua, Grace Chen, Xinhai Chang, Ao Qu, Yilun Du, Zhuang Liu, Paul Pu Liang, Mengyu Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## GP-Adapter: Gaussian Process CLIP-Adapter for Few-Shot Out-of-Distribution Detection

`gp-adapter` | authors: Taisei Saito, Koretaka Ogata, Takafumi Hiroi | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/tms-byte/GP-Adapter

### Method

- GP-Adapter is a training-free framework that augments CLIP with Gaussian Process uncertainty modeling for few-shot classification and out-of-distribution detection. (confidence: 1.00)
  Evidence: We propose GP-Adapter, a training-free framework that augments CLIP (Contrastive Language-Image Pre-training) with Gaussian Process (GP) uncertainty modeling for few-shot classification and out-of-distribution (OOD) detection. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- GP-Adapter constructs modality-specific, class-wise one-class Gaussian Processes on frozen CLIP embeddings, using an RBF kernel for image features and a linear kernel for text prompts. (confidence: 1.00)
  Evidence: GP-Adapter constructs modality-specific, class-wise one-class GPs on top of frozen CLIP embeddings using an RBF kernel for image features and a linear kernel for text prompts [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- The method fuses the predictive statistics of the image and text Gaussian Processes to produce a variance-aware confidence score for out-of-distribution detection. (confidence: 1.00)
  Evidence: and fuses their predictive statistics to produce a variance-aware confidence score for OOD detection. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- GP-Adapter does not require fine-tuning of the CLIP backbone, relying instead on a small K-shot cache and lightweight hyperparameter selection. (confidence: 1.00)
  Evidence: The method requires no fine-tuning of the CLIP backbone and relies only on a small $K$-shot cache and lightweight hyperparameter selection, [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- The memory footprint of GP-Adapter scales as O(CK^2), where C is the number of classes and K is the number of shots. (confidence: 1.00)
  Evidence: with memory cost scaling as $O(CK^2)$ for $C$ classes and $K$ shots. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- For the text modality, GP-Adapter employs a prompt-ensemble strategy using the standard set of seven ImageNet templates. (confidence: 1.00)
  Evidence: Following~\cite{radford2021clip}, we adopt a prompt-ensemble strategy and use the standard set of seven ImageNet templates. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- The predictive distributions from the image and text modalities are fused using a weighted linear combination, assuming independence between the two modalities. (confidence: 1.00)
  Evidence: Assuming independence between the two modalities, 
we fuse their predictive distributions via a weighted linear combination. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex

### Dataset

- The authors evaluate GP-Adapter on ImageNet and multiple out-of-distribution benchmarks. (confidence: 1.00)
  Evidence: Experiments on ImageNet and multiple OOD benchmarks show that GP-Adapter provides competitive few-shot performance [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex

### Claim

- GP-Adapter achieves competitive few-shot performance and consistently improves out-of-distribution detection when combined with prompt-learning baselines. (confidence: 1.00)
  Evidence: Experiments on ImageNet and multiple OOD benchmarks show that GP-Adapter provides competitive few-shot performance and consistently improves OOD detection when combined with prompt-learning baselines, [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex
- Integrating probabilistic inference with large pre-trained vision-language models can improve reliability in low-data and distribution-shifted settings. (confidence: 0.90)
  Evidence: Overall, our results suggest that integrating probabilistic inference with large pre-trained vision-language models can improve reliability in low-data and distribution-shifted settings. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/gp-adapter/source.tex

## GeoWorld-VLM: Geometry from World Models for Vision-Language Models

`geoworld-vlm` | authors: Renjie Gu, Kaichen Zhou, Yan Luo, Mengyu Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Harvard-AI-and-Robotics-Lab/GeoWorld-VLM

No research facts available.

## Geodesic Flow Matching on a Riemannian Degradation Manifold for Blind Image Restoration

`2606_06278` | authors: Akshay Janardan Bankar, Ankita Chatterjee, Sayan Banerjee, Shreyas Pandith, Kalakonda Sai Shashank, Amit Satish Unde | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed method models degradations as points on a low-dimensional Riemannian manifold and formulates blind image restoration as geodesic transport on the joint image-manifold space using a geodesic flow matching objective. (confidence: 1.00)
  Evidence: we explicitly model degradations as points on a low-dimensional Riemannian manifold and formulate restoration as geodesic transport on the joint image–manifold space. Using a geodesic flow matching objective, we learn intrinsic transport dynamics that respect the curvature of degradation space. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex
- The method employs a two-stage training strategy where the first stage jointly learns a geometry-constrained degradation representation with the latent restoration flow, and the second stage freezes the degradation encoder to enforce tangent-bundle consistency for manifold dynamics. (confidence: 1.00)
  Evidence: We further proposed a two-stage training strategy that first learns a geometry-constrained degradation representation jointly with the latent restoration flow, and then enforces tangent-bundle consistency for manifold dynamics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex
- The restoration vector field is parameterized by a UNet backbone operating in the latent space of a pretrained Stable Diffusion autoencoder, with the degradation state injected via cross-attention. (confidence: 1.00)
  Evidence: We operate in the latent space of a pretrained Stable Diffusion autoencoder \cite{rombach2022ldm}. The restoration vector field is parameterized by a UNet backbone. The degradation state $m_t$ is injected through cross-attention by concatenating a projected manifold token with the empty-text embedding, i.e., $\mathbf{c}_t=[\mathrm{Emb}(\varnothing),\,W_m m_t]$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex
- The study compares three manifold instantiations for the degradation state: Euclidean, spherical, and hyperbolic (Lorentz hyperboloid). (confidence: 1.00)
  Evidence: We compare three manifold instantiations for the degradation state: Euclidean ($\mathbb{R}^d$), spherical ($\mathbb{S}^{d-1}$), and hyperbolic (Lorentz hyperboloid $\mathbb{H}^d_c$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex

### Dataset

- The method is evaluated on four blind image restoration tasks: deblurring, dehazing, deraining, and desnowing, using specific paired and real-image benchmarks for each. (confidence: 1.00)
  Evidence: We evaluate four restoration tasks (deblurring, dehazing, deraining, and desnowing). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex

### Benchmark

- Fidelity metrics (PSNR, SSIM, LPIPS) are reported on paired benchmarks (DPDD, NH-HAZE, LHP, RealSnow), while perceptual distribution metrics (FID, KID) are evaluated on real-image benchmarks (RealBlur-J, RESIDE, RealRain/RealTest, Dense-Snow). (confidence: 1.00)
  Evidence: Specifically, we use DPDD \cite{abdelhamed2019dpdd} and RealBlur-J \cite{rim2020realblur} for deblurring; NH-HAZE \cite{ancuti2020nhhaze} and RESIDE \cite{li2018reside} for dehazing; LHP \cite{guo2023lhprain} and RealRain/RealTest \cite{yang2020realrain} for deraining; and RealSnow \cite{liu2021realsnow} together with the ``Realistic'' benchmark from Dense-Snow \cite{chen2021densely} for desnowing. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex

### Claim

- The final hyperbolic model achieves competitive or improved restoration performance across benchmarks, with notable gains on challenging deblurring cases and strong performance on real-world degradations. (confidence: 1.00)
  Evidence: Across these benchmarks, our final hyperbolic model achieves competitive or improved restoration performance. The gains are particularly notable on challenging deblurring cases and remain strong on real-world degradations, indicating that the proposed degradation manifold improves restoration fidelity while remaining competitive with high-capacity restoration architectures. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex
- Non-Euclidean geometries, particularly hyperbolic manifolds, provide a useful inductive bias that results in interpretable severity organization and consistent restoration trajectories. (confidence: 1.00)
  Evidence: our analysis indicates that non-Euclidean geometries—particularly hyperbolic manifolds—offer a useful inductive bias, producing interpretable severity organization and consistent restoration trajectories. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06278/source.tex

## Geometry Guided Self-Consistency for Physical AI

`2605_08638` | authors: Yinwei Dai, Zhuofu Chen, Lijie Yang, Ravi Netravali | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/dywsjtu/keystone

### Method

- KeyStone is an inference-time self-consistency method for diffusion-based action generation that draws K candidate action chunks in parallel, clusters them in continuous action space, and returns the medoid of the largest cluster. (confidence: 1.00)
  Evidence: We introduce KeyStone, an inference-time self-consistency method for diffusion-based action generation that draws $K$ candidate action chunks in parallel from a shared model context, clusters them in continuous action space, and returns the medoid of the largest cluster -- no additional model required. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/summary.md
- KeyStone is implemented as a lightweight Python wrapper that intercepts an existing policy's action-generation call and replaces it with K-sample parallel inference and cluster-medoid selection without modifying model weights. (confidence: 1.00)
  Evidence: KeyStone is implemented as a lightweight Python wrapper that intercepts each action-generation call of an existing policy and replaces it with $K$-sample parallel inference plus cluster-medoid selection. The wrapper does not modify model weights, retrain any component, or change the downstream control loop. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/source.tex

### Benchmark

- KeyStone is evaluated across three testbeds: LeRobot, vla-eval, and Fast-WAM. (confidence: 1.00)
  Evidence: Across the three testbeds we evaluate on (LeRobot, vla-eval, Fast-WAM), the integration follows the same three-step pattern at each round [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/source.tex

### Claim

- KeyStone improves task success rates by up to 13.3% over single-trajectory sampling across diverse vision-language-action models (VLAs) and world-action models (WAMs). (confidence: 1.00)
  Evidence: Across diverse vision-language-action models (VLAs) and world-action models (WAMs), KeyStone improves task success rates by up to \textbf{13.3\%} over single-trajectory sampling with negligible latency overhead [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/summary.md
- Action chunks are geometrically structured such that Euclidean distance directly reflects physical similarity, enabling principled and judge-free selection without a learned judge. (confidence: 1.00)
  Evidence: Second, unlike token or pixel spaces where distance carries no semantic meaning and selection requires a learned judge, action chunks are geometrically structured such that Euclidean distance directly reflects physical similarity, making selection principled and judge-free. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/summary.md
- Running K chains in parallel adds no additional wall-clock latency because the compact nature of action trajectories makes diffusion inference memory-bandwidth bound, leaving spare compute capacity. (confidence: 0.95)
  Evidence: First, the compact nature of action trajectories makes diffusion inference memory-bandwidth bound, leaving spare compute capacity to run $K$ chains in parallel with no additional wall-clock latency. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/summary.md

### Limitation

- KeyStone assumes the underlying model is properly trained and samples useful candidate trajectories; it cannot produce a successful action if all sampled candidates fail or if the model is confidently wrong on the majority of samples. (confidence: 1.00)
  Evidence: Like other existing test-time scaling methods for both language models and physical AI models, KeyStone assumes that the underlying model is properly trained and samples useful candidate trajectories. It can choose a better action chunk among the sampled candidates, but it cannot produce a successful action if none of the sampled candidates would succeed, or if the model is confidently wrong on the majority of samples [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/source.tex
- The latency measurements for KeyStone assume a batch size of one with a dedicated GPU; if the accelerator is shared across multiple robots resulting in a large effective batch size, the headroom for parallel samples may decrease. (confidence: 1.00)
  Evidence: Additionally, our latency measurements use batch size one, a common robot-deployment setting with a dedicated GPU. When the same accelerator is shared across multiple robots and the effective batch size is already large, the available headroom for additional parallel samples may shrink [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08638/source.tex

## Global-Local Monte Carlo Tree Search in Vision-Language Models for Text-to-3D Indoor Scene Generation

`2606_06002` | authors: Mengshi Qi, Wei Deng, Xianlin Zhang, Huadong Ma | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/dw-dengwei/TreeSearchGen

### Method

- The paper proposes a hierarchical scene representation and a Progress Reward Model (PRM)-guided Monte Carlo Tree Search (MCTS) method to effectively search the solution space for 3D scene generation. (confidence: 1.00)
  Evidence: To effectively search the tree, we propose a hierarchical scene representation and a PRM-guided MCTS method. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/summary.md
- The hierarchical scene representation abstracts a scene into four distinct levels: room level, region level, floor object level, and supported object level. (confidence: 1.00)
  Evidence: This representation abstracts a scene into room level, region level, floor object level, and supported object level. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/summary.md
- To ensure visual appearance consistency across the entire scene, the method leverages pre-trained diffusion image generative models to predict textures for all objects. (confidence: 1.00)
  Evidence: To make the whole appearance of the scene consistent, we leverage pre-trained diffusion image generative models to predict textures for all the objects in the scene. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/source.tex

### Dataset

- The authors collected a new large-scale and diverse dataset named 3DTindo-bench, which includes 65 scene types and 3,250 instructions featuring various sizes, layouts, and styles. (confidence: 1.00)
  Evidence: we collect a new large-scale diverse dataset that contains 65 scene types and 3250 instructions with diverse sizes, layouts, and styles, named 3DTindo-bench [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/summary.md

### Benchmark

- The proposed LVLM-powered evaluation framework assesses generated 3D scenes across five dimensions: physical reasonability, semantic reasonability, layout reasonability, instruction alignment, and aesthetic consistency. (confidence: 1.00)
  Evidence: Beyond the dataset, we introduce an LVLM-powered evaluation framework that assesses generated scenes across five dimensions: physical reasonability, semantic reasonability, layout reasonability, instruction alignment, and aesthetic consistency. [sec/1_intro.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/source.tex

### Claim

- The proposed method outperforms the best baseline by an average of approximately 14% in performance scores. (confidence: 1.00)
  Evidence: our method surpasses the best baseline by approximately 14% on average performance scores. [sec/0_abstract.tex]

### Limitation

- Current LVLM-based methods for text-to-3D scene generation rely on chain-of-thought sequential decision mechanisms that cannot revise earlier decisions, which leads to error propagation. (confidence: 1.00)
  Evidence: The main challenge is that prevailing LVLM-based methods employ chain-of-thought sequential decision mechanisms that cannot revise earlier decisions, causing error propagation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/summary.md
- Existing evaluation benchmarks for text-to-3D indoor scene generation, such as LayoutVLM-Bench, suffer from limited scale and diversity, covering very few scene types and instructions without size or style variations. (confidence: 1.00)
  Evidence: existing evaluation protocols, such as the LayoutVLM-Bench~\cite{LayoutVLM} covering only 11 scene types with 33 instructions and lacking size and style variations, employ substantially limited sample sizes [sec/1_intro.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/source.tex
- Exhaustively traversing expansive tree structures for 3D scene layout generation introduces prohibitive computational complexity, especially for scenes with numerous objects. (confidence: 1.00)
  Evidence: Nevertheless, exhaustive traversal of expansive tree structures introduces prohibitive computational complexity, particularly for scenes containing numerous objects. [sec/1_intro.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/source.tex
- Acquiring comprehensive 3D scene datasets is highly resource-intensive, resulting in constrained dataset sizes that limit the generalization and robustness of data-driven models. (confidence: 1.00)
  Evidence: acquiring comprehensive 3D scene datasets remains resource-intensive, yielding constrained dataset sizes that limit model generalization and robustness. [sec/1_intro.tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06002/source.tex

## Guide Me Out: A Framework to Benchmark VLM Operators Communication in Crisis Scenarios

`guide-me-out` | authors: Giacomo Gonella, Stefano Menini, Marco Guerini | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/LanD-FBK/guide-me-out, https://github.com/watabou/TownGeneratorOS

### Method

- The framework evaluates two communication strategies (narrowcast vs. broadcast), two environment representations (visual vs. graph-based), and two threat behaviors (static vs. moving) across nine maps. (confidence: 1.00)
  Evidence: We test two communication strategies (narrowcast vs. broadcast), two environment representations (visual vs. graph-based), and two threat behaviors (static vs. moving) across nine maps of varying structural complexity. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex
- The benchmark constructs scenarios of increasing difficulty using nine maps stratified into Easy, Medium, and Hard tiers based on structural features like the number of exits and structural bottlenecks. (confidence: 1.00)
  Evidence: we construct scenarios of increasing difficulty by varying the geometries across nine maps, which are stratified into three distinct tiers... Easy maps feature multiple exits and open paths. Medium maps reduce exits to a single central one... Hard maps introduce a river crossable only through a few bridges [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex

### Benchmark

- The paper introduces 'Guide Me Out', a simulation-based benchmarking framework for evaluating Vision-Language Models (VLMs) tasked with guiding civilian agents through simulated evacuations. (confidence: 1.00)
  Evidence: We address this gap with a novel benchmarking framework for evaluating Vision-Language Models (VLMs) tasked with guiding civilian agents through simulated evacuations. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex

### Claim

- Narrowcast communication consistently reduces civilian failure rates compared to broadcast communication across all difficulty levels in the simulated evacuations. (confidence: 1.00)
  Evidence: Our results show that Narrowcast consistently reduces civilian Fail rates compared to Broadcast across all difficulty levels. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex
- The visual modality is the primary driver of guidance performance for the VLM operator, whereas adding an adjacency graph representation is model-dependent and frequently detrimental. (confidence: 1.00)
  Evidence: Guidance quality depends heavily on how the VLM operator represents the world: the visual modality drives performance, while adding an adjacency graph is model-dependent and often harmful. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex
- The presence of moving threats increases failure rates across all experimental conditions because the communication must continuously adapt over time. (confidence: 1.00)
  Evidence: Moving threats raise Fail rates across all conditions as communication must continuously adapt over time. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex

### Limitation

- Current NLP research in crisis communication is largely limited to static, text-only classification settings and overlooks the communicative role of AI operators in dynamic, embodied scenarios. (confidence: 1.00)
  Evidence: Yet, current NLP research in crisis communication remains mainly limited to static, text-only classification settings, overlooking the critical communicative role of AI operators in dynamic, embodied scenarios. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/guide-me-out/source.tex

## Guided Discovery of New Behaviors using Diffusion Policies

`2606_08743` | authors: Dian Yu, Sebastian Sanokowski, Majid Khadiv | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed framework, Guided Discovery of New Behaviors (GDNB), systematically guides diffusion policy samples towards promising yet underrepresented samples using Feynman-Kac correctors. (confidence: 1.00)
  Evidence: Thus, we systematically guide samples using Feynman--Kac correctors \cite{skreta2025fkc} towards trajectories from the diffusion policy that are both promising and underrepresented samples. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- GDNB refines frontier trajectories using sampling-based trajectory optimization and reincorporates them into the training set to retrain the diffusion policy. (confidence: 1.00)
  Evidence: These \emph{frontier trajectories} are then refined and corrected using sampling-based trajectory optimization methods and added to the training set to retrain the diffusion policy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- The guidance function in GDNB leverages the learned score of the diffusion model as a proxy to identify low-probability regions, biasing samples towards them. (confidence: 1.00)
  Evidence: A central component of our framework is the guidance function $B_k(A^k_t, x_t)$, which systematically biases diffusion samples toward low-probability regions. To achieve this goal, we propose to leverage the learned score $s^k_\theta(A_t^k, x_t)$ of the diffusion model as a proxy for identifying such regions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- The shape of the guiding potential used to bias diffusion samples is inspired by the Lennard-Jones potential. (confidence: 1.00)
  Evidence: Here, \(\Phi\) is inspired by the Lennard--Jones potential \cite{LJDef,sadus2018second}; writing \(x=d/d^*\), its shape and gradient are shown in Fig.~\ref{fig:rare_shell_potential}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex

### Claim

- Under limited demonstrations, standard sampling in diffusion policies often reproduces dominant modes while under-representing valid but rare behaviors. (confidence: 1.00)
  Evidence: However, under limited demonstrations, standard sampling often reproduces dominant modes while under-representing valid but rare behaviors~\citep{chi2025diffusionpolicy}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- Existing guidance methods for increasing sample diversity often push samples into low-support regions, resulting in infeasible or non-executable trajectories. (confidence: 1.00)
  Evidence: However, these methods often push samples into low-support regions, resulting in trajectories that are infeasible or non-executable in the environment. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- Combining reinforcement learning with diffusion samplers is prone to getting stuck in local minima, which makes it difficult to discover diverse behaviors. (confidence: 1.00)
  Evidence: Yet, RL and diffusion samplers are prone to getting stuck in local minima \cite{he2025no}, making it difficult to discover diverse behaviors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex
- The GDNB framework effectively mines and repairs novel trajectories, enabling the systematic discovery of diverse and executable behaviors across manipulation environments. (confidence: 1.00)
  Evidence: Our method effectively mines and repairs novel trajectories, enabling the systematic discovery of diverse and executable behaviors. We demonstrate the effectiveness of our framework across a range of manipulation environments, consistently discovering new behaviors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex

### Limitation

- A limitation of diffusion models is that when trained in the sparse data regime, they can assign low probability to useful behaviors. (confidence: 1.00)
  Evidence: GDNB is motivated by the evidence that diffusion models, which are trained in the sparse data regime, can assign low probability to useful behaviors [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08743/source.tex

## HOIST: Humanoid Optimization with Imitation and Sample-efficient Tuning for Manipulating Suspended Loads

`hoist` | authors: Songyang Liu, Shunyu Yao, Dingyuan Huang, Shuai Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- HOIST initializes its policy by finetuning a high-level vision-language-action (VLA) model using virtual-reality teleoperation demonstrations. (confidence: 1.00)
  Evidence: HOIST first finetunes a high-level vision-language-action (VLA) policy from virtual-reality (VR) teleoperation demonstrations [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex
- After initialization, HOIST refines the policy using autonomous VLA rollouts and iterative batched reinforcement learning to improve placement accuracy and stopping behavior. (confidence: 1.00)
  Evidence: It then uses VLA rollouts and iterative batched RL to improve placement accuracy and stopping behavior. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex
- The high-level VLA policy outputs short-horizon command increments that update the head target, left-hand target, right-hand target, navigation command, and desired base height. (confidence: 1.00)
  Evidence: Each single-step command increment $\Delta \mathbf{u}_{\tau}$ updates the head target, left-hand target, right-hand target, navigation command, and desired base height [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex
- A fixed decoupled whole-body controller executes the high-level planner commands to handle whole-body tracking, balance, and joint-level stabilization. (confidence: 1.00)
  Evidence: The updated command is then executed by a humanoid whole-body control stack... where $\pi_{\mathrm{wbc}}$ is a fixed decoupled whole-body controller [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex
- The policy receives a combination of onboard RGB and depth observations, an external side-view image, humanoid proprioceptive state, language instruction, and the previous navigation command. (confidence: 1.00)
  Evidence: the policy receives the observation... where $\mathbf{I}^{\mathrm{ego,rgb}}_t$ and $\mathbf{D}^{\mathrm{ego}}_t$ are the humanoid onboard RGB and depth observations, $\mathbf{I}^{\mathrm{side,rgb}}_t$ is an external side-view image... $\mathbf{x}^{r}_t$ denotes the humanoid proprioceptive state, $\ell$ is the language instruction, and $\mathbf{c}^{\mathrm{nav}}_{t-1}$ is the previous navigation command. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex

### Claim

- HOIST reduces translational placement error by 19.9 cm and raw angular error by 3.56 degrees compared to pure VLA rollouts. (confidence: 1.00)
  Evidence: compared with pure VLA rollouts, HOIST reduces translational placement error by 19.9 cm and raw angular error by 3.56 degrees [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex

### Limitation

- Pure imitation learning does not directly optimize final placement accuracy, and training from scratch with reinforcement learning on real humanoids is unsafe and sample-inefficient. (confidence: 1.00)
  Evidence: Imitation learning provides safe initial behavior but does not directly optimize final placement, while reinforcement learning from scratch is unsafe and sample-inefficient on real humanoids. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/hoist/source.tex

## HapTile: A Haptic-Informed Vision-Tactile-Language-Action Dataset for Contact-Rich Imitation Learning

`haptile` | authors: Amirhosein Alian, Yongqiang Zhao, Shiyi Gu, Xuyang Zhang, Zhuo Chen, Christopher E. Mower, Haitham Bou-Ammar, Shan Luo | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The data collection platform for HapTile integrates haptic feedback directly into the teleoperation controller to allow the operator to perceive contact interactions in real time. (confidence: 1.00)
  Evidence: The data collection platform integrates haptic feedback directly into the teleoperation controller, enabling the operator to perceive contact interactions in real time. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- The robotic system used for HapTile data collection is built around a standard and reproducible setup equipped with custom-designed fingertip tactile sensors. (confidence: 1.00)
  Evidence: It is built around a standard and reproducible robotic system equipped with custom-designed fingertip tactile sensors. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex

### Dataset

- HapTile is a contact-grounded visuotactile manipulation dataset that embeds physical interaction sensing at both the robot end-effector and the teleoperator side. (confidence: 1.00)
  Evidence: In this work, we present HapTile, a contact-grounded visuotactile manipulation dataset that advances beyond vision-only trajectory datasets by embedding physical interaction sensing at two levels: fingertip tactile feedback at the robot end-effector, and haptic-informed demonstrations at the teleoperator side. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- The HapTile dataset includes everyday manipulation tasks such as pick-and-place, folding, pressing, and stacking, paired with language instructions, synchronized visuotactile observations, and action trajectories. (confidence: 1.00)
  Evidence: The dataset comprises everyday manipulation tasks spanning a broad range of contact-rich skills, including pick-and-place, folding, pressing, stacking, and other routine activities. Each task is paired with language instructions that condition the policy on the manipulation objective, together with synchronized visuotactile observations and action trajectories. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- The HapTile dataset contains 1,726 demonstrations across 38 tasks and 9 manipulation skills. (confidence: 1.00)
  Evidence: The dataset contains \ndemos\ demonstrations across \ntasks\ tasks and \nmanipulationskills\ manipulation skills, including pick-and-place, pressing, wiping, turning, folding, and compliant object handling. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- The dataset includes objects with diverse mechanical and geometric properties, such as items from the YCB object set. (confidence: 1.00)
  Evidence: It includes objects with diverse mechanical and geometric properties, including items from the YCB object set~\cite{calli2015ycb}, and spans tasks with varying levels of tactile dependency. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex

### Benchmark

- The authors validate the HapTile dataset by training Diffusion Policy and pi_0 baseline policies for manipulation learning. (confidence: 1.00)
  Evidence: We further validate the dataset by training Diffusion Policy and $\pi_0$ baseline policies for manipulation learning. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex

### Claim

- HapTile uses language instructions as policy conditioning signals rather than just descriptive metadata. (confidence: 1.00)
  Evidence: Unlike prior works~\cite{fu2024tvl,dave2024multimodal,fang2023rh20t,huang2026tafvla}, language instructions are used as policy conditioning signals rather than descriptive metadata. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- Most existing Vision-Language-Action (VLA) datasets are vision-only, and those with tactile information usually lack task diversity, language conditioning, and action trajectories. (confidence: 1.00)
  Evidence: most existing Vision-Language-Action (VLA) datasets remain vision-only, and those that do incorporate tactile information typically lack the joint combination of task diversity, language conditioning, and action trajectories. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex
- Incorporating real-time haptic feedback to the operator during data collection improves demonstration quality. (confidence: 0.90)
  Evidence: Data collection incorporates real-time haptic feedback to the operator, improving demonstration quality. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/haptile/source.tex

## HomeWorld: A Unified Floorplan-to-Furnished Framework for Generating Controllable, Densely Interactive Whole-Home Scenes

`homeworld` | authors: Wenbo Li, Xiaoliang Ju, Zipeng Qin, Rongyao Fang, Hongsheng Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The framework uses a K-D tree-based representation along with detailed descriptions to enable controllable whole-home floorplan generation. (confidence: 1.00)
  Evidence: With detailed descriptions and a K-D tree-based representation, our method enables fine-grained, controllable whole-home floorplan generation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md
- Image generation models are used to draft furniture layouts from multi-level roaming viewpoints based on the generated floorplan. (confidence: 1.00)
  Evidence: Building upon the generated whole-home floorplan, we leverage image generation models to draft furniture layouts from multi-level roaming viewpoints [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md
- A VLM-based refiner iteratively corrects the placement of furniture and objects during the layout generation process. (confidence: 1.00)
  Evidence: During furniture and object layout generation, a VLM-based refiner iteratively corrects furniture and object placement [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md
- The system generates layouts for small manipulable objects on supporting surfaces such as cabinets, desks, and dining tables to support embodied AI simulation. (confidence: 1.00)
  Evidence: and then generate the layouts of small manipulable objects on different supporting surfaces (e.g., cabinets, desks, and dining tables) for embodied AI simulation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md

### Dataset

- The authors curated a dataset of 300,000 real residential floorplans to train a large language model for generating whole-home floorplans. (confidence: 1.00)
  Evidence: First, we curate a large-scale dataset of 300K real residential floorplans to train a large language model for whole-home floorplan generation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md
- The authors plan to release their floorplan dataset and 5,000 fully furnished scenes to the public. (confidence: 1.00)
  Evidence: Finally, alongside our generation pipeline, we will release the floorplan dataset and 5K fully furnished scenes to the community. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md

### Claim

- Experiments and user studies show that the pipeline generates indoor spaces with higher layout diversity and better 3D design appeal, outperforming previous methods quantitatively and qualitatively. (confidence: 1.00)
  Evidence: Experiments and user studies demonstrate that our pipeline produces indoor spaces with greater layout diversity and stronger 3D design appeal, outperforming prior methods on both quantitative and qualitative metrics. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md

### Limitation

- Existing indoor scene generation methods often depend on hand-crafted rules or isolated sub-tasks, leading to whole-home scenes that lack global coherence, realism, and readiness for simulation. (confidence: 1.00)
  Evidence: Existing methods often rely on hand-crafted rules or focus on isolated sub-tasks (e.g., floorplan synthesis or single-room furnishing), producing whole-home scenes that lack global coherence, realism, and simulation readiness. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/homeworld/summary.md

## Incantation: Natural Language as the Action Interface for Multi-Entity Video World Models

`incantation` | authors: Shangwen Zhu, Qianyu Peng, Zhao Pu, Zhilei Shu, Xiangrui Ke, Zhaohu Xing, Zizhao Tong, Zeqing Wang, Xinyu Cui, Huangji Wang, Jian Zhao, Yeying Jin, Fan Cheng, Ruili Feng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/QwenLM/Qwen3-VL, https://github.com/madebyollin/taehv, https://github.com/zhushangwen/Incantation

### Method

- Incantation is an interactive video world model that uses natural language as the action interface for per-latent-frame (0.25 s) conditioning, supporting simultaneous multi-entity control and concept-level cross-entity transfer. (confidence: 1.00)
  Evidence: we present Incantation, the first interactive video world model with per-latent-frame (0.25 s) natural-language conditioning that supports simultaneous multi-entity control and concept-level cross-entity transfer beyond any fixed rendering pipeline. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex
- The model architecture pairs a pretrained bidirectional video backbone with frame-local text cross-attention. (confidence: 1.00)
  Evidence: We pair a pretrained bidirectional video backbone with frame-local text cross-attention [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex
- Real-time long-horizon streaming is enabled through ODE-initialized Self-Forcing distillation combined with a RoPE-decoupled sliding KV-cache. (confidence: 1.00)
  Evidence: and enable real-time long-horizon streaming through ODE-initialized Self-Forcing distillation with a RoPE-decoupled sliding KV-cache. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex

### Dataset

- A preview subset of the Incantation dataset was released, consisting of manually collected Elden Ring player-boss combat clips with structured action-oriented metadata. (confidence: 1.00)
  Evidence: We have released a preview subset of the Incantation dataset at https://huggingface.co/datasets/zhush/incantation-elden-ring-scenes, containing manually collected Elden Ring player-boss combat clips with structured action-oriented metadata. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex

### Claim

- Incantation outperforms the Action-Index baseline on cross-entity transfer (89% vs. 43%) and out-of-vocabulary prompts (90% vs. 0%). (confidence: 1.00)
  Evidence: We surpass the Action-Index baseline on cross-entity transfer (89% vs. 43%) and out-of-vocabulary prompts (90% vs. 0%) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex
- The 2-step student model achieves 19.7 FPS at 480p resolution and maintains a stable FVD over 2-hour rollouts. (confidence: 1.00)
  Evidence: and our 2-step student sustains 19.7 FPS at 480p with stable FVD over 2-hour rollouts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex
- The Incantation architecture and training recipe were successfully applied to The King of Fighters by only changing the per-entity action vocabulary slots. (confidence: 1.00)
  Evidence: We further apply the same architecture and training recipe to The King of Fighters, changing only the per-entity action vocabulary slots. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/incantation/source.tex

## Kairos: A Scalable Serving System for Physical AI

`kairos` | authors: Yinwei Dai, Ganesh Ananthanarayanan, Landon Cox, Xenofon Foukas, Bozidar Radunovic, Ravi Netravali | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- Kairos is a multi-robot serving system designed for physical AI that treats the generate-execute loop as a first-class citizen and actively involves itself in the execution phase. (confidence: 1.00)
  Evidence: To fill this gap, we design \name{}, the first multi-robot serving system that makes the generate-execute loop a first-class citizen, with active involvement in the execution phase. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- The paper targets frontier physical AI models including Vision-Language-Action models (VLAs), Video Action Models (VAMs), and World Action Models (WAMs). (confidence: 1.00)
  Evidence: Our work targets this family of frontier physical AI models (VLAs, VAMs, WAMs); we next explain their key properties and differences compared to LLMs used in digital AI. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- State-of-the-art physical AI models use action chunking, where a single inference call produces a chunk of N actions simultaneously using diffusion, to enable high-frequency control. (confidence: 1.00)
  Evidence: State-of-the-art physical AI models instead employ \emph{action chunking}: a single inference call produces a chunk of $N$ actions at the same time using diffusion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- To reduce robot idling between inference rounds, existing physical AI systems use asynchronous inference, which launches the next inference while the robot is still executing the current action chunk. (confidence: 1.00)
  Evidence: To mitigate this, existing physical AI systems \cite{vlash, smolvla, rtc,dream_zero, gigaworldpolicy} apply \emph{asynchronous inference}, which launches the next inference while the robot is still executing the current chunk [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- The execution horizon (H) is a parameter that controls how many actions are executed from each generated chunk, allowing a trade-off between accuracy and resource demand, with actions beyond H being discarded to mitigate execution staleness. (confidence: 1.00)
  Evidence: To mitigate this staleness, robotic practitioners tune the {\em execution horizon, H}, which is a knob that controls how many actions are executed from each chunk. The set of actions in the chunk beyond the first $H$ are discarded. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex

### Claim

- Kairos reduces the average end-to-end task latency by 31.8% to 66.5% compared to state-of-the-art digital AI serving practices across various physical AI models and robots, with gains scaling with the robot fleet size. (confidence: 1.00)
  Evidence: Across a wide range of physical AI models and robots, \name{} reduces the average end-to-end task latency by 31.8--66.5\% over state-of-the-art digital AI serving practices, with gains scaling with the robot fleet size. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- Physical AI tasks involve multiple rounds of inference and action execution, generating a chunk of actions per inference round, and asynchronously interleaving inference and execution, which makes existing digital AI serving systems unsuited for them. (confidence: 1.00)
  Evidence: Physical AI tasks are characterized by inference properties that are markedly different from digital AI. They consist of multiple rounds of inference and action execution, generating a chunk of actions in each inference round, and asynchronously interleaving inference and execution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex
- The optimal execution horizon varies widely across tasks, with about 40% of tasks experiencing no drop in accuracy even when the horizon is 40 or more out of a maximum of 50. (confidence: 1.00)
  Evidence: As Figure~\ref{fig:optimal_horizon} shows, $\sim40\%$ of tasks see no drop in accuracy even for $H \geq 40$ out of a maximum of 50. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/kairos/source.tex

## L-SDPPO: Policy Optimization of Spiking Diffusion Policy for Intra-vehicular Robotic Manipulation

`l-sdppo` | authors: Liwen Zhang, Dong Zhou, Guanghui Sun, Yifei Zheng, Yuhui Hu, Kaihong Ouyang, Zuoquan Zhao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Dongzhou-1996/L-SDPPO

### Method

- The paper proposes L-SDPPO, a low-energy intra-vehicular robotic manipulation framework where the Spiking Diffusion Policy (SDP) is optimized with a reinforcement learning algorithm. (confidence: 1.00)
  Evidence: We therefore propose a low-energy intra-vehicular robotic manipulation framework, L-SDPPO, in which the Spiking Diffusion Policy (SDP) is optimized with a reinforcement learning (RL) algorithm. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex
- The state-dependent latency injection (SDLI) mechanism is proposed to mimic biological neural delays and dynamically regulate the timing of input information, addressing the insufficient perception of dynamic spatiotemporal features in microgravity. (confidence: 1.00)
  Evidence: Furthermore, to address the insufficient perception of dynamic spatiotemporal features in microgravity, we propose the statedependent latency injection (SDLI) mechanism, which mimics biological neural delays to dynamically regulate the timing of input information. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/summary.md
- The Spiking Diffusion Policy (SDP) parameterizes the noise prediction network using a Spiking Neural Network (SNN) to achieve high energy efficiency. (confidence: 1.00)
  Evidence: To achieve high energy efficiency, we parameterize the noise prediction network $\boldsymbol{\mu}_\theta$ using a SNN. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex
- The SDP architecture utilizes a hybrid input encoding module that maps continuous sensory data into the spiking domain by concatenating the noisy action, temporal feature of the discrete timestep, and conditional feature of the observation. (confidence: 1.00)
  Evidence: To process multi-modal inputs, a unified encoding module maps continuous sensory data into the spiking domain. The discrete timestep $k$ is embedded into a temporal feature $\boldsymbol{e}_k$ via sinusoidal positional encoding, while the observation $\boldsymbol{s}$ is processed by a state encoder to extract the conditional feature $\boldsymbol{e}_s$. These are concatenated with the noisy action $\boldsymbol{x}^k$ to form the joint input [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex

### Benchmark

- The authors present a benchmark for intra-vehicular robotic manipulation that includes an expert dataset curated across five representative scenarios, such as hatch operation and dynamic stowing. (confidence: 1.00)
  Evidence: A benchmark for intra-vehicular robotic manipulation is presented, in which an expert dataset is curated across five representative scenarios. This benchmark covers high-precision tasks such as hatch operation and dynamic stowing to address the inherent challenges of manipulation in microgravity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex

### Claim

- Evaluation on five representative intra-vehicular daily tasks demonstrates that the proposed method consistently achieves higher success rates and lower energy consumption compared to state-of-the-art robotic manipulation methods. (confidence: 1.00)
  Evidence: Evaluation on five representative intra-vehicular daily tasks (e.g., hatch opening and precision container capping) shows that our method consistently achieves higher success rates and lower energy consumption, compared to the state-of-the-art robotic manipulation methods. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex

### Limitation

- Diffusion policies (DP) are limited by their iterative sampling process, which consumes too much energy for the limited power budgets of spacecraft. (confidence: 1.00)
  Evidence: Diffusion policies (DP) can model these complex actions, but their iterative sampling process consumes too much energy for the limited power budgets of spacecraft. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex
- Data-driven approaches like reinforcement learning and imitation learning often suffer from low sample efficiency or struggle with multi-modal action distributions. (confidence: 1.00)
  Evidence: Data-driven approaches like reinforcement learning (RL) \cite{capra2024learning, hou2020data} and imitation learning (IL) \cite{li2025research_aca, wang2024novel} offer more flexibility, but they often suffer from low sample efficiency or struggle with multi-modal action distributions \cite{hua2021learning}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/l-sdppo/source.tex

## LAFP: Preserving Latent Action Structure in Latent Policy Learning via Flow Matching

`lafp` | authors: Jiexi Lyu, Xizhou Bu, Qingqiu Huang, Chufeng Tang, Xiaoshuai Hao, Hongbo Wang, Wei Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The Latent Action Flow Policy (LAFP) framework utilizes flow matching for latent policy learning and incorporates an inference-time interpolation mechanism to address misalignment caused by stochasticity. (confidence: 1.00)
  Evidence: To address these, we propose Latent Action Flow Policy (LAFP), which leverages flow matching for latent policy learning and introduces an inference-time interpolation mechanism to mitigate stochasticity-induced misalignment. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex
- The pretraining stage follows the LAOM framework, jointly training an Inverse Dynamics Model (IDM), a Forward Dynamics Model (FDM), and an action decoder, while discretizing the latent space using a VQ-VAE. (confidence: 1.00)
  Evidence: We follow the LAOM framework to learn a latent action space by jointly training an IDM and an FDM, along with an action decoder, as illustrated in Stage 1 of Fig.\ref{fig:mainmethod}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex
- During the distillation stage, behavior cloning is replaced with a conditional flow matching policy that learns a transport process from a simple prior to the conditional distribution of latent actions. (confidence: 1.00)
  Evidence: To capture the underlying multi-modal structure, we replace it with a conditional flow matching policy \pi_{\text{flow}}, which learns a transport process from a simple prior to the conditional distribution of latent actions given o_t. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex
- In the post-training stage, an inference-time interpolation mechanism is used to train the action decoder by interpolating between the source Gaussian noise distribution and the target latent action distribution. (confidence: 1.00)
  Evidence: Additionally, in the post-training stage, we introduce an inference-time interpolation mechanism that performs flow matching inference by interpolating between the source Gaussian noise distribution and the target latent action distribution to train the action decoder [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex

### Benchmark

- The proposed method is evaluated on 16 Procgen tasks to demonstrate its ability to preserve the intrinsic structure of the pretrained latent action space and improve downstream imitation learning. (confidence: 1.00)
  Evidence: The results on 16 Procgen tasks demonstrate that learning latent policies via flow matching can explicitly preserve the intrinsic structure of the pretrained latent action space, leading to consistent improvements in downstream imitation learning performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex

### Claim

- LAFP outperforms prior methods on downstream imitation learning tasks, achieving a 10-15% improvement in success rate with less than 1x additional inference overhead. (confidence: 1.00)
  Evidence: Experimental results demonstrate that LAFP consistently outperforms prior methods on downstream imitation learning tasks, achieving up to 10–15\% improvement in success rate while incurring less than 1× additional inference overhead. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex

### Limitation

- Directly applying flow matching to latent policy learning causes a misalignment between latent and physical actions during action decoder training because of the stochastic nature of the learned policy. (confidence: 1.00)
  Evidence: While flow matching provides a potential alternative, directly applying it leads to a misalignment between latent actions and physical actions during action decoder training, due to the stochastic nature of the learned policy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lafp/source.tex

## LARA: Latent Action Representation Alignment for Vision-Language-Action Models

`lara` | authors: Mengya Liu, Baoxiong Jia, Jiangyong Huang, Jingze Zhang, Siyuan Huang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/lmy1001/LARA

### Method

- LARA (Latent Action Representation Alignment) is a framework that jointly optimizes Latent Action Models (LAM) and Vision-Language-Action (VLA) models via representation alignment. (confidence: 1.00)
  Evidence: we propose Latent Action Representation Alignment (LARA), a plug-and-play framework that jointly optimizes LAM and VLA via representation alignment. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/summary.md
- The Latent Action Model (LAM) in LARA uses an architectural design based on Moto-GPT, consisting of Visual Encoding, Motion Extraction (M-Former), Quantization, and Reconstruction stages. (confidence: 1.00)
  Evidence: We adopt the architectural design from Moto-GPT~\cite{chen2024moto} for our Latent Action Model. The process operates in four stages: [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/source.tex
- The VLA policy in LARA uses Eagle-2 as the vision-language backbone and models the diffusion process with a 16-layer Diffusion Transformer (DiT). (confidence: 1.00)
  Evidence: We employ Eagle-2~\cite{li2025eagle} as the vision-language backbone to process visual observations and task instructions. ... The diffusion process is modeled by a Diffusion Transformer (\ac{dit}) comprising $L=16$ layers [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/source.tex
- During LARA joint training, the LARA loss aligns the latent action extracted from image pairs with the hidden states of the L-2 layer of the DiT, specifically using the hidden state token corresponding to the final timestep of the action chunk to ensure temporal consistency. (confidence: 1.00)
  Evidence: The LARA loss is implemented between $z_t$ extracted from ($I_t, I_{t+C}$), with $C=16$, and aligned with $L-2$ layer of hidden states $h_t^\theta$. Crucially, to ensure temporal consistency, we select the hidden state token corresponding to the final timestep of the action chunk ($t+C$) for alignment. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/source.tex

### Dataset

- LARA is trained on a curated subset of the Open XEmbodiment (OXE) dataset that is filtered for single-arm end-effector control trajectories. (confidence: 1.00)
  Evidence: We curate a targeted subset of the Open XEmbodiment (OXE) dataset~\cite{o2024open}, specifically filtering for trajectories featuring single-arm end-effector control. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/source.tex

### Claim

- Joint optimization in LARA allows LAMs to learn with action trajectories to avoid spurious visual changes, while VLAs are regularized by forward dynamics to reduce hallucinations of ineffective trajectories. (confidence: 1.00)
  Evidence: This enables reciprocal benefits where LAMs learn with action trajectories to avoid spurious visual changes, while VLAs are regularized by forward dynamics learned within LAMs to reduce hallucinations of functionally ineffective trajectories. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/summary.md
- LARA achieves average improvements of approximately 10%, 5%, and 15% for pre-training, post-training enhancement of pre-trained VLA models, and LAM refinement, respectively, across simulation and real-world benchmarks. (confidence: 1.00)
  Evidence: achieving an average of ~10%, ~5%, and ~15% improvement over 3 simulation and 1 meticulously designed real-world robotic manipulation benchmarks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/summary.md

### Limitation

- Existing Visual-language action (VLA) models are limited by the scarcity of real-world robot action datasets and their reliance on large-scale, high-quality data. (confidence: 1.00)
  Evidence: their performance depends on large-scale, high-quality data and is limited by the scarcity of real-world robot action datasets. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lara/summary.md

## LEGS: Fine-Tuning Teleop-Free VLAs for Humanoid Loco-manipulation in an Embodied Gaussian Splatting World

`legs` | authors: Hojune Kim, Timothy Chen, Jiankai Sun, Lars W. Osterberg, Qianzhong Chen, Ke Wang, Mac Schwager | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- LEGS is a hybrid simulator that composites a mesh foreground over a photorealistic 3D Gaussian Splatting (3DGS) background reconstructed from a handheld scene capture. (confidence: 1.00)
  Evidence: We present LEGS (Loco-manipulation via Embodied Gaussian Splatting), a hybrid simulator that composites a mesh foreground (robot, objects, props) over a photorealistic 3D Gaussian Splatting (3DGS) background reconstructed from a handheld scene capture. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- LEGS uses a procedural motion-primitive generator to synthesize labeled demonstrations at scale without human teleoperation. (confidence: 1.00)
  Evidence: LEGS uses a procedural motion-primitive generator to synthesize labeled demonstrations at scale without human teleoperation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- LEGS employs a deterministic two-stage color calibration to align the rendered 3DGS image to the robot's deployment camera. (confidence: 1.00)
  Evidence: and a deterministic two-stage color calibration to align the rendered 3DGS image to the robot's deployment camera. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- Humanoid motion is recorded independently of scene appearance in LEGS, allowing auto-generated demonstrations to be re-rendered under new backgrounds and object meshes to augment training data for robustness to scene variations. (confidence: 1.00)
  Evidence: Humanoid motion is recorded independently of scene appearance in LEGS, allowing the same auto-generated demonstrations to be re-rendered under new backgrounds and object meshes--covering a new scene at more than 15x lower cost than teleoperation--to augment training data for robustness to scene variations. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- The LEGS simulator decouples a visual frontend (3DGS and mesh compositor with color calibration) from a physics backend (MuJoCo with the low-level whole-body controller). (confidence: 1.00)
  Evidence: The simulator decouples a visual frontend (3DGS and mesh compositor with color calibration) from a physics backend (MuJoCo with the low-level whole-body controller). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/source.tex
- The color calibration process uses a per-mesh diagonal scale in linear RGB and a global color-correction matrix fit by least squares from a 24-patch ColorChecker photographed by both cameras. (confidence: 1.00)
  Evidence: where $c_m$ is a mesh vertex color, $c_b$ a background \gsplat pixel, $c_d$ the deployment-camera pixel, $R(\cdot)$ a per-mesh diagonal scale in linear RGB matching each mesh's rendered mean to the handheld scan inside its SAM2~\citep{ravi2025sam} mask, $\sqcup$ depth-test compositing, and $M \in \mathbb{R}^{3\times 3}$ a global color-correction matrix fit by least squares from a 24-patch ColorChecker photographed by both cameras. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/source.tex

### Benchmark

- The evaluation is conducted on a Unitree G1 humanoid robot across three pick-and-place tasks of increasing whole-body difficulty and three VLA backbones (psi_0, pi_0.5, GR00T N1.6). (confidence: 1.00)
  Evidence: On a Unitree G1 humanoid robot, across three pick-and-place tasks of increasing whole-body difficulty and three VLA backbones (psi_0, pi_0.5, GR00T N1.6) [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md

### Claim

- A policy trained purely on LEGS data matches or exceeds one trained on human teleoperation demos on every experiment. (confidence: 1.00)
  Evidence: a policy trained purely on LEGS data matches or exceeds one trained on human teleoperation demos on every experiment. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- LEGS outperforms a mesh-only simulation baseline, demonstrating that photorealistic rendering is a key enabler for synthetic data transfer. (confidence: 1.00)
  Evidence: It also outperforms a mesh-only simulation baseline that ablates the effect of the 3DGS background, showing that photorealistic rendering is a key enabler for synthetic data transfer. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md
- Under combined object-and-scene appearance shift, the policy trained on re-rendered LEGS-AUG data maintains task success while the baseline trained on teleoperation data fails entirely. (confidence: 1.00)
  Evidence: Under combined object-and-scene appearance shift, the policy trained on re-rendered LEGS-AUG data maintains task success while the baseline trained on teleoperation data fails entirely. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/legs/summary.md

## LLM-Guided Evolution for Medical Decision Pipelines

`2606_07342` | authors: Ivan Sviridov, Artem Oskin, Ivan Panin, Iaroslav Bespalov, Dmitry Dylov, Ivan Oseledets, Aleksandr Nesterov | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/BIMSBbioinfo/medLLMbenchmark, https://github.com/univanxx/llm_guided_evo_medical

### Method

- The paper studies LLM-guided MAP-Elites evolution as an inference-time alternative for discovering medical decision strategies. (confidence: 1.00)
  Evidence: We study LLM-guided MAP-Elites evolution as an inference-time alternative for discovering medical decision strategies [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex
- The authors formulate urgency triage, interactive consultation, and medical image classification as evolutionary searches over executable artifacts optimized by task-specific fitness functions. (confidence: 1.00)
  Evidence: We formulate urgency triage, interactive consultation, and medical image classification as evolutionary searches over executable artifacts optimized by task-specific fitness functions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex
- The approach uses task-specific candidate representations and MAP-Elites configurations, ranging from executable decision programs to prompt-producing modules. (confidence: 1.00)
  Evidence: We use task-specific candidate representations and MAP-Elites configurations, ranging from executable decision programs to prompt-producing modules to support search across heterogeneous clinical decision settings rather than a single fixed pipeline. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex

### Dataset

- The study uses the PneumoniaMNIST dataset for medical image classification, where prompt-only evolution improves frozen MedGemma VLMs while preserving strict JSON outputs. (confidence: 1.00)
  Evidence: In PneumoniaMNIST, prompt-only evolution improves frozen MedGemma VLMs while preserving strict JSON outputs. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex

### Benchmark

- The study evaluates triage performance using the Semigran benchmark and measures safety-weighted held-out performance on MIMIC-ESI. (confidence: 1.00)
  Evidence: In triage, evolved programs increase Semigran accuracy from $77.3\%$ to $87.1\%$ and emergency recall from $0.60$ to $0.97$, while improving safety-weighted held-out MIMIC-ESI performance. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex
- The study uses iCRAFTMD as a held-out benchmark to evaluate the transferability of evolved interactive consultation policies. (confidence: 1.00)
  Evidence: In interactive consultation, evolved policies improve the accuracy--cost frontier across Llama-3, Qwen-3.5, and Gemma-4 and transfer to held-out iCRAFTMD. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex

### Claim

- In the triage task, evolved programs increase Semigran accuracy from 77.3% to 87.1% and emergency recall from 0.60 to 0.97. (confidence: 1.00)
  Evidence: In triage, evolved programs increase Semigran accuracy from $77.3\%$ to $87.1\%$ and emergency recall from $0.60$ to $0.97$ [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex
- In interactive consultation, evolved policies improve the accuracy-cost frontier across Llama-3, Qwen-3.5, and Gemma-4 and transfer to the held-out iCRAFTMD benchmark. (confidence: 1.00)
  Evidence: In interactive consultation, evolved policies improve the accuracy--cost frontier across Llama-3, Qwen-3.5, and Gemma-4 and transfer to held-out iCRAFTMD. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex
- Qualitative analysis indicates that performance gains stem from interpretable program-level mechanisms like calibrated triage boundaries, targeted evidence acquisition, selective commitment, and finding-oriented visual decision rules, rather than just superficial prompt rewording. (confidence: 1.00)
  Evidence: Qualitative analysis shows that the gains come from interpretable program-level mechanisms, calibrated triage boundaries, targeted evidence acquisition, selective commitment, and finding-oriented visual decision rules, rather than superficial prompt rewording alone. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07342/source.tex

## LUCID-SAE: Learning Unified Vision-Language Sparse Codes for Interpretable Concept Discovery

`lucid-sae` | authors: Difei Gu, Yunhe Gao, Gerasimos Chatzoudis, Zihan Dong, Guoning Zhang, Bangwei Guo, Yang Zhou, Mu Zhou, Dimitris Metaxas | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- LUCID is a unified vision-language sparse autoencoder that learns a shared latent dictionary for image patch and text token representations while reserving private capacity for modality-specific details. (confidence: 1.00)
  Evidence: we introduce LUCID (Learning Unified vision-language sparse Codes for Interpretable concept Discovery), a unified vision-language sparse autoencoder that learns a shared latent dictionary for image patch and text token representations, while reserving private capacity for modality-specific details. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- LUCID achieves feature alignment by coupling shared codes with a learned optimal transport matching objective without requiring labels. (confidence: 1.00)
  Evidence: We achieve feature alignment by coupling the shared codes with a learned optimal transport matching objective without the need of labeling. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- The authors developed GCMT (Guided Cross-Modal Transport), which combines entropy-regularized transport with structural and contextual guidance to align image patches and text tokens. (confidence: 1.00)
  Evidence: We develop GCMT (Guided Cross-Modal Transport), which combines entropy-regularized transport with structural and contextual guidance to establish the fine-grained alignment between image patches and text tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- The paper introduces an automated dictionary interpretation pipeline based on cross-modal concept clustering without manual annotation. (confidence: 1.00)
  Evidence: We demonstrate an automatic neuron interpretation pipeline through cross-modal concept clustering, revealing coherent semantic specializations without manual annotation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex

### Claim

- LUCID's shared features capture diverse semantic categories beyond objects, such as actions, attributes, and abstract concepts. (confidence: 1.00)
  Evidence: Our analysis reveals that LUCID's shared features capture diverse semantic categories beyond objects, including actions, attributes, and abstract concepts, demonstrating a comprehensive approach to interpretable multimodal representations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- LUCID yields interpretable shared features that support patch-level grounding, establish cross-modal neuron correspondence, and enhance robustness against the concept clustering problem. (confidence: 1.00)
  Evidence: LUCID yields interpretable shared features that support patch-level grounding, establish cross-modal neuron correspondence, and enhance robustness against the concept clustering problem in similarity-based evaluation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex

### Limitation

- Current sparse autoencoders (SAEs) are trained independently for each modality, which prevents concepts learned in one modality from having guaranteed correspondence to analogous concepts in another. (confidence: 1.00)
  Evidence: A key limitation of SAEs is that they are always trained independently for each modality... Consequently, concepts learned in one modality lack the guaranteed correspondence to analogous concepts in the another. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- Concept Bottleneck Models (CBMs) require extensive manual concept annotations during training, and the predefined concepts may not align with the features the model naturally learns. (confidence: 1.00)
  Evidence: They require extensive concept annotations during training. The predefined concept set requires heavy manual design and may not align with the features the model naturally learns [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- Current SAE methodologies have been predominantly applied to language models, with limited exploration in vision domains and vision-language cross-modal concept alignment. (confidence: 1.00)
  Evidence: First, the methodology has been predominantly applied to language models with limited exploration in vision domains and vision-language cross-modal concept alignment. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex
- Features discovered by SAEs are highly fine-grained and task-specific, making them difficult to interpret manually, and current efforts lack mechanisms for automatic vision concept interpretation. (confidence: 1.00)
  Evidence: Second, the features discovered by SAEs are highly fine-grained and task-specific, making them difficult to interpret through manual inspection alone... In particular, current efforts lack mechanisms for automatic vision concept interpretation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/lucid-sae/source.tex

## Lagrangian Perturbation Diffusion Steering: Latent Reinforcement Learning for Generative Policies

`2606_01151` | authors: Hikmet Simsir, Ozgur S. Oguz | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes Lagrangian Perturbation Diffusion Steering (LP-DS), a lightweight adaptation method that improves a frozen generative policy by learning a compact noise-space perturbation before decoding. (confidence: 1.00)
  Evidence: We propose Lagrangian Perturbation Diffusion Steering (LP-DS), a lightweight adaptation method that improves a frozen generative policy by learning a compact noise-space perturbation before decoding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- LP-DS optimizes the noise-space perturbation using a Lagrangian trust-region objective to improve downstream value while constraining deviation from the latent prior. (confidence: 1.00)
  Evidence: LP-DS optimizes this perturbation with a Lagrangian trust-region objective, improving downstream value while constraining deviation from the latent prior. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- LP-DS shifts Gaussian noise inputs by adding a state-conditioned residual perturbation, formulated as w = \epsilon + \Delta_\theta(s). (confidence: 1.00)
  Evidence: LP-DS shifts Gaussian noise inputs via $w = \epsilon + \Delta_\theta(s)$ and optimizes $\Delta_\theta$ with a \emph{Lagrangian trust-region objective} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex

### Benchmark

- The proposed method is evaluated on RoboMimic manipulation, OpenAI Gym locomotion, and Adroit dexterous manipulation benchmarks. (confidence: 1.00)
  Evidence: Across RoboMimic manipulation, OpenAI Gym locomotion, and Adroit dexterous manipulation benchmarks, LP-DS improves sample efficiency, success, and return [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex

### Claim

- LP-DS achieves return improvements of up to 25% over prior baselines while maintaining higher action-space entropy than unconstrained noise-space steering. (confidence: 1.00)
  Evidence: LP-DS improves sample efficiency, success, and return while maintaining higher action-space entropy than unconstrained noise-space steering, with return improvements of up to 25% over prior baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- LP-DS is applicable beyond compact diffusion policies and simulated benchmarks, as demonstrated by evaluations with flow-matching backbones, a large vision-language-action model, and physical Franka robot deployment. (confidence: 1.00)
  Evidence: Additional evaluations with flow-matching backbones, a large vision-language-action model, and physical Franka deployment show that LP-DS is not limited to compact diffusion policies or simulated benchmarks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- LP-DS mitigates mode collapse compared to prior-replacing noise-space steering methods, thereby preserving higher action-space diversity. (confidence: 1.00)
  Evidence: We show that LP-DS mitigates mode collapse relative to prior-replacing noise-space steering, preserving higher action-space diversity while achieving strong performance across manipulation, locomotion, and dexterous-control benchmarks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex

### Limitation

- Behavior cloning with high-capacity generative policies is often limited by demonstration coverage and distribution shift. (confidence: 1.00)
  Evidence: Behavior cloning with high-capacity generative policies achieves strong imitation performance, but is often limited by demonstration coverage and distribution shift. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex
- Direct reinforcement learning fine-tuning of large action decoders is frequently unstable and sample inefficient. (confidence: 1.00)
  Evidence: Direct reinforcement learning fine-tuning can improve performance, but updating large action decoders is frequently unstable and sample inefficient. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01151/source.tex

## Latent Diffusion Policy: Shaping Latent Spaces for Diffusion-Based Robotic Manipulation

`latent-diffusion-policy` | authors: Zhexuan Zhou, Yichen Lai, Jinhao Zhang, Huizhe Li, Youmin Gong, Jie Mei | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Less Is More: Training-Free Acceleration Framework of 3D Diffusion Models for Low-Count PET Denoising via Global-Local Trajectory Reduction

`less-is-more` | authors: Yuhan Liu, Scott M. Leonard, Marlee Crews, Muhannad Fadhel, Jinkui Hao, Tianqi Chen, Ryan J. Avery, Bo Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Advanced-AI-in-Medicine-and-Physics-Lab/LIM

### Method

- The paper proposes a training-free Global-Local Skipping Strategy to accelerate diffusion model-based 3D PET denoising. (confidence: 1.00)
  Evidence: To address these challenges, we propose a training-free Global-Local Skipping Strategy that accelerates diffusion model-based 3D PET denoising while simultaneously improving reconstruction quality. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex
- The global denoising step skipping strategy initializes the reverse diffusion process from an intermediate denoising step using a noise-consistent transformation of the low-count input. (confidence: 1.00)
  Evidence: Specifically, we introduce: (i) a global denoising step skipping strategy that initializes the reverse diffusion process from an intermediate denoising step using a noise-consistent transformation of the low-count input, substantially reducing the number of required denoising steps; [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex
- The local feature reuse shortcut reuses slowly-varying high-level U-Net features across neighboring denoising steps to reduce per-step computation. (confidence: 1.00)
  Evidence: and (ii) a local feature reuse shortcut that reuses slowly-varying high-level U-Net features across neighboring denoising steps, further reducing per-step computation while preserving image fidelity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex

### Dataset

- The proposed approach is evaluated on multiple PET tracers from in-house and public datasets, including 18F-FDG PET, 68Ga-DOTATATE PET, and 18F-PSMA PET. (confidence: 1.00)
  Evidence: We evaluate the proposed approach on multiple PET tracers from in-house and public datasets, including $^{18}$F-FDG PET, $^{68}$Ga-DOTATATE PET, and $^{18}$F-PSMA PET, [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex

### Claim

- The proposed method demonstrates consistent acceleration of over an order of magnitude alongside improved or comparable reconstruction performance relative to the full-step baseline. (confidence: 1.00)
  Evidence: demonstrating consistent acceleration of over an order of magnitude alongside improved or comparable reconstruction performance relative to the full-step baseline. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex
- Blinded reader studies confirm enhanced clinical confidence and perceived diagnostic quality using the proposed method. (confidence: 1.00)
  Evidence: Blinded reader studies further confirm enhanced clinical confidence and perceived diagnostic quality. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex

### Limitation

- The iterative sampling procedure of diffusion-model-based methods becomes prohibitively expensive when applied to high-resolution 3D PET volumes, introducing substantial inference latency that limits practical clinical deployment. (confidence: 1.00)
  Evidence: Diffusion-model-based methods have demonstrated strong potential for restoring low-count PET to near high-count quality, but their iterative sampling procedure becomes prohibitively expensive when applied to high-resolution 3D PET volumes, introducing substantial inference latency that limits practical clinical deployment. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/less-is-more/source.tex

## Let It Be Simple: One-Step Action Generation for Vision-Language-Action Models

`2606_05737` | authors: Yitong Chen, Shiduo Zhang, Jingjing Gong, Xipeng Qiu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed method for one-step action generation in VLA models relies on biasing the training time distribution toward high-noise states, without using teacher models, distillation, or auxiliary objectives. (confidence: 1.00)
  Evidence: We keep standard velocity prediction and add no teacher model, distillation stage, or auxiliary objective; in our main recipe, we simply bias the training time distribution toward high-noise states. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex
- The model uses Conditional Flow Matching with a noise shift applied to the base time sample to shift samples toward high noise (t -> 0). (confidence: 1.00)
  Evidence: Given a base time sample $u\in[0,1]$, we apply a simple \textbf{noise shift}~\cite{esser2024flow}
\begin{equation}
t = \frac{u}{1 + (\alpha-1)(1-u)},
\label{eq:noise_shift}
\end{equation}
where $\alpha>1$ shifts samples toward $t\to0$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex
- The VLA architecture uses SigLIP for vision encoding, PaliGemma for multimodal fusion, and a lightweight action decoder to predict velocities. (confidence: 1.00)
  Evidence: We build on OpenPI~\cite{physical_intelligence_pi0_2024}, using SigLIP~\cite{zhai2023siglip} for vision and PaliGemma~\cite{beyer2024paligemma} for multimodal fusion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex
- The base training-time distribution used for the full-encoder validations is Beta(1, 1.5), which provides a slightly high-noise biased time distribution. (confidence: 1.00)
  Evidence: The base training-time distribution is $\mathrm{Beta}(1,1.5)$, a slightly high-noise biased time distribution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex

### Dataset

- The authors introduce a controlled MNIST grid-to-sequence task to isolate the effect of the rich-condition, compact-target structure. (confidence: 1.00)
  Evidence: We first isolate the effect in a controlled MNIST grid-to-sequence task, then test it with extensive robot-policy experiments. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex

### Benchmark

- The paper evaluates the proposed method on the standard LIBERO, LIBERO-Plus, and LIBERO-Pro benchmarks. (confidence: 1.00)
  Evidence: Across standard LIBERO, LIBERO-Plus, and LIBERO-Pro, one-step policies trained with high-noise biased schedules generally match ten-step decoding under the same recipe [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex

### Claim

- One-step policies trained with high-noise biased schedules match ten-step decoding on LIBERO, LIBERO-Plus, and LIBERO-Pro, and can exceed ten-step policies trained with a uniform time distribution on standard LIBERO. (confidence: 1.00)
  Evidence: Across standard LIBERO, LIBERO-Plus, and LIBERO-Pro, one-step policies trained with high-noise biased schedules generally match ten-step decoding under the same recipe, and on standard LIBERO can exceed ten-step policies trained with a uniform time distribution. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex
- Using a 1.4B VLM model with a 30M action head, one-step decoding achieves a 95.6% success rate on LIBERO-Long. (confidence: 1.00)
  Evidence: On a 1.4B VLM model with a 30M action head, one-step decoding reaches 95.6\% on LIBERO-Long. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex

### Limitation

- While shifting the training time distribution toward high-noise states improves one-step decoding, this same bias can negatively impact the performance of ten-step decoding. (confidence: 1.00)
  Evidence: The trend is clear: shifting training toward high-noise states improves one-step decoding, but the same bias can hurt ten-step decoding, and $\alpha=8$ is already too aggressive. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05737/source.tex

## Look on Demand: A Cognitive Scheduling Framework for Visual Evidence Acquisition in Multimodal Reasoning

`look-on-demand` | authors: Yang Zhang, Xiaoshuai Sun, Rui Zhao, Wujin Sun, Yidong Chen, Jiayi Ji, Qian Chen, Rongrong Ji | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/YangZhang2511/CSMR

### Method

- The paper proposes CSMR, a cognitive scheduling framework where a language model dynamically controls the reasoning process by deciding when to invoke an independent visual perception module. (confidence: 1.00)
  Evidence: we propose CSMR, a multimodal reasoning framework in which a language model controls the reasoning process by deciding when to invoke an independent visual perception module to acquire task-relevant visual evidence. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
- CSMR structurally decouples perception and reasoning to prevent visual evidence from being influenced by linguistic priors. (confidence: 1.00)
  Evidence: Meanwhile, the structural decoupling of perception and reasoning prevents the extracted visual evidence from being influenced by linguistic priors. [introduction] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
- The paper focuses on the single-stream VLM paradigm, utilizing a vision encoder and a decoder-only LLM that process visual and textual information in a unified token sequence. (confidence: 1.00)
  Evidence: we focus on the \emph{single-stream} paradigm, which is the dominant architecture in contemporary VLMs such as LLaVA~\cite{li2024llavanext-strong} and Qwen-VL~\cite{qwen3technicalreport}. A typical single-stream VLM consists of a vision encoder $E_v$ and a decoder-only LLM, which process visual and textual information within a unified token sequence. [preliminaries] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex

### Claim

- CSMR consistently outperforms representative baseline methods in accuracy under zero-shot settings across multiple multimodal reasoning benchmarks. (confidence: 1.00)
  Evidence: Experiments across multiple multimodal reasoning benchmarks show that CSMR consistently outperforms representative baseline methods in accuracy under a zero-shot setting. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/summary.md

### Limitation

- The text-centric pre-reasoning paradigm relies on static visual-to-text conversion, which compresses and loses fine-grained visual details before reasoning begins. (confidence: 1.00)
  Evidence: The former relies on static visual-to-text conversion, which tends to compress and lose fine-grained visual details. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
- The unified multimodal representation paradigm suffers from linguistic dominance caused by joint optimization and attention mechanisms, weakening faithfulness to visual evidence. (confidence: 1.00)
  Evidence: The latter is prone to linguistic dominance induced by joint optimization and attention mechanisms, leading to systematically weakened faithfulness to visual evidence during reasoning. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex
- In unified multimodal models, dominant linguistic priors from joint training objectives can bias visual representations toward the language space, leading to hallucinations and reduced faithfulness to image evidence. (confidence: 1.00)
  Evidence: under joint multimodal training objectives, dominant linguistic priors may bias visual representations toward the language space, undermining faithfulness to the original image evidence. [related_work] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/look-on-demand/source.tex

## MAGIS: Evidence-Based Multi-Agent Reasoning for Interpretable Strabismus Clinical Decision-Making

`magis` | authors: Xikai Tang, Yifan Wang, Jiafan Zhuang, Li Luo, Jinming Guo, Xiaoling Xie, Jiacheng Liu, Peiwei Wei, Lihao Zhong, Xiaoli Kang, Jie Cen, Guangqiang Yin, Kunliang Qiu, Ce Zheng, Zhun Fan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes MAGIS, an evidence-based Multi-Agent reasoning framework for interpretable strabismus diagnosis that transforms black-box generation into a structured diagnostic process. (confidence: 1.00)
  Evidence: we propose MAGIS, an evidence-based Multi-AGent reasoning for Interpretable Strabismus diagnosis framework. MAGIS transforms black-box end-to-end generation into a structured diagnostic process consisting of candidate hypothesis generation, dual-evidence constrained context, evidence-based corrective verification, and report generation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md
- MAGIS introduces a Dual-Evidence Constrained Context (DECC) mechanism that organizes visual evidence from nine cardinal positions of gaze and clinical diagnostic rules into a constrained context. (confidence: 1.00)
  Evidence: Specifically, we introduce a Dual-Evidence Constrained Context (DECC) mechanism that jointly organizes visual evidence from the photograph of the nine cardinal positions of gaze and evidence-based clinical diagnostic rules into a constrained context for reliable diagnostic reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md
- The framework includes an Evidence-Based Corrective Verification (EBCV) mechanism that verifies diagnostic hypotheses against visual evidence, heatmap cues, and clinical rules, triggering refinement upon inconsistency. (confidence: 1.00)
  Evidence: We further develop an Evidence-Based Corrective Verification (EBCV) mechanism that verifies whether the current diagnostic hypothesis is supported by visual evidence, heatmap-based visual cues, and evidence-based clinical diagnostic rules. Hypothesis refinement is triggered when inconsistency is detected. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md

### Benchmark

- The study evaluates the proposed framework on a fine-grained strabismus benchmark. (confidence: 1.00)
  Evidence: Experiments on a fine-grained strabismus benchmark demonstrate that MAGIS not only significantly outperforms other state-of-the-art diagnostic systems [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md
- The authors benchmarked mainstream LVLMs, including Gemini-3-Flash-Preview, GPT-5.2, and Qwen3-VL-Plus, on strabismus subtype classification and diagnostic reasoning to evaluate hallucination issues. (confidence: 1.00)
  Evidence: we benchmarked several mainstream LVLMs, including Gemini-3-Flash-Preview [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/source.tex

### Claim

- MAGIS significantly outperforms state-of-the-art diagnostic systems on the strabismus benchmark, improving the weighted F1 score from 72.0% to 91.3%. (confidence: 1.00)
  Evidence: improving the weighted F1 score from 72.0% to 91.3%, but also substantially improves the clinical reliability (consistency, alignment, and completeness) of generated diagnostic reports. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md
- MAGIS substantially improves the clinical reliability, including consistency, alignment, and completeness, of generated diagnostic reports. (confidence: 1.00)
  Evidence: but also substantially improves the clinical reliability (consistency, alignment, and completeness) of generated diagnostic reports. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md

### Limitation

- Existing deep learning methods for strabismus analysis mainly provide diagnostic predictions without transparent reasoning. (confidence: 1.00)
  Evidence: existing deep learning methods mainly provide diagnostic predictions without transparent reasoning [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/summary.md
- Large vision-language models (LVLMs) remain highly prone to hallucination in strabismus diagnosis, often producing conclusions inconsistent with visual evidence or misaligned with clinical criteria. (confidence: 1.00)
  Evidence: Nevertheless, they remain highly prone to hallucination in strabismus diagnosis, often producing conclusions that are inconsistent with visual evidence or misaligned with accepted clinical criteria [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/source.tex
- Existing hallucination mitigation approaches for LVLMs are inadequate for strabismus diagnosis because they control response-level generation rather than using evidence-based diagnostic verification. (confidence: 1.00)
  Evidence: A central limitation is that these methods mainly treat hallucination mitigation by controlling response-level generation, rather than using evidence-based diagnostic verification. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/magis/source.tex

## MBench: A Comprehensive Benchmark on Memory Capability for Video World Models

`mbench` | authors: Shengjun Zhang, Zhang Zhang, Simin Huang, Zhenyu Tang, Hanyang Wang, Chensheng Dai, Min Chen, Yifan Li, Yuxin Li, Yingjie Chen, Hao Liu, Chen Li, Jing Lyu, Yueqi Duan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/study-overflow/MBench

### Method

- MBench utilizes a hybrid evaluation strategy combining normalized heuristic metrics with VLM-augmented Visual Question Answering (VQA) for objective consistency assessment. (confidence: 1.00)
  Evidence: we employ a hybrid evaluation strategy that integrates normalized heuristic metrics with VLM-augmented Visual Question Answering (VQA). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex

### Dataset

- The MBench dataset is built upon rigorously curated real-captured long videos and comprises over 1040 standardized evaluation cases to audit state-of-the-art video world models. (confidence: 1.00)
  Evidence: Our benchmark is built upon a rigorously curated dataset of real-captured long videos, filtered to select clips that pose meaningful, graded challenges to long-term temporal stability [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex

### Benchmark

- MBench is a comprehensive benchmark designed to quantify and evaluate the long-term memory capability of generative video world models. (confidence: 1.00)
  Evidence: we present \textbf{MBench}, a comprehensive benchmark dedicated to quantifying and evaluating the memory capability of video world models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex
- MBench decomposes memory capability into three hierarchical core dimensions: entity consistency, environment consistency, and causal consistency, which are further refined into 12 quantifiable sub-dimensions. (confidence: 1.00)
  Evidence: We systematically decompose the memory capability of video world models into three hierarchical and complementary core dimensions: entity consistency, environment consistency, and causal consistency, which are further refined into 12 quantifiable sub-dimensions for comprehensive characterization of long-term memory. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/summary.md
- The Entity Consistency dimension in MBench is bifurcated into Object Consistency and Human Consistency to ensure both inanimate items and human agents maintain unique characteristics over time. (confidence: 1.00)
  Evidence: Entity Consistency focuses on the model’s ability to retain the persistent identity and attributes of individual participants throughout the generated sequence, which is bifurcated into Object Consistency and Human Consistency [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex
- The Environment Consistency dimension consists of Spatial Consistency, evaluating 3D scene layouts, and Rendering Consistency, monitoring global scene properties like lighting. (confidence: 1.00)
  Evidence: Environment Consistency measures the stability of the ``stage'' upon which the simulation unfolds. It consists of two primary second-level modules: Spatial Consistency, which evaluates the stability of 3D scene layouts and relative positioning, and Rendering Consistency, which monitors global scene properties like lighting and stylistic coherence. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex
- The Causal Consistency dimension is divided into Self-evolution, testing adherence to physical laws, and Interaction, measuring the propagation of consequences from external prompts or actions. (confidence: 1.00)
  Evidence: Causal Consistency assesses whether the model can uphold the logical relationships between prior states and future dynamics... This dimension is divided into Self-evolution, which tests the model’s internal adherence to inherent physical laws, and Interaction, which measures the model’s ability to remember and propagate the consequences of external prompts or actions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex

### Claim

- Evaluations using MBench reveal that most state-of-the-art video world models suffer from significant temporal drift and forgetfulness, struggling to maintain persistent world states during long-range evolution or interaction. (confidence: 1.00)
  Evidence: Most advanced models exhibit significant temporal drift and forgetfulness as the simulation horizon extends. By providing a rigorous, multi-faceted diagnostic tool, MBench reveals that current generative paradigms struggle to maintain a persistent world state under interaction or long-range evolution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex

### Limitation

- Existing evaluation benchmarks for video world models predominantly focus on visual quality, motion coherence, and text-video alignment, largely overlooking the long-term memory capabilities required for functional world modeling. (confidence: 1.00)
  Evidence: Currently, dominant evaluation protocols predominantly center on visual quality, motion coherence, and text-video alignment. While these metrics effectively quantify how realistic or well-aligned a generated video appears, they entirely overlook the long-term memory of world models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mbench/source.tex

## MLingualFC: Evaluating Jailbreak Vulnerabilities in Multilingual Vision-Language Models

`mlingualfc` | authors: Rishabh Makwana,  Mamta, Deeksha Varshney, Oana Cocarascu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Rishabhpm23/MLingualFC

No research facts available.

## MMBU: A Massive Multi-modal Biomedical Understanding Benchmark to Probe the Perception Capabilities of Vision-Language Models

`mmbu` | authors: Ryan D'Cunha, Alejandro Lozano, Xiaoxiao Sun, Daniel Vela Jarquin, Min Woo Sun, Josiah Aklilu, James Burgess, Yuhui Zhang, Ryan Nayebi, Paola Avila,  Robayo, Jin Ye, Ming Hu, Zhongying Deng, Junjun He, Xin Chen, Yue Yao, Robert Tibshirani, Jeffrey J. Nirschl, Serena Yeung-Levy | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The study evaluates 15 open-weight and 2 frontier Vision-Language Models (VLMs). (confidence: 1.00)
  Evidence: Evaluating 15 open-weight and 2 frontier VLMs, we find that while medical adaptation provides measurable gains for some models [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex

### Dataset

- MMBU covers 11 modalities across 35 submodalities, 20 specimens, 95 unique regions of interest, and spans 410 datasets. (confidence: 1.00)
  Evidence: covering \uniquemodalities\ modalities (across \uniquesubmodalities\ submodalities) from \uniquespecimens\ specimens and \uniquebodyparts\ unique regions of interest within those specimens, spanning \totaldatasets\ datasets. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex
- Each dataset in MMBU is converted into closed- and open-ended visual question answering (VQA) tasks and manually annotated by experts. (confidence: 1.00)
  Evidence: Each dataset is converted into closed- and open-ended visual question answering (VQA) tasks and manually annotated by a group of experts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex
- MMBU provides structured annotations for each datapoint including image provenance, domain, modality, submodality, stain, specimen, topic, context, and institution of acquisition. (confidence: 1.00)
  Evidence: provides rich, structured annotations for each datapoint, covering image provenance, dataset name, domain, modality, submodality, stain (when applicable), specimen, specimen subregion, topic, original task description, context, institution of acquisition, and URL. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex

### Benchmark

- The Massive Multimodal Biomedical Understanding (MMBU) benchmark is introduced as the largest biomedical vision and language benchmark to date. (confidence: 1.00)
  Evidence: To address these gaps, we introduce the Massive Multimodal Biomedical Understanding (MMBU) benchmark. It is the largest biomedical vision and language benchmark to date [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/summary.md
- MMBU includes both open and closed versions of ungrounded classification, grounded classification, and object detection tasks. (confidence: 1.00)
  Evidence: It includes both open and closed versions of ungrounded classification, grounded classification, and object detection, enabling systematic evaluation of model performance across biological scales, clinical settings, and imaging modalities. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex

### Claim

- Medical adaptation provides measurable gains for some models, but high accuracy on established benchmarks can mask deficiencies in visual perception and domain generalization. (confidence: 1.00)
  Evidence: we find that while medical adaptation provides measurable gains for some models, the high accuracy often reported on established benchmarks can mask deficiencies in visual perception and domain generalization. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex
- The evaluation reveals high error rates across all models and tasks, substantial weaknesses in spatially grounded tasks like object detection, and inconsistent generalization beyond commonly used benchmarks. (confidence: 1.00)
  Evidence: we find high error rates across all models and tasks, limited but measurable improvement from medical adaptation, substantial weaknesses in spatially grounded tasks such as object detection, and inconsistent generalization beyond commonly used biomedical benchmarks and MMBU. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex

### Limitation

- Current biomedical VLM evaluation relies on roughly 20 commonly used datasets, which is inadequate due to data pollution and a lack of diversity. (confidence: 1.00)
  Evidence: Current biomedical VLM evaluation relies on roughly 20 commonly used datasets. However, as the training data for large models expands, this evaluation becomes inadequate due to issues such as data pollution and a lack of diversity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex
- State-of-the-art biomedical VLMs are highly sensitive to prompt variation and batch effects, and often fail to consistently outperform general-domain counterparts after biomedical adaptation. (confidence: 1.00)
  Evidence: state-of-the-art biomedical VLMs remain highly sensitive to prompt variation and batch effects—systematic shifts arising from differences in scanners, acquisition protocols, or institutions—and often fail to consistently outperform their general-domain counterparts after biomedical adaptation [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mmbu/source.tex

## MODIP: Efficient Model-Based Optimization for Diffusion Policies

`modip` | authors: Zakariae El Asri, Philippe Gratias-Quiquandon, Nicolas Thome, Olivier Sigaud | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/elasriz/DPMPC

### Method

- MODIP is a framework designed for the offline-to-online fine-tuning of diffusion policies. (confidence: 1.00)
  Evidence: In this work, we propose MODIP, a framework for the offline-to-online fine-tuning of DPs. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- MODIP utilizes model predictive control (MPC) within a learned world model to generate high-quality trajectories, which are then used as supervised targets to fine-tune the diffusion policy. (confidence: 1.00)
  Evidence: We utilize model predictive control (MPC) to generate high-quality trajectories within the WM, and use them as supervised targets for fine-tuning the DP. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- To improve the computational efficiency of MPC planning, MODIP uses a terminal state value function rather than a policy-dependent state-action value function. (confidence: 1.00)
  Evidence: To make MPC planning efficient, MODIP uses a terminal state value instead of a policy-dependent state-action value, reducing inference time. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- MODIP decouples critic learning from the current policy by training critics with policy-independent temporal difference (TD) targets. (confidence: 1.00)
  Evidence: Additionally, MODIP trains critics with policy-independent TD targets, reducing training time. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- MODIP employs a DP-guided MPC planner that uses the diffusion policy as a multi-modal action sequence prior and refines the proposed trajectories through latent MPC. (confidence: 1.00)
  Evidence: We introduce a DP-guided MPC planner that uses a \diffpol as a multi-modal action sequence prior and refines its proposals through latent MPC. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/source.tex
- MODIP fine-tunes the diffusion policy using behavioral cloning on the improved trajectories generated by the DP-guided MPC planner. (confidence: 1.00)
  Evidence: We fine-tune the \diffpol by BC on trajectories improved by the DP-guided MPC planner. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/source.tex

### Benchmark

- The MODIP framework is evaluated on D4RL (including MuJoCo and Kitchen) and RoboMimic benchmark tasks. (confidence: 1.00)
  Evidence: Experiments on D4RL (MuJoCo, Kitchen) and RoboMimic tasks show that MODIP improves diffusion policies beyond BC [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md

### Claim

- MODIP improves the performance of diffusion policies beyond what is achievable with standard behavioral cloning. (confidence: 1.00)
  Evidence: Experiments on D4RL (MuJoCo, Kitchen) and RoboMimic tasks show that MODIP improves diffusion policies beyond BC [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md
- MODIP performs competitively with or better than existing diffusion policy RL fine-tuning methods and strong model-based baselines like TD-MPC2. (confidence: 1.00)
  Evidence: and is competitive with or outperforms diffusion policy RL fine-tuning methods and strong model-based baselines such as TD-MPC2. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md

### Limitation

- Direct reinforcement learning fine-tuning of diffusion policies is challenging and prone to instability because actions are generated via a multi-step denoising process. (confidence: 1.00)
  Evidence: However, while their success has largely been confined to BC, direct reinforcement learning (RL) fine-tuning remains challenging because actions are generated through a multi-step denoising process. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/modip/summary.md

## MPCoT: Reward-Guided Multi-Path Latent Reasoning for Test-Time Scalable Vision-Language-Action

`mpcot` | authors: Boyang Zhang, Lianlei Shan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/EDGSCOUT/MPCoT

No research facts available.

## Make Your VLA More Robust Without More Data By Interleaving Motion Planning

`2606_00985` | authors: Dan BW Choe, Sundhar Vinodh Sangeetha, Samuel Coogan, Shreyas Kousik | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors propose MPVI (Motion Planner / VLA Interleaving), a framework that integrates model-based motion planning with Vision-Language-Action (VLA) models to improve robustness without further training. (confidence: 1.00)
  Evidence: To address these challenges, we propose MPVI: Motion Planner / VLA Interleaving, a framework that integrates model-based motion planning with VLAs to improve robustness without further training. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/summary.md
- The MPVI framework utilizes VLM-based completion checking combined with proprioceptive triggers to enable reliable switching between navigation and manipulation modules. (confidence: 1.00)
  Evidence: we show one way forward via VLM-based completion checking with proprioceptive triggers. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex
- The authors use the pi_0.5 VLA as the manipulation policy in their method because the open-source code for the newer pi_0.7 model was not available. (confidence: 1.00)
  Evidence: Since open-source code for $\pi_{0.7}$ has not been published at the time of writing, we adopt the $\pi_{0.5}$ VLA \cite{pi0.5} as the manipulation policy in our method. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex

### Dataset

- The 2025 BEHAVIOR Challenge at NeurIPS released 1,200 hours of human teleoperated training data comprising 10,000 demonstrations for a 50-task subset of the BEHAVIOR-1K benchmark. (confidence: 1.00)
  Evidence: The 2025 BEHAVIOR Challenge at NeurIPS~\cite{behavior2025challenge} selects a 50-task subset for evaluation and releases 1,200 hours of human teleoperated training data across 10,000 demonstrations of these tasks. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex

### Benchmark

- The proposed MPVI approach is evaluated on the BEHAVIOR-1K benchmark, which involves long-horizon mobile manipulation tasks. (confidence: 1.00)
  Evidence: We evaluate our approach on the BEHAVIOR-1K benchmark [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex

### Claim

- The MPVI framework demonstrates a 113% improvement in task progress over a top end-to-end VLA baseline on the BEHAVIOR-1K benchmark. (confidence: 1.00)
  Evidence: demonstrate 113% improvement in task progress over a top end-to-end VLA baseline. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/summary.md
- Vision-Language-Action (VLA) models continue to perform poorly on long-horizon tasks even when finetuned on large amounts of human teleoperated mobile manipulation data. (confidence: 1.00)
  Evidence: These challenges persist despite finetuning on large human teleoperated mobile manipulation data, indicating that more data alone may not resolve the problem. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex
- The best competition solution in the 2025 BEHAVIOR Challenge achieved only a 12.4% average success rate across all tasks, highlighting the difficulty of the benchmark for VLAs. (confidence: 1.00)
  Evidence: VLAs achieve poor performance in the benchmark, with the best competition solution achieving only 12.4\% average success rate across all tasks. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex

### Limitation

- Relying exclusively on vision-language reasoning for subtask transitions causes cascading failures due to hallucinations by the Vision-Language Model (VLM). (confidence: 1.00)
  Evidence: We identify that relying solely on vision-language reasoning for task transitions leads to cascading failures driven by VLM hallucinations. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00985/source.tex

## MaskAlign: Token-Subset Representation Alignment for Efficient Diffusion Training

`maskalign` | authors: Lianyu Pang, Tianlin Pan, Cheng Da, Changqian Yu, Huan Yang, Kun Gai, Song Guo, Wenhan Luo | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- MaskAlign is a token-subset representation alignment method that applies alignment to randomly sampled token subsets during training. (confidence: 1.00)
  Evidence: we propose MaskAlign, a token-subset representation alignment method that applies alignment to randomly sampled token subsets during training. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/summary.md
- MaskAlign introduces a lightweight pre-mask token mixing block that shares information across tokens before masking to mitigate information loss caused by dropping tokens. (confidence: 1.00)
  Evidence: To mitigate the information loss caused by directly dropping tokens, we further introduce a lightweight pre-mask token mixing block that shares information across tokens before masking. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/summary.md
- MaskAlign uses a shared random mask to compute representation alignment on token subsets while preserving the class token. (confidence: 1.00)
  Evidence: MaskAlign first applies pre-mask token mixing and then uses a shared random mask to compute representation alignment on token subsets while preserving the class token. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex
- The paper evaluates MaskAlign using the SiT-XL/2 diffusion transformer architecture. (confidence: 1.00)
  Evidence: Generated samples from SiT-XL/2 + MaskAlign. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex

### Claim

- Under full-token representation alignment, tokens with large alignment-gradient norms exhibit a stable spatial preference, suggesting the alignment objective does not affect all tokens uniformly. (confidence: 1.00)
  Evidence: We find that, under full-token representation alignment, tokens with large alignment-gradient norms exhibit a stable spatial preference, suggesting that the alignment objective does not affect all tokens uniformly [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/summary.md
- MaskAlign reduces the dependence of representation alignment on the complete token set and encourages alignment behavior that is more stable under token-subset perturbations. (confidence: 1.00)
  Evidence: MaskAlign reduces the dependence of representation alignment on the complete token set and encourages alignment behavior that is more stable under token-subset perturbations. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/summary.md
- Using a 25% mask ratio in MaskAlign substantially reduces the concentrated spatial pattern of high-gradient tokens. (confidence: 1.00)
  Evidence: With a $25\%$ mask ratio, MaskAlign substantially reduces the concentrated spatial pattern. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex
- MaskAlign lowers the full-token alignment loss during training. (confidence: 1.00)
  Evidence: MaskAlign lowers the full-token alignment loss. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex
- MaskAlign narrows the alignment-loss gap between randomly masked and full-token inputs, indicating improved stability under token-subset perturbations. (confidence: 1.00)
  Evidence: MaskAlign narrows the alignment-loss gap
        $L^{\mathrm{mask}}_{\mathrm{REPA}}-L^{\mathrm{full}}_{\mathrm{REPA}}$,
        indicating improved stability under token-subset perturbations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/maskalign/source.tex

## MedQ-UNI: Toward Unified Medical Image Quality Assessment and Restoration via Vision-Language Modeling

`medq-uni` | authors: Jiyao Liu, Junzhi Ning, Wanying Qu, Lihao Liu, Chenglong Ma, Junjun He, Ningsheng Xu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- MedQ-UNI is a unified vision-language model that follows an assess-then-restore paradigm to leverage medical image quality assessment for guiding image restoration. (confidence: 1.00)
  Evidence: we propose MedQ-UNI, a unified vision-language model that follows an assess-then-restore paradigm, explicitly leveraging Med-IQA to guide Med-IR across arbitrary modalities and degradation types. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- The model utilizes a multimodal autoregressive dual-expert architecture with shared attention, comprising a quality assessment expert and a restoration expert. (confidence: 1.00)
  Evidence: MedQ-UNI adopts a multimodal autoregressive dual-expert architecture with shared attention: a quality assessment expert first identifies degradation issues through structured natural language descriptions, and a restoration expert then conditions on these descriptions to perform targeted image restoration. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- MedQ-UNI uses UniMedVL as its base model, freezing the text tokenizer and VAE encoder while fine-tuning the dual-expert modules and shared attention layers. (confidence: 1.00)
  Evidence: MedQ-UNI adopts UniMedVL~\cite{ning2025unimedvl} as our base model. We freeze the text tokenizer and VAE encoder during training and fine-tune the dual-expert modules and shared attention layers on our multi-task dataset. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- Degradations in the dataset are simulated using the TorchIO library, including noise and motion artifacts, with MRI k-space measurements undersampled using a 4x Gaussian 1D mask. (confidence: 1.00)
  Evidence: Degradations are simulated using the TorchIO library, including noise and motion artifacts. For MRI reconstruction, k-space measurements are  undersampled with $4\times$ Gaussian 1D mask. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex

### Dataset

- The authors constructed a training dataset of approximately 50,000 paired samples across three imaging modalities and five restoration tasks, annotated with structured quality descriptions. (confidence: 1.00)
  Evidence: we construct a large-scale dataset of approximately 50K paired samples spanning three imaging modalities and five restoration tasks, each annotated with structured quality descriptions for joint Med-IQA and Med-IR training [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex

### Benchmark

- A 2,000-sample benchmark was constructed to evaluate the model across three modalities and five restoration tasks. (confidence: 1.00)
  Evidence: along with a 2K-sample benchmark for evaluation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex

### Claim

- MedQ-UNI achieves state-of-the-art restoration performance across all evaluated tasks without requiring task-specific adaptation. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that a single MedQ-UNI model, without any task-specific adaptation, achieves state-of-the-art restoration performance across all tasks [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- MedQ-UNI outperforms strong closed-source vision-language models in generating medical image quality descriptions. (confidence: 1.00)
  Evidence: MedQ-UNI achieves the highest scores on all dimensions, outperforming even the strongest closed-source model. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- Ablation studies show that removing the explicit IQA text description causes substantial performance drops, proving its necessity for degradation-aware guidance. (confidence: 1.00)
  Evidence: Removing the IQA description produces substantial drops across all modalities, confirming that the explicit textual quality description provides essential degradation-aware guidance [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex
- A two-stage training strategy yields better restoration performance than end-to-end joint training from scratch by preventing early-stage optimization instability. (confidence: 1.00)
  Evidence: End-to-end joint training from scratch degrades restoration performance compared to our two-stage strategy, confirming that pre-training the restoration expert before introducing the IQA loss prevents early-stage optimization instability. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/medq-uni/source.tex

## Memory-Bound but Not Bandwidth-Limited: The Physical AI Inference Gap in Batch-1 LLM Decode

`2605_30571` | authors: Josef Chen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Dao-AILab/flash-attention, https://github.com/flashinfer-ai/flashinfer, https://github.com/vllm-project/vllm

### Method

- The study measures batch-1 decode performance for three 7 to 8B-class GQA transformers across four NVIDIA GPUs (H100 SXM5, A100-80GB SXM4, L40S, and L4) with context lengths from 2048 to 16384. (confidence: 1.00)
  Evidence: We measure batch-1 decode for three 7 to 8B-class GQA transformers across four NVIDIA GPUs: H100 SXM5, A100-80GB SXM4, L40S and L4. We evaluate context lengths from 2048 to 16384, producing 44 valid cells under a controlled bf16 SDPA setup. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- The researchers conducted a CUDA Graphs A/B experiment to test the impact of launch-side overhead on decode latency. (confidence: 1.00)
  Evidence: We test the missing term with a CUDA Graphs A/B experiment. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- The H100 SXM5 GPU evaluated in the study has a peak HBM bandwidth of 3350 GB/s. (confidence: 1.00)
  Evidence: 3350 GB/s peak HBM [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/source.tex

### Dataset

- The Qwen-2.5-7B model evaluated in the study uses a Grouped Query Attention architecture with 28 Q heads, 4 KV heads, a head dimension of 128, a hidden size of 3584, and an intermediate size of 18944. (confidence: 1.00)
  Evidence: GQA: 28 Q heads, 4 KV heads, head_dim 128, hidden 3584, intermediate 18944, bf16 [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/source.tex

### Claim

- Physical AI systems typically run a single-stream, batch-1 autoregressive decode workload, which differs from cloud LLM serving workloads. (confidence: 1.00)
  Evidence: Physical AI systems, including robots, autonomous vehicles, embodied agents and edge copilots, often run a different inference workload from cloud LLM serving: single-stream, batch-1 autoregressive decode, where one robot, camera feed or user session waits on the next token. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- The fraction of peak HBM bandwidth achieved during batch-1 decode decreases as the peak bandwidth of the GPU increases. (confidence: 1.00)
  Evidence: The achieved fraction of peak HBM bandwidth falls as peak bandwidth rises. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- For the Qwen-2.5-7B model at a context length of 2048, the L4 GPU reaches about 81% of its analytic memory floor, whereas the H100 GPU reaches only 27%. (confidence: 1.00)
  Evidence: On the headline Qwen-2.5-7B ctx=2048 cell, an L4 reaches roughly 81 percent of its analytic memory floor, while an H100 reaches only 27 percent. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- Using CUDA Graphs on an H100 GPU at a context length of 2048 improves decode latency by 1.259x, while on an L4 GPU it only improves latency by 1.028x. (confidence: 1.00)
  Evidence: On H100 at ctx=2048, CUDA Graphs improves decode latency by 1.259x across N=10 fresh sessions, with a 95 percent bootstrap confidence interval of 1.253 to 1.267. On L4, the same intervention gives only 1.028x. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- On the L4 GPU, common quantized paths like bnb-nf4 and AutoAWQ+Marlin do not achieve the expected 4x weight-traffic reduction compared to the bf16 baseline, whereas GPTQ+ExLlamaV2 with Ada-tuned int4 kernels significantly reduces step time. (confidence: 1.00)
  Evidence: On L4, bf16 decode sits close to the memory floor, but common quantised paths do not recover the expected 4x weight-traffic reduction: bnb-nf4 reaches 59.36 ms/step and AutoAWQ+Marlin reaches 45.24 ms/step from a 62.32 ms bf16 baseline. GPTQ+ExLlamaV2, with Ada-tuned int4 kernels, reaches 17.36 ms/step. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/summary.md
- The total step time for the decode process on the H100 SXM5 is 14.83 ms. (confidence: 1.00)
  Evidence: total step: 14.83 ms [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_30571/source.tex

## MemoryVLA++: Temporal Modeling via Memory and Imagination in Vision-Language-Action Models

`memoryvla` | authors: Hao Shi, Weiye Li, Bin Xie, Yulin Wang, Renping Zhou, Tiancai Wang, Xiangyu Zhang, Ping Luo, Gao Huang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/allenzren/open-pi-zero

No research facts available.

## MetaWorld: Scaling Multi-Agent Video World Model from Single-view Video Data

`metaworld` | authors: Teng Hu, Mingchun Lu, Yating Wang, Jiangning Zhang, Jinkun Hao, Ye Pan, Ran Yi, Lizhuang Ma, Dacheng Tao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- MetaWorld introduces Monocular World-State Unrolling (MWSU) to decompose monocular footage into the camera operator's ego-motion and the visible subject's spatial trajectory. (confidence: 1.00)
  Evidence: First, we introduce Monocular World-State Unrolling (MWSU) to explicitly decompose monocular footage into the camera operator's ego-motion and the visible subject's spatial trajectory. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- MetaWorld develops the Subject-Aware World Generator to enable appearance-driven simulation conditioned on per-agent identity images. (confidence: 1.00)
  Evidence: Second, for precise visual control, we develop the Subject-Aware World Generator to enable appearance-driven simulation conditioned on per-agent identity images. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- MetaWorld proposes World-State Alignment (WSA), a per-frame inter-branch cross-attention mechanism inserted at every transformer layer of the video DiT, to synchronize the denoising process and enforce static geometric and dynamic motion consistency. (confidence: 1.00)
  Evidence: Finally, to ensure both views are grounded in the identical physical reality, we propose World-State Alignment, a per-frame inter-branch cross-attention mechanism inserted at every transformer layer of the video DiT. By jointly synchronizing the denoising process, WSA enforces both static geometric consistency and dynamic motion consistency [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- The subject's spatial geometry is abstracted at each frame by calculating the mean position and covariance of its point cloud, representing the subject as a moving 3D Gaussian sphere. (confidence: 1.00)
  Evidence: Instead of modeling complex, non-rigid meshes, we abstract the subject's spatial geometry at each frame by calculating the mean position and covariance of its point cloud. This efficiently represents the subject as a compact, moving 3D Gaussian sphere. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- The shared 3D background scene is constructed using Anchor-Frame Background Modeling, which uses the initial frame for a partial prior, and Holistic Background Aggregation, which fuses multi-frame background point clouds. (confidence: 1.00)
  Evidence: we construct the shared 3D background scene $\mathcal{S}_i$ using two complementary strategies to supervise different generative capabilities. \textit{Anchor-Frame Background Modeling} utilizes only the initial frame to establish a partial environmental prior. ... \textit{Holistic Background Aggregation} replaces the single-frame reconstruction with multi-frame background fusion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- The MetaWorld framework uses the Phantom-Wan2.1 14B model as its backbone initialization for Stage 1 training. (confidence: 1.00)
  Evidence: Backbone init       & Phantom-Wan2.1 14B       & Stage-1 checkpoint [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex

### Dataset

- The dataset construction pipeline extracts continuous camera motion sequences using MoGe-2, estimates dense per-frame depth maps using Depth Anything, and tracks dynamic subjects using SAM 2. (confidence: 1.00)
  Evidence: For a given monocular video, we first extract the continuous camera motion sequence $\mathbf{c}_i$ using MoGe-2~\cite{wang2025moge}. Simultaneously, we estimate dense per-frame depth maps using Depth Anything~\cite{yang2024depth} and track dynamic subjects to obtain continuous instance masks via SAM~2~\cite{ravi2024sam}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex

### Benchmark

- Visual quality is assessed using the VBench evaluation suite, measuring Subject Consistency, Background Consistency, Motion Smoothness, Aesthetic Quality, and Imaging Quality. (confidence: 1.00)
  Evidence: We adopt the VBench~\cite{huang2024vbench} evaluation suite to assess generated video quality from multiple dimensions. Specifically, we report: \textbf{Subject Consistency} ... \textbf{Background Consistency} ... \textbf{Motion Smoothness} ... \textbf{Aesthetic Quality} ... and \textbf{Imaging Quality} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex
- The authors introduce Cross-View Consistency (CVC), a point-cloud-based metric that evaluates geometric and appearance consistency across views by reconstructing colored point clouds using monocular depth estimation and camera back-projection. (confidence: 1.00)
  Evidence: We therefore introduce \textbf{Cross-View Consistency (CVC)}, a point-cloud-based metric that evaluates both geometric and appearance consistency across views. Given a reference video $V_a$ and a generated video $V_b$, we reconstruct a colored point cloud from each video using monocular depth estimation~\cite{yang2024depth} and camera back-projection. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex

### Claim

- MetaWorld successfully scales video world models to open-domain environments, generating identity-consistent video observations from multiple simultaneous egocentric perspectives while enforcing static geometric and dynamic motion consistency. (confidence: 1.00)
  Evidence: Our framework successfully scales video world models to open-domain environments, generating identity-consistent video observations from multiple simultaneous egocentric perspectives. \method\ enforces both static geometric consistency and dynamic motion consistency, encouraging that the shared 3D physical environment evolves identically across all views. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/metaworld/source.tex

## MiVE: Multiscale Vision-language features for reference-guided video Editing

`mive` | authors: Tong Wang, Meng Zou, Chengjing Wu, Xiaochao Qu, Luoqi Liu, Xiaolin Hu, Ting Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- MiVE extracts hierarchical features from the Qwen3-VL model and integrates them into a unified self-attention Diffusion Transformer. (confidence: 1.00)
  Evidence: MiVE extracts hierarchical features from Qwen3-VL and integrates them into a unified self-attention Diffusion Transformer, eliminating the modality mismatch inherent in cross-attention designs. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- MiVE consists of three core components: a multiscale context extraction module, reference-aware latent encoding, and a unified self-attention backbone. (confidence: 1.00)
  Evidence: MiVE comprises three core components designed to leverage this hierarchical complementarity. First, a multiscale context extraction module harvests features from both early and final VLM layers, projecting them into the diffusion latent space. Second, reference-aware latent encoding concatenates reference frames with video latents to preserve structural cues. Third, a unified self-attention backbone processes all tokens—visual latents and multi-level VLM features—within a single attention manifold. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- The cross-modal diagnostic matrix is used to capture how text grounds onto video by computing the attention between text features and visual tokens. (confidence: 1.00)
  Evidence: The top-right block $\mathbf{E}\mathbf{B}^\top$ captures how text grounds onto video, which we denote as the Cross-Modal Diagnostic Matrix $\mathbf{A}_{\text{txt} \to \text{vis}}^{(l)} = \mathbf{E}\mathbf{B}^\top \in \mathbb{R}^{N \times M}$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- MiVE uses Qwen3-VL-8B as the unified encoder for processing the textual instruction, reference image, and source video. (confidence: 1.00)
  Evidence: we design a multi-level feature extraction strategy using Qwen3-VL-8B~\cite{bai2025qwen3vl} as the unified encoder for the textual instruction $\mathbf{x}_\text{text}$, reference image $\mathbf{x}_\text{ref}$, and source video $\mathbf{x}_\text{src}$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- The MiVE model is trained using the flow matching objective. (confidence: 1.00)
  Evidence: The model is trained using the flow matching objective~\cite{lipman2023flow}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- During training, the VLM encoder and VAE are kept frozen, and only the adapters and DiT blocks are optimized. (confidence: 1.00)
  Evidence: During training, the VLM encoder and VAE are frozen and only the adapters and DiT blocks are optimized; during inference, the target latent is initialized from pure noise. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex

### Dataset

- The cross-modal attention analysis was validated using 100 human-centric video sequences ranging from 2 to 8 seconds in length at 720P resolution. (confidence: 1.00)
  Evidence: We validate our diagnostic framework by evaluating Qwen3-VL-8B (36 layers) and GLM-4.6V-Flash-10B (40 layers) on 100 human-centric video sequences (2–8 seconds, 720P). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex

### Claim

- VLM layers encode complementary information hierarchically, with early layers capturing localized spatial details and deeper layers encoding global semantics. (confidence: 1.00)
  Evidence: We observe that VLM layers encode complementary information hierarchically -- early layers capture localized spatial details essential for precise editing, while deeper layers encode global semantics for instruction comprehension. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/summary.md
- MiVE achieves state-of-the-art performance, ranking highest in human preference and outperforming academic and commercial systems. (confidence: 1.00)
  Evidence: Experiments demonstrate that MiVE achieves state-of-the-art performance by ranking highest in human preference, outperforming both academic methods and commercial systems. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- Early layers of VLMs exhibit higher Attention Mask Ratios, confirming they capture spatial details, while deeper layers have lower ratios, indicating they encode holistic semantics. (confidence: 1.00)
  Evidence: As shown in Table~\ref{tab:attention_comparison}, $R_{\text{mask}}$ is higher in early layers and lower in deeper layers, confirming that early layers capture spatial details while final layers encode holistic semantics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex

### Limitation

- Existing decoupled encoder methods suffer from modality gaps because they process text instructions and visual content independently. (confidence: 1.00)
  Evidence: decoupled encoders suffer from modality gaps when processing instructions and visual content independently [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex
- Existing unified vision-language encoders lose fine-grained spatial details because they rely solely on final-layer representations. (confidence: 1.00)
  Evidence: unified vision-language encoders lose fine-grained spatial details by relying solely on final-layer representations. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mive/source.tex

## MiraBench: Evaluating Action-Conditioned Reliability in Robotic World Models

`mirabench` | authors: Tianzhuo Yang, Zihan Shen, Zirui Mi, Zhaoyi Zhang, Jiayi Zhou, Jiaming Ji, Juntao Dai, Jiawei Chen, Boyuan Chen, Yaodong Yang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- MiraBench evaluates reliability across three progressive levels: Physics Adherence, Action-Following Fidelity, and Optimism Bias Detection. (confidence: 1.00)
  Evidence: MiraBench decomposes this target into three progressively demanding levels: \emph{Physics Adherence}, which evaluates reference-free physical consistency; \emph{Action-Following Fidelity}, which measures whether predictions respect task-relevant action inputs; and \emph{Optimism Bias Detection}, which probes the tendency to predict successful outcomes under failure-inducing actions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md
- The study evaluates 12 different model configurations, including vector-conditioned and text-conditioned models, as well as open-weight and closed-source systems of various scales. (confidence: 1.00)
  Evidence: We evaluate 12 representative model configurations spanning vector-conditioned robotic world models, text-conditioned generative world models, open-weight systems, closed-source systems, and multiple model scales. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md

### Dataset

- The authors created a human-annotated corpus containing over 16,000 judgments to support the evaluation of world models. (confidence: 1.00)
  Evidence: To support this evaluation, we curate a human-annotated corpus with over 16,000 judgments across tasks, failure categories, and leading world models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md
- The study utilizes the NVIDIA Arena-GR1-Manipulation-Task dataset and the PsiBot SynData dataset for training and evaluation. (confidence: 1.00)
  Evidence: We leverage two large-scale robot manipulation datasets for training and evaluation: the \textbf{NVIDIA Arena-GR1-Manipulation-Task} dataset and the \textbf{PsiBot SynData} dataset. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/source.tex
- The NVIDIA Arena-GR1-Manipulation-Task dataset is an open-source benchmark released under the CC-BY-4.0 license, focusing on a microwave door opening task with the Fourier GR-1 humanoid robot. (confidence: 1.00)
  Evidence: The Arena-GR1-Manipulation-Task dataset~\cite{nvidia2025gr00tn1openfoundation} is an open-source robot manipulation benchmark released by NVIDIA under the CC-BY-4.0 license as part of the Isaac GR00T initiative. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/source.tex
- The PsiBot SynData dataset comprises real-world human demonstrations of bimanual manipulation tasks, captured using exoskeleton gloves and bare hands, with all sensor streams aligned to a 10 FPS timeline. (confidence: 1.00)
  Evidence: Despite its name, SynData consists entirely of \emph{real-world human demonstrations} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/source.tex

### Benchmark

- MiraBench is a hierarchical benchmark designed to evaluate action-conditioned reliability in robotic world models. (confidence: 1.00)
  Evidence: We introduce \textsc{MiraBench}, a hierarchical benchmark that defines \emph{action-conditioned reliability} as a core evaluation target for robotic world models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md

### Claim

- The evaluation found that visual fidelity is not a good indicator of action fidelity in robotic world models. (confidence: 1.00)
  Evidence: MiraBench reveals three central findings: visual fidelity is a poor proxy for action fidelity; [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md
- Increasing the scale of a model does not consistently lead to better action following in robotic world models. (confidence: 1.00)
  Evidence: increasing model scale does not reliably improve action following; [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md
- Current robotic world models exhibit pervasive optimism bias. (confidence: 1.00)
  Evidence: and optimism bias is pervasive across current systems. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mirabench/summary.md

## MotionEnhancer: Leveraging Video Diffusion for Motion-Enhanced Vision-Language Models

`motionenhancer` | authors: Yifan Xu, Chao Zhang, Ruifei Ma, Fei Gao, Zhifei Yang, Jiaxing Qi, Zhipeng Chen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- MotionEnhancer leverages motion priors distilled from a video diffusion model as auxiliary supervision to enhance a VLM's motion understanding via attention alignment. (confidence: 1.00)
  Evidence: In this paper, we introduce MotionEnhancer, a novel approach that leverages motion priors distilled from a powerful video diffusion model as auxiliary supervision to enhance the motion understanding capability of a VLM via attention alignment. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/summary.md
- MotionEnhancer includes two parameter-free modules: Motion-sensitive Head Selection (MHS) and Motion-salient Text Token Identification (MTTI). (confidence: 1.00)
  Evidence: MotionEnhancer comprises two simple parameter-free modules, Motion-sensitive Head Selection (MHS) and Motion-salient Text Token Identification (MTTI), to directly extract and optimize motion-related attentions from the VDM in a computation-only manner. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/summary.md
- The Motion-sensitive Head Selection (MHS) module selects motion-relevant heads by evaluating temporal attention maps based on diagonal concentration, spatial continuity, and high-value region ratios. (confidence: 1.00)
  Evidence: MHS draws on the findings of SparseVideoGen and evaluates temporal attention maps using diagonal concentration, spatial continuity, and high-value region ratios to select motion-relevant heads. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex
- The Motion-salient Text Token Identification (MTTI) module identifies text tokens responsive to smooth and abrupt motion by computing frame-wise averages and inter-frame differences. (confidence: 1.00)
  Evidence: MTTI computes frame-wise averages and inter-frame differences to identify text tokens responsive to both smooth and abrupt motion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex
- MotionEnhancer extracts attention maps from the Video Diffusion Model using DDIM inversion-sampling. (confidence: 1.00)
  Evidence: Using DDIM inversion-sampling, we extract attention maps from the VDM and apply two parameter-free modules, Motion-sensitive Head Selection (MHS) and Motion-salient Text Token Identification (MTTI), to identify motion-relevant heads and tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex
- The authors utilize Qwen2.5-VL, InternVL3, and CogVideoX-1.5-5B in their experiments, though the method is generalizable to other VLMs and DiT-based VDMs. (confidence: 1.00)
  Evidence: While we use Qwen2.5-VL, InternVL3, and CogVideoX-1.5-5B, our method is general and applicable to other VLMs and DiT-based VDMs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex

### Claim

- Current Vision-Language Models excel at event- or story-level understanding but struggle to capture fine-grained motion details due to a focus on high-level static semantic structures. (confidence: 1.00)
  Evidence: While current VLMs excel at event- or story-level understanding, their ability to capture fine-grained motion details remains limited, primarily due to their focus on high-level static semantic structures and macro-event logic. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex
- Video Diffusion Models are highly capable of modeling dynamic motion patterns because of their training on large-scale video data and the intrinsic requirements of temporal generation. (confidence: 1.00)
  Evidence: In contrast, Video Diffusion Models (VDMs) are adept at modeling dynamic motion patterns, benefiting from large-scale video data and the intrinsic requirement of temporal generation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/source.tex
- MotionEnhancer improves motion understanding without requiring additional training parameters, architectural modifications, or tool calling. (confidence: 1.00)
  Evidence: MotionEnhancer provides a scalable solution for motion understanding without additional training parameters, modifications to existing architectures, or tool calling. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/summary.md
- MotionEnhancer achieves consistent improvements over state-of-the-art VLMs on two motion-level video understanding benchmarks, particularly on motion-related metrics. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that MotionEnhancer can achieve consistent improvements over state-of-the-art VLMs on two motion-level video understanding benchmarks, especially on motion-related metrics. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/motionenhancer/summary.md

## Multi-Condition Guided Diffusion Model for Controllable Elastic Parameter Synthesis

`2606_05751` | authors: Hongling Chen, Qi Pang, Chuangji Meng, Shian Shen, Jinghuai Gao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors propose a multi-condition guided diffusion model for controllable elastic parameter synthesis to address the limitations of existing methods. (confidence: 1.00)
  Evidence: To address this issue, we propose a multi-condition guided diffusion model for controllable elastic parameter synthesis. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex
- The unified multi-condition guided diffusion framework incorporates implicit and explicit conditioning information using iterative latent variable refinement, Adapter-based conditioning, and a diffusion posterior sampling (DPS)-projection guidance strategy. (confidence: 1.00)
  Evidence: Specifically, iterative latent variable refinement, Adapter-based conditioning, and a diffusion posterior sampling (DPS)-projection guidance strategy are introduced for implicit model-domain constraints, implicit structural constraints, and explicit conditioning-operator constraints, respectively. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex
- A multi-elastic parameter dataset construction strategy is developed by combining a Bayesian Gaussian mixture model (BGMM), vertical shearing fields, and displacement vector fields. (confidence: 1.00)
  Evidence: We develop a multi-elastic parameter dataset construction strategy by combining a Bayesian Gaussian mixture model (BGMM), vertical shearing fields, and displacement vector fields. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex
- For explicit conditioning, a DPS-projection hybrid guidance strategy is developed by introducing an additional projection step into diffusion posterior sampling (DPS) to enhance the enforcement of conditions. (confidence: 1.00)
  Evidence: For explicit conditioning, we develop a DPS-projection hybrid guidance strategy by introducing an additional projection step into diffusion posterior sampling (DPS) \cite{chung2023diffusion}. This strategy enhances the enforcement of conditions with explicit conditioning operators and improves the consistency between the generated elastic parameters and the prescribed conditioning information. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex

### Dataset

- Elastic parameter training datasets are constructed based on well log statistics and the geological characteristics of the target area to train the diffusion model. (confidence: 1.00)
  Evidence: Elastic parameter training datasets are first constructed based on well log statistics and geological characteristics of the target area and are used to train the diffusion model. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex

### Claim

- The proposed method improves the prediction of representative elastic parameters, including P-wave velocity, S-wave velocity, and density, compared to baseline methods. (confidence: 1.00)
  Evidence: Experiments show that the proposed method improves the prediction of representative elastic parameters, including P-wave velocity, S-wave velocity, and density, compared with baseline methods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex
- Synthesized samples generated by the proposed method can support downstream deep-learning-based inversion under limited labeled data while achieving competitive performance. (confidence: 1.00)
  Evidence: The synthesized samples can also support downstream deep-learning-based inversion under limited labeled data, achieving competitive performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex

### Limitation

- Existing deep-learning-based methods for prestack elastic parameter inversion generally require sufficient labeled training data and lack flexibility in integrating multi-source conditioning information. (confidence: 1.00)
  Evidence: Most existing deep-learning-based methods have achieved promising results, but they generally require sufficient labeled training data and have limited flexibility in integrating multi-source conditioning information. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05751/source.tex

## Multimodal Structure Learning: Disentangling Shared and Specific Topology via Cross-Modal Graphical Lasso

`multimodal-structure-learning` | authors: Fei Wang, Yutong Zhang, Xiong Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## NVIDIA OmniDreams: Real-Time Generative World Model for Closed-Loop Autonomous Vehicle Simulation

`nvidia-omnidreams` | authors:  NVIDIA,  :, Aarti Basant, Amlan Kar, Despoina Paschalidou, Fangyin Wei, Francesco Ferroni, Guillermo Garcia Cobo, Haithem Turki, Huan Ling, Jaewoo Seo, James Lucas, Jay Zhangjie Wu, Jialiang Wang, Jonathan Lorraine, Jun Gao, Kai He, Katarina Tothova, Kevin Xie, Michał Tyszkiewicz, Qi Wu, Riccardo de Lutio, Ruilong Li, Sanja Fidler, Seung Wook Kim, Tianchang Shen, Tianshi Cao, Tobias Pfaff, William Lew, Xindi Wu, Xuanchi Ren, Yifan Lu, Yuxuan Zhang, Zan Gojcic, Zian Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/NVlabs/alpasim

### Method

- OmniDreams is a generative world model mid- and post-trained from the Cosmos diffusion model to autoregressively generate action-conditioned videos in real time. (confidence: 1.00)
  Evidence: we introduce OmniDreams, a foundation generative world model mid- and post-trained from the Cosmos diffusion model to autoregressively generate action-conditioned videos in real time. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/summary.md
- OmniDreams autoregressively conditions its sensor generation on past frames, the current simulator state, and immediate driving actions. (confidence: 1.00)
  Evidence: it autoregressively conditions its photorealistic sensor generation on past frames, the current simulator state, and immediate driving actions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/summary.md
- OmniDreams utilizes Diffusion Forcing, a training paradigm where each token receives an independent random noise level, allowing the model to act as both a next-token predictor and a full-sequence denoiser. (confidence: 1.00)
  Evidence: Diffusion Forcing: a training paradigm in which each token receives an independent random noise level, enabling a single model to act both as a next-token predictor and as a full-sequence denoiser [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex
- OmniDreams employs Self Forcing, which closes the autoregressive train-test gap by performing self-rollout during training and conditioning each frame on its own previously-generated outputs. (confidence: 1.00)
  Evidence: Self Forcing: a training paradigm that closes the autoregressive train-test gap by performing self-rollout during training, conditioning each frame on its own previously-generated outputs [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex
- The model uses a streaming KV cache, which is a bounded, in-place cache with static shapes that supports CUDA-graph capture and rolling-window eviction. (confidence: 1.00)
  Evidence: Streaming KV cache: a bounded, in-place KV cache with static shapes that supports CUDA-graph capture and rolling-window eviction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex
- OmniDreams-SV and OmniDreams-MV are post-trained from NVIDIA's Cosmos-Predict 2.5 video foundation model platform. (confidence: 1.00)
  Evidence: Cosmos / Cosmos-Predict 2.5: NVIDIA's video-foundation-model platform~\citep{nvidia2025worldsimulationvideofoundation}; \modelnamesv and \modelnamemv post-train from Cosmos-Predict\,2.5. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex

### Dataset

- OmniDreams is mid- and post-trained on 21,000 hours of driving scenarios. (confidence: 1.00)
  Evidence: mid- and post-training on 21k hours of driving scenarios [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/summary.md
- RDS is a multi-view autonomous vehicle training corpus used for mid-training, sourced from real-world driving logs at 1080p and 30 FPS across 15 countries. (confidence: 1.00)
  Evidence: RDS: the multi-view AV training corpus used for mid-training; sourced from real-world driving logs at $1080$p, $30$\,FPS across $15$ countries [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex
- RDS-HQ-1M is the post-training corpus featuring quality- and HD map-focused human verification. (confidence: 1.00)
  Evidence: RDS-HQ-1M: the post-training corpus, with quality- and HD map-focused human verification. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex

### Benchmark

- The paper evaluates 3D object detection using LET-AP, LET-APL, and LET-APH metrics. (confidence: 1.00)
  Evidence: LET-AP / LET-APL / LET-APH: Longitudinal-Error-Tolerant Average Precision and its localization- (APL) and heading-weighted (APH) variants; 3D object-detection metrics reported in \cref{sec::results} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex
- Fréchet Video Distance (FVD) is used as a distribution-level video-quality metric in the results. (confidence: 1.00)
  Evidence: FVD: Fr\'echet Video Distance; a distribution-level video-quality metric referenced in \cref{sec::results}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/source.tex

### Claim

- A world-action model (WAM) post-trained from OmniDreams surpasses the VLA-based Alpamayo 1.5 research policy model on the NuRec dataset while using only 1/5 the total parameters. (confidence: 1.00)
  Evidence: a world-action model (WAM) post-trained from OmniDreams achieves strong performance on the Physical AI Autonomous Vehicles NuRec dataset, surpassing the VLA-based Alpamayo 1.5 research policy model while using only 1/5 the total parameters. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nvidia-omnidreams/summary.md

## Native3D: End-to-End 3D Scene Generation via Unified Mesh-Texture Modeling and Semantic Alignment

`native3d` | authors: Yibo Liu, Ziwei Zhang, Haozhou Pang, Menghao Li, Lanshan He, Gan Qi | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- Native3D is an end-to-end 3D scene generation framework that bypasses 2D intermediate representations by utilizing a unified mesh-texture joint representation and a Transformer-based scene encoder. (confidence: 1.00)
  Evidence: This paper presents Native3D, the first end-to-end 3D scene generation framework that completely bypasses 2D intermediate representations. Traditional approaches typically require adapting 3D representations to the 2D domain to leverage pre-trained diffusion models, which inevitably introduces domain adaptation issues including geometric structural distortion and texture detail degradation. To address these limitations, we design a unified mesh-texture joint representation that simultaneously models both geometric structures and texture features through a Transformer-based scene encoder [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex
- The framework introduces the 3D Representation Alignment Loss (3D REPA Loss), which uses an improved contrastive learning mechanism to align multi-level semantic representations in the latent space. (confidence: 1.00)
  Evidence: We further propose the 3D Representation Alignment Loss (3D REPA Loss), which employs an improved contrastive learning mechanism to align multi-level semantic representations in the latent space, significantly enhancing geometric and textural fidelity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex
- Native3D adopts the Diffusion Transformer (DiT) as its core architecture to learn the diffusion process directly in a high-level 3D feature space, eliminating information loss from 2D-3D cross-domain conversion. (confidence: 1.00)
  Evidence: For the generation module design, we adopt Diffusion Transformer (DiT) as the core architecture, which directly learns the diffusion process in high-level 3D feature space, completely eliminating information loss caused by 2D-3D cross-domain conversion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex
- The 3D REPA Loss aligns multi-scale feature representations in the semantic feature space to guide the model in restoring geometric details and texture quality while maintaining global consistency. (confidence: 1.00)
  Evidence: By aligning these multi-scale representations in semantic feature space, the 3D REPA Loss guides the model to accurately restore geometric details and texture quality of individual target objects while maintaining global consistency. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex

### Claim

- Experimental results indicate that Native3D surpasses existing methods in both generation quality and editing flexibility for 3D scenes. (confidence: 1.00)
  Evidence: Experimental results demonstrate that Native3D outperforms existing methods in both generation quality and editing flexibility, providing a novel solution for 3D scene editing. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex

### Limitation

- Traditional approaches that adapt 3D representations to the 2D domain suffer from domain adaptation issues, such as geometric structural distortion and texture detail degradation. (confidence: 1.00)
  Evidence: Traditional approaches typically require adapting 3D representations to the 2D domain to leverage pre-trained diffusion models, which inevitably introduces domain adaptation issues including geometric structural distortion and texture detail degradation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex
- Pure 2D scene editing methods lack explicit 3D geometric constraints, which causes cross-view inconsistencies, blurring artifacts, and visible seams when viewpoint variations are large. (confidence: 1.00)
  Evidence: The core limitation of these methods lies in the absence of explicit 3D geometric constraints. 2D representations fundamentally lack the capacity to reason about 3D structures and depth relationships, resulting in cross-view inconsistencies, blurring artifacts, and visible seams under large viewpoint variations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex
- Hybrid 2D-processing-3D-reconstruction strategies struggle with consistency propagation because 2D diffusion models lack multi-view geometric constraints, leading to fine-grained misalignment and slow convergence when lifted to 3D. (confidence: 1.00)
  Evidence: These approaches face critical challenges in consistency propagation between 2D editing and 3D reconstruction. Lacking multi-view geometric constraints, 2D diffusion models produce cross-view inconsistencies when lifted to 3D, resulting in fine-grained misalignment and slow convergence. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/native3d/source.tex

## NextMotionQA: Benchmarking and Judging Human Motion Understanding with Vision-Language Models

`nextmotionqa` | authors: Yong Cao, Chuqiao Li, Xianghui Xie, Gerard Pons-Moll, Andreas Geiger | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The pilot study sampled 150 items uniformly from the BABEL-QA test split of HumanMotionQA, rendering the raw motion coordinates into standardized video clips at 30 FPS and 768x768 resolution. (confidence: 1.00)
  Evidence: The 150 sampled items were drawn uniformly from the BABEL-QA test split of HumanMotionQA without stratification to preserve the natural distribution of the source dataset. ... The underlying raw motion coordinates were rendered using Blender into standardized video clips at 30 FPS with a resolution of 768 × 768 pixels. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- The dataset construction retains AMASS sub-clips with durations between 0.81 and 119.92 seconds after concatenating consecutive BABEL segments sharing an action label. (confidence: 1.00)
  Evidence: We retain AMASS sub-clips of duration L∈[0.81, 119.92] seconds, after concatenating consecutive BABEL segments that share an action label. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- Task difficulty is assigned based on the cardinality of BABEL frame-level action labels and the modifier content of the HumanML3D caption. (confidence: 1.00)
  Evidence: We assign difficulty based on the cardinality of BABEL frame-level action labels and the modifier content of the HumanML3D caption. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- The VLM-as-A-Judge evaluation tests nine representative text-to-motion methods spanning diffusion, discrete-token, continuous-latent, and part-based families. (confidence: 1.00)
  Evidence: We evaluate VLM-as-A-Judge on nine representative T2M methods spanning four lines of work. From the diffusion family, we include MDM... From the discrete-token family, we include MoMask... From the continuous-latent family, we include MotionStreamer... From the part-based family, we include FineMoGen... [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- The study evaluates 12 VLMs, running proprietary models via official APIs and open-source models from public weights on a single NVIDIA H100 node. (confidence: 1.00)
  Evidence: Proprietary VLMs were queried through their official APIs; open-source VLMs were run from public weights on a single NVIDIA H100 (80 GB) node. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex

### Benchmark

- NextMotionQA is a comprehensive benchmark for human motion understanding featuring three tasks: multiple-choice question answering, video captioning, and fine-grained error correction. (confidence: 1.00)
  Evidence: NextMotionQA features three complementary tasks: multiple-choice question answering, video captioning, and fine-grained error correction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- The tasks in NextMotionQA are structured across three core semantic axes and stratified into three complexity levels. (confidence: 1.00)
  Evidence: Each task is systematically structured across three core semantic axes and stratified into three task complexity levels. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex

### Claim

- VLMs align strongly with expert ratings on coarse criteria but break down on fine-grained, part-level judgment when acting as judges for text-to-motion evaluation. (confidence: 1.00)
  Evidence: We find that VLMs align strongly with expert ratings on coarse criteria (Cohen's κ=0.70) but break down on fine-grained, part-level judgment (κ=0.10), validating the paradigm in its strong regime while clarifying its limits. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- Domain experts exhibit a "confidently wrong" phenomenon on ambiguous labels, showing a weak correlation between their confidence and actual correctness. (confidence: 1.00)
  Evidence: Our findings indicate a strong presence of the {``confidently wrong''} phenomenon. Experts reported a high confidence score (≥ 4/5) on 69.2% of all items. However, their empirical accuracy on these high-confidence responses was only 65.5%. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- On the fine-grained error correction task, VLMs locate motion-caption errors far better than they fix them, with an average locate-to-fix gap of 26 points. (confidence: 1.00)
  Evidence: On T3, models locate motion-caption errors far better than they fix them. ... The locate→fix gap averages 26 points and never closes: even the best locator, Gemini-3.1-Flash, recovers 76.8% of error spans but corrects only 44.9% of them. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex

### Limitation

- Existing benchmarks suffer from body-part granularity collisions, where vocabulary conflates hierarchical body parts like hand vs. arm. (confidence: 1.00)
  Evidence: The underlying BABEL vocabulary often conflates hierarchical body parts (e.g., hand vs. arm; foot vs. leg). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex
- Directional queries in existing datasets often fail to specify the spatial frame of reference, leaving it ambiguous whether directions are egocentric, allocentric, or viewer-relative. (confidence: 1.00)
  Evidence: Directional queries (e.g., ``move right'') systematically fail to specify the frame of reference. It remains undefined whether the direction refers to the viewer’s right, the actor’s egocentric right, or a fixed allocentric world coordinate. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/nextmotionqa/source.tex

## OSCAR: Omni-Embodiment Action-Conditioned World Model for Robotics

`oscar` | authors: Zhuoyuan Wu, Jun Gao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Occupancy Reward Shaping: Improving Credit Assignment for Offline Goal-Conditioned Reinforcement Learning

`occupancy-reward-shaping` | authors: Aravind Venugopal, Jiayu Chen, Xudong Wu, Chongyi Zheng, Benjamin Eysenbach, Jeff Schneider | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/aravindvenu7/occupancy, https://github.com/aravindvenu7/occupancy_reward_shaping, https://github.com/aravindvenu7.github.io/website, https://github.com/facebookresearch/go-fresh, https://github.com/goodfeli/dlbook_notation, https://github.com/seohongpark/ogbench

### Method

- The paper introduces Occupancy Reward Shaping (ORS), which uses optimal transport to extract temporal geometry from a learned occupancy measure model into a reward function for credit assignment. (confidence: 1.00)
  Evidence: Leveraging optimal transport, we extract this geometry from a learned model of the occupancy measure into a reward function that captures goal-reaching information. Our resulting method, Occupancy Reward Shaping, largely mitigates the problem of credit assignment in sparse reward settings. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/summary.md
- The reward function in ORS is derived using the squared Wasserstein-2 distance between a Dirac delta at the goal state and the transition probability distribution. (confidence: 1.00)
  Evidence: By replacing the general measure $\nu$ with the specific transition probability $d^{\pi_{\mathcal{D}}}(s^+\mid s, a)$ and renaming the integration variable, we obtain the final form:
$$
W_2^2(\delta_g, d^{\pi_{\mathcal{D}}}(s^+\mid s, a)) = \int \|s^+-g\|^2 d^{\pi_{\mathcal{D}}}(ds^+\mid s, a)
= M^{\pi_D}(s, a, g) $$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/source.tex

### Benchmark

- The method is evaluated on 13 long-horizon locomotion and manipulation tasks, as well as 3 real-world Tokamak control tasks for nuclear fusion. (confidence: 1.00)
  Evidence: empirically improves performance by 2.2x across 13 diverse long-horizon locomotion and manipulation tasks. Moreover, we demonstrate the effectiveness of ORS in the real world for controlling nuclear fusion on 3 Tokamak control tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/summary.md

### Claim

- Occupancy Reward Shaping provably does not alter the optimal policy of the environment. (confidence: 1.00)
  Evidence: ORS provably does not alter the optimal policy, yet empirically improves performance by 2.2x across 13 diverse long-horizon locomotion and manipulation tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/summary.md
- ORS empirically improves performance by 2.2 times across 13 diverse long-horizon locomotion and manipulation tasks. (confidence: 1.00)
  Evidence: ORS provably does not alter the optimal policy, yet empirically improves performance by 2.2x across 13 diverse long-horizon locomotion and manipulation tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/summary.md
- Proposition 1 proves that the average squared Wasserstein-2 distance is monotonically increasing with respect to the shortest-path layer index and is minimized by the optimal action. (confidence: 1.00)
  Evidence: the average squared Wasserstein-2 distance ... is monotonically increasing with respect to the shortest-path layer index $k$. ... Moreover, for any state–goal pair $(s,g)$, the squared \textit{Wasserstein-2 distance} is minimized by the optimal action [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/source.tex

### Limitation

- The theoretical proofs in the paper rely on the assumption that the environment dynamics are deterministic. (confidence: 1.00)
  Evidence: We assume that the environment dynamics are deterministic:
For any state $s \in \mathcal{S}$ and action $a \in \mathcal{A}$, 
the state transition probability $p(s'\mid s, a)$ is a point mass distribution, concentrated on the unique successor state $f(s, a)$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/source.tex
- The theoretical analysis assumes one-step reachability of the goal and that the offline policy maintains relative layer ordering consistent with the shortest-path layer structure. (confidence: 0.90)
  Evidence: Assumption [One-step reachability] ... Assumption [Layer monotonicity of $\pi_{\mathcal{D}}$]
We assume the offline policy $\pi_{\mathcal{D}}$ is consistent with the shortest-path layer structure. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/occupancy-reward-shaping/source.tex

## Omni123: Exploring 3D Native Foundation Models with Limited 3D Data by Unifying Text to 2D and 3D Generation

`omni123` | authors: Chongjie Ye, Cheng Cao, Chuanyu Pan, Yiming Hao, Yihao Zhi, Yuanming Hu, Xiaoguang Han | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- Omni123 is a 3D-native foundation model that unifies text-to-2D and text-to-3D generation within a single autoregressive framework. (confidence: 1.00)
  Evidence: We present Omni123, a 3D-native foundation model that unifies text-to-2D and text-to-3D generation within a single autoregressive framework. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- The model represents text, images, and 3D geometry as discrete tokens in a shared sequence space to leverage 2D data as a geometric prior. (confidence: 1.00)
  Evidence: By representing text, images, and 3D as discrete tokens in a shared sequence space, the model leverages abundant 2D data as a geometric prior to improve 3D representations. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- The authors introduce an interleaved X-to-X training paradigm to coordinate cross-modal tasks over heterogeneous paired datasets without needing fully aligned text-image-3D triplets. (confidence: 1.00)
  Evidence: We introduce an interleaved X-to-X training paradigm that coordinates diverse cross-modal tasks over heterogeneous paired datasets without requiring fully aligned text-image-3D triplets. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- The model traverses semantic-visual-geometric cycles, such as text to image to 3D to image, within autoregressive sequences to enforce semantic alignment, appearance fidelity, and geometric consistency. (confidence: 1.00)
  Evidence: By traversing semantic-visual-geometric cycles (e.g., text to image to 3D to image) within autoregressive sequences, the model jointly enforces semantic alignment, appearance fidelity, and multi-view geometric consistency. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- The training process consists of three stages: cross-modal pre-training over heterogeneous pairs, continued training with learnable view tokens, and Text-Image-3D interleaved fine-tuning. (confidence: 1.00)
  Evidence: Our three-stage training recipe---cross-modal pre-training over heterogeneous pairs, continued training with learnable view tokens for viewpoint awareness, and Text--Image--3D interleaved fine-tuning that closes the ``semantic--visual--geometric'' loop---enables abundant 2D observations to serve as an implicit structural constraint for 3D learning. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/source.tex

### Claim

- Cross-modal generative consistency between images and 3D can act as an implicit structural constraint to improve 3D representations. (confidence: 1.00)
  Evidence: Our key insight is that cross-modal consistency between images and 3D can serve as an implicit structural constraint. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md
- Omni123 significantly improves text-guided 3D generation and editing, providing a scalable path toward multimodal 3D world models. (confidence: 1.00)
  Evidence: Experiments show that Omni123 significantly improves text-guided 3D generation and editing, demonstrating a scalable path toward multimodal 3D world models. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md

### Limitation

- Extending native generative capabilities to 3D is challenging because high-quality 3D assets are scarce compared to 2D imagery, leaving 3D synthesis under-constrained. (confidence: 1.00)
  Evidence: Compared to abundant 2D imagery, high-quality 3D assets are scarce, making 3D synthesis under-constrained. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omni123/summary.md

## OmniVL-Guard: Towards Unified Vision-Language Forgery Detection and Grounding via Balanced RL

`omnivl-guard` | authors: Jinjie Shen, Jing Wu, Yaxiong Wang, Lechao Cheng, Shengeng Tang, Tianrui Hui, Nan Pu, Zhun Zhong | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/shen8424/OmniVL-Guard

### Method

- OmniVL-Guard is a balanced reinforcement learning framework designed for omnibus vision-language forgery detection and grounding. (confidence: 1.00)
  Evidence: To address this challenge, we propose \textbf{OmniVL-Guard}, a balanced reinforcement learning framework for omnibus vision-language forgery detection and grounding. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- Self-Evolving CoT Generation is a component of OmniVL-Guard that synthesizes high-quality reasoning paths to overcome the cold-start challenge. (confidence: 1.00)
  Evidence: {Self-Evolving CoT Generation} synthesizes high-quality reasoning paths, effectively overcoming the cold-start challenge. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- Adaptive Reward Scaling Policy Optimization (ARSPO) dynamically modulates reward scales and task weights to ensure balanced joint optimization in multi-task scenarios. (confidence: 1.00)
  Evidence: {Adaptive Reward Scaling Policy Optimization (ARSPO)} dynamically modulates reward scales and task weights, ensuring a balanced joint optimization. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex

### Dataset

- The dataset and code for the OmniVL-Guard framework are publicly available on GitHub. (confidence: 1.00)
  Evidence: The dataset and code are publicly available at \url{https://github.com/shen8424/OmniVL-Guard}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex

### Claim

- In unified vision-language forgery detection, a 'difficulty bias' occurs where the simpler veracity classification task dominates gradients, leading to suboptimal performance in fine-grained grounding during multi-task optimization. (confidence: 1.00)
  Evidence: the {interplay} between diverse modalities and the dual requirements of simultaneous detection and localization pose a critical ``difficulty bias`` problem: the simpler veracity classification task tends to dominate the gradients, leading to suboptimal performance in fine-grained grounding during multi-task optimization. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- OmniVL-Guard significantly outperforms state-of-the-art methods and demonstrates robust zero-shot generalization across out-of-domain scenarios. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that OmniVL-Guard significantly outperforms state-of-the-art methods and exhibits zero-shot robust generalization across out-of-domain scenarios. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex

### Limitation

- Existing forgery detection methods are typically restricted to uni-modal or bi-modal settings and fail to handle the interleaved text, images, and videos found in real-world misinformation. (confidence: 1.00)
  Evidence: Existing forgery detection methods are often limited to uni-modal or bi-modal settings, failing to handle the interleaved text, images, and videos prevalent in real-world misinformation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- State-of-the-art Multi-modal Large Language Models (MLLMs) exhibit significant performance bottlenecks in image, text, and video localization tasks, making them inefficient for generating Chain-of-Thought data due to frequent hallucinations and errors. (confidence: 1.00)
  Evidence: Notably, these models exhibit significant performance bottlenecks in the three localization tasks. Consequently, directly utilizing them to generate CoT data is inefficient due to frequent hallucinations and errors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- Standard Supervised Fine-Tuning (SFT) struggles to deliver consistent performance improvements across all sub-tasks in multi-modal and multi-task forgery detection scenarios. (confidence: 1.00)
  Evidence: Our preliminary experiments reveal that standard Supervised Fine-Tuning (SFT) struggles to deliver consistent improvements across all sub-tasks, as shown in the first row of Table 1(b). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex
- Reinforcement learning approaches like GRPO, despite having strong optimization capabilities, often have their training dynamics dominated by easier classification objectives, leading to insufficient optimization of more challenging grounding tasks. (confidence: 1.00)
  Evidence: While reinforcement learning (RL)–based approaches, such as GRPO, demonstrate stronger optimization capability, the training dynamics are often dominated by the easier classification objective. This imbalance results in insufficient optimization of the more challenging grounding task. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/omnivl-guard/source.tex

## On the Limits of Token Reduction for Efficient Unified Vision Language Training

`2606_01503` | authors: Siyi Chen, Weiming Zhuang, Jingtao Li, Lingjuan Lv | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- The authors design task-specific accelerators that selectively reduce image-token computation for visual understanding and visual generation objectives. (confidence: 1.00)
  Evidence: Guided by this observation, we design task-specific accelerators that selectively reduce image-token computation for each objective. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- The study uses the VILA-U (7B) model paradigm as the testbed for the unified autoregressive vision-language model. (confidence: 1.00)
  Evidence: We study a unified vision-language model (VLM) that jointly performs visual understanding and visual generation within a single autoregressive Transformer backbone, following the unified next-token prediction paradigm of VILA-U (7B)~\cite{wu2024vila}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Dataset

- The ShareGPT-4v dataset is used to collect attention statistics for visual understanding tasks. (confidence: 1.00)
  Evidence: We analyze the VILA-U model and collect attention statistics on both visual understanding (with ShareGPT-4v dataset) and visual generation (with JournyDB dataset). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- The JournyDB dataset is used to collect attention statistics for visual generation tasks. (confidence: 1.00)
  Evidence: We analyze the VILA-U model and collect attention statistics on both visual understanding (with ShareGPT-4v dataset) and visual generation (with JournyDB dataset). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Claim

- Joint training of unified vision-language models that integrate visual understanding and generation is computationally expensive and often overlooked from an efficiency perspective. (confidence: 1.00)
  Evidence: Unified vision-language models (VLMs) integrate visual understanding and visual generation within a single autoregressive backbone, but their joint training is computationally expensive and largely overlooked from an efficiency perspective. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- There is a fundamental asymmetry in token utilization between visual understanding and generation tasks, where understanding exhibits late-layer visual redundancy and generation maintains persistent dependence on image tokens. (confidence: 1.00)
  Evidence: Through a systematic analysis of layerwise attention allocation, we uncover a fundamental asymmetry: visual understanding exhibits substantial late-layer visual redundancy, whereas visual generation maintains persistent dependence on image tokens across depth. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- In unified VLM training, the quadratic self-attention cost of image tokens is the primary computational bottleneck because image tokens typically dominate the sequence length. (confidence: 1.00)
  Evidence: In unified VLM training, image tokens typically dominate the sequence ($M \gg T$), making the $M^2$ term the primary computational bottleneck. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex
- In visual understanding tasks, attention to image tokens drops from roughly 30% in the first layer to below 10% in middle and late layers. (confidence: 1.00)
  Evidence: Image tokens account for roughly $\sim$30\% of attention in the first layer, but this drops below 10\% in middle and late layers. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/source.tex

### Limitation

- Applying task-specific token reduction methods to joint training causes a synergy loss, as it necessitates divergent parameter pathways and eliminates mutual performance gains typically seen in joint optimization. (confidence: 1.00)
  Evidence: While these methods achieve significant efficiency gains in isolated settings, we observe a consistent synergy loss under unified training -- task-specific token dropping necessitates divergent parameter pathways and eliminates the mutual performance gains typically observed in joint optimization. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01503/summary.md

## OpenEAI-Platform: An Open-source Embodied Artificial Intelligence Hardware-Software Unified Platform

`openeai-platform` | authors: Jinyuan Zhang, Luoyi Fan, Leiyu Wang, Yeqiang Wang, Yicheng Zhu, Cewu Lu, Nanyang Ye | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/eai-yeslab/OpenEAI-Arm, https://github.com/eai-yeslab/OpenEAI-VLA, https://github.com/sii-research/ORoboSoul

### Method

- OpenEAI-Platform integrates a low-cost 6+1 degree-of-freedom robotic arm (OpenEAI-Arm) and a reproducible vision-language-action model (OpenEAI-VLA). (confidence: 1.00)
  Evidence: We present OpenEAI-Platform, a fully open-source platform that integrates a low-cost 6+1 degree-of-freedom (dof) robotic arm (OpenEAI-Arm) and a reproducible VLA model (OpenEAI-VLA). [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/summary.md
- OpenEAI-Arm uses DAMIAO DM4340 motors for the first three joints and DAMIAO DM4310 motors for the remaining joints and the gripper, with an aluminum alloy main body and 3D-printed gripper components. (confidence: 1.00)
  Evidence: We adopt off-the-shelf DAMIAO DM4340 motors for the first three joints and DM4310 motors for the remaining joints and the gripper, and build the main body with aluminum alloy while using 3D-printed components with prefabricated slide rails and ball-head pull rods for the gripper. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex
- OpenEAI-VLA uses Qwen3-VL-4B as the backbone vision-language model and employs a diffusion-transformer-based action head for continuous action generation. (confidence: 1.00)
  Evidence: We develop \svla on top of Qwen3-VL-4B \cite{Qwen3-VL}. Following $\pi_0$, \svla uses a flow-matching objective for continuous action generation, but employs a diffusion-transformer-based action head for denoising-based decoding like Diffusion Transformer Policy \cite{hou2025diffusiontransformerpolicy}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex
- OpenEAI-VLA appends a learnable fixed-length query embedding to the vision and language embeddings to compress task-relevant information before conditioning the action head. (confidence: 1.00)
  Evidence: In addition, we append a learnable fixed-length query embedding to the vision and language embeddings to extract and compress task-relevant information from the VLM before conditioning the action head. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex

### Dataset

- OpenEAI-VLA is trained in two stages using only open-source robot and multimodal datasets. (confidence: 1.00)
  Evidence: OpenEAI-VLA builds on Qwen3-VL-4B and uses a Diffusion Transformer action head, and is trained in two stages with only open-source robot and multimodal datasets. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/summary.md

### Claim

- OpenEAI-Arm outperforms two commercial 6+1-dof robotic arms across four real-world manipulation tasks when evaluated under the same policy. (confidence: 1.00)
  Evidence: Across four real-world manipulation tasks, OpenEAI-Arm outperforms two commercial 6+1-dof arms under the same policy [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/summary.md
- OpenEAI-VLA achieves success rates comparable to the large-scale pretrained pi0 baseline despite using only limited open-source pretraining data. (confidence: 1.00)
  Evidence: and OpenEAI-VLA achieves success rates comparable to the large-scale pretrained pi0 baseline with only limited pretraining data. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/summary.md

### Limitation

- State-of-the-art Vision-Language-Action models like pi0 and pi0.5 rely on large-scale proprietary datasets, which creates a significant barrier for reproducibility and data scaling. (confidence: 1.00)
  Evidence: the Physical Intelligence series ($\pi_0$ \cite{pi0}, $\pi_{0.5}$ \cite{pi0_5}) represents state-of-the-art performance but relies on large-scale proprietary datasets, creating a major reproducibility and data-scaling barrier. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex
- The high cost and black-box nature of commercial robotic arms restrict large-scale data collection and make it difficult to study the coupling between VLA algorithms and low-level control methods. (confidence: 1.00)
  Evidence: Moreover, the high cost of commercial robotic arms restrict large-scale data collection and make it difficult to study the interaction between VLA algorithms and low-level control. Besides, the black-box nature of these robotic arms makes it challenging to investigate the complex coupling between VLA algorithms and low-level control methods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/openeai-platform/source.tex

## PAMF: Prior-Aware Multimodal Fusion for Incomplete Time Series Data

`pamf` | authors: Ziwen Kan, Wugeng Zheng, Tianlong Chen, Song Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PAMF is a multimodal time-series framework that explicitly handles different missingness patterns while coupling imputation with downstream prediction through prior-aware flow matching and weight sharing. (confidence: 1.00)
  Evidence: To address these limitations, we present PAMF, a multimodal time-series framework that explicitly handles different missingness patterns while coupling imputation with downstream prediction through prior-aware flow matching and weight sharing. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- The method initializes the flow-matching source state with type-specific priors to distinguish between within-modality missing and modality-level missing types. (confidence: 1.00)
  Evidence: Specifically, the method initializes the flow-matching source state with type-specific priors to distinguish two missing types. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- PAMF connects imputation and classification through architecturally matched encoders with weight sharing, which transfers task-relevant representations into the imputation process. (confidence: 1.00)
  Evidence: It further connects imputation and classification through architecturally matched encoders with weight sharing, transferring task-relevant representations into the imputation process. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- For within-modality missing data, the flow-matching initialization is constructed from temporal neighbor and mean values to keep the starting point within a plausible local observation range. (confidence: 1.00)
  Evidence: For \wmissing{}, the initialization is constructed from temporal neighbor and mean values to keep the starting point within a plausible local observation range, following the intuition of classical carry-forward imputation~\cite{molenberghs2007missing}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- For modality-level missing data, the initialization is derived from other observed data to provide a starting point that better matches the underlying distribution. (confidence: 1.00)
  Evidence: For \mmissing{}, the initialization is derived from other observed data to provide a starting point that better matches the underlying distribution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex

### Dataset

- The proposed method is evaluated on four datasets under multiple missingness settings, including within-modality missing, modality-level missing, and additional mixed or high-missingness cases. (confidence: 1.00)
  Evidence: We evaluate \method{} on four datasets under
    multiple missingness settings, including \wmissing{},
    \mmissing{}, and additional mixed/high-missingness cases [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex

### Claim

- Experiments on multiple multimodal healthcare time-series benchmarks demonstrate that PAMF achieves the strongest overall downstream performance across diverse datasets and missing settings compared to existing baselines. (confidence: 1.00)
  Evidence: Experiments on multiple multimodal healthcare time-series benchmarks show that the proposed method achieves the strongest overall downstream performance across diverse datasets and missing settings compared with existing baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- The prior-aware initialization design reduces inference overhead to fewer function evaluations than diffusion-based alternatives require. (confidence: 0.95)
  Evidence: This design also reduces inference overhead to fewer function evaluations than diffusion-based alternatives~\cite{tashiro2021csdi, alcaraz2023sssd} require. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex

### Limitation

- Existing methods typically represent unobserved data implicitly through masks or missing embeddings without learning instance-specific missing information, and most are designed for only one missingness pattern. (confidence: 1.00)
  Evidence: Existing methods typically represent unobserved data implicitly through masks or missing embeddings, without learning instance-specific missing information, and most are designed for only one missingness pattern. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex
- Existing imputation methods treat missingness uniformly despite their different structural priors, and the imputation process is often isolated from downstream tasks. (confidence: 1.00)
  Evidence: existing imputation methods treat missingness uniformly despite their different structural priors, and the imputation process is often isolated from downstream tasks, preventing downstream tasks from guiding imputation toward more informative representations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pamf/source.tex

## PAR3D: A Unified 3D-MLLM with Part-Aware Representation for Scene Understanding

`par3d` | authors: Shaohui Dai, Yansong Qu, You Shen, Shengchuan Zhang, Liujuan Cao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PAR3D is a unified part-aware 3D-MLLM framework designed to understand, reason about, and ground both objects and their parts in 3D scenes. (confidence: 1.00)
  Evidence: In this work, we present PAR3D, a unified part-aware 3D-MLLM framework that enables models to understand, reason about, and ground both objects and their parts in 3D scenes. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- The framework incorporates Part-Aware 3D Representation Learning to enrich 3D visual representations with fine-grained part-level semantics. (confidence: 1.00)
  Evidence: We further develop Part-Aware 3D Representation Learning to enrich 3D visual representations with fine-grained part-level semantics [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- The framework proposes Hierarchical Segmentation Query Generation to ground part targets using hierarchical object-part queries. (confidence: 1.00)
  Evidence: and propose Hierarchical Segmentation Query Generation to ground part targets via hierarchical object-part queries. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- The PAR3D framework is built upon 3D-LLaVA, a 3D-MLLM that unifies language-based 3D scene understanding and referring segmentation. (confidence: 1.00)
  Evidence: Our framework builds on 3D-LLaVA~\cite{deng20253dllava}, a 3D-MLLM that unifies language-based 3D scene understanding and referring segmentation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex

### Dataset

- The authors introduce ScenePart, a synthetic 3D scene dataset featuring part-level annotations and language instructions to enable the training and evaluation of part-aware 3D scene understanding. (confidence: 1.00)
  Evidence: To enable training and evaluation of part-aware 3D scene understanding, we introduce ScenePart, a synthetic 3D scene dataset with part-level annotations and language instructions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- The ScenePart dataset comprises 800 scenes containing 21K object masks, 44K part masks, and 273K language-task annotations. (confidence: 1.00)
  Evidence: In total, ScenePart contains 800 scenes with 21K object masks, 44K part masks, and 273K language-task annotations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- ScenePart-200K serves as the training set, while ScenePart-QA and ScenePart-Seg are used as test splits for evaluating part-aware 3D question answering and referring segmentation, respectively. (confidence: 1.00)
  Evidence: Based on these annotations, we build ScenePart-200K as the training set... For evaluation, we further construct two test splits: ScenePart-QA evaluates part-aware 3D question answering with diverse question types, while ScenePart-Seg evaluates referring segmentation across objects and parts at different granularities. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex
- ScenePart is constructed by placing part-annotated 3D objects from 3D-CoMPaT into synthesized indoor layouts generated by MiDiffusion on 3D-FRONT floor plans. (confidence: 1.00)
  Evidence: First, we preprocess part-annotated 3D assets from 3D-CoMPaT... Second, we generate indoor layouts using MiDiffusion... on floor plans from 3D-FRONT [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex

### Claim

- Extensive experiments demonstrate that the proposed method substantially improves part-level question answering and referring segmentation while maintaining strong performance on object-level vision-language tasks. (confidence: 1.00)
  Evidence: Extensive experiments show that our method substantially improves part-level question answering and referring segmentation, while also achieving strong performance across object-level vision-language tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex

### Limitation

- Existing 3D-MLLMs are largely object-centric, which limits their capacity to model the fine-grained part structures necessary for embodied interaction with 3D environments. (confidence: 1.00)
  Evidence: However, existing 3D-MLLMs remain largely object-centric, limiting their ability to model fine-grained part structures that are essential for embodied interaction with 3D environments. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/par3d/source.tex

## PHASER: Phase-Aware and Semantic Experience Replay for Vision-Language-Action Models

`phaser` | authors: Ziyang Chen, Shaoguang Wang, Weiyu Guo, Qianyi Cai, He Zhang, Pengteng Li, Yiren Zhao, Yandong Guo | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PHASER is an architecture-agnostic continual learning framework for Vision-Language-Action models that uses phase-centric capacity allocation for equal memory support across sub-skills and multi-modal interference routing to prioritize historical phases at high risk of forgetting. (confidence: 1.00)
  Evidence: To overcome these limitations, we introduce PHASER, an architecture-agnostic continual learning framework. PHASER employs a phase-centric capacity allocation to guarantee equal memory support for all sub-skills, coupled with a multi-modal interference routing strategy that dynamically prioritizes historical phases at high risk of forgetting. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/summary.md
- PHASER integrates Auto-PC, a pipeline combining unsupervised action-signal change-point detection with VLM-based semantic verification to autonomously extract temporal boundaries without manual supervision. (confidence: 1.00)
  Evidence: Furthermore, to enable fully autonomous lifelong adaptation, we integrate Auto-PC, a lightweight pipeline combining unsupervised action-signal change-point detection with VLM-based semantic verification to extract temporal boundaries without intensive manual supervision. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/summary.md
- PHASER's phase-centric capacity floor guarantees foundational kinematic stability, which allows the routing module to safely reallocate residual buffer budget toward at-risk historical phases. (confidence: 1.00)
  Evidence: Integrating the phase-centric capacity floor completely resolves this failure mode. Mechanistically, the capacity floor guarantees foundational kinematic stability, empowering the routing module to safely reallocate the residual buffer budget toward explicitly targeting at-risk historical phases [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/source.tex

### Benchmark

- PHASER is evaluated on the LIBERO continual learning suites across three different Vision-Language-Action backbones. (confidence: 1.00)
  Evidence: Evaluated across three VLA backbones on LIBERO continual learning suites, PHASER yields substantial empirical improvements [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/summary.md

### Claim

- PHASER improves the Average Success Rate by up to 31% compared to matched-budget experience replay and achieves an 87.8% final ASR on the LIBERO-Goal continual learning setting. (confidence: 1.00)
  Evidence: increasing Average Success Rate (ASR) by up to 31% over matched-budget ER and achieving an 87.8% final ASR on the LIBERO-Goal CL setting. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/summary.md
- In manipulation continual learning, forgetting manifests as phase-localized instability where a single bottleneck phase failure ruins the entire trajectory, making retention dependent on per-phase tail variance rather than mean trajectory loss. (confidence: 1.00)
  Evidence: Unlike classification CL where forgetting manifests as uniform calibration drift, manipulation CL exhibits \emph{phase-localized instability}: rollout success is a multiplicative product over sub-skills ($\mathrm{ASR}\propto\prod_p s(\phi_p)$), meaning a transient failure on any single bottleneck phase deterministically ruins the trajectory regardless of how well the rest retain. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/source.tex
- Uniform experience replay systematically starves the shortest sub-skills and exacerbates catastrophic variance because natural phase durations can vary by up to an order of magnitude. (confidence: 1.00)
  Evidence: Crucially, because natural phase durations vary by up to an order of magnitude (App.~\ref{app:phase_nonuniformity}), uniform replay systematically starves the shortest sub-skills and exacerbates this catastrophic variance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/source.tex
- Using multi-modal routing without a phase capacity floor causes catastrophic degradation under strict memory bounds because Boltzmann routing over-concentrates the budget and evicts vulnerable short phases. (confidence: 1.00)
  Evidence: While augmenting ER with multi-modal routing yields general improvements across most settings, it suffers catastrophic degradation under the strictly bounded OV-Long setting (Tab.~\ref{tab:routing_ablation}). Under such extreme memory pressure, Boltzmann routing over-concentrates the limited budget, inadvertently evicting vulnerable short phases before their retention can saturate. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/source.tex
- Forgetting under uniform experience replay is characterized by a heavy-tailed dispersion in per-phase action loss rather than a length-dependent decay. (confidence: 1.00)
  Evidence: Per-phase action loss on QG-3B $\times$ LIBERO-Long reveals that forgetting under uniform ER is characterized not by a length-dependent decay, but by a heavy-tailed dispersion (Fig.~\ref{fig:phase_starvation}). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phaser/source.tex

## PRPO: Perception-Reinforced Policy Optimization via Token-Level Dynamic Advantage Reshaping

`prpo` | authors: Qiming Li, Tianlun Li, Xiaolong Cheng, Hangyu Li, Ruiyan Gong, Kangning Niu, Kaitao Jiang, Mu Xu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- Perception-Reinforced Policy Optimization (PRPO) is a token-level reinforcement learning framework designed to explicitly identify and reinforce pivotal perceptual tokens within long-horizon multimodal reasoning trajectories. (confidence: 1.00)
  Evidence: we propose Perception-Reinforced Policy Optimization (PRPO), a token-level reinforcement learning framework that explicitly identifies and reinforces pivotal perceptual tokens within long-horizon multimodal reasoning trajectories. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/summary.md
- Robust Visual Dependency (RVD) is a metric introduced in PRPO that identifies tokens whose predictions are visually grounded and perturbation-stable, filtering out brittle or noisy visual tokens. (confidence: 1.00)
  Evidence: PRPO introduces Robust Visual Dependency (RVD), a principled metric that identifies tokens whose predictions are both visually grounded and perturbation-stable, filtering out brittle or noisy visual tokens. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/summary.md
- Perceptual Advantage Reshaping (PAR) is a token-level credit assignment technique that amplifies perceptually informative tokens while preserving stable gradients for non-perceptual tokens. (confidence: 1.00)
  Evidence: Based on RVD, we further propose Perceptual Advantage Reshaping (PAR), a token-level credit assignment technique that amplifies perceptually informative tokens while preserving stable gradients for non-perceptual tokens. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/summary.md

### Benchmark

- MathVerse is used as a benchmark to conduct error analysis on multimodal reasoning failures. (confidence: 1.00)
  Evidence: we conduct an error analysis on MathVerse~\citep{zhang2024mathverse} using Qwen2.5-VL-7B. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/source.tex

### Claim

- PRPO achieves average performance gains of 23.3% and 21.1% on 3B and 7B model scales, respectively, across seven multimodal reasoning benchmarks. (confidence: 1.00)
  Evidence: Extensive experiments on seven multimodal reasoning benchmarks demonstrate that PRPO consistently outperforms strong LVLM baselines across both 3B and 7B model scales, achieving average gains of 23.3% and 21.1%, respectively. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/summary.md
- An error analysis on the MathVerse benchmark using Qwen2.5-VL-7B revealed that most multimodal reasoning failures are caused by visual perception errors within long reasoning trajectories rather than a lack of reasoning capability. (confidence: 1.00)
  Evidence: we conduct an error analysis on MathVerse~\citep{zhang2024mathverse} using Qwen2.5-VL-7B. As shown in Figure~\ref{error}, the majority of failures do not stem from insufficient reasoning capability, but from errors in visual perception occurring within long reasoning trajectories. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/source.tex

### Limitation

- Existing RLVR methods rely on trajectory-level outcome rewards that assign identical learning signals to all generated tokens, which is mismatched for multimodal reasoning where only a sparse subset of tokens is causally grounded in visual evidence. (confidence: 1.00)
  Evidence: existing RLVR methods primarily rely on trajectory-level outcome rewards, which assign identical learning signals across all generated tokens. This coarse-grained credit assignment is fundamentally mismatched to multimodal reasoning, where only a sparse subset of tokens is causally grounded in visual evidence. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/prpo/summary.md

## PTQ4ARVG: Post-Training Quantization for AutoRegressive Visual Generation Models

`ptq4arvg` | authors: Xuewen Liu, Zhikai Li, Jing Zhang, Mengjuan Chen, Qingyi Gu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/BienLuky/PTQ4ARVG, https://github.com/FoundationVision/VAR, https://github.com/bytedance/1d-tokenizer, https://github.com/goodfeli/dlbook_notation, https://github.com/thu-nics/ViDiT-Q

### Method

- PTQ4ARVG is a training-free post-training quantization (PTQ) framework designed for ARVG models. (confidence: 1.00)
  Evidence: we propose PTQ4ARVG, a training-free post-training quantization (PTQ) framework [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- Gain-Projected Scaling (GPS) mitigates channel-wise outliers by expanding the quantization loss via a Taylor series to quantify the gain of scaling for activation-weight quantization, and derives the optimal scaling factor through differentiation. (confidence: 1.00)
  Evidence: Gain-Projected Scaling (GPS) mitigates the channel-wise outliers, which expands the quantization loss via a Taylor series to quantify the gain of scaling for activation-weight quantization, and derives the optimal scaling factor through differentiation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- Static Token-Wise Quantization (STWQ) addresses token-wise variance without incurring dynamic calibration overhead by leveraging the fixed token length and position-invariant distribution across samples inherent to ARVG models. (confidence: 1.00)
  Evidence: Static Token-Wise Quantization (STWQ) leverages the inherent properties of ARVG, fixed token length and position-invariant distribution across samples, to address token-wise variance without incurring dynamic calibration overhead. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- Distribution-Guided Calibration (DGC) eliminates sample-wise distribution mismatch by selecting samples that contribute most to distributional entropy. (confidence: 1.00)
  Evidence: Distribution-Guided Calibration (DGC) selects samples that contribute most to distributional entropy, eliminating the sample-wise distribution mismatch. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md

### Claim

- AutoRegressive Visual Generation (ARVG) models retain an architecture compatible with language models, while achieving performance comparable to diffusion-based models. (confidence: 1.00)
  Evidence: AutoRegressive Visual Generation (ARVG) models retain an architecture compatible with language models, while achieving performance comparable to diffusion-based models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- Existing quantization methods fail to generalize effectively to AutoRegressive Visual Generation (ARVG) models. (confidence: 1.00)
  Evidence: existing quantization methods fail to generalize effectively to ARVG models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- Quantizing ARVG models presents three key challenges: severe outliers at the channel-wise level, highly dynamic activations at the token-wise level, and mismatched distribution information at the sample-wise level. (confidence: 1.00)
  Evidence: identify three key challenges: (1) severe outliers at channel-wise level, (2) highly dynamic activations at token-wise level, and (3) mismatched distribution information at sample-wise level. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md
- PTQ4ARVG can effectively quantize ARVG family models to 8-bit and 6-bit precision while maintaining competitive performance. (confidence: 1.00)
  Evidence: Extensive experiments show that PTQ4ARVG can effectively quantize the ARVG family models to 8-bit and 6-bit while maintaining competitive performance. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ptq4arvg/summary.md

## PaCo-VLA: Passivity-Shielded Compliance Prior for Contact-Rich Vision-Language-Action Manipulation

`paco-vla` | authors: Haofan Cao, Zhaoyang Li, Zhichao You, Liang Guo, Tianrui Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PaCo-VLA treats Vision-Language-Action (VLA) network outputs as task-level compliance proposals, such as semantic bindings, task stages, and admittance schedules, instead of direct motor commands. (confidence: 1.00)
  Evidence: Rather than trusting VLAs with direct motor commands, PaCo-VLA treats network outputs as task-level compliance proposals: semantic bindings, task stages, and admittance schedules. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex
- A proposal-independent passivity shield governs the VLA's compliance proposals using energy-tank accounting and boundary checks to prevent invalid or stale predictions from violating low-level contact physics. (confidence: 1.00)
  Evidence: A high-frequency, proposal-independent passivity shield governs these proposals through energy-tank accounting and boundary checks, preventing invalid, stale, or unverified model predictions from bypassing low-level contact physics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex
- PaCo-VLA's decoupled architecture allows for causal evaluation of semantic value through paired simulated counterfactual trials, isolating semantic contributions from geometric shortcuts or shield effects. (confidence: 1.00)
  Evidence: This decoupled architecture also enables causal evaluation, isolating semantic contributions from geometric shortcuts. [...] We therefore evaluate semantic value with paired simulated counterfactual trials instead of aggregate success alone. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex
- The compliance prior interface emits a proposal vector containing the semantic binding, task stage, recovery cue, proposed diagonal admittance schedule, and validity quantities at each control sample. (confidence: 1.00)
  Evidence: At each control sample, the proposal source emits \hat{u}_k = \left(\hat{b}_k,\hat{s}_k,\hat{r}_k,\hat{\theta}_k,\hat{q}_k\right), where \hat{b}_k is the semantic binding or target, \hat{s}_k is the task stage, \hat{r}_k is a recovery cue, \hat{\theta}_k=(\hat{M}_k,\hat{D}_k,\hat{K}_k) is the proposed diagonal admittance schedule, and \hat{q}_k records validity quantities [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex
- The proposal gate in PaCo-VLA accepts only finite proposals whose semantic context matches the current task, otherwise supplying a conservative recovery candidate. (confidence: 1.00)
  Evidence: The proposal gate accepts only finite proposals whose semantic context matches the current task; otherwise it supplies a conservative recovery candidate, as summarized in Algorithm~\ref{alg:paco-gate}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex

### Claim

- Simulated and real-world connector-insertion experiments demonstrate that PaCo-VLA achieves superior precision compared to unshielded VLA baselines and maintains zero passivity violations under adversarial compliance shifts. (confidence: 1.00)
  Evidence: Extensive simulated and real-world connector-insertion experiments demonstrate that PaCo-VLA achieves superior precision over unshielded VLA baselines, sustaining zero passivity violations even under adversarial compliance shifts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex
- The PaCo-VLA framework establishes a provably sampled-passive runtime contract at the admittance port to safely deploy foundation models in contact-rich manipulation domains. (confidence: 1.00)
  Evidence: This framework establishes a provably sampled-passive runtime contract at the admittance port and provides a runtime interface for deploying foundation models in contact-rich domains. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/paco-vla/source.tex

## ParetoSlider: Diffusion Models Post-Training for Continuous Reward Control

`paretoslider` | authors: Shelly Golan, Michael Finkelson, Ariel Bereslavsky, Yotam Nitzan, Or Patashnik | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Partially Observable Adversarial Patch Attacks on Vision-Language-Action Models in Robotics

`2606_03556` | authors: Xiaofei Wang, Mingliang Han, Tianyu Hao, Yi Yang, Yun-Bo Zhao, Keke Tang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors propose a partially observable threat model where the adversary uses only a short prefix of the trajectory to generate a fixed adversarial patch that is applied to all subsequent frames. (confidence: 1.00)
  Evidence: We address this limitation by formulating a partially observable threat model, where the adversary can exploit only a short prefix of the trajectory to generate a fixed patch applied to all subsequent frames. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03556/source.tex
- The first phase of the proposed framework localizes the adversarial patch by utilizing the model's attention maps to find visually critical regions corresponding to the full instruction. (confidence: 1.00)
  Evidence: First, we localize the patch using the model's attention maps to identify visually critical regions that correspond to the full instruction. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03556/summary.md
- The second phase of the framework optimizes the patch to disrupt the semantic grounding of target objects and increase the curvature of action trajectories, compounding failures in perception and control. (confidence: 1.00)
  Evidence: Then, we optimize the patch to disrupt the semantic grounding of target objects and increase the curvature of action trajectories, thereby compounding failures in both perception and control. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03556/source.tex

### Claim

- Experiments in both simulation and real-world robotic environments demonstrate that the proposed method sustains adversarial effects under partial observability, causing long-horizon disruptions and significantly reducing task success rates. (confidence: 1.00)
  Evidence: Extensive experiments in simulation and real-world robotic environments show that our method sustains adversarial effects under partial observability, inducing long-horizon disruptions and significantly reducing task success rates. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03556/source.tex

### Limitation

- Existing adversarial patch attacks on Vision-Language-Action (VLA) models assume full access to the entire execution trajectory, which is an unrealistic requirement in practical scenarios. (confidence: 1.00)
  Evidence: Existing work shows that adversarial patches can mislead VLA-based robots but assumes full access to the entire execution trajectory, an unrealistic requirement in practice. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03556/source.tex

## Per-Group Error, Not Total MSE: Fine-Tuning Vision-Language-Action Models for 11-DoF Mobile Manipulation

`2606_00253` | authors: Pau Montagut Bofi, Mario García Blasco, Tessa Pulli, Markus Vincze | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/paumontagut/per-group-mse-vla

### Method

- The authors evaluate models by decomposing the 11D action vector into four functional groups (arm, gripper, head, base) and computing the mean squared error for each group. (confidence: 1.00)
  Evidence: We decompose the 11D action vector into four functional groups $\mathcal{G} = \{\text{arm}, \text{gripper}, \text{head}, \text{base}\}$ and compute: ... $\text{MSE}_g = \frac{1}{|g|} \sum_{j \in g} (\hat{a}_j - a_j)^2$ [paper]
- The authors propose a two-phase fine-tuning pipeline for SmolVLA that natively supports 11D output. (confidence: 1.00)
  Evidence: We address this through: (1) a two-phase fine-tuning pipeline for SmolVLA with native 11D output [paper]

### Dataset

- SmolVLA was pretrained on a 109,269-episode subset of the ICRA 2026 workshop dataset and fine-tuned on a 3,971-episode pick-up task release. (confidence: 1.00)
  Evidence: Phase 1: pretraining on a 109,269-episode subset (531 tasks) of the ICRA 2026 workshop dataset for 20k steps... Phase 2: task-specific fine-tuning on a six-task pick-up release from the same workshop (3,971 episodes) [paper]

### Benchmark

- Real-robot validation was conducted using 60 trials on the Toyota HSR performing a pick-up task, with each trial graded on a 4-point rubric. (confidence: 1.00)
  Evidence: We conducted 60 trials on the Toyota HSR (20 per model) on a pick-up task... Each trial was graded on a 4-point rubric [paper]

### Claim

- Fine-tuning Vision-Language-Action models for mobile manipulators with heterogeneous joint spaces can result in the checkpoint with the lowest aggregate MSE not being the best performing on a real robot. (confidence: 1.00)
  Evidence: the checkpoint with the lowest aggregate MSE is not the one that performs best on the real robot. [paper] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00253/source.tex
- During SmolVLA fine-tuning, the mobile base converges the slowest and acts as the bottleneck that limits overall performance. (confidence: 1.00)
  Evidence: The base is the last group to converge and sets the ceiling on the aggregate. This is the sense in which the mobile base is the bottleneck of SmolVLA fine-tuning. [paper]
- Expert-only fine-tuning of the pi_0.5 model reduces total MSE but degrades arm accuracy, resulting in worse real-robot performance compared to the untouched baseline. (confidence: 1.00)
  Evidence: expert-only 3k underperforms the untouched baseline despite having lower total MSE (0.95 vs. 1.04) ... the gains concentrate on the gripper and the base ... while the arm (already well-predicted at 0.30) degrades to 0.59. [paper]
- Per-group error is concluded to be a more reliable signal than total MSE for selecting checkpoints on robots with heterogeneous action spaces. (confidence: 1.00)
  Evidence: We conclude that per-group error is a more reliable signal than total MSE for checkpoint selection on robots with heterogeneous action spaces. [paper] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00253/source.tex

### Limitation

- The very low head MSE observed in SmolVLA is likely an artifact of the dataset, where target objects are always within the initial field of view, rather than a general solution to head control. (confidence: 1.00)
  Evidence: Head MSE is already very low after pretraining. However, we caution that this likely reflects the nature of the dataset (in the pick-up task, the target objects are always within the initial field of view, so the head rarely needs to reorient) rather than the problem being solved in a general sense. [paper] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00253/source.tex
- The authors were restricted to expert-only fine-tuning for pi_0.5 because full fine-tuning exceeded their 24 GB VRAM limit and LoRA was incompatible with the provided checkpoint architecture. (confidence: 1.00)
  Evidence: full fine-tuning exceeds 24 GB VRAM, and LoRA is incompatible with the architecture of the provided checkpoint. [paper]

## PhAIL: A Real-Robot VLA Benchmark and Distributional Methodology

`phail` | authors: Sergey Arkhangelskiy | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Positronic-Robotics/phail-paper, https://github.com/Positronic-Robotics/positronic

### Method

- The evaluation methodology uses the time-to-success cumulative distribution function (CDF) as the evaluation primitive. (confidence: 1.00)
  Evidence: the time-to-success cumulative distribution function (CDF) as the evaluation primitive [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- Hard failures during robot operations are absorbed as T = infinity ghost events rather than being treated as censored tails. (confidence: 1.00)
  Evidence: hard failures (items lost outside the workspace, items dropped on the table at episode end, safety stops) are absorbed as $T = \infty$ ghost events rather than censored tails. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- Scoring is performed via Human-Relative Throughput (HRT), a dimensionless scalar with bootstrap confidence intervals anchored to same-fixture human teleoperation. (confidence: 1.00)
  Evidence: The first is scoring via Human-Relative Throughput (HRT), a dimensionless scalar with bootstrap confidence intervals, anchored to same-fixture human teleoperation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- The significance test uses the Kolmogorov-Smirnov test, computed per-object and macro-averaged across objects, to compare time-to-success CDFs. (confidence: 1.00)
  Evidence: The second is a significance test (Kolmogorov-Smirnov, computed per-object and macro-averaged across objects). [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- The time-to-success CDF is estimated using the Kaplan-Meier product-limit estimator on the collection of times and event indicators. (confidence: 1.00)
  Evidence: The CDF $F(t) = P(T \le t)$ is estimated by the Kaplan-Meier product-limit estimator on the $(T, E)$ collection. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/source.tex

### Dataset

- The PhAIL benchmark includes a real-robot dataset of approximately 990 episodes, including 396 same-fixture human-teleoperation reference rollouts on a Franka FR3 across four objects. (confidence: 1.00)
  Evidence: a real-robot dataset of $\sim$990 episodes (including 396 same-fixture human-teleoperation reference rollouts) on a Franka FR3, four trained objects [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/source.tex

### Benchmark

- PhAIL (Physical AI Leaderboard) is an open real-robot benchmark on a Franka FR3 that evaluates vision-language-action (VLA) policies using a distributional evaluation methodology. (confidence: 1.00)
  Evidence: We introduce PhAIL (Physical AI Leaderboard, https://phail.ai), an open real-robot benchmark on a Franka FR3 (dataset, per-rollout artifacts, and end-to-end reference implementation) of a distributional evaluation methodology [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md

### Claim

- The macro-averaged Kolmogorov-Smirnov test resolves close comparisons at N <= 30 rollouts per cell where binary-threshold metrics fail. (confidence: 1.00)
  Evidence: the macro-averaged KS test resolves two close comparisons (GR00T vs. ACT, OpenPI vs. ACT) at $N \le 30$ rollouts per (model, object) cell where binary-threshold metrics do not [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- The best evaluated VLA is approximately 7 times slower per operation (measured by RMST ratio) than the human reference. (confidence: 1.00)
  Evidence: The best evaluated VLA is $\sim 7\times$ slower per operation (RMST ratio) than the human reference. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md
- Standard real-world evaluation of VLA policies using binary success rate at a fixed timeout with N <= 25 rollouts per condition is statistically underpowered and struggles to resolve close comparisons reliably. (confidence: 1.00)
  Evidence: Real-world evaluation of vision-language-action (VLA) policies still rests on binary success rate at a fixed timeout with $N \le 25$ rollouts per condition, almost always without confidence intervals or paired statistical comparison; these cohort sizes struggle to resolve close comparisons reliably. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md

### Limitation

- The closest pair of models (OpenPI vs. GR00T) remains statistically unresolved within the evaluation budget of the study. (confidence: 1.00)
  Evidence: the closest pair (OpenPI vs. GR00T) remains unresolved within our budget. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phail/summary.md

## PhyCritic: Multimodal Critic Models for Physical AI

`phycritic` | authors: Tianyi Xiong, Shihao Wang, Guilin Liu, Yi Dong, Ming Li, Heng Huang, Jan Kautz, Zhiding Yu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/goodfeli/dlbook_notation

### Method

- PhyCritic is optimized through a two-stage RLVR pipeline comprising a physical skill warmup stage and self-referential critic finetuning. (confidence: 1.00)
  Evidence: We introduce PhyCritic, a multimodal critic model optimized for physical AI through a two-stage RLVR pipeline: a physical skill warmup stage that enhances physically oriented perception and reasoning, followed by self-referential critic finetuning [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/summary.md
- During self-referential critic finetuning, the model generates its own prediction to serve as an internal reference before evaluating candidate responses. (confidence: 1.00)
  Evidence: self-referential critic finetuning, where the critic generates its own prediction as an internal reference before judging candidate responses, improving judgment stability and physical correctness. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/summary.md

### Benchmark

- The paper introduces a new benchmark referred to as PhyCritic-Bench alongside a specific critic training dataset. (confidence: 0.90)
  Evidence: Critic Training Dataset
- \ours-Bench [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/summary.md

### Claim

- PhyCritic demonstrates strong performance improvements over open-source baselines on both physical and general-purpose multimodal judge benchmarks. (confidence: 1.00)
  Evidence: Across both physical and general-purpose multimodal judge benchmarks, PhyCritic achieves strong performance gains over open-source baselines [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/summary.md
- Utilizing PhyCritic as a policy model leads to further improvements in perception and reasoning for physically grounded tasks. (confidence: 1.00)
  Evidence: when applied as a policy model, further improves perception and reasoning in physically grounded tasks. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/source.tex

### Limitation

- Current critic models are mostly trained on general visual tasks, which leaves physical AI tasks like perception, causal reasoning, and planning underexplored. (confidence: 1.00)
  Evidence: existing critics are primarily trained in general visual domains such as captioning or image question answering, leaving physical AI tasks involving perception, causal reasoning, and planning largely underexplored. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/phycritic/source.tex

## PhyEdit: Towards Real-World Object Manipulation via Physically-Grounded Image Editing

`phyedit` | authors: Ruihang Xu, Dewei Zhou, Xiaolong Shen, Fan Ma, Yi Yang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Physics in 2-Steps: Locking Motion Priors Before Visual Refinement Erases Them

`physics-in-2-steps` | authors: Woojung Han, Seil Kang, Youngjun Jun, Min-Hung Chen, Fu-En Yang, Seong Jae Hwang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PhaseLock is a training-free framework that extracts a motion prior from just 2 steps and enforces it onto high-fidelity generation via Latent Delta Guidance to preserve valid motion priors throughout the denoising trajectory. (confidence: 1.00)
  Evidence: we propose PhaseLock, a training-free framework that preserves the valid motion priors from few-step inference throughout the denoising trajectory. Rather than relying on full-step inference for physical consistency, PhaseLock extracts a motion prior from just 2 steps and enforces it onto high-fidelity generation via Latent Delta Guidance. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/summary.md

### Dataset

- The experiments employ Diffusion Transformer models, specifically CogVideoX and Wan 2.1. (confidence: 1.00)
  Evidence: We employed Diffusion Transformer models, specifically CogVideoX~\cite{yang2024cogvideox} and Wan 2.1~\cite{wan2025wan}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex

### Benchmark

- The study utilizes the Physics-IQ benchmark, which provides Ground Truth (GT) videos, to evaluate physical consistency and visual quality. (confidence: 1.00)
  Evidence: we utilized the Physics-IQ benchmark~\cite{motamed2025generative}, which provides Ground Truth (GT) videos. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex

### Claim

- A 2-step generation in image-to-video diffusion models often exhibits better physical consistency than a 50-step output from the same model. (confidence: 1.00)
  Evidence: We reveal a surprising finding: a 2-step generation often exhibits better physical consistency than a 50-step output from the same model. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/summary.md
- During the denoising process, the phase degrades significantly (dropping by approximately 18% from step 2 to step 50), whereas the magnitude remains relatively stable. (confidence: 1.00)
  Evidence: the phase degrades significantly (dropping by $\approx 18\%$ from step 2 to step 50), whereas the magnitude remains relatively stable. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex
- PhaseLock improves physical consistency by an average of 6.2 points across diverse models while maintaining visual fidelity, with negligible overhead of 1.06x time and 1.02x memory. (confidence: 1.00)
  Evidence: Our approach effectively mitigates phase degradation, improving physical consistency by an average of 6.2 points across diverse models while largely maintaining visual fidelity, with negligible overhead ($1.06\times$ time, $1.02\times$ memory) [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex
- Phase corruption causes continuous drift in object location and severely impacts velocity consistency, while magnitude error saturates and shows an invariant response. (confidence: 1.00)
  Evidence: Phase corruption causes continuous drift in object location, while magnitude error saturates at $\alpha=0.25$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex
- Injecting 50% uniform noise into the phase spectrum induces an 8.5x larger optical flow End-Point Error than equivalent noise injected into the magnitude spectrum. (confidence: 1.00)
  Evidence: injecting $50\%$ uniform noise into the phase spectrum induces an $8.5\times$ larger optical flow End-Point Error than equivalent noise injected into the magnitude spectrum (EPE: $9.74$ vs $1.14$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex

### Limitation

- The proposed analysis and method rely on the denoising process, making them inapplicable to autoregressive Transformer-based models such as VideoPoet and MAGI-1. (confidence: 1.00)
  Evidence: Our analysis and method rely on the denoising process; therefore, autoregressive Transformer-based models such as VideoPoet~\cite{kondratyuk2023videopoet} and MAGI-1~\cite{teng2025magi} are not applicable to this study. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/physics-in-2-steps/source.tex

## PiL-World: A Chunk-Wise World Model for VLA Policy-in-the-Loop Evaluation

`pil-world` | authors: Chong Ma, Taiyi Su, Jian Zhu, Jianjun Zhang, Zitai Huang, Yi Xu, Hanli Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- PiL-World is a chunk-wise world model designed for policy-in-the-loop VLA evaluation that generates multi-view future observations conditioned on VLA-predicted action chunks. (confidence: 1.00)
  Evidence: we propose PiL-World, a chunk-wise world model designed for policy-in-the-loop VLA evaluation. Given the current observation and the action trajectory rolled out by a VLA policy, PiL-World generates multi-view future observations that are consistent with the VLA rollout and match the image inputs required by the policy. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/summary.md
- PiL-World converts absolute dual-arm action commands into head-view visual control frames using robot kinematics and camera projection to condition video generation. (confidence: 1.00)
  Evidence: we convert absolute dual-arm action commands into head-view gripper markers through robot kinematics and camera projection. The marker locations encode projected gripper positions, while marker sizes encode the corresponding gripper states. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex
- PiL-World maintains a latent history memory by encoding recent multi-view frames to provide visual context for future prediction and prevent drift in closed-loop rollouts. (confidence: 1.00)
  Evidence: PiL-World maintains a latent history memory $\mathcal{H}_t$ by encoding recent multi-view frames as visual context for future prediction. These history frames are real observations at the beginning of rollout and are updated with generated observations in later rollout rounds. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex
- PiL-World is pretrained on RealSource World to learn general dynamics and then fine-tuned on target-task trajectories that include both successful demonstrations and failed teleoperated executions. (confidence: 1.00)
  Evidence: We first pretrain the model on RealSource World~\citep{realsourceworld2025} to learn general action-conditioned robot-environment dynamics, and then fine-tune it on target-task trajectories collected from the same real-robot setup used for evaluation. As shown in Fig.~\ref{fig:method}(c), the target-task data include both successful demonstrations and failed teleoperated executions [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex
- The authors introduce the hallucination-free ratio (HFR) metric to quantify how long dense imagined rollouts remain credible before obvious hallucination appears. (confidence: 1.00)
  Evidence: introduce a new hallucination-free ratio (HFR), which quantifies how long dense imagined rollouts remain credible before obvious hallucination appears. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex

### Dataset

- RealSource World is used as the pretraining dataset for PiL-World to learn general robot-environment dynamics. (confidence: 1.00)
  Evidence: it is first pretrained on RealSource World~\citep{realsourceworld2025} to learn general robot-environment dynamics [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex

### Benchmark

- PiL-World is evaluated on three real dual-arm manipulation tasks: sorting cubes, stacking bowls, and stacking blocks. (confidence: 1.00)
  Evidence: We evaluate PiL-World on three real dual-arm manipulation tasks: sorting cubes, stacking bowls, and stacking blocks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex

### Claim

- PiL-World reduces the error between VLA success rates measured in real-world rollouts and those estimated through closed-loop world-model evaluation from 63.2% to 12.0% compared to the baseline. (confidence: 1.00)
  Evidence: compared with the baseline, it reduces the error between VLA success rates measured in real-world rollouts and those estimated through closed-loop world-model evaluation from 63.2% to 12.0%. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/summary.md
- PiL-World generates imagined rollouts that are highly consistent with real robot executions. (confidence: 0.95)
  Evidence: PiL-World generates imagined rollouts that are highly consistent with real robot executions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pil-world/source.tex

## Plug-and-Play Guidance for Discrete Diffusion Models via Gradient-Informed Logit Correction

`2606_06303` | authors: Hongkun Dou, Zike Chen, Fengji Li, Hongjue Li, Yue Deng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces Gradient-Informed Logit Correction (GILC), a plug-and-play framework for controllable generation with discrete diffusion models that estimates guidance signals by repurposing the pretrained denoising network as a variational proxy. (confidence: 1.00)
  Evidence: In this paper, we present \underline{\textbf{G}}radient-\underline{\textbf{I}}nformed \underline{\textbf{L}}ogit \underline{\textbf{C}}orrection (\textbf{GILC}), a plug-and-play framework that efficiently estimates guidance signals by repurposing the pretrained denoising network as a variational proxy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex
- GILC introduces a Jacobian-free mechanism that directly corrects the clean prediction logits to circumvent gradient instability in high-dimensional discrete spaces. (confidence: 1.00)
  Evidence: To circumvent the gradient instability inherent in high-dimensional discrete spaces, we introduce a Jacobian-free mechanism that directly corrects the clean prediction logits, facilitating stable and effective guidance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex
- The framework combines the Gumbel-Softmax trick and a Straight-Through estimator to maintain gradient flow in the discrete space. (confidence: 1.00)
  Evidence: 1) combining the Gumbel-Softmax (GS) trick \cite{jang2016categorical} and a Straight-Through (ST) estimator \cite{bengio2013estimating} to maintain gradient flow in the discrete space [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex
- GILC establishes a formal connection to policy gradients to universally handle non-differentiable objectives. (confidence: 1.00)
  Evidence: Furthermore, we establish a formal connection between GILC and policy gradients \cite{williams1992simple} to universally handle non-differentiable objectives. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex
- The paper adopts a discrete diffusion framework that directly interpolates between the clean data and a fixed prior distribution, such as an absorbing mask token. (confidence: 1.00)
  Evidence: we adopt a simpler framework, proposed by \citet{sahoo2024simple} and \citet{shi2024simplified}, which directly interpolates between the clean data $\mathbf{x}$ and a fixed prior distribution $\boldsymbol{\pi}$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex

### Dataset

- The method is evaluated on DNA sequence design, protein sequence engineering, and multimodal molecular generation tasks. (confidence: 1.00)
  Evidence: We demonstrate the effectiveness of GILC across a broad set of scientific domains, including DNA sequence design, protein sequence engineering, and multimodal molecular generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex

### Claim

- GILC achieves state-of-the-art performance without additional training across DNA, protein sequence, and molecular generation tasks, frequently outperforming fine-tuning approaches. (confidence: 1.00)
  Evidence: Extensive experiments across DNA, protein sequence, and molecular generation tasks demonstrate that GILC achieves state-of-the-art performance without additional training, frequently outperforming fine-tuning approaches. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex

### Limitation

- Existing plug-and-play methods for discrete diffusion based on Sequential Monte Carlo or importance sampling suffer from prohibitively high computational costs and limited steering effectiveness. (confidence: 1.00)
  Evidence: Existing efforts based on Sequential Monte Carlo ($\text{SMC}$) \cite{wu2023practical,uehara2024understanding} or importance sampling \cite{li2024derivative,lin2025tfg,ou2026inferencetime} often suffer from prohibitively high computational costs and demonstrably limited steering effectiveness. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06303/source.tex

## Popcorn: A Configurable Benchmark for Visual Evidence in Multimodal Movie Recommendation

`popcorn` | authors: Ali Tourani, Fatemeh Nazary, Yashar Deldjoo, Tommaso Di Noia | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/RecSys-lab/Popcorn

No research facts available.

## Potential-Guided Flow Matching for Vision-Language-Action Policy Improvement

`2606_04968` | authors: Yunpeng Mei, Jiakai He, Hongjie Cao, Chenyu Wang, Xiaowen Zhu, Yihan Zhou, Jiamin Wang, Chenbo Xin, Peng Cheng, Yuxuan Yang, Yijie Wang, Xinhu Zheng, Gao Huang, Jie Chen, Gang Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- ForesightFlow is a self-guided flow-matching policy that augments each generated action chunk with a learned success-potential trajectory, allowing the same flow to propose and score candidate actions for best-of-K inference without an external critic. (confidence: 1.00)
  Evidence: We introduce ForesightFlow, a self-guided flow-matching policy that augments each generated action chunk with a learned success-potential trajectory. The same flow proposes and scores candidate actions, enabling best-of-$K$ inference without an external critic. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md
- The method utilizes decoupled advantage-weighted flow matching, which applies exponentiated advantage weights exclusively to action velocities while training potential velocities uniformly to prevent overconfident scores. (confidence: 1.00)
  Evidence: We address this with decoupled advantage-weighted flow matching, applying exponentiated advantage weights only to action velocities while training potential velocities uniformly. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md
- The authors derive a one-step boundary estimator for conditional flow matching that enables advantage computation using a single stop-gradient forward pass. (confidence: 1.00)
  Evidence: We further derive a one-step boundary estimator for conditional flow matching, allowing advantage computation with a single stop-gradient forward pass. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md
- In ForesightFlow, the success-potential vector is not a separate critic network but rather an additional generated coordinate of the same flow endpoint. (confidence: 1.00)
  Evidence: The potential coordinate is not a separate critic network. It is an additional generated coordinate of the same flow endpoint. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/source.tex

### Benchmark

- The proposed method is evaluated across five BEHAVIOR-1K simulation tasks and five real-world bimanual manipulation tasks. (confidence: 1.00)
  Evidence: Across five BEHAVIOR-1K simulation tasks and five real-world bimanual tasks, ForesightFlow improves over imitation baselines [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md

### Claim

- ForesightFlow outperforms imitation baselines, matches the strongest separate-critic baseline in simulation success, improves real-world success rates, and reduces training compute by 38%. (confidence: 1.00)
  Evidence: ForesightFlow improves over imitation baselines, matches the strongest separate-critic baseline in simulation success, improves real-world success, and reduces training compute by $38\%$. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md
- Ablation studies demonstrate that decoupling prevents value hallucination, the one-step estimator maintains candidate-ranking fidelity, and self-guided sampling enhances long-horizon execution. (confidence: 1.00)
  Evidence: Ablations show that decoupling prevents value hallucination, the one-step estimator preserves candidate-ranking fidelity, and self-guided sampling improves long-horizon execution. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md

### Limitation

- A key challenge in unified architectures is that policy improvement and value calibration require different supervision; applying identical advantage weights to potential coordinates suppresses failure gradients and leads to overconfident scores. (confidence: 1.00)
  Evidence: The key issue is that policy improvement and value calibration require different supervision: advantage weighting should emphasize high-quality actions, but applying the same weights to potential coordinates suppresses failure gradients and creates overconfident scores. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_04968/summary.md

## Pre-VLA: Preemptive Runtime Verification for Reliable Vision-Language-Action and World-Model Rollouts

`pre-vla` | authors: Zhen Sun, Yongjian Guo, Haoran Sun, Luqiao Wang, Wei Lu, Jiachi Ji, Shengzhe Ji, Junwu Xiong, Zhijun Meng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/liustone99/Wi-Fi-Energy-Detection-Testbed-12MTC

### Method

- Pre-VLA is a unified runtime verification architecture that assesses action validity preemptively before physical execution or world-model imagination. (confidence: 1.00)
  Evidence: we propose Pre-VLA, a unified runtime verification architecture that performs preemptive action validity assessment before physical execution or world-model imagination. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/summary.md
- Pre-VLA uses a multimodal backbone with modality-aware pooling and a dual-branch head to predict safety confidence and advantage scores for action chunks. (confidence: 1.00)
  Evidence: Pre-VLA leverages an efficient multimodal backbone with modality-aware pooling and a lightweight dual-branch head to predict both safety confidence and critic-derived advantage scores for candidate action chunks. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/summary.md
- The model is trained using a multi-task objective that includes Focal classification, advantage regression, and soft-threshold calibration. (confidence: 1.00)
  Evidence: we train Pre-VLA with a multi-task objective combining Focal classification, advantage regression, and soft-threshold calibration. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/summary.md
- A dual-mode preemptive resampling scheduler is used during deployment to filter low-quality actions and trigger adaptive resampling within a computation budget. (confidence: 1.00)
  Evidence: During deployment, a dual-mode preemptive resampling scheduler filters low-quality actions and triggers adaptive resampling under a limited computation budget. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex

### Benchmark

- The proposed method is evaluated on the LIBERO robotic manipulation benchmark. (confidence: 1.00)
  Evidence: We conduct a comprehensive evaluation of \method{} on the LIBERO~\cite{liu2023libero} robotic manipulation benchmark [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex

### Claim

- Pre-VLA improves the average closed-loop success rate across four LIBERO suites from 30.79% to 37.62% compared to RynnVLA-002. (confidence: 1.00)
  Evidence: Experiments on the LIBERO benchmark show that \method{} improves the average closed-loop success rate across four suites from 30.79\% to 37.62\% over RynnVLA-002 [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex
- Pre-VLA achieves an average forward verification time of 183.9 ms per action chunk. (confidence: 1.00)
  Evidence: achieves 183.9 ms average forward verification time per action chunk [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex
- On the independent LIBERO test set, Pre-VLA achieves an F1 score of 0.8303, an accuracy of 0.9542, and a false pass rate of 0.0200 for invalid actions. (confidence: 1.00)
  Evidence: Experimental results show that \method{} achieves an F1 score of 0.8303 and an accuracy of 0.9542 on the independent LIBERO test set, while reducing the false pass rate of invalid actions to 0.0200 [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex

### Limitation

- Low-quality actions generated by VLA models can cause physical failures during execution or result in misleading world-model rollouts with redundant rendering costs. (confidence: 1.00)
  Evidence: Low-quality actions may cause physical failures during execution or lead to misleading world-model rollouts with redundant rendering costs. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex
- Real-world offline exploration data is limited and suffers from severe class imbalance, as safe trajectories dominate the distribution and overwhelm rare catastrophic failure samples. (confidence: 1.00)
  Evidence: real-world offline exploration data is often limited~\cite{bjorck2025gr00t} and suffers from severe class imbalance. Since standard safe trajectories dominate the data distribution~\cite{xu2025wod,jiang2026wovr}, rare yet critical catastrophic failure samples can be overwhelmed by abundant safe samples [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pre-vla/source.tex

## ProbeAct: Probe-Guided Training-Free Failure Recovery in Vision-Language-Action Models

`probeact` | authors: Fan Zhang, Seongbin Park, Baharan Mirzasoleiman, Shariar Talebi, Nader Sehatbakhsh | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Q-VGM: Q-Guided Value-Gradient Matching for Flow-Matching VLA Policies

`q-vgm` | authors: Ziqian Wang, Jiayu Sun, Xingjian Mao, Minqian Wang, Yao Mu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## ROG-Grasp: Root-Oriented Geometry for Robotic Grasping and Placement

`rog-grasp` | authors: Zijian An, Augustus Sroka, Ran Yang, Bill Cai, Satoru Eto, Brian Poon, Kelvin Cai, Shijie Geng, Feng Liu, Yiming Feng, Lifeng Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- ROG-Grasp estimates produce orientation from root surface geometry using RGB-D perception, employing a YOLO-based root detector and point cloud plane fitting to infer the root normal. (confidence: 1.00)
  Evidence: This paper presents ROG-Grasp, a geometry-based robotic grasping and placement framework that estimates the produce orientation from root surface geometry using RGB-D perception. A YOLO-based root detector and point cloud plane fitting are used to infer the root normal [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex
- A YOLO-26 segmentation model is fine-tuned on the annotated and augmented dataset to perform body and root segmentation. (confidence: 1.00)
  Evidence: A YOLO-26 segmentation model is then fine-tuned on this dataset to produce body and root segmentation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex
- Robot motions in the framework are executed using Cartesian motion commands specified by position and orientation, rather than joint-space commands. (confidence: 1.00)
  Evidence: In this work, all robot motions are executed using Cartesian motion commands specified by position $\mathbf{p}$ and orientation $\mathbf{R}$, as illustrated in Figure~\ref{arch_fig}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex
- The orientation of the root surface is estimated by applying a least-squares plane fitting method to the extracted 3D root point cloud. (confidence: 1.00)
  Evidence: To estimate the orientation of the tomato root surface, a least-squares plane fitting method is applied to the extracted root point cloud. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex

### Dataset

- The training dataset is constructed using a semi-automatic pipeline where produce body polygon annotations are generated via foreground masking against a contrasting backdrop, while root annotations are created manually. (confidence: 1.00)
  Evidence: Individual frames are extracted, and polygon annotations for the produce body are automatically generated by computing a foreground mask against the contrasting backdrop, as illustrated in Figure~\ref{yolo}. Root annotations must be manually created for each root instance. This semi-automatic pipeline substantially reduces the manual effort required for dataset construction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex

### Claim

- Experiments on tomatoes and onions show that ROG-Grasp achieves high success rates and stable execution time in both isolated and cluttered scenarios. (confidence: 1.00)
  Evidence: Experiments on tomatoes and onions demonstrate high success rates and stable execution time in both isolated and cluttered scenarios. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex
- ROG-Grasp achieves more reliable and accurate grasp completion with faster execution compared to vision-language-action (VLA) policies. (confidence: 1.00)
  Evidence: Compared with vision–language–action (VLA) policies, the proposed method achieves more reliable and accurate grasp completion with faster execution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex

### Limitation

- Vision-language-action (VLA) models struggle to reliably identify the root region of produce, making it difficult for end-to-end learning approaches to achieve the required orientation estimation accuracy for stable grasping. (confidence: 1.00)
  Evidence: However, our preliminary experiments indicate that such models often struggle to reliably identify the root region of produce. As a result, purely learning-based end-to-end learning approaches may have difficulty achieving the orientation estimation accuracy required for stable grasping and controlled placement. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rog-grasp/source.tex

## RQUL-UIE: Revitalizing Quality-Unstable Labels for Underwater Image Enhancement via In-Dataset Self-Supervision

`rqul-uie` | authors: Haochen Hu, Yanrui Bin, Chih-yung Wen, Bing Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- RQUL-UIE employs a diffusion-based, in-dataset self-supervised learning strategy that evaluates label quality using semantic perception embeddings from a pre-trained diffusion model without additional training. (confidence: 1.00)
  Evidence: This paper proposes a diffusion-based, in-dataset self-supervised learning strategy designed to exploit the quality distribution of training labels. Specifically, we evaluate label quality via semantic perception embeddings from a pre-trained diffusion model in a training-free manner. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/summary.md
- The method quantizes label quality scores into noise-level indices to guide a multi-step denoising process, providing level-wise supervision that prevents low-quality labels from degrading the model. (confidence: 1.00)
  Evidence: These quality scores are subsequently quantized into noise-level indices, guiding a multi-step denoising process for level-wise supervision. This mechanism prevents low-quality labels from degrading the model while maximizing their utility during training. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/summary.md
- A Fourier-based refinement network is integrated into the framework to explicitly reconstruct high-frequency components and extract hidden texture details via frequency-domain modulation. (confidence: 1.00)
  Evidence: Furthermore, a Fourier-based refinement network is incorporated to explicitly reconstruct high-frequency components. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/summary.md
- The RQUL-UIE framework utilizes Stable Diffusion 2.1 (SD2.1) as its backbone to leverage extensive priors from large-scale natural image pretraining. (confidence: 1.00)
  Evidence: This work uses Stable Diffusion 2.1 (SD2.1) \footnote{https://huggingface.co/sd2-community/stable-diffusion-2-1} as the backbone, leveraging its extensive prior derived from large-scale natural image pretraining. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/source.tex

### Dataset

- The proposed RQUL-UIE method is quantitatively evaluated on three underwater image datasets: LSUI, EUVP, and UIEB. (confidence: 1.00)
  Evidence: An overview of quantitative comparison among the methods with the top-5 performance on three datasets LSUI \cite{li2021ucolor}, EUVP \cite{islam2020euvp}m and UIEB \cite{li2019uieb} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/source.tex

### Benchmark

- The performance of the underwater image enhancement methods is evaluated using four metrics: MUSIQ, Uranker, TwiceMix, and UIQM. (confidence: 1.00)
  Evidence: regarding four metrics MUSIQ \cite{ke2021musiq}, Uranker \cite{guo2023uranker}, TwiceMix \cite{fu2022twicemix} and UIQM \cite{panetta2015uiqm}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/source.tex

### Claim

- RQUL-UIE consistently outperforms state-of-the-art approaches in restoration quality, achieving the average best performance across the evaluated datasets and metrics. (confidence: 1.00)
  Evidence: Extensive evaluations demonstrate that our method consistently outperforms SOTA approaches in restoration quality. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/summary.md

### Limitation

- Existing paired underwater datasets suffer from unstable label quality because labels are manually selected from previous enhancement works, meaning some labels are of middle or low quality, which bottlenecks model performance. (confidence: 1.00)
  Evidence: most rely on paired datasets with unstable label quality, which bottlenecks model performance. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/rqul-uie/summary.md

## Reactive Flux Matching: Mechanism Discovery and Adaptive Sampling of Rare Events

`reactive-flux-matching` | authors: Rishal Aggarwal, David Ryan Koes, Nicholas M. Boffi, Eric Vanden-Eijnden | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces Flux Matching, a framework that learns a current velocity and a scalar potential directly from reactive trajectory data. (confidence: 1.00)
  Evidence: We introduce Flux Matching, a framework that learns two complementary objects directly from reactive trajectory data: a current velocity $u(z)$, whose streamlines trace the dominant reaction pathways, and a scalar potential $h(z)$, obtained from a weighted Helmholtz-Hodge decomposition of the reactive current, that serves as a data-driven reaction coordinate. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/summary.md
- Flux Matching minimizes quadratic functionals over the reactive path ensemble, similar to the flow matching loss in generative modeling, without requiring knowledge of the underlying dynamics or stationary distribution. (confidence: 1.00)
  Evidence: Both minimize quadratic functionals over the reactive path ensemble, analogous to the flow matching loss in generative modeling, and require no knowledge of the underlying dynamics or stationary distribution. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/summary.md

### Dataset

- The Flux Matching framework is validated on the Müller-Brown potential under both overdamped and underdamped dynamics, as well as on alanine dipeptide molecular dynamics. (confidence: 1.00)
  Evidence: We validate the framework on the M"uller--Brown potential under both overdamped and underdamped dynamics, and on alanine dipeptide molecular dynamics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/source.tex

### Claim

- Unlike committor-based methods, the current velocity and scalar potential in Flux Matching remain well-defined when projected onto non-Markovian collective variables. (confidence: 1.00)
  Evidence: Unlike committor-based methods, $u$ and $h$ remain well-defined under projection onto non-Markovian collective variables, and their level sets in turn provide adaptive interfaces for improved sampling with enhanced sampling methods. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/summary.md
- The level sets of the scalar potential learned by Flux Matching can be used as adaptive interfaces or bins for path samplers, creating a loop where improved sampling and estimation reinforce each other. (confidence: 1.00)
  Evidence: The level sets of $h$ can in turn be used as adaptive interfaces or bins for path samplers themselves, closing a loop in which improved sampling and improved estimation reinforce each other. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/source.tex
- When the dynamics are Markovian, the Flux Matching framework recovers the objects from transition path theory (TPT). (confidence: 1.00)
  Evidence: In this appendix, we show that when the dynamics is Markovian, our framework recovers the objects from transition path theory (TPT). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reactive-flux-matching/source.tex

## Reason Twice: Segmentation via Candidate Discovery and Comparative Reasoning

`reason-twice` | authors: Xinyan Gao, Haoran Hao, Xiangyu Yue | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes a two-stage framework called Rea2Seg for mask generation and selection in reasoning-based image segmentation. (confidence: 1.00)
  Evidence: To better transfer MLLMs' perception and reasoning ability to complex reasoning-based segmentation tasks, we propose a two-stage framework Rea2Seg for mask generation and selection. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md
- Rea2Seg first identifies potential regions as candidate masks based on the attention maps of a segmentation MLLM, then employs an MLLM to reason over the question and candidate masks to assign scores, and finally selects the highest-scoring mask. (confidence: 1.00)
  Evidence: Specifically, the framework first identifies potential regions as candidate masks based on the attention maps of a segmentation MLLM. It then employs an MLLM to reason over the question and candidate masks and assign scores to each mask. The final segmentation result is obtained by reranking the candidates and selecting the highest-scoring mask [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md
- Rea2Seg reformulates image segmentation as candidate discovery followed by discriminative mask selection. (confidence: 1.00)
  Evidence: The final segmentation result is obtained by reranking the candidates and selecting the highest-scoring mask, reformulating image segmentation as candidate discovery followed by discriminative mask selection. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

### Dataset

- The authors collected training data to enhance MLLMs' ability to jointly understand multimodal queries and candidate masks, and to assign scores through reasoning. (confidence: 1.00)
  Evidence: In addition, we collect training data to enhance MLLMs' ability to jointly understand multimodal queries and candidate masks, and to assign scores through reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

### Benchmark

- The authors introduce a new benchmark called ReasonSeg-SGDR that evaluates a model's perception, grounding, and reasoning abilities across discriminative recognition, spatial reasoning, geometric reasoning, and multi-step reasoning with fine-grained mask generation. (confidence: 1.00)
  Evidence: To address this issue, we introduce a new benchmark called ReasonSeg-SGDR that comprehensively evaluates a model's perception, grounding, and reasoning abilities across multiple dimensions, including discriminative recognition, spatial reasoning, geometric reasoning, and multi-step reasoning, with fine-grained mask generation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

### Claim

- Experimental results on the ReasonSeg-SGDR and ReasonSeg benchmarks demonstrate the effectiveness of the unified mask generation and selection framework. (confidence: 1.00)
  Evidence: Experimental results on the proposed benchmark and ReasonSeg demonstrate the effectiveness of the unified mask generation and selection framework. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

### Limitation

- Existing MLLM-based segmentation methods are often constrained by limited training data and the gap between MLLMs and mask generation modules. (confidence: 1.00)
  Evidence: Despite promising progress, existing methods are often constrained by limited training data and the gap between MLLMs and mask generation modules. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md
- A large portion of questions in existing reasoning segmentation benchmarks focus on commonsense reasoning and do not fully require joint visual observation and reasoning. (confidence: 1.00)
  Evidence: We also notice that a large portion of questions in existing benchmarks focus on commonsense reasoning, and these questions usually do not fully require joint visual observation and reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reason-twice/summary.md

## Rethinking 3D Shape Generation: Diffusion over Superquadrics

`2606_08957` | authors: Zhiyang Liu, Wanze Li, Yuwei Wu, Chengran Yuan, Jiawei Sun, Rui Zheng, Marcelo H Ang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed method, Diffusion over Superquadrics, shifts the diffusion process from dense geometric representations to compact geometric primitives, representing each 3D shape as a small set of superquadrics. (confidence: 1.00)
  Evidence: We rethink the diffusion representation and propose to move diffusion from dense geometry to compact geometric primitives, representing each shape as a small set of superquadrics. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/summary.md
- The method reduces the diffusion-state dimensionality by leveraging 7KB of superquadric parameters, which include pose, size, and shape, instead of operating on thousands to millions of geometric representation values. (confidence: 1.00)
  Evidence: Instead of operating on thousands to millions of geometric representation values, we leverage 7KB superquadric parameters (pose, size, and shape), drastically reducing diffusion-state dimensionality and per-step compute/memory. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex

### Dataset

- ShapeNet is referenced as a standard benchmark where 2,048-point clouds are typically used for point-based 3D diffusion models. (confidence: 1.00)
  Evidence: Point-based models denoise thousands of continuous values per shape (e.g., 2{,}048-point clouds are standard in ShapeNet benchmarks) [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex

### Claim

- The proposed approach improves scalability by enabling capabilities such as resolution-free point-cloud decoding, part-level editing, and constraint-based design. (confidence: 1.00)
  Evidence: Our diffusion-over-superquadrics improves scalability by supporting broader capabilities (e.g., resolution-free point-cloud decoding, part-level editing, and constraint-based design) [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex
- The method achieves competitive surface-fidelity and distributional performance on standard benchmarks after decoding the superquadrics into point clouds. (confidence: 1.00)
  Evidence: and achieving competitive surface-fidelity and distributional performance on standard benchmarks after point-cloud decoding [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex
- The diffusion-over-superquadrics method enables efficient 3D shape generation, taking within 0.6 seconds per shape for most conditions. (confidence: 1.00)
  Evidence: while enabling efficient generation within 0.6s per shape for most conditions. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex

### Limitation

- Most existing 3D diffusion methods denoise in high-cardinality spaces like voxel/SDF grids, meshes, or point clouds, which is computationally and memory intensive and hinders scaling to higher resolutions and stronger controllability. (confidence: 1.00)
  Evidence: Diffusion models have advanced 3D shape generation, yet most methods still denoise in high-cardinality spaces (e.g., voxel/SDF grids, meshes, or point clouds), which is computationally and memory intensive and makes it difficult to scale in terms of both higher resolution and stronger controllability. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex
- Discretization-based 3D generation methods remain resolution-dependent, and latent diffusion methods often sacrifice explicit geometric interpretability and direct editability to achieve compactness. (confidence: 1.00)
  Evidence: discretization-based methods remain resolution-dependent, while latent diffusion often sacrifices explicit geometric interpretability and direct editability for compactness. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08957/source.tex

## Rethinking Embodied Navigation via Relational Inductive Bias

`2606_10348` | authors: Weitao An, Chenghao Xu, Xu Yang, Cheng Deng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes DB-Nav, an embodied navigation framework that dynamically reshapes the navigation search space through action-conditioned dual relational biases. (confidence: 1.00)
  Evidence: To address this issue, we propose DB-Nav, an embodied navigation framework that dynamically reshapes the navigation search space through action-conditioned dual relational biases. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex
- DB-Nav factorizes target-centric object relations into an Activation Bias for propagating positive search evidence and an Inhibition Bias for suppressing unreliable regions. (confidence: 1.00)
  Evidence: We factorize target-centric object relations into two synergistic biases: an Activation Bias, which propagates positive search evidence through contextual co-occurrence, and an Inhibition Bias, which suppresses unreliable regions by explicitly modeling perceptual confusion and action-level falsification. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex
- The dual biases in DB-Nav are unified into a Relational Activation-Inhibition Exploration Graph that modulates frontier exploration values using online observations and failed accesses. (confidence: 1.00)
  Evidence: These dual biases are unified into a Relational Activation--Inhibition Exploration Graph, which converts online visual observations and failed access events into semantic sources that dynamically modulate the exploration value of frontiers. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

### Dataset

- Object navigation has been extensively studied in environments including Habitat, Matterport3D, Gibson, AI2-THOR, RoboTHOR, and HM3D. (confidence: 1.00)
  Evidence: Object navigation has been extensively studied in Habitat, Matterport3D, Gibson, AI2-THOR, RoboTHOR, and HM3D [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

### Benchmark

- The proposed DB-Nav framework is evaluated on standard ObjectNav benchmarks. (confidence: 1.00)
  Evidence: Experiments on standard ObjectNav benchmarks demonstrate that DB-Nav significantly outperforms existing methods in both success rate (SR) and SPL. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

### Claim

- DB-Nav significantly outperforms existing methods in success rate (SR) and Success weighted by Path Length (SPL) without relying on costly online VLM reasoning. (confidence: 1.00)
  Evidence: Experiments on standard ObjectNav benchmarks demonstrate that DB-Nav significantly outperforms existing methods in both success rate (SR) and SPL. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

### Limitation

- Existing object navigation methods often overlook which semantic cues are unreliable, making them prone to systematic misleading evidence such as false positives, outdated static priors, and repeated failed exploration. (confidence: 1.00)
  Evidence: However, they often overlook an equally critical question: what not to trust, namely, which semantic cues are unreliable. Semantic cues produced by open-vocabulary perception are frequently subject to systematic misleading evidence: visual similarity can induce false positives, static priors are difficult to update once contradicted, and the lack of embodied verification may lead to repeated failed exploration [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10348/source.tex

## Revisiting Embodied Chain-of-Thought for Generalizable Robot Manipulation

`2606_03784` | authors: Nan Sun, Yuan Zhang, Yongkun Yang, Wentao Zhao, Peiyan Li, Jun Guo, Wenxuan Song, Pengxiang Ding, Runze Suo, Yifei Su, Xin Xiao, Xinghang Li, Huaping Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors propose ERVLA, a vision-language-action model that uses embodied chain-of-thought as representation-shaping supervision rather than mandatory test-time reasoning. (confidence: 1.00)
  Evidence: To address these limitations, we propose ERVLA, a VLA model that uses embodied CoT as representation-shaping supervision rather than mandatory test-time reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md
- ERVLA is trained with a reasoning-dropout strategy, allowing it to absorb reasoning traces during training while predicting actions directly without CoT decoding during inference. (confidence: 1.00)
  Evidence: ERVLA is trained with a reasoning-dropout strategy, enabling the model to absorb rich reasoning traces during training while predicting actions directly without CoT decoding during inference. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md
- ERVLA leverages a mixture-of-transformers architecture where a vision-language model processes visual observations and text instructions, and a diffusion transformer generates continuous robot actions via flow matching. (confidence: 1.00)
  Evidence: ERVLA leverages a mixture-of-transformers architecture~\cite{black2026pi0visionlanguageactionflowmodel,intelligence2025pi05visionlanguageactionmodelopenworld,tang2025mindhandpurposefulrobotic}, where a vision-language model~\cite{bai2025qwen3vltechnicalreport} processes visual observations and text instructions, and a diffusion transformer (DiT)~\cite{peebles2023scalablediffusionmodelstransformers} generates continuous robot actions via flow matching [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/source.tex

### Dataset

- The authors constructed the largest embodied CoT corpus to date, comprising 978,743 trajectories, 226.3M samples, and 2592.5 hours of robot data. (confidence: 1.00)
  Evidence: We construct the largest embodied CoT corpus to date, comprising 978,743 trajectories, 226.3M samples, and 2592.5 hours of robot data. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md

### Benchmark

- ERVLA achieves state-of-the-art performance on the LIBERO-Plus benchmark with an 86.9% success rate and reaches a 53.2% success rate on VLABench. (confidence: 1.00)
  Evidence: ERVLA achieves state-of-the-art performance on LIBERO-Plus with an 86.9% success rate and reaches 53.2% success rate on VLABench, demonstrating strong out-of-distribution generalization. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md

### Claim

- Effective embodied chain-of-thought should ground high-level semantic understanding into concrete action guidance, such as end-effector movement descriptions and image-space trajectories, because high-level reasoning alone brings only marginal gains. (confidence: 1.00)
  Evidence: Through extensive experiments, we find that effective embodied CoT should ground high-level semantic understanding into concrete action guidance, such as end-effector movement descriptions and image-space trajectories, while high-level reasoning alone brings only marginal gains. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md
- The authors identify a failure mode termed CoT contamination, where noisy labels in large-scale auto-labeled CoT annotations impose inconsistent supervision on semantically similar observations. (confidence: 1.00)
  Evidence: We identifies a critical yet overlooked failure mode that we term \textbf{CoT contamination}. Noisy labels are inevitable in large-scale auto-labeled CoT annotations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/source.tex

### Limitation

- Explicit chain-of-thought does not scale reliably when used as an autoregressive action prefix because it suffers from compounding inference errors and unstable reasoning-action coupling. (confidence: 1.00)
  Evidence: We further show that explicit CoT does not scale reliably when used as an autoregressive action prefix, as it suffers from compounding inference errors and unstable reasoning-action coupling. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03784/summary.md

## RoboSemanticBench: Diagnosing Semantic Grounding in Action Prediction for VLA Models

`robosemanticbench` | authors: Bin Yu, Yao Zhang, Haishan Liu, Shijie Lian, Yuliang Wei, Xiaopeng Lin, Zhaolong Shen, Changti Wu, Ruina Hu, Bailing Wang, Cong Huang, Kai Chen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/ZGC-EmbodyAI/RoboSemanticBench

### Method

- In RoboSemanticBench, a robot receives a multiple-choice math or general-knowledge question, observes candidate answer blocks, and must grasp the block corresponding to the correct answer. (confidence: 1.00)
  Evidence: In each episode, a robot receives a multiple-choice math or general-knowledge question, observes candidate answer blocks, and must grasp the block corresponding to the correct answer. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- The authors define GSR, TSR, and nSG metrics to separate low-level grasping from semantic target selection and diagnose whether instruction semantics participate in action prediction. (confidence: 1.00)
  Evidence: We define GSR, TSR, and nSG to separate low-level grasping from semantic target selection and diagnose whether instruction semantics participate in action prediction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- RSB-Math uses procedurally generated arithmetic questions including two-digit addition, two-digit subtraction, or one-digit by two-digit multiplication. (confidence: 1.00)
  Evidence: \textbf{(i) RSB-Math} uses procedurally generated arithmetic questions. Each question samples one of three controlled forms: two-digit addition, two-digit subtraction, or one-digit by two-digit multiplication. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- RoboSemanticBench is instantiated in a physics-based tabletop simulator with an Aloha-AgileX dual-arm embodiment, multi-view RGB cameras, wrist cameras, and robot proprioception. (confidence: 1.00)
  Evidence: We instantiate \benchshort{} in a physics-based tabletop simulator with an Aloha-AgileX dual-arm embodiment, multi-view RGB cameras, wrist cameras, robot proprioception. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- Vision-language-action (VLA) models are often described as dual-system architectures with a low-frequency System-2 Semantic Expert and a high-frequency System-1 Action Expert. (confidence: 1.00)
  Evidence: Representative systems, including $\pi_0$, are often described as dual-system architectures with a low-frequency System-2 \emph{Semantic Expert} and a high-frequency System-1 \emph{Action Expert}~\cite{OpenVLA_24,PI0,ChatVLA_25}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex

### Dataset

- RSB covers controlled arithmetic, grade-school mathematical understanding, and commonsense or factual understanding under four-choice and ten-choice suites. (confidence: 1.00)
  Evidence: RSB covers controlled arithmetic, grade-school mathematical understanding, and commonsense or factual understanding under four-choice and ten-choice suites. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- RSB-HardMath uses grade-school word problems derived from GSM8K to test if a VLA policy can follow multi-sentence compositional problem semantics. (confidence: 1.00)
  Evidence: \textbf{(ii) RSB-HardMath} uses grade-school word problems derived from GSM8K \cite{GSM8K_21}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- RSB-General covers non-mathematical semantic understanding, including commonsense QA and MMLU-derived multiple-choice questions. (confidence: 1.00)
  Evidence: \textbf{(iii) RSB-General} covers non-mathematical semantic understanding, including commonsense QA about everyday tools, locations, household functions, and MMLU-derived multiple-choice questions \cite{MMLU_21}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex

### Benchmark

- RoboSemanticBench (RSB) is an embodied benchmark designed to diagnose semantic grounding in action prediction for vision-language-action (VLA) models. (confidence: 1.00)
  Evidence: We introduce RoboSemanticBench (RSB), an embodied benchmark for diagnosing semantic grounding in action prediction: whether post-trained VLA models can use complex instruction semantics to select and manipulate the correct physical target. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/summary.md

### Claim

- Many VLA policies learn to grasp candidate blocks but select the semantically correct block at near-random or below-random rates after controlling for grasp success. (confidence: 1.00)
  Evidence: Across representative VLA models, we find that many policies learn to grasp candidate blocks but select the semantically correct block at near-random or below-random rates after controlling for grasp success, revealing a persistent gap between backbone-level semantic competence and action prediction. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- Robot fine-tuning for VLA models is optimized as imitation over task-specific action distributions, which can lead to learning visual or instruction-action shortcuts rather than using language semantics. (confidence: 1.00)
  Evidence: Yet robot fine-tuning is optimized as imitation over task-specific action distributions, and many evaluations can be solved through visual or instruction-action shortcuts. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex
- CoT-style ReasoningVLA and VLA cotraining do not reliably close the semantic grounding gap in VLA models. (confidence: 1.00)
  Evidence: We report negative interventions and error analyses, showing that CoT-style ReasoningVLA and VLA cotraining do not reliably close the semantic grounding gap. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/robosemanticbench/source.tex

## Robotic Policy Adaptation via Weight-Space Meta-Learning

`2606_07217` | authors: Christian Bianchi, Siamak Yousefi, Alessio Sampieri, Andrea Roberti, Luca Rigazio, Fabio Galasso, Luca Franco | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- WIZARD is a weight-space meta-learning framework that generates task-specific LoRA parameters for a frozen Vision-Language-Action (VLA) policy, avoiding the need for task-specific fine-tuning. (confidence: 1.00)
  Evidence: We propose WIZARD, a weight-space meta-learning framework that sidesteps task-specific fine-tuning by generating task-specific LoRA parameters for a frozen VLA policy. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md
- WIZARD predicts adaptation weights in a single forward pass using only a language instruction and a short demonstration video, without requiring target-task action labels or test-time optimization. (confidence: 1.00)
  Evidence: Given only a language instruction and a short demonstration video, WIZARD predicts the corresponding adaptation weights in a single forward pass, without target-task action labels or test-time optimization. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md
- During the meta-training phase, WIZARD learns to map task evidence directly to expert LoRA updates, which allows it to capture relationships between different tasks in weight space. (confidence: 1.00)
  Evidence: During meta-training, WIZARD learns to map task evidence directly to expert LoRA updates, capturing relationships between tasks in weight space. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md

### Benchmark

- The LIBERO benchmark is used to evaluate the performance and generalization capabilities of the WIZARD framework. (confidence: 1.00)
  Evidence: Experiments on LIBERO show that WIZARD improves performance by up to ~2x on unseen dataset collections and up to ~14x on unseen tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md

### Claim

- WIZARD improves performance by up to ~2x on unseen dataset collections and up to ~14x on unseen tasks when evaluated on the LIBERO benchmark. (confidence: 1.00)
  Evidence: Experiments on LIBERO show that WIZARD improves performance by up to ~2x on unseen dataset collections and up to ~14x on unseen tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md
- When deployed on a real Franka Emika Panda robot, WIZARD consistently outperforms a real-domain adapted baseline, demonstrating that the generated adapters provide task-level specialization that extends beyond simulation. (confidence: 1.00)
  Evidence: On a Franka Emika Panda, WIZARD consistently improves over a real-domain adapted baseline, showing that generated adapters provide task-level specialization beyond simulation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07217/summary.md

## S23DR 2026 Winning Solution

`2606_06695` | authors: Jan Skvrna, Miroslav Purkrabek, Lukas Neumann | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The method treats vertices as a conditional set and denoises 64 vertex tokens using a flow-matching DiT conditioned on Perceiver-style scene tokens. (confidence: 1.00)
  Evidence: The method treats vertices as a conditional set and denoises 64 vertex tokens with a flow-matching DiT conditioned on Perceiver-style scene tokens. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/summary.md
- The prediction pipeline consists of a global pass to predict coarse structure and a hull-cropped second pass to refine it. (confidence: 1.00)
  Evidence: A global pass predicts the coarse structure, a hull-cropped second pass refines it, and a small multi-sample consensus step keeps the stochastic sampler well behaved. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/summary.md
- The scene encoder lifts heterogeneous per-point features to 320-D tokens, contextualizes them at full resolution, and pools them into a fixed bank of 1024 scene tokens. (confidence: 1.00)
  Evidence: Heterogeneous per-point features are lifted to
320-D tokens, contextualized at full resolution, and pooled into a fixed bank of
1024 scene tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex
- The system runs 16 stochastic trajectories and uses a multi-sample consensus ensemble to select and refine the final graph, reducing run-to-run variance. (confidence: 1.00)
  Evidence: The submitted system runs 16 stochastic trajectories, with randomness coming
from slot initialization. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex
- The training objective is a weighted sum of SmoothL1 velocity loss, SmoothL1 endpoint loss, focal validity loss, and pairwise BCE edge loss. (confidence: 1.00)
  Evidence: The objective is a weighted sum of SmoothL1
velocity loss, SmoothL1 endpoint loss, focal validity loss for real/null slots,
and pairwise BCE edge loss: [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex

### Dataset

- The challenge is built on the HoHo dataset, which provides approximately 22,000 training and 200 validation scenes of distinct residential buildings. (confidence: 1.00)
  Evidence: The challenge is built on the HoHo dataset; the public
release
(\texttt{hoho22k\_2026\_trainval}) provides $\approx\!22{,}000$ training and
$\approx\!200$ validation scenes, each a distinct residential building. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex
- The input data for each scene includes a sparse 3D point cloud, per-view metric depth maps, and per-view semantic segmentations, without any RGB images. (confidence: 1.00)
  Evidence: the only inputs are a sparse,
noisy COLMAP point cloud~\cite{schonberger2016sfm}, scale-fitted depth maps, and projected 2D
segmentations~\cite{zhou2017ade20k}, without any RGB images [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex

### Benchmark

- The S23DR 2026 challenge focuses on structured 3D wireframe reconstruction from sparse SfM, fitted depth, and semantic segmentations. (confidence: 1.00)
  Evidence: This text presents the winning solution to the S23DR 2026 challenge for structured 3D wireframe reconstruction from sparse SfM, fitted depth, and semantic segmentations. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/summary.md

### Claim

- The proposed system ranked first on the S23DR 2026 private test leaderboard with a Hybrid Structure Score (HSS) of 0.654. (confidence: 1.00)
  Evidence: This approach ranked \textbf{first} on the S23DR~2026
private test leaderboard with an HSS of \textbf{0.654} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex

### Limitation

- A significant portion of the views lack depth maps, with approximately 42% of training and 69% of validation views being pose-only. (confidence: 1.00)
  Evidence: Depth is also frequently
absent (i.e., $\approx\!42\%$ of training and $\approx\!69\%$ of validation
views are pose-only with no depth map). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06695/source.tex

## SARM2: Multi-Task Stage Aware Reward Modeling for Self Improving Robotic Manipulation

`sarm2` | authors: Qianzhong Chen, Hau Zheng, Justin Yu, Suning Huang, Jiankai Sun, Ken Goldberg, Chuan Wen, Pieter Abbeel, Yide Shentu, Philipp Wu, Mac Schwager | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- SARM2 (referred to as RM) is a multi-task stage-aware reward model that combines an action-primitive-based stage estimator with a multi-gate Mixture-of-Experts (MMoE) value head to produce dense per-step rewards. (confidence: 1.00)
  Evidence: We introduce RM, a multi-task stage-aware reward model that combines an action-primitive-based stage estimator with a multi-gate Mixture-of-Experts (MMoE) value head to produce dense per-step rewards across manipulation tasks. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md
- SPIRAL (Self-Policy Improvement via Reward-Aligned Learning) is an on-policy reward-guided framework designed to improve VLA policies using cheap autonomous rollouts and dense rewards from the proposed reward model. (confidence: 1.00)
  Evidence: Building on RM, we further propose SPIRAL (Self-Policy Improvement via Reward-Aligned Learning), an on-policy reward-guided framework that improves VLA policies from cheap autonomous rollouts. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md
- The action-primitive stage estimator frames stage estimation as a temporal classification task over 22 classes (21 primitives plus a null class) using a 4-layer causal Transformer that processes tokens from three camera views and proprioceptive state. (confidence: 1.00)
  Evidence: We frame stage estimation as temporal classification over the primitive vocabulary plus a null class (K + 1 = 22 classes). ... All tokens are processed by a 4-layer causal Transformer f_\theta followed by a linear head g_\theta producing class logits [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/source.tex

### Dataset

- The authors constructed a balanced action primitive dataset of 66 hours of segments, derived from 200 hours of real-world manipulation data across 100 tasks, covering 21 action primitives and a null class. (confidence: 1.00)
  Evidence: We curated 200 hours of real-world manipulation data spanning 100 tasks. After consolidation we identified K = 21 action primitives that cover >90% of total task duration. We partitioned the source dataset along annotation boundaries and constructed a balanced dataset D_AP with (i) each primitive contributing t_k = 3 hours, and (ii) maximum source-task diversity per primitive, yielding (K + 1) * t_k = 66 hours of segments. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/source.tex

### Claim

- On a 10-task benchmark, the proposed reward model reduces value-estimation Mean Squared Error (MSE) by 80% compared to the strongest baselines. (confidence: 1.00)
  Evidence: On a 10-task benchmark, RM reduces value-estimation MSE by 80% over the strongest baselines [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md
- When integrated into the SPIRAL framework, the proposed method improves task success on the Folding Shorts task from 58% to 100%. (confidence: 1.00)
  Evidence: when used in SPIRAL, it improves task success from around 50% to near-perfect performance on Folding Shorts (58% to 100%) [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md
- When integrated into the SPIRAL framework, the proposed method improves task success on the Cleaning Whiteboard task from 50% to 90%. (confidence: 1.00)
  Evidence: and Cleaning Whiteboard (50% to 90%), showing that high-quality dense rewards are key to a stable robot data flywheel. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/summary.md

### Limitation

- Existing task-specific stage-aware reward models require per-task annotations, while general vision-language-model (VLM) reward models are too coarse for fine-grained long-horizon progress. (confidence: 1.00)
  Evidence: Existing methods fall short: task-specific stage-aware models are accurate but require per-task annotations, while general vision-language-model (VLM) reward models are broadly applicable but too coarse for fine-grained long-horizon progress. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sarm2/source.tex

## SCOPE: Simulating Cross-game Operations in Playable Environments for FPS World Models

`scope` | authors: Zizhao Tong, Yeying Jin, Hongfeng Lai, Zeqing Wang, Zhaohu Xing, Kexu Cheng, Haoran Xu, Zhao Pu, Shangwen Zhu, Ruili Feng, Jian Zhao, Yan Zhang, Hao Tang, Ling Shao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/z2tong/SCOPE

### Method

- SCOPE inserts a conditioning module into each transformer block of a pretrained video diffusion model to reshape features into per-pixel temporal sequences. (confidence: 1.00)
  Evidence: We propose SCOPE, which inserts a conditioning module into each transformer block of a pretrained video diffusion model. It reshapes features into per-pixel temporal sequences so that each position computes its action response from local visual content. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/summary.md
- The action telemetry in CrossFPS consists of 10 dimensions organized into four functional groups: Movement, Camera, Combat, and Utility. (confidence: 1.00)
  Evidence: Each clip is paired with per-frame 10-dimensional controller telemetry organized into four functional groups (Table~\ref{tab:action_format}): Movement (4 continuous axes from the left analog stick), Camera (2 continuous axes from the right analog stick), Combat (3 discrete buttons), and Utility (3 discrete buttons). [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex
- To eliminate human bias, the data processing pipeline explicitly retains inefficient or counter-intuitive actions by identifying clips with the lowest mutual information between visual features and discrete action sequences. (confidence: 1.00)
  Evidence: To force the model to learn raw physics rather than strategic priors, we explicitly retain "inefficient" or counter-intuitive actions (e.g., firing at an empty sky, sprinting into walls). We identify these clips by computing the mutual information between the visual features from a pre-trained scene classifier and the discrete action sequences. [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex
- Cross-game kinetic normalization uses optical flow-based gain calibration to resolve gradient conflicts caused by different game engines mapping analog stick displacements to different camera rotation speeds. (confidence: 1.00)
  Evidence: To resolve the resulting gradient conflicts during multi-game joint training, we apply optical flow-based gain calibration. For each clip, we extract the mean pixel displacement $(\Delta u, \Delta v)$ caused by camera rotation and fit a linear gain model [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex
- Text conditioning during training is provided by generating scene descriptions for the first frame of every clip using Gemini, following a standardized two-sentence format. (confidence: 1.00)
  Evidence: To provide text conditioning during training, we generate scene descriptions for the first frame of every clip using Gemini~\citep{team2023gemini}. Each caption follows a standardized two-sentence format: [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex

### Dataset

- CrossFPS is a multi-game FPS dataset comprising 69,000 five-second clips across seven titles at 20 fps with 10-DoF controller signals. (confidence: 1.00)
  Evidence: CrossFPS comprises 69,000 five-second clips across seven FPS titles at 20 fps ($480{\times}832$) [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex
- CrossFPS data is sourced from the NitroGen and WorldCam public repositories, covering games like Halo, Call of Duty, and Xonotic. (confidence: 1.00)
  Evidence: sourced from two public repositories: NitroGen~\citep{magne2026nitrogen}, which provides gameplay recordings with frame-aligned controller telemetry for the Halo and Call of Duty series, and WorldCam~\citep{nam2026worldcam}, which contributes Xonotic recordings. [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex

### Claim

- SCOPE learns general visual-to-action mappings rather than game-specific patterns, enabling zero-shot transfer to unseen scenes. (confidence: 1.00)
  Evidence: The model learns general visual-to-action mappings rather than game-specific patterns, enabling zero-shot transfer to unseen scenes. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex
- The action entropy of the CrossFPS dataset approaches the theoretical maximum for the discretized 10-dimensional action space, confirming training without human bias. (confidence: 1.00)
  Evidence: The action entropy of $2.94 \pm 0.31$ bits approaches the theoretical maximum for the discretized 10-dimensional action space, substantially exceeding typical human gameplay entropy. This confirms training without human bias [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex

### Limitation

- Optical flow fails in static or highly occluded scenes, requiring a 95th-percentile fallback normalization for cross-game kinetic normalization. (confidence: 0.90)
  Evidence: For static or highly occluded scenes where optical flow fails, we apply a 95th-percentile fallback normalization. [appendix] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/scope/source.tex

## SIMPLE: Simulation-Based Policy Learning and Evaluation for Humanoid Loco-manipulation

`simple` | authors: Songlin Wei, Zhenhao Ni, Jie Liu, Zhenyu Zhao, Junjie Ye, Hongyi Jing, Junkai Xia, Xiawei Liu, Michael Leong, Liang Heng, Di Huang, Yue Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- SIMPLE combines the contact-rich physics engine MuJoCo with the photorealistic rendering engine IsaacSim to create a hybrid simulation framework. (confidence: 1.00)
  Evidence: SIMPLE couples the accurate contact-rich dynamics of MuJoCo with the photorealistic rendering of IsaacSim. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/summary.md
- The SIMPLE framework includes two data generation pipelines for scalable data collection: automated trajectory generation using motion planning and a low-latency VR teleoperation interface. (confidence: 1.00)
  Evidence: To facilitate scalable data collection, the framework integrates two data generation pipelines: automated trajectory generation via motion planning and a low-latency VR teleoperation interface. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex

### Dataset

- The SIMPLE environment consists of 60 diverse whole-body loco-manipulation tasks, 50 indoor scenes, and over 1,000 object assets. (confidence: 1.00)
  Evidence: It provides a large-scale environment comprising 60 diverse whole-body tasks, 50 indoor scenes, and over 1,000 object assets. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex
- The dataset curated for SIMPLE includes over 1,000 Objaverse assets and 50 HSSD scenes. (confidence: 1.00)
  Evidence: we curate over 1,000 Objaverse assets \cite{deitke2023objaverse} and 50 HSSD scenes \cite{khanna2024habitat}, and design 60 diverse whole-body loco-manipulation tasks [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex

### Benchmark

- SIMPLE benchmarks mainstream humanoid policies at scale, including lightweight imitation networks, vision-language-action (VLA) models, and world action models (WAMs). (confidence: 1.00)
  Evidence: We further integrate and benchmark mainstream humanoid policies at scale in SIMPLE, including lightweight imitation networks, large vision-language-action (VLA) models, and recent world action models (WAMs). [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/summary.md

### Claim

- There is a strong correlation between the performance of policies evaluated in the SIMPLE simulation and their performance in the real world. (confidence: 1.00)
  Evidence: Our experiments reveal a strong correlation between policy performance in simulation and the real world. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex
- Policies trained on data collected within the SIMPLE simulator can be transferred to physical humanoid robots in a zero-shot manner under similar settings. (confidence: 1.00)
  Evidence: Furthermore, we demonstrate that policies trained on data collected in SIMPLE can be transferred zero-shot to physical humanoid robots under similar settings [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/summary.md

### Limitation

- Existing simulation benchmarks primarily focus on table-top or wheeled robots, leaving a gap for scalable and reproducible benchmarks for whole-body humanoid loco-manipulation. (confidence: 1.00)
  Evidence: existing simulation benchmarks focus primarily on table-top or wheeled robots. A scalable and reproducible benchmark for whole-body humanoid loco-manipulation remains an open problem. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex
- Real-world testing for humanoid foundation models is expensive and difficult to reproduce. (confidence: 1.00)
  Evidence: While real-world testing is expensive and difficult to reproduce [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex
- Simulation platforms like IsaacSim and IsaacLab rely on the PhysX engine, which suffers from suboptimal contact fidelity and poor portability for state-of-the-art locomotion policies. (confidence: 1.00)
  Evidence: IsaacSim \cite{NVIDIA_Isaac_Sim} and IsaacLab \cite{mittal2025isaaclab} are capable of full-stack, whole-body loco-manipulation platforms. However, it is built on PhysX, which has suboptimal contact fidelity and poor portability for state-of-the-art locomotion policies. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/simple/source.tex

## SS-TPT: Stability and Suitability-Guided Test-Time Prompt Tuning for Adversarially Robust Vision-Language Models

`ss-tpt` | authors: Sunoh Kim, Daeho Um | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/MaxZanella/MTA, https://github.com/Sxing2/CLIP-Test-time-Counterattacks, https://github.com/TomSheng21/R-TPT, https://github.com/azshue/TPT, https://github.com/bookman233/DOC, https://github.com/sunoh-kim/SS-TPT, https://github.com/xinwong/TAPT

### Method

- The paper introduces SS-TPT (Stability and Suitability-guided Test-time Prompt Tuning), which evaluates the quality of augmented views using stability and suitability scores to guide test-time adaptation and inference. (confidence: 1.00)
  Evidence: we present Stability and Suitability-guided Test-time Prompt Tuning (SS-TPT), evaluating the quality of each augmented view via two complementary scores: (1) stability, measuring prediction invariance to weak augmentations, and (2) suitability, measuring feature-space density among views. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex
- The stability score in SS-TPT is defined as the invariance of a view's predictive distribution when the view is perturbed by weak stochastic augmentations. (confidence: 1.00)
  Evidence: stability is defined as the invariance of a view's predictive distribution when the view is perturbed by weak stochastic augmentations [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex
- The suitability score in SS-TPT is defined as the density of a view's surrounding views in the feature space. (confidence: 1.00)
  Evidence: suitability is defined as the density of a view's surrounding views in the feature space. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex
- SS-TPT employs an SS-guided consistency loss during adaptation to align predictions with trustworthy references, and an SS-weighted prediction during inference to aggregate per-view predictions while suppressing corrupted ones. (confidence: 1.00)
  Evidence: SS-TPT (i) applies an SS-guided consistency loss during adaptation to align predictions with trustworthy references, and (ii) performs an SS-weighted prediction during inference to aggregate per-view predictions into the final output that emphasizes trustworthy views while suppressing corrupted ones. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex

### Dataset

- The paper evaluates the robustness-throughput trade-off across test-time defenses averaged over 10 fine-grained classification datasets. (confidence: 1.00)
  Evidence: Robustness-throughput trade-off across test-time defenses, averaged over 10 fine-grained classification datasets. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex
- The paper compares per-image test time and adversarial robustness on the Caltech101 dataset across CLIP, R-TPT, and SS-TPT. (confidence: 1.00)
  Evidence: Comparison of per-image test time and adversarial robustness on the Caltech101 dataset across CLIP, R-TPT with different numbers of augmented views (63 and 15 views), and our method with 15 views. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex

### Claim

- SS-TPT significantly outperforms prior state-of-the-art methods by achieving superior robustness-throughput trade-offs across diverse datasets and varying numbers of views. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that SS-TPT significantly outperforms prior state-of-the-art methods, achieving superior robustness-throughput trade-offs across diverse datasets and varying numbers of views [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/summary.md
- SS-TPT maintains high adversarial robustness even in an extremely low visual diversity regime with only one augmented view. (confidence: 1.00)
  Evidence: Remarkably, even under the extremely low visual diversity regime (one augmented view), SS-TPT maintains high robustness, underscoring its critical role in extracting meaningful information from limited visual evidence. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex
- Reducing the number of augmented views in existing methods like R-TPT speeds up inference but significantly lowers robustness, revealing a clear efficiency-robustness trade-off. (confidence: 1.00)
  Evidence: reducing R-TPT from 63 to 15 views speeds up inference but lowers robustness by over 10%, revealing a clear efficiency-robustness trade-off. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/ss-tpt/source.tex

## STEDiff: Strengthening Text Embedding for Text-to-Image Alignment in Diffusion Model

`stediff` | authors: Hailan Zhang, Haipeng Liu, Bo Fu, Yang Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- STEDiff is a training-free method designed to enhance semantic representations directly within the text-embedding space. (confidence: 1.00)
  Evidence: we propose STEDiff, a training-free method designed to enhance semantic representations directly within the text-embedding space. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/summary.md
- STEDiff leverages the [EOT] token to strengthen the relevant semantics of sub-sentences and replaces the corresponding tokens in the original prompt. (confidence: 1.00)
  Evidence: Specifically, we introduce a method that primarily leverages the [EOT] token to strengthen the relevant semantics of sub-sentences and then replaces the corresponding tokens in the original prompt. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/summary.md
- STEDiff optimizes text embeddings at inference-time using a semantic enhancement loss to strengthen object associations and an entropy loss to encourage tokens to attend to their corresponding regions. (confidence: 1.00)
  Evidence: we optimize the text embeddings at inference-time using a semantic enhancement loss and an entropy loss. The semantic enhancement loss strengthens the associations between objects and their sub-objects... The entropy loss encourages each prompt token to attend to its corresponding region [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/source.tex
- STEDiff splits complex prompts by different entity-nouns to obtain sub-sentences, strengthens their semantics separately, and performs replacements to avoid semantic leakage. (confidence: 1.00)
  Evidence: it first split the complex prompts by different entity-nouns, such as \textit{man} and \textit{woman}, thereby obtaining the sub-sentences... then strength the semantics of the sub-sentence separately, finally perform the replacements from the initial complex prompts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/source.tex

### Benchmark

- STEDiff is evaluated using the T2I-CompBench benchmark. (confidence: 1.00)
  Evidence: Extensive quantitative and qualitative evaluations on the T2I-CompBench demonstrate that our method notably improves semantic consistency and generation integrity in complex scenarios. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/summary.md

### Claim

- STEDiff outperforms baseline methods, particularly in scenarios involving multi-object and multi-attribute generation. (confidence: 1.00)
  Evidence: Through a comparative evaluation across various baselines, datasets, and metrics, it is clear that \textit{STEDiff} outperforms the others, particularly in scenarios involving multi-object and multi-attribute generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/source.tex
- In the CLIP text encoder, tokens with higher indices, culminating in the [EOT] symbol, accumulate the most comprehensive contextual information. (confidence: 1.00)
  Evidence: tokens with higher indices—culminating in the [EOT] symbol—accumulate the most comprehensive contextual information. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/source.tex

### Limitation

- Existing approaches for improving text-to-image alignment often rely on computationally expensive fine-tuning or labor-intensive layout priors. (confidence: 1.00)
  Evidence: Unlike existing approaches that rely on computationally expensive fine-tuning or labor-intensive layout priors, we propose STEDiff [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/summary.md
- Some existing text-to-image alignment methods sacrifice the diversity of generated images or perform simple token summation which leads to low coherence. (confidence: 1.00)
  Evidence: \cite{xie2023boxdiff} sacrifices the diversity of generated images, and \cite{hu2024token} performs simple token summation, which leads to low coherence in the images. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stediff/source.tex

## STREAM: Stochastic Riemannian Flow Matching with Anisotropic Decoder for Digital Histopathology Image Generation

`stream` | authors: Won June Cho, Daeky Jeong, Hyeongyeol Lim, Hongjun Yoon | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- STREAM is a framework that applies Riemannian flow matching in the pathology domain, consisting of a bridge-type stochastic perturbation and an anisotropic decoder. (confidence: 1.00)
  Evidence: We therefore present STREAM, the first framework to apply Riemannian flow matching in the pathology domain. STREAM consists of two stages: 1) a bridge-type stochastic perturbation that establishes per-token rectifiability on $\mathcal{S}^{d-1}$ for training a Diffusion Transformer (DiT) in latent space, and 2) a novel anisotropic decoder that allocates robustness to low-energy directions of the velocity-field Jacobian while preserving fidelity along its high-energy directions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/summary.md
- STREAM uses pretrained histopathology Vision Foundation Models as the latent space itself, leveraging their patch-token features that are l2-normalized and lie on the unit hypersphere. (confidence: 1.00)
  Evidence: Therefore, we instead use pretrained histopathology VFMs as the latent space itself, leveraging their patch-token features that encode rich semantic information. We empirically show that these features are $\ell_2$-normalized and lie on the unit hypersphere $\mathcal{S}^{d-1}$ with strong angular dominance and intrinsic curvature, making them naturally suited for a Riemannian formulation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/summary.md
- The anisotropic decoder's noise covariance is shaped by the singular value decomposition of the trained DiT's velocity-field Jacobian, applying small noise along high-energy directions and large noise along low-energy directions. (confidence: 1.00)
  Evidence: a novel decoder design whose noise covariance is shaped by the singular value decomposition (SVD) of the trained DiT's velocity-field Jacobian --- small noise along high-energy directions (those to which the velocity field is most sensitive) to preserve reconstruction fidelity, large noise along low-energy directions to absorb the residual drift the generator may exhibit at inference. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex

### Dataset

- STREAM achieves state-of-the-art reconstruction and generation performance on breast and colorectal cancer datasets. (confidence: 1.00)
  Evidence: Together, STREAM achieves state-of-the-art reconstruction and generation performance on breast and colorectal cancer datasets. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/summary.md
- The study analyzes the intrinsic geometry of histopathology VFM features using the TCGA-BRCA dataset. (confidence: 1.00)
  Evidence: we analyze the intrinsic geometry of histopathology VFM features on TCGA-BRCA for UNI ($d{=}1024$) and UNI2-h ($d{=}1536$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex
- The study utilizes the SPIDER-breast dataset to evaluate where semantic information resides in VFM features via angular and radial perturbation. (confidence: 1.00)
  Evidence: We next ask \emph{where} in VFM features the semantic information resides via 1-NN angular vs.\ radial perturbation on SPIDER-breast [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex

### Claim

- Existing state-of-the-art generative models in histopathology that use pretrained Vision Foundation Models as conditioning signals suffer from conditioning collapse, where the conditioning signal dominates the latent space and lowers the quality and diversity of generated samples. (confidence: 1.00)
  Evidence: Existing state-of-the-art generative models in histopathology use pretrained Vision Foundation Models (VFMs) as conditioning signals, and we observe that this leads to "conditioning collapse," where the conditioning signal dominates the latent space and lowers the quality and diversity of generated samples. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/summary.md
- Latents generated via Variational Autoencoders primarily emphasize low-level details and lack semantic content, leading to substantially lower performance on downstream tasks compared to representation-encoder features. (confidence: 1.00)
  Evidence: The underlying observation across these works is that latents generated via Variational Autoencoders (VAEs) primarily emphasize low-level details, with linear classifiers on VAE features substantially underperforming those on representation-encoder features. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex
- Class-discriminative information in Vision Foundation Model features resides in the angular structure of the unit hypersphere, with angular perturbation accuracy exceeding 0.97 for pathology VFMs. (confidence: 1.00)
  Evidence: For both pathology VFMs (UNI, UNI2-h) and the natural-image-domain DINOv3-L, $f_\text{angular} > 0.97$: class-discriminative information lives in the angular structure of $\cS^{d-1}$, directly motivating RFM. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex
- Histopathology VFM features exhibit substantial intrinsic curvature, with tangent drift exceeding 0.72 at hop 1, which rules out Euclidean flow matching and justifies Riemannian flow matching on the hypersphere. (confidence: 1.00)
  Evidence: tangent drift exceeds $0.72$ at hop~1 ... direct evidence of manifold curvature. Hop-1 drift this large rules out Euclidean flow matching; combined with $\ell_2$-normalization onto $\cS^{d-1}$, this justifies RFM on the hypersphere. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex

### Limitation

- Direct numerical comparison with prior Riemannian flow matching works for image generation was not possible because neither Geometry-Aware Image FM nor DINO-SAE has been open-sourced. (confidence: 1.00)
  Evidence: Direct numerical comparison with these prior works was not possible as neither has been open-sourced. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/stream/source.tex

## SafeVLA-Bench: A Benchmark for the Success-Safety Gap in Vision-Language-Action Models

`safevla-bench` | authors: Jialiang Fan, Weizhe Xu, Oleg Sokolsky, Insup Lee, Fanxin Kong | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The framework formalizes task-aware safety requirements using Signal Temporal Logic (STL) specifications. (confidence: 1.00)
  Evidence: It formalizes task-aware safety requirements as Signal Temporal Logic (STL) specifications [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md
- SafeVLA-Bench evaluates safety using two unsafe-success metrics: Succ-But-Unsafe (SBU), which measures the fraction of successful rollouts that violate safety, and Violation Severity Index (VSI), a bounded worst-violation depth score. (confidence: 1.00)
  Evidence: and reports native success with two unsafe-success metrics: Succ-But-Unsafe (SBU), the fraction of rollouts that both succeed and violate safety, and Violation Severity Index (VSI), a bounded worst-violation depth score. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md
- To integrate a new host benchmark into SafeVLA-Bench, developers only need to provide an offline adapter that outputs a trajectory record, a task-tag record, and a spec-registry record, rather than reimplementing the metric suite. (confidence: 1.00)
  Evidence: A new benchmark does not need to reimplement the metric suite; it needs an offline adapter that emits a trajectory record, a task-tag record, and a small spec-registry record in the form below. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/source.tex
- A safety specification is activated for a specific task only if all its required tags are present and none of its invalidating tags are present. (confidence: 1.00)
  Evidence: A specification is active iff all of its required tags are present and none of its invalidating tags are present. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/source.tex

### Dataset

- The SafeVLA-Bench framework is instantiated and evaluated on the LIBERO and RoboCasa-365 benchmarks, covering tabletop and kitchen manipulation tasks. (confidence: 1.00)
  Evidence: We instantiate SafeVLA-Bench on LIBERO and RoboCasa-365, evaluating nine policy-benchmark entries across tabletop and kitchen manipulation tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md
- The Auxiliary RoboCasa 5-task PnP dataset is a narrower subset with a different task-sampling protocol than RoboCasa-365 atomic-seen, and its results are excluded from the main benchmark aggregates. (confidence: 1.00)
  Evidence: This narrower subset uses a different task-sampling protocol from RoboCasa-365 atomic-seen and is excluded from the main benchmark aggregate, Pareto plot, and threshold-sensitivity means. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/source.tex

### Benchmark

- SafeVLA-Bench is introduced as a post-hoc safety-evaluation framework designed for existing simulator-based Vision-Language-Action (VLA) benchmarks. (confidence: 1.00)
  Evidence: We present SafeVLA-Bench, a post-hoc safety-evaluation framework for existing simulator-based VLA benchmarks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md

### Claim

- Binary success metrics in VLA benchmarks can obscure safety-relevant trajectory behaviors such as excessive contact, disturbing bystander objects, destabilizing held objects, or robot self-contact. (confidence: 1.00)
  Evidence: Vision-language-action (VLA) benchmarks measure whether a policy completes a requested manipulation task, but binary success can hide safety-relevant trajectory behavior: reaching the goal while applying excessive contact, disturbing bystander objects, destabilizing the held object, or entering robot self-contact. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md
- High task success rates in VLA models do not guarantee safe execution, as evidenced by high-success tabletop baselines still exhibiting 13 to 15 percent unsafe-episode rates. (confidence: 1.00)
  Evidence: High task success does not imply safe execution: high-SR tabletop baselines still leave 13 to 15 percent unsafe-episode rates [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md
- In the RoboCasa-365 benchmark, 36 to 56 percent of successful rollouts were found to violate at least one active safety clause. (confidence: 1.00)
  Evidence: and 36 to 56 percent of successful RoboCasa-365 rollouts violate at least one active safety clause. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/safevla-bench/summary.md

## Same Weights, Different Robot: A Deployment Safety View of VLA Policies

`2606_03724` | authors: Jianwei Tai | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors formalize the deployment-safety gap as an executable policy specification problem, defining a VLA policy to include the learned model, action representation, metadata-selected unnormalizer, and controller-facing conventions. (confidence: 1.00)
  Evidence: We formalize this gap as an executable policy specification problem: a VLA policy includes the learned model, action representation, metadata-selected unnormalizer, and controller-facing conventions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex
- For quantile-style action normalization, the authors derive a closed-form metadata mismatch transform and an ExecSpec certificate to measure action-space semantic drift without requiring model inference or rollout. (confidence: 1.00)
  Evidence: For quantile-style action normalization, we derive a closed-form metadata mismatch transform and an ExecSpec certificate that measures action-space semantic drift without model inference or rollout. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex
- An executable VLA policy is formally defined as a tuple comprising the learned model, image and language processor, normalized action representation, metadata-selected unnormalizer, and controller conventions. (confidence: 1.00)
  Evidence: An executable VLA policy is a tuple
\begin{equation}
\Pi_{\mathrm{exec}}
  = (f_\theta,\mathcal I,\mathcal Z,\mathcal U_k,\mathcal C).
\end{equation}
Here \(f_\theta\) is the learned model, \(\mathcal I\) is the image and language processor, \(\mathcal Z\) is the normalized action representation emitted or decoded by the model, \(\mathcal U_k\) is the action unnormalizer selected by metadata key \(k\), and \(\mathcal C\) collects controller conventions [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex

### Benchmark

- The paper evaluates the impact of metadata substitution on replay success using the LIBERO-Goal, LIBERO-Spatial, LIBERO-Object, and LIBERO-Long benchmarks. (confidence: 1.00)
  Evidence: On LIBERO-Goal replay, substituting a plausible sibling metadata key yields mean drift 0.199 over six non-gripper action dimensions and reduces success from 28/28 to 2/28 under full substitution. On LIBERO-Spatial replay, the same substituted key reduces success from 26/26 to 0/26. The same full-substitution protocol gives 0/28 success for all four Object substitutions and 0/23 or 1/23 success on Long. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex

### Claim

- Treating VLA policies merely as checkpoint-defined objects is a deployment-safety risk because the same normalized model output can result in different physical actions after unnormalization and controller conventions are applied. (confidence: 1.00)
  Evidence: Vision-language-action (VLA) policies are often treated as checkpoint-defined objects: if the weights, prompt, and benchmark suite match, the deployment is assumed to be the same policy. Robot execution breaks this assumption because the same normalized model output can become a different physical action after action unnormalization and controller conventions are applied. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex
- Substituting a plausible sibling metadata key on LIBERO-Goal replay causes a mean drift of 0.199 over six non-gripper action dimensions and reduces task success from 28/28 to 2/28. (confidence: 1.00)
  Evidence: On LIBERO-Goal replay, substituting a plausible sibling metadata key yields mean drift 0.199 over six non-gripper action dimensions and reduces success from 28/28 to 2/28 under full substitution. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex
- Checkpoint equality does not guarantee executable equality, as two deployments with identical models and normalized outputs can issue different physical actions if their unnormalizers differ. (confidence: 1.00)
  Evidence: There exist two executable VLA policies \(\Pi_c\) and \(\Pi_w\) with identical \(f_\theta\), \(\mathcal I\), \(\mathcal Z\), and \(\mathcal C\), and identical normalized action outputs for every history, such that \(\Pi_c\not\equiv_{\mathrm{exec}}\Pi_w\). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex

### Limitation

- The proposed certificates and replay witnesses do not certify closed-loop or hardware safety, but rather support a narrower deployment-safety view regarding action-space metadata. (confidence: 1.00)
  Evidence: These results do not certify closed-loop or hardware safety. They support a narrower deployment-safety view: action-space metadata is part of the executable policy and should be checked before rollout. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_03724/source.tex

## Scaling by Diversified Experience for Vision-Language-Action Models

`2606_09009` | authors: Leiyu Wang, Zhaofengnian Wang, Xueqi Li, Luoyi Fan, Cewu Lu, Nanyang Ye | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces SyVLA, a Vision-Language-Action model that utilizes an Intention Decoupling algorithm to isolate control-relevant features and a similar-sample guided RL pipeline to stabilize policy updates. (confidence: 0.95)
  Evidence: In this paper, we introduce SyVLA, a robust VLA model trained with diversified experiences. We propose an Intention Decoupling algorithm to isolate control-relevant features from reasoning contexts and a similar-sample guided RL pipeline to stabilize policy updates and mitigate distribution shift. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/summary.md
- The Action Expert in SyVLA is a 0.69B parameter Flow Matching model based on a 15-layer decoder-only transformer with a hidden size of 1408 and 32 attention heads. (confidence: 0.95)
  Evidence: We build our Action Expert based on a transformer architecture, which is a 0.69B parameter Flow Matching model. Concretely, it consists of a 15-layer decoder-only transformer with hidden size 1408, 32 attention heads, and an MLP whose ff_ratio is 2.67 in each layer. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex
- To prevent gradient explosion during reinforcement learning, the authors assign a constant advantage of 1.0 to expert samples and clip the GAE values for rollout data to the range [-0.8, +0.8]. (confidence: 0.95)
  Evidence: Therefore, we abandon the standard PPO GAE for expert data and instead assign a constant advantage of 1.0 to all expert samples, which means we want the policy to follow expert behavior. In addition, we clip the GAE values for rollout data by truncating them to the range \([-0.8, +0.8]\) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex
- SyVLA uses Qwen2.5-VL 3B as its Vision-Language Model and employs 20 Feature Query Tokens with a dimensionality of 2048. (confidence: 0.95)
  Evidence: We choose Qwen2.5-VL 3B as the VLM of SyVLA. For the Feature Query Tokens, we use a fixed set of learnable tensors. Across all three experiments, we use 20 Feature Query Tokens with a dimensionality of 2048, matching the hidden state dimensionality of the VLM. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex

### Dataset

- The pretraining stage uses multi-modal datasets including COCO 2017, VQA-v2, Pixmo Point Explanations, Pixmo Points, and Cambrain, mixed with robotic data. (confidence: 0.95)
  Evidence: Our multi-modal datasets mainly include COCO 2017 ~\cite{lin2014microsoft}, VQA-v2 ~\cite{balanced_vqa_v2}, Pixmo Point Explanations ~\cite{deitke2025molmo}, Pixmo Points ~\cite{deitke2025molmo}, and Cambrain ~\cite{tong2024cambrian1}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex

### Claim

- Extensive experiments demonstrate that SyVLA achieves superior task success rates and stronger out-of-distribution generalization compared to existing methods while preserving core vision-language capabilities. (confidence: 0.90)
  Evidence: Extensive experiments on real-world robotic tasks and multi-modal benchmarks demonstrate that SyVLA achieves superior task success rates and stronger out-of-distribution generalization compared to existing methods, while effectively preserving core vision-language capabilities. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/summary.md

### Limitation

- A current limitation of the proposed SyVLA algorithm is the lack of a rigorous theoretical guarantee for its empirical effectiveness. (confidence: 0.95)
  Evidence: Although our algorithm has been empirically demonstrated to be effective, a rigorous theoretical guarantee has yet to be established. This constitutes a current limitation of our work and remains an important open problem in the VLA literature. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09009/source.tex

## See Less, Specify More: Visual Evidence Budgets for Generalizable VLAs

`2606_02735` | authors: Yueh-Hua Wu, Tatsuya Matsushima, Kei Ota | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- S2 (See Less, Specify More) is a framework designed to improve vision-language-action (VLA) model generalization by training the executor under a cleaner interface that combines goal-preserving hierarchical relabeling and annotation-free visual evidence budgeting. (confidence: 1.00)
  Evidence: We present S2 (See Less, Specify More), a framework for improving VLA generalization by training the executor under a cleaner interface. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md
- The 'Specify More' component preserves the original instruction as a stable high-level goal while relabeling each trajectory into refined trajectory- and subtask-level language to disambiguate the current execution mode. (confidence: 1.00)
  Evidence: Specify More preserves the original instruction as a stable high-level goal while relabeling each trajectory into refined trajectory- and subtask-level language that disambiguates the current execution mode. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md
- The 'See Less' component imposes an explicit visual evidence budget, training the executor to act from task-sufficient evidence rather than unconstrained visual context, without requiring region or mask annotations. (confidence: 1.00)
  Evidence: Unlike native attention, See Less imposes an explicit visual evidence budget, training the executor to act from task-sufficient evidence rather than unconstrained visual context, without any region or mask annotation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

### Dataset

- The method is evaluated on eight real-robot tasks using TX-G2 (an AgiBot G2-compatible variant) and HSR robots. (confidence: 1.00)
  Evidence: Across eight real-robot tasks on TX-G2 (an AgiBot G2-compatible variant) and HSR, S2 raises mean subtask success from 54.2% to 79.0% over pi0.5. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

### Benchmark

- The paper evaluates the proposed method using the LIBERO-PRO benchmark, including object and goal ablations. (confidence: 1.00)
  Evidence: LIBERO-PRO Benchmark
- LIBERO-PRO Object/Goal Ablation [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

### Claim

- S2 improves overall generalization metrics by addressing avoidable supervision aliasing from coarse instructions, outperforming instruction replacement with goal-preserving local guidance, and reducing dependence on broad visual context through explicit evidence budgeting. (confidence: 1.00)
  Evidence: Across our main evaluation settings, S2 improves overall generalization metrics by changing the executor's learning problem: coarse instructions induce avoidable supervision aliasing, goal-preserving local guidance outperforms instruction replacement in our main ablations, and explicit evidence budgeting reduces dependence on broad visual context beyond efficiency considerations. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md
- Across eight real-robot tasks on TX-G2 and HSR, S2 increases the mean subtask success rate from 54.2% to 79.0% compared to pi0.5. (confidence: 1.00)
  Evidence: Across eight real-robot tasks on TX-G2 (an AgiBot G2-compatible variant) and HSR, S2 raises mean subtask success from 54.2% to 79.0% over pi0.5. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md
- VLA generalization improves when the executor is trained to act from informative local guidance and task-sufficient visual evidence, rather than attempting to recover both from weak supervision. (confidence: 1.00)
  Evidence: Together, these results suggest that VLA generalization improves when the executor is trained to act from informative local guidance and task-sufficient visual evidence, rather than recovering both from weak supervision. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

### Limitation

- The paper includes a dedicated section discussing the limitations of the proposed approach, though specific limitations are not detailed in the abstract or summary. (confidence: 0.80)
  Evidence: - Limitations [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02735/summary.md

## SeeTraceAct: Visibility-Aware Latent Planning from Cross-Embodiment Demonstration Videos

`seetraceact` | authors: Jaehyeon Son, Junhyun Kim, Kyle Kam, Jeremiah Coholich, Seok Joon Kim, Jinhoo Kim, Chris Dongjoo Kim, Jaemin Cho, Dieter Fox, Zsolt Kira | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/jaehyeon-son/SeeTraceAct

### Method

- SeeTraceAct is a demo-conditioned vision-language-action (VLA) framework that uses visibility-aware prediction of future end-effector traces to encourage precise spatial grounding. (confidence: 1.00)
  Evidence: we propose SeeTraceAct, a demo-conditioned VLA framework that encourages precise spatial grounding through visibility-aware prediction of future end-effector traces. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- SeeTraceAct is built upon the GR00T N1.5 architecture, utilizing a vision-language model and a flow-matching-based action expert. (confidence: 1.00)
  Evidence: We build SeeTraceAct on top of the GR00T N1.5 architecture, which consists of a vision-language model (VLM) and a flow-matching-based action expert. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- The model forms a visual latent plan by appending learnable query tokens to the input sequence, which attend to image, language, and video tokens under causal attention. (confidence: 1.00)
  Evidence: we append a separate set of learnable query tokens after them. Under causal attention, these query tokens attend to the image, language, and video tokens, and their final hidden states constitute the visual latent plan [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- The visibility-aware trace decoder uses a regression head to predict normalized end-effector coordinates and a validity head to predict if the trace point is within the camera view. (confidence: 1.00)
  Evidence: The regression head predicts normalized end-effector coordinates, while the validity head predicts whether or not each trace point lies within the image [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- SeeTraceAct compresses video features extracted by a pre-trained video encoder into a compact set of tokens using a Perceiver Resampler. (confidence: 1.00)
  Evidence: We first encode the demonstration D using a video encoder pre-trained on large-scale video data... We add a Perceiver Resampler on top of the video encoder to compress the extracted features into a compact set of video tokens [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex

### Benchmark

- The authors introduce RoboCasa-DC, a demo-conditioned extension of the RoboCasa simulation environment that includes episode-paired humanoid videos for cross-embodiment evaluation. (confidence: 1.00)
  Evidence: we introduce and release RoboCasa-DC, a demo-conditioned extension of RoboCasa with episode-paired humanoid videos. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex

### Claim

- SeeTraceAct achieves the highest success rate across all four evaluation settings in the RoboCasa-DC benchmark. (confidence: 1.00)
  Evidence: achieving the best success rate across all four RoboCasa-DC settings [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- In a real-world benchmark using a Franka Panda arm conditioned on human demonstrations, SeeTraceAct improves the average success rate by 12.5 percentage points over baselines. (confidence: 1.00)
  Evidence: improving real-world average success by 12.5 percentage points. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex

### Limitation

- Existing end-to-end demo-conditioned VLA approaches often fail at precision-sensitive tasks that require accurately localizing small target regions. (confidence: 1.00)
  Evidence: we find that existing end-to-end approaches often struggle when successful execution requires precisely localizing small target regions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex
- Trace supervision is ill-posed in multi-view setups because the end effector can leave the camera views, making its coordinates undefined. (confidence: 1.00)
  Evidence: trace supervision is not always well-defined, especially in multi-view setups: the end effector may leave some camera views, making its coordinates ill-posed targets. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/seetraceact/source.tex

## Self-Consistent Generative Paths via Admissible Random Variational Transport

`2606_08953` | authors: Lei Luo, Yingzhen Zhang, Jian Yang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces Self-Consistent Generative Paths (SCGP), a framework that defines a self-consistent generative path as a random fixed point of admissible local variational transport corrections. (confidence: 1.00)
  Evidence: We define a self-consistent generative path as a random fixed point of admissible local variational transport corrections. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/summary.md
- The framework utilizes a random fixed-point path residual (R-FPR) to measure the gap between the actual generated path and an admissible local correction. (confidence: 1.00)
  Evidence: The theory yields a random fixed-point path residual (R-FPR), which measures the gap between the actual generated path and an admissible local correction. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/summary.md
- The framework introduces admissible random variational transport operators (A-RVTOs), which include random regularized optimal-transport proximal steps (R-ROTOs) as a structured instance. (confidence: 1.00)
  Evidence: We introduce admissible random variational transport operators (A-RVTOs), with random regularized optimal-transport proximal steps (R-ROTOs) as a structured instance, and give an admissible-proxy principle that avoids same-sampler degeneracy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/source.tex
- To prevent same-sampler degeneracy, the admissible-proxy principle requires that the local correction used in the residual must not be identical to the actual sampler and must represent an independent or refined correction. (confidence: 1.00)
  Evidence: To avoid this pitfall, the local correction used in the residual must be admissible: it must not be identical to the actual sampler, and it must represent an independent or refined local variational correction such as a two-half-step reference, a higher-order solver, a teacher correction, a critic-induced descent step, or a latent-data product correction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/source.tex

### Claim

- The authors provide theoretical proofs for well-posedness, random fixed-point existence and attraction, non-contractive existence, residual-to-generation error bounds, empirical residual concentration, proxy perturbation bounds, continuous-time limits, and operator-level generalization. (confidence: 1.00)
  Evidence: We prove well-posedness, random fixed-point existence and attraction, non-contractive existence, residual-to-generation error bounds, empirical residual concentration, proxy perturbation bounds, continuous-time limits, and operator-level generalization with model-specific corollaries. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/summary.md
- Evaluating generative models based on path self-consistency is more comprehensive than endpoint matching because it ensures the local journey from prior to data is reliable, avoiding issues like local instability or mode collapse. (confidence: 0.95)
  Evidence: Endpoint matching asks whether the destination looks right; path self-consistency asks whether the journey is reliable... A path may reach a plausible endpoint while being locally unstable, excessively curved, over-smoothed, collapsed to a low-dimensional subset, or unsafe to compress into few steps. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/source.tex
- The proposed framework unifies various generative models, showing how diffusion, flow matching, consistency models, VAEs, GANs, and autoregressive generators can be analyzed within the same self-consistency calculus. (confidence: 0.95)
  Evidence: We also give a graded model dictionary showing how diffusion/score models, flow matching, rectified flow, consistency/one-step generators, VAE kernels, WGAN/GAN updates, autoregressive kernels, Schrodinger bridges, and energy-based samplers enter the same self-consistency calculus as exact instances, limits, degeneracies, or compatible embeddings. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08953/source.tex

## Spatiotemporal Imputation with Graph-Informed Flow Matching

`2606_06682` | authors: Zepeng Zhang, Aref Einizade, Jhony H. Giraldo, Olga Fink | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/zepengzhang/GiFlow

### Method

- The paper proposes GiFlow, a Graph-Informed Flow Matching framework designed for spatiotemporal imputation. (confidence: 1.00)
  Evidence: To address these limitations, we propose \textbf{GiFlow}, a \emph{Graph-Informed Flow Matching} framework for spatiotemporal imputation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex
- GiFlow replaces the typical Gaussian prior with a graph-informed prior constructed via spatiotemporal filtering of observable signals to better align the source distribution to the target. (confidence: 1.00)
  Evidence: GiFlow replaces the typical Gaussian prior with a graph-informed prior constructed via spatiotemporal filtering of observable signals, which better aligns the source distribution to the target and thereby simplifies the generation trajectory. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex
- The flow field in GiFlow is parameterized by a hybrid vector field model that integrates spatial attention, temporal attention, and spatiotemporal propagation. (confidence: 1.00)
  Evidence: The flow field is parameterized by a hybrid vector field model that integrates spatial attention, temporal attention, and spatiotemporal propagation, enabling joint modeling of spatial and temporal dependencies. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex
- The paper utilizes Conditional Flow Matching (CFM) to approximate a conditional vector field, providing a tractable alternative to the standard Flow Matching objective. (confidence: 1.00)
  Evidence: Conditional flow matching (CFM) \citep{lipman2023flow} provides a tractable alternative by approximating a conditional vector field $u_t(\mathbf{x} \mid \mathbf{z})$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex

### Dataset

- The proposed GiFlow model is evaluated on both synthetic and real-world datasets. (confidence: 1.00)
  Evidence: We conduct extensive experiments on both synthetic and real-world datasets, demonstrating that the proposed GiFlow model achieves competitive or superior performance across diverse missing patterns and missing rates [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex

### Claim

- GiFlow achieves competitive or superior performance across diverse missing patterns and missing rates, outperforming state-of-the-art baselines. (confidence: 1.00)
  Evidence: We conduct extensive experiments on both synthetic and real-world datasets, demonstrating that the proposed GiFlow model achieves competitive or superior performance across diverse missing patterns and missing rates, outperforming state-of-the-art baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex

### Limitation

- Traditional machine learning approaches like recurrent and graph neural networks rely on iterative propagation, which tends to accumulate errors over time and space. (confidence: 1.00)
  Evidence: Traditional machine learning approaches, like recurrent and graph neural networks, rely on iterative propagation, which tends to accumulate errors over time and space. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex
- Diffusion-based methods require iterative sampling and often depend on problem-agnostic Gaussian priors, which limits their efficiency and effectiveness. (confidence: 1.00)
  Evidence: Recent diffusion-based methods mitigate error propagation but require iterative sampling and often depend on problem-agnostic Gaussian priors, limiting both efficiency and effectiveness. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06682/source.tex

## SpeakerLLM: A Speaker-Specialized Audio-LLM for Speaker Understanding and Verification Reasoning

`speakerllm` | authors: KiHyun Nam, Jungwoo Heo, Siu Bae, Ha-Jin Yu, Joon Son Chung | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- SpeakerLLM is a speaker-specialized audio-LLM framework that unifies single-utterance speaker profiling, recording-condition understanding, utterance-pair speaker comparison, and evidence-organized verification reasoning within a natural-language interface. (confidence: 1.00)
  Evidence: We present SpeakerLLM, a speaker-specialized audio-LLM framework that unifies single-utterance speaker profiling, recording-condition understanding, utterance-pair speaker comparison, and evidence-organized verification reasoning within a natural-language interface. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- The framework utilizes a hierarchical speaker tokenizer to capture multiple granularities of speaker evidence, employing utterance-level embeddings for identity and profile cues, and frame-level features for fine-grained acoustic descriptors. (confidence: 1.00)
  Evidence: At its core, SpeakerLLM uses a hierarchical speaker tokenizer designed to capture multiple granularities of speaker evidence. Utterance-level speaker embeddings summarize identity and profile-level cues, whereas frame-level speaker features preserve fine-grained acoustic descriptors. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- SpeakerLLM constructs verification-reasoning targets and a decision-composition policy that separate profile-level evidence from the final same-or-different decision, organizing them into a structured trace. (confidence: 1.00)
  Evidence: We construct verification-reasoning targets and a decision-composition policy that separate profile-level evidence from the final same-or-different decision and organize recording condition, profile evidence, and the decision into a structured trace. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- Pitch attributes are discretized using gender-conditioned fundamental frequency (F0) percentile cutoffs, while timbral brightness uses gender-shared spectral-centroid percentile cutoffs. (confidence: 1.00)
  Evidence: Pitch is discretized using gender-conditioned F0 percentile cutoffs, while timbral brightness uses gender-shared spectral-centroid percentile cutoffs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- Noise labels are computed and controlled based on the signal-to-noise ratio (SNR) between the clean speech waveform and a scaled non-speech noise waveform. (confidence: 1.00)
  Evidence: Noise labels are controlled by the signal-to-noise ratio (SNR) between the clean speech waveform $s$ and the scaled non-speech noise waveform $\alpha n$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- Acoustic feature extraction derives pitch from the per-utterance mean fundamental frequency using librosa.pyin, and timbral brightness from the per-utterance mean spectral centroid over STFT frames. (confidence: 1.00)
  Evidence: Pitch is derived from the per-utterance mean fundamental frequency (F0), estimated using \texttt{librosa.pyin}. Timbral brightness is derived from the per-utterance mean spectral centroid computed over STFT frames. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- Stage 1 of the training process supports Speaker Understanding by using short-form targets during speaker-tokenizer warm-up to stabilize cue decoding and align audio-derived representations with the language model input space. (confidence: 1.00)
  Evidence: Stage~1 supports Speaker Understanding and uses the same scenario inventory across two target styles. During speaker-tokenizer warm-up, short-form targets are used to stabilize cue decoding and align audio-derived speaker representations with the language model input space. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- The verification reasoning target utilizes an internal profile-support level (supportive, mixed, or conflicting) to summarize whether available speaker-profile attributes support or conflict with a same-speaker interpretation before the final verdict. (confidence: 1.00)
  Evidence: The verification reasoning target uses an internal \emph{profile-support level} with respect to a same-speaker interpretation: \{\textsc{supportive}, \textsc{mixed}, \textsc{conflicting}\}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex

### Dataset

- The authors plan to release the metadata-enriched supervision dataset and the target-construction code to ensure reproducibility. (confidence: 1.00)
  Evidence: We will release the metadata-enriched supervision dataset and target-construction code for reproducibility. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex

### Claim

- Experimental results demonstrate that SpeakerLLM-Base improves speaker-profile and recording-condition understanding compared to general audio-LLMs. (confidence: 1.00)
  Evidence: Experiments show that SpeakerLLM-Base improves speaker-profile and recording-condition understanding over general audio-LLMs [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex
- SpeakerLLM-VR maintains strong generated-verdict accuracy while producing decision traces that are grounded in the supervised verification reasoning schema. (confidence: 1.00)
  Evidence: while SpeakerLLM-VR preserves strong generated-verdict accuracy and produces decision traces grounded in the supervised verification reasoning schema. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/speakerllm/source.tex

## Stabilizing On-Policy Distillation for MLLM Reasoning with Global Normalization

`2606_09091` | authors: Dongze Hao, Zhiwei Jin, Chen Chen, Haonan Lu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/OPPO-Mente-Lab/GNDPO

### Method

- The paper proposes Globally Normalized Distillation Policy Optimization (GNDPO), which stabilizes on-policy distillation by converting raw token-level KL divergence scores into batch-level relative advantages. (confidence: 1.00)
  Evidence: we propose Globally Normalized Distillation Policy Optimization (GNDPO), a practical method that stabilizes optimization by transforming raw KL scores into batch-level relative advantages. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex
- The study uses the InternVL3.5 model family at 1B, 2B, and 4B parameter scales as student models, with InternVL3.5-8B serving as the teacher model. (confidence: 1.00)
  Evidence: We conduct experiments with the InternVL3.5 model family at three scales: InternVL3.5-1B-Instruct, InternVL3.5-2B-Instruct, and InternVL3.5-4B-Instruct. We use InternVL3.5-8B as the teacher model for OPD and GNDPO. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex
- In the on-policy distillation setup, the token-level reward is defined as the negative reverse KL divergence between the student and teacher model distributions. (confidence: 1.00)
  Evidence: We use the reverse KL divergence between the student and teacher distributions as the reward signal for each token [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex

### Dataset

- The models are trained using the Geometry3K multimodal mathematical reasoning dataset. (confidence: 1.00)
  Evidence: For training data, we use the multimodal mathematical reasoning dataset Geometry3K [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex

### Benchmark

- The proposed method is evaluated on multiple multimodal reasoning benchmarks, including MathVista, MMMU, MathVision, MathVerse, DynaMath, Wemath, and LogicVista. (confidence: 1.00)
  Evidence: We evaluate the model on various challenging  multimodal reasoning benchmarks: MathVista, MMMU, MathVision, MathVerse, DynaMath, Wemath, LogicVista. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex

### Claim

- On-policy distillation provides an advantage over reinforcement learning with verifiable rewards (RLVR) by using a teacher model to supply dense, fine-grained supervision rather than sparse outcome-based feedback. (confidence: 1.00)
  Evidence: By using a stronger teacher model to provide dense, fine-grained supervision for sampled trajectories, OPD offers a clear advantage over reinforcement learning with verifiable rewards (RLVR), which typically depends on sparse binary or outcome-based environmental feedback. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex
- Naive token-level distillation experiences gradient instability and explosions due to magnitude misalignment when the student model generates out-of-distribution tokens that the teacher assigns near-zero probability. (confidence: 1.00)
  Evidence: naive token-level distillation can suffer from gradient instability, due to magnitude misalignment in outlier states. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex
- Experimental results indicate that GNDPO consistently improves generation quality and training robustness over state-of-the-art RL and standard distillation baselines across multimodal reasoning tasks. (confidence: 1.00)
  Evidence: Experimental results show that GNDPO substantially improves training robustness and downstream performance across multimodal reasoning tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09091/source.tex

## Stage-1 Controls the Entropy Regime, Not the Outcome

`2606_09059` | authors: Jianxiong Shen | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The study investigates a two-stage post-training pipeline for vision-language models, consisting of a Stage-1 warm-start (SFT or OPD) followed by Stage-2 reinforcement learning. (confidence: 1.00)
  Evidence: Two-stage post-training --- a Stage-1 warm-start (supervised fine-tuning, SFT, or on-policy distillation, OPD) followed by Stage-2 reinforcement learning (RL) --- is increasingly used for vision-language models (VLMs). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- The on-policy distillation (OPD) method uses a same-modality 72B teacher model to train a 7B student model using reverse-KL, token-level distillation. (confidence: 1.00)
  Evidence: Student: Qwen2.5-VL-7B-Instruct. Teacher: Qwen2.5-VL-72B (same modality). OPD is reverse-KL, token-level, on-policy distillation over all $2{,}101$ Geometry3K training prompts. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex

### Benchmark

- Geometry3K is used as the in-domain benchmark, utilizing a 601-item test set. (confidence: 1.00)
  Evidence: In-domain: Geometry3K ($601$-item test). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- MathVista testmini, consisting of 1,000 items, is used for out-of-domain (OOD) evaluation. (confidence: 1.00)
  Evidence: OOD: MathVista testmini ($1{,}000$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex

### Claim

- Catastrophic forgetting in supervised fine-tuning (SFT) is recipe-dependent; an early-stopped SFT improves out-of-domain performance on MathVista, whereas an over-trained variant causes a significant performance drop. (confidence: 1.00)
  Evidence: A matched-recipe, early-stopped SFT improves OOD MathVista by $+2.1$ over base; the $-9.5$ drop appears only in the longer, prompt-mismatched variant. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- After Stage-2 reinforcement learning, all three warm-start methods reach a narrow performance band of 53-54% on the in-domain Geometry3K validation set. (confidence: 1.00)
  Evidence: The three warm-starts reach $53$--$54\%$ best internal validation, similar to the range reported by recent specialized methods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- The Stage-1 warm-start method strongly influences the entropy regime, with on-policy distillation (OPD) entering reinforcement learning with substantially higher policy entropy than SFT initializations. (confidence: 1.00)
  Evidence: The clearest difference is the \emph{entropy regime}: OPD enters RL with substantially higher policy entropy than either SFT initialization, and the separation remains visible through the available trajectories. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- The exploration advantage of OPD over SFT, measured by pass@16, is present at the in-domain initialization but vanishes after reinforcement learning and on out-of-domain benchmarks. (confidence: 1.00)
  Evidence: The advantage is absent after RL (endpoint pass@16 values within $1.1$ points) and on MathVista (six models within $1.2$ points). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex

### Limitation

- The study lacks independent training seeds, which limits the ability to make strong statistical claims about the indistinguishability of the narrow in-domain performance band. (confidence: 1.00)
  Evidence: We do not have independent training seeds, so ``statistically indistinguishable'' would be too strong. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex
- The SFT and OPD warm-starts do not have identical data coverage; SFT uses rejection sampling and only sees problems the teacher can solve, while OPD trains on all problems including the hard tail. (confidence: 1.00)
  Evidence: rejection sampling retains only the \textbf{807 problems} the teacher solves within $4$ samples ($1{,}083$ correct traces, $1.34$ per problem), whereas OPD trains over \textbf{all $2{,}101$} --- including the \textbf{$1{,}294$ problems the teacher never solves}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09059/source.tex

## Stochastic Multiscale Reconstruction of Lagrangian Turbulence via Guided Diffusion Models

`2606_05783` | authors: Conghui Wang, Tianyi Li, Luca Biferale, Qinmin Zheng, Michele Buzzicotti, Fabio Bonaccorso | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/SmartTURB/diffusion-lagr

### Method

- The proposed method samples the conditional distribution of unresolved fine-scale fluctuations using a diffusion-model prior conditioned on large-scale dynamics obtained via wavelet-based coarse-graining. (confidence: 1.00)
  Evidence: we address this problem by sampling the conditional distribution of unresolved fluctuations using a diffusion-model prior conditioned on large-scale dynamics obtained through a wavelet-based coarse-graining of Lagrangian trajectories. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- The sampling process is guided by enforcing consistency with the coarse-grained observation using a diffusion posterior sampling (DPS) approach. (confidence: 1.00)
  Evidence: we guide the sampling process by enforcing consistency with the coarse-grained observation, following a diffusion posterior sampling (DPS) approach [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- A Gaussian process regression (GPR) baseline is applied in the wavelet representation of the velocity trajectories for comparison. (confidence: 1.00)
  Evidence: a Gaussian process regression (GPR) baseline \cite{williams2006gaussian}, applied in the wavelet representation of the velocity trajectories [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex

### Dataset

- The study uses tracer trajectories from direct numerical simulations (DNS) of homogeneous and isotropic turbulence at a Taylor-scale Reynolds number of approximately 310. (confidence: 1.00)
  Evidence: We analyze Lagrangian velocity trajectories obtained from direct numerical simulations (DNS) of homogeneous and isotropic turbulence at Taylor-scale Reynolds number $Re_\lambda \simeq 310$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- Each Lagrangian trajectory in the dataset is sampled at a temporal resolution of 0.1 Kolmogorov times over a duration of approximately 100 Kolmogorov times. (confidence: 1.00)
  Evidence: Each trajectory is sampled at temporal resolution $dt_s = 0.1 \tau_\eta$ over a duration $T \sim 0.7 \tau_L \sim 100 \tau_\eta$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex

### Claim

- The reconstructed signals using the proposed method recover scale-dependent intermittent statistics, including high-order structure functions, flatness, and local scaling exponents. (confidence: 1.00)
  Evidence: the reconstructed signals recover scale-dependent intermittent statistics, including high-order structure functions, flatness, and local scaling exponents, together with cross-scale temporal correlations between resolved and unresolved fluctuations. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- The diffusion posterior sampling (DPS) method remains consistent with DNS across all time lags for the fourth-order structure function, whereas GPR deviates. (confidence: 1.00)
  Evidence: GPR, which reproduces second-order statistics by construction (not shown), deviates from DNS in the fourth-order structure function, whereas DPS remains consistent with DNS across all time lags. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- DPS reproduces the growth of flatness toward small scales and captures scale-dependent intermittency in close agreement with DNS. (confidence: 1.00)
  Evidence: GPR underestimates the growth of flatness toward small scales and fails to capture the scale-dependent intermittency, while DPS reproduces both quantities in close agreement with DNS. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex

### Limitation

- Gaussian-process reconstructions in wavelet representation suppress rare events and fail to reproduce the broad stochastic variability of intermittent acceleration fluctuations. (confidence: 1.00)
  Evidence: whereas Gaussian-process reconstructions in wavelet representation suppress rare events. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- GPR fails to capture the pronounced increase of flatness in the dissipative range, which is a key signature of intermittency. (confidence: 1.00)
  Evidence: GPR fails to capture the pronounced increase of flatness in the dissipative range, a key signature of intermittency that poses a stringent test for stochastic and phenomenological models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex
- GPR collapses toward a narrow band and fails to reproduce large-amplitude values of the detail component, unlike DPS which exhibits strong correlation with the ground truth. (confidence: 1.00)
  Evidence: DPS exhibits a strong correlation with the ground truth across a broad range of fluctuations, whereas GPR collapses toward a narrow band and fails to reproduce large-amplitude values. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05783/source.tex

## TABVERSE: Benchmarking Cross-Format Table Understanding in LLMs and VLMs

`tabverse` | authors: Momina Ahsan, Sarfraz Ahmad, Ming Shan Hee, Roy Ka-Wei Lee, Preslav Nakov | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/mbzuai-nlp/TABVERSE

### Method

- TABVERSE evaluates LLMs and VLMs across three tasks: Question Answering (QA), Structural Understanding Capability (SUC), and Structure Reconstruction (SR). (confidence: 1.00)
  Evidence: We evaluate LLMs and VLMs across three tasks: Question Answering (QA), Structural Understanding Capability (SUC), and Structure Reconstruction (SR). [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex
- The Structural Understanding Capability (SUC) task probes structure understanding through boundary detection, size estimation, and index-based retrieval. (confidence: 1.00)
  Evidence: QA measures answer prediction under different table representations; SUC probes structure understanding through boundary detection, size estimation, and index-based retrieval; and SR measures whether VLMs can reconstruct tables from rendered images. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex

### Dataset

- TABVERSE is built from held-out evaluation splits of FEVEROUS, HybridQA, TabFact, SQA, and WikiTableQuestions. (confidence: 1.00)
  Evidence: Built from held-out evaluation splits of \textsc{FEVEROUS}, \textsc{HybridQA}, \textsc{TabFact}, \textsc{SQA}, and \textsc{WikiTableQuestions}, it includes a full tagged pool and a 700-sample balanced evaluation set balanced by question category and difficulty. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex
- TABVERSE includes a 700-sample balanced evaluation set balanced by question category and difficulty. (confidence: 1.00)
  Evidence: Built from held-out evaluation splits of \textsc{FEVEROUS}, \textsc{HybridQA}, \textsc{TabFact}, \textsc{SQA}, and \textsc{WikiTableQuestions}, it includes a full tagged pool and a 700-sample balanced evaluation set balanced by question category and difficulty. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex

### Benchmark

- TABVERSE is a controlled multimodal table benchmark that aligns the same table content across multiple structural formats and rendered images. (confidence: 1.00)
  Evidence: We introduce TABVERSE, a controlled multimodal table benchmark that aligns the same table content across multiple structural formats and rendered images, with question category and difficulty tags. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/summary.md

### Claim

- Models generally perform better with structured text than with rendered images, though the performance gap depends on the task, model, and format. (confidence: 1.00)
  Evidence: Models generally perform better with structured text than with rendered images, but the size of this gap depends on the task, model, and format. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex
- HTML is often the most robust text format for table understanding among the evaluated formats. (confidence: 1.00)
  Evidence: HTML is often the most robust text format, while row-sensitive structural tasks and syntactically usable LaTeX reconstruction remain challenging. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex

### Limitation

- Row-sensitive structural tasks and syntactically usable LaTeX reconstruction remain challenging for current models. (confidence: 1.00)
  Evidence: HTML is often the most robust text format, while row-sensitive structural tasks and syntactically usable LaTeX reconstruction remain challenging. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tabverse/source.tex

## TORL-VLA: Tactile Guided Online Reinforcement Learning for Contact-Rich Manipulation

`torl-vla` | authors: Huaihang Zheng, Yi Yang, Kai Ma, Shenglin Xu, Tian Xie, Guozheng Li, Xiangyu Wang, Yiren Ma, Si Liu, Yinian Mao, Baoxu Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- TORL-VLA introduces a tactile-derived wrench-aware Vision-Language-Action (VLA) model to predict reference actions and future wrench sequences. (confidence: 1.00)
  Evidence: Our method introduces a tactile-derived wrench-aware VLA to predict reference actions and future wrench sequences [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- A lightweight online reinforcement learning module is utilized to refine the reference actions generated by the VLA. (confidence: 1.00)
  Evidence: while a lightweight online RL module is used to refine the reference actions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- To stabilize learning from mixed exploratory and human-intervention data, TORL-VLA uses an intervention-censored critic that prevents post-intervention success from being incorrectly credited to preceding policy-generated actions. (confidence: 1.00)
  Evidence: To stabilize learning from mixed exploratory policy-generated and human-intervention data, we introduce an intervention-censored critic that prevents post-intervention success from being wrongly credited to policy-generated actions preceding intervention. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- The robotic gripper is equipped with two piezoelectric tactile pads on the inner finger surfaces, and each raw 6x8 tactile array is mapped to a compact 6D wrench representation. (confidence: 1.00)
  Evidence: Our gripper has two piezoelectric tactile pads mounted on the inner finger surfaces, as illustrated in Fig.~\ref{fig:tactile_wrench_mapping}. Each raw \(6 \times 8\) tactile array is mapped to a compact 6D wrench through the calibrated sensor interface. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- Instead of feeding the tactile-derived wrench token into the VLM alongside image and language tokens, it is fused after visual-language encoding by applying self-attention. (confidence: 1.00)
  Evidence: rather than feeding the tactile-derived wrench token into the VLM with image and language tokens, we fuse it after visual-language encoding by applying self-attention to \([\mathbf{P}_t;\mathbf{z}_t^{\mathrm{tac}}]\) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- A soft router is used to compute weights and produce a fused feature from multiple experts, which is then projected to the action horizon and combined with a zero-initialized wrench-token bypass. (confidence: 1.00)
  Evidence: a soft router computes \(\boldsymbol{\rho}_t=\mathrm{Softmax}(R_{\mathrm{tac}}(\mathbf{H}_t))\) and produces the fused feature \(\mathbf{F}_t=\sum_{m=1}^{M}\boldsymbol{\rho}_{t,m}\odot E_m(\mathbf{H}_t)\) [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex
- The model's output head jointly predicts the action chunk and the co-predicted future wrench sequence, trained with a joint action-wrench flow matching objective. (confidence: 1.00)
  Evidence: The output head jointly predicts \(\hat{\mathbf{y}}_t=[\hat{\mathbf{A}}_{t:t+H-1}, \hat{\mathbf{W}}_{t:t+H-1}]\), where \(\hat{\mathbf{A}}_{t:t+H-1}\) is the predicted action chunk and \(\hat{\mathbf{W}}_{t:t+H-1}\) is the co-predicted future wrench sequence [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex

### Claim

- Real-robot experiments on long-horizon contact-rich tasks demonstrate that TORL-VLA improves success rates at both subtask and full-task levels, as well as time-bounded execution efficiency over strong baselines. (confidence: 1.00)
  Evidence: Real-robot experiments on long-horizon contact-rich tasks, including latch manipulation, coffee-cup placement, and egg handling, show that TORL-VLA improves success rates at both subtask and full-task levels, as well as time-bounded execution efficiency over strong baselines. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/torl-vla/source.tex

## TTT-VLA: Test-Time Latent Prompt Optimization for Vision-Language-Action Models

`ttt-vla` | authors: Wenbo Zhang, Jianxiong Li, Shuai Yang, Sijin Chen, Jiajun Liu, Lingqiao Liu, Xiao Ma | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## TVI-CoT: Text-Visual Interleaved Chain-of-Thought Reasoning for Multimodal Understanding

`tvi-cot` | authors: Lianyu Hu, Xiaoyu Ma, Zeqin Liao, Yang Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/hulianyuyy/TVI-CoT

### Method

- The TVI-CoT framework enables the explicit interleaving of textual reasoning and visual feature access using learnable control tokens <THINK>, <LOOK>, and <ANSWER>. (confidence: 1.00)
  Evidence: We propose Text-Visual Interleaved Chain-of-Thought (TVI-CoT), a framework that enables explicit interleaving of textual reasoning and visual feature access through learnable control tokens <THINK>, <LOOK> and <ANSWER>. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- The control tokens in TVI-CoT allow the model to dynamically switch between textual reasoning and visual grounding, attending to relevant image regions based on the evolving reasoning state. (confidence: 1.00)
  Evidence: These tokens allow dynamic switching between reasoning and visual grounding, attending to relevant image regions conditioned on the evolving reasoning state. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/source.tex

### Benchmark

- The TVI-CoT framework was evaluated across eight different multimodal benchmarks. (confidence: 1.00)
  Evidence: Experiments on eight benchmarks demonstrate state-of-the-art results among MLLM-based CoT methods [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/source.tex

### Claim

- TVI-CoT achieves a 6.1% performance improvement on the MMMU benchmark compared to the baseline. (confidence: 1.00)
  Evidence: Experiments on eight benchmarks demonstrate state-of-the-art results among MLLM-based CoT methods and notable performance boost compared to the baseline: +6.1% on MMMU [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- TVI-CoT achieves a 3.8% performance improvement on the MathVerse benchmark compared to the baseline. (confidence: 1.00)
  Evidence: +3.8% on MathVerse [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- TVI-CoT achieves a 3.4% performance improvement on the MathVista benchmark compared to the baseline. (confidence: 1.00)
  Evidence: +3.4% on MathVista [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- TVI-CoT achieves a 3.4% performance improvement on the ScienceQA benchmark compared to the baseline. (confidence: 1.00)
  Evidence: and +3.4% on ScienceQA. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md

### Limitation

- Existing multimodal Chain-of-Thought approaches suffer from a fundamental limitation where they perform reasoning entirely in text without accessing visual features during the reasoning process. (confidence: 1.00)
  Evidence: However, when applied to multimodal LLMs (MLLMs), existing CoT approaches suffer from a fundamental limitation: they perform reasoning entirely in text without accessing visual features during the reasoning process. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md
- The inability to re-access image information after initial encoding creates a 'vision-blind reasoning' paradigm that restricts fine-grained visual extraction, error verification, and adaptive attention. (confidence: 1.00)
  Evidence: After initial visual encoding, image information becomes inaccessible, forcing models to reason based solely on whatever was captured in the initial description, which forms a `vision-blind reasoning' paradigm that limits fine-grained visual extraction, error verification, and adaptive attention. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tvi-cot/summary.md

## Task Robustness via Re-Labelling Vision-Action Robot Data

`2606_10918` | authors: Artur Kuramshin, Özgür Aslan, Cyrus Neary, Glen Berseth | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- TREAD is a scalable framework that leverages large Vision-Language Models (VLMs) to augment existing robotics datasets without requiring additional data collection. (confidence: 1.00)
  Evidence: This paper introduces Task Robustness via Re-Labelling Vision-Action Robot Data (TREAD), a scalable framework that leverages large Vision-Language Models (VLMs) to augment existing robotics datasets without additional data collection [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex
- The TREAD framework operates in three stages using a pretrained VLM: generating semantic sub-tasks from original instructions and initial scenes, segmenting demonstration videos based on these sub-tasks, and producing diverse instructions incorporating object properties. (confidence: 1.00)
  Evidence: Our approach leverages a pretrained VLM through three stages: generating semantic sub-tasks from original instruction labels and initial scenes, segmenting demonstration videos conditioned on these sub-tasks, and producing diverse instructions that incorporate object properties [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex
- Unlike NILS which uses multiple large models and heuristics, TREAD relies on a single iteratively queried VLM without heuristics to segment and relabel trajectories. (confidence: 1.00)
  Evidence: NILS \citep{blank2024scalingshort} is another framework that incorporates multiple large models and heuristics to segment and relabel trajectories, whereas our method (TREAD) relies on a single iteratively queried VLM without heuristics, making it simpler to reproduce. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex
- TREAD decomposes longer-horizon demonstrations into meaningful sub-tasks, which contrasts with methods like SPRINT that focus on composing shorter skills into longer sequences. (confidence: 1.00)
  Evidence: SPRINT \citep{zhang2024sprint}, another closely related work, focuses on composing shorter skills into longer sequences. However, our approach does the opposite by decomposing longer-horizon demonstrations into meaningful sub-tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex

### Dataset

- The TREAD framework is evaluated using the LIBERO robotics dataset. (confidence: 1.00)
  Evidence: Evaluations on LIBERO demonstrate that policies trained on our augmented datasets exhibit improved performance on novel, unseen tasks and goals. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex

### Claim

- TREAD enhances planning generalization through trajectory decomposition and language-conditioned policy generalization through increased linguistic diversity. (confidence: 1.00)
  Evidence: Our results show that TREAD enhances both planning generalization through trajectory decomposition and language-conditioned policy generalization through increased linguistic diversity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex
- Training on the TREAD augmented dataset improves the zero-shot performance and text goal following of the vision-language-action policies Octo and pi_0-FAST. (confidence: 1.00)
  Evidence: In our experiments with the LIBERO dataset \cite{liu2023libero} we show that the resulting augmented dataset improves zero-shot performance and text goal following of the vision-language-action policy Octo \cite{octo_2023} and $\pi_0$-FAST \citep{pertsch2025fast}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex

### Limitation

- Current robot learning policies struggle with following instructions, which is likely caused by the limited linguistic and action sequence diversity present in existing robotics datasets. (confidence: 0.90)
  Evidence: However, these policies continue to struggle with following instructions, likely due to the limited linguistic and action sequence diversity in existing robotics datasets. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10918/source.tex

## Teaching the Way, Not the Answer: Privileged Tutoring Distillation for Multimodal Policy Optimization

`2606_07000` | authors: Shizhe Xiang, Ke An, Wenlong Yu, Yue Liu, Jian Luan, Pei Fu, Qilong Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/XszNeverSleep/PTD-PO, https://github.com/goodfeli/dlbook_notation

### Method

- The paper proposes PTD-PO, a Privileged Tutoring Distillation Policy Optimization framework for RLVR that provides dense guidance without exposing the answer to the student policy. (confidence: 1.00)
  Evidence: To address these limitations, we propose PTD-PO, a Privileged Tutoring Distillation Policy Optimization framework for RLVR that provides dense guidance without exposing the answer to the student policy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- PTD-PO constructs structured privileged hints from spatial attention guidance and intermediate textual reasoning steps, and uses them through in-context learning to produce step-wise token-distribution supervision. (confidence: 1.00)
  Evidence: Specifically, PTD-PO constructs structured privileged hints from spatial attention guidance and intermediate textual reasoning steps, and uses them through in-context learning to produce step-wise token-distribution supervision. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- The authors introduce a Top-K Jensen-Shannon divergence objective to stabilize distillation under the distribution shift between guided and unguided contexts, focusing alignment on informative token probabilities while reducing memory overhead. (confidence: 1.00)
  Evidence: To further stabilize distillation under the distribution shift between guided and unguided contexts, we introduce a Top-K Jensen-Shannon divergence objective that focuses alignment on informative token probabilities while reducing memory overhead. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- GRPO estimates the advantage of each response by normalizing rewards within the sampled group, which removes the need for a learned value function. (confidence: 1.00)
  Evidence: GRPO \citep{shao2024deepseekmath} estimates the advantage of each response by normalizing rewards within the sampled group... GRPO removes the need for a learned value function by using group-relative rewards [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex

### Claim

- Experiments on LVLMs ranging from 2B to 8B parameters show that PTD-PO consistently outperforms RLVR and distillation baselines, mitigates entropy collapse, and improves complex multimodal reasoning performance. (confidence: 1.00)
  Evidence: Experiments on LVLMs ranging from 2B to 8B parameters show that PTD-PO consistently outperforms RLVR and distillation baselines, mitigates entropy collapse, and improves complex multimodal reasoning performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- Informative groups in GRPO, which contain both successful and failed responses and provide discriminative relative rewards, remain limited in proportion throughout training. (confidence: 1.00)
  Evidence: Informative groups provide discriminative relative rewards, but their proportion remains limited throughout training. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex

### Limitation

- The sparse nature of verifiable rewards in RLVR provides little token-level supervision for failed rollouts, often leading to inefficient exploration in complex multimodal reasoning tasks. (confidence: 1.00)
  Evidence: However, the sparse nature of verifiable rewards provides little token-level supervision for failed rollouts, often leading to inefficient exploration in complex multimodal reasoning tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- External teacher-based policy distillation methods introduce substantial computational overhead, while answer-conditioned tuning methods may expose answer-level information and induce shortcut-like generation behavior. (confidence: 1.00)
  Evidence: Although policy distillation can offer dense guidance, external teacher based methods introduce substantial computational overhead, while answer conditioned tuning methods may expose answer-level information and induce shortcut-like generation behavior. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex
- In GRPO, when all sampled responses fail, the policy may receive weak or uninformative guidance for improving intermediate reasoning steps because the learning signal is derived from outcome-level verification. (confidence: 1.00)
  Evidence: Therefore, when all sampled responses fail, the policy may receive weak or even uninformative guidance for improving intermediate reasoning steps. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07000/source.tex

## The Last Visible Pixel: Probing Fine-Scale Perception in Vision-Language Models

`2606_07861` | authors: Lujun Li, Lama Sleem, Niccolo Gentile, Yangjie Xu, Yewei Song, Wenbo Wu, Radu State | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- FineSightBench consists of two complementary components: Perception, which targets pixel-level visual perception by varying maximum object dimensions, and Reasoning, which evaluates models' sensitivity to perform spatially precise, detail-intensive reasoning at different pixel scales. (confidence: 1.00)
  Evidence: This consists of two complementary components. The first, \textbf{Perception}, targets pixel-level visual perception by varying the maximum object dimensions (width and height) and the subtlety of small objects, thereby probing the detection limits of state-of-the-art VLMs. The second, \textbf{Reasoning}, focuses on evaluating models' sensitivity to perform spatially precise, detail-intensive reasoning at different pixel scales. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex
- The authors adopt the Test of Visual Perceptual Skills (TVPS) as the foundation for the design of their benchmark to evaluate visual perceptual abilities. (confidence: 1.00)
  Evidence: We adopt the \textit{Test of Visual Perceptual Skills} (TVPS) as the foundation for design to evaluate human visual perceptual abilities~\cite{brown2018overview,martin2017tvps}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

### Dataset

- The authors chose 448 as the canvas size for their dataset because mainstream open-source VLMs typically adopt input resolutions ranging from 224 to 448 pixels. (confidence: 1.00)
  Evidence: In practice, mainstream open-source VLMs typically adopt input resolutions ranging from 224 to 448 pixels as an empirical observation, which is also the reason why we chose 448 as the canvas size for our dataset. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

### Benchmark

- The authors introduce FineSightBench, a new benchmark that systematically probes the limit of fine-grained visual perception in VLMs by separating perception tasks from reasoning tasks across controlled scales of 4-48px. (confidence: 1.00)
  Evidence: As such, we introduce FineSightBench, a new benchmark that systematically probes this limit by separating perception tasks (pixel-level recognition of letters, shapes, objects) from reasoning tasks (spatial reasoning, counting, ordering over small targets) across controlled scales of 4--48px. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

### Claim

- The study reveals a sharp dissociation in VLMs where perception saturates around 12px, while reasoning remains limited even at larger scales, with persistent numeracy and sequence errors. (confidence: 1.00)
  Evidence: Through comprehensive experiments and detailed failure mode analysis on state-of-the-art models, we reveal a sharp dissociation: perception saturates around 12px, while reasoning remains limited even at larger scales, with persistent numeracy and sequence errors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex
- VLMs perform substantially worse on objects at 4 pixels than on those at 48 pixels, and current models further struggle with complex spatial reasoning tasks, such as object counting. (confidence: 1.00)
  Evidence: Our results demonstrate that VLMs perform substantially worse on objects at \(4\) pixels than on those at \(48\) pixels, and that current models further struggle with complex spatial reasoning tasks, such as object counting. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

### Limitation

- Accurately reporting a visual detail is not equivalent to using it correctly for accurate reasoning; a VLM may occasionally detect a subtle cue, yet still fail to reason over it consistently or express it in a verifiable manner. (confidence: 1.00)
  Evidence: Moreover, accurately reporting a visual detail is not equivalent to using it correctly for accurate reasoning and faithful description: a VLM may occasionally detect a subtle cue, yet still fail to reason over it consistently or express it in a verifiable manner. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_07861/source.tex

## The Lie We Tell: Correcting the Euclidean Fallacy in Vision Language Action Policies via Score Matching on Tangent Space

`2606_01847` | authors: Bing-Cheng Chuang, I-Hsuan Chu, Bor-Jiun Lin, YuanFu Yang, Min Sun, Chun-Yi Lee | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors introduce Lie Diffuser Actor (LDA), a diffusion framework that operates intrinsically on the SE(3) manifold. (confidence: 1.00)
  Evidence: We introduce \textbf{Lie Diffuser Actor (LDA)}, a diffusion framework operating intrinsically on SE(3). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex
- LDA injects noise through left-invariant SDEs, predicts scores in the tangent space, and retracts samples via the exponential map. (confidence: 1.00)
  Evidence: Our method injects noise through left-invariant SDEs, predicts scores in the tangent space, and retracts samples via the exponential map. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex

### Benchmark

- The proposed method is evaluated on the CALVIN ABC->D benchmark. (confidence: 1.00)
  Evidence: On CALVIN ABC$\rightarrow$D, LDA improves average task length from  $3.27$ to $3.51$ ($+7.3\%$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex

### Claim

- The LDA formulation eliminates manifold drift by construction while guaranteeing coordinate-frame equivariance and geodesic optimality. (confidence: 1.00)
  Evidence: This formulation eliminates manifold drift by construction while guaranteeing coordinate-frame equivariance and geodesic optimality. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex
- On the CALVIN ABC->D benchmark, LDA improves the average task length from 3.27 to 3.51, representing a 7.3% increase. (confidence: 1.00)
  Evidence: On CALVIN ABC$\rightarrow$D, LDA improves average task length from  $3.27$ to $3.51$ ($+7.3\%$). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex
- The methodology was validated on a real robot and outperformed the baseline on the majority of tasks. (confidence: 1.00)
  Evidence: We further validate our method on real robot and the results show that our methodology outperforms the baseline on majority tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex

### Limitation

- Existing diffusion-based Vision-Language-Action policies suffer from the 'Euclidean Fallacy' by representing SE(3) poses as flat R^12 vectors, which causes manifold drift, broken equivariance, and non-geodesic trajectories. (confidence: 1.00)
  Evidence: Diffusion-based Vision-Language-Action policies achieve remarkable success in robotic manipulation, yet commit a fundamental geometric error we term the \textbf{Euclidean Fallacy}: representing SE(3) poses as flat $\mathbb{R}^{12}$ vectors. This approximation induces (1) manifold drift violating SO(3) constraints, (2) broken equivariance under coordinate transformations, and (3) non-geodesic trajectories with excessive kinematic cost. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_01847/source.tex

## Thinking with Imagination: Agentic Visual Spatial Reasoning with World Simulators

`thinking-with-imagination` | authors: Chenming Zhu, Jingli Lin, Yilin Long, Peizhou Cao, Tai Wang, Jiangmiao Pang, Xihui Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Threading Optimization for Vision-Language-Action Model Inference in Low-Cost Smart Agricultural Manipulation

`2606_00966` | authors: Keith Truongcao, Christopher Nhu, Zijian An, Phong Nguyen, Siwei Cai, Lifeng Zhou | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors present a system-level implementation of the Real-Time Action Chunking (RTAC) algorithm, optimizing the threading for the policy inference and control pipeline to reduce latency. (confidence: 1.00)
  Evidence: In this work, we present a complete system-level implementation of RTAC tailored for a low-cost robotic manipulation system. We advance beyond the original high-level pseudocode by optimizing the threading implementation for the policy inference and control pipeline [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- The proposed hardware platform includes a Fairino FR5 manipulator, a dual camera setup, and a teleoperation interface using the open-source GELLO framework with 3D-printed hardware. (confidence: 1.00)
  Evidence: We introduce an accessible, low-cost hardware platform that includes the FR5 manipulator, dual camera setup, and a teleoperation interface utilizing the open-source GELLO framework alongside 3D-printed hardware [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- The inference thread uses a PaliGemma LoRA, fine-tuned on data from a custom 3D-printed GELLO teleoperation arm, paired with a pi_0 Action Expert to generate action chunks. (confidence: 1.00)
  Evidence: This thread runs a PaliGemma LoRA (fine-tuned on data from our custom 3D-printed GELLO teleoperation arm that mirrors the FR5) paired with the $\pi_{0}$ Action Expert to generate action chunks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- The system utilizes an Action Broker in the Execution Thread to supply individual 7D actions to the robotic arm. (confidence: 1.00)
  Evidence: The action chunks are sent to the Action Broker in the Execution Thread, which feeds actions to the FR5 robotic arm. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex

### Claim

- The custom threading implementation significantly improves control stability and speed compared to the base implementation of RTAC. (confidence: 1.00)
  Evidence: Experimental results demonstrate that our custom threading implementation significantly improves control stability and speed compared to the base implementation of RTAC. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- The improved implementation enables faster manipulation of agricultural produce, specifically garlic bulbs and walnuts, compared to baseline control schemes. (confidence: 1.00)
  Evidence: We demonstrate that our improved implementation enables the manipulation of agricultural produce (specifically garlic bulbs and walnuts) faster than baseline control schemes, which validates the stability of our approach. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex

### Limitation

- Vision-Language Action (VLA) models are limited by slow inference speeds and difficulties in performing fine-grained motion adjustments. (confidence: 1.00)
  Evidence: Vision-Language Action (VLA) models continue to face challenges such as slow inference speed and difficulty performing fine-grained motion adjustments, limiting their widespread adoption in industry. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- Naive threading implementations of RTAC suffer from a lack of true parallelism, race conditions, and thread locking. (confidence: 1.00)
  Evidence: Naive threading implementations based on the provided pseudocode suffer from not being able to achieve true parallelism, race conditions, and thread locking, which can reintroduce the jitter and latency that RTAC was designed to remove. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- The Python Global Interpreter Lock (GIL) enforces serialized execution, impeding real-time responsiveness in Python-based VLA deployments. (confidence: 1.00)
  Evidence: In particular, the Python Global Interpreter Lock (GIL) as noted by Mitchell et al. \cite{lim2023python}, enforces serialized execution, which can impede real-time responsiveness. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex
- Most VLA architectures based on large transformer backbones operate in the 3–10 Hz range, creating a bandwidth mismatch with industrial robot controllers requiring 500 Hz or above. (confidence: 1.00)
  Evidence: Most VLA architectures, based on large transformer backbones, operate in the 3–10 Hz range \cite{kim2024openvla}, creating a significant bandwidth mismatch with industrial robot controllers that require hard real-time inputs at 500 Hz or above. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_00966/source.tex

## Towards Customized Multimodal Role-Play

`2605_08129` | authors: Chao Tang, Jianzong Wu, Qingyu Shi, Ye Tian, Aixi Zhang, Hao Jiang, Jiangning Zhang, Yunhai Tong | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/Tangc03/UniCharacter

### Method

- The authors propose UniCharacter, a two-stage training framework consisting of Unified Supervised Finetuning (Unified-SFT) and character-specific group relative policy optimization (Character-GRPO). (confidence: 1.00)
  Evidence: Building on a unified model, we devise UniCharacter, a two-stage training framework containing Unified Supervised Finetuning (Unified-SFT) and character-specific group relative policy optimization (Character-GRPO). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex
- The Character-GRPO training stage is applied to text-to-image generation and uses rewards for text-image alignment, group diversity, and a penalty for similarity to training images to enhance output diversity. (confidence: 1.00)
  Evidence: By using rewards for text-image alignment, group diversity, and a penalty for similarity to training images, our Character-GRPO training stage effectively enhances the diversity of model outputs in image generation tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex
- The authors introduce Customized Multimodal Role-Play (CMRP), a task that adapts a general-purpose multimodal model into a virtual character using minimal character-specific data to generate in-character responses and appearance-consistent images. (confidence: 1.00)
  Evidence: To address this gap, we introduce Customized Multimodal Role-Play (CMRP), a task that adapts a general-purpose multimodal model into a virtual character using minimal character-specific data—a textual profile, a few reference images, and example dialogues—to generate in-character responses and appearance-consistent images for interactive role-play with a stable persona and visual identity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex

### Dataset

- The authors introduce the RoleScape-20 dataset, comprising 20 characters with training and evaluation data covering persona, stylistic descriptions, visual/expressive cues, and text-image interactions. (confidence: 1.00)
  Evidence: We construct the RoleScape-20 dataset comprising 20 characters, including training and evaluation data that cover persona, stylistic descriptions, visual/expressive cues, and text–image interactions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex
- The RoleScape-20 dataset includes 20 diverse characters, each with a textual profile, 5-15 reference images, 150-250 role-playing dialogues, and fine-grained multimodal annotations. (confidence: 1.00)
  Evidence: It has 20 diverse characters, each with a textual profile, 5--15 reference images, and 150--250 role-playing dialogues. We also provide fine-grained multimodal annotations, including explicit thinking processes, image-generation instructions, and paired visual or knowledge-based QA samples. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex

### Claim

- Given only 10 images and corresponding interaction examples, the UniCharacter model can acquire the target character and exhibit coherent persona, style, and visual identity in both text and images in about 100 GPU hours. (confidence: 1.00)
  Evidence: Given only 10 images plus corresponding interaction examples, the model acquires the target character and exhibits coherent persona, style, and visual identity in both generated text and images. This process takes about 100 GPU hours. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex
- Experiments on the RoleScape-20 dataset show that the proposed UniCharacter method substantially outperforms prior approaches. (confidence: 1.00)
  Evidence: Experiments on the RoleScape-20 dataset show that the proposed method substantially outperforms prior approaches. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_08129/source.tex

## Towards Precise Intent-Aligned VLA Aerial Navigation via Expert-Guided GRPO

`2606_02313` | authors: Tianyang Chen, Wenjun Li, Xin zhou, Yuze Wu, Fei Gao | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes EG-GRPO (Expert-Guided Group Relative Policy Optimization) to augment online rollouts with few-shot expert data. (confidence: 1.00)
  Evidence: we propose EG-GRPO (Expert-Guided Group Relative Policy Optimization) to augment online rollouts with few-shot expert data. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/summary.md
- A heterogeneous pipeline was designed to enable parallel simulation and inference, reducing rollout time by 43.5%. (confidence: 1.00)
  Evidence: we design a heterogeneous pipeline enabling parallel simulation and inference, which reduces rollout time by 43.5%. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/summary.md
- The framework utilizes OpenVLA-OFT as the foundation model and constrains its action output to 4-DoF pose control commands via a masking function. (confidence: 1.00)
  Evidence: We select OpenVLA-OFT~\cite{kim2025fine} as the foundation model due to its strong capabilities and framework compatibility. To adapt it for UAV navigation, we constrain the original action output via a masking function $\mathcal{M}(\cdot)$, filtering out irrelevant degrees of freedom and restricting the output to the 4-DoF pose control commands [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/source.tex
- The observation space for the VLA policy includes the current RGB observation, the initial RGB observation, and the current proprioceptive state. (confidence: 1.00)
  Evidence: o_t = (o_t^{\mathrm{vis}}, o_0^{\mathrm{vis}}, o_t^{\mathrm{prop}}) 
consists of the current RGB observation o_t^{\mathrm{vis}}, the initial RGB observation o_0^{\mathrm{vis}}, 
and the current proprioceptive state o_t^{\mathrm{prop}} = [x_t, y_t, z_t, \psi_t] [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/source.tex

### Claim

- EG-GRPO improves the success rate to 2.13 times that of the SFT baseline and improves intent alignment performance by 60.9%. (confidence: 1.00)
  Evidence: EG-GRPO improves the success rate to 2.13x that of the SFT baseline, while improving intent alignment performance by 60.9%. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/summary.md

### Limitation

- Standard supervised fine-tuning (SFT) for Vision-Language-Action models suffers from data scarcity, limited generalization, and weak supervision for nuanced human intents. (confidence: 1.00)
  Evidence: standard supervised fine-tuning (SFT) suffers from data scarcity, limited generalization, and weak supervision for nuanced and complicated human intents. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_02313/source.tex

## TraRA: Trajectory-level Recognition Aggregation for Video Text Spotting in Urban Surveillance

`trara` | authors: Duc Tri Tran, Trung Thanh Nguyen, Vijay John, Phi Le Nguyen, Yasutomo Kawanishi | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/trid2912/TraRA

### Method

- TraRA is a plug-and-play method for video text recognition that integrates Temporal Clustering (TC) and Vision-Language Aggregation (VLA) modules to leverage temporal and multimodal consistency. (confidence: 1.00)
  Evidence: we propose TraRA (Trajectory-level Recognition Aggregation for VTS), a plug-and-play method that performs trajectory-level text recognition by leveraging temporal and multimodal consistency. TraRA integrates two key modules: (1) the Temporal Clustering and (2) the Vision-Language Aggregation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md
- The Temporal Clustering module refines noisy trajectories by grouping temporally and visually coherent text instances. (confidence: 1.00)
  Evidence: The former refines noisy trajectories by grouping temporally and visually coherent text instances [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md
- The Vision-Language Aggregation module employs a Low-Rank Adaptation-enhanced Vision-Language model to fuse visual cues with linguistic context across frames. (confidence: 1.00)
  Evidence: while the latter employs a Low-Rank Adaptation-enhanced Vision-Language model to fuse visual cues with linguistic context across frames. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md
- The Vision-Language Aggregation module leverages the Ovis2.5 Vision-Language Model for VTS due to its strong vision-language alignment and robust temporal reasoning capabilities. (confidence: 1.00)
  Evidence: we leverage Ovis2.5~\cite{lu2025ovis2} for VTS, given its strong vision-language alignment and robust temporal reasoning capabilities [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/source.tex
- The Temporal Clustering algorithm extracts visual features from masked text crops using HOG, SIFT, and area, and computes an adaptive distance threshold based on the mean feature variation within the tracklet. (confidence: 1.00)
  Evidence: Extract features for each crop:
        \State \hspace{20pt} $\mathbf{X}_i = [\, f_{\text{HOG}} ;\, f_{\text{SIFT}} ;\, A_i \,]$, $i = \{1,\dots,n\}$
        \State Compute pairwise feature distances
        \State \hspace{20pt} $d_i = \|\mathbf{X}_{i+1} - \mathbf{X}_i\|_2$, $i = \{1,\dots,n{-}1\}$, 
        \State \hspace{20pt} to obtain $D = [d_1, d_2, \dots, d_{n-1}]$
        \State Compute adaptive threshold $\tau = \max(\alpha \cdot \mathrm{mean}(D),\, \beta)$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/source.tex

### Benchmark

- TraRA was evaluated on four public benchmarks, including road and urban scene datasets: RoadText, BOVText, ArTVideo, and ICDAR15. (confidence: 1.00)
  Evidence: Extensive experiments on four public benchmarks, including road and urban scene datasets (RoadText, BOVText, ArTVideo, and ICDAR15) [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md

### Claim

- TraRA consistently improves tracking and recognition performance over state-of-the-art VTS methods on four public benchmarks. (confidence: 1.00)
  Evidence: demonstrate that TraRA consistently improves tracking and recognition performance over state-of-the-art VTS methods. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md

### Limitation

- Existing VTS methods typically perform recognition independently on each frame, which leads to inconsistent and inaccurate results across sequences. (confidence: 1.00)
  Evidence: Existing VTS methods typically perform recognition independently on each frame, leading to inconsistent and inaccurate results across sequences. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/summary.md
- Excessive simulation of severe video conditions in synthetic datasets forces recognition models to learn from text that is often unrecognizable even to humans. (confidence: 1.00)
  Evidence: Excessive simulation of severe video conditions forces recognition models to learn from text that is often unrecognizable even to humans. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/trara/source.tex

## Tracing the Oracle: Improving Diffusion Timestep Scheduling for 3D CT Reconstruction

`tracing-the-oracle` | authors: Yujia Wu, Zhaoqiang Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes Tracing the Oracle (TrO), a plug-and-play framework for improved timestep scheduling in 3D CT reconstruction. (confidence: 1.00)
  Evidence: To overcome this limitation, we propose Tracing the Oracle (TrO), a plug-and-play framework for improved timestep scheduling. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- TrO uses densely sampled numerical integration trajectories on a few samples as a reference oracle. (confidence: 1.00)
  Evidence: Specifically, we treat densely sampled numerical integration trajectories on a few samples as the reference oracle. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- The optimized timestep schedule is extracted using dynamic programming to globally minimize the cumulative error between the few-step approximation and the oracle. (confidence: 1.00)
  Evidence: The optimized schedule is extracted by leveraging dynamic programming to globally minimize the cumulative error between the few-step approximation and the oracle. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- The framework introduces a noise reuse mechanism to isolate deterministic truncation errors from stochastic variance, enabling precise quantification of discretization errors in SDE-based sampling. (confidence: 1.00)
  Evidence: We introduce a noise reuse mechanism that isolates deterministic truncation errors from stochastic variance, enabling precise quantification of discretization errors within SDE-based sampling trajectories. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- The proposed framework formulates timestep scheduling for measurement-conditioned diffusion as a discrete shortest-path problem. (confidence: 1.00)
  Evidence: We propose a plug-and-play framework that formulates timestep scheduling for measurement-conditioned diffusion as a discrete shortest-path problem, aiming to minimize cumulative trajectory errors in 3D inverse problems. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex

### Dataset

- The experiments in the paper are conducted on the AAPM dataset across multiple 3D CT reconstruction tasks. (confidence: 1.00)
  Evidence: Our extensive experiments on the AAPM dataset across multiple 3D CT reconstruction tasks demonstrate that... [artifact:summary]

### Claim

- When combined with the DDS 3D CT reconstruction method, the optimized timesteps from TrO significantly improve reconstruction fidelity and computational efficiency compared to heuristic schedules, especially with 10 or fewer sampling steps. (confidence: 1.00)
  Evidence: ...when combined with the state-of-the-art 3D CT reconstruction method DDS, our optimized timesteps significantly improve reconstruction fidelity and computational efficiency compared to existing heuristic schedules, especially under a strict budget of no more than 10 sampling steps. [artifact:summary]

### Limitation

- Existing uniform timestep schedules fail to capture the non-uniform evolution of the reverse conditional diffusion stochastic differential equation, which introduces substantial truncation errors. (confidence: 1.00)
  Evidence: Furthermore, existing uniform timestep schedules fail to capture the non-uniform evolution of the reverse conditional diffusion stochastic differential equation, thereby introducing substantial truncation errors. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- The inference process of pretrained diffusion models for solving 3D CT inverse problems suffers from significant computational overhead. (confidence: 1.00)
  Evidence: Pretrained diffusion models demonstrate impressive potential in solving highly ill-posed 3D computed tomography (CT) inverse problems, while the inference process suffers from significant computational overhead. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/tracing-the-oracle/source.tex
- Unconditional scheduling algorithms are ineffective for complex conditional inverse solvers because achieving data consistency requires injecting stochastic noise, invalidating deterministic trajectory assumptions. (confidence: 1.00)
  Evidence: Furthermore, achieving data consistency in inverse problems typically requires injecting stochastic noise during the reverse refinement process, which invalidates the deterministic trajectory assumptions relied upon by unconditional scheduling algorithms, rendering them ineffective for complex conditional inverse solvers. [artifact:source_tex]

## Turning Video Models into Generalist Robot Policies

`2605_27817` | authors: Sizhe Lester Li, Evan Kim, Xingjian Bai, Tong Zhao, Tao Pang, Max Simchowitz, Vincent Sitzmann | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes the Video-to-Embodied Robot Action Model (VERA), a closed-loop policy that decouples an action-free video world model from an embodiment-specific inverse dynamics model (IDM) based on the robot embodiment Jacobian. (confidence: 1.00)
  Evidence: We present a closed-loop, video-to-action policy that combines an action-free video world model with a carefully-designed IDM based on the robot embodiment Jacobian. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/summary.md
- The proposed inverse dynamics model, termed Jacobian IDM (J-IDM), translates visual plans into low-level action chunks by inverting the robot embodiment Jacobian. (confidence: 1.00)
  Evidence: The Jacobian IDM inverts each step of this path into a chunk of low-level actions. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

### Dataset

- The DROID dataset is used to train the model for zero-shot evaluation on a real-world Panda arm. (confidence: 1.00)
  Evidence: After training on DROID~\cite{khazatsky2024droid}, we deploy zero-shot on a Panda in an unseen scene with ad-hoc camera placements [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

### Benchmark

- The method is evaluated on simulated benchmarks including Allegro-Sim, Panda-Sim (MimicGen), PushT-Sim, and a 5-joint fingers environment. (confidence: 1.00)
  Evidence: \jidm{} achieves the lowest MSE on Allegro-Sim, PushT-Sim, and 5-joint fingers, and remains competitive on Panda-Sim. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

### Claim

- Decoupling the video planner from the inverse dynamics model allows the planner to remain embodiment-agnostic, enables easy interchangeability of video models, and allows the IDM to be trained independently with self-play data. (confidence: 1.00)
  Evidence: This decoupling offers several natural benefits: the video planner remains embodiment-agnostic, different video models can be interchanged easily without re-training the IDM, and the IDM can be independently trained with readily available self-play data. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/summary.md
- The Jacobian IDM design is data-efficient and scales effectively to high-dimensional action spaces. (confidence: 1.00)
  Evidence: We demonstrate that our IDM design is both data-efficient and scalable to high-dimensional action spaces. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/summary.md
- J-IDM achieves higher closed-loop success rates than a UniPi-style direct inverse-dynamics baseline across planar pushing, 7-DoF arm manipulation, and 16-DoF dexterous manipulation tasks. (confidence: 1.00)
  Evidence: \jIDM{} yields higher closed-loop success than a UniPi*-style direct inverse-dynamics baseline~\citep{du2023learning} across planar pushing, 7-DoF arm manipulation, and 16-DoF dexterous manipulation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

### Limitation

- Using overly long action chunks before replanning can degrade performance due to reduced feedback frequency, particularly when contact or visual tracking errors accumulate. (confidence: 1.00)
  Evidence: However, overly long chunks reduce feedback frequency and can hurt performance, especially when contact or visual tracking errors accumulate. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_27817/source.tex

## Uncovering Vulnerability of Vision-Language-Action Models under Joint-Level Physical Faults

`2606_10501` | authors: Minsoo Jo, Taeju Kwon, Junha Chun, Youngjoon Jeong, Taesup Kim | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/gakakulicc/RobustVLA

### Method

- The Joint-level Physical-fault Aware Residual Calibrator (J-PARC) is a lightweight residual calibration framework designed to be built on top of a frozen VLA policy. (confidence: 1.00)
  Evidence: Motivated by these findings, we propose Joint-level Physical-fault Aware Residual Calibrator (J-PARC), a lightweight residual calibration framework built on top of a frozen VLA policy. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex
- J-PARC infers a latent joint-fault regime from recent joint dynamics and uses it to condition a shared residual calibrator, which enables adaptive action correction across faulty joints. (confidence: 1.00)
  Evidence: J-PARC infers a latent joint-fault regime from recent joint dynamics and conditions a shared residual calibrator on this regime, enabling adaptive action correction across faulty joints. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex
- The study investigates specific joint-level physical faults, including joint lock, limited range of motion, and increased joint friction. (confidence: 1.00)
  Evidence: In this work, we study joint-level physical faults including joint lock, limited range of motion~\cite{lock,lock2,lock3}, and increased joint friction [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex

### Benchmark

- The LIBERO benchmark is used to evaluate the success rates of VLA models under joint fault conditions. (confidence: 1.00)
  Evidence: LIBERO benchmark evaluation results under joint fault. Success rates (%) averaged over LIBERO~\cite{libero} suites. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex

### Claim

- Vision-Language-Action (VLA) models exhibit vulnerability to joint-level physical faults when their predicted actions are executed through a perturbed robot body. (confidence: 1.00)
  Evidence: In this work, we study realistic joint-level physical faults and show that VLA models are vulnerable when predicted actions are executed through a perturbed robot body. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex
- Joint-level physical faults produce joint-dependent effects, resulting in heterogeneous degradation in task success rates across the affected joints. (confidence: 1.00)
  Evidence: Our analysis reveals joint-dependent effects, with heterogeneous degradation in task success across affected joints. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex
- Performance degradation in VLA models under joint-level faults is not solely due to physical infeasibility, as physically feasible faults like increased joint friction can still significantly reduce success rates and cause closed-loop execution mismatch. (confidence: 1.00)
  Evidence: We also show that performance drops cannot be attributed solely to physical infeasibility, since feasible faults such as increased joint friction can still substantially reduce success rates and induce closed-loop execution mismatch. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex
- Experimental results demonstrate that J-PARC improves robustness under joint-level faults while maintaining performance in fault-free environments. (confidence: 1.00)
  Evidence: Experiments show that J-PARC improves robustness under joint-level faults while preserving fault-free environment performance. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_10501/source.tex

## UniCompress: Token Compression for Unified Vision-Language Understanding and Generation

`unicompress` | authors: Ziyao Wang, Chen Chen, Jingtao Li, Weiming Zhuang, Jiabo Huang, Ang Li, Lingjuan Lyu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit

### Method

- UniCompress introduces a plug-in compression and decompression mechanism guided by learnable global meta tokens to reduce visual token count. (confidence: 1.00)
  Evidence: Our method introduces a plug-in compression and decompression mechanism guided with learnable global meta tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- UniCompress uses a compressor to convert a dense token grid into a short sequence of compressed tokens augmented by learnable global meta tokens, and a global-guided decompressor to reconstruct the token grid. (confidence: 1.00)
  Evidence: {\n} inserts two lightweight modules around an off-the-shelf discrete tokenizer: (i) a \emph{compressor} that converts a dense \(H\times W\) token grid into a short sequence of compressed tokens \emph{augmented by a small set of learnable global meta tokens} capturing holistic semantics; and (ii) a \emph{global-guided decompressor} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- The training process for UniCompress involves two stages: first training the tokenizer with the compression modules using a reconstruction loss, and then freezing the tokenizer to mildly finetune the language model. (confidence: 1.00)
  Evidence: Training is done in two stages: we first train the tokenizer with {\n} modules with a reconstruction loss; then we freeze the compressed tokenizer and mildly finetune the LLM model. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- UniCompress augments the visual tokenizer with a global-token extractor that uses one-way cross-attention to summarize scene-level semantics, a pooling-based compressor, and an autoregressive decompressor. (confidence: 1.00)
  Evidence: {\n} augments the visual tokenizer with three lightweight modules while keeping the LLM unchanged: a global-token extractor that uses one-way cross-attention to summarize scene-level semantics; a pooling-based compressor that reshapes the token grid and aggregates non-overlapping patches [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex

### Claim

- Naive downsampling or uniform token pruning degrades image generation performance by more than 15%, despite being effective for image understanding. (confidence: 1.00)
  Evidence: experimental results demonstrate that \textbf{naïve downsampling or uniform token pruning, while effective for image understanding, significantly degrades generation performance by more than 15\%}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- UniCompress reduces visual tokens by up to 4 times while keeping performance degradation to a maximum of 3 points on understanding tasks and a 5-point FID increase on generation tasks. (confidence: 1.00)
  Evidence: On standard understanding and generation benchmarks, {\n} reduces visual tokens by \(4\times\) (for example, \(256\rightarrow64\)) 
while keeping performance within small margins ($\leq$ 3-pt drop on understanding; $\leq$ 5-pt FID increase on generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex
- Compared to uncompressed baselines, UniCompress achieves up to 41.8% lower inference latency and 15.4% shorter training time. (confidence: 1.00)
  Evidence: Relative to uncompressed baselines, {\n} yields up to 41.8\% lower inference latency and 15.4\% shorter training time, together with substantial latency savings from shorter sequences. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex

### Limitation

- The large number of visual tokens in unified models causes substantial computation and memory overhead, limiting deployment in resource-constrained scenarios like embodied AI. (confidence: 1.00)
  Evidence: However, the large number of visual tokens required by such models introduces substantial computation and memory overhead, and this inefficiency directly hinders deployment in resource constrained scenarios such as embodied AI systems. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/unicompress/source.tex

## Unifying Object-Centric World Models and Diffusion Policy: A Hierarchical Framework for Multi-Stage Robotic Tasks

`2606_08775` | authors: Raktim Gautam Goswami, Prashanth Krishnamurthy, Yann LeCun, Farshad Khorrami | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/goodfeli/dlbook_notation

### Method

- The paper introduces WorldDP, a hierarchical framework that uses a high-level world model to optimize feasible subgoals during runtime, which are then executed by a low-level Diffusion Policy. (confidence: 1.00)
  Evidence: In this work, we introduce WorldDP, a world model framework designed for multi-stage robotic manipulation. Our hierarchical approach utilizes a high-level world model as a transition function to optimize for feasible subgoals during runtime, which are subsequently reached by a low-level Diffusion Policy. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- WorldDP incorporates object-centric representations to decouple environmental entities, enabling sequential planning with respect to each entity. (confidence: 1.00)
  Evidence: To further aid in learning dynamics and planning, we incorporate object-centric representations that decouple environmental entities and enable us to plan sequentially with respect to each. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- The object-centric state representation leverages DINOv2 patch-level features guided by SAM2-generated segmentation masks during training. (confidence: 1.00)
  Evidence: We present an object-centric state representation for latent world models that leverages DINOv2 patch-level features guided by SAM2-generated segmentation masks during training. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- The framework employs object-aware planning by incorporating a contact predictor and particle filter optimization to enhance subgoal generation. (confidence: 1.00)
  Evidence: We present the first world model approach to employ object-aware planning, incorporating a contact predictor and particle filter optimization to enhance subgoal generation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- A low-level, goal-conditioned diffusion policy sequentially tracks and executes the subgoals optimized by the object-centric world model. (confidence: 1.00)
  Evidence: A low-level, goal-conditioned diffusion policy (DP) then sequentially tracks and executes these subgoals to solve the task. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- The framework uses multi-modal optimization via a Particle Filter instead of the Cross-Entropy Method (CEM) because robotic tasks are inherently multi-modal. (confidence: 1.00)
  Evidence: Finally, while most world-model-based planning relies on optimization techniques like the Cross-Entropy Method (CEM), we find that multi-modal optimization via a Particle Filter is superior, as robotic tasks are inherently multi-modal [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex

### Benchmark

- The approach is evaluated on several multi-stage tasks from the OGBench benchmark. (confidence: 1.00)
  Evidence: We evaluate our approach on several multi-stage tasks from the OGBench \citep{park2025ogbench} benchmark, demonstrating that it outperforms existing world models, diffusion policies, and diffusion-based subgoal generation baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex

### Claim

- WorldDP consistently outperforms existing baselines across several robotics benchmarks, showing that coupling the world model's physically grounded planning with diffusion policy's efficient execution yields superior multi-stage performance. (confidence: 1.00)
  Evidence: Evaluated across several robotics benchmarks, WorldDP consistently outperforms existing baselines, validating that coupling the world model's physically grounded planning with diffusion policy's efficient execution yields superior multi-stage performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex

### Limitation

- Existing visual world models applied to robotics are limited to single-stage tasks such as reaching or grasping, and struggle with multi-stage tasks that require complex sequential planning. (confidence: 1.00)
  Evidence: When applied to robotics, however, they are limited to single-stage tasks such as reaching or grasping, and struggle with multi-stage ones that demand complex sequential planning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex
- Patch-level features from large-scale encoders are suboptimal for state representation in dynamics learning because they often omit critical fine-grained details. (confidence: 1.00)
  Evidence: While effective for computer vision tasks like segmentation, these patch-level features are suboptimal for state representation for dynamics learning as they often omit critical fine-grained details. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08775/source.tex

## VISTA: Vision-Grounded and Physics-Validated Adaptation of UMI data for VLA Training

`vista` | authors: Siyuan Yang, Linzheng Guo, Ouyang Lu,  Zhaxizhuoma, Daoran Zhang, Xinmiao Wang, Ting Xiao, Fangzheng Yan, Zhijun Chen, Yan Ding, Chao Yu, Chenjia Bai, Xuelong Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/TeleHuman/umi-vista

### Method

- VISTA is a framework that adapts UMI data for VLA training through three synergistic components: UMI-VQA for perceptual alignment, a physical-validation pipeline, and a two-stage co-training recipe. (confidence: 1.00)
  Evidence: To address the challenges, we present VISTA, a framework that bridges this dual gap through three synergistic components. (i)~UMI-VQA, the first large-scale VQA dataset tailored to wrist-mounted fisheye observations, aligns VLM representations to the distorted visual regime via auxiliary vision-language supervision. (ii)~A systematic physical-validation pipeline performs a data-completeness pre-check and scores each valid trajectory for trajectory continuity, self-collision risk, and execution fidelity before it enters training. (iii)~A two-stage co-training recipe jointly learns vision-language grounding on UMI-VQA and action prediction on validated trajectories. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/summary.md
- The physical-validation pipeline audits entire trajectories for kinematic reachability and smoothness, self-collision checks, and controller tracking-feasibility before they enter VLA training. (confidence: 1.00)
  Evidence: Unlike coarse per-pose filtering, our validation audits entire trajectories along three dimensions: trajectory-level kinematic reachability and smoothness, self-collision checks, and controller tracking-feasibility analysis. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/source.tex
- VISTA employs a two-stage co-training recipe where the first stage performs joint autoregressive learning on UMI-VQA and discrete action tokens, and the second stage refines continuous control generation using a flow-matching action expert. (confidence: 1.00)
  Evidence: Stage one performs joint autoregressive learning on large-scale UMI-VQA and validated UMI discrete action token to establish aligned vision-language-action representations. Stage two refines continuous control generation via a flow-matching action expert [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/source.tex

### Dataset

- UMI-VQA is the first large-scale VQA dataset tailored to wrist-mounted fisheye observations, containing 8 million question-answer pairs. (confidence: 1.00)
  Evidence: we construct \textbf{UMI-VQA}, which is, to our knowledge, the \emph{first} large-scale vision-language dataset tailored to wrist-mounted fisheye observations. UMI-VQA contains 8M question-answer pairs [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/source.tex

### Benchmark

- VISTA is evaluated on UMI-style simulation benchmarks, including RoboTwin-UMI and LIBERO-UMI, as well as 20 diverse real-world manipulation tasks. (confidence: 1.00)
  Evidence: We fine-tune and evaluate VISTA on UMI-style simulation benchmarks, including RoboTwin-UMI and LIBERO-UMI, as well as 20 diverse real-world manipulation tasks. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/source.tex

### Claim

- VISTA significantly outperforms strong baselines including pi_0.5, LingBot-VLA, and Wall-X on diverse simulation and real-world manipulation tasks. (confidence: 1.00)
  Evidence: On diverse simulation and real-world manipulation tasks, VISTA significantly outperforms strong baselines including $\pi_{0.5}$, LingBot-VLA, and Wall-X. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/summary.md
- Physical-validation scores are strongly predictive of deployment success, with higher scores generally corresponding to better deployment outcomes. (confidence: 1.00)
  Evidence: physical-validation scores are strongly predictive of deployment success. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/summary.md

### Limitation

- Wrist-mounted fisheye views with severe radial distortion and local gripper-centric perspectives are out-of-distribution for pretrained VLMs, creating a visual grounding mismatch. (confidence: 1.00)
  Evidence: wrist-mounted fisheye views, with severe radial distortion and local gripper-centric perspectives, are out-of-distribution for pretrained VLMs [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/summary.md
- Human-collected UMI trajectories frequently violate kinematic limits, incur collisions, or exceed controller bandwidth, which teaches VLA policies physically infeasible actions. (confidence: 1.00)
  Evidence: human-collected trajectories frequently violate kinematic limits, incur collisions, or exceed controller bandwidth, teaching VLA policies physically infeasible actions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/vista/summary.md

## VeriSpace: Spatially Grounded Action Verification for Vision-Language-Action Models

`verispace` | authors: Guiyu Zhao, Longteng Guo, Junyou Zhu, Jun Fu, Yanghong Mei, Bin Cao, Jie Jiang, Xingjian He, Jing Liu | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Vision Language Model Helps Private Information De-Identification in Vision Data

`2606_09132` | authors: Tiejin Chen, Pingzhi Li, Kaixiong Zhou, Tianlong Chen, Hua Wei | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/tiejin98/VLM_Deidentification

### Method

- The authors introduce VisShield (Vision Privacy Shield), an end-to-end framework designed to enhance the privacy awareness of Vision Language Models (VLMs) for de-identifying visual data. (confidence: 1.00)
  Evidence: To address this issue, we introduce VisShield (Vision Privacy Shield), an end-to-end framework designed to enhance the privacy awareness of VLMs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex
- The training methodology involves fine-tuning the pre-trained VLM Kosmos-2.5 on the OPTIC dataset to enable accurate processing and bounding box localization of sensitive text. (confidence: 1.00)
  Evidence: We fine-tuned a pre-trained VLM, \texttt{Kosmos-2.5}~\cite{lv2023kosmos} on the OPTIC dataset to enable the VLM to process sensitive text accurately. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex

### Dataset

- The framework utilizes OPTIC (Optical Privacy Text Instruction Collection), a specialized instruction-tuning dataset comprising 50 million synthetic image-text pairs with embedded fake private information to teach VLMs how to handle privacy-sensitive textual elements. (confidence: 1.00)
  Evidence: A specialized instruction-tuning dataset OPTIC~(Optical Privacy Text Instruction Collection) designed to teach VLMs how to handle privacy-sensitive textual elements. ... Our dataset comprises 50M samples, providing a rich training resource for localizing sensitive text. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex

### Claim

- The VisShield framework significantly outperforms existing approaches in handling and de-identifying private information in vision data. (confidence: 1.00)
  Evidence: Extensive experiments demonstrate that our framework significantly outperforms existing approaches in handling private information [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex

### Limitation

- The model's effectiveness is dependent on the quality and diversity of the instruction-tuning dataset, meaning rare or highly domain-specific private information formats may still pose challenges for de-identification. (confidence: 1.00)
  Evidence: First, the model's effectiveness depends on the quality of the instruction-tuning dataset, and while we have ensured diversity, rare or highly domain-specific private information formats may still pose challenges. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex
- The proposed method relies on OCR accuracy for text extraction, so errors in detecting or recognizing text in low-quality or distorted images could negatively impact the de-identification performance. (confidence: 1.00)
  Evidence: Second, our method relies on OCR accuracy for text extraction, meaning that errors in detecting or recognizing text in low-quality or distorted images could affect de-identification performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09132/source.tex

## Vision-Language Asymmetry in Bistable Image Captioning

`2606_08031` | authors: Arohan Agate | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The study establishes a behavioral baseline of 3,320 generations over 83 bistable stimuli to identify three regimes (default-dominant, force-dominant, force-balanced) under neutral versus forced-choice prompting. (confidence: 1.00)
  Evidence: We address this with a 3,320-generation behavioral baseline over 83 bistable stimuli that surfaces three regimes (default-dominant, force-dominant, force-balanced) under neutral vs forced-choice prompting... [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex
- The authors trained a TopK sparse autoencoder on the CLIP layer consumed by LLaVA-1.6-7B to probe underlying representations, achieving a validation explained variance of 0.93. (confidence: 1.00)
  Evidence: ...probe the underlying representations using a TopK sparse autoencoder we train on the CLIP layer that LLaVA-1.6-7B actually consumes (validation EV 0.93). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex

### Dataset

- The study utilizes a dataset of 83 bistable stimuli comprising 29 Panagopoulou benchmark images, 53 AmbiBench bistable images, and 1 programmatically rendered Necker cube. (confidence: 1.00)
  Evidence: The full bistable stimulus set (\cref{sec:methods}) contains 83 images: 29 Panagopoulou benchmark images \citep{panagopoulou2024aspect}, 53 \textsc{AmbiBench} bistable images \citep{ambibench2026}, and 1 programmatically rendered Necker cube. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex
- Pure-aspect control images were either generated using SDXL for photographic groups or created programmatically for geometric groups, and all were hand-verified by the authors to ensure the non-target aspect was not visible. (confidence: 1.00)
  Evidence: Pure-aspect controls are SDXL-generated for the photographic groups (\texttt{duck\_rabbit} ducks/rabbits in pond and field settings, \texttt{young\_old\_woman} portraits, etc.) and programmatic for the geometric groups; every control image was hand-verified by the authors and rejected if the non-target aspect was visible or the subject was ambiguous. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex

### Claim

- In 72% (50 out of 69) of bistable stimuli with available per-aspect feature pools, both pools show simultaneous activation at the vision tower. (confidence: 1.00)
  Evidence: Across 69 bistable stimuli with both per-aspect feature pools available, 72% (50/69) show simultaneous activation of both pools at the vision tower, including 12/12 default-dominant duck/rabbit and 7/8 force-balanced young/old. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex
- Causal steering at CLIP layer 22 successfully flips captions on default-dominant stimuli but fails to flip captions on force-balanced young/old stimuli at any tested coefficient. (confidence: 1.00)
  Evidence: Causal steering at CLIP layer 22 flips captions on default-dominant stimuli (33% rabbit-flip rate under a fluency guard) but cannot flip captions on force-balanced young/old at any tested coefficient, despite their vision-side superposition. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex
- The bottleneck for aspect commitment in vision-language models is located downstream of the vision tower. (confidence: 1.00)
  Evidence: The dominance bottleneck lives downstream of the vision tower; the gap between vision-side representation and language-side commitment is an empirical handle on the seeing/seeing-as distinction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex

### Limitation

- Using stable sorting algorithms like numpy.argsort for rank-based statistics on highly sparse TopK SAE outputs introduces a silent row-order bias that creates phantom features with no real discriminative signal. (confidence: 1.00)
  Evidence: Because TopK SAE outputs are over 99% sparse, most feature columns contain mass at exactly zero. The argsort tie-break therefore systematically gave class-A samples low ranks and class-B samples high ranks on any column with no real signal, producing AUROCs near zero (interpreted as ``B-preferring'') for thousands of features that in fact had no class-discriminative behavior. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08031/source.tex

## Vision-and-Language Navigation for UAVs: Progress, Challenges, and a Research Roadmap

`2604_13654` | authors: Hanxuan Chen, Jie Zheng, Siqi Yang, Tianle Zeng, Siwei Feng, Songsheng Cheng, Ruilong Ren, Hanzhong Guo, Shuai Yuan, Xiangyue Wang, Kangli Wang, Ji Pei | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Claim

- Vision-and-Language Navigation for Unmanned Aerial Vehicles (UAV-VLN) is formally modeled as a Partially Observable Markov Decision Process (POMDP). (confidence: 1.00)
  Evidence: To establish a rigorous mathematical foundation, the UAV-VLN task is formally modeled as a Partially Observable Markov Decision Process (POMDP), the standard framework for sequential decision-making under uncertainty in robotics and embodied AI [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex
- The UAV-VLN problem is defined by a tuple consisting of unobservable world states, the agent's action space, probabilistic state transition dynamics, a reward function, possible observations, and an observation function. (confidence: 1.00)
  Evidence: The UAV-VLN problem is thus defined by the tuple $\mathcal{M} = (\mathcal{S}, \mathcal{A}, \mathcal{T}, \mathcal{R}, \Omega, \mathcal{O})$, where $\mathcal{S}$ is the set of unobservable world states, $\mathcal{A}$ is the agent's action space, $\mathcal{T}$ represents the probabilistic state transition dynamics, $\mathcal{R}$ is the reward function, $\Omega$ is the set of possible observations, and $\mathcal{O}$ is the observation function [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex
- For cooperative multi-agent scenarios in UAV-VLN, the POMDP formulation extends to a Decentralized POMDP (DEC-POMDP) to model joint actions and observations. (confidence: 1.00)
  Evidence: For cooperative multi-agent scenarios, this formulation extends to a Decentralized POMDP (DEC-POMDP) to model joint actions and observations [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex
- In UAV-VLN, the observation typically represents partial information available to the agent, usually comprising visual input from egocentric cameras, proprioceptive data from an IMU, and the natural language instruction. (confidence: 1.00)
  Evidence: In contrast, the observation $o_t \in \Omega$ represents the partial information available to the agent, typically a composite of visual input from its egocentric camera(s), proprioceptive data from an Inertial Measurement Unit (IMU), and the natural language instruction $\mathcal{L}$ [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex
- The latest frontier in UAV-VLN involves integrating generative world models with Vision-Language-Action (VLA) policies to equip agents with physical common sense and predictive capabilities. (confidence: 1.00)
  Evidence: Most notably, the latest frontier involves the deep integration of generative world models with Vision-Language-Action (VLA) policies, as seen in models like $\pi_0$, GR00T N1, and Cosmos-Reason1, which equip agents with physical common sense and predictive capabilities for robust, long-horizon reasoning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex

### Limitation

- A primary challenge in UAV-VLN is the inherent ambiguity in natural language instructions, which requires the agent to perform robust cross-modal reasoning to ground abstract descriptions onto the visual scene. (confidence: 1.00)
  Evidence: A primary challenge is the inherent ambiguity in these instructions, requiring the agent to perform robust cross-modal reasoning to ground abstract descriptions, such as occluded or implicitly referenced objects, onto the visual scene [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex
- The aerial domain in VLN introduces complex challenges such as navigating continuous 3D action spaces without predefined graphs, performing long-horizon reasoning in unstructured environments, and overcoming a severe simulation-to-reality gap. (confidence: 1.00)
  Evidence: the aerial domain introduces a distinct and more complex set of challenges... These challenges... include navigating continuous 3D action spaces without predefined graphs, performing long-horizon reasoning with complex spatial relationships in unstructured environments, and overcoming a severe simulation-to-reality gap that complicates real-world deployment [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2604_13654/source.tex

## WALL-WM: Carving World Action Modeling at the Event Joints

`wall-wm` | authors: Shalfun Li, Victor Yao, Charles Yang, Truth Qu, Regis Cheng, Ryan Yu, Howard Lu, Newton Von, Vincent Chen, Yohann Tang, Maeve Zhang, Ellie Ma, Gody Li, Sage Yang, Lorien Shu, J. W. Gao, Ethan Chen, Colin Ye, Yu Sun, Elise Mon, PS Zhang, Neo Li, Lily Li, James Wang, Ping Yang, Chris Pan, Lucy Liang, Hang Su, Roy Gan, Hao Wang, Qian Wang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/X-Square-Robot/wall-x

### Method

- WALL-WM shifts video-action learning from chunk-centric optimization to event-grounded Vision-Language-Action pretraining, using semantically coherent action events as the atomic unit of learning. (confidence: 1.00)
  Evidence: WALL-WM is a World Action Model that shifts video-action learning from chunk-centric optimization to event-grounded Vision-Language-Action pretraining, using semantically coherent action events as the atomic unit of learning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- WALL-WM supports two complementary inference modes: an event mode that consumes next-event descriptions for variable-length execution chunks, and a unified mode that uses a VLM with Staircase Decoding for fixed-length chunk inference. (confidence: 1.00)
  Evidence: From the same event-pretrained backbone, WALL-WM supports two complementary inference modes. The event mode consumes next-event descriptions and enables variable-length execution chunks, while the unified mode uses a VLM with Staircase Decoding to condition conventional fixed-length chunk inference while preserving a gradient-continuous VLA path. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- WALL-WM utilizes a data ecosystem built from event-level captions and cluster-balanced sampling to enable scalable learning over diverse behaviors, scenes, and task structures. (confidence: 1.00)
  Evidence: Specifically, it pairs event-grounded VLA pretraining with a data ecosystem built from event-level captions and cluster-balanced sampling, enabling scalable learning over diverse behaviors, scenes, and task structures. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- The pretraining infrastructure for WALL-WM is based on the Muon optimizer to support large-scale training. (confidence: 1.00)
  Evidence: Together with Muon-optimizer-based large-scale pretraining infrastructure, WALL-WM provides a practical scale-up recipe for general-purpose WAMs. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md
- In the unified inference mode, a VLM with Staircase Decoding supplies event-structured latent reasoning over task progress to guide the next local chunk while maintaining a gradient-continuous VLA path. (confidence: 1.00)
  Evidence: Unified mode supports fixed-length chunk prediction by using VLM-based Staircase Decoding to generate event-structured latent reasoning while maintaining a gradient-continuous VLA path. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/source.tex
- WALL-WM treats action-grounded semantic events as the atomic training unit, pairing them with event captions to train a video-action denoiser. (confidence: 1.00)
  Evidence: WALL-WM treats action-grounded semantic events as the atomic training unit, pairs them with event captions, and trains a video-action denoiser that preserves the inherited video prior while turning event-aligned visual evidence into executable action. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/source.tex

### Claim

- WALL-WM achieves state-of-the-art performance in large-scale real-world generalization evaluation, demonstrating broad generalization across language, scenes, and tasks. (confidence: 1.00)
  Evidence: Experiments show that WALL-WM generalizes broadly across language, scenes, and tasks, achieving state-of-the-art performance in large-scale real-world generalization evaluation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md

### Limitation

- Existing World Action Models (WAMs) that optimize fixed-length action chunks conditioned directly on current observations and instructions suffer from a fundamental granularity mismatch between language, vision, and action timescales. (confidence: 1.00)
  Evidence: Although convenient, this chunk-centric formulation creates a fundamental granularity mismatch. Language describes semantic goals and events, vision evolves through continuous scene dynamics, and actions operate at control-level timescales; forcing all three into the same fixed-length prediction window turns VLA training into short-horizon correlation fitting. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wall-wm/summary.md

## WBench: A Comprehensive Multi-turn Benchmark for Interactive Video World Model Evaluation

`wbench` | authors: Kaining Ying, Hengrui Hu, Siyu Ren, Jiamu Li, Fengjiao Chen, Ziwen Wang, Xuezhi Cao, Xunliang Cai, Henghui Ding | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/meituan-longcat/WBench

### Method

- For navigation tasks, WBench unifies text, 6-DoF pose, and discrete-action control to enable the evaluation of models with different native input interfaces. (confidence: 1.00)
  Evidence: For navigation, WBench unifies text, 6-DoF pose, and discrete-action control, enabling evaluation of models with different native input interfaces. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/summary.md
- The evaluation pipeline uses 22 automatic sub-metrics that combine specialist vision models with large multimodal models, all of which are validated against human judgments. (confidence: 1.00)
  Evidence: Evaluation uses 22 automatic sub-metrics that combine specialist vision models with large multimodal models, and all metrics are validated against human judgments. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/summary.md

### Dataset

- The WBench dataset contains 289 test cases and 1,058 interaction turns, covering diverse scenes, styles, subjects, and both first- and third-person perspectives. (confidence: 1.00)
  Evidence: WBench contains 289 test cases and 1,058 interaction turns, where each case specifies a world setting and a multi-turn interaction sequence, covering diverse scenes, styles, subjects, and both first- and third-person perspectives [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/summary.md
- WBench includes four types of interactions: navigation, subject action, event editing, and perspective switching. (confidence: 1.00)
  Evidence: together with four interaction types, including navigation, subject action, event editing, and perspective switching. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/source.tex

### Benchmark

- WBench is a comprehensive multi-turn benchmark designed for the systematic evaluation of interactive video world models across five dimensions: video quality, setting adherence, interaction adherence, consistency, and physics compliance. (confidence: 1.00)
  Evidence: we introduce WBench, a comprehensive multi-turn benchmark for interactive world model evaluation along five dimensions, namely video quality, setting adherence, interaction adherence, consistency, and physics compliance. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/summary.md

### Claim

- Across 20 state-of-the-art models evaluated on WBench, no single model performs strongly across all five evaluation dimensions. (confidence: 1.00)
  Evidence: Across 20 state-of-the-art models, we find that no single model performs strongly across all dimensions. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/summary.md
- Navigation capability is largely independent of other evaluation dimensions in interactive world models. (confidence: 1.00)
  Evidence: navigation is largely independent of other dimensions, [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/source.tex
- Physical correctness in interactive world models correlates more with rendering quality than with control capabilities. (confidence: 1.00)
  Evidence: physical correctness correlates with rendering quality rather than control, [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/source.tex

### Limitation

- Existing video-generation and world-model benchmarks lack a unified protocol that spans open-domain scenes, both first- and third-person perspectives, and all four primary interaction types. (confidence: 1.00)
  Evidence: None provides a unified protocol spanning open-domain scenes, both perspectives, and all four interaction types. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/wbench/source.tex

## Watch, Remember, Reason: Human-View Video Understanding with MLLMs

`watch-remember-reason` | authors: Jiahao Meng, Yue Tan, Qi Xu, Kuan Gao, Weisong Liu, Yanwei Li, Jason Li, Lingdong Kong, Haochen Wang, Qianyu Zhou, Jiangning Zhang, Guangliang Cheng, Yunhai Tong, Lu Qi, Minghsuan Yang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/marinero4972/Awesome-HumanView-VideoUnderstanding

### Method

- The paper presents a human-view perspective on LLM-based video understanding structured around three functional abilities: watching, remembering, and reasoning. (confidence: 1.00)
  Evidence: This work presents a human-view perspective on LLM-based video understanding, organized around three functional abilities: watching, remembering, and reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md
- The authors introduce a formulation that characterizes video understanding systems using perceptual representations, memory states, reasoning traces, and final predictions. (confidence: 1.00)
  Evidence: We introduce a formulation that characterizes video understanding systems by their perceptual representations, memory states, reasoning traces, and final predictions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md
- The paper categorizes representative methods in video MLLM systems into watching (fine-grained, comprehensive, audio-visual, and efficient perception), remembering (offline and streaming memory), and reasoning (text-only reasoning and thinking with videos). (confidence: 1.00)
  Evidence: Watching covers fine-grained, comprehensive, audio-visual, and efficient perception. Remembering includes offline and streaming memory, while reasoning covers text-only reasoning and thinking with videos. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md

### Benchmark

- The paper covers training datasets and evaluation benchmarks across task types, supervision formats, modalities, and capability dimensions for domains like egocentric, sports, instructional, medical, and narrative videos. (confidence: 1.00)
  Evidence: We further examine application domains such as egocentric, sports, instructional, medical, and narrative videos, and cover training datasets and evaluation benchmarks across task types, supervision formats, modalities, and capability dimensions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md

### Claim

- Video understanding research is shifting from short clips to long, multimodal, and knowledge-intensive video scenarios, driven by multimodal large language models (MLLMs). (confidence: 1.00)
  Evidence: Video understanding is being rapidly transformed by multimodal large language models (MLLMs), as research moves from short clips to long, multimodal, and knowledge-intensive video scenarios. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md
- The paper identifies key challenges in video MLLMs including spatio-temporal perception, efficient long-video processing, memory modeling, streaming understanding, and faithful reasoning. (confidence: 1.00)
  Evidence: Based on this formulation, we identify challenges in spatio-temporal perception, efficient long-video processing, memory modeling, streaming understanding, and faithful reasoning. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/watch-remember-reason/summary.md

## What-If World: A Causal Benchmark for General World Models in Embodied Scenarios

`what-if-world` | authors: Kunlin Cai, Rui Song, Jinghuai Zhang, Kaiyuan Zhang, Pranav Bodapati, Alicia Yu, Fnu Suya, Mohammad Rostami, Jiaqi Ma, Yuan Tian | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The What-If World benchmark uses APEO, a four-part rubric that checks whether each video follows its prompt (Adherence), is physically consistent (Physics), preserves the shared scene (Environment), and ends in the correct difference (Outcome). (confidence: 1.00)
  Evidence: Each pair is scored with APEO, a four-part rubric checking whether each video follows its prompt (Adherence), is physically consistent (Physics), preserves the shared scene (Environment), and ends in the correct difference (Outcome). [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/summary.md
- The benchmark evaluates causal reasoning by providing a model with two prompts describing the same initial scene but with one physical detail varied, and checking if the generated videos diverge according to physical predictions. (confidence: 1.00)
  Evidence: We test this by giving a model two prompts describing the same scene with one physical detail varied, and checking whether the two videos diverge the way physics predicts. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/summary.md

### Dataset

- The What-If World benchmark comprises 319 test instances spanning six physical primitives across two embodied domains: Autonomous Driving and Robotic Arm Manipulation. (confidence: 1.00)
  Evidence: The benchmark comprises 319 test instances spanning six physical primitives across two embodied domains: Autonomous Driving (AD, 11 sub-categories) and Robotic Arm Manipulation (Rob, 7 sub-categories), for 18 sub-categories in total. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/source.tex

### Benchmark

- What-If World is a causal benchmark consisting of 319 prompt pairs built on real frames from nuScenes and DROID, organized by a taxonomy of six physical variables shared across driving and manipulation. (confidence: 1.00)
  Evidence: We introduce What-If World, 319 such prompt pairs built on real frames from nuScenes and DROID, organized by a taxonomy of six physical variables shared across driving and manipulation. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/summary.md

### Claim

- Across nine state-of-the-art video generation models evaluated on the What-If World benchmark, no system exceeds 52% on the paired score, and open-source models cluster near 28%. (confidence: 1.00)
  Evidence: Across nine state-of-the-art models, no system exceeds 52% on the paired score, and open-source models cluster near 28%. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/summary.md
- Video generation models' performance on causal interventions tracks the visual prominence of the intervention rather than the tractability of its underlying physics, with visually subtle interventions scoring as low as 14.2% and visually pronounced ones reaching 40.4%. (confidence: 1.00)
  Evidence: Where models do score well, performance appears to track the visual prominence of the intervention rather than the tractability of its underlying physics. Some visually subtle interventions score as low as 14.2%, while visually pronounced ones reach 40.4%. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/summary.md

### Limitation

- Single-video evaluation scores consistently overestimate the causal capabilities of video generation models, as generating an individually plausible video does not guarantee correct causal differentiation across a contrastive pair. (confidence: 1.00)
  Evidence: Single-video scores consistently overestimate capability. Every model attains a higher score on single-video metrics than on paired metrics for both Action and Physics... We refer to this discrepancy as the contrastive bottleneck: the generation of an individually plausible video does not translate into correct causal differentiation across a contrastive pair. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/source.tex
- Temporal Sequencing represents a universal challenge for current video generation models, with even the best model achieving only 25.6% on the outcome metric and the performance gap between closed-source and open-source models nearly vanishing. (confidence: 1.00)
  Evidence: Temporal Sequencing represents a universal challenge. ... Temporal Sequencing shows compressed performance: even the best model (Seedance 2.0) reaches only $O_p = 25.6\%$, and the closed-source advantage nearly vanishes [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/what-if-world/source.tex

## When Vision Misleads, Let Location Speak: A Worldwide Image Geo-Localization Method via Location Attention Mechanism and Large Multimodal Models

`2606_08918` | authors: Junchao Cui, Wenqi Shi, Xuanzi Ma, Nan Wu, Shaoyong Du, Xiangyang Luo | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/CJ310177/TransGeoCILP

### Method

- The paper proposes TransGeoCLIP, a retrieval-based framework integrating a location attention mechanism and large multimodal models (LMMs) for worldwide image geo-localization. (confidence: 1.00)
  Evidence: To address this issue, we propose TransGeoCLIP, a novel retrieval-based framework that integrates a location attention mechanism and large multimodal models (LMMs). [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex
- TransGeoCLIP operates in two stages: retrieval database construction using Transformers with location attention to encode GPS coordinates and enable joint image-text-GPS embedding via CLIP, and retrieval-augmented inference using LMMs to predict the final location. (confidence: 1.00)
  Evidence: The framework consists of two stages: 1) Retrieval database construction, which employs Transformers equipped with location attention mechanisms to encode labeled GPS coordinates and enhance location semantics, subsequently enables joint image-text-GPS embedding through CLIP; 2) Retrieval-augmented inference, which leverages LMMs to infer the final image location prediction from retrieved database results. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex
- The paper introduces a Transformer-based GPS encoder to extract rich semantic representations from GPS coordinates during retrieval database construction. (confidence: 1.00)
  Evidence: We introduce the first Transformer-based GPS encoder for worldwide image geo-localization. By leveraging Transformers to extract rich semantic representations from GPS coordinates during retrieval database construction, our encoder significantly enhances the geographical awareness and leads to more accurate localization; [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex
- The proposed location attention mechanism learns locational distances between images, dynamically reorders images in the retrieval database, and mitigates interference from misleading visual cues. (confidence: 1.00)
  Evidence: We design a location attention mechanism that learns locational distances between images, dynamically reorders images in the retrieval database, and strengthens the ability to distinguish visually similar scenes while mitigating interference from misleading visual cues. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex

### Dataset

- The authors construct and release TwinBuilds, a small dataset of similar landmarks, to evaluate performance on visually similar buildings. (confidence: 1.00)
  Evidence: To facilitate evaluation on visually similar buildings, we construct and release TwinBuilds, small dataset of similar landmarks; [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex

### Benchmark

- The TransGeoCLIP framework is evaluated on the IM2GPS, IM2GPS3k, YFCC4k, and YFCC26k datasets. (confidence: 1.00)
  Evidence: Extensive experimental results on diverse datasets, including IM2GPS, IM2GPS3k, YFCC4k, and YFCC26k, demonstrate that TransGeoCLIP significantly enhances localization performance for visually similar images. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex

### Claim

- TransGeoCLIP improves street-level localization accuracy (within 1 km error), surpassing state-of-the-art methods by 1.5%, 1.07%, 7.18%, and 9.75% on the IM2GPS, IM2GPS3k, YFCC4k, and YFCC26k benchmarks, respectively. (confidence: 1.00)
  Evidence: Particularly, street-level localization accuracy (within 1 km error) is substantially improved, surpassing state-of-the-art methods by 1.5%, 1.07%, 7.18%, and 9.75% on these benchmarks, respectively. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex

### Limitation

- Existing worldwide image geo-localization methods often mislocalize images by matching them to visually similar scenes from different geographic regions. (confidence: 1.00)
  Evidence: Existing methods often mislocalize images by matching them to visually similar scenes from different geographic regions, which limits reliability in practical applications. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex
- Classification-based geo-localization methods are limited by grid granularity, which can cause significant errors if the true location is far from the predicted grid center. (confidence: 1.00)
  Evidence: Despite avoiding large-scale retrieval databases, classification-based methods remain constrained by grid granularity, often incurring significant errors when the true location lies far from the predicted grid center. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex
- Retrieval-based methods that rely heavily on visual similarity struggle to achieve high precision because visually similar images can correspond to geographically distant locations. (confidence: 1.00)
  Evidence: However, retrieval-based methods that rely heavily on visual similarity often struggle to achieve high precision, as visually similar images can correspond to geographically distant locations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_08918/source.tex

## Where Does the Answer Come From? Benchmarking View-Level Visual Evidence Identification in Multi-View MLLMs for Autonomous Driving

`2606_09644` | authors: Yimu Wang, Yee Man Choi, Barry Zhang, Mozhgan Nasr Azadani, Sean Sedwards, Krzysztof Czarnecki | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The evaluation protocol includes three settings: camera-view selection, oracle QA given the golden view, and joint prediction where the model selects a view and answers in one pass. (confidence: 1.00)
  Evidence: We evaluate three settings: camera-view selection, oracle QA given the golden view, and joint prediction in which the model selects a view and answers in one pass. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex
- Answers are evaluated using exact match for multiple-choice structured predictions and an LLM judge for free-form responses. (confidence: 1.00)
  Evidence: Answers are evaluated in both multiple-choice and free-form formats, using exact match for structured predictions and an LLM judge for free-form responses. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex

### Dataset

- The benchmark dataset consists of 122 conflict-centric question-answer pairs derived from 73 NuScenes scenes, covering causality, counterfactual reasoning, and intent prediction. (confidence: 1.00)
  Evidence: The benchmark contains 122 conflict-centric question-answer pairs from 73 scenes, spanning causality, counterfactual reasoning, and intent prediction. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex

### Benchmark

- The paper introduces a multi-view visual question answering benchmark to evaluate evidence-source identification in autonomous driving scenes. (confidence: 1.00)
  Evidence: We introduce a multi-view visual question answering benchmark for evaluating evidence-source identification: given six synchronized NuScenes views and a question, the model must identify the supporting camera view and answer the question. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex

### Claim

- Claude achieved the highest mean accuracy for view selection among the evaluated models, while open-source models like Qwen2.5VL-7B performed significantly lower. (confidence: 1.00)
  Evidence: Claude achieving the highest mean accuracy (82.62\%, 95\% CI: [81.77, 83.47]) and GPT-5.4/Gemini following at 77.54\%/74.10\%.
Open-source performance is generally lower: Qwen3VL-8B and InternVL3 cluster around 61.5\%, while Qwen2.5VL-7B drops to 12.62\% [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex
- There is a consistent performance drop from the oracle setting to the joint prediction setting across all models, indicating that view identification is a major bottleneck for end-to-end grounded answering. (confidence: 1.00)
  Evidence: \Cref{tab:main-results} further reveals a consistent oracle-to-joint drop across all models (e.g., Claude: 89.3$\rightarrow$73.2 in MC; GPT-5.4: 86.9$\rightarrow$66.9).
Because the oracle setting supplies the golden view, this drop indicates that view identification is a major bottleneck for end-to-end grounded answering. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex
- Free-form answer scores are consistently lower than multiple-choice scores, suggesting that unconstrained generation introduces additional reasoning and grounding errors. (confidence: 1.00)
  Evidence: Finally, free-form scores are consistently below multiple-choice in both oracle and joint settings, suggesting that unconstrained generation introduces additional reasoning, calibration, and grounding errors beyond option selection. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex

### Limitation

- The benchmark is designed as test-only without a training split to prevent annotation leakage, meaning results should be interpreted as controlled diagnostics rather than saturated leaderboard performance. (confidence: 1.00)
  Evidence: To reduce annotation leakage into evaluation, we treat the dataset as test-only and do not create a training split.
This choice matches the benchmark's diagnostic goal: we want to measure whether existing MLLMs can identify the evidence source under realistic multi-view prompting, rather than optimize a model specifically for this label space.
Because the benchmark is compact, the reported numbers should be interpreted as controlled diagnostics of grounding behaviour rather than leaderboard-style saturated performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09644/source.tex

## Where Should Knowledge Enter? A Layered Framework for Knowledge Infusion in Multimodal Iterative Generative Mo

`2606_06356` | authors: Renjith Prasad, Chathurangi Shyalika, Anushka Pawar, Amit Sheth | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper introduces a four-layer framework for knowledge infusion in iterative generative models, comprising surface, trajectory, latent, and parametric layers. (confidence: 1.00)
  Evidence: This maps to four intervention layers: surface, trajectory, latent, and parametric infusion. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/summary.md
- Surface infusion modifies the conditioning input or post-processes the output without changing the generator's internal dynamics. (confidence: 1.00)
  Evidence: Surface infusion transforms the conditioning input
  or post-processes the output without altering the generator's
  internal dynamics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex
- Trajectory infusion alters the transition function during inference to steer the evolution of the generative process. (confidence: 1.00)
  Evidence: Trajectory infusion modifies the transition function
  at inference time, steering \emph{how} the process evolves. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex
- Latent infusion directly reshapes the intermediate state of the generative process. (confidence: 1.00)
  Evidence: Latent infusion directly reshapes the intermediate
  state $h_t$, changing \emph{what} is being evolved. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex
- Parametric infusion internalizes knowledge into the model parameters or architecture, fundamentally altering the generator. (confidence: 1.00)
  Evidence: Parametric infusion internalizes knowledge into the
  parameters $\theta$ or architecture, altering the
  generator itself. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex

### Dataset

- The framework was validated using a multimodal knowledge graph as a structured knowledge source in a safety-alignment experiment. (confidence: 1.00)
  Evidence: In a controlled safety-alignment experiment using a multimodal
knowledge graph with two diffusion backbones, we implement three of
the four layers cumulatively [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex

### Claim

- Implementing three of the four knowledge infusion layers cumulatively reduced knowledge-violating outputs by 70.97% compared to vanilla generation. (confidence: 1.00)
  Evidence: reducing knowledge-violating outputs by 70.97\% compared to
vanilla generation and empirically confirming the framework's complementarity prediction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex

### Limitation

- The parametric infusion layer was not implemented in the empirical validation because it requires retraining the model. (confidence: 1.00)
  Evidence: leaving parametric infusion for future work as it requires retraining. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06356/source.tex

## Where, What, Why, and Importance: Structured Defect Grounding for Text-to-Image Feedback

`2606_06113` | authors: Huaisong Zhang, Hao Yu, Yuxuan Zhang, Jiahe Wang, Xinrui Chen, Haoxiang Cao, Feng Lu, Wendong Zhang, Changqian Yu, Chun Yuan | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/EthanG97/ImageDoctor, https://github.com/nianbai006/SDG

### Method

- Structured Defect Grounding (SDG) formulates text-to-image diagnosis as a structured set prediction task by modeling each defect as a (location, type, reason, importance) tuple. (confidence: 1.00)
  Evidence: we propose Structured Defect Grounding (SDG), which casts T2I diagnosis as structured set prediction by modeling each defect as a (location, type, reason, importance) tuple. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/source.tex
- BoxFlow-GRPO is an algorithm that converts predicted defect sets into box-derived, importance-weighted spatial rewards for diffusion model alignment. (confidence: 1.00)
  Evidence: BoxFlow-GRPO converts predicted defect sets into box-derived, importance-weighted spatial rewards for diffusion model alignment. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/summary.md

### Dataset

- SDG-30K is a dataset comprising 30,096 images with box-grounded artifact and misalignment annotations across four modern text-to-image generators. (confidence: 1.00)
  Evidence: we construct SDG-30K, a 30,096-image dataset with box-grounded artifact and misalignment annotations across four modern T2I generators [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/source.tex

### Benchmark

- SDG-Eval is a dedicated evaluation protocol designed for structured defect-set evaluation. (confidence: 1.00)
  Evidence: define SDG-Eval, a dedicated protocol for structured defect-set evaluation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/source.tex

### Claim

- The proposed SDG detector outperforms leading proprietary Vision-Language Models on the task of structured defect grounding. (confidence: 1.00)
  Evidence: Extensive experiments show that our SDG detector outperforms leading proprietary VLMs on structured defect grounding [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/summary.md
- Using SDG-guided rewards consistently improves text-to-image alignment and supports localized image refinement. (confidence: 1.00)
  Evidence: SDG-guided rewards consistently improve T2I alignment and support localized image refinement. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/summary.md

### Limitation

- Existing heatmap-centric dense-feedback methods formulate diagnosis as pixel-field regression, which makes it difficult to localize variable-cardinality defects and bind semantic reasons to individual failures. (confidence: 1.00)
  Evidence: their heatmap-centric representations still formulate diagnosis as pixel-field regression, making it difficult to localize variable-cardinality defects and bind semantic reasons to individual failures. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/summary.md
- Scalar preference scores collapse image defects into a single global value, preventing the localization of faulty content and distinction between different types of errors. (confidence: 1.00)
  Evidence: Evaluating such outputs with scalar preference scores~\citep{wu2023humanpreferencescorebetter,wu2023humanpreferencescorev2,xu2023imagerewardlearningevaluatinghuman,kirstain2023pickapicopendatasetuser} collapses these defects into a single global value. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_06113/source.tex

## World Action Models: The Next Frontier in Embodied AI

`world-action-models` | authors: Siyin Wang, Junhao Shi, Zhaoyang Fu, Xinzhe He, Feihong Liu, Chenchen Yang, Yikang Zhou, Zhaoye Fei, Jingjing Gong, Jinlan Fu, Mike Zheng Shou, Xuanjing Huang, Xipeng Qiu, Yu-Gang Jiang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/OpenMOSS/Awesome-WAM

### Method

- World Action Models (WAMs) are defined as embodied foundation models that unify predictive state modeling with action generation to target a joint distribution over future states and actions. (confidence: 1.00)
  Evidence: We term this emerging paradigm World Action Models (WAMs): embodied foundation models that unify predictive state modeling with action generation, targeting a joint distribution over future states and actions rather than actions alone. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/summary.md
- The paper categorizes World Action Models into a taxonomy of Cascaded and Joint WAMs, further subdivided by generation modality, conditioning mechanism, and action decoding strategy. (confidence: 1.00)
  Evidence: We organize existing methods into a structured taxonomy of Cascaded and Joint WAMs, with further subdivision by generation modality, conditioning mechanism, and action decoding strategy. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex
- Cascaded World Action Models factorize the objective by first synthesizing representations of anticipated future states and subsequently deriving actions from them. (confidence: 1.00)
  Evidence: Cascaded WAM explicitly factorizes the objective, formally $p(o', a \mid o, l) = p(a \mid o', o, l)p(o' \mid o, l)$, by first synthesizing representations of anticipated future states, from which actions are subsequently derived [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex
- Joint World Action Models directly model the joint distribution of future states and actions, co-optimizing state prediction and action generation within a shared representational space. (confidence: 1.00)
  Evidence: Joint WAM directly modeling the joint distribution ($p(o', a \mid o, l)$), where state prediction and action generation are co-optimized within a shared representational space [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

### Dataset

- The data ecosystem for developing World Action Models includes robot teleoperation, portable human demonstrations, simulation, and internet-scale egocentric video. (confidence: 1.00)
  Evidence: We systematically analyze the data ecosystem fueling WAMs development, spanning robot teleoperation, portable human demonstrations, simulation, and internet-scale egocentric video [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

### Benchmark

- Evaluation protocols for World Action Models are organized around three main dimensions: visual fidelity, physical commonsense, and action plausibility. (confidence: 1.00)
  Evidence: synthesize emerging evaluation protocols organized around visual fidelity, physical commonsense, and action plausibility. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

### Claim

- Vision-Language-Action (VLA) models learn reactive observation-to-action mappings without explicitly modeling how the physical world evolves under intervention. (confidence: 1.00)
  Evidence: Vision-Language-Action (VLA) models have achieved strong semantic generalization for embodied policy learning, yet they learn reactive observation-to-action mappings without explicitly modeling how the physical world evolves under intervention. [metadata] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex
- Integrating world modeling into embodied policies enables stronger physical understanding, better generalization across novel environments, and the use of large-scale human video data lacking action annotations. (confidence: 1.00)
  Evidence: The integration of world modeling brings stronger physical understanding, improved generalization across novel environments, and the ability to leverage large-scale human video data that lack action annotations—substantially expanding the data foundations available for embodied policy learning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

### Limitation

- The absence of predictive physical reasoning in standard VLA models limits their generalization in scenarios where anticipating future states is essential. (confidence: 1.00)
  Evidence: This absence of predictive physical reasoning limits their generalization, where anticipating future states is essential. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world-action-models/source.tex

## World Model for Robot Learning: A Comprehensive Survey

`2605_00080` | authors: Bohan Hou, Gen Li, Jindou Jia, Tuo An, Xinying Guo, Sicong Leng, Haoran Geng, Yanjie Ze, Tatsuya Harada, Philip Torr, Oier Mees, Marc Pollefeys, Zhuang Liu, Jiajun Wu, Pieter Abbeel, Jitendra Malik, Yilun Du, Jianfei Yang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/NTUMARS/Awesome-World-Model-for-Robotics-Policy, https://github.com/facebookresearch/repo

### Claim

- World models are predictive representations of how environments evolve under actions and have become a central component of robot learning. (confidence: 1.00)
  Evidence: World models, which are predictive representations of how environments evolve under actions, have become a central component of robot learning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_00080/source.tex
- An actionable world model should provide three core capabilities: foresight, imagination-driven planning, and data amplification. (confidence: 1.00)
  Evidence: Accordingly, an actionable world model should provide three core capabilities: \textbf{foresight}~\citep{tcidm,lingbotva,saydream,motus}, i.e., anticipating future states or action consequences before execution; \textbf{imagination-driven planning}~\citep{CosmosPolicy}, i.e., using imagined rollouts to compare and select candidate behaviors; and \textbf{data amplification}~\citep{dreamgen,CosmosPredict}, i.e., synthesizing additional demonstrations or interaction trajectories to improve learning. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_00080/source.tex
- The resurgence of world models in modern machine learning is driven by model-based reinforcement learning and large-scale generative modeling, particularly video generation. (confidence: 1.00)
  Evidence: In modern machine learning, the resurgence of world models is driven mainly by two lines of progress~\citep{ha2018worldmodels}: model-based reinforcement learning~\citep{nguyen1990improving,wovr,wmpo}, which uses learned dynamics for planning and policy improvement, and large-scale generative modeling~\citep{CosmosPredict,ctrlworld,rynnvla001,dreamgen}, especially video generation, which learns rich spatiotemporal regularities from large-scale visual or interaction data. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_00080/source.tex
- The literature on world models for robot learning remains fragmented across architectures, functional roles, and embodied application domains. (confidence: 1.00)
  Evidence: However, the literature remains fragmented across architectures, functional roles, and embodied application domains. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_00080/source.tex

### Limitation

- Purely reactive Vision-Language-Action (VLA) policies are limited in complex physical environments due to struggles with long-horizon reasoning, temporal credit assignment, and robustness under compounding errors. (confidence: 1.00)
  Evidence: purely reactive VLA policies remain limited in complex physical environments, where they often struggle with long-horizon reasoning, temporal credit assignment, and robustness under compounding errors. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_00080/source.tex

## World Model-Enabled Causal Digital Twins for Semantic Communications in Physical AI Systems

`2605_16547` | authors: Lingyi Wang, Tingyu Shui, Walid Saad, Pascal Adjakple | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The paper proposes a world-model-enabled causal digital twin (WM-CDT) framework to capture the dynamics of closed-loop physical AI systems and enable counterfactual reasoning for long-horizon imagined rollouts. (confidence: 1.00)
  Evidence: Then, a world-model-enabled causal digital twin (WM-CDT) framework is proposed to capture the dynamics of closed-loop physical AI systems and enable counterfactual reasoning for long-horizon imagined rollouts. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/summary.md
- A novel causal information value (CIV) metric is introduced to evaluate the marginal contribution of each semantic token to the expected long-term return by transmission interventions. (confidence: 1.00)
  Evidence: To solve this problem, a novel causal information value (CIV) metric is introduced to evaluate the marginal contribution of each semantic token to the expected long-term return by transmission interventions. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/summary.md

### Dataset

- The proposed framework is evaluated using an AirSim-Sionna-based unmanned aerial vehicle (UAV) navigation simulator with realistic wireless channel modeling. (confidence: 1.00)
  Evidence: Extensive simulations on an AirSim-Sionna-based unmanned aerial vehicle (UAV) navigation simulator with realistic wireless channel modeling show that the proposed WM-CDT framework achieves significant improvement [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex

### Claim

- The WM-CDT framework achieves up to 17.3%, 55.4%, 30.7%, and 33.7% higher return-per-kbit than AC-based recurrent reinforcement learning (AC-RRL), model-based policy optimization (MBPO), AC, and proximal policy optimization (PPO), respectively. (confidence: 1.00)
  Evidence: Extensive simulation results on the UAV navigation task show that WM-CDT achieves up to $17.3\%$, $55.4\%$, $30.7\%$, and $33.7\%$ higher return-per-kbit than AC-based recurrent reinforcement learning (AC-RRL) \cite{gc}, model-based policy optimization (MBPO), AC, and proximal policy optimization (PPO), respectively [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex
- The WM-CDT framework improves the navigation success rate by up to 9.6%, 26.3%, 16.1%, and 18.0% compared to AC-RRL, MBPO, AC, and PPO, respectively. (confidence: 1.00)
  Evidence: and improves the navigation success rate by up to $9.6\%$, $26.3\%$, $16.1\%$, and $18.0\%$, respectively. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex
- The causal information value (CIV) metric provides a better estimation of the true long-horizon return gain compared to existing information value metrics like myopic VoI, saliency score, and confidence score. (confidence: 1.00)
  Evidence: Moreover, CIV is shown to be more aligned with the true long-horizon return gain than the myopic VoI, saliency score, and confidence score. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex

### Limitation

- Most existing semantic communication solutions are tailored to one-shot tasks and optimize instantaneous performance, making them unsuitable for closed-loop dynamic systems with physical AI. (confidence: 1.00)
  Evidence: However, most existing semantic communication solutions are tailored to one-shot tasks and optimize instantaneous performance. Hence, they cannot be used to support closed-loop dynamic systems with physical artificial intelligence (AI) [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/summary.md
- Existing reinforcement learning approaches rely on trial-and-error interactions which are data-inefficient and may be unsafe in physical AI systems, and they mainly optimize policies from current observations rather than explicitly reasoning over future states. (confidence: 1.00)
  Evidence: First, RL relies on trial-and-error interactions, which are data-inefficient and may be unsafe in physical AI systems. Second, RL-based approaches mainly optimize policies from current observations, rather than explicitly reasoning over future wireless and physical states. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_16547/source.tex

## World Models as Group Actions

`2605_24578` | authors: Zijie Wang, Wei Zhang, Weiming Zhang, Fanqi Zhang, Xiao Tan, Yipeng Qin, Guanbin Li | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The authors formalize action-conditioned world modeling as realizing a group action on the state space. (confidence: 1.00)
  Evidence: we formalize action-conditioned world modeling as realizing a group action on the state space, providing a principled criterion for evaluating dynamics beyond visual quality. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/summary.md
- The proposed approach enforces identity, inverse, and composition consistency via latent-space regularization with synthesized supervision. (confidence: 1.00)
  Evidence: we propose a unified approach that enforces identity, inverse, and composition consistency via latent-space regularization with synthesized supervision, avoiding additional data collection. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex
- The method synthesizes supervision signals from existing trajectories by constructing zero-action, forward-inverse, and composition-equivalent action segments. (confidence: 1.00)
  Evidence: the method synthesizes supervision signals from existing trajectories by constructing zero-action, forward-inverse, and composition-equivalent action segments, avoiding the need for additional data collection. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex

### Benchmark

- The authors introduce Group-Action Consistency (GAC) and Group-Action Robustness (GAR) metrics to evaluate structural correctness and rollout stability. (confidence: 1.00)
  Evidence: We further introduce two metrics: Group-Action Consistency (GAC) and Group-Action Robustness (GAR), to evaluate structural correctness and rollout stability. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex

### Claim

- Visual realism in video world models does not guarantee that their dynamics are truly governed by actions. (confidence: 1.00)
  Evidence: Video world models have achieved strong visual realism, but this does not ensure that their dynamics are truly governed by actions. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex
- Action faithfulness in embodied settings can be understood through the compositional structure of actions, which often follows a group structure like SE(2) for navigation. (confidence: 1.00)
  Evidence: we argue that action faithfulness should be understood through the compositional structure of actions, which in many embodied settings follows a group structure (e.g., SE(2) for navigation). [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex
- The state-of-the-art video world model NWM exhibits clear violations of the group-action structure despite producing visually convincing rollouts. (confidence: 1.00)
  Evidence: Despite producing visually convincing rollouts, NWM exhibits clear violations of the group-action structure. [artifact:source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex
- The proposed method consistently improves both GAC and GAR in state-of-the-art video world models without degrading perceptual quality. (confidence: 1.00)
  Evidence: Extensive experimental results show that our method consistently improves both GAC and GAR in state-of-the-art video world models without degrading perceptual quality. [artifact:summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2605_24578/source.tex

## World-Language-Action Model for Unified World Modeling, Language Reasoning, and Action Synthesis

`2606_05979` | authors: Yi Yang, Zhihong Liu, Siqi Kou, Yiyang Chen, Yanzhe Hu, Jianbo Zhou, Boyuan Zhao, Zhijie Wei, Xiao Xia, Xueqi Li, Pengfei Liu, Zhijie Deng | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/SJTU-DENG-Lab/WLA

### Method

- The World-Language-Action (WLA) model takes textual instructions, images, and robot states as inputs to jointly predict textual subtasks, subgoal images, and robot actions. (confidence: 1.00)
  Evidence: WLA takes textual instructions, images, and robot states as inputs to jointly predict textual subtasks, subgoal images, and robot actions [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05979/source.tex
- The core of the WLA model is an autoregressive (AR) Transformer backbone that predicts the next state, comprising semantic-level textual intention and fine-grained physical dynamics. (confidence: 1.00)
  Evidence: At the core of WLA lies an autoregressive (AR) Transformer backbone, instead of a bidirectional diffusion Transformer as in WAMs, to predict the next state, comprising the semantic-level textual intention and complementary fine-grained physical dynamics. [abstract]
- The physical dynamics in WLA are supervised by a world modeling objective based on a dedicated World Expert and are used to ease the characterization of state-action correlation for the Action Expert. (confidence: 1.00)
  Evidence: The physical dynamics are supervised by the world modeling objective based on a dedicated World Expert, and are leveraged to ease the characterization of the state-action correlation for the Action Expert. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05979/source.tex
- WLA uses meta-queries to allow world prediction to implicitly impact action generation, enabling the world prediction to be disabled during inference. (confidence: 1.00)
  Evidence: WLA leverages meta-queries to make the world prediction implicitly impact the action generation so that the former can be disabled during inference. [abstract]

### Benchmark

- WLA-0 achieves a 92.94% success rate on the RoboTwin2.0 Clean benchmark and a 56.5% success rate on RMBench. (confidence: 1.00)
  Evidence: Evaluations across simulated and real-world environments demonstrate that WLA-0 achieves state-of-the-art multi-task and long-horizon learning abilities, e.g., 92.94% success rate on RoboTwin2.0 Clean and 56.5% success rate on RMBench. [abstract]

### Claim

- The WLA-0 prototype has 2 billion active parameters and achieves an inference time of 40 ms on an NVIDIA RTX 5090. (confidence: 1.00)
  Evidence: Our WLA-0 prototype, with 2B active parameters, achieves 40 ms per inference on an NVIDIA RTX 5090. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_05979/source.tex
- WLA-0 can learn novel tasks directly from cross-embodiment robot videos without requiring action annotations. (confidence: 0.90)
  Evidence: WLA-0 also holds the promise to learn novel tasks directly from cross-embodiment robot videos without action annotations. [abstract]

## World2VLM: Distilling World Model Imagination into VLMs for Dynamic Spatial Reasoning

`world2vlm` | authors: Wanyue Zhang, Wenxiang Wu, Wang Xu, Jiaxin Luo, Helu Zhi, Yibin Huang, Shuo Ren, Zitao Liu, Jiajun Zhang | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/WanyueZhang-ai/World2VLM, https://github.com/cvpr-org/author-kit

### Method

- World2VLM is a training framework that distills spatial imagination from a generative world model into a vision-language model. (confidence: 1.00)
  Evidence: In this work, we propose World2VLM, a training framework that distills spatial imagination from a generative world model into a vision-language model. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex
- The framework uses a view-consistent world model to synthesize geometrically aligned future views based on an initial observation and a parameterized camera trajectory. (confidence: 1.00)
  Evidence: Given an initial observation and a parameterized camera trajectory, we use a view-consistent world model to synthesize geometrically aligned future views and derive structured supervision for both forward (action-to-outcome) and inverse (outcome-to-action) spatial reasoning. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex
- The post-training recipe for World2VLM consists of two stages: supervised distillation followed by task-aware GRPO refinement. (confidence: 1.00)
  Evidence: Third, a two-stage post-training recipe combines supervised distillation with task-aware GRPO refinement, enabling the model to internalize dynamic spatial structure and then sharpen its structured spatial outputs. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex
- The experiments instantiate the world-model teacher using both Stable Virtual Camera and HY-WorldPlay. (confidence: 1.00)
  Evidence: in our experiments, we instantiate it with both Stable Virtual Camera and HY-WorldPlay to study how different world-model priors affect downstream spatial supervision. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Dataset

- The World2VLM dataset is publicly available on Hugging Face. (confidence: 1.00)
  Evidence: The dataset is available at \url{https://huggingface.co/datasets/WanyueZhang/World2VLM}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Benchmark

- World2VLM is evaluated on the SAT-Real, SAT-Synthesized, VSI-Bench, and MindCube spatial reasoning benchmarks. (confidence: 1.00)
  Evidence: World2VLM delivers consistent improvements over the base model across diverse benchmarks, including SAT-Real, SAT-Synthesized, VSI-Bench, and MindCube. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Claim

- World2VLM outperforms test-time world-model-coupled methods while avoiding the computational overhead of inference-time generation. (confidence: 1.00)
  Evidence: It also outperforms the test-time world-model-coupled methods while eliminating the need for expensive inference-time generation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex
- World2VLM achieves consistent improvements over the base Qwen2.5-VL model across all evaluated benchmarks, with the GRPO stage providing further improvements over the SFT checkpoint. (confidence: 1.00)
  Evidence: Across all four, World2VLM delivers consistent improvements over the base Qwen2.5-VL model, and the GRPO stage further improves over the SFT checkpoint. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

### Limitation

- Current vision-language models are fundamentally limited in dynamic spatial reasoning, such as inferring scene evolution under egocentric motion or predicting action consequences. (confidence: 1.00)
  Evidence: current VLMs remain fundamentally limited in dynamic spatial reasoning---the ability to infer how a scene evolves under egocentric motion, predict the consequences of actions, or mentally simulate unseen viewpoints. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex
- Coupling VLMs with world models at inference time introduces substantial computational overhead and does not update the VLM's internal parameters. (confidence: 1.00)
  Evidence: The second is to couple VLMs with world models or imagination-based reasoning procedures at inference time... Although this can improve dynamic spatial reasoning, it incurs substantial test-time overhead and leaves the VLM itself largely unchanged. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/world2vlm/source.tex

## Your Model Already Knows: Attention-Guided Safety Filter for Vision-Language-Action Models

`2606_09749` | authors: Seongbin Park, Fan Zhang, Baharan Mirzasoleiman, Shahriar Talebi, Nader Sehatbakhsh | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed training-free safety framework extracts the active target from specific attention heads within a Vision-Language-Action (VLA) model at every step, treats the rest of the scene as obstacles, and uses a Control Barrier Function (CBF) filter along with a lightweight real-time object tracker for collision avoidance. (confidence: 1.00)
  Evidence: These heads can be exploited within a training-free safety framework that obtains the active target from the attention heads at every step, treats the remainder of the scene as obstacles, and feeds these into a Control Barrier Function (CBF) filter. Together with a lightweight real-time object tracker, this allows for collision avoidance for non-static obstacles. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/source.tex
- The Control Barrier Function (CBF) uses a separating-hyperplane approach for ellipsoids, eliminating the hyperplane offset by summing the support functions of the robot and obstacle ellipsoids to form a single combined function. (confidence: 0.95)
  Evidence: Because the obstacle ellipsoid $\mathcal{E}_O$ is uncontrolled in our setting, we eliminate the hyperplane offset $\gamma$ by summing the two functions, yielding a single combined function [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/source.tex

### Benchmark

- The framework is evaluated on SafeLIBERO, which the authors extended to include moving obstacles to create a dynamic variant. (confidence: 1.00)
  Evidence: We evaluate our framework on SafeLIBERO, which we extend with moving obstacles. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/summary.md

### Claim

- A small number of attention heads within a Vision-Language-Action (VLA) model can reliably localize the object that the policy intends to approach. (confidence: 1.00)
  Evidence: We discover that a small number of attention heads within a VLA model reliably localize the object the policy intends to approach. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/source.tex
- On the dynamic variant of the benchmark, the proposed method outperforms an oracle that uses privileged simulator state for init-time target assignment by an average of 43%. (confidence: 1.00)
  Evidence: On the dynamic variant, where the oracle's init-time target assignment becomes stale, our method substantially outperforms it by 43%, on average. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/summary.md
- The perceptual signals required for real-time safety filtering are already present within VLA policies and can be utilized without extra training or heavy auxiliary models. (confidence: 1.00)
  Evidence: Our findings suggest that the perceptual signals needed for real-time safety filtering are already present within VLA policies and can be exploited without additional training or heavy auxiliary models. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/source.tex

### Limitation

- Existing safety filters that query a vision-language model to identify obstacles are too slow to run in the control loop and can only be invoked at episode initialization, making them unable to track moving obstacles. (confidence: 1.00)
  Evidence: Existing safety filters sidestep this problem by querying a vision-language model (VLM) to identify obstacles and their locations. This, however, is too slow to run in the control loop and can only be invoked at episode initialization, leaving the filter unable to track moving obstacles. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09749/source.tex

## Zero-Shot Semantic Re-Identification for Autonomous Driving: A VLM Baseline Study

`2606_09362` | authors: Eduardo Borges, Manuel Abreu, Luís Garrote, Urbano J. Nunes | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The proposed zero-shot semantic re-identification pipeline consists of three stages: generating one-line descriptions from object image crops using a Vision-Language Model (VLM), encoding these descriptions into text embeddings, and retrieving objects via cosine similarity between the embeddings. (confidence: 1.00)
  Evidence: Our pipeline consists of three stages, as presented in Fig.~\ref{fig:paper_teaser}. First, each labeled object instance in KITTI is cropped from the source image to form a single-object input. Second, a \ac{vlm} generates a one-line description of the crop using a prompt designed for identity discrimination. Third, the generated text is encoded with a sentence embedding model, and retrieval is performed by cosine similarity between object embeddings. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex
- The prompting strategy is designed to elicit compact, one-line descriptions by instructing the VLM to avoid hedging language, omit uncertain details, prioritize stable identity-bearing attributes, follow a fixed attribute order, and emphasize concrete visual cues. (confidence: 1.00)
  Evidence: The prompt is designed to elicit compact descriptions with high instance-level discriminability. It explicitly instructs the \ac{vlm} to:

\begin{enumerate}
    \item Produce exactly one line of plain text,
    \item Avoid hedging language,
    \item Omit uncertain or invisible details,
    \item Prioritize stable identity-bearing attributes,
    \item Follow a fixed attribute order,
    \item And emphasize concrete visual cues such as shape, color, trim, markings, accessories, and wear.
\end{enumerate} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex
- To evaluate the approach in a strictly zero-shot setting, all VLMs and text embedding models are used off-the-shelf without any task-specific fine-tuning, prompt tuning, adapter training, or parameter updates. (confidence: 1.00)
  Evidence: To evaluate the feasibility of language-mediated \ac{reid} in a strictly zero-shot setting, all models are used off-the-shelf without any task-specific fine-tuning, prompt tuning, adapter training, or parameter updates. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex
- The study evaluates four Vision-Language Models (Qwen3.5 0.8B, Qwen3.5 9B, Qwen3.5 27B, and Gemma 4 E2B) paired with four text embedding models (Embedding Gemma 300M, Nomic Embed v2 305M, Qwen3-Embedding 4B, and Qwen3-Embedding 8B). (confidence: 1.00)
  Evidence: We evaluate four \acp{vlm}:
\begin{itemize}
    \item Qwen3.5 0.8B~\cite{qwen3.5}
    \item Qwen3.5 9B (Q4-K-M)~\cite{qwen3.5}
    \item Qwen3.5 27B (Q4-K-M)~\cite{qwen3.5}
    \item Gemma 4 E2B~\cite{gemma4}
\end{itemize}

We pair these with four text embedding models:
\begin{itemize}
    \item Embedding Gemma 300M~\cite{embedgemma}
    \item Nomic Embed v2 305M~\cite{nomicembedv2}
    \item Qwen3-Embedding 4B~\cite{qwen3embedding}
    \item Qwen3-Embedding 8B~\cite{qwen3embedding}
\end{itemize} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex

### Dataset

- The experiments are conducted on the KITTI-ReID dataset, which is derived from the KITTI tracking dataset by extracting object crops from annotated bounding boxes and associating them with their corresponding identity labels. (confidence: 1.00)
  Evidence: Experiments are conducted on KITTI-ReID, a benchmark previously introduced in our earlier work~\cite{borges2026appearance}. KITTI-ReID is derived from the KITTI tracking dataset by extracting object crops from the annotated bounding boxes and associating them with their corresponding identity labels. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex

### Benchmark

- The study follows the standard re-identification evaluation protocol used in the Market-1501 benchmark, reporting Mean Average Precision (mAP) and Rank-1 accuracy. (confidence: 1.00)
  Evidence: We follow the standard re-identification evaluation protocol used in the Market-1501~\cite{Liang2015market1501} benchmark and report:

\begin{itemize}
    \item Mean Average Precision (mAP), measuring the quality of the full ranked list.
    \item Rank-1 accuracy, measuring whether the top retrieved match belongs to the correct identity,
\end{itemize} [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex

### Claim

- Zero-shot semantic descriptions generated by VLMs can support effective object re-identification, achieving retrieval performance comparable to a supervised CNN baseline while providing greater interpretability through explicit identity cues. (confidence: 1.00)
  Evidence: Results demonstrate that zero-shot semantic descriptions can support effective object re-identification, achieving retrieval performance comparable to a supervised CNN baseline while offering greater interpretability through explicit identity cues. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex

### Limitation

- The use of VLM-generated semantic descriptions for re-identification faces challenges such as attribute inconsistency across different viewpoints and limited fine-grained discrimination between visually similar instances. (confidence: 1.00)
  Evidence: However, the experiments also reveal important challenges, including attribute inconsistency across viewpoints and limited fine-grained discrimination between visually similar instances. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2606_09362/source.tex

## scCBGM: Interpretable Single-Cell Counterfactual Editing

`sccbgm` | authors: Alma Andersson, Aya Abdelsalam Ismail, Edward De Brouwer, Doron Haviv, Tommaso Biancalani, Kyunghyun Cho, Gabriele Scalia, Aïcha BenTaieb, Hector Corrada Bravo | year: 2026 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/almaan/conceptlab, https://github.com/almaan/scCBGM

### Method

- scCBGM adapts concept bottleneck architectures for single-cell data by using decoder skip connections and a cross-covariance penalty to promote disentanglement without dimensional constraints. (confidence: 1.00)
  Evidence: scCBGM adapts concept bottleneck architectures for single-cell data through decoder skip connections and a cross-covariance penalty that promotes disentanglement without dimensional constraints. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/summary.md
- The scCBGM framework is extended to flow matching models to enable concept-guided editing in both encoding-decoding and generation regimes. (confidence: 1.00)
  Evidence: We extend the framework to flow matching models, enabling concept-guided editing in both encoding-decoding and generation regimes. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/summary.md

### Dataset

- The Kang et al. dataset used for benchmarking comprises 24,264 cells across 8 broad-cell types, observed under two conditions: with and without IFN-beta stimulation. (confidence: 1.00)
  Evidence: The \cite{kang} dataset comprises 24,264 cells across 8  broad-cell types, observed under two conditions: with and without IFN-$\beta$ stimulation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/source.tex
- The Immune Dictionary dataset by Cui et al. comprises 110,378 cells, encompassing over 17 distinct immune cell types stimulated with 86 different cytokines in vivo. (confidence: 1.00)
  Evidence: This dataset comprises 110,378 cells, encompassing over 17 distinct immune cell types stimulated with 86 different cytokines in vivo, providing a rich map of cellular responses to immune perturbations. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/source.tex

### Benchmark

- The authors developed a synthetic benchmark with ground-truth counterfactuals to enable rigorous evaluation of the model. (confidence: 1.00)
  Evidence: To enable rigorous evaluation, we develop a synthetic benchmark with ground-truth counterfactuals. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/summary.md

### Claim

- scCBGM demonstrates superior performance in combinatorial generalization and counterfactual prediction across multiple real datasets, supported by cell-level validation on synthetic data and population-level benchmarks on real datasets. (confidence: 1.00)
  Evidence: Across multiple real datasets, scCBGM demonstrates superior performance in combinatorial generalization and counterfactual prediction, supported by cell-level validation on synthetic data and population-level benchmarks on real datasets. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/summary.md

### Limitation

- High-fidelity generative models carry ethical risks such as the potential for fabricating biological data, and over-reliance on simulated counterfactuals without rigorous experimental validation could lead to false therapeutic leads. (confidence: 1.00)
  Evidence: However, high-fidelity generative models carry ethical risks, such as the potential for fabricating biological data. Furthermore, an over-reliance on simulated counterfactuals without rigorous experimental validation could lead to false therapeutic leads, wasting critical resources. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/sccbgm/source.tex

## ColaVLA: Leveraging Cognitive Latent Reasoning for Hierarchical Parallel Trajectory Planning in Autonomous Driving

`colavla` | authors: Qihang Peng, Xuesong Chen, Chenye Yang, Shaoshuai Shi, Hongsheng Li | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/cvpr-org/author-kit, https://github.com/pqh22/ColaVLA

### Method

- ColaVLA is a unified vision-language-action framework that transfers reasoning from text to a unified latent space and uses a hierarchical, parallel trajectory decoder. (confidence: 1.00)
  Evidence: We propose ColaVLA, a unified vision-language-action framework that transfers reasoning from text to a unified latent space and couples it with a hierarchical, parallel trajectory decoder. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/summary.md
- The Cognitive Latent Reasoner component compresses scene understanding into compact, decision-oriented meta-action embeddings using ego-adaptive selection and two VLM forward passes. (confidence: 1.00)
  Evidence: The Cognitive Latent Reasoner compresses scene understanding into compact, decision-oriented meta-action embeddings through ego-adaptive selection and only two VLM forward passes. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/summary.md
- The Hierarchical Parallel Planner generates multi-scale, causality-consistent trajectories in a single forward pass. (confidence: 1.00)
  Evidence: The Hierarchical Parallel Planner then generates multi-scale, causality-consistent trajectories in a single forward pass. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/summary.md
- The cognitive latent reasoner forms a multimodal sequence from a fixed driving prompt, multi-view visual images, and ego status to obtain unified tokens through a VLM. (confidence: 1.00)
  Evidence: Specifically, our reasoner first form a multimodal sequence from a fixed driving prompt, multi-view visual images and ego status, and pass it through a VLM to obtain unified tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- An ego-adaptive modulation aligns visual tokens with the vehicle state, and a lightweight router selects the top-K safety-critical vision tokens. (confidence: 1.00)
  Evidence: An ego-adaptive modulation aligns these tokens with the instantaneous vehicle state, after which a lightweight router scores and selects the top-$K$ safety-critical vision tokens. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- The hierarchical parallel planner uses a causality-preserving hybrid attention mask that allows bidirectional interaction within each temporal scale but enforces strict causality across scales. (confidence: 1.00)
  Evidence: A causality-preserving hybrid attention mask allows bidirectional interaction within each temporal scale for local consistency, while enforcing strict causality across scales such that tokens at scale $s$ can attend only to themselves and the immediately preceding scale $s{-}1$. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- During training, one-hot supervision is applied to the mode closest to the ground truth while optimizing confidence across all candidates to encourage accuracy and diversity. (confidence: 1.00)
  Evidence: During training, one-hot supervision is applied to the mode closest to the ground truth while optimizing confidence across all candidates, encouraging both accuracy and diversity. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex

### Benchmark

- The proposed ColaVLA framework is evaluated on the nuScenes benchmark. (confidence: 1.00)
  Evidence: Experiments on the nuScenes benchmark show that ColaVLA achieves state-of-the-art performance in both open-loop and closed-loop settings [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex

### Claim

- ColaVLA achieves state-of-the-art performance in both open-loop and closed-loop settings on the nuScenes benchmark with favorable efficiency and robustness. (confidence: 1.00)
  Evidence: Experiments on the nuScenes benchmark show that ColaVLA achieves state-of-the-art performance in both open-loop and closed-loop settings with favorable efficiency and robustness. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex

### Limitation

- Current VLM-based planners suffer from a modality mismatch between discrete text reasoning and continuous control actions. (confidence: 1.00)
  Evidence: yet current VLM-based planners face three key challenges: (i) a mismatch between discrete text reasoning and continuous control [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- Existing VLM-based planners experience high latency due to autoregressive chain-of-thought decoding. (confidence: 1.00)
  Evidence: (ii) high latency from autoregressive chain-of-thought decoding [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex
- Inefficient or non-causal planners in current VLM-based systems limit their real-time deployment capabilities. (confidence: 1.00)
  Evidence: (iii) inefficient or non-causal planners that limit real-time deployment. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/colavla/source.tex

## Generalizing vision-language models to novel domains: A comprehensive survey

`2506_18504v2` | authors: Xinyao Li, Jingjing Li, Fengling Li, Lei Zhu, Yang Yang, Heng Tao Shen | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- The survey categorizes VLM generalization methods into prompt-based, parameter-based, and feature-based methods according to the transferred modules or adapted model components. (confidence: 1.00)
  Evidence: Delving into the typical VLM structures, current literatures are categorized into prompt-based, parameter-based and feature-based methods according to the transferred modules. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/summary.md
- The survey reviews generalization methods based on traditional transfer learning settings to reveal how transfer problems are solved in vision-language studies. (confidence: 1.00)
  Evidence: The reviewed methods are introduced based on the traditional transfer learning settings, revealing how these transfer problems are being solved in the era of vision-language studies. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/source.tex

### Claim

- Vision-language models (VLMs) exhibit strong zero-shot capabilities due to web-scale pretraining data, but their performance often deteriorates on domain-specific or specialized generalization tasks. (confidence: 1.00)
  Evidence: Leveraging web-scale pretraining data, these models exhibit strong zero-shot capabilities. However, their performance often deteriorates when confronted with domain-specific or specialized generalization tasks. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/summary.md
- The survey discusses the relations and differences between VLMs and up-to-date multimodal large language models (MLLMs), such as DeepSeek-VL. (confidence: 1.00)
  Evidence: this survey also discusses the relations and differences between VLMs and up-to-date multimodal large language models (MLLM), e.g., DeepSeek-VL. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/summary.md
- Multimodal large language models (MLLMs) enhance the generalizability of vision-language systems by leveraging powerful large language models. (confidence: 1.00)
  Evidence: this survey also includes most up-to-date and representative multimodal large language models (MLLMs), which enhances the generalizability of vision-language systems with powerful large language models. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2506_18504v2/source.tex

## MLLM-For3D: Adapting Multimodal Large Language Model for 3D Reasoning Segmentation

`mllm-for3d` | authors: Jiaxin Huang, Runnan Chen, Ziwen Li, Zhengqing Gao, Xiao He, Yandong Guo, Mingming Gong, Tongliang Liu | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/tmllab/2025_NeurIPS_MLLM-For3D

### Method

- MLLM-For3D utilizes 2D MLLMs to generate multi-view pseudo segmentation masks and text embeddings, which are then unprojected into 3D space and aligned. (confidence: 1.00)
  Evidence: Specifically, we utilize MLLMs to generate multi-view pseudo segmentation masks and corresponding text embeddings, then unproject 2D masks into 3D space and align them with the text embeddings. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md
- The framework introduces a spatial consistency strategy to ensure segmentation masks remain coherent in 3D space and capture scene geometry. (confidence: 1.00)
  Evidence: To address this, we introduce a spatial consistency strategy to enforce that segmentation masks remain coherent in the 3D space, effectively capturing the geometry of the scene. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md
- A Token-for-Query approach is developed for multimodal semantic alignment to consistently identify the same object across different views. (confidence: 1.00)
  Evidence: Moreover, we develop a Token-for-Query approach for multimodal semantic alignment, enabling consistent identification of the same object across different views. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md
- The method filters irrelevant views using token attention to address the issue of irrelevant objects degrading performance. (confidence: 1.00)
  Evidence: To address this, we first filter irrelevant views using token attention. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex

### Dataset

- The pilot study evaluates the performance of 2D reasoning segmentation models on the ScanNet++ dataset. (confidence: 1.00)
  Evidence: We evaluate the performance of 2D reasoning segmentation models, LISA~\cite{lai2024lisa} on the ScanNet++ dataset~\cite{yeshwanthliu2023scannetpp}, by providing the model with different views corresponding to a 3D scene along with an implicit language instruction. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex

### Benchmark

- The paper includes evaluations on the Intent3D and Reason3D benchmarks. (confidence: 1.00)
  Evidence: Evaluation on Intent3D and Reason3D [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md

### Claim

- MLLM-For3D outperforms existing 3D reasoning segmentation methods on indoor scene benchmarks without using any labeled 3D training data. (confidence: 1.00)
  Evidence: Extensive evaluations on various challenging indoor scene benchmarks demonstrate that, even without any labeled 3D training data, MLLM-For3D outperforms existing 3D reasoning segmentation methods [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md
- MLLM-For3D achieves approximately 55% higher mIoU compared to previous methods in 3D reasoning segmentation tasks without 3D annotations. (confidence: 1.00)
  Evidence: MLLM-For3D is evaluated on three challenging benchmarks and shows that it achieves state-of-the-art performance in 3D reasoning segmentation tasks even without the need for any 3D annotations, which achieves about 55\% higher mIoU than the previous methods. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex

### Limitation

- The absence of 3D context and spatial consistency across multiple views causes 2D models to hallucinate non-existent objects and fail to consistently target objects. (confidence: 1.00)
  Evidence: The primary challenge lies in the absence of 3D context and spatial consistency across multiple views, causing the model to hallucinate objects that do not exist and fail to target objects consistently. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/summary.md
- 2D MLLMs processing a single view may produce false positives by hallucinating or mistakenly segmenting objects described in the instruction but not visible in the view. (confidence: 1.00)
  Evidence: False positives in invisible views: A 2D MLLM processing a single view might hallucinate or mistakenly segment objects that are described by the instruction but not visible in that particular view. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex
- Multi-view prediction inconsistency degrades performance when aggregating multi-view predictions into 3D due to a lack of spatial alignment mechanisms across views. (confidence: 1.00)
  Evidence: Multi-View prediction inconsistency occurs when the model lacks a mechanism to ensure spatial alignment of predictions across views, thereby degrading the performance when we aggregate multi-view predictions into 3D. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/mllm-for3d/source.tex

## PAI-Bench: A Comprehensive Benchmark For Physical AI

`pai-bench` | authors: Fengzhe Zhou, Jiannan Huang, Jialuo Li, Deva Ramanan, Humphrey Shi | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/SHI-Labs/physical-ai-bench

### Method

- PAI-Bench-G evaluates video generation by integrating both visual quality and physical plausibility through a domain score and a quality score. (confidence: 1.00)
  Evidence: We introduce \textbf{PAI-Bench-G}, which distinguishes itself by integrating both aspects via a domain score and a quality score, with a strong emphasis on Physical AI applications. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex

### Dataset

- The PAI-Bench dataset comprises 2,808 high-quality real-world cases sourced from captures like dashcam recordings, covering sub-domains such as autonomous vehicles, robotics, and ego-view scenes. (confidence: 1.00)
  Evidence: all videos are sourced from real-world captures, such as dashcam recordings. Furthermore,~\dataset~covers several sub-domains, such as autonomous vehicles, robotics, ego-view scenes, \emph{etc.} , across three tracks, comprising 2,808 high-quality cases. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex

### Benchmark

- PAI-Bench is a unified benchmark designed to evaluate perception and prediction capabilities across video generation, conditional video generation, and video understanding for Physical AI. (confidence: 1.00)
  Evidence: We introduce Physical AI Bench (PAI-Bench), a unified and comprehensive benchmark that evaluates perception and prediction capabilities across video generation, conditional video generation, and video understanding [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex
- PAI-Bench is divided into three tracks: PAI-Bench-G for video generation, PAI-Bench-C for conditional video generation, and PAI-Bench-U for physical video understanding. (confidence: 1.00)
  Evidence: \item \textbf{PAI-Bench-G} (Generation): Targets \textit{prediction} by evaluating visual quality and physical plausibility of VGMs.
\item \textbf{PAI-Bench-C} (Conditional Generation): Further probes \textit{prediction} by evaluating the fidelity of conditional VGMs, specifically their conformance to input control signals (e.g., depth maps).
\item \textbf{PAI-Bench-U} (Understanding): Targets the \textit{perception} component by evaluating MLLM capabilities on video understanding tasks specific to the Physical AI domain. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex
- The study evaluates 15 video generative models, 4 conditional video generative models across 5 control settings, and 16 multi-modal large language models. (confidence: 1.00)
  Evidence: We conduct a large-scale evaluation of 15 VGMs, 4 conditional VGMs with 5 control settings, and 16 MLLMs, establishing the current landscape of Physical AI and highlighting key challenges to guide future research. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex

### Claim

- State-of-the-art video generative models achieve high visual fidelity but often fail to adhere to basic physical laws or model complex real-world dynamics. (confidence: 1.00)
  Evidence: while SOTA VGMs like Veo3~\cite{deepmind2025veo} achieve high visual fidelity, their \textit{prediction} abilities are limited, as they often fail to adhere to basic physical laws or to model complex real-world dynamics. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex
- Powerful multi-modal large language models exhibit limited performance in forecasting and causal interpretation, lagging substantially behind human performance in physical perception tasks. (confidence: 1.00)
  Evidence: the \textit{perception} capabilities of powerful MLLMs, such as GPT-5~\cite{openai2025gpt5}, lag substantially behind human performance. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex
- Current AI systems remain in a nascent stage regarding the core prediction and perception capabilities required for Physical AI. (confidence: 1.00)
  Evidence: These findings suggest that the core \textit{prediction} and \textit{perception} capabilities required for Physical AI remain in a nascent stage. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/pai-bench/source.tex

## ReinFlow: Fine-tuning Flow Matching Policy with Online Reinforcement Learning

`reinflow` | authors: Tonghe Zhang, Chao Yu, Sichang Su, Yu Wang | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

### Method

- ReinFlow is an online reinforcement learning framework designed to fine-tune flow matching policies for continuous robotic control. (confidence: 1.00)
  Evidence: We propose ReinFlow, a simple yet effective online reinforcement learning (RL) framework that fine-tunes a family of flow matching policies for continuous robotic control. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex
- ReinFlow injects learnable noise into a flow policy's deterministic path to convert it into a discrete-time Markov Process for exact likelihood computation. (confidence: 1.00)
  Evidence: ReinFlow injects learnable noise into a flow policy's deterministic path, converting the flow into a discrete-time Markov Process for exact and straightforward likelihood computation. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex
- ReinFlow utilizes a noise injection network to convert flows into a discrete-time Markov process with Gaussian transition probabilities. (confidence: 1.00)
  Evidence: We train a noise injection network to convert flows to a discrete-time Markov process with Gaussian transition probabilities for exact and tractable likelihood computation. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex
- ReinFlow is capable of fine-tuning diverse flow model variants, such as Rectified Flow and Shortcut Models, even at a single denoising step. (confidence: 1.00)
  Evidence: enabling ReinFlow to fine-tune diverse flow model variants, including Rectified Flow [35] and Shortcut Models [19], particularly at very few or even one denoising step. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md

### Benchmark

- ReinFlow is benchmarked on locomotion and manipulation tasks, including long-horizon planning with visual inputs and sparse rewards. (confidence: 1.00)
  Evidence: We benchmark ReinFlow in representative locomotion and manipulation tasks, including long-horizon planning with visual input and sparse reward. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex

### Claim

- Fine-tuning Rectified Flow policies with ReinFlow in legged locomotion tasks resulted in an average net episode reward growth of 135.36%. (confidence: 1.00)
  Evidence: The episode reward of Rectified Flow policies obtained an average net growth of 135.36% after fine-tuning in challenging legged locomotion tasks [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md
- ReinFlow saves 82.63% of wall time compared to the DPPO diffusion RL fine-tuning method in legged locomotion tasks. (confidence: 1.00)
  Evidence: while saving denoising steps and 82.63% of wall time compared to state-of-the-art diffusion RL fine-tuning method DPPO [43]. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md
- Shortcut Model policies fine-tuned with ReinFlow achieved a 40.34% average net increase in success rate in state and visual manipulation tasks. (confidence: 1.00)
  Evidence: The success rate of the Shortcut Model policies in state and visual manipulation tasks achieved an average net increase of 40.34% after fine-tuning with ReinFlow at four or even one denoising step [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md
- ReinFlow's performance in manipulation tasks is comparable to fine-tuned DDIM policies while saving an average of 23.20% in computation time. (confidence: 1.00)
  Evidence: whose performance is comparable to fine-tuned DDIM policies while saving computation time for an average of 23.20%. [abstract] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/summary.md

### Limitation

- Inferring flow policies at very few denoising steps exacerbates the problem of obtaining stable log probabilities due to large discretization errors. (confidence: 1.00)
  Evidence: This problem is exacerbated when we infer flow policies at very few denoising steps, where the discretization error becomes large at a low inference cost. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/reinflow/source.tex

## Remasking Discrete Diffusion Models with Inference-Time Scaling

`2503_00307` | authors: Guanghan Wang, Yair Schiff, Subham Sekhar Sahoo, Volodymyr Kuleshov | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/google-research/maskgit, https://github.com/openai/guided-diffusion

### Method

- The paper introduces the remasking diffusion model (ReMDM) sampler, which is derived from a discrete diffusion model with a custom remasking backward process and can be applied to pretrained masked diffusion models. (confidence: 1.00)
  Evidence: Here, we address this limitation by introducing the remasking diffusion model (ReMDM) sampler, a method that can be applied to pretrained masked diffusion models in a principled way and that is derived from a discrete diffusion model with a custom remasking backward process. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex
- The ReMDM model uses an objective that is a rescaled version of the MDLM objective, which allows the ReMDM sampler to be effectively used on top of pretrained MDLMs. (confidence: 1.00)
  Evidence: The ReMDM model admits an objective that is a rescaled version of the MDLM objective \citep{sahoo2024simple}. This suggests using the ReMDM sampler on top of pretrained MDLMs, which we find to work well. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex

### Dataset

- The paper evaluates model performance using MAUVE scores on the OpenWebText dataset. (confidence: 0.90)
  Evidence: MAUVE scores on OpenWebText. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex

### Claim

- ReMDM provides discrete diffusion with inference-time compute scaling, allowing it to generate natural language outputs that approach the quality of autoregressive models by increasing the number of sampling steps. (confidence: 1.00)
  Evidence: Most interestingly, ReMDM endows discrete diffusion with a form of inference-time compute scaling. By increasing the number of sampling steps, ReMDM generates natural language outputs that approach the quality of autoregressive models [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex
- ReMDM improves the sample quality of masked diffusion models for discretized images and pushes the Pareto frontier of controllability in molecule design by facilitating diffusion guidance. (confidence: 1.00)
  Evidence: ReMDM also improves sample quality of masked diffusion models for discretized images, and in scientific domains such as molecule design, ReMDM facilitates diffusion guidance and pushes the Pareto frontier of controllability relative to classical masking and uniform noise diffusion. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex
- ReMDM is theoretically more general than previous corrector samplers for masked diffusion models. (confidence: 1.00)
  Evidence: Notably, we demonstrate that ReMDM is theoretically more general than previous corrector samplers for masked diffusion models \citep{campbell2022continuous, gat2024discrete}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex
- When the number of sampling steps is reduced to increase speed, ReMDM's performance degrades less compared to other samplers. (confidence: 1.00)
  Evidence: Conversely, when we reduce the sampling steps to increase speed, ReMDM's performance degrades less than other samplers. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex

### Limitation

- Modern masked discrete diffusion models lack the capability for iterative refinement, meaning that once a token is generated or unmasked, it cannot be updated again even if it introduces an error. (confidence: 1.00)
  Evidence: However, modern masked discrete diffusion lacks this capability: when a token is generated, it cannot be updated again, even when it introduces an error. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2503_00307/source.tex

## VLA-OS: Structuring and Dissecting Planning Representations and Paradigms in Vision-Language-Action Models

`vla-os` | authors: Chongkai Gao, Zixuan Liu, Zhenghao Chi, Junshan Huang, Xin Fei, Yiwen Hou, Yuxuan Zhang, Yudi Lin, Zhirui Fang, Zeyu Jiang, Lin Shao | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## What Can RL Bring to VLA Generalization? An Empirical Study

`2505_19789v4` | authors: Jijia Liu, Feng Gao, Bingwen Wei, Xinlei Chen, Qingmin Liao, Yi Wu, Chao Yu, Yu Wang | year: 2025 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr

No research facts available.

## Informed Correctors for Discrete Diffusion Models

`2407_21243` | authors: Yixiu Zhao, Jiaxin Shi, Feng Chen, Shaul Druckmann, Lester Mackey, Scott Linderman | year: 2024 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/lindermanlab/informed-correctors

### Method

- The authors propose a predictor-corrector sampling scheme called the informed corrector, which uses the diffusion model to counter accumulating approximation errors. (confidence: 1.00)
  Evidence: To address these limitations, we propose a predictor-corrector sampling scheme where the corrector is informed by the diffusion model to more reliably counter the accumulating approximation errors. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- The authors introduce architectural modifications based on hollow transformers and a tailored training objective to enhance the informed corrector. (confidence: 1.00)
  Evidence: To further enhance the effectiveness of our informed corrector, we introduce complementary architectural modifications based on hollow transformers and a simple tailored training objective that leverages more training signal. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- The paper focuses on the absorbing state process, also known as masked discrete diffusion, for the forward process. (confidence: 1.00)
  Evidence: We focus on the absorbing state process in this paper, for which the base rate matrix for each dimension can be written as [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/source.tex
- Tau-leaping is used as an approximate sampling method that allows simultaneous updates to multiple dimensions for a single model evaluation by assuming a constant backward process transition rate between intervals. (confidence: 1.00)
  Evidence: citet{campbell2022continuous} proposed to use tau-leaping, an approximate sampling method that allows simultaneous updates to multiple dimensions for a single model evaluation. Tau-leaping assumes that the backward process transition rate is constant between $[t-\tau, t)$, regardless of whether states change during that interval. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/source.tex

### Dataset

- The proposed method is evaluated on the text8 dataset. (confidence: 1.00)
  Evidence: On the text8 and tokenized ImageNet 256x256 datasets, our informed corrector consistently produces superior samples with fewer errors or improved FID scores for discrete diffusion models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- The proposed method is evaluated on the tokenized ImageNet 256x256 dataset. (confidence: 1.00)
  Evidence: On the text8 and tokenized ImageNet 256x256 datasets, our informed corrector consistently produces superior samples with fewer errors or improved FID scores for discrete diffusion models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md

### Claim

- The informed corrector consistently produces superior samples with fewer errors or improved FID scores for discrete diffusion models on text8 and tokenized ImageNet 256x256. (confidence: 1.00)
  Evidence: On the text8 and tokenized ImageNet 256x256 datasets, our informed corrector consistently produces superior samples with fewer errors or improved FID scores for discrete diffusion models. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- Sampling with the informed corrector drastically decreases the error rate in a synthetic example and in Text8, resulting in fewer spelling errors than baselines. (confidence: 1.00)
  Evidence: Sampling with the informed corrector drastically decreases error rate in our synthetic example, as well as in Text8, where the model makes much fewer spelling errors than baselines. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/source.tex

### Limitation

- Existing sampling strategies for discrete diffusion models often struggle to balance computation and sample quality when the number of sampling steps is reduced. (confidence: 1.00)
  Evidence: Existing sampling strategies often struggle to balance computation and sample quality when the number of sampling steps is reduced, even when the model has learned the data distribution well. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/summary.md
- Forward-backward corrector steps are suboptimal in practice because they can only correct mistakes by masking tokens at random. (confidence: 1.00)
  Evidence: Though forward-backward corrector steps solve the issue in theory, they are far from optimal in practice. The steps can only correct mistakes by masking tokens at random. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/2407_21243/source.tex

## Attention Is All You Need

`1706_03762` | authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin | year: 2017 | artifacts: equations, notes, paper_pdf, source_tex, summary, tldr | code: https://github.com/tensorflow/tensor2tensor

### Method

- The Transformer is a network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. (confidence: 1.00)
  Evidence: We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
- The Transformer uses Multi-Head Attention to counteract the reduced effective resolution caused by averaging attention-weighted positions. (confidence: 1.00)
  Evidence: In the Transformer this is reduced to a constant number of operations, albeit at the cost of reduced effective resolution due to averaging attention-weighted positions, an effect we counteract with Multi-Head Attention as described in section~\ref{sec:attention}. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/source.tex
- Self-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. (confidence: 1.00)
  Evidence: Self-attention, sometimes called intra-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/source.tex
- **Transformer attention architecture**: The Transformer replaces recurrence and convolution with attention-based sequence modeling. (confidence: 0.92)
  Evidence: The Transformer uses attention instead of recurrence or convolution. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md

### Benchmark

- The Transformer model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over existing best results by over 2 BLEU. (confidence: 1.00)
  Evidence: Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
- The Transformer model establishes a single-model state-of-the-art BLEU score of 41.8 on the WMT 2014 English-to-French translation task after training for 3.5 days on eight GPUs. (confidence: 1.00)
  Evidence: On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md

### Claim

- The Transformer generalizes well to other tasks, successfully applying to English constituency parsing with both large and limited training data. (confidence: 1.00)
  Evidence: We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
- The Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. (confidence: 1.00)
  Evidence: To the best of our knowledge, however, the Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. [source_tex] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/source.tex
- **Attention-only modeling**: Attention alone is presented as sufficient for the model architecture described in the paper summary. (confidence: 0.85)
  Evidence: The Transformer uses attention instead of recurrence or convolution. [summary] /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/papers/1706_03762/summary.md
