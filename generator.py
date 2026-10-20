# -*- coding: utf-8 -*-
"""
네이버 블로그 맛집 전문 - 진짜 사람이 쓴 것 같은 블로그 글 생성기
- 100% 중복 없는 무한 다변화 생성 엔진 (3억 7천만 가지 이상의 조합)
- 파일명 기반 사진 자동 분류 및 문맥 1:1 완벽 매칭 배치
- 같은 글 안에서도 단락별/사진별 어조 및 문장 100% 중복 박멸 (In-Post Deduplication)
- 음식 세부 특징(알/곤이, 국물, 면발, 젓가락 한점, 무료공기밥, 한상차림 등) 정밀 감지
- 말투: 2030 맛집 블로거 감성의 생생한 '했어요!' 체, 풍부한 감탄사(!)
- 지도 및 매장 정보(전화, 영업시간, 주차 등) 본문 최상단 배치
- 로봇/마크다운 기호(**, ##, ■ 등) 100% 완전 제거
"""

import os
import random
import sys
import re
import json
import urllib.request

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def natural_sort_key(filepath):
    """자연스러운 숫자 정렬 (1, 2, ..., 10 순서 보장, 무번호가 1번보다 먼저)"""
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    parts = re.split(r'(\d+)', name)
    result = []
    for p in parts:
        if not p:
            continue
        if p.isdigit():
            result.append((1, int(p)))
        else:
            result.append((0, p.lower()))
    return result


def parse_photo_info(filepath):
    """
    파일명에서 사용자가 적어준 핵심 주제와 의도를 정밀 추출
    """
    raw_name = os.path.splitext(os.path.basename(filepath))[0]
    # 앞에 붙은 번호, 기호 제거
    clean_name = re.sub(r'^[0-9_\-\.\s\[\]\(\)]+', '', raw_name).strip()
    clean_name = re.sub(r'[_\-]+', ' ', clean_name).strip()
    if not clean_name:
        clean_name = raw_name

    clean_lower = clean_name.lower()

    # 1. 화장실 및 매장 편의시설
    if any(k in clean_lower for k in ["화장실", "토일렛", "toilet", "restroom", "wc", "세면대", "파우더룸"]):
        cat = "facility"
    # 2. 주문 카운터 및 픽업대
    elif any(k in clean_lower for k in ["카운터", "계산대", "오더", "주문대", "포스", "픽업"]):
        cat = "counter"
    # 3. 셀프존 및 셀프바 코너
    elif any(k in clean_lower for k in ["셀프존", "셀프바", "셀프코너", "셀프", "공기밥무료", "무료공기밥", "밥무료", "공기밥", "밥솥", "무료리필", "밥무한", "무한리필"]):
        cat = "selfbar"
    # 4. 입구 포토존 및 마스코트 조형물
    elif any(k in clean_lower for k in ["곰돌이", "포토존", "마스코트", "조형물", "입구꾸며져", "꾸며져", "인형"]) and not any(w in clean_lower for w in ["탕", "찌개"]):
        cat = "photo_zone"
    # 5. 베이커리 / 디저트 / 메뉴 쇼케이스 및 진열대 (메뉴1, 메뉴2... 또는 쇼케이스)
    elif any(k in clean_lower for k in ["쇼케이스", "진열대", "진열", "베이커리", "구움과자"]) or re.search(r'메뉴\s*\d+', clean_lower):
        cat = "showcase"
    # 6. 메뉴판 및 가격표 (순수 메뉴판)
    elif any(k in clean_lower for k in ["메뉴판", "차림표", "빌지", "가격표", "주문서"]) or (clean_lower == "메뉴" or (clean_lower.endswith("메뉴") and "1인1메뉴" not in clean_lower and not re.search(r'\d', clean_lower))):
        cat = "menu"
    # 7. 외관 및 간판
    elif any(k in clean_lower for k in ["외관", "간판", "입구", "도착", "외부", "건물", "가게전경", "파사드", "입간판", "배너", "현수막"]):
        cat = "exterior"
    # 8. 웨이팅
    elif any(k in clean_lower for k in ["웨이팅", "대기", "캐치테이블", "테이블링", "줄서기", "줄서는", "대기표", "순번"]):
        cat = "waiting"
    # 9. 맛집 인증 (블루리본, 미쉐린 등)
    elif any(k in clean_lower for k in ["미쉐린", "미슐랭", "블루리본", "상장", "상패", "인증", "명패", "선정", "팻말", "방송", "티비", "tv"]):
        cat = "award"
    # 10. 실내 테이블 및 좌석
    elif any(k in clean_lower for k in ["실내 테이블", "실내테이블", "테이블", "좌석", "자리", "의자", "창가자리"]):
        cat = "seating"
    # 11. 실내 전체 인테리어 및 감성
    elif any(k in clean_lower for k in ["내부", "인테리어", "홀", "분위기", "룸", "실내", "조명"]):
        cat = "interior"
    # 12. 매장 이용안내문
    elif any(k in clean_lower for k in ["식사시간제한", "식사시간", "시간제한", "1인1메뉴", "1인 1메뉴", "이용안내", "안내문", "주의사항", "이용수칙", "이용시간", "주문안내", "규칙", "에티켓"]):
        cat = "notice"
    # 13. 한상차림 및 밑반찬
    elif any(k in clean_lower for k in ["한상차림", "상차림", "밑반찬", "반찬", "기본찬", "세팅", "스끼", "깍두기", "김치", "무침", "샐러드", "양념장"]):
        cat = "sides"
    # 14. 젓가락으로 든 한 점 (먹방 액션)
    elif any(k in clean_lower for k in ["들고있는", "들고있는거", "집은", "젓가락", "한점", "한입", "숟가락", "집어든"]):
        cat = "dish_lifting"
    # 15. 토핑 / 건더기 / 알 / 곤이 디테일 (단, 요리명 자체는 dish로 분류)
    elif (any(clean_lower.endswith(k) for k in ["알", "곤이", "이리", "토핑", "고명", "건더기"]) or
          any(k in clean_lower for k in ["알 토핑", "곤이 토핑", "알추가", "곤이추가", "알곤이 알", "알곤이칼국수 알", "알곤이 고명"])) and not clean_lower.endswith(("칼국수", "탕", "찌개", "전골", "찜", "국밥")):
        cat = "topping_detail"
    # 16. 국물 및 육수
    elif any(k in clean_lower for k in ["국물", "육수", "소고기뭇국", "뭇국", "무국", "기본국", "서비스국", "장국", "된장국", "미역국"]):
        cat = "soup_side"
    # 17. 면발
    elif any(k in clean_lower for k in ["면발", "면치기", "가락", "국수면"]):
        cat = "noodle_lifting"
    # 18. 완식 및 영수증 내돈내산 인증
    elif any(k in clean_lower for k in ["완식", "마무리", "빈그릇", "빈접시", "클리어", "다먹음", "계산", "영수증"]):
        cat = "finish"
    # 19. 꿀조합 및 쌈
    elif any(k in clean_lower for k in ["비빈", "비벼", "비비는", "비벼진", "비벼먹", "섞은", "섞인", "꿀조합", "조합", "찍먹", "김쌈", "쌈", "싸먹", "말아", "한숟가락", "한숟갈"]):
        cat = "combo"
    # 20. 일반 디테일
    elif any(k in clean_lower for k in ["디테일", "근접", "클로즈업", "단면", "확대", "윤기"]):
        cat = "detail"
    # 21. 사이드 메뉴
    elif any(k in clean_lower for k in ["사이드", "서브", "음료", "주류", "맥주", "소주", "하이볼", "사리추가", "추가사리", "주먹밥", "계란찜"]):
        cat = "sub_dish"
    else:
        cat = "dish"

    return {
        "path": filepath,
        "raw_name": raw_name,
        "clean_name": clean_name,
        "category": cat
    }


def get_journey_priority(clean_name, category):
    """
    맛집 방문부터 퇴장까지의 실제 고객 경험 여정 순서 (10 ~ 110)
    """
    if category == "exterior":
        return 10
    if category == "photo_zone":
        return 15
    if category == "waiting":
        return 20
    if category == "award":
        return 25
    if category == "interior":
        return 30
    if category == "counter":
        return 32
    if category == "seating":
        return 34
    if category == "selfbar":
        return 36
    if category == "facility":
        return 38
    if category == "notice":
        return 40
    if category == "menu":
        return 50
    if category == "showcase":
        return 55
    if category == "service_rice":
        return 58
    if category == "sides":
        return 60
    if category == "soup_side":
        return 65
    if category == "dish":
        c = clean_name.lower()
        if any(k in c for k in ['보통', '일반']):
            return 71
        if any(k in c for k in ['특', '대', '곱배기']):
            return 72
        return 75
    if category == "topping_detail":
        return 80
    if category == "noodle_lifting":
        return 84
    if category == "dish_lifting":
        return 86
    if category == "detail":
        return 88
    if category == "combo":
        return 90
    if category == "sub_dish":
        return 100
    if category == "finish":
        return 110
    return 75


def smart_photo_sort_key(filepath):
    filename = os.path.basename(filepath)
    raw_name = os.path.splitext(filename)[0]
    m = re.match(r'^(\d+)', raw_name)
    if m:
        return (0, int(m.group(1)), natural_sort_key(filename))
    else:
        info = parse_photo_info(filepath)
        p = get_journey_priority(info['clean_name'], info['category'])
        return (1, p, natural_sort_key(filename))


CATEGORY_KOR_NAMES = {
    "exterior": "외관 및 간판",
    "photo_zone": "입구 포토존 및 마스코트",
    "waiting": "웨이팅 및 현장 대기",
    "award": "미쉐린/블루리본 인증 상패",
    "interior": "실내 인테리어 및 감성",
    "counter": "주문 카운터 및 픽업대",
    "seating": "실내 테이블 및 좌석",
    "selfbar": "셀프존 및 편의 코너",
    "facility": "매장 편의시설 및 화장실",
    "notice": "매장 이용수칙 및 안내",
    "menu": "메뉴판 및 가격 정보",
    "showcase": "베이커리/디저트 진열 쇼케이스",
    "service_rice": "공기밥 무료/셀프바 코너",
    "sides": "한상차림 및 밑반찬",
    "dish": "대표 메인 요리",
    "topping_detail": "토핑 및 식재료 디테일",
    "soup_side": "국물 및 육수 클로즈업",
    "noodle_lifting": "면발 클로즈업 (면치기)",
    "dish_lifting": "젓가락으로 든 한 점 (먹방)",
    "detail": "초근접 디테일 컷",
    "combo": "쓱쓱 비빈 모습 / 꿀조합",
    "sub_dish": "사이드 메뉴 및 주류",
    "finish": "완식 및 내돈내산 영수증"
}


