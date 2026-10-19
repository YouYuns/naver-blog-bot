# -*- coding: utf-8 -*-
"""
전체 사진 카테고리별 서사 풀 통합 모듈 (photo_narratives.py)
"""
from photo_narratives_1 import POOLS_1
from photo_narratives_2 import POOLS_2

PHOTO_CATEGORY_POOLS = {}
PHOTO_CATEGORY_POOLS.update(POOLS_1)
PHOTO_CATEGORY_POOLS.update(POOLS_2)
