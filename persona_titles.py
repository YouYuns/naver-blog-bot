# -*- coding: utf-8 -*-
"""
6대 작가 페르소나별 36개 고유 제목 풀 (persona_titles.py)
"""

PERSONA_TITLES = {
    "trendy": [
        lambda s, l, m: f"[{l} 핫플] {s} 솔직후기! {m} 제대로 즐기고 왔어요! ✨",
        lambda s, l, m: f"요즘 SNS 난리난 {l} 맛집 '{s}'! 대표메뉴 {m} 찐 영접기 💖",
        lambda s, l, m: f"웨이팅 각오하고 달려간 {l} {s}! {m}의 황홀한 비주얼과 맛 🔥",
        lambda s, l, m: f"[{l} 데이트 성지] 분위기부터 {m} 맛까지 올킬! {s} 솔직 방문기 📸",
        lambda s, l, m: f"드디어 영접한 {l} 줄서는 핫플 {s}! 인생 {m} 등극이에요 👍",
        lambda s, l, m: f"입소문 자자한 이유가 있었네! {l} {s} {m} 먹방 대성공 😋"
    ],
    "gourmet": [
        lambda s, l, m: f"[{l} 미식 기행] 깊은 내공의 정수, {s}의 {m} 탐방기 🍽️",
        lambda s, l, m: f"식재료 본연의 풍미가 살아있는 {l} 맛집 '{s}' {m} 솔직 평 🥢",
        lambda s, l, m: f"미식가들이 입을 모아 극찬하는 {l} {s}, {m}의 정갈한 맛 🌿",
        lambda s, l, m: f"조리와 숙성의 정석! {l} {s}에서 경험한 격조 높은 {m} 🍲",
        lambda s, l, m: f"[{l} 정통 맛집] 세심한 밸런스가 돋보이는 {s}의 시그니처 {m} 🎖️",
        lambda s, l, m: f"기대 이상의 완성도와 품격, {l} {s} {m} 방문 리포트 ☕"
    ],
    "honest": [
        lambda s, l, m: f"[{l} 내돈내산] 소문난 {s} 솔직 후기! {m} 진짜 맛있을까? 💳",
        lambda s, l, m: f"1원도 안 아까웠던 {l} 찐맛집 '{s}'! {m} 현실 방문 솔직평 👍",
        lambda s, l, m: f"웨이팅 할 가치 충분할까? {l} {s} {m} 내돈내산 팩트체크 👀",
        lambda s, l, m: f"솔직히 말씀드리면, {l} {s}의 {m}는 기대 이상이었습니다 💬",
        lambda s, l, m: f"[{l} 솔직 리뷰] 재방문 의사 100%! {s} {m}와 주차/웨이팅 팁 💡",
        lambda s, l, m: f"현지인 친구 추천으로 다녀온 {l} {s}! {m} 먹어본 솔직 체감 😋"
    ],
    "healing": [
        lambda s, l, m: f"[{l} 힐링 스팟] 지친 일상에 다정한 온기를 전해준 {s} {m} 🌿",
        lambda s, l, m: f"마음까지 포근해지는 정갈한 한 끼, {l} {s}에서 즐긴 {m} 🌸",
        lambda s, l, m: f"바쁜 일상 속 작은 쉼표! {l} 감성 맛집 {s} {m} 솔직 방문기 🌤️",
        lambda s, l, m: f"소중한 사람과 함께 도란도란 나누고 싶은 {l} {s} {m} 이야기 ☕",
        lambda s, l, m: f"은은한 분위기 속에서 누린 행복한 시간, {l} {s} {m} 힐링 후기 💫",
        lambda s, l, m: f"따뜻한 정성과 온기가 가득했던 {l} {s}, {m}로 채운 위로 🥰"
    ],
    "worker": [
        lambda s, l, m: f"[{l} 퇴근길 힐링] 오늘 하루 수고한 나를 위한 보상! {s} {m} ⚡",
        lambda s, l, m: f"직장인 스트레스 단번에 날려준 {l} 찐맛집 '{s}' {m} 🍺",
        lambda s, l, m: f"푸짐한 양과 깊은 감칠맛! {l} 직장인 추천 맛집 {s} {m} 🥢",
        lambda s, l, m: f"퇴근 후 한 잔 곁들이기 완벽했던 {l} {s}, 푸짐한 {m} 대만족 👏",
        lambda s, l, m: f"[{l} 회식/모임 추천] 팀원들 모두 극찬한 {s} 대표메뉴 {m} 🍚",
        lambda s, l, m: f"하루의 피로가 싹 가시는 든든한 한 끼! {l} {s} {m} 정복기 🔥"
    ],
    "local": [
        lambda s, l, m: f"[{l} 노포 탐방] 세월이 빚어낸 깊은 손맛! {s} {m}의 진수 🏮",
        lambda s, l, m: f"골목길 숨은 고수의 아우라! {l} 찐 로컬 맛집 '{s}' {m} 🍲",
        lambda s, l, m: f"단골들이 남몰래 아껴두는 {l} 식당, {s}의 푸근한 {m} 🌾",
        lambda s, l, m: f"오랜 전통과 넉넉한 인심이 살아있는 {l} {s}, 변함없는 {m} 맛 👵",
        lambda s, l, m: f"[{l} 숨은 맛집] 소박하지만 압도적인 내공! {s} {m} 방문기 💯",
        lambda s, l, m: f"할머니 손맛처럼 정겨운 깊은 풍미, {l} {s} {m} 솔직 후기 👍"
    ]
}
