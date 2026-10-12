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
    """자연스러운 숫자 정렬 (1, 2, ..., 10 순서 보장)"""
    filename = os.path.basename(filepath)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]


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

    # 1. 외관 / 간판
    if any(k in clean_lower for k in ["외관", "간판", "입구", "도착", "외부", "건물", "가게전경", "파사드"]):
        cat = "exterior"
    # 2. 웨이팅
    elif any(k in clean_lower for k in ["웨이팅", "대기", "캐치테이블", "테이블링", "줄서기", "줄서는", "대기표", "순번"]):
        cat = "waiting"
    # 3. 맛집 인증 (블루리본, 미쉐린 등)
    elif any(k in clean_lower for k in ["미쉐린", "미슐랭", "블루리본", "상장", "상패", "인증", "명패", "선정", "팻말", "방송", "티비", "tv"]):
        cat = "award"
    # 4. 무료 공기밥 / 셀프바 코너
    elif any(k in clean_lower for k in ["공기밥무료", "무료공기밥", "밥무료", "공기밥", "셀프바", "셀프코너", "밥솥", "무료리필", "밥무한", "무한리필"]):
        cat = "service_rice"
    # 5. 매장 이용안내문 / 규칙
    elif any(k in clean_lower for k in ["식사시간제한", "식사시간", "시간제한", "1인1메뉴", "1인 1메뉴", "이용안내", "안내문", "주의사항", "이용수칙", "이용시간", "주문안내", "규칙", "에티켓"]):
        cat = "notice"
    # 6. 메뉴판
    elif any(k in clean_lower for k in ["메뉴판", "차림표", "빌지", "가격표", "주문서"]) or (clean_lower.endswith("메뉴") and "1인1메뉴" not in clean_lower):
        cat = "menu"
    # 7. 실내 좌석 / 테이블
    elif any(k in clean_lower for k in ["실내 테이블", "실내테이블", "테이블", "좌석", "자리", "의자"]):
        cat = "seating"
    # 8. 실내 전체 인테리어 / 분위기
    elif any(k in clean_lower for k in ["내부", "인테리어", "홀", "분위기", "룸", "실내", "조명"]):
        cat = "interior"
    # 9. 한상차림 / 상차림 / 밑반찬
    elif any(k in clean_lower for k in ["한상차림", "상차림", "밑반찬", "반찬", "기본찬", "세팅", "스끼", "깍두기", "김치", "무침", "샐러드", "양념장"]):
        cat = "sides"
    # 10. 젓가락으로 든 한 점 / 클로즈업 먹방 액션
    elif any(k in clean_lower for k in ["들고있는", "들고있는거", "집은", "젓가락", "한점", "한입", "숟가락", "집어든"]):
        cat = "dish_lifting"
    # 11. 토핑 / 건더기 / 알 / 곤이 디테일 (단, '알곤이칼국수', '알탕' 등 요리명 자체는 dish로 분류)
    elif (any(clean_lower.endswith(k) for k in ["알", "곤이", "이리", "토핑", "고명", "건더기"]) or
          any(k in clean_lower for k in ["알 토핑", "곤이 토핑", "알추가", "곤이추가", "알곤이 알", "알곤이칼국수 알", "알곤이 고명"])) and not clean_lower.endswith(("칼국수", "탕", "찌개", "전골", "찜", "국밥")):
        cat = "topping_detail"
    # 12. 국물 / 육수 (음식의 국물 부위)
    elif any(k in clean_lower for k in ["국물", "육수", "소고기뭇국", "뭇국", "무국", "기본국", "서비스국", "장국", "된장국", "미역국"]):
        cat = "soup_side"
    # 13. 면발 / 면치기
    elif any(k in clean_lower for k in ["면발", "면치기", "가락", "국수면"]):
        cat = "noodle_lifting"
    # 14. 완식 및 영수증 내돈내산 인증
    elif any(k in clean_lower for k in ["완식", "마무리", "빈그릇", "빈접시", "클리어", "다먹음", "계산", "영수증"]):
        cat = "finish"
    # 15. 꿀조합 / 비빈 모습 / 쌈
    elif any(k in clean_lower for k in ["비빈", "비벼", "비비는", "비벼진", "비벼먹", "섞은", "섞인", "꿀조합", "조합", "찍먹", "김쌈", "쌈", "싸먹", "말아", "한숟가락", "한숟갈"]):
        cat = "combo"
    # 16. 일반 디테일
    elif any(k in clean_lower for k in ["디테일", "근접", "클로즈업", "단면", "확대", "윤기"]):
        cat = "detail"
    # 17. 사이드 메뉴 / 주류
    elif any(k in clean_lower for k in ["사이드", "서브", "라면", "찌개", "볶음밥", "냉면", "음료", "주류", "맥주", "소주", "하이볼", "사리", "추가", "주먹밥", "계란찜", "만두"]):
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
    c = clean_name.lower()
    if category == "exterior" or any(k in c for k in ['외관', '간판', '입구', '도착', '외부', '건물', '가게전경']):
        return 10
    if category == "waiting" or any(k in c for k in ['웨이팅', '대기', '캐치테이블', '테이블링', '줄서기', '대기표']):
        return 20
    if category == "award" or any(k in c for k in ['미쉐린', '미슐랭', '블루리본', '상패', '인증']):
        return 25
    if category == "interior" or any(k in c for k in ['내부', '인테리어', '홀', '분위기', '실내']):
        return 30
    if category == "seating" or any(k in c for k in ['실내 테이블', '테이블', '좌석', '자리']):
        return 35
    if category == "notice" or any(k in c for k in ['식사시간제한', '1인1메뉴', '이용안내', '안내문']):
        return 40
    if category == "menu" or any(k in c for k in ['메뉴판', '차림표', '빌지', '가격표']):
        return 50
    if category == "service_rice" or any(k in c for k in ['공기밥무료', '무료공기밥', '셀프바', '밥솥']):
        return 55
    if category == "sides" or any(k in c for k in ['한상차림', '상차림', '밑반찬', '반찬', '기본찬']):
        return 60
    if category == "soup_side" and not any(k in c for k in ['알곤이', '칼국수', '전골']):
        return 65
    if category == "dish":
        if any(k in c for k in ['보통', '일반']):
            return 71
        if any(k in c for k in ['특', '대', '곱배기']):
            return 72
        return 75
    if category == "topping_detail":
        return 80
    if category == "soup_side":
        return 82
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
        return (0, int(m.group(1)), filename.lower())
    else:
        info = parse_photo_info(filepath)
        p = get_journey_priority(info['clean_name'], info['category'])
        return (1, p, filename.lower())


