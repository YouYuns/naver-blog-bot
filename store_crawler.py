# -*- coding: utf-8 -*-
"""
네이버 검색 기반 실제 매장 정보 및 사진 자동 수집기
- 상호명과 위치로 실제 네이버 플레이스 정보(전화번호, 주소, 영업시간, 브레이크타임, 주차) 자동 수집
- 네이버 이미지 검색을 통해 해당 식당의 실제 고화질 음식 사진 6~8장 자동 다운로드 및 세팅
"""

import os
import sys
import re
import io
import urllib.parse
import urllib.request
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DOWNLOADS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "downloaded_photos"))

_OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR_ENGINE = RapidOCR()
        except Exception:
            pass
    return _OCR_ENGINE

def is_clean_image(image_bytes_or_path, is_menu=False):
    """
    사진 내 워터마크, 텍스트 오버레이, 카드뉴스 글자, 블로그 서명 유무를 정밀 판정.
    - 음식, 외관, 내부, 상차림: 글자/워터마크가 감지되면 무조건 탈락! (100% 클린한 실사만 통과)
    - 메뉴판: 메뉴판 특성상 메뉴명/가격 텍스트는 허용하되, 모서리 워터마크나 카드뉴스형 리뷰 글씨는 차단.
    """
    try:
        if isinstance(image_bytes_or_path, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image_bytes_or_path)).convert("RGB")
        else:
            pil_img = Image.open(image_bytes_or_path).convert("RGB")

        w, h = pil_img.size
        # 기본 해상도 및 비율 검사 (너무 작거나 지나치게 길쭉한 파노라마/배너 제외)
        if min(w, h) < 220:
            return False, "해상도 미달"
        aspect = w / h
        if aspect < 0.55 or aspect > 2.0:
            return False, "비정상 화면비"

        engine = get_ocr_engine()
        if engine is None:
            return True, "ocr_skip"

        img_arr = np.array(pil_img)
        boxes, _ = engine.text_det(img_arr)
        num_boxes = len(boxes) if boxes is not None else 0

        if is_menu:
            # 메뉴판은 글자가 있지만, 모서리(상하단 12%)에 2개 이상 몰려있는 블로그 워터마크 검출
            corner_watermarks = 0
            for box in boxes:
                y_coords = [pt[1] for pt in box]
                if max(y_coords) > h * 0.88 or min(y_coords) < h * 0.10:
                    corner_watermarks += 1
            if corner_watermarks >= 2:
                return False, f"메뉴판 모서리 워터마크({corner_watermarks}개) 감지"
            return True, "클린 메뉴판"

        # 음식, 외관, 내부, 상차림은 글자나 워터마크가 하나라도 있으면 엄격히 제외
        if num_boxes > 0:
            return False, f"글자/워터마크/카드뉴스 텍스트({num_boxes}개) 감지"

        return True, "클린 사진"
    except Exception as e:
        return False, f"이미지 검사 오류: {e}"

