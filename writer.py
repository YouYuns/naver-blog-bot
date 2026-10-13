# -*- coding: utf-8 -*-
"""
네이버 블로그 스마트에디터 ONE 자동 포스팅 엔진
Playwright + Google Chrome 기반
- 가운데 정렬(Center Alignment) 기본 적용
- 네이버 스티커(OGQ/모션 스티커) 정상 삽입
- 사진 자동 첨부 (expect_file_chooser 기반 100% 정상 업로드)
- 네이버 지도(장소) dispatch_event 기반 자동 첨부
- 취소선 및 서식 오류 완벽 방지
- 제목과 본문 완벽 분리
- 임시저장
"""

import os
import sys
import time
import random
import subprocess
import pyperclip
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

USER_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "naver_profile"))

_STOP_BROWSER_WAIT = False

def stop_active_browser_session():
    """진행 중인 브라우저 대기 루프를 즉시 중단하고 프로세스 해제"""
    global _STOP_BROWSER_WAIT
    _STOP_BROWSER_WAIT = True
    unlock_profile()

def unlock_profile():
    """기존에 naver_profile을 물고 있는 브라우저 프로세스 정리"""
    try:
        cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*naver_profile*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=5)
        time.sleep(1)
    except Exception:
        pass

def check_is_authenticated(context):
    """네이버 로그인 인증 쿠키(NID_AUT 또는 NID_SES) 존재 여부 확인"""
    try:
        cookies = context.cookies()
        return any(c.get("name") in ["NID_AUT", "NID_SES"] for c in cookies)
    except Exception:
        return False

def dismiss_naver_security_checkpoints(page, status_callback=print):
    """새로운 기기 등록(등록 안 함) 및 비밀번호 다음에 변경 등 중간 확인 화면 자동 건너뛰기"""
    skip_selectors = [
        'button:has-text("등록 안 함")', 'a:has-text("등록 안 함")',
        'button:has-text("등록안함")', 'a:has-text("등록안함")',
        '#btn_cancel', '.btn_cancel',
        'button:has-text("다음에 변경")', 'a:has-text("다음에 변경")',
        'button:has-text("다음에 하기")', 'a:has-text("다음에 하기")',
        'button:has-text("나중에 하기")', 'a:has-text("나중에 하기")',
        'button:has-text("다음에")', 'a:has-text("다음에")'
    ]
    for sel in skip_selectors:
        try:
            elem = page.locator(sel).first
            if elem.is_visible():
                status_callback(f"⚡ 보안/기기등록 확인 건너뛰기 클릭: {sel}")
                elem.click(timeout=1500)
                time.sleep(0.5)
                return True
        except Exception:
            pass
    return False

def dismiss_all_editor_popups(frame, page, status_callback=print):
    """스마트에디터 ONE 초기 팝업(작성중인 글 복구 취소, 웰컴 튜토리얼 확인/닫기) 완벽 해제"""
    for _ in range(4):
        found_any = False
        for target in [frame, page]:
            if not target:
                continue
            # 1. 이전 작성 글 복구 팝업 -> '취소'를 눌러 깨끗한 새 글로 시작
            cancel_selectors = [
                'button.se-popup-button-cancel',
                '.se-popup button.se-popup-button-cancel',
                '.se-popup button:text-is("취소")',
                '.se-popup-alert button:text-is("취소")',
                '.se-popup-confirm button:text-is("취소")'
            ]
            for sel in cancel_selectors:
                try:
                    btn = target.locator(sel)
                    if btn.count() > 0 and btn.first.is_visible():
                        status_callback(f"이전 글 복구 팝업 취소 클릭 (새 글 시작): {sel}")
                        btn.first.click(timeout=1000)
                        found_any = True
                        time.sleep(0.3)
                        break
                except Exception:
                    pass

            # 2. 도움말 / 튜토리얼 / 웰컴 / 새 기능 안내 팝업 -> '확인' 또는 '닫기' 또는 '다시 보지 않기'
            close_selectors = [
                'button.se-help-panel-close-button',
                'button.se-popup-close-button',
                '.se-popup button[aria-label="닫기"]',
                '.se-popup button:text-is("닫기")',
                '.se-popup button:text-is("확인")',
                'button.se-popup-button-confirm',
                '.se-popup button:text-is("다시 보지 않기")',
                'button:has-text("다시 보지 않기")'
            ]
            for sel in close_selectors:
                try:
                    btn = target.locator(sel)
                    if btn.count() > 0 and btn.first.is_visible():
                        status_callback(f"에디터 튜토리얼/안내 팝업 닫기: {sel}")
                        btn.first.click(timeout=1000)
                        found_any = True
                        time.sleep(0.3)
                        break
                except Exception:
                    pass
        if not found_any:
            break
        time.sleep(0.3)

