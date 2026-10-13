# -*- coding: utf-8 -*-
"""
작성한 맛집 히스토리 관리 및 최신 핫플 맛집 데이터베이스
- 한 번 작성한 식당은 영구 기록되어 다음 추천 풀에서 자동 제외
- 캐치테이블, 네이버 플레이스, SNS 최신(2024~2026) 핫플레이스 엄선
"""

import os
import json
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "written_history.json")

# 최신 핫플레이스 / 줄서는식당 / 미쉐린 / 캐치테이블 상위 맛집 풀 (50곳)
HOT_RESTAURANT_POOL = [
    # [성수동 핫플레이스]
    ("능동미나리", "성수동", "미나리 곰탕, 미나리 수육전골", "향긋한 청도 미나리 듬뿍, 야들야들한 한우 수육, 줄서는식당 대기 1위 핫플"),
    ("난포", "성수동", "강된장 쌈밥, 제철회 묵은지말이", "정갈하고 깔끔한 퓨전 한식, 새우치즈감자전, 성수동 대표 웨이팅 맛집"),
    ("소문난성수감자탕", "성수동", "감자탕, 수제비사리, 볶음밥", "백종원의 3대천왕 방영, 24시간 우려낸 깊은 국물, 큼직하고 부드러운 살코기"),
    ("조조칼국수", "성수동", "동죽칼국수, 낙지해물파전", "신선한 산지직송 동죽조개 물총탕, 바삭바삭한 낙지해물파전, 가성비 최고"),
    ("진작다이닝", "성수동", "후토마키, 대창덮밥(호르몬동)", "압도적인 비주얼의 대왕 후토마키, 불향 가득 매콤달콤 대창덮밥, 모던 인테리어"),
    ("토라식당", "성수동", "흑돼지 돈카츠, 오므라이스", "성수 직장인 성지, 겉바속촉 흑돼지 카츠와 부드러운 일본식 달걀 오므라이스"),
    ("중앙감속기", "성수동", "차돌 마라크림 짬뽕, 발사믹 꿔바로우", "최현석 셰프의 이탈리안&차이니즈 퓨전, 크리미하고 알싸한 마라 크림"),

    # [용산 / 삼각지 / 용리단길 / 숙대]
    ("몽탄", "삼각지", "우대갈비, 짚불삼겹살", "짚불 훈연 향 가득, 살살 녹는 식감의 우대갈비, 시그니처 양파볶음밥"),
    ("쌤쌤쌤", "용리단길", "클래식 라자냐, 잠봉뵈르 파스타", "샌프란시스코 감성의 인테리어, 치즈 풍미 가득 라자냐, 오픈런 핫플레이스"),
    ("효뜨", "용리단길", "소고기 쌀국수, 분짜, 닭튀김", "베트남 로컬 야시장 분위기, 진하고 이국적인 육수, 바삭한 베트남식 치킨"),
    ("초원", "숙대입구", "한우 등심주물럭, 특상 우설", "두툼하고 쫄깃한 식감의 우설 구이, 마늘향 솔솔 특제 양념 주물럭, 시원한 냉면"),
    ("남영돈", "남영동", "항정살, 가브리살", "참숯 화로구이 육즙 폭발, 아삭아삭 쫀득한 항정살, 조개젓과 와사비 꿀조합"),
    ("꺼거", "용리단길", "원앙볶음밥, 치킨에그누들", "홍콩 노포 감성 레트로 식당, 토마토와 크림 두 가지 맛 볶음밥"),

    # [을지로 / 신당 / 힙지로]
    ("산청숯불가든", "을지로", "재래식 소금구이, 고추장양념구이", "지리산 산청 흑돼지, 숯불 직화 육즙 폭발, 쪽파와 갓김치 조합"),
    ("금돼지식당", "신당동", "본삼겹, 눈꽃목살", "미쉐린 빕구루망 선정, 풍부한 육즙과 바질 쌈 조합, 특제 파절임 소스"),
    ("하니칼국수", "신당동", "알곤이칼국수, 수육", "알과 곤이가 산더미처럼 푸짐한 칼칼 얼큰 칼국수, 야들야들한 제육 수육"),
    ("백송", "을지로", "서대살, 짝갈비", "두툼한 소고기 서대살 숯불구이, 쫄깃한 식감과 깊은 육향, 레트로 분위기"),
    ("사랑방칼국수", "을지로", "백숙백반, 닭곰탕", "반세기 전통의 을지로 노포, 촉촉하고 부드러운 백숙과 특제 초고추장 양념"),
    ("을지다락", "을지로", "다락오므라이스, 매콤크림파스타", "부드럽게 갈라지는 포슬포슬 오므라이스, 힙지로 숨은 감성 레스토랑"),

    # [압구정 / 신사 / 도산공원 / 강남]
    ("호족반", "압구정 도산공원", "들기름 메밀국수, NY 양념갈비", "퓨전 한식의 진수, 고소한 들기름 풍미, 바삭한 트러플 감자전"),
    ("런던베이글뮤지엄", "도산공원", "브릭레인 베이글, 쪽파 프레첼 베이글", "영국 감성 인테리어, 쫀득쫄깃 수제 베이글, 대파 크림치즈 꿀조합"),
    ("땀땀", "강남역", "매운 소곱창 쌀국수, 분짜", "얼큰 칼칼한 중독성 국물, 푸짐한 소곱창 토핑, 불맛 가득 불고기 쌀국수"),
    ("달마시안", "도산공원", "달마시안 브런치 플래터, 프렌치토스트", "유럽 정원 감성 꽃분수대 뷰, 촉촉한 프렌치토스트와 감성 브런치"),
    ("클랩피자", "신사 가로수길", "트러플 고르곤졸라, 콘샐러드 피자", "미국 뉴욕 스타일 피자, 토핑 아낌없이 올라간 도우, 힙한 펍 분위기"),
    ("다운타우너", "압구정 로데오", "아보카도 버거, 갈릭버터 프라이즈", "부드러운 생아보카도 슬라이스, 촉촉한 소고기 패티, 달콤 짭조름 감자튀김"),

    # [홍대 / 연남동 / 합정 / 망원]
    ("바다회사랑", "홍대 연남동", "대방어회, 해물라면", "신선하고 두툼한 대방어회 성지, 백김치 묵은지 꿀조합, 얼큰한 해물라면"),
    ("소이연남", "홍대 연남동", "소고기 쌀국수, 똠얌누들", "진하고 깊은 태국식 소고기 육수, 큼직한 아롱사태 고명, 바삭한 뽀삐아 튀김"),
    ("연남토마", "홍대 연남동", "명란 바질오일 파스타, 안심가츠", "초록 정원이 예쁜 단독주택 개조 식당, 정갈하고 담백한 퓨전 양식"),
    ("헤키", "망원동", "히레카츠 정식, 상로스카츠", "망원동 인생 돈카츠, 선홍빛 촉촉한 안심카츠와 트러플 오일, 히말라야 핑크솔트"),
    ("오레노라멘", "합정", "토리 파이탄 라멘, 카라 파이탄", "미쉐린 빕구루망, 진하고 크리미한 닭 육수 백탕, 자가제면 얇은 면발"),

    # [안국 / 북촌 / 종로 / 익선동]
    ("아티스트 베이커리", "안국역", "플레인 소금빵, 트러플 소금빵", "소금빵 웨이팅 1위 성지, 겉바속촉 쫄깃한 식감, 다양한 토핑 소금빵"),
    ("도토리 가든", "안국역", "리얼 벌집 요거트 볼, 도토리 브레드", "지브리 애니메이션 속 감성 공간, 신선한 그릭요거트와 달콤한 벌집꿀"),
    ("청수당", "종로 익선동", "수플레 카스텔라, 말차 프로마쥬", "대나무 숲과 물길 연못 정원 뷰, 주문 즉시 굽는 몽글몽글 수플레"),
    ("부촌육회", "종로 광장시장", "육회낙지탕탕이, 육회비빔밥", "미쉐린 가이드 7년 연속 선정, 찰지고 신선한 한우 육회와 꿈틀대는 산낙지"),
    ("익선애뜻", "종로 익선동", "돼지감태 주먹밥, 우삼겹 칼비빔면", "한국적인 멋과 맛이 담긴 한식, 감태로 감싼 주먹밥과 새콤매콤 칼비빔면"),
    ("깡통만두", "안국 북촌", "칼만두, 비빔국수, 모둠전", "수요미식회 방영, 손으로 빚은 속이 꽉 찬 수제 손만두와 고소한 육전"),

    # [잠실 / 송리단길 / 한남동 / 여의도]
    ("갓잇", "송리단길", "갓 파히타 세트, 타코, 버팔로윙", "줄서서 먹는 멕시칸 타코 핫플, 푸짐한 고기와 또띠아 쌈, 감각적인 플레이팅"),
    ("오스테리아 오르조", "한남동", "화이트 라구 파스타, 투뿔 안심 카르파치오", "미쉐린 가이드 선정 생면 파스타바, 트러플 오일 풍미, 기념일 데이트 추천"),
    ("미엔아이", "송리단길", "대만 우육면, 마약 꿔바로우", "진하고 담백한 대만식 소고기 우육탕면, 인절미 가루 묻힌 바삭 꿔바로우"),
    ("세상의모든아침", "여의도", "바게트 프렌치토스트, 트러플 리조또", "여의도 전경련회관 50층 환상적인 한강뷰, 인생샷 명소 브런치 다이닝"),
    ("화포식당", "한남동", "숙성 통삼겹살, 목살", "두툼한 한돈 원육, 멜젓과 명이나물 조합, 구워주는 편리함과 풍부한 육즙"),

    # [전국구 대표 핫플]
    ("해목", "부산 해운대", "특 히츠마부시(장어덮밥), 연어사시미", "나고야식 숯불 장어덮밥의 정수, 4가지 방법으로 즐기는 감칠맛"),
    ("톤쇼우", "부산 광안리", "버크셔K 특로스카츠, 히레카츠", "캐치테이블 전국 1위 돈카츠, 숯불 훈연 향과 핑크빛 육즙이 일품인 명품 카츠"),
    ("이재모피자", "부산 서면", "이재모 크러스트 피자, 치즈오븐스파게티", "임실 자연산 치즈 폭탄, 쫀득한 도우와 고소함의 극치, 부산 필수 코스"),
    ("뵈르뵈르", "성수동", "버터 아이스크림, 쿠키 샌드", "프랑스산 유지방 82% 최고급 버터로 만든 꾸덕하고 진한 버터 아이스크림 핫플"),
    ("테디뵈르하우스", "용리단길", "크루아상, 피스타치오 퀸아망", "유럽 파리 감성의 테디베어 베이커리 카페, 버터 풍미 가득 결이 살아있는 크루아상"),
    ("카츠바이콘반", "압구정 도산공원", "로스카츠, 히레카츠", "국내 돈카츠 붐을 이끈 성지, 육즙 가득 부드러운 안심과 바삭한 튀김옷"),
    ("온천집", "종로 익선동", "된장 샤브샤브, 미나리 육전", "도심 속 일본 료칸 온천 정원 무드, 정갈한 3단 도시락 샤브샤브와 고소한 육전"),
    ("양키스버거", "문래동", "문래버거, 칠리치즈 프라이", "문래 창작촌 철공소 골목의 힙한 수제버거 맛집, 육즙 가득 소고기 패티와 트러플 마요"),
    ("바오하우스", "부산 전포", "클래식 바오, 마파두부&가지튀김", "부산 전포 카페거리 줄서는 대만 요리 핫플, 촉촉한 바오 번과 감칠맛 폭발 가지튀김")
]