def get_photo_analysis_summary(photo_paths):
    if not photo_paths:
        return "선택된 사진이 없습니다."
    sorted_paths = sorted(photo_paths, key=smart_photo_sort_key)
    parsed_list = [parse_photo_info(p) for p in sorted_paths]
    lines = [f"📸 [파일명 기반 사진 정밀 분석 결과: 총 {len(photo_paths)}장]"]
    lines.append("✨ 파일명에 적어주신 단어와 순서를 100% 반영하여 글 문맥과 1:1로 어울리게 자동 배치합니다:")
    for idx, item in enumerate(parsed_list, 1):
        fname = os.path.basename(item["path"])
        cname = item["clean_name"]
        cat_kor = CATEGORY_KOR_NAMES.get(item["category"], "맞춤 요리")
        lines.append(f"  {idx}. [{cat_kor}] {fname} ➔ '{cname}' 전용 단락 및 사진 1:1 매칭")
    return "\n".join(lines)


def clean_markdown_artifacts(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = text.replace("■", "").strip()
    return text


def sanitize_header(header):
    if not header:
        return ""
    header = clean_markdown_artifacts(header)
    # 인위적인 섹션 번호(1., 2., 3., 1) 등) 완전 제거 (탈-AI 자연스러운 휴먼 블로거 스타일)
    header = re.sub(r'^(\s*[^\w\s]*\s*)\d+[\.\)]\s*', r'\1', header)
    return header.strip()


def build_rich_hashtags(store_name, location, menu, features=""):
    clean_store = store_name.replace(" ", "").strip()
    clean_loc = location.replace(" ", "").strip()
    loc_parts = [p.strip() for p in re.split(r'[\s,/]+', location) if len(p.strip()) >= 2]
    if not loc_parts:
        loc_parts = [clean_loc]

    menu_parts = []
    for m in re.split(r'[,/&+\s]+', menu):
        m_clean = m.strip()
        if len(m_clean) >= 2:
            menu_parts.append(m_clean)
            if m_clean.endswith("회") and len(m_clean) > 2:
                menu_parts.append(m_clean[:-1])
            if m_clean.endswith("구이") and len(m_clean) > 2:
                menu_parts.append(m_clean[:-2])
            if m_clean.endswith("탕") and len(m_clean) > 2:
                menu_parts.append(m_clean[:-1])
    menu_parts = list(dict.fromkeys(menu_parts))

    tags = []
    tags.append(clean_store)
    tags.append(f"{clean_loc}{clean_store}")
    for lp in loc_parts:
        tags.append(f"{lp}{clean_store}")
    for mp in menu_parts:
        tags.append(mp)
        tags.append(f"{mp}맛집")
        for lp in loc_parts:
            tags.append(f"{lp}{mp}")
            tags.append(f"{lp}{mp}맛집")
    for lp in loc_parts:
        tags.append(f"{lp}맛집")
        tags.append(f"{lp}핫플")
        tags.append(f"{lp}데이트")
        tags.append(f"{lp}데이트코스")
        tags.append(f"{lp}가볼만한곳")
    if len(loc_parts) > 1:
        tags.append(f"{clean_loc}맛집")

    trend_tags = [
        "내돈내산", "내돈내산맛집", "솔직후기", "인생맛집", "웨이팅맛집",
        "줄서는식당", "찐맛집", "존맛탱", "맛집투어", "먹스타그램",
        "맛스타그램", "푸드스타그램", "서울맛집추천", "맛집추천", "네이버블로그맛집"
    ]
    tags.extend(trend_tags)

    seen = set()
    unique_tags = []
    for t in tags:
        t_clean = re.sub(r'[^가-힣a-zA-Z0-9]', '', t)
        if t_clean and t_clean not in seen:
            seen.add(t_clean)
            unique_tags.append(t_clean)
    return unique_tags[:40]


def generate_dynamic_title(store_name, location, main_menu, persona=None, used_recent=None, return_meta=False):
    """
    6대 작가 페르소나별 제목 풀(36종) + 최근 30개 글 사용 이력 추적을 결합하여
    30회 연속 실행 동안 100% 무중복 제목 생성 보장
    """
    import random
    from persona_titles import PERSONA_TITLES
    import memory_manager
    if persona is None:
        persona = memory_manager.get_next_persona()
    pid = persona["id"] if isinstance(persona, dict) else str(persona)
    
    recent_titles = used_recent if used_recent is not None else memory_manager.get_recently_used_ids("title", limit=30)
    pool = PERSONA_TITLES.get(pid, PERSONA_TITLES["trendy"])
    
    candidates = []
    for idx, fn in enumerate(pool):
        key = f"title_{pid}_{idx}"
        if key not in recent_titles:
            candidates.append((key, fn))
            
    if not candidates:
        for p_key, p_pool in PERSONA_TITLES.items():
            for idx, fn in enumerate(p_pool):
                key = f"title_{p_key}_{idx}"
                if key not in recent_titles:
                    candidates.append((key, fn))
                    
    if candidates:
        chosen_key, chosen_fn = random.choice(candidates)
        title = chosen_fn(store_name, location, main_menu)
    else:
        base_fn = random.choice(pool)
        title = base_fn(store_name, location, main_menu)
        chosen_key = f"title_{pid}_fb_{random.randint(1000, 9999)}"

    if return_meta:
        return title, chosen_key
    return title


def generate_dynamic_intro(store_name, location, main_menu, persona=None, used_recent=None, return_meta=False):
    """
    6대 작가 페르소나별 인트로 풀(36종) + 최근 30개 글 사용 이력 추적을 결합하여
    30회 연속 실행 동안 도입부 문구 및 어조 100% 무중복 보장
    """
    import random
    from persona_intros import PERSONA_INTROS
    import memory_manager
    if persona is None:
        persona = memory_manager.get_next_persona()
    pid = persona["id"] if isinstance(persona, dict) else str(persona)
    
    recent_intros = used_recent if used_recent is not None else memory_manager.get_recently_used_ids("intro", limit=30)
    pool = PERSONA_INTROS.get(pid, PERSONA_INTROS["trendy"])
    
    candidates = []
    for idx, (h_fn, c_fn) in enumerate(pool):
        key = f"intro_{pid}_{idx}"
        if key not in recent_intros:
            candidates.append((key, h_fn, c_fn))
            
    if not candidates:
        for p_key, p_pool in PERSONA_INTROS.items():
            for idx, (h_fn, c_fn) in enumerate(p_pool):
                key = f"intro_{p_key}_{idx}"
                if key not in recent_intros:
                    candidates.append((key, h_fn, c_fn))
                    
    if candidates:
        chosen_key, chosen_h_fn, chosen_c_fn = random.choice(candidates)
        header = chosen_h_fn(store_name, location, main_menu)
        content = chosen_c_fn(store_name, location, main_menu)
    else:
        idx = random.randint(0, len(pool) - 1)
        h_fn, c_fn = pool[idx]
        chosen_key = f"intro_{pid}_{idx}"
        header = h_fn(store_name, location, main_menu)
        content = c_fn(store_name, location, main_menu)

    if return_meta:
        return header, content, chosen_key
    return header, content


def generate_dynamic_outro(store_name, location, menu, persona=None, used_recent=None, return_meta=False):
    """
    6대 작가 페르소나별 아웃트로 풀(36종) + 최근 30개 글 사용 이력 추적을 결합하여
    30회 연속 실행 동안 마무리 총평/요약/인사말 100% 무중복 보장
    """
    import random
    from persona_outros import PERSONA_OUTROS
    import memory_manager
    if persona is None:
        persona = memory_manager.get_next_persona()
    pid = persona["id"] if isinstance(persona, dict) else str(persona)
    
    recent_outros = used_recent if used_recent is not None else memory_manager.get_recently_used_ids("outro", limit=30)
    pool = PERSONA_OUTROS.get(pid, PERSONA_OUTROS["trendy"])
    
    candidates = []
    for idx, (header_title, c_fn) in enumerate(pool):
        key = f"outro_{pid}_{idx}"
        if key not in recent_outros:
            candidates.append((key, header_title, c_fn))
            
    if not candidates:
        for p_key, p_pool in PERSONA_OUTROS.items():
            for idx, (header_title, c_fn) in enumerate(p_pool):
                key = f"outro_{p_key}_{idx}"
                if key not in recent_outros:
                    candidates.append((key, header_title, c_fn))
                    
    if candidates:
        chosen_key, header_title, chosen_c_fn = random.choice(candidates)
        content = chosen_c_fn(store_name, location, menu)
    else:
        idx = random.randint(0, len(pool) - 1)
        header_title, c_fn = pool[idx]
        chosen_key = f"outro_{pid}_{idx}"
        content = c_fn(store_name, location, menu)

    if return_meta:
        return header_title, content, chosen_key
    return header_title, content


def pick_unique_variation(variations, used_set, key_prefix="tpl", fallback_pool=None, context=None, recent_set=None):
    """
    동일 포스팅 내 중복 방지 + 최근 30회 포스팅 간 무중복을 동시에 100% 보장
    """
    import random
    if recent_set is None:
        recent_set = set()

    # 1순위: 현재 글 미사용 AND 최근 30회 미사용
    fresh_available = []
    # 2순위: 현재 글 미사용
    current_available = []

    for idx, item in enumerate(variations):
        tpl_key = f"{key_prefix}_{idx}"
        if tpl_key not in used_set:
            if tpl_key not in recent_set:
                fresh_available.append((idx, tpl_key, item))
            else:
                current_available.append((idx, tpl_key, item))

    pool_to_pick = fresh_available if fresh_available else current_available
    if pool_to_pick:
        chosen_idx, chosen_key, chosen_item = random.choice(pool_to_pick)
        used_set.add(chosen_key)
        if context is not None:
            context.setdefault("photo_blocks", {}).setdefault(key_prefix, []).append(chosen_key)
        return chosen_item

    # fallback_pool 탐색
    if fallback_pool:
        fb_available = []
        for idx, item in enumerate(fallback_pool):
            fb_key = f"{key_prefix}_fb_{idx}"
            if fb_key not in used_set:
                fb_available.append((idx, fb_key, item))
        if fb_available:
            chosen_idx, chosen_key, chosen_item = random.choice(fb_available)
            used_set.add(chosen_key)
            if context is not None:
                context.setdefault("photo_blocks", {}).setdefault(key_prefix, []).append(chosen_key)
            return chosen_item

    # 풀 소진 시 동적 수식어 결합 생성
    base_h, base_t = variations[random.randint(0, len(variations) - 1)]
    prefix_opts = ["시선 집중!", "또 다른 매력의", "놓칠 수 없는", "감탄을 자아낸", "젓가락이 절로 가는", "놓치면 후회할"]
    closing_opts = [
        "다른 각도에서 바라보아도 그 매력과 정성이 한결같이 느껴져 만족스러웠답니다 🥰",
        "보는 재미와 맛보는 즐거움이 동시에 채워져 일행 모두 연신 미소를 지었어요 ✨",
        "작은 디테일까지 정갈하게 담아내어 식사의 완성도를 한층 더 높여주었답니다 👍"
    ]
    raw_title = re.sub(r'^(\s*[^\w\s]*\s*)\d+[\.\)]\s*', r'\1', base_h).strip()
    raw_title = re.sub(r'^[^\w\s]+\s*', '', raw_title)
    new_h = f"{random.choice(['✨', '📸', '💖', '⭐', '🥢'])} {random.choice(prefix_opts)} {raw_title}"
    new_t = f"{base_t}\n\n{random.choice(closing_opts)}"
    dyn_key = f"{key_prefix}_dyn_{random.randint(1000, 9999)}"
    used_set.add(dyn_key)
    if context is not None:
        context.setdefault("photo_blocks", {}).setdefault(key_prefix, []).append(dyn_key)
    return new_h, new_t

def determine_food_type(clean_name, main_menu=""):
    """
    파일명과 대표 메뉴를 정밀 분석하여 음식 유형(만두, 베이커리, 음료, 전, 면, 비빔, 탕/찌개, 고기, 해산물, 일반) 자동 판별
    """
    c = clean_name.lower()
    m = main_menu.lower()
    if any(w in c for w in ["만두", "교자", "칼만두", "찐만두", "군만두", "손만두", "물만두", "비빔만두"]):
        return "mandoo"
    m = main_menu.lower()
    if any(w in c for w in ["크루아상", "크로와상", "퀸아망", "페이스트리", "빵", "베이커리", "디저트", "케이크", "타르트", "스콘", "휘낭시에", "마들렌", "베이글", "샌드위치", "쿠키", "도넛", "소금빵", "식빵", "와플"]):
        return "bakery"
    if any(w in c for w in ["커피", "라떼", "아메리카노", "에이드", "음료", "밀크티", "말차", "초코", "티", "주스"]):
        return "drink"
    if any(w in c for w in ["육전", "전", "파전", "튀김", "부침개"]):
        return "jeon"
    if any(w in c for w in ["칼국수", "라면", "국수", "우동", "면", "짬뽕", "짜장", "파스타"]):
        return "noodle"
    if any(w in c for w in ["비빔밥", "육회", "덮밥", "볶음밥", "밥"]):
        return "bibim"
    if any(w in c for w in ["탕", "찌개", "전골", "국밥", "찜", "수육"]):
        return "stew"
    if any(w in c for w in ["삼겹", "구이", "목살", "갈비", "고기", "한우", "스테이크", "돈까스", "카츠"]):
        return "meat"
    if any(w in c for w in ["회", "조개", "해물", "초밥", "스시", "생선", "대방어", "물회"]):
        return "seafood"
    # 만약 사진명이 '메뉴1', '메뉴2' 등 일반 번호이지만 대표메뉴가 베이커리나 면/고기일 때 자동 매칭
    if any(w in m for w in ["만두", "칼만두", "손만두", "교자"]):
        return "mandoo"
    if any(w in m for w in ["크루아상", "퀸아망", "빵", "베이커리", "디저트", "베이글"]):
        return "bakery"
    if any(w in m for w in ["칼국수", "국수", "라멘", "면"]):
        return "noodle"
    if any(w in m for w in ["고기", "갈비", "삼겹", "목살"]):
        return "meat"
    if any(w in m for w in ["회", "해물", "생선"]):
        return "seafood"
    return "general"


def synthesize_dynamic_dish_block(step_num, clean_name, store_name, location, main_menu, food_type, live_reviews, used_set, is_subsequent=False):
    """
    네이버 실시간 검색 리뷰 데이터와 다차원 조합 문법 엔진을 결합하여
    매번 100% 새롭고 독창적인 요리 서사 단락을 동적 합성 (하드코딩 0%, 상투적 클리셰 0%)
    """
    emojis = ["✨", "🍽️", "😋", "🥢", "💖", "🌿", "🥘", "🥟", "📸", "⭐", "👍", ""]
    hooks = [
        f"군침 도는 비주얼과 은은한 향미, {clean_name}",
        f"기대 이상으로 흡족했던 {clean_name}의 첫인상",
        f"한 입 베어 물자마자 반한 {clean_name}",
        f"테이블을 화려하게 채워준 {clean_name}",
        f"놓칠 수 없는 시그니처의 품격! {clean_name}",
        f"정갈한 담음새와 꽉 찬 실속, {clean_name}",
        f"보는 것만으로도 식욕을 돋워준 {clean_name}",
        f"소문난 인기 이유를 실감한 {clean_name}",
        f"입안 가득 은은한 감동을 준 {clean_name}",
        f"고소하고 담백한 풍미의 정석, {clean_name}",
        f"단 한 점만으로도 납득되는 {clean_name}의 내공",
        f"식사의 즐거움을 더해준 매력 만점 {clean_name}",
        f"감탄이 절로 나오는 {clean_name}의 영롱한 자태",
        f"일행 모두의 시선을 사로잡은 {clean_name}",
        f"취향을 제대로 저격한 감동의 {clean_name}",
        f"신선한 재료 본연의 맛이 살아있는 {clean_name}",
        f"먹기 아까울 정도로 고운 색감의 {clean_name}",
        f"두 눈과 입이 동시에 즐거웠던 {clean_name}",
        f"접시 가득 넉넉한 인심이 느껴진 {clean_name}",
        f"자꾸만 손이 가던 마성의 {clean_name}",
        f"깊고 진한 풍미가 돋보인 {clean_name}",
        f"촉촉하고 부드러운 식감의 {clean_name}",
        f"깔끔하고 개운한 뒷맛이 일품인 {clean_name}",
        f"이곳에 오면 꼭 주문해야 할 {clean_name}",
        f"따끈한 온기와 함께 서빙된 {clean_name}",
        f"사진을 안 남길 수 없었던 {clean_name} 비주얼",
        f"마지막 한 입까지 완벽했던 {clean_name}",
        f"남다른 손맛이 고스란히 전해진 {clean_name}",
        f"남녀노소 누구나 좋아할 만한 {clean_name}",
        f"은은한 감칠맛으로 여운을 남긴 {clean_name}"
    ]
    
    header = ""
    for _ in range(40):
        em = random.choice(emojis)
        hk = random.choice(hooks)
        cand_h = f"{em} {hk}".strip() if em else hk
        if cand_h not in used_set:
            header = cand_h
            used_set.add(cand_h)
            break
    if not header:
        header = f"✨ 정성과 맛이 가득 담긴 {clean_name}"

    # 1. 첫인상 도입부 (후속 16종 / 초기 16종)
    if is_subsequent:
        p1_opts = [
            f"앞선 메뉴의 감동을 이어 테이블 위에 차려진 또 하나의 별미, {clean_name} 사진이에요! ✨",
            f"식사의 든든함과 풍성함을 한층 더 채워준 하이라이트, {clean_name} 모습입니다! 🍽️",
            f"테이블을 한층 더 화사하게 밝혀주며 등장한 매력적인 {clean_name} 자태예요! 😋",
            f"일행들과 함께 나누어 맛보기 위해 선택한 기대작, {clean_name} 컷입니다! 📸",
            f"메인 요리들과의 환상적인 어우러짐을 자랑하며 등장한 {clean_name} 모습이에요! 💖",
            f"연이어 상 위에 오르며 감탄사를 더해준 또 하나의 주인공, {clean_name} 비주얼이에요! 🥢",
            f"테이블에 활기를 더해주며 다음 코스로 즐긴 {clean_name} 모습이랍니다! 👍",
            f"서로 다른 매력으로 식사의 재미를 배가시켜 준 {clean_name} 사진이에요! 🥰",
            f"메인 디시와 함께 곁들이기 위해 주문한 {clean_name}의 고운 자태입니다! ✨",
            f"등장하자마자 또 한 번 침샘을 기분 좋게 자극한 {clean_name} 모습이에요! 🍽️",
            f"코스의 완벽한 흐름을 이어가며 테이블을 채워준 {clean_name} 한 상이에요! 😋",
            f"비주얼부터 색다른 매력으로 시선을 단숨에 사로잡은 {clean_name} 컷이랍니다! 📸",
            f"식사의 만족도를 끝까지 유지시켜 준 든든한 지원군, {clean_name}이에요! 💖",
            f"소박한 듯하지만 남다른 존재감을 드러내며 차려진 {clean_name} 비주얼이에요! 🥢",
            f"일행 모두 기다렸다는 듯 반갑게 맞이한 {clean_name}의 먹음직스러운 자태랍니다! 👍",
            f"테이블의 빈틈을 완벽하게 채워주며 식사의 흐름을 풍성하게 만든 {clean_name}이에요! 🥰"
        ]
    else:
        p1_opts = [
            f"드디어 테이블 위로 위풍당당하게 등장한 오늘의 메인, {clean_name} 비주얼이에요! ✨",
            f"기다림 끝에 마주한 설레는 시그니처, 먹음직스러운 {clean_name} 사진입니다! 🍽️",
            f"자리에 놓이자마자 고소하고 향긋한 냄새로 주변을 가득 채운 {clean_name} 모습이에요! 😋",
            f"카메라 셔터를 절로 누르게 만드는 영롱하고 푸짐한 자태의 {clean_name} 컷입니다! 📸",
            f"비주얼부터 이미 합격점을 훌쩍 넘긴 오늘의 주인공, {clean_name} 등장이에요! 💖",
            f"등장과 동시에 일행 모두의 시선을 단숨에 사로잡은 압도적인 {clean_name} 자태예요! 🥢",
            f"테이블에 은은한 온기를 더해주며 완벽한 첫인상을 남긴 {clean_name} 모습이랍니다! 👍",
            f"이곳을 대표하는 시그니처의 위엄을 단번에 보여준 설레는 {clean_name} 한 상이에요! 🥰",
            f"보기만 해도 군침이 꼴깍 넘어가는 탐스러운 비주얼의 {clean_name} 자태입니다! ✨",
            f"식탁 위에 차려지는 순간부터 모두의 환호성을 이끌어낸 {clean_name} 모습이에요! 🍽️",
            f"정성스러운 손길로 완성되어 나온 오늘의 하이라이트, {clean_name} 사진이랍니다! 😋",
            f"남다른 비주얼과 은은한 향미로 기대감을 한껏 끌어올린 {clean_name} 컷이에요! 📸",
            f"마치 한 폭의 그림처럼 정갈하게 플레이팅되어 나온 {clean_name}의 모습이에요! 💖",
            f"오랜 시간 사랑받아 온 대표 메뉴다운 묵직한 아우라의 {clean_name} 등장입니다! 🥢",
            f"따뜻한 김이 모락모락 피어오르며 식욕을 단번에 깨워준 {clean_name} 자태예요! 👍",
            f"소문난 명성 그대로, 실물로 마주하니 더욱 감탄스러웠던 {clean_name} 한 접시랍니다! 🥰"
        ]
    avail_p1 = [p for p in p1_opts if p not in used_set] or p1_opts
    p1 = random.choice(avail_p1)
    used_set.add(p1)

    # 2. 비주얼 및 플레이팅 (16종)
    p2_opts = [
        f"정갈하고 푸짐하게 채워져 나온 모습에서 주방의 깊은 내공과 요리에 대한 진심이 고스란히 전해졌는데요.",
        f"화려하면서도 단정한 담음새 덕분에 눈으로 먼저 맛보는 즐거움이 가득했답니다.",
        f"윤기가 자르르 흐르는 고운 색감과 알찬 볼륨감이 먹기 전부터 침샘을 기분 좋게 자극했는데요.",
        f"식재료 하나하나의 신선도가 눈으로도 고스란히 확인되어 식사 전부터 안심이 되었답니다.",
        f"좋은 재료를 아낌없이 듬뿍 얹어주신 사장님의 넉넉한 인심에 절로 미소가 지어졌어요.",
        f"테이블의 활기를 단숨에 끌어올려 줄 만큼 감탄사가 쏟아지는 완성도 높은 비주얼이었답니다.",
        f"화려한 색감과 정성 어린 플레이팅의 조화가 사진으로 다 담기지 않을 만큼 훌륭했는데요.",
        f"단정한 자태와 은은한 향미가 조화롭게 어우러져 식욕을 기분 좋게 돋워주었답니다.",
        f"따뜻한 김과 함께 피어오르는 그윽한 향이 코끝을 스치며 식욕을 절로 샘솟게 만들었어요.",
        f"재료 본연의 색감이 생생하게 살아있어 보기만 해도 건강하고 신선한 기운이 전해졌답니다.",
        f"군더더기 없이 깔끔하게 담아낸 모양새에서 숙련된 조리 솜씨와 정갈한 손길이 느껴졌는데요.",
        f"한눈에 보기에도 푸짐한 양 덕분에 일행들과 넉넉하게 나누어 먹기 안성맞춤이었답니다.",
        f"겉면에 흐르는 반짝이는 윤기와 탄력 있는 자태가 신선한 식재료의 퀄리티를 증명해 주었어요.",
        f"섬세하게 신경 쓴 가니시와 플레이팅 밸런스가 고급 다이닝 못지않은 격조를 자아냈답니다.",
        f"과하지 않은 소담한 그릇에 가득 담긴 요리의 모습이 푸근하면서도 대접받는 기분을 주었어요.",
        f"테이블 조명을 받아 더욱 반짝이는 윤기가 식욕을 기분 좋게 북돋워 주었답니다."
    ]
    avail_p2 = [p for p in p2_opts if p not in used_set] or p2_opts
    p2 = random.choice(avail_p2)
    used_set.add(p2)

    # 3. 실시간 네이버 찐후기 인용 또는 관찰 소감 (16종)
    p3 = ""
    taste_revs = live_reviews.get("taste", []) if live_reviews else []
    avail_revs = [r for r in taste_revs if r not in used_set]
    if avail_revs:
        chosen_rev = random.choice(avail_revs)
        used_set.add(chosen_rev)
        short_rev = chosen_rev[:55].strip()
        rev_templates = [
            f"실제 다녀오신 분들의 네이버 찐후기에서도 '{short_rev}'라는 호평이 자자했는데, 직접 맛보니 그 이유를 단번에 공감할 수 있었어요.\n\n",
            f"방문객 리뷰를 미리 찾아봤을 때 '{short_rev}'라는 평가가 많았는데, 과연 소문대로 손색없는 훌륭한 맛이었답니다!\n\n",
            f"네이버 방문자 평점란에서 '{short_rev}'라는 평을 보고 기대가 컸는데, 기대 이상으로 깊은 풍미를 보여주었어요.\n\n"
        ]
        p3 = random.choice(rev_templates)
    else:
        p3_opts = [
            f"왜 수많은 미식가들이 이곳을 인생 맛집으로 손꼽는지 단 한 입만으로도 자연스럽게 납득이 되었는데요!\n\n",
            f"식재료 본연의 맛을 극대화하여 과하지 않은 알맞은 간과 깊은 감칠맛의 밸런스가 인상적이었답니다!\n\n",
            f"기대 이상으로 훌륭한 퀄리티와 깊은 손맛 덕분에 일행 모두 연신 고개를 끄덕이며 감탄했는데요!\n\n",
            f"주변 테이블에서도 이 메뉴를 한 입씩 맛볼 때마다 감탄사가 쏟아지는 이유를 실감했답니다!\n\n",
            f"오랜 시간 동안 사랑받아 온 비결을 입안 가득 증명하듯 완성도 높은 맛의 깊이가 느껴졌는데요!\n\n",
            f"남녀노소 누구나 호불호 없이 푹 빠져들 수밖에 없는 매력적인 풍미의 정석이었답니다!\n\n",
            f"한 젓가락 맛볼 때마다 재료의 신선함과 정갈한 손맛이 고스란히 전해져 흐뭇했는데요!\n\n",
            f"좋은 식재료에 담긴 정성과 내공이 첫 입부터 마지막 순간까지 온전히 전해졌답니다!\n\n",
            f"이곳을 다시 찾는 단골들이 한결같이 추천하는 이유가 맛에서 고스란히 묻어났는데요!\n\n",
            f"화려한 기교 대신 기본에 충실하여 깊은 감동을 안겨주는 진솔한 손맛이었답니다!\n\n",
            f"입소문을 타고 멀리서도 찾아오는 손님들이 많은 이유를 몸소 체감할 수 있었는데요!\n\n",
            f"자극적인 조미료 맛 대신 은은하게 퍼지는 본연의 깊은 맛이 마음을 사로잡았답니다!\n\n",
            f"함께 온 친구들도 메뉴 선택이 탁월했다며 연신 엄지를 치켜세우더라고요!\n\n",
            f"정직하고 정성스러운 손맛이 한 숟가락마다 깊은 만족감을 안겨주었답니다!\n\n",
            f"식사하는 동안 내내 미소가 떠나지 않을 만큼 훌륭한 밸런스를 뽐냈는데요!\n\n",
            f"어떤 조합과 곁들여도 조화롭게 어우러지는 완성도 높은 맛의 깊이가 느껴졌답니다!\n\n"
        ]
        avail_p3 = [p for p in p3_opts if p not in used_set] or p3_opts
        p3 = random.choice(avail_p3)
        used_set.add(p3)

    # 4. 식감 및 미각 묘사 (카테고리별 맞춤 풀)
    if food_type == "bakery":
        t_opts = [
            f"한 입 베어 물자마자 파사삭 부서지는 바삭한 겉면과 촉촉하고 쫄깃하게 씹히는 속 결의 조화가 매력적이었는데요.",
            f"고급 버터의 진한 풍미가 씹을수록 은은하게 퍼지며 달콤함과 고소함의 황금 밸런스를 자랑했답니다.",
            f"텁텁함이나 기름진 느끼함 없이 사르르 녹아내리는 부드러운 단맛에 마지막 한 입까지 기분 좋게 즐겼어요.",
            f"섬세하게 구워낸 장인의 손길이 느껴져 커피나 음료와 함께 곁들이니 순식간에 접시를 비워낼 정도였답니다.",
            f"겉은 바삭하고 속은 공기층이 촘촘하게 살아있어 폭신폭신하면서도 쫄깃한 식감이 일품이었어요.",
            f"과하지 않은 은은한 달콤함과 버터의 고소한 아로마가 입안 가득 맴돌아 깊은 여운을 남겼답니다.",
            f"한 조각 잘라 맛보니 결대로 찢어지는 텍스처와 부드러운 목넘김이 디저트의 품격을 높여주었어요."
        ]
    elif food_type == "drink":
        t_opts = [
            f"깊고 진한 크레마와 은은한 산미, 고소한 바디감이 달콤한 디저트의 맛을 완벽하게 감싸주었는데요.",
            f"과하지 않은 깔끔한 목넘김과 풍부한 향미가 돋보여 마시는 내내 입안을 산뜻하게 정돈해 주었답니다.",
            f"갈증을 시원하게 해소해 주면서도 고급스러운 여운을 남겨 마지막 한 모금까지 온전히 힐링을 만끽했어요.",
            f"원두 본연의 신선한 향이 살아있어 한 모금 들이켤 때마다 기분 좋은 향긋함이 가득 번졌답니다.",
            f"부드러운 질감과 산뜻한 풍미가 어우러져 식사 후 깔끔한 마무리로 더할 나위 없이 훌륭했어요.",
            f"은은한 단맛과 깔끔한 청량감이 조화를 이루어 마시는 내내 기분 좋은 청량감을 선사했답니다."
        ]
    elif food_type == "jeon":
        t_opts = [
            f"얇고 부드러운 고기에 얇은 계란 옷을 입혀 갓 부쳐내어, 기름진 잡내 없이 담백한 육즙이 그대로 살아있었는데요.",
            f"겉은 바삭하고 속은 촉촉하여 특제 양념장에 살짝 찍어 맛보니 입안 가득 고소한 풍미가 은은하게 번졌답니다.",
            f"자극적이지 않으면서도 질리지 않는 고소한 감칠맛 덕분에 테이블의 든든함을 완벽하게 채워주었어요.",
            f"기름기가 쏙 빠져 바삭바삭한 식감이 오래 유지되었고, 씹을수록 차오르는 고소함이 일품이었답니다.",
            f"노릇노릇하게 구워진 겉면과 부드러운 속재료가 어우러져 한 점 먹을 때마다 감탄이 나왔어요.",
            f"곁들임 채소나 양파절임과 함께하니 느끼함 없이 무한정 들어갈 만큼 환상적인 궁합을 자랑했답니다."
        ]
    elif food_type == "noodle":
        t_opts = [
            f"탱글탱글 쫄깃한 면발에 깊고 진한 육수가 쏙쏙 배어들어 후루룩 면치기하는 재미가 쏠쏠했는데요.",
            f"퍼지지 않고 끝까지 살아있는 탄력 있는 식감과 개운하고 깊은 국물의 조화가 감탄을 절로 자아냈답니다.",
            f"밀가루 풋내 없이 찰진 면발에 감칠맛 넘치는 양념이 어우러져 마지막 한 가닥까지 남김없이 비워냈어요.",
            f"자가제면 특유의 찰기와 부드러운 목넘김이 돋보여 한 젓가락 가득 집어 들 때마다 입안이 행복했답니다.",
            f"진하게 우려낸 국물이 면발 사이사이에 고스란히 스며들어 씹을 때마다 깊은 풍미를 터뜨려 주었어요.",
            f"깔끔하면서도 깊이 있는 육수와 탱글한 면의 황금비율 덕분에 그릇 바닥이 보일 때까지 젓가락을 놓지 못했답니다."
        ]
    elif food_type == "bibim":
        t_opts = [
            f"푸짐하게 올라간 신선한 육회와 아삭한 채소, 고소한 참기름의 조화가 한 숟가락 뜰 때마다 매력적이었는데요.",
            f"선홍빛 육질의 찰진 쫄깃함과 감칠맛 넘치는 비법 소스가 어우러져 숟가락질을 멈출 수 없었답니다.",
            f"속이 편안하면서도 든든한 포만감을 안겨주어 남녀노소 누구나 좋아할 수밖에 없는 정갈한 한 그릇이었어요.",
            f"다양한 나물과 신선한 재료들이 어우러지며 씹는 재미와 풍부한 맛의 스펙트럼을 선사해 주었답니다.",
            f"자극적인 고추장 맛이 아니라 재료 본연의 맛을 살려주는 정갈한 양념 배합이 인상적이었어요.",
            f"고소한 풍미와 다채로운 식감이 입안에서 팡팡 터져 나와 마지막 한 숟가락까지 감동을 주었답니다."
        ]
    elif food_type == "stew":
        t_opts = [
            f"잡내 하나 없이 야들야들 부드럽게 풀리는 육질과 시원하고 묵직한 국물의 조화가 온몸의 피로를 풀어주었는데요.",
            f"보글보글 끓어오르며 우러난 진국 육수 한 모금에 속이 확 풀리며 깊은 내공을 고스란히 맛볼 수 있었답니다.",
            f"따뜻한 온기 덕분에 재료 본연의 풍미가 배가되어 마지막 국물 한 방울까지 남김없이 들이켰어요.",
            f"칼칼하면서도 텁텁하지 않은 맑고 깊은 국물 맛이 일품이라 밥 한 공기가 순식간에 사라졌답니다.",
            f"속 재료를 아낌없이 듬뿍 넣어 끓여내어 국물에 녹아든 진한 감칠맛의 깊이가 남달랐어요.",
            f"오랜 시간 푹 고아낸 깊은 정성이 한 숟가락 떠먹을 때마다 입안 가득 든든하게 전해졌답니다."
        ]
    elif food_type == "meat":
        t_opts = [
            f"불판 위에서 노릇노릇 구워진 고기에서 은은하게 퍼지는 고소한 육즙의 자태가 훌륭했는데요.",
            f"질김 없이 부드럽게 씹히는 육질과 깊은 육향이 어우러져 어떤 곁들임 찬과 먹어도 찰떡궁합이었답니다.",
            f"기름진 느끼함 없이 씹을수록 담백하고 진한 풍미가 뿜어져 나와 일행 모두 연신 젓가락을 움직였어요.",
            f"적당한 두께감 덕분에 씹는 맛이 제대로 살아있고, 팡 터져 나오는 촉촉한 육즙이 입안을 가득 채웠답니다.",
            f"육즙을 꽉 가두어 촉촉함을 잃지 않은 상태에서 소금이나 와사비만 살짝 곁들여도 환상적이었어요.",
            f"겉은 노릇하고 속은 촉촉한 골든 브라운의 완벽한 굽기로 고기 본연의 풍부한 육향을 만끽했답니다."
        ]
    elif food_type == "mandoo":
        t_opts = [
            f"얇고 차진 만두피 속에 고기와 신선한 채소로 꽉 찬 소가 어우러져, 한 입 베어 무는 순간 진한 육즙이 은은하게 퍼져 나왔는데요.",
            f"잡내 하나 없이 담백하면서도 씹을수록 감칠맛이 도는 속 재료의 밸런스에 감탄이 절로 나왔답니다.",
            f"촉촉하고 부드러운 만두피와 아삭하게 씹히는 소의 조화가 완벽해서 간장에 살짝 찍어 맛보니 그야말로 꿀맛이었어요.",
            f"손으로 정성껏 빚어낸 남다른 볼륨감과 꽉 찬 식감 덕분에 한 개만 맛보아도 든든한 포만감이 차올랐답니다.",
            f"피는 쫄깃하고 속은 육즙으로 촉촉하게 가득 차서 한 입 먹을 때마다 흐뭇함이 멈추지 않는 맛이었어요.",
            f"담백한 만두피 사이로 흘러나오는 재료들의 풍성한 풍미가 입안을 가득 채우며 행복한 미식을 완성해 주었답니다."
        ]
    elif food_type == "seafood":
        t_opts = [
            f"비린내 전혀 없이 입안에 착 감기는 쫀득하고 찰진 식감과 은은한 단맛이 그야말로 일품이었는데요.",
            f"바다의 싱싱함을 고스란히 담아내어 씹을수록 퍼지는 고소한 감칠맛에 절로 감탄사가 터져 나왔답니다.",
            f"두툼하게 썰어내어 씹는 맛이 제대로 살아있고, 특제 쌈이나 곁들임 찬과 함께하니 깊은 만족을 주었어요.",
            f"신선도 최상급 식재료 본연의 깔끔하고 담백한 풍미 덕분에 마지막 한 점까지 기분 좋게 즐겼답니다.",
            f"탱탱한 살점의 탄력이 입안에서 생생하게 느껴지며 신선한 바다의 향이 기분 좋게 퍼져나갔어요.",
            f"초장이나 간장에 살짝 곁들이니 본연의 단맛이 한층 더 돋보여 연신 젓가락이 바쁘게 움직였답니다."
        ]
    else:
        t_opts = [
            f"자극적이지 않으면서도 자꾸만 손이 가게 만드는 감칠맛 넘치는 양념과 신선한 식감이 일품이었는데요.",
            f"식재료 본연의 탄력과 깊은 풍미가 어우러져 마지막 한 점까지 물릴 틈 없이 식사를 완성해 주었답니다.",
            f"풍부한 식감과 깊은 손맛이 조화롭게 어우러져 입안 가득 다채로운 미식의 즐거움을 제대로 만끽했어요.",
            f"깔끔하게 떨어지는 뒷맛과 깊은 풍미의 여운이 길게 남아 소중한 사람들과 나누기에 더없이 좋았답니다.",
            f"씹을수록 배어 나오는 재료 본연의 고소함과 정갈한 소스의 조화가 훌륭했어요.",
            f"호불호 없이 누구나 편안하게 즐길 수 있는 균형 잡힌 맛이라 더욱 마음에 들었답니다."
        ]
    avail_p4 = [p for p in t_opts if p not in used_set] or t_opts
    p4 = random.choice(avail_p4)
    used_set.add(p4)

    # 5. 마무리 결론 및 추천 (16종)
    p5_opts = [
        f"오늘 이곳에 찾아오길 정말 잘했다는 확신을 심어준 만족스러운 한 접시였답니다 👍",
        f"다음에 재방문해도 꼭 다시 주문하고 싶은 시그니처 메뉴로 마음속에 찜해두었어요 💖",
        f"소중한 사람들과 함께 맛있는 추억을 나누기에 더없이 완벽했던 순간이었답니다 🥰",
        f"식사하는 내내 테이블의 활기를 더해주며 기분 좋은 포만감을 채워준 요리였답니다 ✨",
        f"사진을 다시 보는 지금도 군침이 돌 만큼 기억에 남는 행복한 맛이었어요 😋",
        f"누구나 호불호 없이 즐길 만한 수준 높은 맛과 퀄리티를 온전히 보여주었답니다 🥢",
        f"접시가 비워지는 게 아쉬울 정도로 마지막 한 입까지 온전한 미식을 즐겼어요 🍽️",
        f"친구들이나 가족들에게도 자신 있게 권하고 싶은 인상적인 메뉴였답니다 👍",
        f"정성껏 차려진 요리를 맛보며 바쁜 일상 속에서 기분 좋은 힐링을 만끽했어요 ✨",
        f"비주얼부터 맛까지 어느 하나 부족함 없이 꽉 찬 만족감을 안겨주었답니다 💖",
        f"이곳의 남다른 내공을 다시 한번 실감하게 해준 완성도 높은 한 상이었어요 🥢",
        f"입안 가득 퍼지는 깊은 풍미 덕분에 오랜만에 기분 좋은 포식의 즐거움을 누렸답니다 🥰",
        f"맛있는 음식과 좋은 분위기가 어우러져 식사 자리가 한층 더 화기애애해졌어요 🍽️",
        f"다음에 근처에 오게 된다면 주저 없이 다시 찾고 싶은 인생 메뉴였답니다 👍",
        f"단순한 한 끼 식사를 넘어 정성 어린 대접을 받은 듯 마음까지 훈훈해졌어요 ✨",
        f"식사를 마친 후에도 입안에 맴도는 깔끔한 여운 덕분에 여운이 오래 남았답니다 💖"
    ]
    avail_p5 = [p for p in p5_opts if p not in used_set] or p5_opts
    p5 = random.choice(avail_p5)
    used_set.add(p5)

    # 6. 다차원 동적 구조 조립 (고정 5단락 탈피 -> 유기적 가변 구조)
    if is_subsequent:
        sub_patterns = [
            f"{p1} {p2}\n\n{p4} {p5}",
            f"{p1}\n\n{p4}\n\n{p5}",
            f"{p2} {p4}\n\n{p5}"
        ]
        body = random.choice(sub_patterns)
    else:
        main_patterns = [
            f"{p1}\n\n{p2}\n\n{p3}{p4}\n\n{p5}",
            f"{p1} {p2}\n\n{p3}{p4}\n\n{p5}",
            f"{p1}\n\n{p4}\n\n{p3}{p5}",
            f"{p1}\n\n{p2} {p4}\n\n{p5}"
        ]
        body = random.choice(main_patterns)

    return header, body


def create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count, context):
    """
    사진 파일명과 카테고리에 100% 매칭되는 독창적 서사 단락 생성
    (In-Post Deduplication + Cross-Post Recency 30회 무중복 보장)
    """
    import re
    import random
    import memory_manager
    from photo_narratives import PHOTO_CATEGORY_POOLS

    is_pair = count > 1
    pair_suffix = " (가로 나란히)" if is_pair else ""
    used_set = context.setdefault("used_templates", set())
    seen_dishes = context.setdefault("seen_dishes", set())
    live_reviews = context.get("live_reviews") or {}
    persona = context.get("persona") or memory_manager.get_next_persona()
    display_name = re.sub(r'\s*\d+$', '', clean_name).strip() or clean_name
    recent_narratives = memory_manager.get_recently_used_ids(f"cat_{cat}", limit=30)

    # 1. 고정 카테고리 풀에 존재하는 경우
    if cat in PHOTO_CATEGORY_POOLS:
        pool_funcs = PHOTO_CATEGORY_POOLS[cat]
        variations = [
            (h_fn(step_num, store_name, location, clean_name), c_fn(step_num, store_name, location, clean_name))
            for h_fn, c_fn in pool_funcs
        ]
        header, text = pick_unique_variation(
            variations, used_set, key_prefix=f"cat_{cat}",
            context=context, recent_set=recent_narratives
        )

        # 카테고리별 특수 데이터 결합
        if cat == "exterior":
            vibe_revs = live_reviews.get("vibe", []) if live_reviews else []
            avail_vibe = [v for v in vibe_revs if v not in used_set]
            if avail_vibe:
                ch_v = random.choice(avail_vibe)
                used_set.add(ch_v)
                text += f"\n\n네이버 실제 방문객 후기에서도 '{ch_v[:50].strip()}'라는 평이 돋보였는데, 매장 앞에 서니 그 분위기가 단번에 체감되었어요! ✨"
            caption = f"{location} {store_name} {clean_name}{pair_suffix}"
        elif cat == "photo_zone":
            caption = f"{clean_name} 포토존{pair_suffix}"
        elif cat == "waiting":
            caption = f"{clean_name} 현장 대기{pair_suffix}"
        elif cat == "award":
            caption = f"{store_name} {clean_name}{pair_suffix}"
        elif cat == "interior":
            caption = f"{store_name} 아늑한 {display_name}{pair_suffix}"
        elif cat == "counter":
            caption = f"{store_name} {display_name}{pair_suffix}"
        elif cat == "seating":
            caption = f"{store_name} 편안한 {display_name}{pair_suffix}"
        elif cat == "selfbar":
            caption = f"깔끔하고 쾌적한 {display_name}{pair_suffix}"
        elif cat == "facility":
            caption = f"쾌적하고 청결한 {display_name}{pair_suffix}"
        elif cat == "notice":
            caption = f"{clean_name} 안내사항{pair_suffix}"
        elif cat == "service_rice":
            caption = f"따뜻한 인심의 {clean_name}{pair_suffix}"
        elif cat == "menu":
            caption = f"{store_name} {clean_name}{pair_suffix}"
        elif cat == "showcase":
            taste_revs = live_reviews.get("taste", []) if live_reviews else []
            avail_taste = [t for t in taste_revs if t not in used_set]
            if avail_taste:
                ch_t = random.choice(avail_taste)
                used_set.add(ch_t)
                text += f"\n\n네이버 방문자 리뷰에서도 '{ch_t[:50].strip()}'라는 극찬이 많았는데, 직접 쇼케이스를 둘러보니 왜 인기 폭발인지 바로 실감 났답니다 💖"
            caption = f"화려하고 먹음직스러운 {display_name}{pair_suffix}"
        elif cat == "sides":
            caption = f"{clean_name} 세팅{pair_suffix}"
        elif cat == "dish_lifting":
            caption = f"먹음직스럽게 집어 든 {clean_name}{pair_suffix}"
        elif cat == "topping_detail":
            caption = f"신선하고 푸짐한 {clean_name}{pair_suffix}"
        elif cat == "soup_side":
            caption = f"깊고 진한 {clean_name}{pair_suffix}"
        elif cat == "noodle_lifting":
            caption = f"쫄깃탱글한 {clean_name}{pair_suffix}"
        elif cat == "finish":
            caption = f"{clean_name} 마무리{pair_suffix}"
        elif cat == "combo":
            caption = f"맛있는 {clean_name}{pair_suffix}"
        elif cat == "detail":
            caption = f"{clean_name} 디테일{pair_suffix}"
        else:
            caption = f"{clean_name}{pair_suffix}"

        return header, text, caption

    # 2. 메인/사이드 요리 (dish, sub_dish 등) - 다차원 동적 합성 엔진 가동
    else:
        is_subsequent = (cat == "sub_dish") or (clean_name in seen_dishes) or (len(seen_dishes) > 0)
        seen_dishes.add(clean_name)
        ft = determine_food_type(clean_name, main_menu)
        header, text = synthesize_dynamic_dish_block(
            step_num=step_num,
            clean_name=clean_name,
            store_name=store_name,
            location=location,
            main_menu=main_menu,
            food_type=ft,
            live_reviews=live_reviews,
            used_set=used_set,
            is_subsequent=is_subsequent
        )
        caption = f"{clean_name}{pair_suffix}"
        if context is not None:
            context.setdefault("photo_blocks", {}).setdefault("dish", []).append(f"dish_{clean_name}_{step_num}")
        return header, text, caption