def open_login_browser(status_callback=print):
    """네이버 로그인 전용 브라우저 실행"""
    unlock_profile()
    status_callback("네이버 로그인 브라우저를 실행합니다...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://nid.naver.com/nidlogin.login")
        status_callback("브라우저에서 네이버 로그인을 완료해주세요. 로그인이 확인되면 세션이 저장됩니다.")

        logged_in = False
        for _ in range(180):
            time.sleep(1)
            try:
                curr_url = page.url
                dismiss_naver_security_checkpoints(page, status_callback)
                is_auth = check_is_authenticated(context)
                if is_auth or ("nidlogin" not in curr_url and "naver.com" in curr_url):
                    logged_in = True
                    status_callback("✅ 네이버 로그인이 확인되었습니다! 세션이 영구 저장되었습니다.")
                    time.sleep(2)
                    break
            except Exception:
                break
        
        try:
            context.close()
        except Exception:
            pass
        unlock_profile()
        return logged_in

def apply_center_alignment(frame, status_callback=print):
    """본문 전체를 네이버 블로그 감성의 '가운데 정렬'로 설정"""
    try:
        status_callback("블로그 본문 가운데 정렬 적용 중...")
        align_dropdown = frame.locator('button[data-name="align-drop-down-with-justify"]').first
        if align_dropdown.count() > 0:
            align_dropdown.click()
            time.sleep(0.4)
            center_opt = frame.locator('button.se-toolbar-option-align-center-button, button:has-text("가운데")').first
            if center_opt.count() > 0:
                center_opt.click()
                time.sleep(0.4)
                status_callback("✅ 가운데 정렬 설정 완료")
    except Exception as e:
        status_callback(f"정렬 설정 안내: {e}")