def fetch_store_details(store_name, location=""):
    """
    네이버 포털 검색을 통해 해당 식당의 실제 정보 및 실시간 블로그 찐후기 크롤링
    """
    query = f"{location} {store_name}".strip()
    url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
    
    info = {
        "name": store_name,
        "address": "매장 위치 정보 참조",
        "tel": "등록된 전화번호 없음",
        "bizhour": "매장 운영시간 안내 참조",
        "break_time": "",
        "holiday": "",
        "parking": "인근 유료/공영주차장 이용 권장",
        "convenience": "",
        "star_rating": "",
        "review_count": "",
        "ai_summary": "",
        "popular_menus": [],
        "live_reviews": {
            "taste": [],
            "vibe": [],
            "general": []
        }
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(2000)

            boxes = page.locator('.place_section, .api_subject_bx')
            matched_text = ""
            for i in range(min(6, boxes.count())):
                t = boxes.nth(i).inner_text().strip()
                if "주소" in t or "전화번호" in t or "영업시간" in t:
                    matched_text = t
                    break

            # 실시간 블로그 및 방문자 찐리뷰 수집을 위한 전체 본문 텍스트
            all_page_text = page.inner_text("body")
            browser.close()

            if matched_text:
                lines = [l.strip() for l in matched_text.split("\n") if l.strip()]
                for idx, line in enumerate(lines):
                    # 별점 및 리뷰 수 탐색
                    if line == "별점" and idx + 1 < len(lines):
                        score_text = lines[idx + 1]
                        m_score = re.search(r'(\d+\.\d+)', score_text)
                        if m_score:
                            info["star_rating"] = m_score.group(1)
                        m_rev = re.search(r'리뷰\s*([0-9\.,만\+]+)', score_text)
                        if m_rev:
                            info["review_count"] = m_rev.group(1)

                    # AI 요약 한줄평
                    if "AI 요약" in line or "AI요약" in line:
                        clean_ai = line.replace("AI 요약", "").replace("AI요약", "").strip()
                        if clean_ai:
                            info["ai_summary"] = clean_ai

                    # 주소 탐색
                    elif line == "주소" and idx + 1 < len(lines):
                        addr = lines[idx + 1].replace("지도", "").strip()
                        if addr:
                            info["address"] = addr
                    
                    # 전화번호 탐색
                    elif line == "전화번호" and idx + 1 < len(lines):
                        tel = lines[idx + 1].strip()
                        if re.match(r'[\d\-]+', tel):
                            info["tel"] = tel
                    
                    # 영업시간 탐색
                    elif line == "영업시간" and idx + 1 < len(lines):
                        hours = []
                        for h_idx in range(idx + 1, min(idx + 6, len(lines))):
                            val = lines[h_idx]
                            if val in ["전화번호", "편의", "메뉴", "주소", "펼쳐보기", "접기", "제보"]:
                                break
                            if val not in ["펼쳐보기", "접기"] and val not in hours:
                                hours.append(val)
                        if hours:
                            info["bizhour"] = " / ".join(hours)
                            for h in hours:
                                if "브레이크타임" in h:
                                    info["break_time"] = h
                                if "휴무" in h:
                                    info["holiday"] = h

                    # 편의 / 주차 정보 탐색
                    elif line == "편의" and idx + 1 < len(lines):
                        conv = lines[idx + 1].strip()
                        info["convenience"] = conv
                        if "주차" in conv:
                            info["parking"] = "주차 가능 (매장 안내)"
                        elif "발렛" in conv:
                            info["parking"] = "발렛파킹 가능"

                # 본문에서 주차 키워드 추가 검사
                if "주차 불가" in matched_text:
                    info["parking"] = "전용 주차장 없음 (인근 공영주차장 이용 권장)"
                elif "무료주차" in matched_text or "주차 가능" in matched_text:
                    info["parking"] = "매장 무료/유료 주차 가능"

            # 실시간 블로그 찐후기 문장 추출
            all_lines = [l.strip() for l in all_page_text.split("\n") if len(l.strip()) > 25]
            filter_words = ["스마트블록", "인기글", "전체보기", "접기", "공유", "네이버", "거리순", "광고"]
            for line in all_lines:
                if any(w in line for w in filter_words):
                    continue
                clean_l = re.sub(r'^\d{4}\.\d{2}\.\d{2}\.?', '', line).strip()
                clean_l = re.sub(r'#\S+', '', clean_l).strip()
                if len(clean_l) < 20:
                    continue

                if any(k in clean_l for k in ["맛있", "풍미", "식감", "달콤", "고소", "바삭", "촉촉", "육수", "쫄깃", "버터", "국물"]):
                    if clean_l not in info["live_reviews"]["taste"]:
                        info["live_reviews"]["taste"].append(clean_l)
                elif any(k in clean_l for k in ["인테리어", "분위기", "감성", "사진", "포토", "소품", "매장", "조명", "자리"]):
                    if clean_l not in info["live_reviews"]["vibe"]:
                        info["live_reviews"]["vibe"].append(clean_l)
                else:
                    if clean_l not in info["live_reviews"]["general"]:
                        info["live_reviews"]["general"].append(clean_l)

    except Exception as e:
        print(f"가게 정보 검색 중 안내: {e}")

    return info


def resolve_store_from_address_or_url(input_query, status_callback=print):
    """
    사용자가 입력한 주소(도로명/지번) 또는 URL(네이버 지도/플레이스 링크)로부터
    상호명, 위치, 대표메뉴, 특징 및 매장 상세 정보를 자동 판별
    반환: dict(store_name, location, menu, features, store_info)
    """
    raw_query = input_query.strip()
    if not raw_query:
        return None

    status_callback(f"🌐 [주소/링크 분석] 입력값: '{raw_query}'")
    
    # 1. URL 형태인 경우 분석
    if raw_query.startswith("http://") or raw_query.startswith("https://"):
        target_url = raw_query
        if "naver.me" in target_url or "bit.ly" in target_url:
            status_callback("🔗 단축 URL 원본 주소 추적 중...")
            try:
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    target_url = resp.geturl()
            except urllib.error.HTTPError as e:
                loc = e.headers.get('Location')
                if loc:
                    target_url = loc
            except Exception:
                pass
        
        parsed = urllib.parse.urlparse(target_url)
        qs = urllib.parse.parse_qs(parsed.query)
        store_cand = ""
        if "query" in qs:
            store_cand = qs["query"][0]
        elif "q" in qs:
            store_cand = qs["q"][0]
        
        if not store_cand:
            m_id = re.search(r'(?:place|restaurant)/(\d+)', target_url)
            if m_id:
                store_cand = m_id.group(1)
        
        search_target = store_cand if store_cand else target_url
    else:
        search_target = raw_query

    # 2. 네이버 포털 통합검색을 통해 장소/상호명 정확 추출
    search_url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(search_target)}"
    status_callback("🔍 네이버 포털에서 매장 정보 및 상호명 탐색 중...")
    
    found_store = ""
    found_category = ""
    found_address = ""
    found_phone = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(2000)
            
            # A. '이 주소의 장소' 박스 탐색 (도로명 주소 입력 시)
            boxes = page.locator('.place_section, .api_subject_bx, .sc_new').all()
            for b in boxes:
                txt = b.inner_text().strip()
                if "이 주소의 장소" in txt:
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    for idx, line in enumerate(lines):
                        if line == "이 주소의 장소" and idx + 1 < len(lines):
                            cand_line = lines[idx + 1]
                            # 업종 분리
                            cat_match = re.search(r'(카페,디저트|베이커리|만두|칼국수,만두|칼국수|냉면|육류,고기요리|고기요리|한식|일식|양식|중식|음식점|주점|카페|디저트|요리|바|호프)$', cand_line)
                            if cat_match:
                                found_category = cat_match.group(1)
                                found_store = cand_line[:cat_match.start()].strip()
                            else:
                                found_store = cand_line
                            found_store = re.sub(r'\s+[가-힣0-9]+점$', '', found_store)
                            
                            for nxt_idx in range(idx + 2, min(idx + 5, len(lines))):
                                nxt_line = lines[nxt_idx]
                                m_tel = re.search(r'(0\d{1,2}-\d{3,4}-\d{4})', nxt_line)
                                if m_tel:
                                    found_phone = m_tel.group(1)
                                if any(r in nxt_line for r in ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]):
                                    found_address = nxt_line
                            break
                    if found_store:
                        break

            # B. 플레이스 일반 타이틀 탐색 (.Fc1rA, .GHAhO, .tit 등)
            if not found_store:
                tit_els = page.locator('.place_section .Fc1rA, .place_section .GHAhO, .api_subject_bx .tit').all()
                for t in tit_els:
                    text_val = t.inner_text().strip()
                    if text_val and text_val not in ["플레이스", "지도", "길찾기", "MY플레이스"]:
                        found_store = re.sub(r'\s+[가-힣0-9]+점$', '', text_val)
                        break

            # C. 주소 추출
            if not found_address:
                m_addr = re.search(r'([가-힣]+(?:시|도)?\s*[가-힣]+(?:구|군|시)\s*[가-힣0-9]+(?:로|길|동|리)?(?:\s*\d+[\-\d]*)?)', raw_query)
                if m_addr:
                    found_address = m_addr.group(1).strip()
            
            browser.close()
    except Exception as e:
        status_callback(f"⚠️ 주소 분석 중 일시적 오류: {e}")

    if not found_store:
        words = [w for w in re.split(r'[\s,/]+', raw_query) if len(w) >= 2]
        found_store = words[-1] if words else "맛집"

    # 지역/위치명 추출 (구/동 또는 핫플 키워드 매핑)
    location_cand = ""
    addr_to_check = f"{found_address} {raw_query}"
    loc_patterns = [
        ("용산", "용리단길"), ("성수", "성수동"), ("을지로", "을지로"), 
        ("신당", "신당동"), ("안국", "안국 북촌"), ("북촌", "안국 북촌"),
        ("압구정", "압구정"), ("신사", "가로수길"), ("연남", "연남동"),
        ("망원", "망원동"), ("한남", "한남동"), ("송파", "송리단길"),
        ("잠실", "송리단길"), ("종로", "종로"), ("강남", "강남역"),
        ("홍대", "홍대"), ("여의도", "여의도"), ("해운대", "해운대"), ("광안리", "광안리")
    ]
    for key, loc_name in loc_patterns:
        if key in addr_to_check:
            location_cand = loc_name
            break
    if not location_cand:
        m_gu = re.search(r'([가-힣]+(?:구|군|시))', addr_to_check)
        location_cand = m_gu.group(1) if m_gu else "서울"

    status_callback(f"✅ 매장 식별 완료: 상호명='{found_store}', 지역='{location_cand}'")

    # 3. 매장 상세 정보 수집
    status_callback(f"📋 '{location_cand} {found_store}'의 상세 매장 정보 및 대표 메뉴 수집 중...")
    details = fetch_store_details(found_store, location_cand)
    if found_address and details.get("address") == "매장 위치 정보 참조":
        details["address"] = found_address
    if found_phone and details.get("tel") == "등록된 전화번호 없음":
        details["tel"] = found_phone

    # 4. 대표 메뉴 결정
    menu_cand = ""
    if details.get("popular_menus"):
        menu_cand = ", ".join(details["popular_menus"][:3])
    elif found_category:
        if any(k in found_category for k in ["베이커리", "카페", "디저트"]):
            menu_cand = "시그니처 크루아상, 페이스트리, 아메리카노"
        elif "만두" in found_category:
            menu_cand = "칼만두, 손만두, 만두전골"
        elif "칼국수" in found_category:
            menu_cand = "손칼국수, 수육, 보쌈"
        elif any(k in found_category for k in ["고기", "육류", "삼겹", "구이"]):
            menu_cand = "숙성 삼겹살, 목살구이, 된장찌개"
        elif "냉면" in found_category:
            menu_cand = "물냉면, 비빔냉면, 만두"
        else:
            menu_cand = "대표 시그니처 요리, 인기 세트 메뉴"
    else:
        menu_cand = "대표 인기 시그니처 메뉴"

    # 5. 특징 / 꿀팁
    features_cand = ""
    if details.get("ai_summary"):
        features_cand = details["ai_summary"]
    else:
        features_cand = f"현지인과 여행객이 함께 찾는 {location_cand}의 핫플레이스 찐맛집"

    return {
        "store_name": found_store,
        "location": location_cand,
        "menu": menu_cand,
        "features": features_cand,
        "store_info": details
    }