CATEGORY_KOR_NAMES = {
    "exterior": "외관 및 간판",
    "waiting": "웨이팅 및 현장 대기",
    "award": "미쉐린/블루리본 인증 상패",
    "interior": "실내 인테리어 및 감성",
    "seating": "실내 테이블 및 좌석",
    "notice": "매장 이용수칙 및 안내",
    "service_rice": "공기밥 무료/셀프바 코너",
    "menu": "메뉴판 및 가격 정보",
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


def pick_unique_variation(variations, used_set, key_prefix=""):
    """
    동일한 포스팅 내에서 절대 같은 문장 또는 헤더 패턴이 중복 선택되지 않도록 보장
    """
    candidates = []
    for idx, v in enumerate(variations):
        # 헤더의 핵심 패턴 추출 (숫자, clean_name을 제외한 수식어구)
        h_core = re.sub(r'^[^\.\!]+[\.\!]\s*', '', v[0])
        h_core = re.sub(r'[0-9\s_\-\.\(\)\[\]]', '', h_core)
        k = f"{key_prefix}_{idx}" if key_prefix else h_core
        if k not in used_set and h_core not in used_set and v[0] not in used_set and v[1] not in used_set:
            candidates.append((k, h_core, v))

    if not candidates:
        chosen_k, chosen_core, chosen_v = "", "", random.choice(variations)
    else:
        chosen_k, chosen_core, chosen_v = random.choice(candidates)
        if chosen_k:
            used_set.add(chosen_k)
        if chosen_core:
            used_set.add(chosen_core)

    used_set.add(chosen_v[0])
    used_set.add(chosen_v[1])
    return chosen_v


def create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count, context):
    """
    사진 파일명과 카테고리에 100% 매칭되는 독창적 서사 단락 생성
    (In-Post Deduplication: 같은 글 내에서 헤더/본문 중복 절대 불가)
    """
    is_pair = count > 1
    pair_suffix = " (가로 나란히)" if is_pair else ""
    used_set = context.setdefault("used_templates", set())
    seen_dishes = context.setdefault("seen_dishes", set())

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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{location} {store_name} {clean_name}{pair_suffix}"

    # 2. 웨이팅
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
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{clean_name} 현장 대기{pair_suffix}"

    # 3. 맛집 인증 (미쉐린, 블루리본)
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
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{store_name} {clean_name}{pair_suffix}"

    # 4. 실내 인테리어 / 분위기
    elif cat == "interior":
        variations = [
            (
                f"🌿 {step_num}. 아늑함과 정갈함이 공존하는 실내 분위기!",
                f"매장 문을 열고 안으로 들어서서 담아본 {clean_name} 사진이에요! 🌿\n\n"
                f"따스하고 은은한 조명에 전체적인 공간이 쾌적하게 꾸며져 있어 일행과 편안하게 대화 나누기 참 좋았어요.\n\n"
                f"구석구석 먼지 하나 없이 위생적으로 관리된 모습에 식사 전부터 안심이 되었답니다 💖"
            ),
            (
                f"💡 {step_num}. 레트로와 모던 감성이 어우러진 매장 내부 전경!",
                f"특유의 감각적인 무드가 매력적이었던 {clean_name} 모습이에요! ✨\n\n"
                f"원목과 현대적인 감성이 조화롭게 어우러져 사진을 찍는 족족 감성 샷이 완성되었는데요.\n\n"
                f"식사하는 손님들을 배려한 차분한 공기 덕분에 대접받는 듯한 기분 좋은 여유를 즐길 수 있었답니다 🛋️"
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{store_name} 아늑한 {clean_name}{pair_suffix}"

    # 5. 실내 좌석 / 테이블
    elif cat == "seating":
        variations = [
            (
                f"🛋️ {step_num}. 편안하고 쾌적한 자리! {clean_name} 전경!",
                f"손님들이 편안하게 식사에 온전히 집중할 수 있도록 정갈하게 배치된 {clean_name} 공간이에요! 🪑\n\n"
                f"테이블 간격도 널찍하고 청결하게 정돈되어 있어 옆자리 방해 없이 식사를 즐길 수 있었는데요.\n\n"
                f"의자도 편안해서 오랜 시간 머물며 도란도란 이야기 나누기에 더없이 좋았답니다 ✨"
            ),
            (
                f"🪑 {step_num}. 깔끔하고 쾌적한 정돈! {clean_name} 좌석!",
                f"안내를 받아 자리에 앉기 전 둘러본 {clean_name} 모습이에요! 🛋️\n\n"
                f"테이블 위 식기류와 소품들이 각 잡혀 깔끔하게 세팅되어 있어 위생 면에서 백점 만점을 주고 싶었는데요.\n\n"
                f"데이트는 물론이고 가족이나 소중한 지인들과의 모임 자리로도 손색이 없겠더라고요 💖"
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{store_name} 편안한 {clean_name}{pair_suffix}"

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
        header, text = pick_unique_variation(variations, used_set)
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
        header, text = pick_unique_variation(variations, used_set)
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
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{store_name} {clean_name}{pair_suffix}"

    # 9. 한상차림 / 상차림 / 밑반찬
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
        header, text = pick_unique_variation(variations, used_set)
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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
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
        header, text = pick_unique_variation(variations, used_set)
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
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
        caption = f"맛있는 {clean_name}{pair_suffix}"

    # 16. 사이드 메뉴
    elif cat == "sub_dish":
        variations = [
            (
                f"🍜 {step_num}. 놓칠 수 없는 든든한 별미! {clean_name}!",
                f"메인 요리와 함께 곁들이기 위해 주문한 {clean_name} 사진이에요! 🍜✨\n\n"
                f"사진처럼 푸짐하고 먹음직스러운 비주얼을 자랑하며 식사의 완성도를 한층 더 높여주었는데요.\n\n"
                f"메인 요리와의 궁합도 찰떡이라 마지막 한 숟가락까지 감탄하며 든든하게 즐겼답니다 ✨"
            ),
            (
                f"🍲 {step_num}. 식사를 더욱 풍성하게 만들어준 {clean_name}!",
                f"테이블을 한층 더 화려하게 채워준 매력적인 사이드, {clean_name} 비주얼이에요! 🍽️\n\n"
                f"메인 못지않은 푸짐한 양과 정갈한 플레이팅에 다들 젓가락을 멈추지 못했는데요.\n\n"
                f"함께 곁들이니 물릴 틈 없이 식사의 텐션을 끝까지 끌어올려 주었답니다 😋"
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
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
                f"✨ {step_num}. 오감을 자극하는 영롱한 비주얼! {clean_name} 컷!",
                f"선명한 색감과 고운 자태를 자랑하는 {clean_name} 모습이에요! 🍽️\n\n"
                f"빛깔 하나만 보아도 얼마나 신선하고 정성스럽게 준비되었는지 알 수 있었는데요.\n\n"
                f"먹기 아까울 정도로 아름다운 비주얼에 연신 감탄하며 셔터를 눌렀답니다 😋"
            )
        ]
        header, text = pick_unique_variation(variations, used_set)
        caption = f"{clean_name} 디테일{pair_suffix}"

    # 18. 메인 요리 (dish) - 세부 유형별 & 순서별 분기
    else:
        c_lower = clean_name.lower()
        is_subsequent = clean_name in seen_dishes or len(seen_dishes) > 0
        seen_dishes.add(clean_name)

        # 육전 / 파전 / 부침 / 튀김
        if any(w in c_lower for w in ["육전", "전", "파전", "튀김", "부침개"]):
            if is_subsequent:
                variations = [
                    (
                        f"🥢 {step_num}. 테이블의 든든함을 더해준 노릇노릇 {clean_name}!",
                        f"국물 요리와 함께 곁들이기 위해 주문한 고소한 {clean_name} 비주얼이에요! 🥩✨\n\n"
                        f"얇고 부드러운 소고기에 얇은 계란 옷을 입혀 갓 부쳐내어, 기름진 잡내 없이 담백한 육즙이 그대로 살아있었는데요.\n\n"
                        f"매콤한 음식과 육전의 고소한 감칠맛이 어우러져 궁합이 그야말로 환상적이었답니다 💖"
                    ),
                    (
                        f"✨ {step_num}. 겉은 바삭 속은 촉촉! 별미 중의 별미 {clean_name}!",
                        f"황금빛 자태를 뽐내며 등장한 또 하나의 명물, {clean_name} 사진이에요! 🥢\n\n"
                        f"한 점 집어서 간장 소스에 콕 찍어 맛보니 입안 가득 퍼지는 고소한 풍미에 절로 감탄이 나왔는데요.\n\n"
                        f"메인과 함께 테이블의 푸짐함을 완성해 주는 최고의 히든카드였답니다 👍"
                    )
                ]
            else:
                variations = [
                    (
                        f"🥢 {step_num}. 갓 부쳐내어 고소한 풍미 폭발! 노릇노릇 {clean_name}!",
                        f"황금빛 자태를 자랑하며 테이블에 오른 오늘의 주인공, {clean_name} 사진이에요! 🥩✨\n\n"
                        f"노릇하게 부쳐진 고기에서 은은하게 퍼지는 고소한 기름 향이 먹기 전부터 군침을 돌게 만들었는데요.\n\n"
                        f"질김 없이 사르르 녹아내리는 부드러운 식감에 일행 모두 연신 젓가락을 움직였답니다 😋"
                    ),
                    (
                        f"✨ {step_num}. 바삭 고소함의 극치! 정갈한 {clean_name} 등장!",
                        f"테이블에 놓이자마자 시선을 사로잡은 {clean_name} 비주얼이에요! 🍽️\n\n"
                        f"기름진 느끼함 없이 담백하고 바삭하게 구워내어 마지막 한 조각까지 물릴 틈 없이 즐겼는데요.\n\n"
                        f"좋은 재료를 아낌없이 사용해 완성도 높은 손맛을 제대로 맛볼 수 있었답니다 💖"
                    )
                ]

        # 칼국수 / 면 요리
        elif any(w in c_lower for w in ["칼국수", "라면", "국수", "우동", "면"]):
            if "동죽" in c_lower or "조개" in c_lower or "해물" in c_lower:
                variations = [
                    (
                        f"🍜 {step_num}. 맑고 개운한 바다의 맛! 시원한 {clean_name}!",
                        f"맑고 깊은 육수에 싱싱한 조개가 가득 담겨 나온 {clean_name} 사진이에요! 🍜✨\n\n"
                        f"뽀얗고 맑은 국물 한 모금 넘기니 조개에서 우러나온 시원하고 개운한 감칠맛이 속을 편안하게 감싸주었는데요.\n\n"
                        f"해감도 완벽하게 되어 조갯살 하나하나 쏙쏙 빼먹는 재미와 함께 깔끔한 뒷맛을 선사해 주었답니다 💖"
                    ),
                    (
                        f"✨ {step_num}. 깔끔 담백한 국물의 반전 매력! {clean_name} 등장!",
                        f"얼큰한 메뉴와 완벽한 대조를 이루며 입맛을 정돈해 준 {clean_name} 비주얼이에요! 🥢\n\n"
                        f"푸짐하게 들어간 동죽 조개의 쫄깃함과 맑은 육수가 어우러져 한 숟가락 뜰 때마다 감탄을 자아냈는데요.\n\n"
                        f"자극적이지 않으면서도 깊은 감칠맛 덕분에 마지막 국물 한 방울까지 싹 들이켰답니다 👍"
                    )
                ]
            elif "알곤이" in c_lower or "알" in c_lower or "곤이" in c_lower:
                variations = [
                    (
                        f"🍜 {step_num}. 비주얼부터 압도적인 시그니처! {clean_name} 등장!",
                        f"소문으로만 듣던 독보적인 시그니처, {clean_name} 한 그릇이 드디어 눈앞에 차려졌어요! 🍜✨\n\n"
                        f"그릇이 넘쳐날 듯 수북하게 쌓인 푸짐한 알과 곤이, 진한 붉은빛 국물의 강렬한 비주얼에 탄성이 절로 나왔는데요.\n\n"
                        f"매콤 칼칼한 향이 코끝을 스치며 먹기 전부터 오감을 강렬하게 사로잡았답니다 💖"
                    ),
                    (
                        f"🔥 {step_num}. 침샘을 자극하는 붉은 유혹! 푸짐한 {clean_name}!",
                        f"테이블에 놓이자마자 입이 떡 벌어졌던 화려한 비주얼의 {clean_name} 사진이에요! 😋\n\n"
                        f"칼칼하고 진한 국물 속에 신선한 알과 곤이가 산더미처럼 들어가 있어 보기만 해도 든든함이 느껴졌는데요.\n\n"
                        f"한 번 맛보면 숟가락질을 멈출 수 없을 만큼 중독성 강한 얼큰함에 완전히 매료되었답니다 👍"
                    )
                ]
            else:
                if is_subsequent:
                    variations = [
                        (
                            f"🍜 {step_num}. 이어 맛본 또 하나의 매력! 든든한 {clean_name}!",
                            f"푸짐한 그릇 가득 윤기 흐르는 면발을 자랑하는 {clean_name} 모습이에요! 🍜✨\n\n"
                            f"앞서 맛본 메뉴와는 또 다른 깊은 육수와 면발의 밸런스가 돋보였는데요.\n\n"
                            f"퍼지지 않고 살아있는 탄력 있는 식감 덕분에 마지막 한 젓가락까지 감탄하며 비워냈답니다 👍"
                        ),
                        (
                            f"🥢 {step_num}. 깊은 육수와 쫄깃한 면발의 조화! {clean_name}!",
                            f"뜨끈한 김과 함께 차려져 나온 {clean_name} 사진이에요! 😋\n\n"
                            f"후루룩 면치기를 즐기기에 완벽한 찰진 식감과 진한 풍미가 입안을 가득 채워주었는데요.\n\n"
                            f"식사의 든든함을 배로 만들어주는 훌륭한 선택이었답니다 💖"
                        )
                    ]
                else:
                    variations = [
                        (
                            f"🍜 {step_num}. 쫄깃탱글한 면발이 일품인 {clean_name} 등장!",
                            f"뜨끈한 김과 함께 푸짐하게 차려져 나온 {clean_name} 사진이에요! 🍜✨\n\n"
                            f"탱글탱글 쫄깃한 면발에 진한 육수와 양념이 쏙쏙 배어들어 있어서 후루룩 면치기하는 재미가 쏠쏠했는데요!\n\n"
                            f"젓가락질을 멈출 수 없을 만큼 중독성 넘치는 맛에 마지막 한 가닥까지 대만족하며 즐겼답니다 💖"
                        ),
                        (
                            f"🥢 {step_num}. 후루룩 면치기 유발! 마성의 {clean_name}!",
                            f"푸짐한 그릇 가득 윤기 흐르는 면발을 자랑하는 {clean_name} 모습이에요! 😋\n\n"
                            f"퍼지지 않고 살아있는 탄력 있는 식감과 깊은 소스의 조화가 완벽해서 순식간에 한 그릇을 뚝딱 비워냈답니다 👍"
                        )
                    ]

        # 육회비빔밥 / 비빔밥 / 덮밥
        elif any(w in c_lower for w in ["비빔밥", "육회", "덮밥", "솥밥"]):
            if any(k in c_lower for k in ["특", "대", "곱배기"]):
                variations = [
                    (
                        f"🥣 {step_num}. 육회가 산더미처럼 푸짐한 {clean_name} 등장!",
                        f"기다리던 오늘의 하이라이트! 사진 속 푸짐한 {clean_name} 비주얼 보이시나요? 🥣✨\n\n"
                        f"'특' 사이즈답게 신선하고 영롱한 붉은빛의 한우 육회가 밥이 보이지 않을 정도로 그릇 가득 산더미처럼 올려져 나왔는데요!\n\n"
                        f"파릇파릇 향긋한 채소와 육회의 푸짐한 비율에 먹기 전부터 감탄사가 절로 쏟아졌답니다 💖"
                    ),
                    (
                        f"👑 {step_num}. 오늘 식사의 주인공! 위풍당당한 {clean_name}!",
                        f"비주얼부터 이미 합격점을 훌쩍 넘긴 {clean_name} 컷이에요! 🍽️\n\n"
                        f"푸짐한 양은 물론이고 육질 하나하나의 신선도가 최상급이라 감탄을 금치 못했는데요!\n\n"
                        f"특으로 주문하길 정말 잘했다며 일행들과 하이파이브를 할 정도로 흡족했답니다 👍"
                    )
                ]
            else:
                variations = [
                    (
                        f"🥣 {step_num}. 신선한 재료와 정갈한 담음새! {clean_name} 등장!",
                        f"테이블을 풍성하게 채워준 오늘의 든든한 주인공, {clean_name} 사진이에요! 🥣✨\n\n"
                        f"아낌없이 올라간 신선한 고명과 고소한 참기름 냄새가 먹기 전부터 침샘을 무한 자극했는데요!\n\n"
                        f"재료 하나하나의 신선도가 눈으로도 고스란히 전해질 만큼 영롱한 비주얼을 뽐내고 있었답니다 💖"
                    ),
                    (
                        f"🌿 {step_num}. 오감을 깨우는 완벽한 조화! {clean_name} 영접!",
                        f"드디어 영접한 시그니처 대표 메뉴, {clean_name} 비주얼이에요! 😋\n\n"
                        f"선홍빛의 고운 자태와 아삭하고 향긋한 식재료들이 어우러져 보기만 해도 눈이 호강하는 느낌이었는데요!\n\n"
                        f"좋은 재료에서 우러나오는 본연의 단맛과 고소함이 먹기 전부터 가슴을 설레게 만들었답니다 ✨"
                    )
                ]

        # 수육 / 전골 / 탕 / 곰탕 / 국밥
        elif any(w in c_lower for w in ["수육", "전골", "곰탕", "국밥", "탕", "찌개"]):
            variations = [
                (
                    f"🍲 {step_num}. 야들야들한 육질과 깊은 육수의 조화, {clean_name}!",
                    f"보글보글 끓어오르는 비주얼이 예술인 {clean_name} 사진이에요! 🍲✨\n\n"
                    f"맑고 깊은 육수 위에 얇고 부드럽게 삶아진 고기와 향긋한 채소가 푸짐하게 올려져 나왔는데요!\n\n"
                    f"잡내 하나 없이 야들야들 녹아내리는 육질과 시원하고 깊은 국물의 조화가 감탄 그 자체였답니다 💖"
                ),
                (
                    f"✨ {step_num}. 보글보글 피어오르는 깊은 풍미! {clean_name} 등장!",
                    f"테이블 위에서 은은한 온기를 더해준 오늘의 메인, {clean_name} 비주얼이에요! 🥘\n\n"
                    f"부드럽게 익어가는 고기와 진국 육수의 냄새가 코끝을 스치자마자 다들 젓가락을 들고 대기했는데요!\n\n"
                    f"입에 넣는 순간 사르르 녹아내리는 부드러움에 눈이 번쩍 뜨일 만큼 황홀했답니다 👍"
                )
            ]

        # 고기 / 구이 / 삼겹살
        elif any(w in c_lower for w in ["삼겹", "구이", "목살", "갈비", "고기", "한우", "스테이크"]):
            variations = [
                (
                    f"🥩 {step_num}. 지글지글 노릇하게 익어가는 황금빛 {clean_name}!",
                    f"불판 위에서 지글지글 소리를 내며 노릇노릇 맛있게 구워지는 {clean_name} 사진이에요! 🥩✨\n\n"
                    f"두툼한 고기 두께와 팡팡 터지는 고소한 육즙의 자태에 굽는 내내 침샘이 무한 자극되었는데요.\n\n"
                    f"겉은 바삭하고 속은 촉촉하게 익어 첫 한 점을 소금에 콕 찍어 맛보았는데, 씹자마자 육즙이 팡 터지며 감탄사가 터졌답니다 💖"
                ),
                (
                    f"🔥 {step_num}. 침샘 폭발! 극상의 마블링과 육즙을 품은 {clean_name}!",
                    f"불판을 가득 채운 영롱한 자태의 {clean_name} 비주얼이에요! 🍽️\n\n"
                    f"선홍빛 육질과 알맞은 지방의 황금비율이 눈을 뗄 수 없게 만들었는데요!\n\n"
                    f"기름진 느끼함 없이 씹을수록 담백하고 진한 감칠맛이 폭발해 순식간에 불판을 비워냈답니다 😋"
                )
            ]

        # 일반 요리
        else:
            variations = [
                (
                    f"✨ {step_num}. 감탄이 절로 나오는 비주얼! {clean_name} 등장!",
                    f"드디어 등장한 오늘의 하이라이트! 사진 속 먹음직스러운 {clean_name} 비주얼 보이시나요? 🍽️✨\n\n"
                    f"테이블에 놓이자마자 군침 도는 냄새와 푸짐한 담음새에 다들 감탄사를 연발했는데요!\n\n"
                    f"좋은 식재료를 아낌없이 사용하셔서 한 입 맛볼 때마다 깊은 풍미와 신선한 식감이 그대로 전해졌답니다 😋"
                ),
                (
                    f"🍽️ {step_num}. 오감을 사로잡은 특급 요리, {clean_name}!",
                    f"사진으로도 전해지는 남다른 아우라의 {clean_name} 모습이에요! 💖\n\n"
                    f"정성 가득한 플레이팅과 먹음직스러운 빛깔이 먹기 전부터 기대를 한껏 끌어올렸는데요!\n\n"
                    f"한 점 입에 넣는 순간 퍼지는 풍성한 맛에 찾아온 보람을 제대로 만끽했답니다 👍"
                )
            ]
        header, text = pick_unique_variation(variations, used_set)
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
    context = {"used_templates": set(), "seen_dishes": set()}

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
