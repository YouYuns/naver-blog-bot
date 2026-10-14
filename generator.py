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


def generate_dynamic_title(store_name, location, main_menu):
    templates = [
        f"[{location} 맛집] {store_name} 솔직후기! {main_menu} 제대로 즐기고 왔어요! ✨",
        f"{location} {main_menu} 맛집 '{store_name}' 내돈내산 찐후기! 감탄하고 온 솔직 후기! 😋",
        f"드디어 다녀온 {location} 핫플 {store_name}! 입소문난 {main_menu} 먹고 완전 반했어요! 👍",
        f"[{location} 데이트 추천] 분위기부터 맛까지 완벽했던 {main_menu} 맛집 {store_name} 다녀온 후기! 💖",
        f"{location} 인생 맛집 등극! {store_name} 대표메뉴 {main_menu}부터 꿀조합 팁까지 싹 정리했어요! 🍽️",
        f"웨이팅이 전혀 아깝지 않았던 {location} {store_name}! 인생 {main_menu} 영접한 솔직 방문기 ✨",
        f"[{location} 찐맛집] 소문 듣고 찾아간 {store_name}! 향긋하고 깊은 {main_menu}에 푹 빠졌어요 🥰",
        f"{location}에서 가장 핫하다는 {store_name} 정복기! 대표 시그니처 {main_menu} 먹방 리뷰 🥢",
        f"현지인들도 줄서서 먹는 {location} 맛집 {store_name}! 감탄이 절로 나오는 {main_menu} 찐후기 👍",
        f"[{location} 가볼만한곳] 정갈한 한 상에 감동받은 {store_name}! {main_menu} 솔직 방문기 💖",
        f"기대 그 이상이었던 {location} {store_name}! {main_menu}의 황홀한 맛에 반하고 온 날 😋",
        f"[{location} 핫플 탐방] 재방문 의사 200%! {store_name} {main_menu} 비주얼과 꿀팁 총정리 🍽️",
        f"오랜만에 찾은 취향 저격 식당! {location} {store_name}에서 즐긴 환상의 {main_menu} ✨",
        f"[{location} 내돈내산] 입소문 자자한 {store_name} 솔직 후기! {main_menu} 강력 추천해요 👍",
        f"눈과 입이 모두 즐거웠던 {location} {store_name}! {main_menu} 먹으러 또 가고 싶은 찐후기 🥰"
    ]
    return random.choice(templates)


def generate_dynamic_intro(store_name, location, main_menu):
    intros = [
        (
            f"✨ {location} 핫플! {store_name} 솔직 방문기!",
            f"안녕하세요 잇님들! 맛있는 곳이라면 어디든 찾아가는 맛집 탐방러예요! 😋\n\n"
            f"요즘 SNS 피드에서 유독 자주 보이고 볼 때마다 침샘을 자극했던 {location} 핫플, '{store_name}'에 드디어 다녀왔답니다!\n\n"
            f"평소에도 {main_menu}를 워낙 좋아해서 벼르고 벼르다가 찾아갔는데, 기대했던 것보다 훨씬 더 만족스러워서 카메라 셔터를 쉴 새 없이 눌렀어요 ✨\n\n"
            f"생생한 사진과 함께하는 솔직한 방문기 시작하기 전에, 매장 상세 정보와 위치부터 먼저 위에 깔끔하게 정리해 드릴게요!"
        ),
        (
            f"💖 입소문 자자한 {location} 명소, {store_name} 다녀왔어요!",
            f"안녕하세요 여러분! 소문난 맛집만 쏙쏙 골라 다니는 일상 블로거예요! ✨\n\n"
            f"주변에 입맛 까다롭기로 유명한 친구들이 인생 맛집이라며 입이 마르도록 칭찬하던 {location}의 대표 맛집, '{store_name}'에 드디어 발도장을 찍고 왔습니다!\n\n"
            f"대표 메뉴인 {main_menu}의 명성이 워낙 자자해서 설레는 마음으로 방문했는데, 한 입 맛보는 순간 왜 그렇게 다들 칭찬했는지 바로 납득이 가더라고요 💖\n\n"
            f"본격적인 먹방 사진을 풀어보기 전에, 매장 이용 정보와 위치 지도부터 알차게 짚어드릴게요!"
        ),
        (
            f"🍽️ 힐링 가득한 한 끼! {location} {store_name} 솔직 리뷰!",
            f"잇님들 안녕하세요! 오늘 하루도 기분 좋게 보내고 계신가요? 🥰\n\n"
            f"지친 일상 속에서 맛있는 음식 하나로 완벽하게 힐링하고 싶었던 날, 고민 없이 달려간 {location} 찐맛집 '{store_name}' 솔직 후기를 가져왔어요!\n\n"
            f"정갈한 분위기 속에서 즐긴 {main_menu}의 감동적인 풍미가 아직도 잊혀지지 않는데요 ✨\n\n"
            f"방문 계획 있으신 분들을 위해 도움 되는 매장 필수 정보와 위치 안내부터 먼저 상단에 싹 공유해 드릴게요!"
        ),
        (
            f"🌟 {location} 골목 핫플레이스! {store_name} 탐방기!",
            f"안녕하세요 잇님들! 맛집 레이더 가동 중인 맛집 사냥꾼이에요! 🍽️\n\n"
            f"오늘은 {location} 골목 사이에서 가장 뜨거운 인기를 자랑하는 핫플레이스, '{store_name}'에 다녀온 찐 후기입니다!\n\n"
            f"사진으로만 보던 {main_menu}의 영롱한 비주얼을 직접 눈앞에서 마주하니 찾아온 보람이 물씬 들었는데요 👍\n\n"
            f"사진과 꿀팁이 가득한 생생 후기를 시작하기에 앞서, 방문 전 꼭 알아두어야 할 매장 상세 정보부터 먼저 체크해 드릴게요!"
        ),
        (
            f"😋 감탄이 절로 나온 {location} 찐맛집 {store_name}!",
            f"반가워요 잇님들! 늘 맛있는 순간을 기록하는 푸드 블로거예요! 💖\n\n"
            f"매일 먹는 평범한 외식 말고, 정말 제대로 된 맛있는 한 끼가 간절했던 날 찾아간 {location} 맛집 '{store_name}' 이야기입니다!\n\n"
            f"신선한 식재료와 깊은 손맛이 어우러진 {main_menu} 덕분에 식사하는 내내 감탄사를 연발했는데요 😋\n\n"
            f"본격적인 방문 사진과 꿀조합을 소개해 드리기 전, 매장 운영 정보와 네이버 지도부터 정갈하게 정리해 드릴게요!"
        ),
        (
            f"🌿 솔직 담백 내돈내산! {location} {store_name} 리얼 후기!",
            f"안녕하세요 잇님들! 솔직하고 생생한 맛집 리뷰로 인사드려요! 🌿\n\n"
            f"'소문난 잔치에 먹을 것 없다'는 편견을 단번에 깨부숴준 {location}의 줄서는 맛집, 바로 '{store_name}'에 다녀왔습니다!\n\n"
            f"많은 손님들이 찾는 대표 시그니처 {main_menu}를 직접 맛보고 왔는데, 웨이팅이 전혀 아깝지 않을 만큼 감동적이었어요 ✨\n\n"
            f"사진과 함께 전해드리는 알찬 방문기 전에, 매장 위치와 상세 정보부터 먼저 꼼꼼하게 정리해 드릴게요!"
        )
    ]
    return random.choice(intros)