def load_written_history():
    """작성 완료된 식당 목록 불러오기"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("written_stores", [])
        except Exception:
            return []
    return []


def get_written_store_names():
    """작성 완료된 상호명 set 반환"""
    items = load_written_history()
    return {item.get("store", "").strip() for item in items if item.get("store")}


def add_written_store(store_name, location="", menu=""):
    """새로운 식당을 작성 완료 목록에 추가 (영구 저장)"""
    store_name = store_name.strip()
    if not store_name:
        return False

    history = load_written_history()
    for item in history:
        if item.get("store") == store_name:
            item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            item["location"] = location
            break
    else:
        history.append({
            "store": store_name,
            "location": location,
            "menu": menu,
            "written_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"written_stores": history}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"히스토리 저장 실패: {e}")
        return False


def remove_written_store(store_name):
    """특정 식당을 작성 완료 목록에서 제거 (다시 추천받을 수 있도록)"""
    history = load_written_history()
    new_history = [item for item in history if item.get("store") != store_name]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"written_stores": new_history}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def clear_written_history():
    """작성 목록 전체 초기화"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"written_stores": []}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


LIVE_CACHE_FILE = os.path.join(CURRENT_DIR, "live_hotplaces_cache.json")

def load_live_hotplaces():
    """실시간 네이버 검색으로 발굴된 핫플레이스 캐시 불러오기"""
    if os.path.exists(LIVE_CACHE_FILE):
        try:
            with open(LIVE_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("places", [])
                return [(it["store"], it["location"], it["menu"], it["features"]) for it in items]
        except Exception:
            return []
    return []

def save_live_hotplaces(places_list):
    """실시간 크롤링된 핫플레이스를 캐시에 누적 저장"""
    existing = {it[0]: it for it in load_live_hotplaces()}
    for it in places_list:
        if isinstance(it, dict):
            s = it.get("store", "")
            if s:
                existing[s] = (s, it.get("location", ""), it.get("menu", ""), it.get("features", ""))
        elif isinstance(it, (tuple, list)) and len(it) >= 4:
            existing[it[0]] = (it[0], it[1], it[2], it[3])
            
    payload = [
        {"store": v[0], "location": v[1], "menu": v[2], "features": v[3]}
        for v in existing.values()
    ]
    try:
        with open(LIVE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"places": payload}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"라이브 핫플 캐시 저장 실패: {e}")

def get_unwritten_hot_candidates(current_store=""):
    """
    아직 작성하지 않은 핫플레이스 식당 목록만 필터링하여 반환
    (실시간 네이버 크롤링으로 발굴된 최신 매장 우선 포함)
    """
    written_names = get_written_store_names()
    live_pool = load_live_hotplaces()
    
    # 실시간 수집 풀 + 기본 엄선 풀 합산 (중복 제거)
    seen = set()
    combined = []
    for item in live_pool + HOT_RESTAURANT_POOL:
        if item[0] not in seen:
            seen.add(item[0])
            combined.append(item)

    candidates = [
        p for p in combined 
        if p[0] not in written_names and p[0] != current_store
    ]
    return candidates


def get_history_stats():
    """작성 통계 반환 (총 핫플 수, 작성 완료 수, 남은 수)"""
    written = len(get_written_store_names())
    live_pool = load_live_hotplaces()
    seen = set()
    for item in live_pool + HOT_RESTAURANT_POOL:
        seen.add(item[0])
    total = len(seen)
    return {
        "total": total,
        "written": written,
        "remaining": max(0, total - written)
    }


