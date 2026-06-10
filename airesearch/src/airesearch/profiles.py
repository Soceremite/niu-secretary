from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now


PRIMARY_SINCE = "2025-06-08"
EXCEPTION_SINCE = "2024-01-01"

PREFERRED_VENUES = [
    "CVPR",
    "ICCV",
    "ECCV",
    "ICLR",
    "ICML",
    "NeurIPS",
    "CoRL",
    "RSS",
    "ICRA",
    "IROS",
    "Science Robotics",
]

PREFERRED_ORGANIZATIONS = [
    "Google",
    "Google DeepMind",
    "DeepMind",
    "Meta",
    "NVIDIA",
    "OpenAI",
    "Anthropic",
    "Microsoft",
    "ByteDance",
    "DeepSeek",
    "Apple",
    "Tesla",
    "Figure AI",
    "Physical Intelligence",
    "MIT",
    "Stanford",
    "Berkeley",
    "UC Berkeley",
    "CMU",
    "Carnegie Mellon",
    "Princeton",
    "Harvard",
    "Oxford",
    "Cambridge",
    "ETH",
    "EPFL",
    "Tsinghua",
    "PKU",
    "Peking University",
    "Shanghai AI Lab",
    "NTU",
    "NUS",
]

PREFERRED_SCHOLARS = [
    "Kaiming He",
    "Fei-Fei Li",
    "Pieter Abbeel",
    "Sergey Levine",
    "Chelsea Finn",
    "Jitendra Malik",
    "Yann LeCun",
    "Yoshua Bengio",
    "Dieter Fox",
    "Anima Anandkumar",
]


@dataclass(frozen=True)
class ResearchProfile:
    name: str
    description: str
    keywords: list[str]
    preferred_venues: list[str]
    preferred_organizations: list[str]
    preferred_scholars: list[str]
    exception_keywords: list[str]
    primary_since: str = PRIMARY_SINCE
    exception_since: str = EXCEPTION_SINCE


def default_profiles() -> list[ResearchProfile]:
    return [
        ResearchProfile(
            name="multimodal_foundation_models",
            description="Recent multimodal foundation models, VLMs, MLLMs, and omni-modal systems.",
            keywords=[
                "multimodal foundation model",
                "vision-language model",
                "MLLM",
                "VLM",
                "omni-modal",
                "large multimodal model",
            ],
            preferred_venues=PREFERRED_VENUES,
            preferred_organizations=PREFERRED_ORGANIZATIONS,
            preferred_scholars=PREFERRED_SCHOLARS,
            exception_keywords=["GPT-4o", "Gemini", "Claude", "Llama", "Qwen", "VILA", "LLaVA"],
        ),
        ResearchProfile(
            name="unified_multimodal_understanding_generation",
            description="Unified models that combine multimodal understanding and generation.",
            keywords=[
                "unified multimodal understanding and generation",
                "unified vision-language",
                "image understanding and generation",
                "multimodal understanding generation",
                "autoregressive visual generation",
            ],
            preferred_venues=PREFERRED_VENUES,
            preferred_organizations=PREFERRED_ORGANIZATIONS,
            preferred_scholars=PREFERRED_SCHOLARS,
            exception_keywords=["VILA-U", "Show-o", "UniGen", "MMaDA", "Emu", "Chameleon"],
        ),
        ResearchProfile(
            name="world_models_physical_ai",
            description="World models, physical AI, video world models, and interactive simulators for agents.",
            keywords=[
                "world model",
                "world foundation model",
                "physical AI",
                "video world model",
                "interactive world model",
                "generative world model",
            ],
            preferred_venues=PREFERRED_VENUES,
            preferred_organizations=PREFERRED_ORGANIZATIONS,
            preferred_scholars=PREFERRED_SCHOLARS,
            exception_keywords=["Cosmos", "Genie", "Dreamer", "GAIA", "Sora", "V-JEPA"],
        ),
        ResearchProfile(
            name="diffusion_models",
            description="Diffusion models for multimodal generation, unified modeling, robotics, and policies.",
            keywords=[
                "diffusion model",
                "discrete diffusion",
                "multimodal diffusion",
                "diffusion policy",
                "flow matching",
                "rectified flow",
            ],
            preferred_venues=PREFERRED_VENUES,
            preferred_organizations=PREFERRED_ORGANIZATIONS,
            preferred_scholars=PREFERRED_SCHOLARS,
            exception_keywords=["Diffusion Policy", "DiT", "Stable Diffusion", "Imagen", "DALL-E", "Sora"],
        ),
        ResearchProfile(
            name="embodied_ai_vla_robotics",
            description="Embodied AI, VLA models, robot foundation models, and generalist robot policies.",
            keywords=[
                "embodied AI",
                "vision-language-action",
                "VLA",
                "robot foundation model",
                "generalist robot policy",
                "humanoid robot foundation model",
                "robotics foundation model",
            ],
            preferred_venues=PREFERRED_VENUES,
            preferred_organizations=PREFERRED_ORGANIZATIONS,
            preferred_scholars=PREFERRED_SCHOLARS,
            exception_keywords=["RT-2", "RT-X", "OpenVLA", "GR00T", "Gemini Robotics", "Magma"],
        ),
    ]


def as_json(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def seed_profiles(db_path: Path) -> int:
    init_db(db_path)
    now = utc_now()
    profiles = default_profiles()
    with connect(db_path) as conn:
        for profile in profiles:
            conn.execute(
                """
                insert into research_profiles (
                    name, description, keywords_json, preferred_venues_json,
                    preferred_organizations_json, preferred_scholars_json,
                    exception_keywords_json, primary_since, exception_since,
                    created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(name) do update set
                    description = excluded.description,
                    keywords_json = excluded.keywords_json,
                    preferred_venues_json = excluded.preferred_venues_json,
                    preferred_organizations_json = excluded.preferred_organizations_json,
                    preferred_scholars_json = excluded.preferred_scholars_json,
                    exception_keywords_json = excluded.exception_keywords_json,
                    primary_since = excluded.primary_since,
                    exception_since = excluded.exception_since,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.name,
                    profile.description,
                    as_json(profile.keywords),
                    as_json(profile.preferred_venues),
                    as_json(profile.preferred_organizations),
                    as_json(profile.preferred_scholars),
                    as_json(profile.exception_keywords),
                    profile.primary_since,
                    profile.exception_since,
                    now,
                    now,
                ),
            )
        conn.commit()
    return len(profiles)


def load_profile(db_path: Path, name: str) -> ResearchProfile:
    with connect(db_path) as conn:
        row = conn.execute("select * from research_profiles where name = ?", (name,)).fetchone()
    if row is None:
        raise ValueError(f"research profile not found: {name}")
    return ResearchProfile(
        name=row["name"],
        description=row["description"],
        keywords=json.loads(row["keywords_json"]),
        preferred_venues=json.loads(row["preferred_venues_json"]),
        preferred_organizations=json.loads(row["preferred_organizations_json"]),
        preferred_scholars=json.loads(row["preferred_scholars_json"]),
        exception_keywords=json.loads(row["exception_keywords_json"]),
        primary_since=row["primary_since"],
        exception_since=row["exception_since"],
    )