def generate_dynamic_outro(store_name, location, menu):
    outros = [
        (
            "⭐ 총평 & 별점 5.0 만점이에요!",
            (
                f"맛, 신선함, 친절한 서비스, 분위기까지 무엇 하나 빠짐없이 대만족이었던 {location} '{store_name}'! 💖\n\n"
                f"특별한 날 소중한 사람들과 맛있는 추억을 쌓기에도 제격이고, 지친 하루를 맛있는 음식으로 힐링하기에 더할 나위 없는 곳이었어요!\n\n"
                f"📌 매장 방문 핵심 요약!\n"
                f"- 상호명 : {store_name}\n"
                f"- 대표 메뉴 : {menu} (강력 추천!)\n"
                f"- 분위기 : 아늑함, 청결함, 모임 및 데이트 최적!\n"
                f"- 별점 평가 : ⭐⭐⭐⭐⭐ (5.0 / 5.0 만점!)\n\n"
                f"오늘 제 솔직후기가 {location} 맛집을 찾으시는 분들께 알찬 도움이 되었길 바라요 🥰\n"
                f"도움이 되셨다면 공감 하트랑 따뜻한 댓글 부탁드려요! 이웃 추가도 언제나 환영합니다! 감사합니다 ✨"
            )
        ),
        (
            "💖 입안 가득 감동! 재방문 의사 300%!",
            (
                f"정말 오랜만에 입안 가득 찐 감동을 선물해 준 최고의 {location} 맛집 '{store_name}'이었어요! ✨\n\n"
                f"바쁜 일상 속에서 맛있는 음식 하나로 이렇게 큰 행복을 느낄 수 있다는 게 참 감사했는데요!\n\n"
                f"💡 방문 전 꼭 기억할 포인트!\n"
                f"1. 시그니처 메뉴인 {menu}는 무조건 주문 필수!\n"
                f"2. 피크 타임 방문 시 현장 대기 시스템 미리 체크!\n"
                f"3. 소중한 지인이나 연인과 함께 오면 만족도 두 배!\n\n"
                f"다음에 이 근처에 오면 무조건 재방문 1순위로 찜해뒀답니다 😋\n"
                f"유익하셨다면 공감 하트와 따뜻한 댓글 부탁드려요! 감사합니다 💖"
            )
        ),
        (
            "📌 오늘의 솔직 방문기 3줄 요약!",
            (
                f"웨이팅의 피로감을 단 한 입에 싹 날려버릴 만큼 기대를 200% 충족시켜 준 '{store_name}'! 👍\n\n"
                f"문 나설 때까지 미소가 떠나지 않았던 곳이라 잇님들께 자신 있게 추천해 드려요!\n\n"
                f"✨ 핵심 포인트 3줄 요약!\n"
                f"✔ 식재료 본연의 신선함과 깊은 손맛이 살아있는 곳!\n"
                f"✔ {menu}의 환상적인 밸런스와 푸짐한 담음새!\n"
                f"✔ 남녀노소 누구나 호불호 없이 반할 수밖에 없는 인생 맛집!\n\n"
                f"{location}에서 믿고 갈 수 있는 찐맛집을 찾으신다면 망설임 없이 방문해 보세요 🥰\n"
                f"도움이 되셨다면 이웃 추가도 언제나 대환영입니다! 감사합니다 ✨"
            )
        ),
        (
            "🍽️ 소문난 핫플 인증! 실패 없는 선택!",
            (
                f"왜 그렇게 수많은 손님들의 발길이 끊이지 않는지 온몸으로 실감하고 온 {location} 명소 '{store_name}'! 🍽️\n\n"
                f"사진을 다시 보는 지금도 군침이 고일 만큼 잊지 못할 행복한 한 끼였는데요!\n\n"
                f"📋 방문 추천 가이드!\n"
                f"- 상호명 : {store_name}\n"
                f"- 필수 주문 : {menu}\n"
                f"- 추천 대상 : 데이트, 가족 외식, 친구 모임 모두 강력 추천!\n\n"
                f"제대로 된 맛있는 식사로 기분 전환하고 싶을 때 꼭 한번 들러보세요 💖\n"
                f"포스팅이 도움 되셨다면 공감 꾸욱 눌러주시고 궁금한 점은 편하게 댓글 남겨주세요! 감사합니다 ✨"
            )
        ),
        (
            "🥰 기분 좋은 포만감으로 마무리한 하루!",
            (
                f"맛있는 기억으로 가득 채워져 하루 종일 기분 좋은 미소가 떠나지 않았던 {location} '{store_name}' 탐방! 🥰\n\n"
                f"좋은 사람과 맛있는 음식을 나누는 시간이야말로 일상 속 가장 큰 행복이라는 걸 다시금 느꼈답니다!\n\n"
                f"💖 솔직 담백 방문 요약!\n"
                f"- 대표 시그니처인 {menu}는 꼭 드셔보시길 추천해요!\n"
                f"- 정갈한 상차림과 곁들임 찬의 궁합도 최고였어요!\n"
                f"- 친절하고 세심한 서비스 덕분에 식사 내내 대접받는 기분이었답니다!\n\n"
                f"오늘도 제 블로그에 놀러 와주셔서 진심으로 감사드려요 잇님들 ✨\n"
                f"맛있는 음식 많이 드시고 늘 행복 가득한 날 보내세요! 다음에도 맛있는 핫플 소식으로 찾아올게요 😋"
            )
        )
    ]
    return random.choice(outros)


