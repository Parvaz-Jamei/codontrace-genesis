# Research and protocol sources — reviewed 2026-10-11

Sources are primary publications, authors’ preprints or official specifications. Preprints are not automatically peer-reviewed findings. Related work is evidence of prior art, not evidence Genesis implements those entire algorithms.

| Source | Relevance / boundary |
|---|---|
| [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html) | QoS/duplicates, expiry, application correlation. Genesis uses node replies, bounded commands and no retained telemetry. |
| [Eclipse Paho Python client](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html) | MQTTv5 and version-2 callback API; optional dependency 2.1–<3. |
| [ROS and Buzz: consensus in heterogeneous teams](https://arxiv.org/abs/1710.08843) | Heterogeneous robot coordination already exists. Genesis V1 is centrally orchestrated sensor cooperation, not decentralized consensus. |
| [Self-Reconfigurable Heterogeneous Robotic Swarms](https://arxiv.org/abs/2004.13997) | Existing edge/cloud sensor-compute swarm architecture. Fault reallocation alone is not a new discovery. |
| [Online Distributed Sensor Selection](https://arxiv.org/abs/1002.1782) | Active sensor selection is established; oldest-first is only a baseline. |
| [RL Sensing Design in Resource-Constrained Wireless Networked Control Systems](https://arxiv.org/abs/2204.00703) | Scheduling under resource constraints; motivates measured budgets and comparative baselines. |
| [Noise2Noise, ICML 2018](https://proceedings.mlr.press/v80/lehtinen18a.html) | Learning denoising has existing theory/assumptions; Genesis EMA/clipping is not an implementation of Noise2Noise. |
| [Robots that can adapt like animals](https://arxiv.org/abs/1407.3501) | Archive-based adaptation has prior art; current PolicyArchive is a bounded pipeline candidate archive, not full MAP-Elites. |
| [FedConD](https://arxiv.org/abs/2109.00151) | Distributed concept drift prior art; local validation must handle changing contexts. |
| [Swarm Oracle, 2025 preprint](https://arxiv.org/abs/2509.15956) | Sensor consensus, reputation and Byzantine tolerance already investigated with robot experiments. Genesis V1 does not implement Byzantine consensus/blockchain. |
| [MoME, accepted CVPR 2025](https://arxiv.org/abs/2503.19776) | Robust fusion with modality-specific experts under sensor failure. Our scalar fusion is simpler and not equivalent to multimodal 3D perception. |

Potential Genesis research contribution: reproducible coupling of heterogeneous sensor streams, selective pipeline transfer and bounded co-adaptation under explicit information budgets. This is a research direction, not a demonstrated first-in-the-world result. Establish novelty through a task-specific literature comparison and locked experiments before publication claims.

## V3 research update

| Primary source | Specific design implication |
|---|---|
| [Mattson et al., Real2Sim2Real swarm behavior discovery, 2025](https://arxiv.org/abs/2502.15937) | Swarm behavior discovery and physical transfer have prior art. A sensor coordinator is not an implementation of this robot-learning method. |
| [Aljalbout et al., Reality Gap survey, 2025](https://arxiv.org/abs/2510.20808) | Explicit evaluation of simulation/physical discrepancies and metrics; author preprint, not a claim that our bridge closes the gap. |
| [Sandha et al., stochastic transition delays, CoRL/PMLR](https://proceedings.mlr.press/v155/sandha21a.html) | Evaluate sampling/latency shifts separately; noise-only tests cannot validate timing robustness. |
| [React useEffect](https://react.dev/reference/react/useEffect) | Ignore/abort stale fetches; capture export scope before asynchronous work. |
| [W3C Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) | Lifecycle meaning uses shapes/text as well as colors. |
| [W3C Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) | Replay/follow are user controlled; replay pause is distinct from worker control. |

The V3 empirical note uses exploratory seed-level paired percentile bootstrap intervals. It does not treat time samples as independent replications, infer physical performance, or report unadjusted intervals as confirmatory simultaneous evidence. See `docs/simulation/AUDIT_V3_FA.md` for a five-phase evaluation plan and actual measurements.
