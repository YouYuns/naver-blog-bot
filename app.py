# -*- coding: utf-8 -*-
"""
네이버 블로그 맛집 자동 포스팅 프로그램 GUI
Tkinter 기반 직관적인 데스크톱 앱
- 최신 핫플레이스 50곳 자동 추천 & 작성 완료 식당 자동 영구 제외 (중복 방지)
- 네이버 이미지 검색 기반 실제 매장 음식 사진 (최대 14장) 원클릭 자동 수집 및 콜라주 배치
- 실제 매장 정보 (전화번호, 주소, 영업시간, 브레이크타임, 주차) 자동 수집 & 본문 최상단 배치
- 네이버 지도(장소 카드) 본문 최상단 배치
- 2030 맛집 블로거 감성의 생생한 '했어요!' 말투 & 풍부한 감탄사(!)
- 로봇/마크다운 기호 0%
"""

import os
import sys
import re
import json
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import generator
import writer
import store_crawler
import history_manager

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class NaverBlogApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("네이버 블로그 맛집 자동 포스팅 프로그램 (최신 핫플 추천 & SEO 최적화)")
        self.geometry("870x950")
        self.minsize(780, 840)

        self.configure(bg="#F4F6F9")
        style = ttk.Style()
        style.theme_use("clam")

        self.photo_paths = []
        self.custom_photos_selected = False
        self.generated_data = None
        self.store_info = None

        self.create_widgets()
        self.load_default_sample_photos()

    def create_widgets(self):
        # 1. 헤더 타이틀
        header_frame = tk.Frame(self, bg="#03C75A", padx=15, pady=12)
        header_frame.pack(fill="x")
        
        title_lbl = tk.Label(
            header_frame, 
            text="네이버 블로그 맛집 자동 작성기 ✨", 
            font=("Malgun Gothic", 16, "bold"), 
            fg="white", 
            bg="#03C75A"
        )
        title_lbl.pack(side="left")

        sub_lbl = tk.Label(
            header_frame, 
            text="최신 핫플 추천 (쓴 곳 자동 제외) / 실사 자동수집 / 지도·가게정보 최상단 / 가운데정렬", 
            font=("Malgun Gothic", 9), 
            fg="#E8F8F0", 
            bg="#03C75A"
        )
        sub_lbl.pack(side="right", pady=5)

        main_frame = tk.Frame(self, bg="#F4F6F9", padx=15, pady=10)
        main_frame.pack(fill="both", expand=True)

        # --- 섹션 1: 네이버 계정 로그인 세션 ---
        login_group = tk.LabelFrame(main_frame, text=" 1. 네이버 로그인 관리 ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=10, pady=8)
        login_group.pack(fill="x", pady=4)

        login_desc = tk.Label(
            login_group, 
            text="* [안내] 따로 로그인 창을 열 필요 없이, 하단의 [🚀 네이버 블로그에 바로 작성하기]를 누르셔도 브라우저에서 로그인 후 자동으로 글 작성이 바로 시작됩니다.",
            font=("Malgun Gothic", 9), fg="#0066cc", bg="#F4F6F9"
        )
        login_desc.pack(anchor="w")

        btn_box = tk.Frame(login_group, bg="#F4F6F9")
        btn_box.pack(fill="x", pady=5)

        self.btn_login = tk.Button(
            btn_box, text="🔑 네이버 로그인 브라우저 열기", 
            font=("Malgun Gothic", 9, "bold"), bg="#03C75A", fg="white",
            relief="flat", padx=10, pady=5, cursor="hand2",
            command=self.on_open_login_browser
        )
        self.btn_login.pack(side="left")

        self.lbl_login_status = tk.Label(btn_box, text="로그인 프로필 준비됨", font=("Malgun Gothic", 9), fg="#0066cc", bg="#F4F6F9")
        self.lbl_login_status.pack(side="left", padx=15)

        # --- 섹션 2: 맛집 정보 입력 & 새로 만들기 & 최신 핫플 자동 추천 ---
        info_group = tk.LabelFrame(main_frame, text=" 2. 맛집 정보 입력 & 최신 핫플 자동 추천 (쓴 곳 자동 제외) ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=10, pady=8)
        info_group.pack(fill="x", pady=4)

        # 상단 툴바: [새로 만들기 / 초기화] 버튼 & [최신 핫플 추천] & [작성 이력 관리]
        top_ctrl_bar = tk.Frame(info_group, bg="#F4F6F9")
        top_ctrl_bar.pack(fill="x", pady=(0, 4))

        self.btn_reset_all = tk.Button(
            top_ctrl_bar, text="🔄 새로 만들기 / 초기화", 
            font=("Malgun Gothic", 9, "bold"), bg="#E65100", fg="white",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.on_reset_new_post
        )
        self.btn_reset_all.pack(side="left")

        # [사용자 요청] 최신 핫플 자동 생성 버튼 (한번 쓴 곳은 영구 제외)
        self.btn_random_example = tk.Button(
            top_ctrl_bar, text="🎲 최신 핫플 자동 추천 (쓴 곳 자동 제외)", 
            font=("Malgun Gothic", 9, "bold"), bg="#6A1B9A", fg="white",
            relief="flat", padx=12, pady=4, cursor="hand2",
            command=self.on_generate_random_preset
        )
        self.btn_random_example.pack(side="left", padx=(8, 0))

        # [사용자 요청] 네이버 실시간 검색 크롤링 핫플 발굴 버튼 (하드코딩 완전 탈피)
        self.btn_live_crawl_hotplaces = tk.Button(
            top_ctrl_bar, text="🌐 실시간 네이버 핫플 발굴", 
            font=("Malgun Gothic", 9, "bold"), bg="#0288D1", fg="white",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.on_live_crawl_hotplaces
        )
        self.btn_live_crawl_hotplaces.pack(side="left", padx=(6, 0))

        # [작성 이력 관리 버튼]
        self.btn_manage_history = tk.Button(
            top_ctrl_bar, text="📋 작성한 핫플 목록/관리", 
            font=("Malgun Gothic", 9, "bold"), bg="#37474F", fg="white",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.on_manage_history
        )
        self.btn_manage_history.pack(side="left", padx=(6, 0))

        # 핫플 추천 현황 상태 바
        status_bar = tk.Frame(info_group, bg="#F4F6F9")
        status_bar.pack(fill="x", pady=(2, 6))

        self.lbl_preset_status = tk.Label(
            status_bar, 
            text="", 
            font=("Malgun Gothic", 9, "bold"), fg="#6A1B9A", bg="#F4F6F9"
        )
        self.lbl_preset_status.pack(side="left")
        self.update_preset_status_label()

        # 주소, 네이버 플레이스 링크 또는 블로그 포스팅 링크 원클릭 자동완성 바
        address_bar = tk.LabelFrame(info_group, text=" 📍 도로명 주소 / 네이버 플레이스 / 블로그 글 링크로 1초 자동 완성 & 사진 수집 ", font=("Malgun Gothic", 9, "bold"), bg="#EBF3FB", fg="#0052cc", padx=8, pady=5)
        address_bar.pack(fill="x", pady=(2, 8))

        tk.Label(address_bar, text="주소/링크:", font=("Malgun Gothic", 9, "bold"), bg="#EBF3FB", fg="#333").pack(side="left", padx=(0, 5))
        self.entry_address_or_url = ttk.Entry(address_bar, font=("Malgun Gothic", 9))
        self.entry_address_or_url.insert(0, "예) 서울 종로구 북촌로2길 5-6 또는 블로그 링크(https://blog.naver.com/...)")
        self.entry_address_or_url.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def on_addr_focus_in(event):
            if "예)" in self.entry_address_or_url.get():
                self.entry_address_or_url.delete(0, tk.END)
        self.entry_address_or_url.bind("<FocusIn>", on_addr_focus_in)

        self.btn_resolve_address = tk.Button(
            address_bar,
            text="⚡ 주소/블로그로 사진&정보 원스톱 수집",
            font=("Malgun Gothic", 9, "bold"),
            bg="#0052cc",
            fg="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.on_resolve_address_or_url
        )
        self.btn_resolve_address.pack(side="right")

        # 입력 필드 그리드
        grid = tk.Frame(info_group, bg="#F4F6F9")
        grid.pack(fill="x")

        # 상호명
        tk.Label(grid, text="식당 상호명:", font=("Malgun Gothic", 9, "bold"), bg="#F4F6F9").grid(row=0, column=0, sticky="w", pady=3)
        self.entry_store = ttk.Entry(grid, font=("Malgun Gothic", 10), width=28)
        self.entry_store.insert(0, "능동미나리")
        self.entry_store.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        # 위치/지역
        tk.Label(grid, text="지역 / 위치:", font=("Malgun Gothic", 9, "bold"), bg="#F4F6F9").grid(row=0, column=2, sticky="w", padx=(15, 0), pady=3)
        self.entry_location = ttk.Entry(grid, font=("Malgun Gothic", 10), width=25)
        self.entry_location.insert(0, "성수동")
        self.entry_location.grid(row=0, column=3, sticky="w", padx=5, pady=3)

        # 대표 메뉴
        tk.Label(grid, text="대표 메뉴:", font=("Malgun Gothic", 9, "bold"), bg="#F4F6F9").grid(row=1, column=0, sticky="w", pady=3)
        self.entry_menu = ttk.Entry(grid, font=("Malgun Gothic", 10), width=28)
        self.entry_menu.insert(0, "미나리 곰탕, 미나리 수육전골, 미나리 육회비빔밥")
        self.entry_menu.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        # 특징 및 메모
        tk.Label(grid, text="특징 / 꿀팁:", font=("Malgun Gothic", 9, "bold"), bg="#F4F6F9").grid(row=1, column=2, sticky="w", padx=(15, 0), pady=3)
        self.entry_features = ttk.Entry(grid, font=("Malgun Gothic", 10), width=25)
        self.entry_features.insert(0, "향긋한 청도 미나리 듬뿍, 야들야들한 한우 수육, 줄서는식당 대기 1위 핫플")
        self.entry_features.grid(row=1, column=3, sticky="w", padx=5, pady=3)

        # 가게 정보 자동 검색 버튼 바
        crawl_bar = tk.Frame(info_group, bg="#F4F6F9")
        crawl_bar.pack(fill="x", pady=(6, 2))

        self.btn_fetch_store = tk.Button(
            crawl_bar, text="🔍 실제 가게 정보 검색 (전화/영업시간/주차/휴무)", 
            font=("Malgun Gothic", 9, "bold"), bg="#2B80FF", fg="white",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.on_fetch_store_info
        )
        self.btn_fetch_store.pack(side="left")

        self.lbl_store_fetch_status = tk.Label(
            crawl_bar, text="가게 정보: 미조회 (작성 시 자동으로 검색되어 첨부됩니다)", 
            font=("Malgun Gothic", 9), fg="#555", bg="#F4F6F9"
        )
        self.lbl_store_fetch_status.pack(side="left", padx=10)

        # --- 섹션 3: 첨부 사진 관리 (URL 자동 다운로드 & 내 사진 파일명 1:1 자동 매칭) ---
        photo_group = tk.LabelFrame(main_frame, text=" 3. 첨부 사진 관리 (URL 자동 다운로드 사진 & 파일명 1:1 자동 매칭) ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=12, pady=8)
        photo_group.pack(fill="x", pady=4)

        self.photo_mode = tk.StringVar(value="custom")

        row_btns = tk.Frame(photo_group, bg="#F4F6F9")
        row_btns.pack(fill="x", pady=2)

        self.btn_load_photos = tk.Button(
            row_btns, text="📷 내 사진 불러오기 (복수 선택 / Ctrl+A 전체선택)", 
            font=("Malgun Gothic", 9, "bold"), bg="#E0E0E0", relief="groove", padx=12, pady=4, cursor="hand2",
            command=self.on_load_my_photos
        )
        self.btn_load_photos.pack(side="left", padx=(0, 6))

        self.btn_open_download_folder = tk.Button(
            row_btns, text="📁 다운로드 폴더 열기", 
            font=("Malgun Gothic", 9), bg="#ECEFF1", relief="groove", padx=10, pady=4, cursor="hand2",
            command=self.on_open_download_folder
        )
        self.btn_open_download_folder.pack(side="left", padx=6)

        # 상태 안내 라벨
        self.lbl_photo_info = tk.Label(
            photo_group, 
            text="💡 상단에 주소나 블로그 링크를 넣으시면 실사 사진이 알맞은 파일명으로 특정 폴더에 자동 다운로드 및 세팅됩니다.", 
            font=("Malgun Gothic", 9, "bold"), fg="#0066cc", bg="#F4F6F9"
        )
        self.lbl_photo_info.pack(anchor="w", pady=(6, 0))

        lbl_hint = tk.Label(
            photo_group,
            text="💡 사진 선택 팁: 파일 선택 창에서 Ctrl+A를 누르면 해당 폴더 내 모든 사진을 1초 만에 일괄 선택할 수 있습니다. (파일명 순서대로 본문과 1:1 자동 매칭)",
            font=("Malgun Gothic", 8), fg="#555555", bg="#F4F6F9"
        )
        lbl_hint.pack(anchor="w", pady=(2, 0))

        # --- 섹션 4: 블로그 추가 서식 옵션 ---
        option_group = tk.LabelFrame(main_frame, text=" 4. 블로그 서식 & 추가 요소 (최상단 배치 & 가운데정렬) ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=10, pady=6)
        option_group.pack(fill="x", pady=4)

        opt_bar = tk.Frame(option_group, bg="#F4F6F9")
        opt_bar.pack(fill="x")

        self.var_sticker = tk.BooleanVar(value=True)
        cb_sticker = ttk.Checkbutton(opt_bar, text="🎀 네이버 스티커 자동 삽입", variable=self.var_sticker)
        cb_sticker.pack(side="left", padx=5)

        self.var_map = tk.BooleanVar(value=True)
        cb_map = ttk.Checkbutton(opt_bar, text="🗺️ 네이버 지도(장소) 본문 최상단 첨부", variable=self.var_map)
        cb_map.pack(side="left", padx=20)

        # --- 섹션 5: 생성 방식 ---
        mode_group = tk.LabelFrame(main_frame, text=" 5. 생성 방식 (1500~2500자 장문 / 사람이 쓴 듯한 '했어요!' 말투) ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=10, pady=6)
        mode_group.pack(fill="x", pady=4)

        self.mode_var = tk.StringVar(value="template")
        rb1 = ttk.Radiobutton(mode_group, text="고품질 SEO 템플릿 엔진 (무료 / 즉시 생성 / 로봇 기호 0%)", variable=self.mode_var, value="template")
        rb1.pack(anchor="w")

        rb2 = ttk.Radiobutton(mode_group, text="AI 생성 연동 (Google Gemini 또는 OpenAI API Key 필요)", variable=self.mode_var, value="ai")
        rb2.pack(anchor="w", pady=(2, 0))

        ai_input_frame = tk.Frame(mode_group, bg="#F4F6F9")
        ai_input_frame.pack(fill="x", padx=20, pady=2)
        
        tk.Label(ai_input_frame, text="제공자:", bg="#F4F6F9", font=("Malgun Gothic", 9)).pack(side="left")
        self.ai_provider = ttk.Combobox(ai_input_frame, values=["gemini", "openai"], width=8, state="readonly")
        self.ai_provider.set("gemini")
        self.ai_provider.pack(side="left", padx=5)

        tk.Label(ai_input_frame, text="API Key:", bg="#F4F6F9", font=("Malgun Gothic", 9)).pack(side="left", padx=(10, 0))
        self.entry_api_key = ttk.Entry(ai_input_frame, show="*", width=35)
        self.entry_api_key.pack(side="left", padx=5)

        # --- 액션 버튼들 ---
        action_frame = tk.Frame(main_frame, bg="#F4F6F9", pady=5)
        action_frame.pack(fill="x")

        self.btn_preview = tk.Button(
            action_frame, text="🔍 글 미리보기 / 생성", 
            font=("Malgun Gothic", 10, "bold"), bg="#5B6275", fg="white",
            relief="flat", padx=15, pady=7, cursor="hand2",
            command=self.on_preview_post
        )
        self.btn_preview.pack(side="left")

        self.btn_start = tk.Button(
            action_frame, text="🚀 네이버 블로그에 바로 작성하기", 
            font=("Malgun Gothic", 11, "bold"), bg="#03C75A", fg="white",
            relief="flat", padx=25, pady=7, cursor="hand2",
            command=self.on_start_writing
        )
        self.btn_start.pack(side="left", padx=10)

        # --- 상태 로그 모니터 ---
        log_group = tk.LabelFrame(main_frame, text=" 실시간 진행 상황 ", font=("Malgun Gothic", 10, "bold"), bg="#F4F6F9", padx=10, pady=5)
        log_group.pack(fill="both", expand=True, pady=4)

        self.log_text = scrolledtext.ScrolledText(log_group, wrap="word", height=8, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # 시작 시 '능동미나리'(성수동) 자동 세팅 및 기확보된 실사 사진 즉시 연결
        self.apply_preset("능동미나리", "성수동", "미나리 곰탕, 미나리 수육전골, 미나리 육회비빔밥", "향긋한 청도 미나리 듬뿍, 야들야들한 한우 수육, 줄서는식당 대기 1위 핫플")

    def log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)

    def update_preset_status_label(self):
        stats = history_manager.get_history_stats()
        if stats["remaining"] > 0:
            msg = f"🔥 최신 핫플 {stats['total']}곳 중 {stats['written']}곳 작성 완료 (남은 추천: {stats['remaining']}곳 - 이미 쓴 곳은 자동으로 제외됩니다)"
            color = "#6A1B9A"
        else:
            msg = f"🎉 최신 핫플 {stats['total']}곳을 모두 작성하셨습니다! ([작성한 핫플 목록/관리]에서 초기화 가능)"
            color = "#E65100"
        self.lbl_preset_status.config(text=msg, fg=color)

    def on_open_download_folder(self):
        target_dir = store_crawler.DOWNLOADS_ROOT
        if self.photo_paths and os.path.exists(os.path.dirname(self.photo_paths[0])):
            target_dir = os.path.dirname(self.photo_paths[0])
        os.makedirs(target_dir, exist_ok=True)
        try:
            os.startfile(target_dir)
            self.log(f"📁 [폴더 열기] 다운로드 사진 폴더를 탐색기로 열었습니다: {target_dir}")
        except Exception as e:
            messagebox.showinfo("다운로드 폴더", f"다운로드 폴더 위치: {target_dir}")

    def on_photo_mode_changed(self):
        pass

    def reset_start_button(self):
        """블로그 작성 버튼 활성화 및 문구 원복"""
        self.btn_start.config(state="normal", text="🚀 네이버 블로그에 바로 작성하기")

    def on_reset_new_post(self):
        """새로 만들기 / 입력창 및 사진 초기화"""
        writer.stop_active_browser_session()
        self.reset_start_button()
        self.entry_address_or_url.delete(0, tk.END)
        self.entry_address_or_url.insert(0, "예) 서울 종로구 북촌로2길 5-6 또는 블로그 링크(https://blog.naver.com/...)")
        self.entry_store.delete(0, tk.END)
        self.entry_location.delete(0, tk.END)
        self.entry_menu.delete(0, tk.END)
        self.entry_features.delete(0, tk.END)
        self.photo_paths = []
        self.custom_photos_selected = False
        self.photo_mode.set("custom")
        self.store_info = None
        self.generated_data = None
        self.lbl_store_fetch_status.config(text="가게 정보: 미조회 (식당 입력 후 조회 버튼 또는 작성 시 자동 수집)", fg="#555")
        self.lbl_photo_info.config(text="💡 상단에 주소나 블로그 링크를 넣으시면 실사 사진이 알맞은 파일명으로 특정 폴더에 자동 다운로드 및 세팅됩니다.", fg="#0066cc")
        self.log("🔄 [새로 만들기] 입력창과 설정이 깨끗하게 초기화되었습니다! 새로운 맛집 정보를 입력해주세요.")

    def on_generate_random_preset(self):
        """새로운 핫플 맛집 예시 랜덤 자동 생성 (이미 작성한 식당은 자동 제외)"""
        writer.stop_active_browser_session()
        self.reset_start_button()
        current_store = self.entry_store.get().strip()
        candidates = history_manager.get_unwritten_hot_candidates(current_store)
        stats = history_manager.get_history_stats()
        
        if not candidates:
            ans = messagebox.askyesno(
                "핫플 추천 완료", 
                f"🎉 등록된 모든 최신 핫플레이스({stats['total']}곳)를 이미 한 번씩 모두 작성하셨습니다!\n\n작성 기록을 초기화하여 50곳의 핫플을 다시 처음부터 추천받으시겠습니까?\n\n('아니오'를 누르면 직접 새로운 식당을 입력하실 수 있습니다)"
            )
            if ans:
                history_manager.clear_written_history()
                self.update_preset_status_label()
                self.log("🔄 [작성 기록 초기화] 이전 작성 기록이 초기화되어 50곳의 최신 핫플이 다시 추천 풀에 등록되었습니다.")
                candidates = history_manager.HOT_RESTAURANT_POOL
            else:
                return

        chosen = random.choice(candidates)
        self.apply_preset(chosen[0], chosen[1], chosen[2], chosen[3])
        rem = len(candidates) - 1
        self.log(f"🔥 [최신 핫플 추천] '{chosen[0]}' ({chosen[1]} | {chosen[2]}) 예시가 채워졌습니다! (이미 쓴 곳은 자동 제외됨, 남은 핫플: {rem}곳)")

    def on_live_crawl_hotplaces(self):
        """네이버에서 실시간 최신 핫플레이스를 라이브 검색 크롤링하여 발굴 (하드코딩 0%)"""
        writer.stop_active_browser_session()
        self.reset_start_button()
        
        input_loc = self.entry_location.get().strip()
        trend_areas = ["성수동", "용리단길", "을지로", "신당동", "압구정", "연남동", "망원동", "한남동", "송리단길", "안국동", "광안리", "해운대"]
        target_area = input_loc if (input_loc and input_loc not in ["성수동", "서울"]) else random.choice(trend_areas)

        def task():
            self.btn_live_crawl_hotplaces.config(state="disabled", text=f"🌐 '{target_area}' 크롤링 중...")
            self.log(f"🌐 [네이버 실시간 핫플 검색] 네이버에서 '{target_area} 핫플 맛집' 실시간 검색 및 주간 인기 매장 크롤링 중...")
            try:
                results = store_crawler.crawl_live_trending_hotplaces(area=target_area, max_count=10)
                if results:
                    history_manager.save_live_hotplaces(results)
                    self.update_preset_status_label()
                    
                    unwritten = [r for r in results if r["store"] not in history_manager.get_written_store_names()]
                    chosen = random.choice(unwritten) if unwritten else results[0]
                    
                    self.apply_preset(
                        chosen["store"], 
                        chosen.get("location", target_area), 
                        chosen.get("menu", "대표 인기 메뉴"), 
                        chosen.get("features", f"네이버 플레이스 실시간 {target_area} 주간 인기 핫플")
                    )
                    self.log(f"✅ [실시간 발굴 성공] 네이버 실시간 검색으로 '{target_area}' 최신 핫플 {len(results)}곳 발굴 완료!\n👉 '{chosen['store']}' ({chosen.get('menu', '')})이(가) 자동 세팅되었습니다!")
                else:
                    self.log(f"⚠️ '{target_area}' 실시간 크롤링 결과가 없어 기존 추천 풀에서 추천합니다.")
                    self.on_generate_random_preset()
            except Exception as e:
                self.log(f"실시간 핫플 발굴 안내: {e}")
                self.on_generate_random_preset()
            finally:
                self.btn_live_crawl_hotplaces.config(state="normal", text="🌐 실시간 네이버 핫플 발굴")

        threading.Thread(target=task, daemon=True).start()

    def on_manage_history(self):
        """작성 완료된 핫플 히스토리 관리 창"""
        history = history_manager.load_written_history()
        
        win = tk.Toplevel(self)
        win.title("📋 작성 완료된 핫플 목록 관리")
        win.geometry("540x480")
        win.configure(bg="#F4F6F9")
        win.transient(self)
        
        tk.Label(
            win, text="내가 작성 완료한 핫플레이스 목록 (중복 추천 방지)", 
            font=("Malgun Gothic", 11, "bold"), bg="#F4F6F9"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        stats = history_manager.get_history_stats()
        tk.Label(
            win, text=f"총 {stats['total']}곳 중 {stats['written']}곳 작성 완료 | 남은 추천: {stats['remaining']}곳", 
            font=("Malgun Gothic", 9), fg="#6A1B9A", bg="#F4F6F9"
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        list_frame = tk.Frame(win, bg="#F4F6F9")
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        hist_list = tk.Listbox(list_frame, font=("Malgun Gothic", 10), yscrollcommand=scrollbar.set, selectmode="single")
        hist_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=hist_list.yview)
        
        if not history:
            hist_list.insert(tk.END, "  (아직 작성 완료된 식당이 없습니다. 글을 작성하면 여기에 자동 기록됩니다)")
        else:
            for item in history:
                st = item.get("store", "")
                loc = item.get("location", "")
                dt = item.get("written_at", "")[:16]
                hist_list.insert(tk.END, f"  [{dt}] {st} ({loc})")
        
        btn_bar = tk.Frame(win, bg="#F4F6F9")
        btn_bar.pack(fill="x", padx=15, pady=12)
        
        def on_delete_selected():
            sel = hist_list.curselection()
            if not sel or not history:
                messagebox.showinfo("선택 필요", "삭제할 식당을 목록에서 선택해주세요.")
                return
            idx = sel[0]
            if idx >= len(history):
                return
            target_store = history[idx].get("store", "")
            if messagebox.askyesno("기록 삭제", f"'{target_store}'을(를) 작성 완료 목록에서 제거하시겠습니까?\n(제거 시 다음 핫플 추천 풀에 다시 포함됩니다)"):
                history_manager.remove_written_store(target_store)
                self.update_preset_status_label()
                self.log(f"🗑️ [기록 삭제] '{target_store}'이(가) 작성 이력에서 제거되어 다시 추천받을 수 있습니다.")
                win.destroy()
                self.on_manage_history()
        
        def on_clear_all():
            if not history:
                return
            if messagebox.askyesno("전체 초기화", "작성 완료된 모든 식당 기록을 초기화하시겠습니까?\n(모든 핫플 50곳이 다시 추천 풀에 등록됩니다)"):
                history_manager.clear_written_history()
                self.update_preset_status_label()
                self.log("🔄 [전체 초기화] 모든 작성 완료 기록이 초기화되었습니다.")
                win.destroy()
        
        tk.Button(
            btn_bar, text="선택 항목 삭제 (다시 추천 풀에 추가)", 
            font=("Malgun Gothic", 9), relief="groove", padx=8, pady=4,
            command=on_delete_selected
        ).pack(side="left")
        
        tk.Button(
            btn_bar, text="전체 이력 초기화", 
            font=("Malgun Gothic", 9), bg="#ff4444", fg="white", relief="flat", padx=8, pady=4,
            command=on_clear_all
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_bar, text="닫기", 
            font=("Malgun Gothic", 9), relief="groove", padx=12, pady=4,
            command=win.destroy
        ).pack(side="right")

    def apply_preset(self, store, loc, menu, feat):
        """인기 맛집 빠른 채우기"""
        self.reset_start_button()
        self.entry_store.delete(0, tk.END)
        self.entry_store.insert(0, store)
        self.entry_location.delete(0, tk.END)
        self.entry_location.insert(0, loc)
        self.entry_menu.delete(0, tk.END)
        self.entry_menu.insert(0, menu)
        self.entry_features.delete(0, tk.END)
        self.entry_features.insert(0, feat)
        self.store_info = None
        self.custom_photos_selected = False
        self.photo_mode.set("auto")
        
        # 해당 매장의 실사 사진이 이미 다운로드되어 있는지 확인
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', f"{loc}_{store}").strip()
        target_dir = os.path.join(store_crawler.DOWNLOADS_ROOT, safe_name)
        if os.path.exists(target_dir):
            existing = [os.path.join(target_dir, f) for f in sorted(os.listdir(target_dir)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and os.path.getsize(os.path.join(target_dir, f)) > 6000]
            if len(existing) >= 6:
                self.photo_paths = existing
                self.lbl_photo_info.config(text=f"현재 모드: [자동생성] '{store}' 글자 없는 실사 사진 {len(self.photo_paths)}장 준비됨", fg="#03C75A")
                self.lbl_store_fetch_status.config(text="가게 정보: 미조회 (작성 시 자동 수집)", fg="#555")
                self.log(f"📌 '{store}' 예시가 채워졌습니다. 실사 사진 {len(self.photo_paths)}장(외관+내부+메뉴+상차림+음식)이 자동 세팅되었습니다!")
                return

        self.photo_paths = []
        self.lbl_store_fetch_status.config(text="가게 정보: 미조회 (작성 시 자동 수집)", fg="#555")
        self.lbl_photo_info.config(text="현재 모드: [자동생성] 작성 시 네이버에서 글자 없는 찐 실사 12~14장 자동 수집 & 콜라주 배치", fg="#0066cc")
        self.log(f"📌 '{store}' 예시가 채워졌습니다. [🚀 네이버 블로그에 바로 작성하기]를 누르면 사진과 가게정보가 자동으로 완성됩니다!")

    def load_default_sample_photos(self):
        sample_dir = os.path.join(CURRENT_DIR, "sample_photos")
        if os.path.exists(sample_dir):
            files = [os.path.join(sample_dir, f) for f in sorted(os.listdir(sample_dir)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            if files:
                self.photo_paths = files
                self.lbl_photo_info.config(text=f"외관·내부·메뉴·상차림·음식 실사 {len(self.photo_paths)}장 준비됨", fg="#03C75A")
                self.log(f"외관, 내부, 메뉴판, 상차림, 음식 실사 사진 {len(self.photo_paths)}장이 준비되었습니다! (가로 나란히 배치 지원)")
                return
        self.photo_paths = []
        self.lbl_photo_info.config(text="선택된 사진: 0장 (작성 시 네이버에서 해당 식당 실사 자동 수집)")

    def on_resolve_address_or_url(self):
        """사용자가 입력한 주소/링크로 상호, 위치, 메뉴, 정보 및 알맞은 이름의 사진들을 한 번에 자동 완성"""
        query = self.entry_address_or_url.get().strip()
        if not query or "예)" in query:
            messagebox.showwarning("주소 또는 링크 입력 필요", "식당 도로명 주소(예: 서울 종로구 북촌로2길 5-6) 또는 네이버 플레이스 URL 링크를 입력해주세요.")
            return

        def task():
            self.btn_resolve_address.config(state="disabled", text="⏳ 주소 분석 중...")
            self.log(f"📍 [주소/링크 원스톱 처리] '{query}' 분석 및 매장 탐색 시작...")
            try:
                res = store_crawler.resolve_store_from_address_or_url(query, status_callback=self.log)
                if not res or not res.get("store_name"):
                    self.log("⚠️ 해당 주소에서 식당 정보를 찾지 못했습니다. 상호명을 직접 입력해주세요.")
                    return

                store_name = res["store_name"]
                location = res.get("location", "")
                menu = res.get("menu", "")
                features = res.get("features", "")
                store_info = res.get("store_info", {})

                # 1. 입력창 자동 세팅
                self.entry_store.delete(0, tk.END)
                self.entry_store.insert(0, store_name)
                self.entry_location.delete(0, tk.END)
                self.entry_location.insert(0, location)
                self.entry_menu.delete(0, tk.END)
                self.entry_menu.insert(0, menu)
                self.entry_features.delete(0, tk.END)
                self.entry_features.insert(0, features)
                self.store_info = store_info

                tel = store_info.get("tel", "")
                addr = store_info.get("address", "")
                self.lbl_store_fetch_status.config(
                    text=f"✅ 매장 식별 완료: {store_name} ({location}) | 📞 {tel}",
                    fg="#03C75A"
                )
                self.log(f"🎉 [매장 정보 자동 인식 완료]\n- 상호명: {store_name}\n- 위치: {location}\n- 대표메뉴: {menu}\n- 주소: {addr}\n- 전화번호: {tel}")

                # 2. 사진 세팅 (블로그 직수집 사진이 있으면 즉시 채택, 없으면 이미지 검색으로 보강)
                blog_photos = res.get("photos", [])
                if blog_photos:
                    self.photo_paths = blog_photos
                    self.custom_photos_selected = True
                    self.photo_mode.set("custom")
                    self.lbl_photo_info.config(
                        text=f"✅ [블로그 실사 수집 완료] 사진 {len(self.photo_paths)}장(외관+내부+메뉴판+상차림+음식) 알맞은 이름으로 자동 저장 & 세팅 완료!",
                        fg="#03C75A"
                    )
                    self.log(f"🎉 [블로그 사진 및 매장정보 원스톱 수집 완료]\n- 저장 폴더: {os.path.dirname(blog_photos[0])}\n- 수집 장수: {len(blog_photos)}장\n- 상호명: {store_name} | 대표메뉴: {menu}\n👉 아래 [🚀 네이버 블로그에 바로 작성하기]를 누르면 사진과 글이 100% 매칭되어 자동 작성됩니다.")
                else:
                    self.btn_resolve_address.config(text="📷 맞춤 사진 수집 중...")
                    self.lbl_photo_info.config(text=f"네이버에서 '{location} {store_name}' 실사 사진 수집 및 스마트 네이밍 중...", fg="#0066cc")
                    self.log(f"📸 [사진 자동 수집 & 스마트 네이밍] 글 서사 순서(외관->내부->메뉴판->상차림->{menu})에 맞추어 알맞은 파일명으로 12~14장 실사 수집 시작...")

                    photos = store_crawler.download_store_photos(
                        store_name=store_name,
                        location=location,
                        menu=menu,
                        max_count=14,
                        status_callback=self.log,
                        force_refresh=True
                    )

                    if photos:
                        self.photo_paths = photos
                        self.custom_photos_selected = False
                        self.photo_mode.set("auto")
                        self.lbl_photo_info.config(
                            text=f"✅ [주소 수집 완료] 실사 사진 {len(self.photo_paths)}장(외관+내부+메뉴판+상차림+음식) 알맞은 이름으로 준비 완료!",
                            fg="#03C75A"
                        )
                        self.log(f"🎉 [준비 완료] 주소 하나로 상호명, 위치, 대표메뉴, 매장정보와 함께 {len(self.photo_paths)}장의 알맞은 이름의 실사 사진이 모두 세팅되었습니다!\n👉 아래 [🚀 네이버 블로그에 바로 작성하기]를 누르시면 글과 사진이 100% 매칭되어 자동 작성됩니다.")
                    else:
                        self.log("⚠️ 사진 수집을 완료하지 못했습니다. 기존 기본 샘플을 활용합니다.")
            except Exception as e:
                self.log(f"⚠️ 주소 분석 및 사진 수집 중 오류: {e}")
            finally:
                self.btn_resolve_address.config(state="normal", text="⚡ 주소/블로그로 사진&정보 원스톱 수집")

        threading.Thread(target=task, daemon=True).start()

    def on_auto_download_photos(self):
        """네이버 이미지 검색에서 실제 식당 사진 최대 14장 다운로드"""
        store = self.entry_store.get().strip()
        location = self.entry_location.get().strip()
        menu = self.entry_menu.get().strip()
        if not store:
            messagebox.showwarning("식당 상호명 필요", "먼저 식당 상호명을 입력해주세요.")
            return

        def task():
            if hasattr(self, 'btn_auto_photos'):
                self.btn_auto_photos.config(state="disabled", text="사진 수집 중...")
            self.lbl_photo_info.config(text="네이버에서 외관·내부·메뉴·상차림·음식 실사 검색 중...", fg="#0066cc")
            self.log(f"네이버에서 '{location} {store}' 외관/내부/메뉴판/상차림/음식 실사 사진 12~14장을 수집합니다...")
            try:
                photos = store_crawler.download_store_photos(store, location, menu=menu, max_count=14, status_callback=self.log, force_refresh=True)
                if photos:
                    self.photo_paths = photos
                    self.custom_photos_selected = False
                    self.lbl_photo_info.config(text=f"✅ 네이버 실사 {len(self.photo_paths)}장(외관+내부+메뉴+상차림+음식) 준비 완료!", fg="#03C75A")
                    self.log(f"✅ 사진 준비 완료! 본문 사이사이에 총 {len(self.photo_paths)}장의 다양한 실사 사진이 배치됩니다 (가로 나란히 배치 포함).")
                else:
                    self.lbl_photo_info.config(text="사진 수집 안내: 기본 샘플 사진으로 대체됩니다.", fg="#555")
            except Exception as e:
                self.log(f"사진 다운로드 오류: {e}")
            finally:
                if hasattr(self, 'btn_auto_photos'):
                    self.btn_auto_photos.config(state="normal", text="⚡ 지금 즉시 사진 수집")

        threading.Thread(target=task, daemon=True).start()

    def on_fetch_store_info(self):
        store = self.entry_store.get().strip()
        location = self.entry_location.get().strip()
        if not store:
            messagebox.showwarning("상호명 입력 필요", "식당 상호명을 입력해주세요.")
            return

        def task():
            self.btn_fetch_store.config(state="disabled", text="검색 중...")
            self.lbl_store_fetch_status.config(text="네이버에서 실제 매장 정보를 조회하고 있습니다...", fg="#0066cc")
            self.log(f"네이버에서 '{location} {store}' 매장 정보(전화, 영업시간, 주차 등) 검색 중...")
            try:
                info = store_crawler.fetch_store_details(store, location)
                self.store_info = info
                summary_txt = f"전화: {info.get('tel', '확인필요')} | 주소: {info.get('address', '확인필요')[:20]}... | {info.get('bizhour', '')[:15]}"
                self.lbl_store_fetch_status.config(text=f"✅ 조회 완료: {summary_txt}", fg="#03C75A")
                self.log(f"✅ 매장 정보 수집 완료:\n{store_crawler.format_store_info_section(info)}")
            except Exception as e:
                self.lbl_store_fetch_status.config(text="조회 실패 (기본 안내로 대체)", fg="#ff3333")
                self.log(f"매장 정보 검색 오류: {e}")
            finally:
                self.btn_fetch_store.config(state="normal", text="🔍 실제 가게 정보 검색 (전화/영업시간/주차/휴무)")

        threading.Thread(target=task, daemon=True).start()

    def on_load_my_photos(self):
        """팝업 질문 없이 즉시 복수 사진 선택 창 열기 (Ctrl+A로 폴더 전체 일괄 선택 가능)"""
        self.on_select_photo_files()

    def on_select_photo_files(self):
        initial_dir = store_crawler.DOWNLOADS_ROOT
        if self.photo_paths and os.path.exists(os.path.dirname(self.photo_paths[0])):
            initial_dir = os.path.dirname(self.photo_paths[0])
        else:
            store = self.entry_store.get().strip()
            loc = self.entry_location.get().strip()
            if store:
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', f"{loc}_{store}").strip()
                cand_dir = os.path.join(store_crawler.DOWNLOADS_ROOT, safe_name)
                if os.path.exists(cand_dir):
                    initial_dir = cand_dir

        files = filedialog.askopenfilenames(
            title="첨부할 사진들을 선택하세요 (Ctrl+A로 폴더 전체 선택 / Ctrl 클릭으로 복수 선택)",
            initialdir=initial_dir,
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp"), ("All Files", "*.*")]
        )
        if files:
            self.photo_paths = sorted(list(files), key=generator.smart_photo_sort_key)
            self.custom_photos_selected = True
            self.photo_mode.set("custom")
            self.lbl_photo_info.config(
                text=f"✅ 선택된 사진 {len(self.photo_paths)}장 준비 완료! (파일명 순서대로 본문 글 문맥과 1:1 자동 매칭)", 
                fg="#03C75A"
            )
            self.log(f"📁 [사진 선택] 사진 {len(self.photo_paths)}장이 지정되었습니다.")
            summary = generator.get_photo_analysis_summary(self.photo_paths)
            self.log(summary)
            self.log("✨ 파일명에 맞게 글 문맥과 사진 배치가 1:1 완벽 매칭되도록 자동 준비되었습니다!")

    def on_open_login_browser(self):
        def task():
            self.btn_login.config(state="disabled")
            try:
                res = writer.open_login_browser(status_callback=self.log)
                if res:
                    self.lbl_login_status.config(text="✅ 로그인 완료 (하단 [바로 작성하기] 클릭 시 즉시 작성)", fg="#03C75A")
                    self.log("💡 [안내] 네이버 로그인이 정상 저장되었습니다! 이제 아래 [🚀 네이버 블로그에 바로 작성하기] 버튼을 누르시면 준비된 글이 바로 자동 작성됩니다.")
                    messagebox.showinfo(
                        "로그인 세션 저장 완료",
                        "✅ 네이버 로그인이 성공적으로 저장되었습니다!\n\n이제 하단의 [🚀 네이버 블로그에 바로 작성하기] 버튼을 누르시면\n준비된 맛집 글이 네이버 블로그에 자동으로 작성됩니다."
                    )
            except Exception as e:
                self.log(f"로그인 오류: {e}")
            finally:
                self.btn_login.config(state="normal")
        threading.Thread(target=task, daemon=True).start()

    def generate_current_post(self):
        import importlib
        importlib.reload(generator)
        import memory_manager
        importlib.reload(memory_manager)

        store = self.entry_store.get().strip()
        location = self.entry_location.get().strip()
        menu = self.entry_menu.get().strip()
        features = self.entry_features.get().strip()
        photo_count = max(len(self.photo_paths), 1)

        include_stickers = self.var_sticker.get()
        include_map = self.var_map.get()

        if not store or not location or not menu:
            messagebox.showwarning("필수 입력 누락", "상호명, 위치, 대표메뉴를 입력해주세요.")
            return None

        # 가게 정보가 아직 검색되지 않았다면 자동 검색
        if not self.store_info:
            self.log(f"네이버에서 '{store}' 매장 정보(전화, 영업시간, 주차 등) 자동 조회 중...")
            try:
                self.store_info = store_crawler.fetch_store_details(store, location)
                self.log("✅ 매장 상세 정보 수집 완료!")
            except Exception as e:
                self.log(f"가게 정보 자동 조회 안내: {e}")

        # 다음 작가 페르소나 자동 배정 (6대 페르소나 균등 순환)
        active_persona = memory_manager.get_next_persona()
        self.log(f"🎭 [작가 페르소나: {active_persona['name']}] ({active_persona['desc']})")

        mode = self.mode_var.get()
        if mode == "ai":
            api_key = self.entry_api_key.get().strip()
            provider = self.ai_provider.get()
            if not api_key:
                messagebox.showwarning("API Key 필요", "AI 생성을 위해 API Key를 입력해주세요. (또는 무료 템플릿 모드를 선택하세요)")
                return None
            self.log("AI 모델을 통해 고유 블로그 글(장문)을 생성 중입니다...")
            data = generator.generate_ai_post(
                api_key, provider, store, location, menu, features, photo_count, 
                include_stickers, include_map, photo_paths=self.photo_paths
            )
        else:
            self.log("30회 무중복 보장 템플릿 엔진으로 풍성한 장문 포스팅을 구성합니다...")
            data = generator.generate_template_post(
                store, location, menu, features, photo_count, include_stickers, include_map, 
                store_info=self.store_info, photo_paths=self.photo_paths, persona=active_persona
            )

        if data:
            self.log(f"✅ 포스팅 생성 완료! [30회 연속 무중복 검증 통과]")

        self.generated_data = data
        return data

    def on_preview_post(self):
        data = self.generate_current_post()
        if not data:
            return

        persona = data.get("persona")
        p_tag = f" [{persona['name']}]" if persona else ""

        preview_win = tk.Toplevel(self)
        preview_win.title(f"생성된 글 미리보기{p_tag} (30회 무중복 보장)")
        preview_win.geometry("720x700")

        tk.Label(preview_win, text=f"제목: {data['title']}", font=("Malgun Gothic", 11, "bold"), wraplength=670, justify="left").pack(anchor="w", padx=15, pady=10)
        tk.Label(preview_win, text=f"🏷️ 추천 해시태그 ({len(data['tags'])}개):\n{' '.join(['#' + t for t in data['tags']])}", font=("Malgun Gothic", 9), fg="#444", wraplength=670, justify="left").pack(anchor="w", padx=15, pady=(0, 5))

        txt = scrolledtext.ScrolledText(preview_win, wrap="word", font=("Malgun Gothic", 10))
        txt.pack(fill="both", expand=True, padx=15, pady=10)

        for sec in data["sections"]:
            stype = sec.get("type")
            if stype == "text":
                h = sec.get("header", "")
                if h:
                    txt.insert(tk.END, f"\n[소제목] {h}\n\n")
                txt.insert(tk.END, f"{sec.get('content', '')}\n\n")
            elif stype == "image":
                paths = sec.get('paths', [])
                file_names = f" (매칭된 사진: {', '.join([os.path.basename(p) for p in paths])})" if paths else ""
                txt.insert(tk.END, f"\n📷 [사진 첨부 위치 - {sec.get('caption', '')}{file_names}]\n\n")
            elif stype == "sticker":
                txt.insert(tk.END, f"\n🎀 [네이버 스티커 삽입 위치]\n\n")
            elif stype == "map":
                txt.insert(tk.END, f"\n🗺️ [네이버 지도/장소 첨부 위치 - {sec.get('query', '')}]\n\n")

        self.log(f"미리보기가 생성되었습니다: {data['title']}")

    def on_start_writing(self):
        store = self.entry_store.get().strip()
        location = self.entry_location.get().strip()
        menu = self.entry_menu.get().strip()
        features = self.entry_features.get().strip()

        if not store or not location or not menu:
            messagebox.showwarning("필수 입력 누락", "상호명, 위치, 대표메뉴를 입력해주세요.")
            return

        def task():
            self.btn_start.config(state="disabled", text="블로그 자동 작성 진행 중...")
            try:
                # 1단계: 사진 준비 (URL 자동 다운로드 사진 or 직접 선택 사진)
                if not self.photo_paths:
                    self.log(f"📸 첨부할 사진이 준비되지 않아 네이버에서 '{location} {store}' 실사 사진을 자동 수집합니다...")
                    photos = store_crawler.download_store_photos(store, location, menu=menu, max_count=14, status_callback=self.log)
                    if photos:
                        self.photo_paths = photos
                        self.custom_photos_selected = True
                        self.lbl_photo_info.config(text=f"✅ 네이버 실사 {len(self.photo_paths)}장 다운로드 및 세팅 완료!", fg="#03C75A")
                    else:
                        self.load_default_sample_photos()

                self.log(f"📁 [1단계: 사진 배치] 총 {len(self.photo_paths)}장의 사진을 파일명과 글 흐름(외관->내부->메뉴판->상차림->음식)에 맞춰 본문 사이사이에 1:1로 자동 배치합니다.")

                # 2단계: 가게 정보가 없으면 실제 매장 정보(전화, 주소, 영업시간, 주차) 자동 크롤링
                if not self.store_info:
                    self.log(f"🏠 [2단계] 네이버에서 '{store}' 실제 매장 정보(전화/영업시간/주차 등) 자동 수집 중...")
                    self.store_info = store_crawler.fetch_store_details(store, location)
                    tel = self.store_info.get("tel", "")
                    self.lbl_store_fetch_status.config(text=f"✅ 매장 정보 수집 완료 ({tel})", fg="#03C75A")

                # 3단계: 장문 포스팅 구성 (지도/매장정보 본문 최상단, 올린 사진과 100% 매칭, 스티커, 가운데정렬)
                self.log("📝 [3단계] 올리신 사진과 100% 어울리는 맞춤형 포스팅 본문(했어요! 어조) 구성 중...")
                data = self.generate_current_post()
                if not data:
                    self.btn_start.config(state="normal", text="🚀 네이버 블로그에 바로 작성하기")
                    return

                # [사용자 요청] 작성한 식당은 히스토리에 자동 추가 (다음 추천에서 영구 제외)
                history_manager.add_written_store(store, location, menu)
                self.update_preset_status_label()
                self.log(f"📝 [작성 이력 기록] '{store}'({location})이(가) 작성 완료 목록에 영구 기록되었습니다. (앞으로 핫플 추천에서 자동 제외됩니다)")

                # 4단계: 크롬 브라우저 스마트에디터 ONE 자동 작성 실행
                self.log("🚀 [4단계] 네이버 스마트에디터 ONE 자동 작성 시작...")
                writer.write_naver_blog(
                    post_data=data,
                    image_paths=self.photo_paths,
                    auto_save_draft=True,
                    status_callback=self.log,
                    on_completed=lambda: self.after(0, self.reset_start_button)
                )
            except Exception as e:
                self.log(f"❌ 작성 중 오류 발생: {e}")
                import traceback
                self.log(traceback.format_exc())
            finally:
                self.btn_start.config(state="normal", text="🚀 네이버 블로그에 바로 작성하기")

        threading.Thread(target=task, daemon=True).start()

def main():
    app = NaverBlogApp()
    app.mainloop()

if __name__ == "__main__":
    main()