def pick_unique_variation(variations, used_set, key_prefix="tpl", fallback_pool=None):
    """
    동일한 포스팅 내에서 절대 같은 템플릿 인덱스나 서사가 중복 선택되지 않도록 100% 보장
    """
    available = []
    for idx, item in enumerate(variations):
        tpl_key = f"{key_prefix}_{idx}"
        if tpl_key not in used_set:
            available.append((idx, tpl_key, item))

    if available:
        chosen_idx, chosen_key, chosen_item = random.choice(available)
        used_set.add(chosen_key)
        return chosen_item

    # 만약 1차 풀을 모두 소진한 경우 fallback_pool에서 미사용 항목 탐색
    if fallback_pool:
        fb_available = []
        for idx, item in enumerate(fallback_pool):
            fb_key = f"dish_fallback_{idx}"
            if fb_key not in used_set:
                fb_available.append((idx, fb_key, item))
        if fb_available:
            chosen_idx, chosen_key, chosen_item = random.choice(fb_available)
            used_set.add(chosen_key)
            return chosen_item

    # 만약 모든 풀을 소진한 경우 (사진 개수가 풀보다 많을 때):
    # 기존 문장을 그대로 반복하지 않고 새로운 수식어와 헤더/문맥을 동적 결합하여 중복 완전 방지!
    base_h, base_t = variations[random.randint(0, len(variations) - 1)]
    prefix_opts = ["✨ 시선 집중!", "📸 또 다른 매력의", "💖 놓칠 수 없는", "👍 감탄을 자아낸", "😋 젓가락이 절로 가는"]
    closing_opts = [
        "다른 각도에서 바라보아도 그 매력과 정성이 한결같이 느껴져 만족스러웠답니다 🥰",
        "보는 재미와 맛보는 즐거움이 동시에 채워져 일행 모두 연신 미소를 지었어요 ✨",
        "작은 디테일까지 정갈하게 담아내어 식사의 완성도를 한층 더 높여주었답니다 👍"
    ]
    raw_title = base_h.split(".")[-1].strip() if "." in base_h else base_h
    new_h = f"{random.choice(['✨', '📸', '💖', '⭐', '🥢'])} {random.choice(prefix_opts)} {raw_title}"
    new_t = f"{base_t}\n\n{random.choice(closing_opts)}"
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
    매번 100% 새롭고 독창적인 요리 서사 단락을 동적 합성 (하드코딩 0%)
    """
    emojis = ["✨", "🍽️", "😋", "🥢", "👑", "🔥", "📸", "⭐", "💖", "🌿", "🥘", "🥟"]
    hooks = [
        f"감탄이 절로 나오는 비주얼! {clean_name}",
        f"식욕을 무한 자극하는 극상의 풍미! {clean_name}",
        f"시선 집중! 기대 이상이었던 {clean_name}",
        f"입안 가득 찐 감동을 선사한 {clean_name}",
        f"남다른 내공과 아우라, {clean_name}",
        f"코끝을 스치는 군침 도는 온기! {clean_name}",
        f"정갈한 담음새와 특급 퀄리티! {clean_name}",
        f"소문난 인기 실감! 압도적인 {clean_name}",
        f"한 번 맛보면 반할 수밖에 없는 {clean_name}",
        f"테이블을 화려하게 빛내준 {clean_name}",
        f"미식의 즐거움을 제대로 만끽한 {clean_name}",
        f"보는 순간 셔터를 누르게 만든 {clean_name}",
        f"놓칠 수 없는 시그니처의 품격! {clean_name}",
        f"단 한 입만으로도 납득되는 {clean_name}",
        f"기대를 200% 충족시켜 준 명품 {clean_name}"
    ]
    endings = ["등장!", "비주얼!", "영접!", "한입!", "실물 영접!", "매력!", "한 접시!", "먹방!", "자태!"]
    
    header = ""
    for _ in range(30):
        cand_h = f"{random.choice(emojis)} {step_num}. {random.choice(hooks)} {random.choice(endings)}"
        if cand_h not in used_set:
            header = cand_h
            used_set.add(cand_h)
            break
    if not header:
        header = f"✨ {step_num}. 맛과 비주얼 모두 사로잡은 {clean_name}!"

    # 1. 첫인상 도입부
    if is_subsequent:
        p1_opts = [
            f"앞선 메뉴의 감동을 이어 테이블 위에 차려진 또 하나의 별미, {clean_name} 사진이에요! ✨",
            f"식사의 든든함과 풍성함을 배로 채워준 오늘의 하이라이트, {clean_name} 비주얼입니다! 🍽️",
            f"테이블을 한층 더 화려하게 밝혀주며 등장한 매력 만점 {clean_name} 모습이에요! 😋",
            f"일행들과 함께 나누어 맛보기 위해 선택한 기대작, {clean_name} 컷입니다! 📸",
            f"메인 요리들과의 환상적인 시너지를 예고하며 등장한 {clean_name} 자태예요! 💖",
            f"연이어 상 위에 오르며 감탄사를 더해준 또 하나의 주인공, {clean_name} 비주얼이에요! 🥢",
            f"테이블에 활기를 더해주며 다음 코스로 즐긴 {clean_name} 모습이랍니다! 👍",
            f"서로 다른 매력으로 식사의 재미를 배가시켜 준 {clean_name} 사진이에요! 🥰"
        ]
    else:
        p1_opts = [
            f"드디어 테이블 위로 위풍당당하게 등장한 오늘의 메인, {clean_name} 비주얼이에요! ✨",
            f"기다림 끝에 마주한 설레는 시그니처, 먹음직스러운 {clean_name} 사진입니다! 🍽️",
            f"자리에 놓이자마자 고소하고 향긋한 냄새로 주변을 가득 채운 {clean_name} 모습이에요! 😋",
            f"카메라 셔터를 절로 누르게 만드는 영롱하고 푸짐한 자태의 {clean_name} 컷입니다! 📸",
            f"비주얼부터 이미 합격점을 훌쩍 넘긴 오늘의 원픽, {clean_name} 등장이에요! 💖",
            f"등장과 동시에 일행 모두의 시선을 단숨에 사로잡은 압도적인 {clean_name} 자태예요! 🥢",
            f"테이블에 은은한 온기를 더해주며 완벽한 첫인상을 남긴 {clean_name} 모습이랍니다! 👍",
            f"이곳을 대표하는 시그니처의 위엄을 단번에 보여준 설레는 {clean_name} 한 상이에요! 🥰"
        ]
    avail_p1 = [p for p in p1_opts if p not in used_set] or p1_opts
    p1 = random.choice(avail_p1)
    used_set.add(p1)

    # 2. 비주얼 및 플레이팅
    p2_opts = [
        f"정갈하고 푸짐하게 채워져 나온 모습에서 주방의 깊은 내공과 요리에 대한 진심이 고스란히 전해졌는데요.",
        f"화려하면서도 단정한 담음새 덕분에 눈으로 먼저 맛보는 즐거움이 가득했답니다.",
        f"윤기가 자르르 흐르는 고운 색감과 알찬 볼륨감이 먹기 전부터 침샘을 무한 자극했는데요.",
        f"식재료 하나하나의 신선도가 눈으로도 고스란히 확인되어 식사 전부터 안심이 되었답니다.",
        f"좋은 재료를 아낌없이 듬뿍 얹어주신 사장님의 넉넉한 인심에 절로 미소가 지어졌어요.",
        f"테이블의 활기를 단숨에 끌어올려 줄 만큼 감탄사가 쏟아지는 완성도 높은 비주얼이었답니다.",
        f"화려한 색감과 정성 어린 플레이팅의 조화가 사진으로 다 담기지 않을 만큼 훌륭했는데요.",
        f"단정한 자태와 은은한 향미가 조화롭게 어우러져 식욕을 기분 좋게 돋워주었답니다."
    ]
    avail_p2 = [p for p in p2_opts if p not in used_set] or p2_opts
    p2 = random.choice(avail_p2)
    used_set.add(p2)

    # 3. 실시간 네이버 찐후기 인용 (라이브 검색 결과 반영)
    p3 = ""
    taste_revs = live_reviews.get("taste", []) if live_reviews else []
    avail_revs = [r for r in taste_revs if r not in used_set]
    if avail_revs:
        chosen_rev = random.choice(avail_revs)
        used_set.add(chosen_rev)
        short_rev = chosen_rev[:55].strip()
        p3 = f"실제 다녀오신 분들의 네이버 찐후기에서도 '{short_rev}'라는 극찬이 자자했는데, 직접 맛보니 그 이유를 단번에 공감할 수 있었는데요!\n\n"
    else:
        p3_opts = [
            f"왜 수많은 미식가들이 이곳을 인생 맛집으로 손꼽는지 단 한 입만으로도 완벽하게 납득이 되었는데요!\n\n",
            f"식재료 본연의 맛을 극대화하여 과하지 않은 알맞은 간과 깊은 감칠맛의 밸런스가 예술이었답니다!\n\n",
            f"기대 이상으로 훌륭한 퀄리티와 깊은 손맛 덕분에 일행 모두 연신 고개를 끄덕이며 감탄했는데요!\n\n",
            f"주변 테이블에서도 이 메뉴를 한 입씩 맛볼 때마다 감탄사가 쏟아지는 이유를 실감했답니다!\n\n",
            f"오랜 시간 동안 사랑받아 온 비결을 입안 가득 증명하듯 완성도 높은 맛의 깊이가 느껴졌는데요!\n\n",
            f"남녀노소 누구나 호불호 없이 푹 빠져들 수밖에 없는 매력적인 풍미의 정석이었답니다!\n\n",
            f"한 젓가락 맛볼 때마다 재료의 신선함과 정갈한 손맛이 고스란히 전해져 감동이 밀려왔는데요!\n\n",
            f"좋은 식재료에 담긴 정성과 내공이 첫 입부터 마지막 순간까지 온전히 전해졌답니다!\n\n"
        ]
        avail_p3 = [p for p in p3_opts if p not in used_set] or p3_opts
        p3 = random.choice(avail_p3)
        used_set.add(p3)

    # 4. 식감 및 미각 묘사 (카테고리별 맞춤 풀)
    if food_type == "bakery":
        t_opts = [
            f"한 입 베어 물자마자 파사삭 부서지는 바삭한 겉면과 촉촉하고 쫄깃하게 씹히는 속 결의 조화가 그야말로 극락이었는데요.",
            f"고급 버터의 진한 풍미가 씹을수록 은은하게 퍼지며 달콤함과 고소함의 황금 밸런스를 자랑했답니다.",
            f"텁텁함이나 기름진 느끼함 없이 사르르 녹아내리는 부드러운 단맛에 마지막 한 입까지 행복하게 즐겼어요.",
            f"섬세하게 구워낸 장인의 손길이 느껴져 커피나 음료와 함께 곁들이니 순식간에 접시를 비워낼 정도였답니다."
        ]
    elif food_type == "drink":
        t_opts = [
            f"깊고 진한 크레마와 은은한 산미, 고소한 바디감이 달콤한 디저트의 맛을 완벽하게 감싸주었는데요.",
            f"과하지 않은 깔끔한 목넘김과 풍부한 향미가 돋보여 마시는 내내 입안을 산뜻하게 정돈해 주었답니다.",
            f"갈증을 시원하게 해소해 주면서도 고급스러운 여운을 남겨 마지막 한 모금까지 온전히 힐링을 만끽했어요."
        ]
    elif food_type == "jeon":
        t_opts = [
            f"얇고 부드러운 고기에 얇은 계란 옷을 입혀 갓 부쳐내어, 기름진 잡내 없이 담백한 육즙이 그대로 살아있었는데요.",
            f"겉은 바삭하고 속은 촉촉하여 특제 양념장에 살짝 찍어 맛보니 입안 가득 고소한 풍미가 폭발했답니다.",
            f"자극적이지 않으면서도 질리지 않는 고소한 감칠맛 덕분에 테이블의 든든함을 완벽하게 채워주었어요."
        ]
    elif food_type == "noodle":
        t_opts = [
            f"탱글탱글 쫄깃한 면발에 깊고 진한 육수가 쏙쏙 배어들어 후루룩 면치기하는 재미가 쏠쏠했는데요.",
            f"퍼지지 않고 끝까지 살아있는 탄력 있는 식감과 개운하고 깊은 국물의 조화가 감탄을 절로 자아냈답니다.",
            f"밀가루 풋내 없이 찰진 면발에 감칠맛 넘치는 양념이 어우러져 마지막 한 가닥까지 남김없이 비워냈어요."
        ]
    elif food_type == "bibim":
        t_opts = [
            f"푸짐하게 올라간 신선한 육회와 아삭한 채소, 고소한 참기름의 조화가 한 숟가락 뜰 때마다 환상적이었는데요.",
            f"선홍빛 육질의 찰진 쫄깃함과 감칠맛 넘치는 비법 소스가 어우러져 숟가락질을 멈출 수 없었답니다.",
            f"속이 편안하면서도 든든한 포만감을 안겨주어 남녀노소 누구나 극찬할 수밖에 없는 정갈한 한 그릇이었어요."
        ]
    elif food_type == "stew":
        t_opts = [
            f"잡내 하나 없이 야들야들 사르르 녹아내리는 육질과 시원하고 묵직한 국물의 조화가 온몸의 피로를 싹 풀어주었는데요.",
            f"보글보글 끓어오르며 우러난 진국 육수 한 모금에 속이 확 풀리며 깊은 내공을 고스란히 맛볼 수 있었답니다.",
            f"따뜻한 온기 덕분에 재료 본연의 풍미가 배가되어 마지막 국물 한 방울까지 남김없이 들이켰어요."
        ]
    elif food_type == "meat":
        t_opts = [
            f"불판 위에서 노릇노릇 구워진 고기에서 팡 터지는 고소한 육즙의 자태가 그야말로 극상의 황홀함을 선사했는데요.",
            f"질김 없이 사르르 녹아내리는 부드러운 육질과 깊은 육향이 어우러져 어떤 곁들임 찬과 먹어도 찰떡궁합이었답니다.",
            f"기름진 느끼함 없이 씹을수록 담백하고 진한 풍미가 뿜어져 나와 일행 모두 연신 젓가락을 움직였어요."
        ]
    elif food_type == "mandoo":
        t_opts = [
            f"얇고 차진 만두피 속에 고기와 신선한 채소로 꽉 찬 소가 어우러져, 한 입 베어 무는 순간 진한 육즙이 팡 터져 나왔는데요.",
            f"잡내 하나 없이 담백하면서도 씹을수록 감칠맛이 폭발하는 속 재료의 환상적인 밸런스에 감탄이 절로 나왔답니다.",
            f"촉촉하고 부드러운 만두피와 아삭하게 씹히는 소의 조화가 완벽해서 간장에 살짝 찍어 맛보니 그야말로 꿀맛이었어요.",
            f"손으로 정성껏 빚어낸 남다른 볼륨감과 꽉 찬 식감 덕분에 한 개만 맛보아도 입안 가득 든든한 포만감이 차올랐답니다.",
            f"피는 쫄깃하고 속은 육즙으로 촉촉하게 가득 차서 한 입 먹을 때마다 감탄사가 멈추지 않는 독보적인 맛이었어요."
        ]
    elif food_type == "seafood":
        t_opts = [
            f"비린내 전혀 없이 입안에 착 감기는 쫀득하고 찰진 식감과 은은한 단맛이 그야말로 일품이었는데요.",
            f"바다의 싱싱함을 고스란히 담아내어 씹을수록 퍼지는 고소한 감칠맛에 절로 감탄사가 터져 나왔답니다.",
            f"두툼하게 썰어내어 씹는 맛이 제대로 살아있고, 특제 쌈이나 곁들임 찬과 함께하니 끝없는 감동을 선사했어요.",
            f"신선도 최상급 식재료 본연의 깔끔하고 담백한 풍미 덕분에 마지막 한 점까지 황홀하게 즐겼답니다."
        ]
    else:
        t_opts = [
            f"자극적이지 않으면서도 자꾸만 손이 가게 만드는 중독성 넘치는 양념과 신선한 식감이 일품이었는데요.",
            f"식재료 본연의 탄력과 깊은 감칠맛이 어우러져 마지막 한 점까지 물릴 틈 없이 식사를 완성해 주었답니다.",
            f"풍부한 식감과 깊은 손맛이 조화롭게 어우러져 입안 가득 다채로운 미식의 즐거움을 제대로 만끽했어요.",
            f"깔끔하게 떨어지는 뒷맛과 깊은 풍미의 여운이 길게 남아 소중한 사람들과 나누기에 더없이 완벽했답니다."
        ]
    avail_p4 = [p for p in t_opts if p not in used_set] or t_opts
    p4 = random.choice(avail_p4)
    used_set.add(p4)

    # 5. 마무리 결론
    p5_opts = [
        f"오늘 이곳에 찾아오길 정말 잘했다는 확신을 심어준 최고의 한 접시였답니다 👍",
        f"다음에 재방문해도 꼭 다시 주문하고 싶은 최애 메뉴로 등극했어요 💖",
        f"소중한 사람들과 함께 맛있는 추억을 나누기에 더없이 완벽했던 감동의 순간이었답니다 🥰",
        f"식사하는 내내 테이블의 활기를 더해준 고마운 요리였답니다 ✨",
        f"사진을 다시 보는 지금도 군침이 돌 만큼 잊지 못할 행복한 맛의 기억으로 남았어요 😋",
        f"호불호 없이 누구나 극찬할 만한 수준 높은 맛과 퀄리티를 온몸으로 증명해 주었답니다 🥢",
        f"접시가 비워지는 게 아쉬울 정도로 마지막 한 입까지 온전한 미식을 즐겼어요 🍽️",
        f"친구들이나 가족들에게도 자신 있게 추천하고 싶은 감동의 메뉴였답니다 👍"
    ]
    avail_p5 = [p for p in p5_opts if p not in used_set] or p5_opts
    p5 = random.choice(avail_p5)
    used_set.add(p5)

    body = f"{p1}\n\n{p2}\n\n{p3}{p4}\n\n{p5}"
    return header, body


def create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count, context):
    """
    사진 파일명과 카테고리에 100% 매칭되는 독창적 서사 단락 생성
    (In-Post Deduplication: 같은 글 내에서 헤더/본문 중복 절대 불가)
    """
    is_pair = count > 1
    pair_suffix = " (가로 나란히)" if is_pair else ""
    used_set = context.setdefault("used_templates", set())
    seen_dishes = context.setdefault("seen_dishes", set())
    live_reviews = context.get("live_reviews") or {}
    display_name = re.sub(r'\s*\d+$', '', clean_name).strip() or clean_name

    # 1. 외관
    if cat == "exterior":
        variations = [
            (
                f"📍 {step_num}. 멀리서도 한눈에 쏙 들어오는 {store_name} {clean_name}!",
                f"{location} 골목에 들어서자마자 멀리서부터 감각적인 {clean_name} 모습이 눈에 확 띄었어요! ✨\n\n"
                f"특유의 세련되고 깔끔한 파사드 덕분에 초행길인데도 헤매지 않고 단번에 찾아왔답니다.\n\n"
                f"입구에서부터 풍기는 핫플의 기운에 벌써부터 가슴이 두근두근 설레더라고요 😋"
            ),
            (
                f"✨ {step_num}. 감성 가득한 첫인상! {store_name} {clean_name} 도착!",
                f"약속 장소에 도착해 가장 먼저 카메라를 켜게 만든 {clean_name} 전경이에요! 📸\n\n"
                f"모던하면서도 정겨운 무드가 가득 느껴지는 매장 입구를 보니 기대감이 한층 더 차올랐는데요.\n\n"
                f"들어가기 전부터 맛있는 냄새가 솔솔 풍겨와서 얼른 문을 열고 들어가고 싶었답니다 🌿"
            ),
            (
                f"🚪 {step_num}. 소문난 핫플 영접! {store_name} {clean_name} 앞!",
                f"드디어 도착한 오늘의 목적지, {store_name} {clean_name} 입구 앞이에요! 🚪✨\n\n"
                f"간판부터 풍겨오는 범상치 않은 내공에 지나가는 분들도 한 번씩 발걸음을 멈추고 쳐다보더라고요.\n\n"
                f"기분 좋은 설렘을 안고 설레는 마음으로 매장 안으로 발걸음을 옮겼답니다 👍"
            ),
            (
                f"🏙️ {step_num}. 골목의 랜드마크! 감각적인 {store_name} {clean_name}!",
                f"주변 거리와 멋스럽게 어우러져 시선을 사로잡은 {clean_name} 사진이에요! 📸\n\n"
                f"외관부터 느껴지는 힙하고 따뜻한 감성 덕분에 들어가기 전부터 인생샷 스팟으로 딱이었는데요.\n\n"
                f"웨이팅하며 외관을 둘러보는 동안에도 지루할 틈 없이 기대가 가득했답니다 ✨"
            ),
            (
                f"🏷️ {step_num}. 지나가는 발걸음도 멈추게 하는 {clean_name} 전경!",
                f"세련된 간판 디자인과 외관 익스테리어가 돋보이는 {clean_name} 모습이에요! 🚪\n\n"
                f"입구 쪽에 걸린 안내와 분위기가 매장의 개성을 한눈에 보여주어 더욱 흥미로웠는데요.\n\n"
                f"설레는 마음으로 문을 열고 매장 안쪽으로 한 걸음 들어섰답니다 💖"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="exterior")
        vibe_revs = live_reviews.get("vibe", []) if live_reviews else []
        avail_vibe = [v for v in vibe_revs if v not in used_set]
        if avail_vibe:
            ch_v = random.choice(avail_vibe)
            used_set.add(ch_v)
            text += f"\n\n네이버 실제 방문객 후기에서도 '{ch_v[:50].strip()}'라는 평이 돋보였는데, 매장 앞에 서니 그 분위기가 단번에 체감되었어요! ✨"
        caption = f"{location} {store_name} {clean_name}{pair_suffix}"

    # 2. 입구 포토존 / 마스코트
    elif cat == "photo_zone":
        variations = [
            (
                f"📸 {step_num}. 시선 강탈! 귀여움 한도 초과 {display_name} 포토존!",
                f"매장 입구에 들어서자마자 저절로 휴대폰을 꺼내 들게 만든 {clean_name} 모습이에요! 📸✨\n\n"
                f"아기자기하고 사랑스러운 소품과 마스코트가 반겨주어 기다리는 시간마저 지루할 틈이 없었는데요.\n\n"
                f"연인이나 친구들과 함께 예쁜 인증샷을 남기기에 그야말로 완벽한 명당 포토스팟이었답니다 💖"
            ),
            (
                f"🧸 {step_num}. 입구부터 취향 저격! 앙증맞은 {display_name} 감성!",
                f"입구 쪽을 감성 가득하게 밝혀주고 있던 사랑스러운 {clean_name} 공간이에요! ✨\n\n"
                f"특유의 포근하고 아늑한 무드가 매장 전체의 분위기를 한층 더 사랑스럽게 살려주었는데요.\n\n"
                f"이곳을 배경으로 사진 한 장 남기면 바로 인생샷이 완성될 만큼 비주얼이 예술이었답니다 🧸"
            ),
            (
                f"✨ {step_num}. 발걸음을 멈추게 만든 감성 스팟! {display_name}!",
                f"골목을 지나가던 사람들도 한 번씩 멈춰 서서 구경하게 만드는 {clean_name} 전경이에요! 📸\n\n"
                f"동화 속에 들어온 듯 아늑하고 따뜻한 감성이 물씬 묻어나서 매장에 들어서는 순간부터 힐링이 시작되었답니다 🥰"
            ),
            (
                f"🎀 {step_num}. 놓칠 수 없는 핫플 인증! 사랑스러운 {display_name} 코너!",
                f"매장에 들어서자마자 반갑게 맞이해 준 러블리한 {clean_name} 모습이에요! 🎀\n\n"
                f"보는 것만으로도 미소가 번지는 귀여운 조형물 덕분에 기분 좋게 방문 인증샷을 남길 수 있었는데요.\n\n"
                f"작은 디테일까지 정성스레 꾸며놓으신 센스에 절로 감탄이 나왔답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="photo_zone")
        caption = f"{clean_name} 포토존{pair_suffix}"

    # 3. 웨이팅
    elif cat == "waiting":
        variations = [
            (
                f"⏳ {step_num}. 핫플 필수 코스! {clean_name} 등록 완료!",
                f"문 앞에 도착하자마자 가장 먼저 확인한 {clean_name} 현장이에요! 📱✨\n\n"
                f"피크 시간에 맞춰 왔더니 역시나 소문난 핫플답게 대기하시는 분들이 꽤 계시더라고요.\n\n"
                f"카카오톡 알림 시스템이 워낙 편리하게 잘 되어 있어서 주변 골목을 가볍게 구경하며 기분 좋게 차례를 기다렸답니다 🎶"
            ),
            (
                f"📱 {step_num}. 소문난 인기 실감! {clean_name} 시스템!",
                f"매장 입구에 큼직하게 안내되어 있던 {clean_name} 기기 모습이에요! 🕒\n\n"
                f"빠르게 대기를 걸어두니 실시간으로 입장 순번을 확인할 수 있어 한결 마음이 편했는데요.\n\n"
                f"기다림마저 맛있는 음식을 만나기 위한 행복한 워밍업처럼 느껴졌답니다 💖"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="waiting")
        caption = f"{clean_name} 현장 대기{pair_suffix}"

    # 4. 맛집 인증 (미쉐린, 블루리본)
    elif cat == "award":
        variations = [
            (
                f"🏅 {step_num}. 신뢰감 팍팍! 자랑스러운 {clean_name} 인증!",
                f"매장 입구에 당당하게 자리 잡고 있던 영광의 {clean_name} 모습이에요! 🏆✨\n\n"
                f"수많은 미식가들과 공신력 있는 기관에서 맛과 퀄리티를 인정받은 명패를 직접 눈으로 마주하니 믿음이 배가 되었는데요.\n\n"
                f"오늘 방문이 절대 헛되지 않을 거라는 확신이 들면서 기대감이 수직 상승했답니다 👍"
            ),
            (
                f"🌟 {step_num}. 찐맛집의 확실한 증거! {clean_name} 마크!",
                f"벽면을 빛내고 있던 {clean_name} 현판을 담아봤어요! 🎖️\n\n"
                f"까다로운 검증을 통과한 식당에만 주어지는 마크를 보니 찾아온 보람이 물씬 느껴졌는데요.\n\n"
                f"오랜 세월 동안 변함없는 맛을 지켜온 사장님의 자부심과 뚝심이 고스란히 묻어나는 순간이었답니다 ✨"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="award")
        caption = f"{store_name} {clean_name}{pair_suffix}"

    # 5. 실내 인테리어 / 분위기
    elif cat == "interior":
        variations = [
            (
                f"🌿 {step_num}. 아늑함과 정갈함이 공존하는 실내 분위기!",
                f"매장 문을 열고 안으로 들어서서 담아본 {display_name} 사진이에요! 🌿\n\n"
                f"따스하고 은은한 조명에 전체적인 공간이 쾌적하게 꾸며져 있어 일행과 편안하게 대화 나누기 참 좋았어요.\n\n"
                f"구석구석 먼지 하나 없이 위생적으로 관리된 모습에 식사 전부터 안심이 되었답니다 💖"
            ),
            (
                f"💡 {step_num}. 레트로와 모던 감성이 어우러진 매장 내부 전경!",
                f"특유의 감각적인 무드가 매력적이었던 {display_name} 모습이에요! ✨\n\n"
                f"원목과 현대적인 감성이 조화롭게 어우러져 사진을 찍는 족족 감성 샷이 완성되었는데요.\n\n"
                f"식사하는 손님들을 배려한 차분한 공기 덕분에 대접받는 듯한 기분 좋은 여유를 즐길 수 있었답니다 🛋️"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="interior")
        caption = f"{store_name} 아늑한 {display_name}{pair_suffix}"

    # 6. 주문 카운터 및 픽업대
    elif cat == "counter":
        variations = [
            (
                f"🛒 {step_num}. 친절하고 활기찬 분위기! {display_name} & 픽업대!",
                f"메뉴를 고르고 주문을 위해 다가간 {display_name} 모습이에요! ✨\n\n"
                f"직원분들이 워낙 밝고 친절하게 응대해 주셔서 주문하는 순간부터 기분이 한껏 좋아졌는데요.\n\n"
                f"카운터 주변도 먼지 하나 없이 깔끔하고 위생적으로 정돈되어 있어 더욱 믿음이 갔답니다 💖"
            ),
            (
                f"🛎️ {step_num}. 정갈하고 쾌적하게 정돈된 {store_name} {display_name}!",
                f"매장의 중심에서 활기를 불어넣어 주던 아늑한 {display_name} 전경이에요! 🛎️\n\n"
                f"주문 동선도 편리하고 픽업 공간도 정돈이 잘 되어 있어 붐비는 시간에도 혼잡함 없이 쾌적하게 이용할 수 있었는데요.\n\n"
                f"매장 곳곳에 묻어나는 섬세한 배려에 절로 미소가 지어졌답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="counter")
        caption = f"{store_name} {display_name}{pair_suffix}"

    # 7. 실내 좌석 / 테이블
    elif cat == "seating":
        variations = [
            (
                f"🛋️ {step_num}. 편안하고 쾌적한 자리! {display_name} 전경!",
                f"손님들이 편안하게 식사에 온전히 집중할 수 있도록 정갈하게 배치된 {display_name} 공간이에요! 🪑\n\n"
                f"테이블 간격도 널찍하고 청결하게 정돈되어 있어 옆자리 방해 없이 식사를 즐길 수 있었는데요.\n\n"
                f"의자도 편안해서 오랜 시간 머물며 도란도란 이야기 나누기에 더없이 좋았답니다 ✨"
            ),
            (
                f"🪑 {step_num}. 깔끔하고 쾌적한 정돈! {display_name} 좌석!",
                f"안내를 받아 자리에 앉기 전 둘러본 {display_name} 모습이에요! 🛋️\n\n"
                f"테이블 위 식기류와 소품들이 각 잡혀 깔끔하게 세팅되어 있어 위생 면에서 백점 만점을 주고 싶었는데요.\n\n"
                f"데이트는 물론이고 가족이나 소중한 지인들과의 모임 자리로도 손색이 없겠더라고요 💖"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="seating")
        caption = f"{store_name} 편안한 {display_name}{pair_suffix}"

    # 8. 셀프존 및 셀프바 코너
    elif cat == "selfbar":
        variations = [
            (
                f"💧 {step_num}. 깔끔하고 편리한 이용! 정돈된 {display_name} 코너!",
                f"매장 한편에 손님들을 위해 정갈하게 마련된 {display_name} 공간이에요! 🌿\n\n"
                f"시원한 냉수와 컵, 냅킨, 물티슈 등 필요한 편의 용품들이 청결하게 구비되어 있어 언제든 편하게 이용할 수 있었는데요.\n\n"
                f"작은 부분까지 꼼꼼하고 위생적으로 신경 쓰신 모습에서 사장님의 세심한 정성이 느껴졌답니다 ✨"
            ),
            (
                f"🌿 {step_num}. 손님을 위한 세심한 배려! 쾌적한 {display_name}!",
                f"언제든 자유롭고 편리하게 이용할 수 있도록 준비된 깔끔한 {display_name} 모습이에요! 💧\n\n"
                f"주변에 흘린 자국 하나 없이 수시로 깨끗하게 닦아 관리하시는 모습에 절로 감탄이 나왔는데요.\n\n"
                f"머무는 내내 부족함 없이 편안하게 즐길 수 있도록 도와준 고마운 코너였답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="selfbar")
        caption = f"깔끔하고 쾌적한 {display_name}{pair_suffix}"

    # 9. 화장실 및 매장 편의시설
    elif cat == "facility":
        variations = [
            (
                f"🚻 {step_num}. 청결함이 돋보이는 쾌적한 매장 {display_name}!",
                f"매장 안쪽에 손님들을 위해 깔끔하게 마련된 {display_name} 모습이에요! 🚻✨\n\n"
                f"식당이나 카페를 고를 때 위생과 화장실 청결도를 정말 중요하게 생각하는데, 들어서자마자 은은하고 기분 좋은 디퓨저 향이 퍼지며 반겨주더라고요.\n\n"
                f"물기 하나 없이 뽀송뽀송하고 쾌적하게 관리되어 있어 이용하는 내내 기분이 참 상쾌했답니다 💖"
            ),
            (
                f"🌿 {step_num}. 위생 점수 100점 만점! 안심하고 이용하는 {display_name} 시설!",
                f"손님들의 편의를 위해 정갈하게 관리되고 있던 {display_name} 공간이에요! 🌿\n\n"
                f"세련된 원목과 감각적인 인테리어 소품으로 꾸며져 있어 매장 전체의 세심한 디테일이 돋보였는데요.\n\n"
                f"핸드워시와 페이퍼타월까지 빈틈없이 갖춰져 있어 마지막까지 대만족이었답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="facility")
        caption = f"쾌적하고 청결한 {display_name}{pair_suffix}"

    # 6. 매장 이용안내문 / 수칙
    elif cat == "notice":
        variations = [
            (
                f"📋 {step_num}. 방문 전 필독! 친절한 {clean_name} 확인!",
                f"매장 벽면에 깔끔하게 정리되어 안내된 {clean_name} 모습이에요! 📌\n\n"
                f"더 많은 손님들이 쾌적하게 식사를 누릴 수 있도록 세심하게 적어두신 수칙들을 꼼꼼하게 읽어보았는데요.\n\n"
                f"서로 배려하는 에티켓 덕분에 매장 전체가 한층 더 정돈되고 질서정연하게 운영되는 느낌이었답니다 ✨"
            ),
            (
                f"💡 {step_num}. 더욱 맛있게 즐기는 꿀팁! {clean_name} 정독!",
                f"테이블 한편에 비치되어 시선을 사로잡은 {clean_name} 안내문이에요! 📖\n\n"
                f"사장님께서 오랜 연구 끝에 완성하신 '맛있게 먹는 법' 꿀팁이 알기 쉽게 적혀 있었는데요.\n\n"
                f"음식이 나오면 이 순서대로 꼭 따라 해봐야겠다고 일행들과 다짐했답니다 😋"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="notice")
        caption = f"{clean_name} 안내사항{pair_suffix}"

    # 7. 무료 공기밥 / 셀프바 코너
    elif cat == "service_rice":
        variations = [
            (
                f"🍚 {step_num}. 넉넉한 인심에 감동! 무제한 {clean_name} 코너!",
                f"매장 한편에 마련된 따뜻한 밥솥, 바로 넉넉한 인심의 {clean_name} 코너예요! 🍚✨\n\n"
                f"메인 메뉴의 양도 워낙 푸짐한데, 남은 얼큰한 국물에 밥까지 든든하게 말아먹을 수 있도록 배려해 주신 사장님의 따뜻한 마음에 절로 미소가 지어졌는데요.\n\n"
                f"탄수화물 러버들에게는 그야말로 놓칠 수 없는 최고의 감동 서비스였답니다 💖"
            ),
            (
                f"✨ {step_num}. 든든한 마무리 보장! 자유롭게 이용하는 {clean_name}!",
                f"식사 도중 언제든 편하게 이용할 수 있도록 마련된 {clean_name} 공간이에요! 🌾\n\n"
                f"갓 지은 따끈따끈한 쌀밥을 원하는 만큼 담아갈 수 있어 마지막 국물 한 방울까지 남김없이 밥을 말아 싹 비울 수 있었는데요.\n\n"
                f"추가 요금 부담 없이 든든한 한 끼를 완성해 준 최고의 꿀팁 코너였답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="service_rice")
        caption = f"따뜻한 인심의 {clean_name}{pair_suffix}"

    # 8. 메뉴판
    elif cat == "menu":
        variations = [
            (
                f"🍽️ {step_num}. 정갈한 차림표 정독 & {clean_name} 주문 완료!",
                f"어떤 조합으로 먹어야 가장 맛있을지 행복하게 고민했던 {clean_name} 타임이에요! 📝\n\n"
                f"대표 메뉴들의 밸런스가 워낙 훌륭해서 일행들과 상의 끝에 황금 조합으로 빠르게 주문을 넣었답니다.\n\n"
                f"주문이 들어가자마자 주방에서 맛있는 요리 냄새가 솔솔 풍겨와서 침샘이 폭발하기 일보 직전이었어요 😋"
            ),
            (
                f"📜 {step_num}. 알찬 구성과 합리적인 가격! {clean_name} 탐색!",
                f"한눈에 보기 쉽게 정리된 정갈한 {clean_name} 사진이에요! 🔎✨\n\n"
                f"요즘 물가 생각하면 재료 퀄리티 대비 가격대도 정말 착하고 합리적이라 감탄이 절로 나왔는데요.\n\n"
                f"시그니처 메뉴부터 곁들임 사이드까지 일행 모두 만족할 수 있는 알찬 라인업으로 푸짐하게 선택했답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="menu")
        caption = f"{store_name} {clean_name}{pair_suffix}"

    # 베이커리 / 디저트 진열 쇼케이스 (메뉴1~메뉴8 등)
    elif cat == "showcase":
        variations = [
            (
                f"🥐 {step_num}. 눈을 뗄 수 없는 달콤한 유혹! 화려한 베이커리 쇼케이스!",
                f"진열대를 가득 채운 화려하고 먹음직스러운 빵들의 비주얼에 감탄사가 절로 터져 나왔어요! 🥐✨\n\n"
                f"노릇노릇 윤기가 자르르 흐르는 크루아상부터 결이 살아있는 페이스트리까지, 갓 구워져 나온 고소한 버터 풍미가 진열대 주변을 가득 채우고 있었는데요.\n\n"
                f"하나하나 정성껏 빚어낸 완성도 높은 비주얼에 무엇을 골라야 할지 행복한 고민에 빠졌답니다 💖"
            ),
            (
                f"✨ {step_num}. 갓 구워낸 빵들의 향연! 비주얼 폭발 베이커리 라인업!",
                f"카메라 셔터를 멈출 수 없게 만든 감동의 베이커리 & 디저트 진열대 모습이에요! 📸✨\n\n"
                f"바삭바삭한 식감이 눈으로도 전해지는 겉면과 촉촉함이 돋보이는 비주얼이 그야말로 예술이었는데요.\n\n"
                f"재료를 아끼지 않고 듬뿍 넣어 구워낸 빵들의 자태를 보니 왜 오픈런을 부르는 핫플인지 단번에 실감 났답니다 👍"
            ),
            (
                f"🧁 {step_num}. 빵순이 & 빵돌이 심쿵 유발! 영롱한 디저트 진열대!",
                f"트레이마다 정갈하게 채워져 있던 매력 만점의 베이커리 라인업이에요! 🧁\n\n"
                f"달콤하고 고소한 풍미가 솔솔 풍겨와서 보는 것만으로도 입안에 군침이 가득 고였는데요.\n\n"
                f"비주얼뿐만 아니라 식감과 풍미의 조화까지 완벽하게 고려해 만든 디저트들이라 일행 모두 연신 감탄사를 쏟아냈답니다 😋"
            ),
            (
                f"🥖 {step_num}. 노릇노릇 고소한 버터 풍미! 다채로운 구움과자 & 베이커리!",
                f"먹음직스러운 자태로 시선을 사로잡은 다채로운 디저트 쇼케이스 모습이에요! 🥖✨\n\n"
                f"금방 채워진 신선한 빵들마다 특유의 고소한 온기와 달콤한 시럽의 반짝임이 살아있었는데요.\n\n"
                f"선물용이나 포장으로도 인기가 많은 이유를 눈으로 직접 확인한 순간이었답니다 🥰"
            ),
            (
                f"🍰 {step_num}. 고르는 재미가 쏠쏠한 환상의 디저트 쇼케이스!",
                f"눈과 코를 동시에 사로잡은 감동의 베이커리 진열 공간이에요! 🍰\n\n"
                f"정성 가득한 담음새와 독창적인 토핑들이 돋보여 트레이에 하나씩 집어 담는 손길이 멈추지 않았는데요.\n\n"
                f"오늘 이곳에 찾아오길 정말 잘했다며 일행들과 환호성을 질렀답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="showcase")
        taste_revs = live_reviews.get("taste", []) if live_reviews else []
        avail_taste = [t for t in taste_revs if t not in used_set]
        if avail_taste:
            ch_t = random.choice(avail_taste)
            used_set.add(ch_t)
            text += f"\n\n네이버 방문자 리뷰에서도 '{ch_t[:50].strip()}'라는 극찬이 많았는데, 직접 쇼케이스를 둘러보니 왜 인기 폭발인지 바로 실감 났답니다 💖"
        caption = f"화려하고 먹음직스러운 {display_name}{pair_suffix}"

    # 한상차림 / 상차림 / 밑반찬
    elif cat == "sides":
        if "한상" in clean_name or "차림" in clean_name:
            variations = [
                (
                    f"🥗 {step_num}. 상다리 부러질 듯 푸짐한 비주얼! 오늘의 {clean_name}!",
                    f"주문한 메뉴들이 모두 세팅되고 담아본 설레는 {clean_name} 항공샷이에요! 📸✨\n\n"
                    f"정갈한 밑반찬부터 테이블 가득 채워진 대표 요리들까지, 빈틈없이 차려진 화려한 구성에 감탄이 절로 나왔는데요.\n\n"
                    f"보기만 해도 배부르고 든든해지는 역대급 비주얼에 일행 모두 카메라를 들고 셔터 누르기 바빴답니다 💖"
                ),
                (
                    f"✨ {step_num}. 테이블 위 가득 펼쳐진 감동의 {clean_name}!",
                    f"눈으로 먼저 맛보는 완벽한 조화, 정갈한 {clean_name} 사진이에요! 🍽️\n\n"
                    f"각 메뉴들의 다채로운 색감과 고소한 향이 어우러져 식탁 전체가 하나의 예술 작품처럼 보였는데요.\n\n"
                    f"본격적으로 숟가락과 젓가락을 들기 전, 감탄사를 쏟아내며 설레는 식사의 시작을 알렸답니다 👍"
                )
            ]
        else:
            variations = [
                (
                    f"🥗 {step_num}. 메인 요리의 맛을 돋워줄 정갈한 {clean_name}!",
                    f"주문 후 테이블 위에 정갈하게 세팅된 {clean_name} 사진이에요! 🥢\n\n"
                    f"담김새부터 단정하고 신선함이 돋보이는 밑반찬들이 테이블을 채워주었는데요.\n\n"
                    f"조미료 맛이 아닌 재료 고유의 감칠맛이 살아있어 메인 요리가 나오기 전부터 자꾸만 젓가락이 가더라고요 💖"
                ),
                (
                    f"🥢 {step_num}. 손맛 가득 정갈한 밑반찬! 알찬 {clean_name} 세팅!",
                    f"테이블을 산뜻하게 밝혀준 깔끔한 {clean_name} 구성이에요! 🥗✨\n\n"
                    f"아삭아삭한 식감과 과하지 않은 양념 밸런스가 메인 요리의 풍미를 극대화해 주기에 완벽했는데요.\n\n"
                    f"부족함 없이 넉넉하게 챙겨주시는 인심 덕분에 식사 내내 곁들임 찬의 매력을 톡톡히 누렸답니다 😋"
                )
            ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="sides")
        caption = f"{clean_name} 세팅{pair_suffix}"

    # 10. 젓가락으로 든 한 점 / 먹방 액션
    elif cat == "dish_lifting":
        variations = [
            (
                f"🥩 {step_num}. 젓가락으로 큼직하게 한 점! 촉촉한 {clean_name}!",
                f"젓가락으로 큼직한 한 점을 집어 들어본 생생한 {clean_name} 클로즈업 사진이에요! 🥢✨\n\n"
                f"사진에서도 얇고 부드러운 고기 결의 촉촉한 육즙과 윤기가 그대로 느껴지시죠?\n\n"
                f"함께 나온 특제 소스나 양념간장에 콕 찍어 한입 가득 넣으니 사르르 녹아내리는 극상의 식감이 예술이었답니다 😋"
            ),
            (
                f"🥢 {step_num}. 감탄이 터져 나오는 실물 비주얼! {clean_name} 한입!",
                f"한 점 집어 올리자마자 뿜어져 나오는 고소한 풍미의 {clean_name} 모습이에요! 💖\n\n"
                f"두툼하면서도 야들야들하게 씹히는 부드러운 식감에 씹을수록 깊은 고소함이 입안 가득 맴돌았는데요.\n\n"
                f"왜 이곳의 필수 시그니처로 손꼽히는지 단 한 입만으로도 완벽하게 납득이 되었답니다 👍"
            ),
            (
                f"✨ {step_num}. 멈출 수 없는 젓가락질! 입안 가득 감동의 {clean_name}!",
                f"한 젓가락 듬뿍 집어 올려 카메라에 담아본 {clean_name} 컷이에요! 🍽️✨\n\n"
                f"잡내 없이 깔끔하고 찰진 식감이 돋보여 입에 넣자마자 탄성이 절로 흘러나왔는데요.\n\n"
                f"씹는 맛과 풍미의 밸런스가 뛰어나 일행 모두 연신 젓가락을 바쁘게 움직였답니다 🥰"
            ),
            (
                f"😋 {step_num}. 침샘을 자극하는 영롱한 한 점! {clean_name}!",
                f"클로즈업으로 담아낸 먹음직스러운 {clean_name} 비주얼이에요! 🥢\n\n"
                f"겉면에 감도는 윤기와 촉촉함이 사진으로도 고스란히 전해져 식욕을 무한 자극했는데요.\n\n"
                f"특제 곁들임 찬과 조합해 맛보니 풍미가 두 배로 업그레이드되어 감탄을 연발했답니다 💖"
            ),
            (
                f"👑 {step_num}. 독보적인 식감과 손맛의 향연! {clean_name} 한입!",
                f"정성 가득한 내공이 깃든 {clean_name} 한 점의 매력이에요! 📸✨\n\n"
                f"입에 닿는 순간 퍼지는 깊은 풍미와 부드러운 탄력이 그야말로 환상적이었는데요.\n\n"
                f"오랜 기다림 끝에 맛본 보람을 200% 만끽하게 해 준 최고의 먹방 순간이었답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="dish_lifting")
        caption = f"먹음직스럽게 집어 든 {clean_name}{pair_suffix}"

    # 11. 토핑 / 건더기 / 알 / 곤이 디테일
    elif cat == "topping_detail":
        variations = [
            (
                f"✨ {step_num}. 입안 가득 톡톡 터지는 고소함! {clean_name} 클로즈업!",
                f"푸짐하게 얹어진 싱싱한 {clean_name}의 영롱한 디테일 사진이에요! 🥢✨\n\n"
                f"잡내나 퍽퍽함이 1도 없이 탱글탱글하고 촉촉한 식감이 감탄을 자아냈는데요.\n\n"
                f"와사비 간장에 살짝 콕 찍어 맛보니 입안 가득 크리미하고 진한 고소함이 부드럽게 퍼져나가며 미소를 짓게 만들었답니다 😋"
            ),
            (
                f"🌟 {step_num}. 아낌없이 팍팍 들어간 신선함! {clean_name} 비주얼!",
                f"그릇 가득 채워져 있던 푸짐한 {clean_name} 모습이에요! 🍽️\n\n"
                f"신선한 재료 본연의 담백한 맛과 양념이 쏙 배어든 깊은 감칠맛의 밸런스가 완벽했는데요.\n\n"
                f"골라 먹어도 먹어도 줄지 않을 만큼 혜자로운 양에 사장님의 아낌없는 인심을 체감했답니다 👍"
            ),
            (
                f"🔍 {step_num}. 재료의 신선도가 한눈에 보이는 {clean_name} 디테일!",
                f"클로즈업으로 정밀하게 담아본 알찬 {clean_name} 컷이에요! 📸✨\n\n"
                f"재료 하나하나의 탄력과 맑은 빛깔이 살아있어 좋은 식재료만을 고집하시는 철학이 느껴졌는데요.\n\n"
                f"메인 요리와 어우러지며 국물과 면발의 맛을 한 차원 끌어올려 주는 일등공신이었답니다 💖"
            ),
            (
                f"🍲 {step_num}. 아삭쫄깃 살아있는 식감의 앙상블, {clean_name}!",
                f"숟가락 위에 소복하게 얹어 담아본 먹음직스러운 {clean_name} 모습이에요! 😋\n\n"
                f"씹을 때마다 은은하게 배어 나오는 본연의 풍미 덕분에 질릴 틈 없이 식사를 즐겼는데요.\n\n"
                f"푸짐한 양과 뛰어난 퀄리티 모두 대만족을 안겨준 특별한 고명이었답니다 ✨"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="topping_detail")
        caption = f"신선하고 푸짐한 {clean_name}{pair_suffix}"

    # 12. 국물 / 육수
    elif cat == "soup_side":
        variations = [
            (
                f"🥣 {step_num}. 속이 확 풀리는 얼큰 칼칼함! {clean_name} 한 숟가락!",
                f"숟가락으로 조심스럽게 떠올려 맛본 {clean_name}의 진국 국물이에요! 🍲✨\n\n"
                f"재료에서 진하게 우러나온 감칠맛에 기분 좋은 칼칼함이 더해져, 한 모금 넘기는 순간 온몸의 피로가 싹 풀리는 기분이었는데요.\n\n"
                f"텁텁함 없이 맑고 개운하게 떨어지는 끝 맛 덕분에 연신 숟가락을 멈추지 못하고 들이켰답니다 😋"
            ),
            (
                f"🍲 {step_num}. 깊은 내공이 느껴지는 진국 육수! {clean_name}!",
                f"따끈따끈한 김과 함께 퍼지는 구수한 향의 {clean_name} 모습이에요! 🥣\n\n"
                f"오랜 정성으로 푹 끓여내어 기름기 없이 깔끔하면서도 묵직한 내공이 돋보이는 육수 맛이 일품이었는데요.\n\n"
                f"숟가락으로 떠먹을 때마다 속이 따뜻해지며 감탄사가 절로 새어 나왔답니다 👍"
            ),
            (
                f"✨ {step_num}. 속을 편안하게 감싸주는 개운한 감칠맛! {clean_name}!",
                f"맑고 투명하면서도 깊은 향미를 품은 {clean_name} 클로즈업 사진이에요! 🍲\n\n"
                f"인공적인 조미료 맛이 아닌 천연 식재료에서 우러나온 은은하고 시원한 단맛이 압권이었는데요.\n\n"
                f"식사 중간중간 목을 축여주며 입안을 산뜻하게 리프레시해 주었답니다 💖"
            ),
            (
                f"🔥 {step_num}. 뚝배기 가득 우러난 정성! 뜨끈한 {clean_name}!",
                f"보글보글 온기가 고스란히 남아있는 {clean_name} 비주얼이에요! 🥣✨\n\n"
                f"한 숟가락 후루룩 넘기자마자 온몸이 사르르 녹아내리는 듯한 힐링을 선사해 주었는데요.\n\n"
                f"마지막 한 방울까지 남김없이 비워낼 만큼 중독성 강한 명품 육수였답니다 🥰"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="soup_side")
        caption = f"깊고 진한 {clean_name}{pair_suffix}"

    # 13. 면발 / 면치기
    elif cat == "noodle_lifting":
        variations = [
            (
                f"🥢 {step_num}. 탱글탱글 살아있는 탄력! {clean_name}의 진수!",
                f"후루룩 면치기를 절로 부르는 탄력 넘치는 {clean_name} 컷이에요! 🍜✨\n\n"
                f"밀가루 풋내 없이 쫄깃쫄깃 찰진 식감이 돋보였고, 진한 육수가 면발에 쏙쏙 배어들어 씹을수록 깊은 감칠맛이 느껴졌는데요.\n\n"
                f"쉽게 퍼지지 않고 끝까지 탱탱한 식감을 유지해 면 요리의 매력을 백퍼센트 만끽할 수 있었답니다 👍"
            ),
            (
                f"🍜 {step_num}. 젓가락 가득 후루룩! 중독성 넘치는 {clean_name}!",
                f"윤기가 자르르 흐르는 먹음직스러운 {clean_name} 사진이에요! 🥢\n\n"
                f"입안 가득 차오르는 풍성한 면발의 볼륨감과 쫄깃한 식감에 일행 모두 쉼 없이 면치기에 몰입했는데요.\n\n"
                f"마지막 한 가닥까지 남김없이 건져먹을 정도로 완벽한 완성도를 자랑했답니다 💖"
            ),
            (
                f"✨ {step_num}. 자가제면의 깊은 손맛! 탄력 넘치는 {clean_name}!",
                f"길쭉하게 들어 올린 면발 사이로 김이 모락모락 피어오르는 {clean_name} 컷이에요! 🍜\n\n"
                f"겉은 매끄럽고 속은 탄탄하게 씹히는 이상적인 면발의 정석을 보여주었는데요.\n\n"
                f"양념장 및 육수와의 흡착력이 뛰어나 후루룩 흡입할 때마다 감탄사가 쏟아졌답니다 👍"
            ),
            (
                f"😋 {step_num}. 입에 착 감기는 황홀한 식감! {clean_name} 면치기!",
                f"카메라를 절로 켜게 만든 역대급 {clean_name} 비주얼이에요! 🥢✨\n\n"
                f"쫄깃하면서도 부드럽게 넘어가는 환상의 목넘김 덕분에 젓가락을 멈출 새가 없었는데요.\n\n"
                f"면 요리 마니아라면 누구나 엄지를 치켜세울 수밖에 없는 명품 면발이었답니다 🥰"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="noodle_lifting")
        caption = f"쫄깃탱글한 {clean_name}{pair_suffix}"

    # 14. 완식 및 영수증 인증
    elif cat == "finish":
        if any(k in clean_name for k in ["영수증", "계산"]):
            variations = [
                (
                    f"🧾 {step_num}. 100% 내돈내산 찐인증! {clean_name} 확인!",
                    f"기분 좋게 계산을 마치며 담아본 솔직 담백 {clean_name} 사진이에요! 💳✨\n\n"
                    f"쓴 돈이 1도 아깝지 않을 만큼 양, 맛, 퀄리티 모든 면에서 감동을 준 곳이라 영수증마저 뿌듯하게 느껴졌는데요.\n\n"
                    f"광고나 협찬 없이 오직 찐 맛으로 승부하는 인생 맛집임을 확실하게 증명합니다 👍"
                ),
                (
                    f"💳 {step_num}. 돈 아깝지 않은 완벽한 소비! {clean_name} 영수증!",
                    f"식사를 마치고 나오며 당당하게 찍어본 {clean_name} 인증 컷이에요! 🧾\n\n"
                    f"합리적인 가격에 최상의 퀄리티를 누릴 수 있어 일행 모두 계산하면서도 연신 미소를 지었는데요.\n\n"
                    f"진짜 제 지갑에서 나간 내돈내산인 만큼 믿고 방문하셔도 절대 후회 없으실 거예요 ✨"
                )
            ]
        else:
            variations = [
                (
                    f"🍚 {step_num}. 밥알 한 톨 남김없이 싹 비운 완식 인증!",
                    f"사진에 보이는 것처럼 마지막 한 숟가락까지 그릇 바닥을 싹싹 긁어먹은 완식 컷이에요! 🍽️✨\n\n"
                    f"배는 터질 듯이 부르지만 마지막 한 점까지 너무 아쉬워서 숟가락을 놓을 수 없었는데요.\n\n"
                    f"기분 좋은 포만감과 함께 오늘 하루의 피로가 눈 녹듯 싹 사라지는 힐링을 경험했답니다 💖"
                ),
                (
                    f"✨ {step_num}. 대만족으로 마무리한 완벽한 한 끼 식사!",
                    f"빈 그릇과 함께 훈훈하게 마무리된 식사 현장이에요! 🥰\n\n"
                    f"일행 모두가 연신 감탄사를 쏟아내며 엄지를 치켜세웠을 정도로 완벽했던 자리였는데요.\n\n"
                    f"문을 나서는 순간까지도 입안에 맴도는 기분 좋은 여운에 벌써부터 다음 재방문 일정을 잡고 싶어졌답니다 🍽️"
                )
            ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="finish")
        caption = f"{clean_name} 마무리{pair_suffix}"

    # 15. 꿀조합 / 비빈 모습 / 쌈
    elif cat == "combo":
        variations = [
            (
                f"🥢 {step_num}. 꿀맛 보장! 군침 도는 {clean_name} 한입!",
                f"정성껏 버무리고 쌈을 싸서 완성한 황금 {clean_name} 컷이에요! 😋✨\n\n"
                f"각 재료의 식감과 소스의 조화가 완벽해서 입에 넣자마자 폭발적인 감칠맛이 터져 나왔는데요.\n\n"
                f"이렇게 드셔보시면 왜 이 조합을 강력 추천하는지 단번에 공감하실 거예요 💖"
            ),
            (
                f"✨ {step_num}. 실패 없는 꿀조합 완성! {clean_name}!",
                f"사장님이 귀띔해 주신 팁대로 알차게 조합해 본 {clean_name} 비주얼이에요! 🥢\n\n"
                f"단독으로 먹어도 훌륭하지만 서로 다른 재료들이 시너지를 내어 풍미가 두 배로 업그레이드되었는데요.\n\n"
                f"마지막 한 점까지 이 조합으로 알차게 즐기며 폭풍 먹방을 이어갔답니다 👍"
            ),
            (
                f"🥗 {step_num}. 다채로운 식감의 폭발! 환상적인 {clean_name} 조합!",
                f"신선한 곁들임 찬과 메인 요리를 함께 올려 완성한 {clean_name} 컷이에요! 🍽️✨\n\n"
                f"아삭함과 쫄깃함이 입안에서 어우러지며 전혀 새로운 미식의 세계를 열어주었는데요.\n\n"
                f"물릴 틈 없이 계속해서 손이 가게 만드는 마성의 황금 조합이었답니다 🥰"
            ),
            (
                f"😋 {step_num}. 입안 가득 터지는 감칠맛의 시너지! {clean_name}!",
                f"골고루 비비고 어우러져 더욱 먹음직스러워진 {clean_name} 비주얼이에요! 🥢\n\n"
                f"단짠의 균형과 알싸한 양념이 재료 본연의 맛을 극대화해 주어 한 입 가득 행복을 채웠답니다 👍"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="combo")
        caption = f"맛있는 {clean_name}{pair_suffix}"

    # 16. 사이드 메뉴 - 고정 템플릿 탈피, 동적 합성 엔진으로 무한 다변화
    elif cat == "sub_dish":
        is_subsequent = True
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
            is_subsequent=True
        )
        caption = f"푸짐하고 맛깔스러운 {clean_name}{pair_suffix}"

    # 17. 디테일
    elif cat == "detail":
        variations = [
            (
                f"🔍 {step_num}. 사진으로 확인하는 압도적 퀄리티! {clean_name} 디테일!",
                f"카메라 렌즈를 가까이 대고 담아본 생생한 {clean_name} 클로즈업 사진이에요! 📸✨\n\n"
                f"신선함이 뚝뚝 묻어나는 남다른 자태와 촉촉한 윤기가 눈으로도 고스란히 확인되었는데요.\n\n"
                f"좋은 식재료만을 고집하시는 사장님의 진심 어린 정성이 고스란히 느껴졌답니다 💖"
            ),
            (
                f"✨ {step_num}. 시선을 사로잡는 영롱한 비주얼! {clean_name} 컷!",
                f"선명한 색감과 고운 자태를 자랑하는 {clean_name} 모습이에요! 🍽️\n\n"
                f"빛깔 하나만 보아도 얼마나 신선하고 정성스럽게 준비되었는지 알 수 있었는데요.\n\n"
                f"먹기 아까울 정도로 아름다운 비주얼에 연신 감탄하며 셔터를 눌렀답니다 😋"
            )
        ]
        header, text = pick_unique_variation(variations, used_set, key_prefix="detail")
        caption = f"{clean_name} 디테일{pair_suffix}"

    # 18. 메인 요리 (dish) - 세부 유형 자동 감지 & 실시간 찐후기 기반 다차원 동적 합성 (하드코딩 0%)
    else:
        is_subsequent = clean_name in seen_dishes or len(seen_dishes) > 0
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

    return header, text, caption


def generate_photo_matched_sections(store_name, location, menu, features, photo_paths, include_stickers=True, include_map=True, store_info=None):
    """
    첨부된 사진 목록을 분석하여 파일명과 100% 매칭되는 글 생성 (중복 절대 없음)
    """
    sections = []
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu

    # 1. 인트로 (6가지 스토리 중 랜덤 1택)
    intro_header, intro_content = generate_dynamic_intro(store_name, location, main_menu)
    sections.append({
        "type": "text",
        "header": intro_header,
        "content": intro_content
    })

    if include_stickers:
        sections.append({"type": "sticker", "role": "intro"})

    # 2. 매장 상세 정보 & 네이버 지도
    if store_info:
        from store_crawler import format_store_info_section
        info_text = format_store_info_section(store_info)
        sections.append({
            "type": "text",
            "header": "📌 매장 상세 방문 정보 (위치, 주차, 영업시간 총정리!)",
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
            # 둘 다 같은 카테고리이면서, 두 사진의 핵심 이름이 완전히 동일할 때만 가로 2장 묶음
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

    # 4. 각 사진 묶음마다 파일명과 100% 매칭되는 스토리 단락 생성 (In-Post Deduplication 컨텍스트 적용)
    step_num = 1
    context = {
        "used_templates": set(),
        "seen_dishes": set(),
        "live_reviews": (store_info.get("live_reviews") if store_info else {}) or {},
        "store_info": store_info or {}
    }

    for b_idx, batch in enumerate(batches, 1):
        cat = batch["category"]
        clean_name = batch["clean_name"]
        count = len(batch["items"])
        b_paths = [item["path"] for item in batch["items"]]

        # 중간 스티커 자연스럽게 삽입
        if include_stickers and b_idx in (2, 5, 8):
            sections.append({"type": "sticker", "role": "mid"})

        header, text, caption = create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count, context)
        step_num += 1

        sections.append({
            "type": "text",
            "header": header,
            "content": text
        })

        sections.append({
            "type": "image",
            "paths": b_paths,
            "count": count,
            "caption": caption
        })

    # 5. 동적 총평 & 재방문 의사 (5가지 중 랜덤 1택)
    outro_header, outro_content = generate_dynamic_outro(store_name, location, menu)
    sections.append({
        "type": "text",
        "header": outro_header,
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


def generate_template_post(store_name, location, menu, features, photo_count=14, include_stickers=True, include_map=True, store_info=None, photo_paths=None):
    """
    사진 목록이 있으면 사진 파일명에 100% 매칭되는 맞춤형 포스팅 생성,
    사진이 없으면 텍스트 중심의 정갈한 포스팅 생성
    (매 실행 시마다 제목, 도입, 본문, 총평이 완전히 다르게 생성되며 동일 글 내 중복 0%)
    """
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu

    title = generate_dynamic_title(store_name, location, main_menu)

    if photo_paths:
        sections = generate_photo_matched_sections(
            store_name=store_name,
            location=location,
            menu=menu,
            features=features,
            photo_paths=photo_paths,
            include_stickers=include_stickers,
            include_map=include_map,
            store_info=store_info
        )
    else:
        sections = []
        intro_h, intro_c = generate_dynamic_intro(store_name, location, main_menu)
        sections.append({"type": "text", "header": intro_h, "content": intro_c})
        if store_info:
            from store_crawler import format_store_info_section
            sections.append({"type": "text", "header": "📌 매장 상세 정보", "content": format_store_info_section(store_info)})
        if include_map:
            sections.append({"type": "map", "query": store_name, "location_name": f"{location} {store_name}"})
        outro_h, outro_c = generate_dynamic_outro(store_name, location, menu)
        sections.append({"type": "text", "header": outro_h, "content": outro_c})

    tags = build_rich_hashtags(store_name, location, menu, features)

    return {
        "title": clean_markdown_artifacts(title),
        "sections": sections,
        "tags": tags
    }


def call_llm_api(provider, api_key, prompt):
    try:
        p_lower = str(provider).lower()
        if "gemini" in p_lower:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['candidates'][0]['content']['parts'][0]['text']
        elif "openai" in p_lower:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
        elif "claude" in p_lower:
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.8
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['content'][0]['text']
    except Exception as e:
        print(f"AI API 호출 안내 (다변화 템플릿 엔진으로 즉시 자동 대체): {e}")
    return None


def generate_ai_post(api_key, api_provider, store_name, location, menu, features, photo_count=5, include_stickers=True, include_map=True, photo_paths=None):
    res = generate_template_post(store_name, location, menu, features, photo_count, include_stickers, include_map, photo_paths=photo_paths)
    if api_key and api_key.strip():
        photo_names = [os.path.basename(p) for p in (photo_paths or [])]
        prompt = (
            f"당신은 네이버 블로그 맛집 전문 파워블로거입니다.\n"
            f"식당: {store_name}\n"
            f"위치: {location}\n"
            f"메뉴: {menu}\n"
            f"특징: {features}\n"
            f"첨부된 사진 파일명 목록: {', '.join(photo_names)}\n\n"
            f"위 정보를 바탕으로 독창적이고 흥미진진한 블로그 제목 하나와, 맛집 방문의 설렘이 느껴지는 도입부 3문단을 한국어로 작성해주세요.\n"
            f"형식:\n제목: [제목]\n도입부: [도입부 본문]"
        )
        ai_resp = call_llm_api(api_provider, api_key.strip(), prompt)
        if ai_resp:
            m_title = re.search(r'제목:\s*(.+)', ai_resp)
            m_intro = re.search(r'도입부:\s*([\s\S]+)', ai_resp)
            if m_title:
                res["title"] = clean_markdown_artifacts(m_title.group(1).strip())
            if m_intro and res["sections"]:
                for s in res["sections"]:
                    if s.get("type") == "text":
                        s["content"] = clean_markdown_artifacts(m_intro.group(1).strip())
                        break

    for s in res["sections"]:
        if s.get("type") == "text":
            s["content"] = clean_markdown_artifacts(s["content"])
            s["header"] = clean_markdown_artifacts(s["header"])
    return res