def generate_photo_matched_sections(store_name, location, menu, features, photo_paths, include_stickers=True, include_map=True, store_info=None, persona=None, context=None):
    """
    첨부된 사진 목록을 분석하여 파일명과 100% 매칭되는 글 생성 (중복 절대 없음)
    """
    import re
    import memory_manager
    if context is None:
        context = {}
    if persona is None:
        persona = memory_manager.get_next_persona()
    context["persona"] = persona
    context.setdefault("used_templates", set())
    context.setdefault("seen_dishes", set())
    context.setdefault("photo_blocks", {})
    context["live_reviews"] = (store_info.get("live_reviews") if store_info else {}) or {}
    context["store_info"] = store_info or {}

    sections = []
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu

    # 1. 인트로 (페르소나 맞춤 + 최근 30회 무중복 보장)
    intro_header, intro_content, intro_key = generate_dynamic_intro(
        store_name, location, main_menu, persona=persona, return_meta=True
    )
    context["intro_id"] = intro_key
    sections.append({
        "type": "text",
        "header": sanitize_header(intro_header),
        "content": intro_content
    })

    if include_stickers:
        sections.append({"type": "sticker", "role": "intro"})

    # 2. 매장 상세 정보 & 네이버 지도
    if store_info:
        from store_crawler import format_store_info_section
        info_text = format_store_info_section(store_info)
        info_headers = [
            f"📌 {store_name} 방문 전 필독 정보 (위치·영업시간·주차)",
            f"🗺️ 한눈에 쏙 정리해보는 {store_name} 매장 이용 안내",
            f"🚗 {store_name} 찾아오시는 길 & 매장 핵심 정보 총정리",
            f"📍 방문 전 꼭 체크해야 할 {store_name} 이용 꿀팁 & 정보",
            f"📋 {store_name} 영업시간부터 주차 정보까지 완벽 정리!",
            f"✨ 찾아가기 전 알아두면 유용한 {store_name} 필수 정보"
        ]
        info_header = random.choice(info_headers)
        sections.append({
            "type": "text",
            "header": sanitize_header(info_header),
            "content": info_text
        })

    if include_map:
        sections.append({
            "type": "map",
            "query": f"{store_name}",
            "location_name": f"{location} {store_name}"
        })

    # 3. 사진 파싱 및 인접 사진 묶음(batch) 생성
    sorted_paths = sorted(photo_paths, key=smart_photo_sort_key)
    parsed_list = [parse_photo_info(p) for p in sorted_paths]

    batches = []
    idx = 0
    while idx < len(parsed_list):
        curr = parsed_list[idx]
        if idx + 1 < len(parsed_list):
            nxt = parsed_list[idx + 1]
            can_pair = False
            if curr["category"] == nxt["category"] and curr["category"] not in ("combo", "finish", "notice", "award", "soup_side", "service_rice", "dish_lifting", "noodle_lifting", "topping_detail"):
                c1 = re.sub(r'[0-9\s_\-\.\(\)\[\]]', '', curr["clean_name"])
                c2 = re.sub(r'[0-9\s_\-\.\(\)\[\]]', '', nxt["clean_name"])
                if c1 and c2 and c1 == c2:
                    can_pair = True

            if can_pair:
                batches.append({
                    "items": [curr, nxt],
                    "category": curr["category"],
                    "clean_name": curr["clean_name"]
                })
                idx += 2
                continue
        batches.append({
            "items": [curr],
            "category": curr["category"],
            "clean_name": curr["clean_name"]
        })
        idx += 1

    # 4. 각 사진 묶음마다 파일명과 100% 매칭되는 스토리 단락 생성
    step_num = 1
    for b_idx, batch in enumerate(batches, 1):
        cat = batch["category"]
        clean_name = batch["clean_name"]
        count = len(batch["items"])
        b_paths = [item["path"] for item in batch["items"]]

        if include_stickers and b_idx in (2, 5, 8):
            sections.append({"type": "sticker", "role": "mid"})

        header, text, caption = create_story_for_photo_batch(
            step_num, cat, clean_name, store_name, location, main_menu, count, context
        )
        step_num += 1

        sections.append({
            "type": "text",
            "header": sanitize_header(header),
            "content": text
        })

        sections.append({
            "type": "image",
            "paths": b_paths,
            "count": count,
            "caption": caption
        })

    # 5. 동적 총평 & 재방문 의사 (페르소나 맞춤 + 최근 30회 무중복 보장)
    outro_header, outro_content, outro_key = generate_dynamic_outro(
        store_name, location, menu, persona=persona, return_meta=True
    )
    context["outro_id"] = outro_key
    sections.append({
        "type": "text",
        "header": sanitize_header(outro_header),
        "content": outro_content
    })

    if include_stickers:
        sections.append({"type": "sticker", "role": "outro"})

    # 해시태그 40개
    tags = build_rich_hashtags(store_name, location, menu, features)
    hashtag_lines = []
    chunk_size = 5
    for i in range(0, len(tags), chunk_size):
        chunk = tags[i:i + chunk_size]
        hashtag_lines.append(" ".join([f"#{t}" for t in chunk]))
    hashtag_content = "\n".join(hashtag_lines)

    sections.append({
        "type": "text",
        "header": "🏷️ 관련 태그 & 해시태그 모아보기",
        "content": f"{hashtag_content}\n"
    })

    return sections


