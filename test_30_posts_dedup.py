# -*- coding: utf-8 -*-
"""
30회 연속 무중복 및 6대 작가 페르소나 순환 + 상투적 클리셰 0% 검증 테스트 스크립트
"""
import os
import sys
import re
from collections import Counter

# Add naver_blog_bot to sys.path
sys.path.insert(0, r"C:\Users\SUNGHO\.gemini\antigravity\scratch\naver_blog_bot")

import memory_manager
import generator

def run_test():
    print("=" * 60)
    print("🚀 30회 연속 생성 시뮬레이션: 중복 0% & 클리셰(200% 등) 전면 배제 검증")
    print("=" * 60)

    # 1. 메모리 초기화
    memory_manager.clear_generation_memory()

    stores = [
        ("하니칼국수", "신당동", "알곤이칼국수", "칼칼한 국물"),
        ("테디뵈르하우스", "용리단길", "크루아상", "유럽 파리 감성"),
        ("깡통만두", "안국 북촌", "칼만두", "손으로 빚은 만두"),
        ("능동미나리", "성수동", "미나리 곰탕", "향긋한 미나리"),
        ("산청숯불가든", "을지로", "소금구이", "지리산 흑돼지"),
        ("부촌육회", "종로", "육회낙지탕탕이", "미쉐린 빕구루망")
    ]

    titles = []
    intros = []
    outros = []
    personas = []
    sample_photos = [
        "1_외관.jpg", "2_웨이팅.jpg", "3_실내.jpg", "4_메뉴판.jpg", 
        "5_상차림.jpg", "6_메인요리.jpg", "7_고기한점.jpg", "8_마무리.jpg"
    ]

    cliche_words = ["200%", "200프로", "300%", "300프로", "대만족", "올킬", "삼박자"]
    found_cliches = []
    all_post_texts = []

    for i in range(1, 31):
        s_info = stores[(i - 1) % len(stores)]
        store_name, location, menu, features = s_info

        post = generator.generate_template_post(
            store_name=store_name,
            location=location,
            menu=menu,
            features=features,
            photo_count=8,
            include_stickers=True,
            include_map=True,
            photo_paths=sample_photos
        )

        title = post["title"]
        persona = post["persona"]
        sections = post["sections"]

        # 전체 텍스트 수집 및 클리셰 검사
        post_full_text = title + "\n"
        intro_text = ""
        outro_text = ""
        for s in sections:
            if s.get("type") == "text":
                c = s.get("content", "")
                h = s.get("header", "")
                post_full_text += f"{h}\n{c}\n"
                if "방문 정보" in h or "태그" in h:
                    continue
                if not intro_text:
                    intro_text = c
                else:
                    outro_text = c

        all_post_texts.append(post_full_text)
        for kw in cliche_words:
            if kw in post_full_text:
                found_cliches.append(f"Post {i} ({persona['id']}): contains '{kw}'")

        titles.append(title)
        intros.append(intro_text)
        outros.append(outro_text)
        personas.append(persona["id"])

        print(f"[{i:02d}/30] 페르소나: {persona['name']:<18} | 제목: {title[:40]}...")

    print("\n" + "=" * 60)
    print("📊 30회 생성 종합 검증 결과")
    print("=" * 60)

    # 1. 제목 중복 검사
    unique_titles = set(titles)
    title_dup_count = len(titles) - len(unique_titles)
    print(f"1. 제목 무중복: {len(unique_titles)}/30 고유 (중복 {title_dup_count}건) -> {'✅ 합격' if title_dup_count == 0 else '❌ 실패'}")

    # 2. 인트로 중복 검사
    unique_intros = set(intros)
    intro_dup_count = len(intros) - len(unique_intros)
    print(f"2. 인트로 무중복: {len(unique_intros)}/30 고유 (중복 {intro_dup_count}건) -> {'✅ 합격' if intro_dup_count == 0 else '❌ 실패'}")

    # 3. 아웃트로 중복 검사
    unique_outros = set(outros)
    outro_dup_count = len(outros) - len(unique_outros)
    print(f"3. 아웃트로 무중복: {len(unique_outros)}/30 고유 (중복 {outro_dup_count}건) -> {'✅ 합격' if outro_dup_count == 0 else '❌ 실패'}")

    # 4. 페르소나 균등 순환 검사
    p_counts = Counter(personas)
    print(f"4. 6대 페르소나 순환 분포: {dict(p_counts)}")
    all_cycled = all(count == 5 for count in p_counts.values()) and len(p_counts) == 6
    print(f"   페르소나 5회씩 완전 균등 분배 여부 -> {'✅ 완벽 순환' if all_cycled else '⚠️ 불균등'}")

    # 5. 소제목 인위적 번호(1., 2. 등) 배제 검사
    numbered_headers = []
    total_headers = 0
    for i in range(1, 31):
        s_info = stores[(i - 1) % len(stores)]
        post = generator.generate_template_post(*s_info, photo_paths=sample_photos)
        for s in post["sections"]:
            h = s.get("header", "")
            if h:
                total_headers += 1
                if re.search(r'\b\d+[\.\)]\s*', h) or re.search(r'^\s*[^\w\s]*\s*\d+[\.\)]', h):
                    numbered_headers.append(h)

    print(f"5. 소제목 탈-AI 번호 배제 검증: {total_headers}개 헤더 중 번호 헤더 {len(numbered_headers)}개 -> {'✅ 전면 번호 배제 통과' if len(numbered_headers) == 0 else '❌ 번호 포함'}")

    # 6. 상투적 클리셰 단어(200%, 대만족 등) 전면 배제 검사
    print(f"6. 클리셰(200%, 대만족 등) 배제 검증: 검출 건수 {len(found_cliches)}건 -> {'✅ 100% 클리셰 박멸 통과' if len(found_cliches) == 0 else '❌ 클리셰 잔존'}")
    if found_cliches:
        for fc in found_cliches:
            print(f"   ⚠️ {fc}")

    assert title_dup_count == 0, "제목에 중복이 발생했습니다!"
    assert intro_dup_count == 0, "인트로에 중복이 발생했습니다!"
    assert outro_dup_count == 0, "아웃트로에 중복이 발생했습니다!"
    assert all_cycled, "페르소나가 균등 순환되지 않았습니다!"
    assert len(numbered_headers) == 0, f"소제목에 인위적 번호가 포함되어 있습니다: {numbered_headers}"
    assert len(found_cliches) == 0, f"클리셰 단어가 검출되었습니다: {found_cliches}"

    print("\n🎉 모든 30회 무중복 보장, 클리셰 전면 배제, 탈-AI 소제목 및 페르소나 순환 검증 100% 통과!\n")

if __name__ == "__main__":
    run_test()
