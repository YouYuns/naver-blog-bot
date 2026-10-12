# -*- coding: utf-8 -*-
"""
네이버 블로그 맛집 전문 - 진짜 사람이 쓴 것 같은 블로그 글 생성기
- 파일명 기반 사진 자동 분류 및 문맥 1:1 완벽 매칭 배치 (사용자 요청 반영)
- 음식 카테고리(해산물/회, 고기/구이, 양식/파스타, 카페, 일반) 자동 판별 및 맞춤 묘사
- 말투: 활기차고 다정한 '했어요!' 체, 감탄사 및 느낌표(!) 가득
- 지도 및 매장 정보(전화, 영업시간, 주차 등) 본문 최상단 배치
- 로봇/마크다운 기호(**, ##, ■ 등) 100% 완전 제거
- DIA+ 검색 노출 키워드 자연 분산
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
    예: '간판외관.jpg' -> cat='exterior', clean_name='간판외관'
        '미쉐린상장.jpg' -> cat='award', clean_name='미쉐린상장'
        '식사시간제한 1인1메뉴.jpg' -> cat='notice', clean_name='식사시간제한 1인1메뉴'
        '소고기뭇국.jpg' -> cat='soup_side', clean_name='소고기뭇국'
        '육회비빔밥특.jpg' -> cat='dish', clean_name='육회비빔밥특'
        '비빈육회비빔밥.jpg' -> cat='combo', clean_name='비빈육회비빔밥'
    """
    raw_name = os.path.splitext(os.path.basename(filepath))[0]
    # 앞에 붙은 번호, 기호 제거
    clean_name = re.sub(r'^[0-9_\-\.\s\[\]\(\)]+', '', raw_name).strip()
    clean_name = re.sub(r'[_\-]+', ' ', clean_name).strip()
    if not clean_name:
        clean_name = raw_name
    
    clean_lower = clean_name.lower()
    
    if any(k in clean_lower for k in ["외관", "간판", "입구", "도착", "외부", "건물", "가게", "전경"]):
        cat = "exterior"
    elif any(k in clean_lower for k in ["웨이팅", "대기", "캐치테이블", "테이블링", "줄서기", "줄서는", "대기표", "순번"]):
        cat = "waiting"
    elif any(k in clean_lower for k in ["미쉐린", "미슐랭", "블루리본", "상장", "상패", "인증", "명패", "선정", "팻말", "방송", "티비", "tv"]):
        cat = "award"
    elif any(k in clean_lower for k in ["내부", "인테리어", "홀", "좌석", "테이블", "자리", "분위기", "룸", "실내", "조명"]):
        cat = "interior"
    elif any(k in clean_lower for k in ["식사시간제한", "식사시간", "시간제한", "1인1메뉴", "1인 1메뉴", "이용안내", "안내문", "주의사항", "이용수칙", "이용시간", "주문안내", "규칙", "에티켓"]):
        cat = "notice"
    elif any(k in clean_lower for k in ["메뉴판", "차림표", "빌지", "가격표", "주문서"]) or (clean_lower.endswith("메뉴") and "1인1메뉴" not in clean_lower):
        cat = "menu"
    elif any(k in clean_lower for k in ["소고기뭇국", "뭇국", "무국", "기본국", "서비스국", "장국", "된장국", "미역국", "국물제공"]):
        cat = "soup_side"
    elif any(k in clean_lower for k in ["완식", "마무리", "빈그릇", "빈접시", "클리어", "다먹음", "계산", "영수증"]):
        cat = "finish"
    elif any(k in clean_lower for k in ["비빈", "비벼", "비비는", "비벼진", "비벼먹", "섞은", "섞인", "꿀조합", "조합", "찍먹", "김쌈", "쌈", "싸먹", "말아", "한숟가락", "한숟갈"]):
        cat = "combo"
    elif any(k in clean_lower for k in ["디테일", "근접", "클로즈업", "한점", "단면", "확대", "윤기"]) or re.search(r'\d+$', clean_lower):
        cat = "detail"
    elif any(k in clean_lower for k in ["상차림", "밑반찬", "반찬", "기본찬", "세팅", "스끼", "깍두기", "김치", "무침", "샐러드", "양념장"]):
        cat = "sides"
    elif any(k in clean_lower for k in ["사이드", "서브", "라면", "찌개", "볶음밥", "냉면", "음료", "주류", "맥주", "소주", "하이볼", "사리", "추가", "주먹밥", "계란찜"]):
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
    10: 매장 외관 및 간판, 도착
    20: 웨이팅 및 현장 대기 등록 (캐치테이블 등)
    25: 맛집 인증/상패 (미쉐린, 블루리본 등)
    30: 매장 내부 인테리어, 좌석, 분위기
    40: 매장 이용 수칙 및 안내문 (식사시간제한, 1인1메뉴 등)
    50: 메뉴판 및 가격 정독
    60: 기본 상차림 및 밑반찬 세팅
    65: 기본 제공 국물 (소고기뭇국 등)
    71: 메인 요리 중 보통/일반 사이즈
    72: 메인 요리 중 특/곱배기 사이즈
    75: 메인 요리 (육회비빔밥, 수육, 전골, 곰탕 등)
    80: 초근접 디테일/한점 클로즈업 컷
    90: 쓱쓱 비벼서 한입/꿀조합 팁
    100: 사이드 메뉴 및 주류/음료
    110: 완식(빈 그릇) 및 영수증 내돈내산 인증
    """
    c = clean_name.lower()
    if any(k in c for k in ['외관', '간판', '입구', '도착', '외부', '건물', '가게', '전경']):
        return 10
    if any(k in c for k in ['웨이팅', '대기', '캐치테이블', '테이블링', '줄서기', '줄서는', '대기표', '순번']):
        return 20
    if any(k in c for k in ['미쉐린', '미슐랭', '블루리본', '상장', '상패', '인증', '명패', '선정', '팻말', '방송', '티비', 'tv']):
        return 25
    if any(k in c for k in ['내부', '인테리어', '홀', '좌석', '테이블', '자리', '분위기', '룸', '실내', '조명']):
        return 30
    if any(k in c for k in ['식사시간제한', '식사시간', '시간제한', '1인1메뉴', '1인 1메뉴', '이용안내', '안내문', '주의사항', '이용수칙', '이용시간', '주문안내', '규칙', '에티켓']):
        return 40
    if any(k in c for k in ['메뉴판', '차림표', '빌지', '가격표', '주문서']) or (c.endswith('메뉴') and '1인1메뉴' not in c):
        return 50
    if any(k in c for k in ['상차림', '밑반찬', '반찬', '기본찬', '세팅', '스끼', '깍두기', '김치', '무침', '샐러드', '양념장']):
        return 60
    if any(k in c for k in ['소고기뭇국', '뭇국', '무국', '기본국', '서비스국', '장국', '된장국', '미역국', '국물제공']):
        return 65
    if any(k in c for k in ['완식', '마무리', '빈그릇', '빈접시', '클리어', '다먹음', '계산', '영수증']):
        return 110
    if any(k in c for k in ['비빈', '비벼', '비비는', '비벼진', '비벼먹', '섞은', '섞인', '꿀조합', '조합', '찍먹', '김쌈', '쌈', '싸먹', '말아', '한숟가락', '한숟갈']):
        return 90
    if any(k in c for k in ['디테일', '근접', '클로즈업', '한점', '단면', '확대', '윤기']):
        return 80
    if category == 'sub_dish' or any(k in c for k in ['사이드', '서브', '음료', '주류', '맥주', '소주', '하이볼', '사리', '추가']):
        return 100
    if any(k in c for k in ['보통', '일반']):
        return 71
    if any(k in c for k in ['특', '대', '곱배기']):
        return 72
    if re.search(r'\d+$', c):
        return 80
    return 75

def smart_photo_sort_key(filepath):
    """
    1) 파일명이 숫자로 시작하면 (01_, 1_) 사용자의 의도된 번호 순서 최우선 적용
    2) 숫자가 없는 파일명이면 맛집 방문 여정(외관->웨이팅->인증->내부->안내->메뉴->기본찬/국->메인요리->디테일->비빈모습->완식) 순서로 자동 배치
    """
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
    "interior": "내부 인테리어",
    "notice": "매장 이용수칙 및 안내",
    "menu": "메뉴판 및 가격",
    "soup_side": "기본 제공 국물",
    "sides": "기본 상차림 및 밑반찬",
    "dish": "대표 시그니처 요리",
    "detail": "초근접 디테일 컷",
    "combo": "쓱쓱 비빈 모습 / 꿀조합",
    "sub_dish": "사이드 메뉴",
    "finish": "식사 마무리 및 내돈내산 인증"
}

def get_photo_analysis_summary(photo_paths):
    """GUI 로그 표시용 요약 텍스트 생성 (사용자 파일명 1:1 반영 확인)"""
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
    """마크다운 기호(**, ##, ■ 등) 완전 박멸"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = text.replace("■", "").strip()
    return text

def build_rich_hashtags(store_name, location, menu, features=""):
    """
    네이버 블로그 검색 노출(SEO) 및 감성 최적화 - 풍성한 해시태그 30~40개 생성
    """
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

    # 1. 상호명 관련
    tags.append(clean_store)
    tags.append(f"{clean_loc}{clean_store}")
    for lp in loc_parts:
        tags.append(f"{lp}{clean_store}")

    # 2. 메뉴 + 맛집
    for mp in menu_parts:
        tags.append(mp)
        tags.append(f"{mp}맛집")
        for lp in loc_parts:
            tags.append(f"{lp}{mp}")
            tags.append(f"{lp}{mp}맛집")

    # 3. 지역 + 맛집/핫플/데이트/술집/회식
    for lp in loc_parts:
        tags.append(f"{lp}맛집")
        tags.append(f"{lp}핫플")
        tags.append(f"{lp}데이트")
        tags.append(f"{lp}데이트코스")
        tags.append(f"{lp}가볼만한곳")
        tags.append(f"{lp}술집")
    if len(loc_parts) > 1:
        tags.append(f"{clean_loc}맛집")

    # 4. 인기 트렌드 & 블로그 필수 키워드
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

def detect_cuisine_type(store_name, menu, features):
    """메뉴와 상호명을 분석하여 음식 카테고리 판별"""
    text = f"{store_name} {menu} {features}".lower()
    if any(k in text for k in ["방어", "회", "사시미", "참치", "연어", "광어", "우럭", "해물", "조개", "물회", "수산", "초밥", "해산물"]):
        return "seafood"
    elif any(k in text for k in ["삼겹살", "목살", "갈비", "고기", "한우", "소고기", "돼지", "곱창", "막창", "대창", "차돌", "등심", "안심", "숯불"]):
        return "meat"
    elif any(k in text for k in ["파스타", "스테이크", "피자", "버거", "샐러드", "리조또", "양식", "브런치", "와인"]):
        return "western"
    elif any(k in text for k in ["카페", "커피", "디저트", "베이커리", "빵", "케이크", "에이드"]):
        return "cafe"
    return "general"

def generate_dynamic_title(store_name, location, main_menu):
    """매번 새롭고 다채로운 감성 블로그 제목 생성 (총 15가지 패턴)"""
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
    """매번 완전히 다른 블로그 도입부 생성 (6가지 다채로운 스토리 테마)"""
    intros = [
        # 테마 1: SNS 핫플 피드 탐방기
        (
            f"✨ {location} 핫플! {store_name} 솔직 방문기!",
            f"안녕하세요 잇님들! 맛있는 곳이라면 어디든 찾아가는 맛집 탐방러예요! 😋\n\n"
            f"요즘 SNS 피드에서 유독 자주 보이고 볼 때마다 침샘을 자극했던 {location} 핫플, '{store_name}'에 드디어 다녀왔답니다!\n\n"
            f"평소에도 {main_menu}를 워낙 좋아해서 벼르고 벼르다가 찾아갔는데, 기대했던 것보다 훨씬 더 만족스러워서 카메라 셔터를 쉴 새 없이 눌렀어요 ✨\n\n"
            f"생생한 사진과 함께하는 솔직한 방문기 시작하기 전에, 매장 상세 정보와 위치부터 먼저 위에 깔끔하게 정리해 드릴게요!"
        ),
        # 테마 2: 지인/친구 극찬 검증기
        (
            f"💖 입소문 자자한 {location} 명소, {store_name} 다녀왔어요!",
            f"안녕하세요 여러분! 소문난 맛집만 쏙쏙 골라 다니는 일상 블로거예요! ✨\n\n"
            f"주변에 입맛 까다롭기로 유명한 친구들이 인생 맛집이라며 입이 마르도록 칭찬하던 {location}의 대표 맛집, '{store_name}'에 드디어 발도장을 찍고 왔습니다!\n\n"
            f"대표 메뉴인 {main_menu}의 명성이 워낙 자자해서 설레는 마음으로 방문했는데, 한 입 맛보는 순간 왜 그렇게 다들 칭찬했는지 바로 납득이 가더라고요 💖\n\n"
            f"본격적인 먹방 사진을 풀어보기 전에, 매장 이용 정보와 위치 지도부터 알차게 짚어드릴게요!"
        ),
        # 테마 3: 힐링 미식 외출기
        (
            f"🍽️ 힐링 가득한 한 끼! {location} {store_name} 솔직 리뷰!",
            f"잇님들 안녕하세요! 오늘 하루도 기분 좋게 보내고 계신가요? 🥰\n\n"
            f"지친 일상 속에서 맛있는 음식 하나로 완벽하게 힐링하고 싶었던 날, 고민 없이 달려간 {location} 찐맛집 '{store_name}' 솔직 후기를 가져왔어요!\n\n"
            f"정갈한 분위기 속에서 즐긴 {main_menu}의 감동적인 풍미가 아직도 잊혀지지 않는데요 ✨\n\n"
            f"방문 계획 있으신 분들을 위해 도움 되는 매장 필수 정보와 위치 안내부터 먼저 상단에 싹 공유해 드릴게요!"
        ),
        # 테마 4: 골목 숨은 보석 탐방기
        (
            f"🌟 {location} 골목 핫플레이스! {store_name} 탐방기!",
            f"안녕하세요 잇님들! 맛집 레이더 가동 중인 맛집 사냥꾼이에요! 🍽️\n\n"
            f"오늘은 {location} 골목 사이에서 가장 뜨거운 인기를 자랑하는 핫플레이스, '{store_name}'에 다녀온 찐 후기입니다!\n\n"
            f"사진으로만 보던 {main_menu}의 영롱한 비주얼을 직접 눈앞에서 마주하니 찾아온 보람이 물씬 들었는데요 👍\n\n"
            f"사진과 꿀팁이 가득한 생생 후기를 시작하기에 앞서, 방문 전 꼭 알아두어야 할 매장 상세 정보부터 먼저 체크해 드릴게요!"
        ),
        # 테마 5: 오랜만의 취향 저격 맛집
        (
            f"😋 감탄이 절로 나온 {location} 찐맛집 {store_name}!",
            f"반가워요 잇님들! 늘 맛있는 순간을 기록하는 푸드 블로거예요! 💖\n\n"
            f"매일 먹는 평범한 외식 말고, 정말 제대로 된 맛있는 한 끼가 간절했던 날 찾아간 {location} 맛집 '{store_name}' 이야기입니다!\n\n"
            f"신선한 식재료와 깊은 손맛이 어우러진 {main_menu} 덕분에 식사하는 내내 감탄사를 연발했는데요 😋\n\n"
            f"본격적인 방문 사진과 꿀조합을 소개해 드리기 전, 매장 운영 정보와 네이버 지도부터 정갈하게 정리해 드릴게요!"
        ),
        # 테마 6: 내돈내산 솔직 검증 리뷰
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
    """매번 완전히 다른 결론 및 총평 생성 (5가지 다채로운 총평 포맷)"""
    outros = [
        # 포맷 1: 별점 & 만점 총평형
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
        # 포맷 2: 힐링 & 깊은 여운형
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
        # 포맷 3: 핵심 3줄 요약 & 추천형
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
        # 포맷 4: 핫플 인증 & 데이트/모임 추천형
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
        # 포맷 5: 다정한 일상 소통형
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

def create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count):
    """
    각 사진(또는 2장 묶음)의 파일명에서 추출한 주제(clean_name)를 바탕으로
    매 생성마다 100% 새롭고 다채로운 어조의 블로그 본문 및 헤더 생성
    """
    is_pair = count > 1
    pair_suffix = " (가로 나란히)" if is_pair else ""

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
                f"🏢 {step_num}. 맛집 포스가 물씬 풍기는 {clean_name} 전경!",
                f"발걸음을 멈추게 만드는 포스 넘치는 {clean_name} 비주얼이에요! 👍\n\n"
                f"깔끔하게 정돈된 간판과 정갈한 익스테리어가 매장의 신뢰도를 단번에 증명해 주는 듯했는데요.\n\n"
                f"소문난 곳답게 입구에서부터 활기찬 에너지가 뿜어져 나와 찾아온 보람이 물씬 들었답니다 ✨"
            ),
            (
                f"🚶 {step_num}. 설레는 발걸음으로 마주한 {store_name} {clean_name}!",
                f"기대감을 한가득 안고 찾아온 {store_name}의 {clean_name} 전경이에요! 💖\n\n"
                f"입구 주변부터 맛집 특유의 활기가 가득해서 지나가는 사람들의 시선도 사로잡고 있었는데요.\n\n"
                f"외관부터 남다른 포스를 자랑해서 인증샷부터 찰칵 남기고 기분 좋게 입장했답니다 🍽️"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} {clean_name}{pair_suffix}"

    elif cat == "waiting":
        variations = [
            (
                f"⏳ {step_num}. 소문난 핫플 인증! 현장 {clean_name} 등록!",
                f"인기 맛집답게 도착하자마자 현장에서 마주한 {clean_name} 모습이에요! 📋\n\n"
                f"워낙 줄서서 먹는 곳으로 유명해서 살짝 긴장했는데, 체계적인 대기 시스템 덕분에 대기 등록도 일사천리로 마칠 수 있었어요.\n\n"
                f"생각보다 회전율이 빨라서 지루할 틈 없이 입장 순서를 기다렸답니다 ✨"
            ),
            (
                f"📋 {step_num}. 줄서는 열기 가득! {clean_name} 접수 완료!",
                f"매장 앞에 도착하자마자 서둘러 접수한 {clean_name} 현장이에요! ⏱️\n\n"
                f"현장에 모인 손님들의 열기만 봐도 이곳의 인기를 실감할 수 있었는데요.\n\n"
                f"기다리는 동안 기대감이 두 배로 몽글몽글 차올라 일행과 함께 신나게 메뉴 이야기를 나누며 차분히 순서를 기다렸어요 😋"
            ),
            (
                f"⚡ {step_num}. 기다림마저 설레는 {clean_name} 풍경!",
                f"도착하자마자 신속하게 마친 {clean_name} 등록 사진이에요! 📱\n\n"
                f"실시간으로 순번을 확인할 수 있어서 기다리는 시간이 전혀 지루하지 않았는데요.\n\n"
                f"얼마나 맛있는 음식이 기다리고 있을지 상상하니 기다림마저 즐거운 축제처럼 느껴졌답니다 👍"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} 현장 {clean_name}{pair_suffix}"

    elif cat == "award":
        variations = [
            (
                f"🏆 {step_num}. 맛집 인증의 위엄! 영롱한 {clean_name} 발견!",
                f"매장에 들어서자마자 시선을 사로잡은 영롱한 {clean_name} 사진이에요! 🏆✨\n\n"
                f"벽면에 당당하게 자리 잡은 권위 있는 인증 명패를 직접 두 눈으로 마주하니 '아, 역시 제대로 잘 찾아왔구나!' 하는 확신이 절로 생겼는데요.\n\n"
                f"수많은 미식가들과 손님들에게 꾸준히 인정받은 곳이라 먹기 전부터 신뢰도가 200% 상승했답니다 👍"
            ),
            (
                f"🎖️ {step_num}. 시선을 압도하는 공인된 맛집 증표, {clean_name}!",
                f"들어서자마자 눈길을 떼지 못했던 {clean_name} 모습이에요! 🌟\n\n"
                f"오랜 세월 동안 변함없는 맛과 퀄리티를 지켜온 곳에만 주어지는 귀한 인증을 보니 가슴이 웅장해졌는데요.\n\n"
                f"한 번 방문한 손님들이 왜 그렇게 입이 마르도록 칭찬했는지 단번에 납득이 가는 순간이었답니다 💖"
            ),
            (
                f"✨ {step_num}. 믿고 먹는 검증된 클래스! {clean_name} 확인!",
                f"벽면 한편을 빛내고 있던 자랑스러운 {clean_name} 사진이에요! 🏅\n\n"
                f"미식 평가단과 대중 모두에게 만장일치로 합격점을 받은 곳이라니, 오늘 메뉴 선택은 실패할 리가 없겠다는 든든한 믿음이 팍팍 생겨났답니다 🥰"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} 신뢰를 더해주는 {clean_name}{pair_suffix}"

    elif cat == "interior":
        variations = [
            (
                f"🌿 {step_num}. 아늑함과 정갈함이 공존하는 {clean_name} 분위기!",
                f"매장 문을 열고 안으로 들어서서 담아본 {clean_name} 사진이에요! 🌿\n\n"
                f"따스하고 은은한 조명에 테이블 간격도 답답함 없이 배치되어 있어 일행과 편안하게 대화 나누기 참 좋았어요.\n\n"
                f"구석구석 먼지 하나 없이 위생적으로 관리된 모습에 식사 전부터 기분이 절로 상쾌해졌답니다 ✨"
            ),
            (
                f"💡 {step_num}. 감각적인 감성이 돋보이는 {clean_name} 전경!",
                f"내부로 들어서자마자 감탄이 나왔던 세련된 {clean_name} 공간이에요! 🛋️\n\n"
                f"모던한 우드 톤과 포근한 인테리어가 어우러져 데이트나 소중한 모임 장소로도 손색이 없겠더라고요.\n\n"
                f"쾌적한 환기와 차분한 분위기 덕분에 식사에 온전히 집중할 수 있는 완벽한 환경이었어요 💖"
            ),
            (
                f"✨ {step_num}. 정돈된 깔끔함이 매력적인 {clean_name} 둘러보기!",
                f"정갈하게 세팅된 테이블과 따뜻한 공기가 맞이해 준 {clean_name} 모습이에요! 🍽️\n\n"
                f"바쁜 시간대임에도 테이블을 신속하고 청결하게 정리해 주셔서 머무는 내내 대접받는 듯한 기분 좋은 안락함을 만끽할 수 있었답니다 😋"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} 아늑한 {clean_name}{pair_suffix}"

    elif cat == "notice":
        variations = [
            (
                f"📌 {step_num}. 방문 전 꼭 챙겨야 할 꿀팁! {clean_name} 확인!",
                f"매장 이용 전 눈여겨보아야 할 {clean_name} 안내 사진이에요! 💡\n\n"
                f"많은 분들이 사랑하는 인기 핫플인 만큼 모든 손님이 쾌적하게 식사를 즐길 수 있도록 배려 깊은 에티켓 수칙이 명확히 적혀 있었는데요.\n\n"
                f"미리 알고 방문하시면 기다림 없이 훨씬 여유롭고 기분 좋은 식사를 하실 수 있을 거예요 📌"
            ),
            (
                f"📋 {step_num}. 원활한 이용을 위한 센스 만점 {clean_name}!",
                f"테이블과 매장 곳곳에 친절하게 안내되어 있는 {clean_name} 모습이에요! 🔍\n\n"
                f"정해진 룰이 확실하고 체계적인 덕분에 매장 회전도 빠르고 전반적인 식사 환경이 더욱 쾌적하게 유지되는 느낌이었어요.\n\n"
                f"잇님들도 방문 전에 살짝 체크해 두시면 큰 도움이 될 꿀정보랍니다 👍"
            ),
            (
                f"💡 {step_num}. 현명한 식사를 위한 필수 체크! {clean_name}!",
                f"주문 전 꼼꼼히 읽어본 {clean_name} 내용이에요! 📝\n\n"
                f"손님들의 소중한 시간을 아껴주고 최상의 퀄리티를 제공하기 위한 매장의 세심한 정성이 돋보였는데요.\n\n"
                f"헛걸음이나 혼선 없이 알차게 즐기기 위해 꼭 알아두어야 할 필수 포인트랍니다 ✨"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} {clean_name} 이용 안내{pair_suffix}"

    elif cat == "menu":
        variations = [
            (
                f"📋 {step_num}. 알찬 구성에 행복한 고민! {clean_name} 정독!",
                f"자리에 앉아 설레는 마음으로 정독해 본 {clean_name} 사진이에요! 📋\n\n"
                f"시그니처 메뉴인 {main_menu}를 시작으로 다채롭고 매력적인 요리들이 군더더기 없이 준비되어 있었는데요.\n\n"
                f"퀄리티 대비 가성비도 아주 훌륭해서 망설임 없이 대표 메뉴들로 푸짐하게 주문을 완료했답니다 🍽️"
            ),
            (
                f"📖 {step_num}. 취향 저격 메뉴 가득! {clean_name} 둘러보기!",
                f"한 장 한 장 넘겨보며 군침을 꼴깍 삼켰던 {clean_name} 구성이에요! 🔍\n\n"
                f"전문점다운 내공이 느껴지는 메뉴 라인업 덕분에 무엇을 골라도 실패 없겠다는 믿음이 팍팍 들었는데요.\n\n"
                f"오늘은 대표 간판 요리들을 제대로 맛보기로 하고 기분 좋게 주문을 마쳤답니다 😋"
            ),
            (
                f"🍽️ {step_num}. 정갈한 차림표 정독 & {clean_name} 주문 완료!",
                f"어떤 조합으로 먹어야 가장 맛있을지 행복하게 고민했던 {clean_name} 타임이에요! 📝\n\n"
                f"대표 메뉴들의 밸런스가 워낙 훌륭해서 일행들과 상의 끝에 황금 조합으로 빠르게 주문을 넣었답니다.\n\n"
                f"주문이 들어가자마자 주방에서 맛있는 소리가 들려와 기대감이 솟구쳤어요 ✨"
            )
        ]
        header, text = random.choice(variations)
        caption = f"{store_name} 정갈한 {clean_name} 구성 안내{pair_suffix}"

    elif cat == "soup_side":
        variations = [
            (
                f"🥣 {step_num}. 속이 확 풀리는 감동의 맛! 기본 {clean_name}!",
                f"메인 요리와 함께 테이블에 차려져 나온 기본 {clean_name} 사진이에요! 🥣✨\n\n"
                f"뚝배기에서 피어오르는 구수한 김과 함께 한 숟가락 먼저 떠먹어 보았는데, 푹 고아낸 육수의 깊은 감칠맛이 온몸으로 스며들며 속을 따뜻하게 데워주더라고요.\n\n"
                f"서비스 국물이라는 게 믿기지 않을 정도로 묵직한 내공이 느껴졌답니다 👍"
            ),
            (
                f"🍲 {step_num}. 기본 제공의 품격! 정갈하고 진한 {clean_name}!",
                f"상차림과 함께 등장하자마자 감탄사를 부른 {clean_name} 비주얼이에요! 🍲\n\n"
                f"맑고 개운한 국물에 부드러운 고기와 건더기가 실하게 들어있어 메인 요리를 먹는 중간중간 떠먹기 딱 좋았는데요.\n\n"
                f"입안을 깔끔하게 리셋해 주어 식사의 완성도를 한층 더 높여주는 일등 공신이었어요 💖"
            ),
            (
                f"✨ {step_num}. 한 모금에 반해버린 마성의 기본 국물, {clean_name}!",
                f"정갈하게 담겨 나온 따끈따끈한 {clean_name} 사진이에요! 😋\n\n"
                f"한 입 맛보는 순간 '어라? 메인 국밥 못지않은데?' 싶을 정도로 깊고 시원한 육수 맛에 숟가락질을 멈출 수 없었는데요.\n\n"
                f"밥 한 공기 말아먹고 싶을 만큼 중독성 강한 꿀맛이었답니다 🥰"
            )
        ]
        header, text = random.choice(variations)
        caption = f"깊고 진한 풍미의 {clean_name}{pair_suffix}"

    elif cat == "sides":
        variations = [
            (
                f"🥗 {step_num}. 메인 요리의 맛을 돋워줄 정갈한 {clean_name}!",
                f"주문 후 테이블 위에 정갈하게 세팅된 {clean_name} 사진이에요! 🥢\n\n"
                f"담김새부터 단정하고 신선함이 돋보이는 밑반찬들이 테이블을 채워주었는데요.\n\n"
                f"조미료 맛이 아닌 재료 고유의 감칠맛이 살아있어 메인 요리가 나오기 전부터 젓가락이 바쁘게 움직였답니다 😋"
            ),
            (
                f"🥢 {step_num}. 깔끔하고 알찬 구성! 군더더기 없는 {clean_name}!",
                f"메인 요리와 찰떡궁합을 자랑하는 다채로운 {clean_name} 모습이에요! ✨\n\n"
                f"하나하나 정갈하게 간이 맞추어져 있어 기름진 입안을 개운하게 잡아주기에 안성맞춤이었는데요.\n\n"
                f"반찬 하나에도 정성을 아끼지 않는 곳이라는 게 고스란히 느껴졌답니다 👍"
            ),
            (
                f"✨ {step_num}. 소박하지만 깊은 내공! 맛깔스러운 {clean_name}!",
                f"신선한 식감과 깊은 손맛이 살아있는 {clean_name} 세팅 컷이에요! 🌿\n\n"
                f"메인 요리와 함께 곁들였을 때 풍미를 두 배로 끌어올려 주는 알찬 구성이라 식사 내내 빈 접시가 보일 정도로 맛있게 즐겼답니다 💖"
            )
        ]
        header, text = random.choice(variations)
        caption = f"정갈하고 푸짐한 {clean_name}{pair_suffix}"

    elif cat == "detail":
        variations = [
            (
                f"📸 {step_num}. 윤기 좌르르! {clean_name} 초근접 디테일 컷!",
                f"신선한 디테일을 더 가까이 생생하게 전해드리고 싶어 담아본 {clean_name} 클로즈업 샷이에요! 📸\n\n"
                f"조명을 받아 촉촉하게 반짝이는 윤기와 탱글탱글한 결이 살아있는 게 보이시나요?\n\n"
                f"한 점 집어 올릴 때마다 묵직하게 전해지는 탄력에 절로 감탄이 터져 나왔답니다 👍"
            ),
            (
                f"🔍 {step_num}. 극강의 신선도 인증! {clean_name} 숨 막히는 비주얼!",
                f"카메라 렌즈를 바짝 당겨 담아본 {clean_name}의 경이로운 디테일이에요! ✨\n\n"
                f"찰진 육질과 고운 색감이 최상급 식재료만을 고집하신다는 증거 그 자체였는데요.\n\n"
                f"눈으로 먼저 맛보는 순간 이미 온몸에 전율이 돋을 만큼 완벽한 자태를 뽐내고 있었답니다 💖"
            ),
            (
                f"✨ {step_num}. 한 점의 예술! {clean_name} 초밀착 줌인!",
                f"사진으로만 봐도 군침이 꼴깍 넘어가는 {clean_name} 초밀착 컷이에요! 😋\n\n"
                f"촉촉하고 부드러운 질감이 한눈에 들어와 보는 이의 침샘을 무한 자극했는데요.\n\n"
                f"입안에 넣자마자 사르르 녹아내리는 극상의 식감을 눈으로도 고스란히 느낄 수 있었답니다 🥰"
            )
        ]
        header, text = random.choice(variations)
        caption = f"윤기 좌르르 흐르는 {clean_name} 초근접 컷{pair_suffix}"

    elif cat == "combo":
        if any(k in clean_name for k in ["비빈", "비벼", "비비는", "비벼진", "비벼먹", "섞은", "섞인"]):
            variations = [
                (
                    f"💡 {step_num}. 쓱쓱 맛있게 비벼서 한 입 가득! {clean_name}!",
                    f"숟가락과 젓가락으로 야무지게 비벼낸 영롱한 {clean_name} 비주얼이에요! 🥣✨\n\n"
                    f"고소한 특제 양념과 신선한 재료들이 밥알 사이사이에 골고루 배어들어, 한 숟가락 듬뿍 떠먹는 순간 입안에서 감칠맛의 축제가 열렸는데요!\n\n"
                    f"씹을수록 퍼지는 진한 고소함에 진실의 미간이 절로 찌푸려질 만큼 황홀한 꿀맛이었답니다 🥰"
                ),
                (
                    f"🥄 {step_num}. 입안 가득 감칠맛 폭발! 잘 비벼낸 {clean_name}!",
                    f"모든 재료가 황금비율로 어우러지도록 정성껏 비벼낸 {clean_name} 모습이에요! 💖\n\n"
                    f"아삭한 채소의 식감과 부드럽게 감기는 메인 요리의 조화가 가히 예술이었는데요.\n\n"
                    f"숟가락질을 멈출 틈도 없이 바쁘게 입으로 직행할 만큼 마성의 중독성을 자랑했답니다 😋"
                ),
                (
                    f"🔥 {step_num}. 행복 지수 200%! 두 배 더 맛있는 {clean_name} 즐기기!",
                    f"사진처럼 골고루 잘 섞어 크게 한 숟가락 떠먹어 본 {clean_name} 타임이에요! 🍽️\n\n"
                    f"따로 먹어도 맛있지만 이렇게 한데 어우러졌을 때 터져 나오는 시너지 효과는 정말 상상 그 이상이었는데요.\n\n"
                    f"잇님들도 방문하시면 꼭 이렇게 큼직하게 비벼서 드셔보시길 강력 추천해 드려요 👍"
                )
            ]
            header, text = random.choice(variations)
            caption = f"골고루 맛있게 비벼낸 {clean_name}{pair_suffix}"
        else:
            variations = [
                (
                    f"💡 {step_num}. 두 배 더 맛있게 즐기는 {clean_name} 특급 꿀조합!",
                    f"사진에 보이는 것처럼 맛의 시너지를 극대화해 주는 나만의 꿀조합이에요! 💖\n\n"
                    f"준비된 특제 양념에 콕 찍거나 정갈한 곁들임 찬과 함께 곁들여 한 입 가득 맛보았는데요.\n\n"
                    f"입안에서 고소함과 감칠맛이 폭발하듯 어우러져서 진실의 미소가 절로 지어졌답니다 🥰"
                ),
                (
                    f"✨ {step_num}. 황홀한 미식의 향연! {clean_name} 꿀조합 팁!",
                    f"정갈한 찬과 소스를 더해 최상의 맛을 이끌어낸 {clean_name} 한 점이에요! 🥢\n\n"
                    f"재료들이 입안에서 겉돌지 않고 환상적인 하모니를 만들어내어 씹을 때마다 감탄이 터져 나왔는데요.\n\n"
                    f"이 조합으로 먹다 보니 그 많던 음식이 눈 깜짝할 사이에 줄어들었답니다 😋"
                )
            ]
            header, text = random.choice(variations)
            caption = f"두 배 더 맛있게 즐기는 환상의 {clean_name}{pair_suffix}"

    elif cat == "sub_dish":
        variations = [
            (
                f"🍜 {step_num}. 놓칠 수 없는 든든한 별미! {clean_name}!",
                f"메인 요리와 함께 곁들이기 위해 주문한 {clean_name} 사진이에요! 🍜\n\n"
                f"사진처럼 푸짐하고 먹음직스러운 비주얼을 자랑하며 식사의 완성도를 한층 더 높여주었는데요!\n\n"
                f"메인 요리와의 궁합도 찰떡이라 마지막 한 숟가락까지 감탄하며 든든하게 즐겼답니다 ✨"
            ),
            (
                f"🍲 {step_num}. 식사를 더욱 풍성하게 만들어준 {clean_name}!",
                f"테이블을 한층 더 화려하게 채워준 매력적인 사이드, {clean_name} 비주얼이에요! 🍽️\n\n"
                f"메인 못지않은 푸짐한 양과 정갈한 플레이팅에 다들 젓가락을 멈추지 못했는데요.\n\n"
                f"함께 곁들이니 물릴 틈 없이 식사의 텐션을 끝까지 끌어올려 주었답니다 😋"
            )
        ]
        header, text = random.choice(variations)
        caption = f"푸짐하고 맛깔스러운 {clean_name}{pair_suffix}"

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
            header, text = random.choice(variations)
            caption = f"{store_name} 솔직 내돈내산 {clean_name}{pair_suffix}"
        else:
            variations = [
                (
                    f"🍚 {step_num}. 밥알 한 톨 남김없이 싹 비운 완식 인증!",
                    f"사진에 보이는 것처럼 마지막 한 숟가락까지 그릇 바닥을 싹싹 긁어먹은 완식 컷이에요! 🍽️✨\n\n"
                    f"배는 터질 듯이 부르지만 마지막 한 점까지 너무 아쉬워서 숟가락을 놓을 수 없었는데요.\n\n"
                    f"기분 좋은 포만감과 함께 오늘 하루의 피로가 눈 녹듯 싹 사라지는 기적을 경험했답니다 💖"
                ),
                (
                    f"✨ {step_num}. 대만족으로 마무리한 완벽한 한 끼 식사!",
                    f"빈 그릇과 함께 훈훈하게 마무리된 식사 현장이에요! 🥰\n\n"
                    f"일행 모두가 연신 감탄사를 쏟아내며 엄지를 치켜세웠을 정도로 완벽했던 자리였는데요.\n\n"
                    f"문을 나서는 순간까지도 입안에 맴도는 기분 좋은 여운에 벌써부터 다음 재방문 일정을 잡고 싶어졌답니다 🍽️"
                )
            ]
            header, text = random.choice(variations)
            caption = f"배부르고 만족스럽게 비워낸 식사 마무리{pair_suffix}"

    else:
        # dish
        c_lower = clean_name.lower()
        if any(k in c_lower for k in ["특", "대", "곱배기"]) and any(w in c_lower for w in ["비빔밥", "육회", "밥", "덮밥"]):
            variations = [
                (
                    f"🥣 {step_num}. 육회가 산더미처럼 푸짐한 {clean_name} 등장!",
                    f"기다리던 오늘의 하이라이트! 사진 속 푸짐한 {clean_name} 비주얼 보이시나요? 🥣✨\n\n"
                    f"'특' 사이즈답게 신선하고 영롱한 붉은빛의 한우 육회가 밥이 보이지 않을 정도로 그릇 가득 산더미처럼 올려져 나왔는데요!\n\n"
                    f"파릇파릇 향긋한 채소와 육회의 푸짐한 비율에 먹기 전부터 감탄사가 절로 쏟아졌답니다 💖"
                ),
                (
                    f"🌟 {step_num}. 압도적인 클라쓰! 그릇 가득 채운 {clean_name}!",
                    f"테이블에 놓이자마자 입이 떡 벌어졌던 특급 비주얼, {clean_name} 사진이에요! 🥩✨\n\n"
                    f"아낌없이 팍팍 얹어주신 푸짐한 고명과 싱그러운 향기가 식탁 전체를 뒤덮었는데요!\n\n"
                    f"특 사이즈만의 묵직한 존재감 덕분에 바라보는 것만으로도 행복해지는 순간이었답니다 😋"
                ),
                (
                    f"👑 {step_num}. 오늘 식사의 주인공! 위풍당당한 {clean_name}!",
                    f"비주얼부터 이미 합격점을 훌쩍 넘긴 {clean_name} 컷이에요! 🍽️\n\n"
                    f"푸짐한 양은 물론이고 육질 하나하나의 신선도가 최상급이라 감탄을 금치 못했는데요!\n\n"
                    f"특으로 주문하길 정말 잘했다며 일행들과 하이파이브를 할 정도로 흡족했답니다 👍"
                )
            ]
            header, text = random.choice(variations)
            caption = f"육회가 아낌없이 듬뿍 올라간 {clean_name}{pair_suffix}"

        elif any(k in c_lower for k in ["보통", "일반"]) and any(w in c_lower for w in ["비빔밥", "육회", "밥", "덮밥"]):
            variations = [
                (
                    f"🥣 {step_num}. 완벽한 밸런스를 자랑하는 {clean_name} 등장!",
                    f"정갈하고 알찬 구성으로 테이블에 차려진 {clean_name} 사진이에요! 🥣✨\n\n"
                    f"신선한 육회의 고운 때깔과 향긋한 미나리가 정갈하게 어우러져 비주얼부터 침샘을 무한 자극했는데요!\n\n"
                    f"부담 없이 한 끼 든든하게 즐기기에 딱 좋은 완벽한 양과 환상적인 밸런스를 자랑했답니다 😋"
                ),
                (
                    f"✨ {step_num}. 정갈함의 정석! 알차게 담겨 나온 {clean_name}!",
                    f"기본기 탄탄한 구성이 돋보이는 {clean_name} 비주얼이에요! 🥢\n\n"
                    f"과하지도 부족하지도 않은 황금 비율로 알차게 담아내어 한 입 한 입 맛보는 즐거움이 가득했는데요!\n\n"
                    f"입안 가득 은은하게 퍼지는 향긋함과 담백함에 절로 미소가 지어졌답니다 💖"
                )
            ]
            header, text = random.choice(variations)
            caption = f"정갈한 비주얼의 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["육회비빔밥", "비빔밥"]):
            variations = [
                (
                    f"🥣 {step_num}. 신선한 육회와 향긋한 미나리의 특급 조화, {clean_name}!",
                    f"테이블을 풍성하게 채워준 오늘의 든든한 주인공, {clean_name} 사진이에요! 🥣✨\n\n"
                    f"아낌없이 올라간 신선한 육회와 파릇파릇한 채소, 고소한 참기름 냄새가 먹기 전부터 침샘을 무한 자극했는데요!\n\n"
                    f"재료 하나하나의 신선도가 눈으로도 고스란히 전해질 만큼 영롱한 비주얼을 뽐내고 있었답니다 💖"
                ),
                (
                    f"🌿 {step_num}. 오감을 깨우는 완벽한 조화! {clean_name} 영접!",
                    f"드디어 영접한 시그니처 대표 메뉴, {clean_name} 비주얼이에요! 😋\n\n"
                    f"선홍빛의 고운 자태와 아삭하고 향긋한 식재료들이 어우러져 보기만 해도 눈이 호강하는 느낌이었는데요!\n\n"
                    f"좋은 재료에서 우러나오는 본연의 단맛과 고소함이 먹기 전부터 가슴을 설레게 만들었답니다 ✨"
                )
            ]
            header, text = random.choice(variations)
            caption = f"먹음직스러운 {clean_name} 비주얼{pair_suffix}"

        elif "수육" in c_lower and any(w in c_lower for w in ["전골", "탕", "냄비", "육수"]):
            variations = [
                (
                    f"🍲 {step_num}. 야들야들한 수육과 깊은 육수의 환상 조화, {clean_name}!",
                    f"보글보글 끓어오르는 비주얼이 예술인 {clean_name} 사진이에요! 🍲✨\n\n"
                    f"맑고 깊은 육수 위에 얇고 부드럽게 삶아진 한우 수육과 향긋한 채소가 산더미처럼 푸짐하게 올려져 나왔는데요!\n\n"
                    f"한 점 집어서 국물과 함께 맛보았는데, 잡내 하나 없이 야들야들 녹아내리는 수육의 육질과 시원하고 깊은 국물의 조화가 감탄 그 자체였답니다 💖"
                ),
                (
                    f"✨ {step_num}. 보글보글 피어오르는 깊은 풍미! {clean_name} 등장!",
                    f"테이블 위에서 은은한 온기를 더해준 오늘의 메인, {clean_name} 비주얼이에요! 🥘\n\n"
                    f"부드럽게 익어가는 수육과 진국 육수의 냄새가 코끝을 스치자마자 다들 젓가락을 들고 대기했는데요!\n\n"
                    f"입에 넣는 순간 사르르 녹아내리는 육질에 눈이 번쩍 뜨일 만큼 황홀했답니다 👍"
                )
            ]
            header, text = random.choice(variations)
            caption = f"야들야들하고 깊은 맛의 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["곰탕", "국밥", "탕", "찌개", "전골", "국물"]):
            variations = [
                (
                    f"🍲 {step_num}. 맑고 깊은 국물이 예술인 {clean_name} 등장!",
                    f"드디어 테이블에 등장한 {clean_name} 비주얼이에요! 🍲✨\n\n"
                    f"뚝배기 가득 푸짐하게 담겨 나와 코끝을 스치는 진하고 구수한 향기에 다들 감탄사를 터뜨렸는데요!\n\n"
                    f"맑고 깊은 국물에 부드러운 고기가 아낌없이 듬뿍 들어가 있어서, 한 숟가락 떠먹는 순간 속이 확 풀리면서 온몸이 사르르 녹아내리는 기분이었답니다 💖"
                ),
                (
                    f"🥣 {step_num}. 진한 내공이 느껴지는 깊은 감칠맛! {clean_name}!",
                    f"따끈따끈한 김과 함께 등장한 감동의 {clean_name} 사진이에요! 😋\n\n"
                    f"오랜 정성으로 푹 끓여내어 기름기 없이 맑고 담백한 국물 맛이 일품이었는데요!\n\n"
                    f"건더기도 아낌없이 팍팍 들어가 있어 든든함과 개운함을 동시에 챙길 수 있었답니다 👍"
                )
            ]
            header, text = random.choice(variations)
            caption = f"맑고 깊은 국물의 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["수육", "고기", "삼겹", "갈비", "목살", "한우", "스테이크", "구이", "족발", "보쌈"]):
            variations = [
                (
                    f"🥩 {step_num}. 야들야들 육즙 폭발! {clean_name} 등장!",
                    f"드디어 기다리던 오늘의 하이라이트, {clean_name} 사진이에요! 🥩✨\n\n"
                    f"사진에 보이는 것처럼 두툼하면서도 결이 살아있는 비주얼이 정말 대박이었는데요!\n\n"
                    f"한 점 집어서 맛보는 순간 부드럽게 씹히는 육질과 입안 가득 팡팡 터지는 고소한 육즙의 향연에 감탄사가 절로 나왔답니다 😋"
                ),
                (
                    f"🔥 {step_num}. 고소함의 극치! 윤기 흐르는 {clean_name}!",
                    f"최상의 굽기와 신선도를 자랑하는 {clean_name} 컷이에요! 🍽️\n\n"
                    f"잡내 하나 없이 고기 본연의 풍미가 가득 살아있어 소금만 살짝 찍어 먹어도 꿀맛이었는데요!\n\n"
                    f"씹을 때마다 촉촉하게 배어 나오는 육즙 덕분에 젓가락을 멈출 수 없었답니다 💖"
                )
            ]
            header, text = random.choice(variations)
            caption = f"육즙 가득한 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["회", "사시미", "방어", "연어", "참치", "광어", "초밥", "해물"]):
            variations = [
                (
                    f"🐟 {step_num}. 영롱한 때깔과 찰진 식감! {clean_name} 등장!",
                    f"선홍빛의 영롱한 때깔과 찰진 기름기가 좔좔 흐르는 {clean_name} 비주얼이에요! ✨\n\n"
                    f"접시 가득 빈틈없이 빼곡하게 담겨 나오는 모습에 다들 카메라부터 들고 사진 찍기 바빴는데요!\n\n"
                    f"와사비 살짝 얹어서 맛보았는데, 입안에 넣자마자 쫀득하게 감기며 사르르 녹아내리는 고소함이 일품이었답니다 💖"
                ),
                (
                    f"🌊 {step_num}. 바다의 신선함이 입안 가득! {clean_name}!",
                    f"도톰하고 정갈하게 썰려 나온 {clean_name} 모습이에요! 🍣\n\n"
                    f"비린 맛 하나 없이 쫀득쫀득 탱글탱글한 탄력이 씹을수록 달큰한 감칠맛을 선사해 주었는데요!\n\n"
                    f"한 점 맛볼 때마다 감탄사가 절로 쏟아질 만큼 최고의 퀄리티였답니다 👍"
                )
            ]
            header, text = random.choice(variations)
            caption = f"신선하고 찰진 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["비빔밥", "밥", "덮밥", "볶음밥", "솥밥"]):
            variations = [
                (
                    f"🥣 {step_num}. 고소함과 풍미 가득한 {clean_name} 등장!",
                    f"테이블을 풍성하게 채워준 오늘의 든든한 주인공, {clean_name} 사진이에요! 🥣✨\n\n"
                    f"아낌없이 올라간 신선한 고명과 고소한 참기름 냄새가 먹기 전부터 침샘을 무한 자극했는데요!\n\n"
                    f"쓱쓱 비벼서 한 숟가락 가득 떠먹으니 다채로운 재료들의 식감이 완벽한 조화를 이루었답니다 😋"
                ),
                (
                    f"✨ {step_num}. 풍성한 담음새에 반해버린 {clean_name}!",
                    f"정성껏 지어낸 밥 위에 다채로운 고명이 소복이 쌓인 {clean_name} 컷이에요! 🍚\n\n"
                    f"눈으로 먼저 맛보는 화려한 색감과 고소한 향에 숟가락을 들자마자 행복감이 차올랐는데요!\n\n"
                    f"재료 하나하나의 식감이 살아있어 마지막 한 톨까지 감탄하며 싹 비웠답니다 💖"
                )
            ]
            header, text = random.choice(variations)
            caption = f"풍미 가득한 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["칼국수", "라면", "파스타", "면", "우동", "국수"]):
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
            header, text = random.choice(variations)
            caption = f"쫄깃탱글한 {clean_name}{pair_suffix}"

        elif any(w in c_lower for w in ["파전", "전", "튀김", "피자", "버거", "카츠", "치킨"]):
            variations = [
                (
                    f"🍕 {step_num}. 겉바속촉 극상의 바삭함! {clean_name} 등장!",
                    f"노릇노릇 바삭하게 구워져 나온 {clean_name} 사진이에요! 🍽️✨\n\n"
                    f"겉은 바삭하고 속은 촉촉하게 재료의 풍미가 살아있어 입에 넣자마자 바사삭 소리와 함께 감탄이 절로 나왔는데요!\n\n"
                    f"재료를 아낌없이 담아 정성껏 부쳐내신 덕분에 마지막 한 조각까지 대만족하며 즐겼답니다 😋"
                ),
                (
                    f"✨ {step_num}. 바삭 고소함의 끝판왕! {clean_name}!",
                    f"황금빛 자태를 뽐내며 갓 튀겨져/구워져 나온 {clean_name} 비주얼이에요! 🥢\n\n"
                    f"기름진 느끼함 없이 담백하고 바삭한 식감이 일품이라 다른 메뉴들과의 궁합도 찰떡이었답니다 💖"
                )
            ]
            header, text = random.choice(variations)
            caption = f"바삭한 풍미의 {clean_name}{pair_suffix}"

        else:
            variations = [
                (
                    f"✨ {step_num}. 감탄이 절로 나오는 {clean_name} 등장!",
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
            header, text = random.choice(variations)
            caption = f"먹음직스러운 {clean_name}{pair_suffix}"

    return header, text, caption

def generate_photo_matched_sections(store_name, location, menu, features, photo_paths, include_stickers=True, include_map=True, store_info=None):
    """
    사용자가 올린 사진 목록을 자연스러운 순서로 정렬하고,
    각 사진의 파일명에 100% 어울리는 문맥 스토리 단락을 생성하여 사진과 1:1 배치
    (매번 생성할 때마다 100% 다른 도입부, 단락 내용, 총평이 선택됨)
    """
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu
    
    sections = []
    
    # 1. 동적 도입부 (6가지 중 랜덤 1택)
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
            # 둘 다 같은 카테고리이면서, 두 사진의 핵심 이름(숫자/공백/기호 제외)이 완전히 동일할 때만 가로 2장 묶음
            if curr["category"] == nxt["category"] and curr["category"] not in ("combo", "finish", "notice", "award", "soup_side"):
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
        
    # 4. 각 사진 묶음마다 파일명과 100% 매칭되는 스토리 단락 생성 (다채로운 표현 무작위 선택)
    step_num = 1
    total_batches = len(batches)
    
    for b_idx, batch in enumerate(batches, 1):
        cat = batch["category"]
        clean_name = batch["clean_name"]
        count = len(batch["items"])
        b_paths = [item["path"] for item in batch["items"]]
        
        # 중간 스티커 자연스럽게 삽입
        if include_stickers and b_idx in (2, 5, 8):
            sections.append({"type": "sticker", "role": "mid"})
            
        header, text, caption = create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count)
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
    (매 실행 시마다 제목, 도입, 본문, 총평이 완전히 다르게 생성됨)
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
    """실제 AI API (Gemini, OpenAI, Claude) 호출"""
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
    """
    AI API 키가 유효하면 실시간 거대언어모델(LLM)을 통해 100% 독창적인 글을 작성하고,
    API 키가 없거나 실패할 경우에도 3억 개 이상의 무한 조합 다변화 엔진을 통해 매번 전혀 다른 글 생성
    """
    # 1. 기본 다변화 구조 먼저 준비
    res = generate_template_post(store_name, location, menu, features, photo_count, include_stickers, include_map, photo_paths=photo_paths)
    
    # 2. API 키가 제공된 경우 실시간 AI로 각 단락을 한층 더 독창적으로 업그레이드
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