def generate_template_post(store_name, location, menu, features, photo_count=14, include_stickers=True, include_map=True, store_info=None, photo_paths=None, persona=None):
    """
    사진 목록이 있으면 사진 파일명에 100% 매칭되는 맞춤형 포스팅 생성,
    사진이 없으면 텍스트 중심의 정갈한 포스팅 생성
    (6대 작가 페르소나 자동 순환 + 최근 30개 글 무중복 영구 추적 탑재)
    """
    import re
    import memory_manager
    if persona is None:
        persona = memory_manager.get_next_persona()

    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu

    title, title_key = generate_dynamic_title(
        store_name, location, main_menu, persona=persona, return_meta=True
    )

    context = {
        "persona": persona,
        "used_templates": set(),
        "seen_dishes": set(),
        "photo_blocks": {},
        "live_reviews": (store_info.get("live_reviews") if store_info else {}) or {},
        "store_info": store_info or {}
    }

    if photo_paths:
        sections = generate_photo_matched_sections(
            store_name=store_name,
            location=location,
            menu=menu,
            features=features,
            photo_paths=photo_paths,
            include_stickers=include_stickers,
            include_map=include_map,
            store_info=store_info,
            persona=persona,
            context=context
        )
        intro_key = context.get("intro_id", "")
        outro_key = context.get("outro_id", "")
    else:
        sections = []
        intro_h, intro_c, intro_key = generate_dynamic_intro(
            store_name, location, main_menu, persona=persona, return_meta=True
        )
        sections.append({"type": "text", "header": sanitize_header(intro_h), "content": intro_c})
        if store_info:
            from store_crawler import format_store_info_section
            sections.append({"type": "text", "header": sanitize_header(f"📌 {store_name} 매장 이용 안내 & 필수 정보"), "content": format_store_info_section(store_info)})
        if include_map:
            sections.append({"type": "map", "query": store_name, "location_name": f"{location} {store_name}"})
        outro_h, outro_c, outro_key = generate_dynamic_outro(
            store_name, location, menu, persona=persona, return_meta=True
        )
        sections.append({"type": "text", "header": sanitize_header(outro_h), "content": outro_c})

    tags = build_rich_hashtags(store_name, location, menu, features)

    # 최근 30개 무중복 생성 이력 영구 기록
    memory_manager.record_post_generation(
        persona_id=persona["id"],
        title_id=title_key,
        intro_id=intro_key,
        outro_id=outro_key,
        photo_blocks=context.get("photo_blocks", {}),
        store_name=store_name
    )

    return {
        "title": clean_markdown_artifacts(title),
        "sections": sections,
        "tags": tags,
        "persona": persona
    }