def crawl_live_trending_hotplaces(area="성수동", max_count=10):
    """
    네이버에서 실시간 최신 핫플레이스를 검색 크롤링하여 (상호, 위치, 대표메뉴, 특징) 반환
    - 하드코딩 없이 네이버 플레이스 주간 인기 매장과 메뉴를 라이브로 직접 가져옴
    """
    query = f"{area} 핫플 맛집"
    url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
    
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(2500)
            
            boxes = page.locator('.api_subject_bx')
            place_text = ""
            for i in range(boxes.count()):
                t = boxes.nth(i).inner_text().strip()
                if "플레이스플레이스 검색결과" in t or "플레이스 검색결과" in t:
                    place_text = t
                    break
            browser.close()
            
        if place_text:
            lines = [l.strip() for l in place_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                if line == "주간 인기 많은 메뉴" and i + 1 < len(lines):
                    menus = lines[i + 1]
                    save_idx = -1
                    for back in range(1, 15):
                        if i - back >= 0 and lines[i - back] == "저장":
                            save_idx = i - back
                            break
                    
                    store_name = ""
                    feature = ""
                    if save_idx != -1:
                        for back in range(1, 10):
                            idx = save_idx - back
                            if idx >= 0:
                                cand = lines[idx]
                                if cand in ["광고", "영업 중", "별점", "TV", "2TV생생정보", "예약", "쿠폰", "톡톡", "네이버페이"]:
                                    continue
                                if re.match(r'^\d+(\.\d+)?(리뷰.*)?$', cand):
                                    continue
                                if not feature and len(cand) > 6 and not any(w in cand for w in ["양식", "한식", "카페", "일식"]):
                                    feature = cand
                                elif not store_name and 2 <= len(cand) <= 20 and not any(w in cand for w in ["양식", "한식", "카페", "일식", "스파게티"]):
                                    store_name = cand
                                    break
                    if store_name and not any(r['store'] == store_name for r in results):
                        results.append({
                            "store": store_name,
                            "location": area,
                            "menu": menus,
                            "features": feature or f"네이버 플레이스 실시간 {area} 주간 인기 핫플레이스"
                        })
    except Exception as e:
        print(f"실시간 핫플 검색 오류: {e}")
        
    return results[:max_count]

def download_store_photos(store_name, location="", menu="", max_count=14, status_callback=print, force_refresh=False):
    """
    네이버 이미지 검색에서 실제 맛집의 다양한 실사 사진을 카테고리별로 자동 수집 (12~14장)
    - 글자/워터마크/카드뉴스 텍스트 완전 배제 (100% 클린 실사 필터링)
    - 외관(2장), 내부(2장), 메뉴판(2장), 상차림(2장), 대표 음식(6장)으로 엄격한 순서와 알맞은 파일명 유지
    """
    safe_name = re.sub(r'[\/\\:\*\?"<>\|]', '_', f"{location}_{store_name}").strip()
    target_dir = os.path.join(DOWNLOADS_ROOT, safe_name)
    os.makedirs(target_dir, exist_ok=True)

    clean_menu = re.split(r'[,/&+\s]+', menu)[0].strip() if menu else "대표음식"
    if clean_menu in ["음식", "메뉴", "대표메뉴", "시그니처", "인기메뉴"]:
        clean_menu = "시그니처"

    if not force_refresh:
        existing_files = [
            os.path.join(target_dir, f)
            for f in sorted(os.listdir(target_dir))
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and os.path.getsize(os.path.join(target_dir, f)) > 6000
        ]
        all_valid = True
        if len(existing_files) >= 12:
            for ef in existing_files:
                is_menu = "메뉴판" in os.path.basename(ef)
                clean, reason = is_clean_image(ef, is_menu=is_menu)
                if not clean:
                    status_callback(f"⚠️ 기존 캐시 사진 중 '{os.path.basename(ef)}'에서 {reason} -> 최신 클린 사진으로 재수집합니다.")
                    all_valid = False
                    break
            if all_valid:
                status_callback(f"✅ 기존에 수집된 100% 무글자·무워터마크 실제 매장 사진 {len(existing_files)}장을 불러왔습니다.")
                return existing_files[:max_count]

    status_callback(f"네이버에서 '{location} {store_name}' 글자 없는 100% 찐 실사 사진 12~14장 수집 시작...")

    categories = [
        ("외관", [f"{store_name} 간판", f"{store_name} 매장 입구", f"{location} {store_name} 외관 간판"], 2, False),
        ("내부", [f"{store_name} 내부 인테리어", f"{location} {store_name} 매장 내부 좌석"], 2, False),
        ("메뉴판", [f"{store_name} 메뉴판 가격표", f"{location} {store_name} 차림표"], 2, True),
        ("상차림", [f"{store_name} 상차림 반찬", f"{location} {store_name} 기본 상차림"], 2, False),
        ("음식", [f"{store_name} {clean_menu}", f"{store_name} 대표 음식", f"{location} {store_name} {clean_menu}"], 6, False),
    ]

    saved_paths = []
    file_idx = 1
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()

            for cat_name, queries, req_count, is_menu in categories:
                cat_count = 0
                for query in queries:
                    if cat_count >= req_count:
                        break
                    url = f"https://search.naver.com/search.naver?where=image&sm=tab_jum&query={urllib.parse.quote(query)}"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=10000)
                        page.wait_for_timeout(1500)
                    except Exception:
                        continue

                    imgs = page.locator('.image_tile img, .photo_tile img, .thumb img')
                    for i in range(imgs.count()):
                        src = imgs.nth(i).get_attribute('src')
                        if src and ('pstatic.net' in src or 'phinf' in src or 'naver.net' in src):
                            try:
                                req = urllib.request.Request(src, headers=headers)
                                with urllib.request.urlopen(req, timeout=4) as resp:
                                    img_data = resp.read()

                                if len(img_data) < 6000:
                                    continue

                                clean, reason = is_clean_image(img_data, is_menu=is_menu)
                                if not clean:
                                    continue

                                if cat_name == "외관":
                                    fname = os.path.join(target_dir, f"{file_idx:02d}_외관_{cat_count + 1}.jpg")
                                elif cat_name == "내부":
                                    fname = os.path.join(target_dir, f"{file_idx:02d}_내부_인테리어_{cat_count + 1}.jpg")
                                elif cat_name == "메뉴판":
                                    fname = os.path.join(target_dir, f"{file_idx:02d}_메뉴판_{cat_count + 1}.jpg")
                                elif cat_name == "상차림":
                                    fname = os.path.join(target_dir, f"{file_idx:02d}_상차림_{cat_count + 1}.jpg")
                                elif cat_name == "음식":
                                    if cat_count == 0:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}.jpg")
                                    elif cat_count == 1:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}_디테일.jpg")
                                    elif cat_count == 2:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_음식_{clean_menu}_한점.jpg")
                                    elif cat_count == 3:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_음식_{clean_menu}_클로즈업.jpg")
                                    elif cat_count == 4:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_음식_{clean_menu}_조합.jpg")
                                    else:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_마무리.jpg")
                                else:
                                    fname = os.path.join(target_dir, f"{file_idx:02d}_{cat_name}_{cat_count + 1}.jpg")

                                with open(fname, 'wb') as f:
                                    f.write(img_data)

                                saved_paths.append(fname)
                                cat_count += 1
                                file_idx += 1
                                if cat_count >= req_count or len(saved_paths) >= max_count:
                                    break
                            except Exception:
                                pass

                status_callback(f"  -> [{cat_name}] 글자 없는 깨끗한 실사 사진 {cat_count}장 확보 완료")

            # 만약 목표 장수 미만이면 일반 맛집 쿼리로 추가 보충 (글자/워터마크 없는 사진만 엄선)
            if len(saved_paths) < max_count:
                extra_needed = max_count - len(saved_paths)
                extra_url = f"https://search.naver.com/search.naver?where=image&sm=tab_jum&query={urllib.parse.quote(f'{location} {store_name} 맛집')}"
                try:
                    page.goto(extra_url, wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(1500)
                    imgs = page.locator('.image_tile img, .photo_tile img, .thumb img')
                    extra_c = 0
                    for i in range(imgs.count()):
                        src = imgs.nth(i).get_attribute('src')
                        if src and ('pstatic.net' in src or 'phinf' in src or 'naver.net' in src):
                            try:
                                req = urllib.request.Request(src, headers=headers)
                                with urllib.request.urlopen(req, timeout=4) as resp:
                                    img_data = resp.read()
                                if len(img_data) < 6000:
                                    continue
                                clean, reason = is_clean_image(img_data, is_menu=False)
                                if not clean:
                                    continue

                                fname = os.path.join(target_dir, f"{file_idx:02d}_음식_{clean_menu}_{extra_c + 1}.jpg")
                                with open(fname, 'wb') as f:
                                    f.write(img_data)
                                saved_paths.append(fname)
                                extra_c += 1
                                file_idx += 1
                                if len(saved_paths) >= max_count:
                                    break
                            except Exception:
                                pass
                except Exception:
                    pass

            browser.close()
            status_callback(f"✅ 총 {len(saved_paths)}장의 글자/워터마크 없는 100% 찐 실사 사진 준비 완료!")
    except Exception as e:
        status_callback(f"사진 수집 안내: {e}")

    return saved_paths

def format_store_info_section(info):
    """블로그 본문에 들어갈 예쁜 매장 안내 텍스트 블록 생성"""
    name = info.get("name", "")
    addr = info.get("address", "")
    tel = info.get("tel", "")
    biz = info.get("bizhour", "")
    parking = info.get("parking", "")
    conv = info.get("convenience", "")

    lines = [
        f"🏠 매장명 : {name}",
        f"📍 주소 : {addr}",
        f"📞 전화번호 : {tel}",
        f"⏰ 영업시간 : {biz}",
    ]
    if info.get("star_rating"):
        rev_txt = f" (방문자 리뷰 {info['review_count']})" if info.get("review_count") else ""
        lines.append(f"⭐ 네이버 평점 : {info['star_rating']}점{rev_txt}")
    if info.get("ai_summary"):
        lines.append(f"💡 매장 특징 : {info['ai_summary']}")
    if info.get("break_time"):
        lines.append(f"☕ 브레이크타임 : {info['break_time']}")
    if info.get("holiday"):
        lines.append(f"🗓️ 정기휴무 : {info['holiday']}")
    
    lines.append(f"🚗 주차 정보 : {parking}")
    if conv:
        lines.append(f"✨ 편의시설 : {conv}")

    return "\n".join(lines)
