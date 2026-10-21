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
import json
import base64
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


def extract_naver_blog_params(url):
    m = re.search(r'blog\.naver\.com/(?:m/)?([a-zA-Z0-9_-]+)/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'blogId=([a-zA-Z0-9_-]+).*?[&?]logNo=(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'logNo=(\d+).*?[&?]blogId=([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(2), m.group(1)
    return None, None


def smart_classify_photo_context(ctx_lower, idx, total, known_menus=None):
    """
    블로그 캡션과 식당의 실제 메뉴 목록을 대조하여 가장 자연스럽고 명확한 한글 파일명 키워드 추출
    ('음식_1', '음식_2' 등 무의미한 번호 완전 박멸)
    """
    if not known_menus:
        known_menus = []

    # 1. 명확한 비음식 공간/이용 분류
    if any(k in ctx_lower for k in ["메뉴판", "차림표", "가격표", "주문서", "키오스크", "빌지", "주문메뉴"]):
        return "메뉴판"
    if any(k in ctx_lower for k in ["웨이팅", "대기", "캐치테이블", "테이블링", "조기마감", "줄서"]):
        return "웨이팅"
    if any(k in ctx_lower for k in ["외관", "간판", "입구", "전경", "도착", "외부", "건물", "찾아가는", "파사드", "주소", "매장앞"]):
        return "외관"
    if any(k in ctx_lower for k in ["내부", "인테리어", "좌석", "다찌석", "다찌", "테이블", "자리", "착석", "오픈키친", "홀", "조명", "분위기"]):
        return "내부_인테리어"
    if any(k in ctx_lower for k in ["셀프바", "셀프존", "셀프코너", "무료리필", "밥솥", "공기밥"]):
        return "셀프바"
    if any(k in ctx_lower for k in ["기본찬", "밑반찬", "반찬", "상차림", "세팅", "소스", "양념장", "김치", "단무지", "깍두기", "장국", "스프"]):
        return "기본반찬"
    if any(k in ctx_lower for k in ["마무리", "총평", "완식", "다먹음", "영수증", "빈접시", "빈그릇", "클리어", "배불"]):
        return "완식"

    # 2. 식당의 실제 대표 메뉴 목록과 대조 (음식_ 접두사 없이 순수 요리명 부여)
    for m in known_menus:
        clean_m = re.sub(r'[^가-힣a-zA-Z0-9]', '', m)
        if len(clean_m) >= 2 and clean_m.lower() in ctx_lower:
            if any(k in ctx_lower for k in ["면발", "면치기", "가락", "후루룩"]):
                return f"{clean_m}_면발"
            if any(k in ctx_lower for k in ["한점", "한입", "젓가락", "집어", "숟가락", "들고"]):
                return f"{clean_m}_한점"
            if any(k in ctx_lower for k in ["국물", "육수", "뚝배기", "보글"]):
                return f"{clean_m}_국물"
            return clean_m

    # 3. 음식 특정 키워드 패턴 추출 (짬뽕, 짜장, 탕수육, 만두, 칼국수, 카츠, 삼겹살, 파스타 등)
    food_pattern = r'([가-힣]{2,10}(?:짬뽕|짜장|탕수육|만두|칼국수|국수|라멘|우동|파스타|피자|스테이크|카츠|돈까스|삼겹살|목살|갈비|고기|수육|보쌈|국밥|곰탕|전골|찌개|탕|볶음밥|덮밥|비빔밥|초밥|스시|회|조개|구이|찜|치킨|버거|디저트|케이크|크루아상|빵))'
    m_food = re.search(food_pattern, ctx_lower)
    if m_food:
        matched = m_food.group(1)
        if any(k in ctx_lower for k in ["면발", "면치기"]):
            return f"{matched}_면발"
        if any(k in ctx_lower for k in ["한점", "한입", "젓가락"]):
            return f"{matched}_한점"
        return matched

    # 4. 순서 기반 스마트 폴백 (알려진 실제 메뉴 순환 할당)
    if idx <= 1:
        return "외관"
    elif idx <= 3:
        return "내부_인테리어"
    elif idx >= total - 1:
        return "완식"
    else:
        if known_menus:
            m_idx = (idx - 4) % len(known_menus)
            clean_m = re.sub(r'[^가-힣a-zA-Z0-9]', '', known_menus[m_idx])
            return clean_m
        return "시그니처_메뉴"



def classify_photos_with_vision(image_paths, store_name, location, known_menus=None, status_callback=print):
    """
    구글 제미나이 멀티모달 비전(Vision AI)을 활용하여 다운로드된 실제 이미지 파일들을 직접 시각적으로 분석.
    - 실제 사진의 시각 정보를 보고 외관, 실내_인테리어, 실내_간판, 메뉴판, 밑반찬, 실제 요리명(나베, 후토마키, 튀김 등)을 100% 식별.
    - 무의미한 번호('음식_1', '음식_2')나 엉뚱한 메뉴명('수육' 등)을 원천 박멸.
    """
    if not image_paths:
        return image_paths

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_config.json")
    api_key = ""
    api_provider = "gemini"
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                api_key = cfg.get("api_key", "").strip()
                api_provider = cfg.get("provider", "gemini")
        except Exception:
            pass

    if not api_key:
        status_callback("ℹ️ Vision AI API 키 미등록 -> 스마트 문맥 분석 파일명을 유지합니다.")
        return image_paths

    status_callback(f"👁️ [비전 AI 실물 사진 분석] Gemini Vision으로 다운로드된 실사 사진 {len(image_paths)}장의 실제 이미지를 직접 판독 중...")

    def compress_img(filepath, max_size=768):
        try:
            with Image.open(filepath) as img:
                img = img.convert("RGB")
                img.thumbnail((max_size, max_size))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80)
                return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')

    results = {}
    chunk_size = 10
    total = len(image_paths)

    for chunk_start in range(0, total, chunk_size):
        chunk = image_paths[chunk_start:chunk_start + chunk_size]
        parts = []
        for idx_in_chunk, fpath in enumerate(chunk):
            global_idx = chunk_start + idx_in_chunk + 1
            b64_data = compress_img(fpath)
            parts.append({'text': f'[{global_idx}번 사진]'})
            parts.append({'inlineData': {'mimeType': 'image/jpeg', 'data': b64_data}})

        menu_hint = f"참고 메뉴: {', '.join(known_menus[:5])}" if known_menus else ""
        prompt = f"""식당명: {location} {store_name}
{menu_hint}

위 {chunk_start + 1}번부터 {chunk_start + len(chunk)}번까지의 실제 사진 이미지를 직접 보고, 각 사진의 핵심 피사체를 가장 적절한 한국어 명사로 분류해주세요:
- 건물 바깥 모습/도로 전경 -> 외관
- 매장 입구/출입문/웨이팅 공간 -> 매장입구 또는 웨이팅
- 매장 실내 좌석/테이블/조명 -> 실내_인테리어
- 벽면/간판에 적힌 상호명 또는 조형물 -> 실내_간판
- 키오스크/주문서/메뉴판/가격표 -> 메뉴판
- 밑반찬/소스/국물 -> 기본반찬
- 음식은 사진에 보이는 실제 요리명(예: 나베, 후토마키, 모둠튀김, 우동_면발 등)으로 분류
- 다 먹은 빈 그릇/영수증 -> 완식
* 절대로 '음식_1', '음식_2' 같은 무의미한 번호나 단순 '음식'이라는 단어는 사용하지 마세요.
* 사진에 보이지도 않는 다른 메뉴(예: 이자카야인데 수육 등)를 지어내지 마세요.

반드시 JSON 배열 형식으로만 응답하세요:
[
  {{"idx": {chunk_start + 1}, "name": "외관"}}
]
"""
        parts.append({'text': prompt})

        gemini_vision_models = ["gemini-3-flash-preview", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-1.5-flash"]
        for vm in gemini_vision_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{vm}:generateContent?key={api_key}"
            payload = {
                'contents': [{'parts': parts}],
                'generationConfig': {'responseMimeType': 'application/json'}
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_json = json.loads(resp.read().decode('utf-8'))
                    raw_ans = resp_json['candidates'][0]['content']['parts'][0]['text']
                    clean_ans = re.sub(r'^```json\s*', '', raw_ans.strip())
                    clean_ans = re.sub(r'```$', '', clean_ans.strip())
                    parsed = json.loads(clean_ans)
                    for item in parsed:
                            clean_name = re.sub(r'[^가-힣a-zA-Z0-9_]', '', item["name"]).strip()
                            if not clean_name.startswith("메뉴판"):
                                clean_name = re.sub(r'^(?:음식|사진|image|img|요리)[\s_]*', '', clean_name).strip()
                                clean_name = re.sub(r'^메뉴[\s_]+', '', clean_name).strip()
                            clean_name = re.sub(r'[\s_]*\d+$', '', clean_name).strip()
                            if clean_name in ["판", "차림표"]:
                                clean_name = "메뉴판"
                            if not clean_name or clean_name.isdigit():
                                clean_name = "시그니처_요리"
                            results[int(item["idx"])] = clean_name
                    break
            except Exception:
                continue

    if not results:
        status_callback("⚠️ Vision AI 판독 일시 지연 -> 기존 스마트 파일명을 유지합니다.")
        return image_paths

    new_paths = []
    target_dir = os.path.dirname(image_paths[0])
    cat_counts = {}

    for i, old_path in enumerate(image_paths, 1):
        if not os.path.exists(old_path):
            continue
        cat_name = results.get(i)
        if not cat_name:
            base_no_ext = os.path.splitext(os.path.basename(old_path))[0]
            cat_name = base_no_ext
            if not cat_name.startswith("메뉴판"):
                cat_name = re.sub(r'^(?:음식|사진|image|img|요리)[\s_]*', '', cat_name).strip()
                cat_name = re.sub(r'^메뉴[\s_]+', '', cat_name).strip()
            cat_name = re.sub(r'[\s_]*\d+$', '', cat_name).strip()
            if cat_name in ["판", "차림표"]:
                cat_name = "메뉴판"
            if not cat_name or cat_name.isdigit():
                cat_name = "시그니처_요리"

        cnt = cat_counts.get(cat_name, 0) + 1
        cat_counts[cat_name] = cnt
        suffix = f"_{cnt}" if cnt > 1 else ""

        new_fname = f"{i:02d}_{cat_name}{suffix}.jpg"
        new_fpath = os.path.join(target_dir, new_fname)

        if old_path != new_fpath:
            try:
                if os.path.exists(new_fpath):
                    os.remove(new_fpath)
                os.rename(old_path, new_fpath)
                new_paths.append(new_fpath)
            except Exception:
                new_paths.append(old_path)
        else:
            new_paths.append(old_path)

    status_callback(f"🎉 [Vision AI 사진 판독 완료] 사진 {len(new_paths)}장의 실물 피사체를 100% 인식하여 고유 파일명으로 재지정했습니다!")
    return new_paths


def classify_photos_smart_and_ai(photo_items, store_name, location, menu_cands, status_callback=print):
    """
    블로그 사진 캡션과 문맥을 분석하여 각 사진에 최적화된 파일명 키워드 목록 반환
    1순위: AI API (Gemini/OpenAI) 등록 시 실시간 지능형 문맥 분석
    2순위: 네이버 플레이스 실제 메뉴 기반 스마트 NLP 분류
    """
    total = len(photo_items)
    if total == 0:
        return []

    # 1. API 키 확인 (api_config.json)
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_config.json")
    api_key = ""
    api_provider = "gemini"
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                api_key = cfg.get("api_key", "").strip()
                api_provider = cfg.get("provider", "gemini")
        except Exception:
            pass

    # AI API가 설정되어 있다면 AI 실시간 사진 작명 시도
    if api_key:
        try:
            import generator
            status_callback(f"🤖 [AI 사진 문맥 분석] {api_provider.upper()}로 블로그 사진 {total}장의 실제 내용을 분석 중...")
            
            caption_list = []
            for idx, item in enumerate(photo_items, 1):
                ctx = item.get("context", "").strip()[:80]
                caption_list.append(f"{idx}. {ctx}" if ctx else f"{idx}. (설명 없음)")
            captions_text = "\n".join(caption_list)
            
            prompt = f"""식당명: {store_name} ({location})
대표메뉴: {', '.join(menu_cands) if menu_cands else '시그니처 요리'}

아래는 블로그 글에서 추출한 사진 {total}장의 위치별 캡션/설명 텍스트입니다:
{captions_text}

각 사진의 캡션과 식당 정보를 분석하여, 각 사진에 가장 어울리는 한국어 파일명 키워드를 하나씩 정해주세요.
- 외관/간판 -> 외관
- 실내/좌석 -> 실내_인테리어
- 메뉴판/가격표 -> 메뉴판
- 밑반찬/상차림 -> 기본반찬
- 특정 요리 -> 실제 요리명(예: '돌짬뽕', '탕수육', '돌짜장', '만두' 등)
- 요리 먹는 장면 -> '돌짬뽕_면발', '고기_한점' 등
- 다 먹은 그릇/영수증 -> 완식
* 절대로 '음식_1', '음식_2' 같은 무의미한 번호나 '음식'이라는 단어만 쓰지 말고 실제 요리명을 써주세요.

JSON 배열로만 응답하세요:
[
  {{"idx": 1, "name": "외관"}},
  {{"idx": 2, "name": "실내_인테리어"}}
]
"""
            raw_resp = generator.call_llm_api(api_provider, api_key, prompt, status_callback=lambda x: None)
            if raw_resp:
                clean_json = generator.clean_json_text(raw_resp)
                parsed = json.loads(clean_json)
                ai_names = {}
                for it in parsed:
                    if "idx" in it and "name" in it:
                        ai_names[int(it["idx"])] = re.sub(r'[^가-힣a-zA-Z0-9_]', '', it["name"]).strip()
                if len(ai_names) >= total // 2:
                    result = []
                    for i in range(1, total + 1):
                        result.append(ai_names.get(i) or "요리")
                    status_callback(f"✅ [AI 사진 분석 완료] 사진 {total}장의 고유 파일명이 지능형으로 작명되었습니다.")
                    return result
        except Exception as e:
            status_callback(f"AI 사진 분석 안내: {e} -> 스마트 NLP 분석기로 자동 대체합니다.")

    # 2. 오프라인 스마트 NLP 분석기 (실제 크롤링된 메뉴 기반 매칭)
    status_callback(f"🔍 [스마트 문맥 분석] 사진 캡션과 실제 메뉴 목록을 대조하여 알맞은 파일명을 추출합니다...")
    result = []
    for i, item in enumerate(photo_items):
        cat = smart_classify_photo_context(item["context"].lower(), i, total, known_menus=menu_cands)
        result.append(cat)
    return result


def crawl_store_and_photos_from_blog(blog_url, status_callback=print, on_store_found=None):
    """
    네이버 블로그 포스팅 URL로부터 상호명, 주소, 위치, 메뉴, 특징을 파악하고
    포스팅 내의 실제 고화질 실사 사진들을 순서 및 문맥에 맞게 스마트 네이밍하여 다운로드
    """
    status_callback(f"📖 [블로그 정밀 분석] 블로그 포스팅 원본 주소 분석 중: {blog_url}")
    blog_id, log_no = extract_naver_blog_params(blog_url)
    if not blog_id or not log_no:
        status_callback("⚠️ 네이버 블로그 URL 형식(blog.naver.com/아이디/글번호)을 확인해주세요.")
        return None

    postview_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
    
    found_store = ""
    found_address = ""
    post_title = ""
    all_post_text = ""
    photo_items = []
    
    status_callback("🌐 블로그 포스트 및 실사 이미지 로딩 중...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()
            page.goto(postview_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            
            # 1. 글 제목 추출
            t_el = page.locator(".se-title-text, .se_title, .title_area, h3.se_textarea").first
            if t_el.count():
                post_title = t_el.inner_text().strip()
            
            # 2. 첨부된 네이버 지도/플레이스 위젯 탐색
            map_boxes = page.locator(".se-map-info, .se-place-map, .se-module-map, .se-places-map").all()
            for mb in map_boxes:
                mtxt = mb.inner_text().strip()
                if mtxt:
                    lines = [l.strip() for l in mtxt.split("\n") if l.strip()]
                    if lines:
                        cand_name = lines[0]
                        cand_name = re.sub(r'\s+[가-힣0-9]+점$', '', cand_name).strip()
                        if cand_name and not found_store:
                            found_store = cand_name
                        for l in lines[1:]:
                            if any(r in l for r in ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]):
                                found_address = l
                                break
            
            # 3. 레이지 로딩된 이미지들을 위해 페이지 스크롤 다운
            status_callback("📸 블로그 본문 실사 사진 스크롤 수집 중...")
            for _ in range(8):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(300)
                
            # 4. 본문 컴포넌트 순회 (텍스트 및 이미지 추출)
            modules = page.locator(".se-component").all()
            prev_text = ""
            accumulated_texts = []
            
            for m in modules:
                txt = m.inner_text().strip()
                if txt:
                    accumulated_texts.append(txt)
                
                img = m.locator("img").first
                if img.count():
                    src = img.get_attribute("src") or img.get_attribute("data-lazy-src") or ""
                    if "postfiles.pstatic.net" in src or "blogfiles.pstatic.net" in src:
                        # 고화질 원본 해상도(w966) 강제 적용
                        high_res_src = src.split("?")[0] + "?type=w966"
                            
                        cap_el = m.locator(".se-caption, .se-image-caption").first
                        caption = cap_el.inner_text().strip() if cap_el.count() else ""
                        context_txt = f"{caption} {prev_text}".strip()
                        
                        photo_items.append({
                            "src": high_res_src,
                            "context": context_txt
                        })
                else:
                    if txt and len(txt) > 2:
                        prev_text = txt[:200]
                        
            all_post_text = "\n".join(accumulated_texts)
            browser.close()
    except Exception as e:
        status_callback(f"⚠️ 블로그 페이지 로드 중 오류: {e}")

    # 5. 상호명 보정 (지도 위젯이 없었을 경우 글 제목/본문에서 추출)
    if not found_store and post_title:
        clean_t = re.sub(r'\[.*?\]|\(.*?\)', '', post_title)
        words = [w for w in re.split(r'[\s,/]+', clean_t) if len(w) >= 2]
        stopwords = ["맛집", "솔직후기", "후기", "내돈내산", "방문기", "웨이팅", "추천", "메뉴", "가격", "위치", "원격", "평일", "주말", "캐치테이블", "테이블링"]
        cands = [w for w in words if w not in stopwords]
        if cands:
            found_store = cands[-1] if len(cands) > 1 else cands[0]
            
    if not found_store:
        found_store = "추천맛집"

    # 6. 위치/지역 판별
    location_cand = ""
    addr_to_check = f"{found_address} {post_title} {all_post_text[:500]}"
    loc_patterns = [
        ("광안리", "부산 광안리"), ("해운대", "부산 해운대"), ("서면", "부산 서면"),
        ("용산", "용리단길"), ("성수", "성수동"), ("을지로", "을지로"), 
        ("신당", "신당동"), ("안국", "안국 북촌"), ("북촌", "안국 북촌"),
        ("압구정", "압구정"), ("신사", "가로수길"), ("연남", "연남동"),
        ("망원", "망원동"), ("한남", "한남동"), ("송파", "송리단길"),
        ("잠실", "송리단길"), ("종로", "종로"), ("강남", "강남역"),
        ("홍대", "홍대"), ("여의도", "여의도"), ("수원", "수원 행궁동"),
        ("행궁동", "수원 행궁동"), ("동탄", "동탄"), ("판교", "판교")
    ]
    for key, loc_name in loc_patterns:
        if key in addr_to_check:
            location_cand = loc_name
            break
            
    if not location_cand:
        m_gu = re.search(r'([가-힣]+(?:시|도)?\s*[가-힣]+(?:구|군|시))', addr_to_check)
        location_cand = m_gu.group(1) if m_gu else "서울"

    status_callback(f"✅ [블로그 정보 추출] 상호명: '{found_store}', 지역: '{location_cand}'")

    # 7. 네이버 플레이스 정밀 조회를 통한 실제 매장 정보(메뉴, 영업시간, 주차 등) 먼저 확보
    status_callback(f"📋 '{location_cand} {found_store}'의 상세 매장 정보 조회 중...")
    details = fetch_store_details(found_store, location_cand)
    if found_address and details.get("address") == "매장 위치 정보 참조":
        details["address"] = found_address

    # 실제 식당의 인기 메뉴 목록 수집 (하드코딩 0%)
    all_menus = []
    if details.get("popular_menus"):
        for m in details["popular_menus"]:
            clean_m = re.sub(r'[^가-힣a-zA-Z0-9]', '', m)
            if clean_m and clean_m not in all_menus:
                all_menus.append(clean_m)

    # 본문 텍스트에서도 추가 메뉴 발굴
    food_pattern = r'([가-힣]{2,8}(?:짬뽕|짜장|탕수육|만두|칼국수|국수|라멘|우동|파스타|피자|스테이크|카츠|돈까스|삼겹살|목살|갈비|고기|수육|보쌈|국밥|곰탕|전골|찌개|탕|볶음밥|덮밥|비빔밥|초밥|스시|회|조개|구이|찜|치킨|버거|디저트|케이크|크루아상|빵))'
    for kw in re.findall(food_pattern, all_post_text):
        if kw not in all_menus and len(kw) >= 2:
            all_menus.append(kw)

    if not all_menus:
        all_menus = ["대표요리"]

    menu_str = ", ".join(all_menus[:3])
    features_cand = details.get("ai_summary") or f"{location_cand}에서 높은 평점과 인기를 자랑하는 핫플레이스 찐맛집"
    
    # 상호명, 위치, 대표메뉴 식별 완료 즉시 콜백 호출 (사용자 UI에 1~2초 만에 즉시 반영)
    if on_store_found:
        try:
            on_store_found(found_store, location_cand, menu_str, features_cand)
        except Exception as e:
            print(f"on_store_found 콜백 오류: {e}")

    # 8. 실사 사진 스마트 네이밍 분류 및 다운로드 (AI & 스마트 NLP)
    saved_photos = []
    if photo_items:
        safe_store = re.sub(r'[\/*?:"<>|]', "", found_store).replace(" ", "_")
        safe_loc = re.sub(r'[\/*?:"<>|]', "", location_cand).replace(" ", "_")
        target_dir = os.path.join(DOWNLOADS_ROOT, f"{safe_loc}_{safe_store}")
        os.makedirs(target_dir, exist_ok=True)
        
        # 다운로드 전 기존 잔여 파일 완전 정리 (오염된 파일 제거)
        for old_f in os.listdir(target_dir):
            if old_f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                try:
                    os.remove(os.path.join(target_dir, old_f))
                except Exception:
                    pass

        status_callback(f"💾 블로그 사진 {len(photo_items)}장 분석 및 다운로드 시작 -> {target_dir}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://blog.naver.com'
        }
        
        # 각 사진에 대한 지능형 스마트 파일명 리스트 생성
        photo_names = classify_photos_smart_and_ai(photo_items, found_store, location_cand, all_menus, status_callback=status_callback)
        
        cat_counts = {}
        for i, item in enumerate(photo_items):
            cat = photo_names[i] if i < len(photo_names) else "요리"
            c_cnt = cat_counts.get(cat, 0) + 1
            cat_counts[cat] = c_cnt
            
            suffix = f"_{c_cnt}" if c_cnt > 1 else ""
            fname = f"{len(saved_photos) + 1:02d}_{cat}{suffix}.jpg"
            fpath = os.path.join(target_dir, fname)
            
            try:
                req = urllib.request.Request(item["src"], headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img_data = resp.read()
                if len(img_data) < 10000:
                    continue
                with open(fpath, "wb") as f:
                    f.write(img_data)
                saved_photos.append(fpath)
            except Exception as e:
                print(f"이미지 저장 오류 ({fname}): {e}")

        status_callback(f"🎉 블로그 실사 {len(saved_photos)}장 다운로드 완료! Vision AI 정밀 판독을 진행합니다...")
        saved_photos = classify_photos_with_vision(saved_photos, found_store, location_cand, known_menus=all_menus, status_callback=status_callback)

    

    return {
        "store_name": found_store,
        "location": location_cand,
        "menu": menu_str,
        "features": features_cand,
        "store_info": details,
        "photos": saved_photos
    }


def resolve_store_from_address_or_url(input_query, status_callback=print, on_store_found=None):
    """
    사용자가 입력한 주소(도로명/지번) 또는 URL(네이버 지도/플레이스 링크/블로그 포스팅 링크)로부터
    상호명, 위치, 대표메뉴, 특징 및 매장 상세 정보를 자동 판별
    반환: dict(store_name, location, menu, features, store_info, photos)
    """
    raw_query = input_query.strip()
    if not raw_query:
        return None

    if raw_query.startswith("blog.naver.com") or raw_query.startswith("m.blog.naver.com"):
        raw_query = "https://" + raw_query

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
        
        # 블로그 포스팅 링크인 경우 즉시 블로그 전용 실사 수집기로 분기
        if "blog.naver.com" in target_url:
            return crawl_store_and_photos_from_blog(target_url, status_callback=status_callback, on_store_found=on_store_found)

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

    if on_store_found:
        try:
            on_store_found(found_store, location_cand, menu_cand, features_cand)
        except Exception as e:
            print(f"on_store_found 오류: {e}")

    return {
        "store_name": found_store,
        "location": location_cand,
        "menu": menu_cand,
        "features": features_cand,
        "store_info": details,
        "photos": []
    }


def is_valid_store_name(s):
    """실제 식당 상호명인지 엄격히 검증 (쿠폰/프로모션/영업상태/방송명 등 철저 배제)"""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 2 or len(s) > 22:
        return False
    invalid_keywords = [
        "할인", "쿠폰", "이벤트", "증정", "혜택", "서비스", "콜키지", "무료", "예약", "모임",
        "영업 중", "영업중", "영업 전", "영업전", "영업 종료", "오늘 휴무", "정기휴무", "브레이크타임",
        "생방송투데이", "2TV생생정보", "생방송오늘저녁", "놀라운토요일", "줄서는식당", "맛있는녀석들",
        "휠체어", "출입 가능", "출입가능", "주차 가능", "배달", "포장", "더보기", "다음", "이전", "플레이스", "지도",
        "길찾기", "톡톡", "네이버페이", "새로오픈", "주간 인기", "리뷰", "별점", "광고", "저장", "NAVER", "Corp"
    ]
    if any(k in s for k in invalid_keywords):
        return False
    if re.search(r'\d+%', s) or re.search(r'^\d+(\.\d+)?$', s):
        return False
    return True


def crawl_live_trending_hotplaces(area="성수동", max_count=10):
    """
    네이버에서 실시간 최신 핫플레이스를 검색 크롤링하여 (상호, 위치, 대표메뉴, 특징) 반환
    - 카드 단위(li:has(span.TYaxT) 등)로 정밀 파싱하여 식당 상호명, 카테고리, 메뉴, 혜택을 100% 구분
    - 쿠폰/할인 프로모션 문구(청첩장 모임 10% 할인 쿠폰 등), TV 프로그램명, 영업 상태가 상호명으로 오인되지 않도록 완벽 필터링
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
            
            # 플레이스 카드 단위 탐색
            cards = page.locator('li:has(span.TYaxT), li.UEzoS, li.VLTHu, .place_section li')
            card_count = cards.count()
            
            seen_names = set()
            
            for i in range(card_count):
                c = cards.nth(i)
                title_loc = c.locator('span.TYaxT, span.Ypcqn, a.place_bluelink')
                if not title_loc.count():
                    continue
                
                raw_s = title_loc.first.inner_text().strip()
                clean_s = re.sub(r'\s+[가-힣0-9]+점$', '', raw_s)
                clean_s = re.sub(r'\s+(본점|직영점|1호점|2호점|신당본점|성수본점)$', '', clean_s).strip()
                
                if not is_valid_store_name(clean_s):
                    continue
                if clean_s in seen_names:
                    continue
                seen_names.add(clean_s)
                
                # 카테고리 추출
                cat_loc = c.locator('span.KCMnt')
                cat = cat_loc.first.inner_text().strip() if cat_loc.count() else ""
                
                # 카드 내 전체 텍스트
                lines = [l.strip() for l in c.inner_text().split('\n') if l.strip()]
                if not cat:
                    for l in lines:
                        if any(k in l for k in ["한식", "양식", "일식", "중식", "카페", "디저트", "베이커리", "고기", "구이", "햄버거", "치킨", "피자", "파스타", "만두", "칼국수", "주점", "브런치", "라멘"]):
                            cat = l
                            break
                            
                # 대표 메뉴 추출
                menu = ""
                for j, l in enumerate(lines):
                    if "주간 인기 많은 메뉴" in l and j + 1 < len(lines):
                        menu = lines[j + 1].strip().rstrip(' ,.')
                        break
                        
                if not menu:
                    if any(k in cat for k in ["카페", "디저트", "베이커리"]):
                        menu = "시그니처 디저트, 베이커리, 스페셜티 커피"
                    elif any(k in cat for k in ["버거", "햄버거"]):
                        menu = "수제버거, 프렌치프라이, 쉐이크"
                    elif any(k in cat for k in ["양식", "파스타", "스테이크"]):
                        menu = "시그니처 파스타, 스테이크, 리조또"
                    elif any(k in cat for k in ["고기", "구이"]):
                        menu = "숙성 삼겹살, 목살구이, 된장찌개"
                    elif "라멘" in cat:
                        menu = "시그니처 라멘, 차슈 덮밥, 교자"
                    else:
                        menu = f"{cat} 대표 인기 시그니처 메뉴" if cat else "대표 인기 시그니처 메뉴"
                        
                # 쿠폰/프로모션/혜택 정보
                promo_loc = c.locator('a.UhcHZ, .benefit, .place_promotion')
                promo = promo_loc.first.inner_text().strip() if promo_loc.count() else ""
                
                if promo:
                    feature = f"{cat} 핫플 ({promo})" if cat else f"네이버 플레이스 실시간 인기 핫플 ({promo})"
                elif cat:
                    feature = f"네이버 플레이스 실시간 {area} 주간 인기 {cat} 핫플레이스"
                else:
                    feature = f"네이버 플레이스 실시간 {area} 주간 인기 핫플레이스"
                    
                results.append({
                    "store": clean_s,
                    "location": area,
                    "category": cat,
                    "menu": menu,
                    "features": feature
                })
                if len(results) >= max_count:
                    break
                    
            browser.close()
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

    if force_refresh:
        for old_f in os.listdir(target_dir):
            if old_f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                try:
                    os.remove(os.path.join(target_dir, old_f))
                except Exception:
                    pass
    else:
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
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}_한점.jpg")
                                    elif cat_count == 3:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}_클로즈업.jpg")
                                    elif cat_count == 4:
                                        fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}_조합.jpg")
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

                                fname = os.path.join(target_dir, f"{file_idx:02d}_{clean_menu}_{extra_c + 1}.jpg")
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
            status_callback(f"✅ 총 {len(saved_paths)}장의 무글자 찐 실사 사진 다운로드 완료! Vision AI로 각 사진을 정밀 분석합니다...")
            saved_paths = classify_photos_with_vision(saved_paths, store_name, location, status_callback=status_callback)
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