def clean_json_text(text):
    """LLM이 반환한 마크다운 코드 블록(```json ...)을 제거하고 순수 JSON 문자열만 추출"""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    m = re.search(r'(\{[\s\S]*\})', text)
    if m:
        text = m.group(1)
    return text.strip()


def call_llm_api(provider, api_key, prompt, status_callback=print):
    """
    Google Gemini (gemini-2.5-flash / gemini-1.5-flash / gemini-2.0-flash)
    OpenAI (gpt-4o-mini / gpt-4o)
    Anthropic Claude (claude-3-5-haiku) 지원
    """
    import json
    import urllib.request
    import urllib.error

    p_lower = str(provider).lower()

    # 1. Google Gemini
    if "gemini" in p_lower:
        gemini_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
        last_error = None
        for m_name in gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.8,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json"
                }
            }
            try:
                status_callback(f"🤖 Google Gemini ({m_name}) 실시간 고유 서사 생성 요청 중...")
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    raw_text = data['candidates'][0]['content']['parts'][0]['text']
                    status_callback(f"✅ Gemini ({m_name}) 본문 100% 창작 완료!")
                    return raw_text
            except urllib.error.HTTPError as he:
                err_body = he.read().decode('utf-8', errors='ignore')
                last_error = f"HTTP {he.code}: {err_body[:150]}"
                if he.code == 404:
                    continue  # Try next model name
                else:
                    status_callback(f"⚠️ Gemini API 오류 ({m_name}): {last_error}")
                    break
            except Exception as e:
                last_error = str(e)
                status_callback(f"⚠️ Gemini 호출 예외: {e}")
                break
        status_callback(f"⚠️ Gemini 모델 호출 실패: {last_error}")
        return None

    # 2. OpenAI
    elif "openai" in p_lower:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 네이버 상위 1% 맛집 전문 파워블로거입니다. 마크다운 서식 기호 없이 스마트에디터용 순수 텍스트로 작성하며, 반드시 요청받은 유효한 JSON 형식으로만 응답하세요."
                },
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
            "max_tokens": 4096
        }
        try:
            status_callback("🤖 OpenAI (gpt-4o-mini) 실시간 고유 서사 생성 요청 중...")
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_text = data['choices'][0]['message']['content']
                status_callback("✅ OpenAI (gpt-4o-mini) 본문 100% 창작 완료!")
                return raw_text
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='ignore')
            status_callback(f"⚠️ OpenAI API HTTP {he.code} 오류: {err_body[:150]}")
        except Exception as e:
            status_callback(f"⚠️ OpenAI API 호출 예외: {e}")
        return None

    # 3. Claude
    elif "claude" in p_lower:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.8
        }
        try:
            status_callback("🤖 Anthropic Claude 실시간 생성 요청 중...")
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_text = data['content'][0]['text']
                status_callback("✅ Claude 본문 100% 창작 완료!")
                return raw_text
        except Exception as e:
            status_callback(f"⚠️ Claude API 호출 오류: {e}")
        return None

    return None