def insert_naver_sticker(frame, page, status_callback=print):
    """스마트에디터 ONE 스티커 삽입 (글자 중간 삽입 방지 & 독립 라인 삽입)"""
    try:
        status_callback("🎀 네이버 스티커 삽입 중...")
        # 1. 기존 글자 중간 클릭 절대 금지! 직전 문장 아래 새 줄 확보
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

        # 2. 툴바 스티커 버튼 클릭
        sticker_btn = frame.locator('button[data-name="sticker"], button.se-sticker-toolbar-button, button[aria-label="스티커"]').first
        if sticker_btn.count() > 0:
            try:
                sticker_btn.click(timeout=3000)
            except Exception:
                sticker_btn.dispatch_event('click')
            page.wait_for_timeout(2000)
            
            # 3. 사이드바 스티커 버튼 목록 클릭 (정확한 클래스: se-sidebar-element-sticker)
            stickers = frame.locator('button.se-sidebar-element-sticker, button.se-sidebar-element')
            if stickers.count() > 0:
                chosen_idx = random.randint(0, min(10, stickers.count() - 1))
                try:
                    stickers.nth(chosen_idx).click(timeout=3000)
                except Exception:
                    stickers.nth(chosen_idx).dispatch_event('click')
                page.wait_for_timeout(1000)
                status_callback("✅ 네이버 스티커 삽입 완료")
            
            # 4. 사이드바 닫기 (스티커 툴바 버튼 다시 클릭)
            try:
                if frame.locator('.se-sidebar-container-sticker').first.is_visible():
                    try:
                        sticker_btn.click(timeout=2000)
                    except Exception:
                        sticker_btn.dispatch_event('click')
                    page.wait_for_timeout(500)
            except Exception:
                page.keyboard.press("Escape")
            
            # 스티커 아래로 새 줄 확보
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
    except Exception as e:
        status_callback(f"스티커 삽입 안내: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

def insert_naver_map(frame, page, query, status_callback=print):
    """스마트에디터 ONE 장소(지도) 첨부"""
    try:
        status_callback(f"🗺️ 네이버 지도(장소) 검색 및 첨부: '{query}'")
        map_btn = frame.locator('button[data-name="place"], button.se-places-toolbar-button, button[aria-label="장소"], button:has-text("장소")').first
        if map_btn.count() > 0:
            map_btn.click()
            page.wait_for_timeout(1500)
            
            map_popup = frame.locator('.se-popup-placesMap, .se-popup-places')
            if map_popup.count() > 0 and map_popup.first.is_visible():
                search_input = map_popup.locator('input[type="text"]').first
                search_input.click()
                search_input.fill(query)
                time.sleep(0.3)
                
                # 검색 버튼 클릭 또는 Enter
                search_btn = map_popup.locator('button:has-text("검색"), button.se-place-search-button').first
                if search_btn.count() > 0:
                    search_btn.click()
                else:
                    search_input.press("Enter")
                page.wait_for_timeout(1500)
                
                # 첫 번째 장소의 [추가] 버튼에 클릭 이벤트 전송
                add_btn = map_popup.locator('button.se-place-add-button, button:has-text("추가")').first
                if add_btn.count() > 0:
                    add_btn.dispatch_event('click')
                    page.wait_for_timeout(800)
                
                # [확인] 버튼 클릭
                confirm_btn = map_popup.locator('button.se-popup-button-confirm, button:has-text("확인")').first
                if confirm_btn.count() > 0 and confirm_btn.is_enabled():
                    confirm_btn.click()
                    page.wait_for_timeout(1000)
                    status_callback(f"✅ 네이버 지도 첨부 완료: '{query}'")
                else:
                    cancel_btn = map_popup.locator('button.se-popup-button-cancel, button:has-text("취소")').first
                    if cancel_btn.count() > 0:
                        cancel_btn.click()
                    else:
                        page.keyboard.press("Escape")
            else:
                page.keyboard.press("Escape")
    except Exception as e:
        status_callback(f"지도 첨부 안내 (건너뜀): {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

def handle_image_attach_mode_popup(frame, page, mode="collage", status_callback=print):
    """
    복수 장 사진 첨부 시 노출되는 '사진 첨부 방식' (개별사진 / 콜라주 / 슬라이드) 팝업 감지 및 자동 선택
    """
    try:
        for _ in range(12):
            for target_scope in (frame, page):
                popup = target_scope.locator('.se-popup-image-type, [data-name="se-popup-image-type"], .se-image-type-popup')
                if popup.count() > 0 and popup.first.is_visible():
                    status_callback("📸 '사진 첨부 방식' 팝업 감지 -> '콜라주' 자동 선택 중...")
                    if mode == "collage":
                        target = target_scope.locator('#image-type-collage, label[for="image-type-collage"], .se-image-type-option-collage, li[data-log*="coll"], button:has-text("콜라주"), label:has-text("콜라주")').first
                    else:
                        target = target_scope.locator('#image-type-individual, label[for="image-type-individual"], .se-image-type-option-list, li[data-log*="ind"], button:has-text("개별사진"), label:has-text("개별사진")').first
                    
                    if target.count() > 0:
                        try:
                            target.click(timeout=1500)
                        except Exception:
                            target.dispatch_event('click')
                        time.sleep(0.5)
                        status_callback("✅ '콜라주' (가로 나란히) 레이아웃 적용 완료!")
                        return True
            time.sleep(0.2)
    except Exception as e:
        status_callback(f"사진 레이아웃 팝업 안내: {e}")
    return False

def write_naver_blog(post_data, image_paths=None, auto_save_draft=True, status_callback=print, on_completed=None):
    """
    스마트에디터 ONE에 제목, 본문, 사진, 스티커, 지도를 정확히 분리하여 자동 입력
    """
    global _STOP_BROWSER_WAIT
    _STOP_BROWSER_WAIT = False

    title = post_data.get("title", "")
    sections = post_data.get("sections", [])
    if image_paths is None:
        image_paths = []

    unlock_profile()
    status_callback("크롬 브라우저를 실행하고 네이버 블로그로 연결합니다...")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # 블로그 글쓰기 페이지 진입
        status_callback("네이버 블로그 글쓰기 화면으로 이동합니다...")
        page.goto("https://blog.naver.com/GoBlogWrite.naver")
        
        # 로그인 필요 여부 및 완료 감지 대기 (최대 5분)
        status_callback("로그인 상태 확인 및 스마트에디터 로딩 대기 중...")
        for wait_i in range(300):
            try:
                curr_url = page.url
                is_auth = check_is_authenticated(context)

                # 기기 등록(deviceConfirm)이나 비밀번호 변경(changePw) 화면인 경우 자동 건너뛰기 시도
                if "deviceConfirm" in curr_url or "changePw" in curr_url or "showAccountNotice" in curr_url:
                    status_callback("⚡ 기기 등록 / 비밀번호 변경 확인창 감지 -> 자동 건너뛰기 진행 중...")
                    dismiss_naver_security_checkpoints(page, status_callback)
                    time.sleep(1)
                    page.goto("https://blog.naver.com/GoBlogWrite.naver")
                    time.sleep(1.5)
                    continue

                if is_auth:
                    # 인증된 상태인데 아직 블로그 글쓰기 페이지가 아니면 글쓰기 화면으로 즉시 이동
                    if "blog.naver.com" not in curr_url and page.locator("#mainFrame").count() == 0 and page.locator(".se-documentTitle").count() == 0:
                        status_callback("✅ 네이버 로그인 감지 완료! 스마트에디터 ONE 글쓰기 화면으로 즉시 이동합니다...")
                        page.goto("https://blog.naver.com/GoBlogWrite.naver")
                        time.sleep(2)
                        continue
                    else:
                        status_callback("✅ 네이버 로그인 확인 완료! 스마트에디터 로딩을 시작합니다...")
                        break

                # 미인증 상태에서 로그인 페이지에 머무르는 경우
                if "nid.naver.com" in curr_url or "nidlogin" in curr_url:
                    if wait_i % 6 == 0:
                        status_callback("⚠️ 네이버 로그인이 필요합니다! 열린 브라우저 창에서 로그인해 주세요 (로그인 시 즉시 자동 시작됩니다)...")
                    time.sleep(1)
                    continue

                # 블로그 도메인에 이미 도착했거나 스마트에디터 프레임이 나타난 경우
                if "blog.naver.com" in curr_url or page.locator("#mainFrame").count() > 0 or page.locator(".se-documentTitle").count() > 0:
                    status_callback("✅ 로그인 확인 완료! 스마트에디터 로딩을 시작합니다...")
                    break

                if "naver.com" in curr_url:
                    page.goto("https://blog.naver.com/GoBlogWrite.naver")
                    time.sleep(2)
            except Exception:
                pass
            time.sleep(1)

        # 스마트에디터 iframe 대기
        status_callback("스마트에디터 프레임 연결 대기 중...")
        frame = None
        for _ in range(50):  # 최대 25초
            try:
                if page.locator("#mainFrame").count() > 0:
                    frame = page.frame_locator("#mainFrame")
                    if frame.locator('.se-documentTitle').count() > 0:
                        status_callback("✅ 스마트에디터 에디터 프레임 연결 완료.")
                        break
                elif page.locator('.se-documentTitle').count() > 0:
                    frame = page
                    status_callback("✅ 스마트에디터 메인 프레임 연결 완료.")
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not frame:
            try:
                page.wait_for_selector("#mainFrame", timeout=15000)
                frame = page.frame_locator("#mainFrame")
                status_callback("스마트에디터 프레임 연결 완료.")
            except Exception:
                frame = page
                status_callback("단일 프레임 모드로 진행합니다.")

        # 1. 팝업 창 닫기 (이전문 복구 취소 + 웰컴/튜토리얼 닫기 완벽 처리)
        status_callback("에디터 초기 팝업 감지 및 닫기 확인 중...")
        dismiss_all_editor_popups(frame, page, status_callback)

        # 취소선(strikethrough) 강제 해제 (글자에 가로줄 쳐지는 현상 원천 차단)
        try:
            strike_btn = frame.locator('button.se-strikethrough-toolbar-button, button[data-name="strikethrough"]').first
            if strike_btn.count() > 0:
                is_selected = strike_btn.evaluate("""el => {
                    return el.classList.contains('se-is-selected') || 
                           el.classList.contains('is-selected') || 
                           el.classList.contains('active') ||
                           el.getAttribute('aria-pressed') === 'true' ||
                           el.getAttribute('data-is-selected') === 'true';
                }""")
                if is_selected:
                    status_callback("⚠️ 켜져 있던 취소선(가로줄)을 해제합니다.")
                    strike_btn.click()
                    time.sleep(0.2)
        except Exception:
            pass

        # 2. 제목 입력 (클립보드 불필요, CDP direct typing)
        status_callback(f"제목 자동 입력 중: {title}")
        title_box = frame.locator('.se-documentTitle').first
        title_box.wait_for(state="visible", timeout=20000)
        
        # 팝업 잔여물 최종 닫기
        dismiss_all_editor_popups(frame, page, status_callback)

        title_input_elem = frame.locator('.se-documentTitle .se-placeholder, .se-documentTitle .se-title-text, .se-documentTitle p, .se-documentTitle').first
        try:
            title_input_elem.click(timeout=3000)
        except Exception:
            try:
                title_box.click(timeout=3000)
            except Exception:
                pass
            
        time.sleep(0.2)
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        time.sleep(0.1)
        
        try:
            title_input_elem.press_sequentially(title, delay=2)
        except Exception:
            page.keyboard.type(title, delay=2)
            
        time.sleep(0.3)
        status_callback("✅ 제목 입력 완료!")

        # 3. 본문 영역으로 포커스 이동 & 가운데 정렬 적용
        status_callback("본문 영역 포커스 이동...")
        page.keyboard.press("Enter")
        time.sleep(0.3)

        # 가운데 정렬 적용
        apply_center_alignment(frame, status_callback)
        time.sleep(0.2)

        # 4. 섹션별 순차 입력 (본문, 사진, 스티커, 지도)
        image_idx = 0
        attached_paths = set()
        total_sections = len(sections)

        for s_idx, sec in enumerate(sections, 1):
            sec_type = sec.get("type", "text")
            
            if sec_type == "text":
                header = sec.get("header", "")
                content = sec.get("content", "")
                
                status_callback(f"본문 작성 중 ({s_idx}/{total_sections})...")
                
                if header:
                    page.keyboard.type(header)
                    page.keyboard.press("Enter")
                    time.sleep(0.04)
                    page.keyboard.press("Enter")
                    time.sleep(0.04)
                
                for line in content.split('\n'):
                    line_str = line.strip()
                    if line_str:
                        page.keyboard.type(line_str)
                    page.keyboard.press("Enter")
                    time.sleep(0.02)
                
                page.keyboard.press("Enter")
                time.sleep(0.05)

            elif sec_type == "sticker":
                insert_naver_sticker(frame, page, status_callback)

            elif sec_type == "map":
                query = sec.get("query", "")
                if query:
                    insert_naver_map(frame, page, query, status_callback)

            elif sec_type in ("image", "image_group"):
                # 섹션에 지정된 사진 경로가 있으면 우선 사용, 없으면 순차 인덱스로 가져옴
                if "paths" in sec and sec["paths"]:
                    batch_paths = [os.path.abspath(x) for x in sec["paths"] if os.path.exists(x)]
                else:
                    req_count = sec.get("count", 1)
                    batch_paths = []
                    for _ in range(req_count):
                        if image_idx < len(image_paths):
                            p = os.path.abspath(image_paths[image_idx])
                            if os.path.exists(p):
                                batch_paths.append(p)
                            image_idx += 1
                
                if batch_paths:
                    attached_paths.update(batch_paths)
                    is_pair = len(batch_paths) > 1
                    file_names = ", ".join([os.path.basename(x) for x in batch_paths])
                    if is_pair:
                        status_callback(f"사진 가로 나란히 첨부 중 ({len(batch_paths)}장 묶음): {file_names}")
                    else:
                        status_callback(f"사진 단독 첨부 중 (1장): {file_names}")

                    uploaded = False
                    
                    # 1차 시도: input[type="file"] 복수 파일 주입 (빠르고 팝업 차단 없음)
                    try:
                        file_inputs = frame.locator('input[type="file"]')
                        if file_inputs.count() > 0:
                            file_inputs.first.set_input_files(batch_paths)
                            page.wait_for_timeout(2000)
                            
                            # 만약 콜라주/가로배치 선택 버튼/팝업이 뜨면 자동 선택
                            if is_pair:
                                handle_image_attach_mode_popup(frame, page, mode="collage", status_callback=status_callback)

                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("Enter")
                            uploaded = True
                            status_callback(f"✅ 사진 첨부 완료 ({len(batch_paths)}장)")
                    except Exception:
                        pass
                    
                    # 2차 시도: 툴바 사진 버튼 클릭 + expect_file_chooser
                    if not uploaded:
                        try:
                            photo_btn = frame.locator('button[data-name="image"], button.se-image-toolbar-button, button[aria-label="사진"], button:has-text("사진")').first
                            if photo_btn.count() > 0:
                                with page.expect_file_chooser(timeout=7000) as fc_info:
                                    photo_btn.click()
                                fc_info.value.set_files(batch_paths)
                                page.wait_for_timeout(2000)
                                if is_pair:
                                    handle_image_attach_mode_popup(frame, page, mode="collage", status_callback=status_callback)
                                page.keyboard.press("ArrowDown")
                                page.keyboard.press("Enter")
                                uploaded = True
                                status_callback(f"✅ 사진 첨부 완료 ({len(batch_paths)}장)")
                        except Exception as img_err:
                            status_callback(f"사진 첨부 안내: {img_err}")

        # 잔여 직접 첨부 사진이 있다면 마무리 구간에 마저 첨부
        remaining = [os.path.abspath(x) for x in image_paths if os.path.abspath(x) not in attached_paths and os.path.exists(x)]
        if remaining:
            status_callback(f"남은 사진 {len(remaining)}장 본문 추가 배치 중...")
            for i in range(0, len(remaining), 2):
                sub_batch = remaining[i:i+2]
                attached_paths.update(sub_batch)
                is_pair = len(sub_batch) > 1
                try:
                    file_inputs = frame.locator('input[type="file"]')
                    if file_inputs.count() > 0:
                        file_inputs.first.set_input_files(sub_batch)
                        page.wait_for_timeout(2000)
                        if is_pair:
                            handle_image_attach_mode_popup(frame, page, mode="collage", status_callback=status_callback)
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                except Exception:
                    pass

        # 4.5 전체 본문 가운데 정렬 일괄 최종 적용
        try:
            status_callback("본문 전체 선택 후 가운데 정렬 최종 적용 중...")
            body_first = frame.locator('.se-component.se-text').first
            if body_first.count() > 0:
                body_first.click()
                page.wait_for_timeout(300)
                page.keyboard.press("Control+a")
                page.wait_for_timeout(400)
                apply_center_alignment(frame, status_callback)
                page.wait_for_timeout(400)
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(300)
        except Exception as align_err:
            status_callback(f"최종 가운데 정렬 안내: {align_err}")

        # 4.8 네이버 블로그 공식 태그 입력 시도 (최대 30개)
        tags = post_data.get("tags", [])
        if tags:
            try:
                pub_btn = frame.locator('button.se-publish-button, button:has-text("발행")').first
                if pub_btn.count() == 0 or not pub_btn.is_visible():
                    pub_btn = page.locator('button.se-publish-button, button:has-text("발행")').first
                
                if pub_btn.count() > 0 and pub_btn.is_visible():
                    status_callback(f"🏷️ 네이버 공식 태그 {min(len(tags), 30)}개 입력 창 열기...")
                    pub_btn.click()
                    page.wait_for_timeout(1200)

                    tag_box = frame.locator('.se-tag-editor input, input.tag_input, input[placeholder*="태그"]').first
                    if tag_box.count() == 0 or not tag_box.is_visible():
                        tag_box = page.locator('.se-tag-editor input, input.tag_input, input[placeholder*="태그"]').first
                    
                    if tag_box.count() > 0 and tag_box.is_visible():
                        tag_box.click()
                        for t in tags[:30]:
                            tag_box.fill(t)
                            page.keyboard.press("Enter")
                            time.sleep(0.08)
                        status_callback(f"✅ 공식 태그 {min(len(tags), 30)}개 등록 완료!")
                    
                    # 발행 레이어 닫고 에디터 복귀 (임시저장 유지)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
            except Exception as tag_err:
                status_callback(f"공식 태그 등록 안내 (본문에 해시태그 포함됨): {tag_err}")
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass

        # 5. 임시저장 수행
        if auto_save_draft:
            status_callback("임시저장 버튼을 누릅니다...")
            try:
                save_btn = frame.locator('button.se-save-button, button:has-text("저장")').first
                if save_btn.count() > 0:
                    save_btn.click()
                    page.wait_for_timeout(1500)
                    status_callback("✅ 임시저장 완료!")
            except Exception as e:
                status_callback(f"임시저장 안내: {e}")

        status_callback("🎉 자동 작성이 완료되었습니다! 브라우저 창에서 내용을 확인하고 [발행]을 누르실 수 있습니다.")
        
        # 글 작성이 끝났으므로 GUI의 '바로 작성하기' 버튼을 즉시 활성화
        if on_completed:
            try:
                on_completed()
            except Exception:
                pass

        # 사용자가 브라우저를 확인하고 발행할 수 있도록 유지 (사용자가 새 핫플을 누르거나 창을 닫으면 즉시 종료)
        for _ in range(300):
            if _STOP_BROWSER_WAIT:
                break
            time.sleep(1)
            try:
                if not context.pages or context.pages[0].is_closed():
                    break
            except Exception:
                break

        try:
            context.close()
        except Exception:
            pass
        unlock_profile()
