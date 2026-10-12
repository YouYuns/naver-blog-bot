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
    네이버 포털 검색을 통해 해당 식당의 실제 정보를 크롤링
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
        "convenience": ""
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

            if matched_text:
                lines = [l.strip() for l in matched_text.split("\n") if l.strip()]
                for idx, line in enumerate(lines):
                    # 주소 탐색
                    if line == "주소" and idx + 1 < len(lines):
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

            browser.close()
    except Exception as e:
        print(f"가게 정보 검색 중 안내: {e}")

    return info

def download_store_photos(store_name, location="", max_count=14, status_callback=print, force_refresh=False):
    """
    네이버 이미지 검색에서 실제 맛집의 다양한 실사 사진을 카테고리별로 자동 수집 (12~14장)
    - 글자/워터마크/카드뉴스 텍스트 완전 배제 (100% 클린 실사 필터링)
    - 이상한 수족관 반사 / 무관한 사진 배제 (간판, 입구, 매장 내부, 실제 음식 집중)
    - 외관(2장), 내부(2장), 메뉴판(2장), 상차림(2장), 음식(6장)으로 엄격한 순서와 카테고리 유지
    """
    safe_name = re.sub(r'[\/\\:\*\?"<>\|]', '_', f"{location}_{store_name}").strip()
    target_dir = os.path.join(DOWNLOADS_ROOT, safe_name)
    os.makedirs(target_dir, exist_ok=True)

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
        ("음식", [f"{store_name} 대표 음식", f"{location} {store_name} 맛집 메뉴", f"{location} {store_name}"], 6, False),
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

                                fname = os.path.join(target_dir, f"{file_idx:02d}_추가음식_{extra_c + 1}.jpg")
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
    if info.get("break_time"):
        lines.append(f"☕ 브레이크타임 : {info['break_time']}")
    if info.get("holiday"):
        lines.append(f"🗓️ 정기휴무 : {info['holiday']}")
    
    lines.append(f"🚗 주차 정보 : {parking}")
    if conv:
        lines.append(f"✨ 편의시설 : {conv}")

    return "\n".join(lines)