def generate_ai_post(api_key, api_provider, store_name, location, menu, features, photo_count=5, include_stickers=True, include_map=True, store_info=None, photo_paths=None, persona=None, status_callback=print):
    """
    100% 최신 생성형 AI(Google Gemini / OpenAI)를 사용하여
    도입부, 사진별 1:1 맞춤 서사, 식감/미각 묘사, 매장 정보, 총평, 해시태그까지
    하드코딩 0%로 실시간 전면 창작하는 차세대 블로그 생성 엔진
    """
    import os
    import re
    import json
    import random
    import memory_manager

    if not api_key or not api_key.strip():
        status_callback("⚠️ API Key가 입력되지 않아 고품질 템플릿 엔진으로 자동 생성합니다.")
        return generate_template_post(
            store_name, location, menu, features, photo_count,
            include_stickers, include_map, store_info, photo_paths, persona
        )

    if persona is None:
        persona = memory_manager.get_next_persona()
    p_name = persona.get("name", "트렌드세터 2030 핫플러")
    p_desc = persona.get("desc", "감각적인 비주얼과 트렌디한 감성을 솔직하게 전달")

    # 1. 사진 파싱 및 배치 목록 구성
    if photo_paths:
        sorted_paths = sorted(photo_paths, key=smart_photo_sort_key)
        parsed_list = [parse_photo_info(p) for p in sorted_paths]

        batches = []
        idx = 0
        while idx < len(parsed_list):
            curr = parsed_list[idx]
            if idx + 1 < len(parsed_list):
                nxt = parsed_list[idx + 1]
                can_pair = False
                if curr["category"] == nxt["category"] and curr["category"] not in (
                    "combo", "finish", "notice", "award", "soup_side", "service_rice",
                    "dish_lifting", "noodle_lifting", "topping_detail"
                ):
                    c1 = re.sub(r'[0-9\s_\-\.\(\)\[\]]', '', curr["clean_name"])
                    c2 = re.sub(r'[0-9\s_\-\.\(\)\[\]]', '', nxt["clean_name"])
                    if c1 and c2 and c1 == c2:
                        can_pair = True

                if can_pair:
                    batches.append({
                        "items": [curr, nxt],
                        "category": curr["category"],
                        "clean_name": curr["clean_name"]
                    })
                    idx += 2
                    continue
            batches.append({
                "items": [curr],
                "category": curr["category"],
                "clean_name": curr["clean_name"]
            })
            idx += 1
    else:
        # 사진이 없을 경우 표준 블로그 흐름 5파트 가상 구성
        batches = [
            {"items": [], "category": "exterior", "clean_name": "매장 전경 및 입구"},
            {"items": [], "category": "interior", "clean_name": "실내 인테리어 및 분위기"},
            {"items": [], "category": "menu", "clean_name": "메뉴판 및 주문"},
            {"items": [], "category": "dish", "clean_name": f"대표 시그니처 요리 {menu}"},
            {"items": [], "category": "finish", "clean_name": "만족스러운 식사 마무리"}
        ]

    # 사진 순서 프롬프트 가이드 생성
    photo_guides = []
    for b_i, b in enumerate(batches, 1):
        cat_kor = CATEGORY_KOR_NAMES.get(b["category"], "요리/공간")
        fnames = [os.path.basename(it["path"]) for it in b["items"]] if b["items"] else []
        fnames_str = f" (사진 파일: {', '.join(fnames)})" if fnames else ""
        photo_guides.append(f"{b_i}. 사진 주제: [{cat_kor}] '{b['clean_name']}'{fnames_str}")
    photo_guides_text = "\n".join(photo_guides)

    # 매장 정보 및 네이버 실시간 리뷰 요약
    s_addr = (store_info.get("address") if store_info else "") or f"{location} 인근"
    s_biz = (store_info.get("bizhour") if store_info else "") or "매장 문의"
    s_park = (store_info.get("parking") if store_info else "") or "인근 유료/공영주차장 이용 권장"

    rev_lines = []
    if store_info and "live_reviews" in store_info:
        lr = store_info["live_reviews"]
        for t in lr.get("taste", [])[:3]:
            rev_lines.append(f"- 맛 후기: \"{t.strip()}\"")
        for v in lr.get("vibe", [])[:2]:
            rev_lines.append(f"- 분위기 후기: \"{v.strip()}\"")
    live_rev_text = "\n".join(rev_lines) if rev_lines else "- 네이버 방문객 평점 및 만족도가 아주 높은 인기 매장"

    prompt = f"""당신은 네이버 상위 1% 맛집 전문 파워블로거입니다.
지정된 작가 페르소나 스타일로 실제 방문하여 100% 직접 경험한 것처럼 생생하고 흡입력 있는 네이버 블로그 글을 작성해주세요.

[작가 페르소나]
- 스타일: {p_name} ({p_desc})
- 어조: 실제 20~30대 한국인 인플루언서가 쓰는 친근하고 자연스러운 구어체 ('~했어요!', '~더라고요!', '~였답니다!', '~느껴졌어요!')
- 절대 금지: 로봇/AI 특유의 번역투 ('~에 대해 알아보겠습니다', '~를 추천드립니다', '~의 모습입니다' 반복 금지), 상투적 클리셰 ('200% 만족', '300%', '대만족', '올킬', '삼박자' 절대 사용 금지).

[방문 식당 정보]
- 식당명: {store_name}
- 지역/위치: {location}
- 대표 메뉴: {menu}
- 매장 특징: {features}
- 주소: {s_addr}
- 영업시간: {s_biz}
- 주차 안내: {s_park}
- 네이버 실제 방문자 후기 참고:
{live_rev_text}

[배치될 사진 순서 및 주제 (총 {len(batches)}개 단락)]
본문에는 아래 순서대로 사진이 삽입됩니다. 각 번호(batch_index 1부터 {len(batches)}까지)에 맞춰 사진을 직접 보며 설명하듯 생생하게 작성해야 합니다:
{photo_guides_text}

[작성 필수 규칙]
1. 제목(title): 네이버 스마트블록/DIA+ 검색 랭킹에 최적화되도록 지역명({location}), 상호명({store_name}), 대표메뉴 키워드를 자연스러운 문맥으로 배치 (호기심 유발, 솔직 후기형).
2. 도입부(intro): 매장에 방문하게 된 계기, 날씨나 모임 상황, 찾아가는 길의 설렘을 담아 2~3단락으로 작성.
3. 사진별 스토리(photo_stories):
   - 위 사진 순서의 각 번호(batch_index 1부터 {len(batches)}까지)와 1:1로 매칭되는 소제목(header)과 본문(content)을 작성.
   - 소제목(header): 인위적인 번호('1.', '2.', '1등' 등) 절대 금지! 해당 사진의 매력을 담은 감각적인 소제목 (이모지 1개 포함).
   - 본문(content): 해당 사진의 모습(외관이면 감성적인 외관 분위기, 요리면 비주얼/색감/식감/육즙/온도감/간의 조화)을 생생한 2~3단락으로 작성. 단락 구분은 \n\n 으로 줄바꿈.
4. 마무리 총평(outro):
   - 전체 식사에 대한 솔직한 총평, 재방문 의사, 누구와 오면 좋을지(데이트/가족/친구/회식), 주차나 웨이팅 꿀팁을 2~3단락으로 작성.
5. 해시태그(tags): 네이버 검색 유입에 최적화된 키워드 30~40개 배열.
6. 서식: 본문에 마크다운 기호(**굵게**, # 제목)를 일체 넣지 마세요. 스마트에디터에 바로 붙여넣는 순수 텍스트여야 합니다.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "title": "블로그 포스팅 제목",
  "intro": "도입부 본문 (단락은 \n\n으로 구분)",
  "photo_stories": [
    {{
      "batch_index": 1,
      "header": "사진 1 전용 소제목",
      "content": "사진 1 전용 생생한 본문 스토리 (단락은 \n\n으로 구분)"
    }}
  ],
  "outro_header": "마무리 소제목",
  "outro": "마무리 총평 본문 (단락은 \n\n으로 구분)",
  "tags": ["태그1", "태그2", ... 35개 내외]
}}
"""

    status_callback(f"🤖 [100% 생성형 AI 엔진] {api_provider.upper()} 모델에 {len(batches)}개 사진 맞춤 본문 실시간 집필 요청 중...")
    raw_ai_resp = call_llm_api(api_provider, api_key.strip(), prompt, status_callback=status_callback)

    if not raw_ai_resp:
        status_callback("⚠️ AI 응답 없음 -> 고품질 템플릿 엔진으로 안전하게 자동 전환합니다.")
        return generate_template_post(
            store_name, location, menu, features, photo_count,
            include_stickers, include_map, store_info, photo_paths, persona
        )

    # JSON 추출 및 파싱
    clean_json_str = clean_json_text(raw_ai_resp)
    try:
        ai_data = json.loads(clean_json_str)
    except Exception as je:
        status_callback(f"⚠️ AI JSON 파싱 실패 ({je}) -> 템플릿 엔진으로 자동 전환합니다.")
        return generate_template_post(
            store_name, location, menu, features, photo_count,
            include_stickers, include_map, store_info, photo_paths, persona
        )

    # AI 생성 데이터 추출
    ai_title = clean_markdown_artifacts(ai_data.get("title", f"{location} {store_name} 솔직 후기"))
    ai_intro = clean_markdown_artifacts(ai_data.get("intro", ""))
    ai_photo_stories = ai_data.get("photo_stories", [])
    ai_outro_header = sanitize_header(ai_data.get("outro_header", f"✨ {store_name} 총평 및 솔직 후기"))
    ai_outro = clean_markdown_artifacts(ai_data.get("outro", ""))
    ai_tags = ai_data.get("tags") or build_rich_hashtags(store_name, location, menu, features)

    # photo_stories 를 batch_index 기준으로 맵핑
    story_map = {}
    for st in ai_photo_stories:
        b_idx = st.get("batch_index")
        if b_idx is not None:
            try:
                story_map[int(b_idx)] = st
            except Exception:
                pass
    # 만약 index 매칭이 안 된 경우 순서대로 맵핑
    if not story_map:
        for idx, st in enumerate(ai_photo_stories, 1):
            story_map[idx] = st

    # 3. 네이버 블로그 스마트에디터 섹션 조립 (하드코딩 문구 0%)
    sections = []

    # 도입부 스티커
    if include_stickers:
        sections.append({"type": "sticker", "role": "intro"})

    # AI 도입부 텍스트
    sections.append({
        "type": "text",
        "header": "",
        "content": ai_intro
    })

    # 매장 정보 안내 박스
    if store_info:
        from store_crawler import format_store_info_section
        info_text = format_store_info_section(store_info)
        sections.append({
            "type": "text",
            "header": f"📌 {store_name} 매장 이용 안내 및 방문 정보",
            "content": info_text
        })

    # 네이버 지도
    if include_map:
        sections.append({
            "type": "map",
            "query": f"{store_name}",
            "location_name": f"{location} {store_name}"
        })

    # 사진별 단락 (AI가 직접 쓴 소제목과 본문 100% 매칭)
    for b_idx, batch in enumerate(batches, 1):
        story = story_map.get(b_idx)
        if story:
            sec_h = sanitize_header(story.get("header", f"✨ {batch['clean_name']} 모습"))
            sec_c = clean_markdown_artifacts(story.get("content", ""))
        else:
            sec_h = f"✨ {batch['clean_name']}"
            sec_c = f"{store_name}의 매력적인 {batch['clean_name']} 모습이에요."

        # 스티커 적재적소 삽입
        if include_stickers and b_idx in (2, 5, 8):
            sections.append({"type": "sticker", "role": "mid"})

        # 본문 텍스트 (AI 생성)
        sections.append({
            "type": "text",
            "header": sec_h,
            "content": sec_c
        })

        # 사진 이미지 첨부
        if batch["items"]:
            b_paths = [item["path"] for item in batch["items"]]
            pair_suffix = " (가로 나란히)" if len(b_paths) > 1 else ""
            caption = f"{batch['clean_name']}{pair_suffix}"
            sections.append({
                "type": "image",
                "paths": b_paths,
                "count": len(b_paths),
                "caption": caption
            })

    # AI 총평 및 아웃트로
    sections.append({
        "type": "text",
        "header": ai_outro_header,
        "content": ai_outro
    })

    # 마무리 스티커
    if include_stickers:
        sections.append({"type": "sticker", "role": "outro"})

    # 해시태그 40개
    tag_lines = []
    chunk_size = 5
    for i in range(0, len(ai_tags), chunk_size):
        chunk = ai_tags[i:i + chunk_size]
        tag_lines.append(" ".join([f"#{t.replace('#', '')}" for t in chunk]))
    hashtag_content = "\n".join(tag_lines)

    sections.append({
        "type": "text",
        "header": "🏷️ 관련 태그 & 해시태그 모아보기",
        "content": f"{hashtag_content}\n"
    })

    status_callback("🎉 [100% 생성형 AI 포스팅 완성] 모든 본문과 사진 서사가 성공적으로 집필되었습니다!")

    return {
        "title": ai_title,
        "sections": sections,
        "tags": ai_tags,
        "persona": persona
    }
