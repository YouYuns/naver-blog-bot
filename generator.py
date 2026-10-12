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

def create_story_for_photo_batch(step_num, cat, clean_name, store_name, location, main_menu, count):
    """
    각 사진(또는 2장 묶음)의 파일명에서 추출한 주제(clean_name)를 바탕으로
    1:1 완벽하게 매칭되는 생생하고 다정한 블로그 본문 및 헤더 생성
    """
    is_pair = count > 1
    pair_suffix = " (가로 나란히)" if is_pair else ""

    if cat == "exterior":
        header = f"📍 {step_num}. 멀리서도 한눈에 띄는 {store_name} {clean_name}!"
        text = (
            f"{location}에 도착해서 가장 먼저 마주한 {clean_name} 모습이에요! ✨\n\n"
            f"감각적인 간판과 활기찬 매장 입구 덕분에 초행길인데도 헤매지 않고 바로 찾을 수 있었는데요!\n\n"
            f"입구에서부터 맛집 특유의 활기와 맛있는 냄새가 솔솔 풍겨와서 들어가기 전부터 가슴이 두근두근 설렜답니다 😋"
        )
        caption = f"{store_name} {clean_name}{pair_suffix}"

    elif cat == "waiting":
        header = f"⏳ {step_num}. 줄서는 핫플 인증! 현장 {clean_name} 등록!"
        text = (
            f"소문난 핫플답게 도착하자마자 현장에서 마주한 {clean_name} 모습이에요! 📋\n\n"
            f"워낙 인기가 많은 곳이라 대기가 필수라는 소문을 들었는데, 현장 대기 시스템 덕분에 생각보다 순서가 빠르게 돌아오더라고요!\n\n"
            f"기다리는 동안 기대감이 두 배로 차올라서 설레는 마음으로 입장 순서를 기다렸답니다 ✨"
        )
        caption = f"{store_name} 현장 {clean_name}{pair_suffix}"

    elif cat == "award":
        header = f"🏆 {step_num}. 맛집 인증! 시선을 사로잡는 {clean_name}!"
        text = (
            f"매장에 들어서자마자 시선을 사로잡은 영롱한 {clean_name} 사진이에요! 🏆✨\n\n"
            f"벽면에 당당하게 걸려있는 미쉐린 가이드/블루리본 등 공인된 맛집 인증 마크를 직접 눈으로 확인하니, 들어서자마자 '아, 여긴 찐이다!' 하는 확신이 절로 생겼는데요!\n\n"
            f"수많은 미식가들과 손님들에게 꾸준히 인정받아 온 곳답게, 음식 맛에 대한 신뢰도와 기대감이 최고조로 올라갔답니다 👍"
        )
        caption = f"{store_name} 신뢰를 더해주는 {clean_name}{pair_suffix}"

    elif cat == "interior":
        header = f"🌿 {step_num}. 아늑하고 정갈한 {clean_name} 분위기!"
        text = (
            f"매장 문을 열고 안으로 들어서서 담아본 {clean_name} 사진이에요! 🌿\n\n"
            f"따뜻하고 은은한 조명에 테이블 간격도 널찍널찍해서 일행과 편안하게 대화 나누며 식사하기 딱 좋은 분위기였어요!\n\n"
            f"매장 구석구석 위생도 아주 청결하게 관리되고 있어서 데이트나 친구들 모임, 가족 외식 장소로도 손색이 없겠더라고요 ✨"
        )
        caption = f"{store_name} 아늑한 {clean_name}{pair_suffix}"

    elif cat == "notice":
        header = f"📌 {step_num}. 매장 방문 필수 꿀팁! {clean_name} 안내!"
        text = (
            f"매장 이용 전 꼭 확인해야 할 {clean_name} 안내 사진이에요! 💡\n\n"
            f"워낙 많은 손님들이 찾는 소문난 인기 맛집인 만큼, 모든 분들이 쾌적하고 원활하게 식사를 즐길 수 있도록 식사 시간 및 주문 관련 에티켓이 친절하게 안내되어 있었는데요!\n\n"
            f"방문하시기 전에 이런 이용 수칙들을 미리 알아두시면 기다림이나 혼선 없이 훨씬 더 여유롭고 기분 좋게 식사를 즐기실 수 있을 것 같아요 📌"
        )
        caption = f"{store_name} {clean_name} 이용 안내{pair_suffix}"

    elif cat == "menu":
        header = f"📋 {step_num}. 정갈한 {clean_name} 정독 & 대표 시그니처 주문!"
        text = (
            f"자리에 앉아 꼼꼼하게 정독해 본 {clean_name} 사진이에요! 📋\n\n"
            f"대표 인기 메뉴인 {main_menu}를 필두로, 취향에 맞게 즐길 수 있는 다채로운 메뉴 구성이 알차게 준비되어 있었는데요!\n\n"
            f"푸짐한 퀄리티 대비 가격대도 아주 합리적이어서 망설임 없이 대표 시그니처 메뉴들로 빠르게 주문을 완료했답니다 🍽️"
        )
        caption = f"{store_name} 정갈한 {clean_name} 구성 안내{pair_suffix}"

    elif cat == "soup_side":
        header = f"🥣 {step_num}. 깊고 진한 국물 맛이 일품인 기본 {clean_name}!"
        text = (
            f"메인 요리와 함께 정갈하게 차려져 나온 기본 {clean_name} 사진이에요! 🥣✨\n\n"
            f"뚝배기/그릇에 담겨 나온 따끈한 국물을 한 숟가락 먼저 떠먹어 보았는데, 푹 끓여내어 깊고 진한 육수의 감칠맛과 부드러운 고기가 어우러져 속을 확 풀어주더라고요!\n\n"
            f"메인 요리를 먹는 중간중간 곁들이니 입안을 개운하게 정돈해 주는 최고의 기본 찬이었답니다 👍"
        )
        caption = f"깊고 진한 풍미의 {clean_name}{pair_suffix}"

    elif cat == "sides":
        header = f"🥗 {step_num}. 정갈하고 푸짐한 {clean_name} 등장!"
        text = (
            f"주문하고 얼마 지나지 않아 정갈하게 차려진 {clean_name} 사진이에요! 🥢\n\n"
            f"사진에 보이는 것처럼 메인 요리의 감칠맛을 배가시켜줄 알찬 밑반찬들이 정성스럽게 세팅되었는데요!\n\n"
            f"하나하나 간도 딱 맞고 재료의 신선함이 그대로 살아있어서 메인 요리가 나오기도 전에 젓가락질을 멈출 수 없었답니다 😋"
        )
        caption = f"정갈하고 푸짐한 {clean_name}{pair_suffix}"

    elif cat == "detail":
        header = f"📸 {step_num}. 윤기 좌르르! {clean_name} 초근접 디테일 컷!"
        text = (
            f"디테일을 더 생생하게 보여드리고 싶어서 초근접 클로즈업으로 담아본 {clean_name} 사진이에요! 📸\n\n"
            f"사진으로도 촉촉하게 흐르는 윤기와 부드러운 결이 생생하게 느껴지시죠?\n\n"
            f"좋은 식재료만 엄선해서 정성껏 차려내셨다는 게 한 점 맛볼 때마다 온몸으로 전해질 만큼 극상의 퀄리티를 자랑했답니다 👍"
        )
        caption = f"윤기 좌르르 흐르는 {clean_name} 초근접 컷{pair_suffix}"

    elif cat == "combo":
        if any(k in clean_name for k in ["비빈", "비벼", "비비는", "비벼진", "비벼먹", "섞은", "섞인"]):
            header = f"💡 {step_num}. 쓱쓱 맛있게 비벼서 한 입 가득! {clean_name}!"
            text = (
                f"숟가락과 젓가락으로 골고루 맛있게 비벼낸 {clean_name} 사진이에요! 🥣✨\n\n"
                f"고소한 특제 양념과 신선한 재료, 아삭한 채소와 밥알이 한데 어우러져 한 숟가락 가득 떠먹는 순간 입안에서 감칠맛이 폭발하듯 퍼졌는데요!\n\n"
                f"입에 착착 감기는 꿀맛이라 숟가락질을 멈출 수 없을 정도로 행복한 맛이었답니다 🥰 꼭 이렇게 골고루 비벼서 드셔보세요!"
            )
            caption = f"골고루 맛있게 비벼낸 {clean_name}{pair_suffix}"
        else:
            header = f"💡 {step_num}. 사진처럼 두 배 더 맛있게 즐기는 {clean_name} 꿀조합!"
            text = (
                f"사진에 보이는 것처럼 두 배 더 맛있게 즐기는 특급 조합이에요! 💖\n\n"
                f"준비된 특제 양념장에 콕 찍거나 정갈한 곁들임 찬과 함께 곁들여 한 입 가득 맛보았는데요!\n\n"
                f"입안에서 고소함과 감칠맛이 폭발하듯 어우러져서 진실의 미소가 절로 지어졌답니다 🥰 이렇게 꼭 드셔보시길 강력 추천해요!"
            )
            caption = f"두 배 더 맛있게 즐기는 환상의 {clean_name}{pair_suffix}"

    elif cat == "sub_dish":
        header = f"🍜 {step_num}. 놓칠 수 없는 든든한 별미! {clean_name}까지 완벽!"
        text = (
            f"메인 요리와 함께 곁들이기 위해 주문한 {clean_name} 사진이에요! 🍜\n\n"
            f"사진처럼 푸짐하고 먹음직스러운 비주얼을 자랑하며 식사의 완성도를 한층 더 높여주었는데요!\n\n"
            f"메인 요리와의 궁합도 찰떡이라 마지막 한 숟가락까지 감탄하며 든든하게 즐겼답니다 ✨"
        )
        caption = f"푸짐하고 맛깔스러운 {clean_name}{pair_suffix}"

    elif cat == "finish":
        if any(k in clean_name for k in ["영수증", "계산"]):
            header = f"🧾 {step_num}. 내돈내산 찐인증! {clean_name} 확인!"
            text = (
                f"기분 좋게 식사를 마치고 담아본 솔직 담백 {clean_name} 사진이에요! 🧾✨\n\n"
                f"돈이 전혀 아깝지 않을 만큼 양도 푸짐하고 퀄리티도 훌륭해서 일행 모두 대만족하며 계산을 마쳤답니다!\n\n"
                f"진짜 내돈내산으로 다녀와서 자신 있게 추천할 수 있는 찐맛집이에요 👍"
            )
            caption = f"{store_name} 솔직 내돈내산 {clean_name}{pair_suffix}"
        else:
            header = f"🍚 {step_num}. 국물 한 방울 남기지 않고 싹 비운 완식!"
            text = (
                f"사진에 보이는 것처럼 마지막 한 점, 국물 한 방울 남기지 않고 깔끔하게 싹 비워낸 모습이에요! 🍽️\n\n"
                f"배도 든든하게 부르고 기분 좋은 포만감에 다들 행복한 미소를 감추지 못했답니다!\n\n"
                f"정말 '인생 맛집'이라는 타이틀이 전혀 아깝지 않을 만큼 감동적인 한 끼였어요 ✨"
            )
            caption = f"배부르고 만족스럽게 비워낸 식사 마무리{pair_suffix}"

    else:
        # 특정 요리/음식 (dish) - 파일명에 적힌 음식 종류 및 사이즈에 맞게 정밀 맞춤 묘사
        c_lower = clean_name.lower()
        if any(k in c_lower for k in ["특", "대", "곱배기"]) and any(w in c_lower for w in ["비빔밥", "육회", "밥", "덮밥"]):
            header = f"🥣 {step_num}. 육회가 산더미처럼 푸짐한 {clean_name} 등장!"
            text = (
                f"기다리던 오늘의 하이라이트! 사진 속 푸짐한 {clean_name} 비주얼 보이시나요? 🥣✨\n\n"
                f"'특' 사이즈답게 신선하고 영롱한 붉은빛의 한우 육회가 밥이 보이지 않을 정도로 그릇 가득 산더미처럼 올려져 나왔는데요!\n\n"
                f"파릇파릇 향긋한 채소와 육회의 푸짐한 비율에 먹기 전부터 감탄사가 절로 쏟아졌답니다 💖"
            )
            caption = f"육회가 아낌없이 듬뿍 올라간 {clean_name}{pair_suffix}"
        elif any(k in c_lower for k in ["보통", "일반"]) and any(w in c_lower for w in ["비빔밥", "육회", "밥", "덮밥"]):
            header = f"🥣 {step_num}. 완벽한 밸런스를 자랑하는 {clean_name} 등장!"
            text = (
                f"정갈하고 알찬 구성으로 테이블에 차려진 {clean_name} 사진이에요! 🥣✨\n\n"
                f"신선한 육회의 고운 때깔과 향긋한 미나리가 정갈하게 어우러져 비주얼부터 침샘을 무한 자극했는데요!\n\n"
                f"부담 없이 한 끼 든든하게 즐기기에 딱 좋은 완벽한 양과 환상적인 밸런스를 자랑했답니다 😋"
            )
            caption = f"정갈한 비주얼의 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["육회비빔밥", "비빔밥"]):
            header = f"🥣 {step_num}. 신선한 육회와 향긋한 미나리의 특급 조화, {clean_name}!"
            text = (
                f"테이블을 풍성하게 채워준 오늘의 든든한 주인공, {clean_name} 사진이에요! 🥣✨\n\n"
                f"아낌없이 올라간 신선한 육회와 파릇파릇한 채소, 고소한 참기름 냄새가 먹기 전부터 침샘을 무한 자극했는데요!\n\n"
                f"재료 하나하나의 신선도가 눈으로도 고스란히 전해질 만큼 영롱한 비주얼을 뽐내고 있었답니다 💖"
            )
            caption = f"먹음직스러운 {clean_name} 비주얼{pair_suffix}"
        elif "수육" in c_lower and any(w in c_lower for w in ["전골", "탕", "냄비", "육수"]):
            header = f"🍲 {step_num}. 야들야들한 수육과 깊은 육수의 환상 조화, {clean_name}!"
            text = (
                f"보글보글 끓어오르는 비주얼이 예술인 {clean_name} 사진이에요! 🍲✨\n\n"
                f"맑고 깊은 육수 위에 얇고 부드럽게 삶아진 한우 수육과 향긋한 채소가 산더미처럼 푸짐하게 올려져 나왔는데요!\n\n"
                f"한 점 집어서 국물과 함께 맛보았는데, 잡내 하나 없이 야들야들 녹아내리는 수육의 육질과 시원하고 깊은 국물의 조화가 감탄 그 자체였답니다 💖"
            )
            caption = f"야들야들하고 깊은 맛의 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["곰탕", "국밥", "탕", "찌개", "전골", "국물"]):
            header = f"🍲 {step_num}. 맑고 깊은 국물이 예술인 {clean_name} 등장!"
            text = (
                f"드디어 테이블에 등장한 {clean_name} 비주얼이에요! 🍲✨\n\n"
                f"뚝배기 가득 푸짐하게 담겨 나와 코끝을 스치는 진하고 구수한 향기에 다들 감탄사를 터뜨렸는데요!\n\n"
                f"맑고 깊은 국물에 부드러운 고기가 아낌없이 듬뿍 들어가 있어서, 한 숟가락 떠먹는 순간 속이 확 풀리면서 온몸이 사르르 녹아내리는 기분이었답니다 💖"
            )
            caption = f"맑고 깊은 국물의 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["수육", "고기", "삼겹", "갈비", "목살", "한우", "스테이크", "구이", "족발", "보쌈"]):
            header = f"🥩 {step_num}. 야들야들 육즙 폭발! {clean_name} 등장!"
            text = (
                f"드디어 기다리던 오늘의 하이라이트, {clean_name} 사진이에요! 🥩✨\n\n"
                f"사진에 보이는 것처럼 두툼하면서도 결이 살아있는 비주얼이 정말 대박이었는데요!\n\n"
                f"한 점 집어서 맛보는 순간 부드럽게 씹히는 육질과 입안 가득 팡팡 터지는 고소한 육즙의 향연에 감탄사가 절로 나왔답니다 😋"
            )
            caption = f"육즙 가득한 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["회", "사시미", "방어", "연어", "참치", "광어", "초밥", "해물"]):
            header = f"🐟 {step_num}. 영롱한 때깔과 찰진 식감! {clean_name} 등장!"
            text = (
                f"선홍빛의 영롱한 때깔과 찰진 기름기가 좔좔 흐르는 {clean_name} 비주얼이에요! ✨\n\n"
                f"접시 가득 빈틈없이 빼곡하게 담겨 나오는 모습에 다들 카메라부터 들고 사진 찍기 바빴는데요!\n\n"
                f"와사비 살짝 얹어서 맛보았는데, 입안에 넣자마자 쫀득하게 감기며 사르르 녹아내리는 고소함이 일품이었답니다 💖"
            )
            caption = f"신선하고 찰진 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["비빔밥", "밥", "덮밥", "볶음밥", "솥밥"]):
            header = f"🥣 {step_num}. 고소함과 풍미 가득한 {clean_name} 등장!"
            text = (
                f"테이블을 풍성하게 채워준 오늘의 든든한 주인공, {clean_name} 사진이에요! 🥣✨\n\n"
                f"아낌없이 올라간 신선한 고명과 고소한 참기름 냄새가 먹기 전부터 침샘을 무한 자극했는데요!\n\n"
                f"쓱쓱 비벼서 한 숟가락 가득 떠먹으니 다채로운 재료들의 식감이 완벽한 조화를 이루었답니다 😋"
            )
            caption = f"풍미 가득한 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["칼국수", "라면", "파스타", "면", "우동", "국수"]):
            header = f"🍜 {step_num}. 쫄깃탱글한 면발이 일품인 {clean_name} 등장!"
            text = (
                f"뜨끈한 김과 함께 푸짐하게 차려져 나온 {clean_name} 사진이에요! 🍜✨\n\n"
                f"탱글탱글 쫄깃한 면발에 진한 육수와 양념이 쏙쏙 배어들어 있어서 후루룩 면치기하는 재미가 쏠쏠했는데요!\n\n"
                f"젓가락질을 멈출 수 없을 만큼 중독성 넘치는 맛에 마지막 한 가닥까지 대만족하며 즐겼답니다 💖"
            )
            caption = f"쫄깃탱글한 {clean_name}{pair_suffix}"
        elif any(w in c_lower for w in ["파전", "전", "튀김", "피자", "버거", "카츠", "치킨"]):
            header = f"🍕 {step_num}. 겉바속촉 극상의 바삭함! {clean_name} 등장!"
            text = (
                f"노릇노릇 바삭하게 구워져 나온 {clean_name} 사진이에요! 🍽️✨\n\n"
                f"겉은 바삭하고 속은 촉촉하게 재료의 풍미가 살아있어 입에 넣자마자 바사삭 소리와 함께 감탄이 절로 나왔는데요!\n\n"
                f"재료를 아낌없이 담아 정성껏 부쳐내신 덕분에 마지막 한 조각까지 대만족하며 즐겼답니다 😋"
            )
            caption = f"바삭한 풍미의 {clean_name}{pair_suffix}"
        else:
            header = f"✨ {step_num}. 감탄이 절로 나오는 {clean_name} 등장!"
            text = (
                f"드디어 등장한 오늘의 하이라이트! 사진 속 먹음직스러운 {clean_name} 비주얼 보이시나요? 🍽️✨\n\n"
                f"테이블에 놓이자마자 군침 도는 냄새와 푸짐한 담음새에 다들 감탄사를 연발했는데요!\n\n"
                f"좋은 식재료를 아낌없이 사용하셔서 한 입 맛볼 때마다 깊은 풍미와 신선한 식감이 그대로 전해졌답니다 😋"
            )
            caption = f"먹음직스러운 {clean_name} 비주얼{pair_suffix}"

    return header, text, caption

