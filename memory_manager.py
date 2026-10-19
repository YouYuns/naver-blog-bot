# -*- coding: utf-8 -*-
"""
최근 30개 글 생성 이력 및 작가 페르소나 순환 관리 엔진 (memory_manager.py)
"""

import os
import json
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(CURRENT_DIR, "generation_memory.json")

PERSONAS = [
    {
        "id": "trendy",
        "name": "트렌드세터 2030 핫플러",
        "desc": "발랄하고 텐션 높은 어조, 이모지 풍부, 신조어/핫플 감성",
        "emojis": ["✨", "💖", "🔥", "😋", "📸", "👍", "👑"],
        "tone": "trendy"
    },
    {
        "id": "gourmet",
        "name": "정갈한 미식 탐방가",
        "desc": "차분하고 품격 있는 미식 비평 어조, 식재료 본연의 맛과 조리 기법 중심",
        "emojis": ["🍽️", "🥢", "🌿", "☕", "🎖️", "🍲"],
        "tone": "gourmet"
    },
    {
        "id": "honest",
        "name": "털털한 내돈내산 찐친",
        "desc": "가식 없는 솔직 담백 어조, 현실 웨이팅 체감, 가성비 및 솔직 평가",
        "emojis": ["👍", "💡", "👀", "💬", "💳", "😋"],
        "tone": "honest"
    },
    {
        "id": "healing",
        "name": "감성 힐링 에세이스트",
        "desc": "따스하고 서정적인 위로의 어조, 바쁜 일상 속 작은 쉼표와 온기",
        "emojis": ["🌿", "🌸", "🌤️", "💫", "☕", "🥰"],
        "tone": "healing"
    },
    {
        "id": "worker",
        "name": "퇴근길 직장인 & 실속파",
        "desc": "활기차고 실용적인 어조, 퇴근 후 힐링 한 끼, 스트레스 해소, 회식/모임 최적화",
        "emojis": ["⚡", "🍺", "🥢", "🍚", "👏", "🔥"],
        "tone": "worker"
    },
    {
        "id": "local",
        "name": "골목 숨은 고수 탐험가",
        "desc": "깊이 있고 정겨운 로컬 탐방 어조, 세월의 내공, 사장님의 푸근한 손맛",
        "emojis": ["🏮", "🍲", "🌾", "👵", "💯", "👍"],
        "tone": "local"
    }
]

PERSONA_MAP = {p["id"]: p for p in PERSONAS}


def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("recent_posts", [])
        except Exception as e:
            print(f"메모리 로드 오류: {e}")
            return []
    return []


def save_memory(recent_posts):
    try:
        trimmed = recent_posts[-50:]
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"recent_posts": trimmed}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"메모리 저장 실패: {e}")


def get_next_persona(force_id=None):
    if force_id and force_id in PERSONA_MAP:
        return PERSONA_MAP[force_id]

    memory = load_memory()
    if not memory:
        return PERSONAS[0]

    used_personas = [p.get("persona_id") for p in memory if p.get("persona_id")]
    scores = {}
    for p in PERSONAS:
        pid = p["id"]
        try:
            rev_idx = list(reversed(used_personas)).index(pid)
            scores[pid] = rev_idx
        except ValueError:
            scores[pid] = 999

    best_pid = max(scores, key=scores.get)
    return PERSONA_MAP[best_pid]


def get_recently_used_ids(category, limit=30):
    memory = load_memory()
    recent_slice = memory[-limit:]
    used_keys = set()
    for post in recent_slice:
        if category == "title":
            t_id = post.get("title_id")
            if t_id:
                used_keys.add(t_id)
        elif category == "intro":
            i_id = post.get("intro_id")
            if i_id:
                used_keys.add(i_id)
        elif category == "outro":
            o_id = post.get("outro_id")
            if o_id:
                used_keys.add(o_id)
        else:
            cat_map = post.get("photo_blocks", {})
            if category in cat_map:
                used_keys.update(cat_map[category])
    return used_keys


def record_post_generation(persona_id, title_id, intro_id, outro_id, photo_blocks, store_name=""):
    memory = load_memory()
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "store": store_name,
        "persona_id": persona_id,
        "title_id": title_id,
        "intro_id": intro_id,
        "outro_id": outro_id,
        "photo_blocks": photo_blocks
    }
    memory.append(entry)
    save_memory(memory)
    return entry


def clear_generation_memory():
    save_memory([])