def generate_photo_matched_sections(store_name, location, menu, features, photo_paths, include_stickers=True, include_map=True, store_info=None):
    """
    사용자가 올린 사진 목록을 자연스러운 순서로 정렬하고,
    각 사진의 파일명에 100% 어울리는 문맥 스토리 단락을 생성하여 사진과 1:1 배치
    """
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu
    
    sections = []
    
    # 1. 도입부
    intro_p = (
        f"안녕하세요 잇님들! 맛있는 곳이라면 어디든 찾아가는 맛집 탐방러예요! 😋\n\n"
        f"오늘은 SNS에서 정말 핫하고 친구들도 입을 모아 극찬했던 {location} 맛집, '{store_name}'에 다녀온 솔직 후기를 들려드릴게요!\n\n"
        f"평소에 {main_menu}를 너무 좋아해서 벼르고 벼르다가 방문했는데요! "
        f"기대한 것보다 훨씬 더 만족스러워서 카메라에 사진을 잔뜩 담아왔답니다 ✨\n\n"
        f"사진과 함께 생생한 방문기 시작하기 전에, 매장 상세 정보와 위치부터 먼저 위에 싹 정리해 드릴게요!"
    )
    sections.append({
        "type": "text",
        "header": f"✨ {location} 핫플! {store_name} 솔직 방문기!",
        "content": intro_p
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
            # 예: '외관1' & '외관2' -> 핵심명 '외관'으로 동일하여 가로 2장 나란히 배치
            # 단, '육회비빔밥보통' vs '육회비빔밥특' 등 서로 다른 메뉴/사이즈는 각각 전용 단락과 함께 1:1 독립 배치!
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
        
    # 4. 각 사진 묶음마다 파일명과 100% 매칭되는 스토리 단락 생성
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

    # 5. 총평 & 재방문 의사
    summary_p1 = (
        f"맛, 신선함, 친절한 서비스, 분위기까지 무엇 하나 빠짐없이 대만족이었던 {location} '{store_name}'! 💖\n\n"
        f"특별한 날 소중한 사람들과 맛있는 추억을 쌓기에도 제격이고, 지친 하루를 맛있는 음식으로 힐링하기에 더할 나위 없는 곳이었어요!\n"
        f"저는 앞으로도 무조건 재방문할 생각입니다!"
    )
    summary_p2 = (
        f"📌 매장 방문 핵심 요약!\n"
        f"- 상호명 : {store_name}\n"
        f"- 대표 메뉴 : {menu} (강력 추천!)\n"
        f"- 분위기 : 아늑함, 청결함, 모임 및 데이트 최적!\n"
        f"- 재방문 의사 : 200% 강력 추천해요!\n\n"
        f"오늘 제 솔직후기가 {location} 맛집을 찾으시는 분들께 알찬 도움이 되었길 바라요 🥰\n"
        f"도움이 되셨다면 공감 하트랑 따뜻한 댓글 부탁드려요! 이웃 추가도 언제나 환영합니다! 감사합니다 ✨"
    )
    sections.append({
        "type": "text",
        "header": "💖 총평 & 재방문 의사 200%예요!",
        "content": f"{summary_p1}\n\n{summary_p2}"
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
    """
    menu_items = [m.strip() for m in re.split(r'[,/&+\s]+', menu) if m.strip()]
    main_menu = menu_items[0] if menu_items else menu

    title_patterns = [
        f"[{location} 맛집] {store_name} 솔직후기! {main_menu} 제대로 즐기고 왔어요! ✨",
        f"{location} {main_menu} 맛집 '{store_name}' 내돈내산 찐후기! 감탄하고 온 솔직 후기! 😋",
        f"드디어 다녀온 {location} 핫플 {store_name}! 입소문난 {main_menu} 먹고 완전 반했어요! 👍",
        f"[{location} 데이트 추천] 분위기까지 대만족했던 {main_menu} 맛집 {store_name} 다녀온 후기! 💖",
        f"{location} 인생 맛집 등극! {store_name} 대표메뉴 {main_menu}부터 꿀조합 팁까지 싹 정리했어요! 🍽️"
    ]
    title = random.choice(title_patterns)

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
        intro_p = (
            f"안녕하세요 잇님들! 맛있는 곳이라면 어디든 찾아가는 맛집 탐방러예요! 😋\n\n"
            f"오늘은 SNS에서 정말 핫하고 친구들도 강력 추천했던 {location} 맛집, '{store_name}'에 다녀왔어요!\n\n"
            f"평소에 {main_menu}를 너무 좋아해서 벼르고 벼르다가 방문했는데요! 정갈한 분위기와 기대 이상의 퀄리티에 대만족하고 돌아왔답니다 ✨"
        )
        sections.append({"type": "text", "header": f"✨ {location} 핫플 {store_name} 방문기!", "content": intro_p})
        if store_info:
            from store_crawler import format_store_info_section
            sections.append({"type": "text", "header": "📌 매장 상세 정보", "content": format_store_info_section(store_info)})
        if include_map:
            sections.append({"type": "map", "query": store_name, "location_name": f"{location} {store_name}"})

    tags = build_rich_hashtags(store_name, location, menu, features)

    return {
        "title": clean_markdown_artifacts(title),
        "sections": sections,
        "tags": tags
    }

def generate_ai_post(api_key, api_provider, store_name, location, menu, features, photo_count=5, include_stickers=True, include_map=True, photo_paths=None):
    res = generate_template_post(store_name, location, menu, features, photo_count, include_stickers, include_map, photo_paths=photo_paths)
    for s in res["sections"]:
        if s.get("type") == "text":
            s["content"] = clean_markdown_artifacts(s["content"])
            s["header"] = clean_markdown_artifacts(s["header"])
    return res
