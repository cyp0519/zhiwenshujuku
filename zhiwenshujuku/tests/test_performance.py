"""
智问数据库 — 数据库性能诊断与索引调优单元测试
"""

import pytest
import re

def test_explain_query_plan(db_manager):
    """测试执行计划解析与全表扫描识别"""
    # 无索引字段过滤，应当触发全表扫描 (SCAN TABLE movies)
    sql = "SELECT * FROM movies WHERE rating > 8.0"
    result = db_manager.explain_query(sql)
    
    assert result["success"] is True
    assert result["has_table_scan"] is True
    assert "movies" in result["scan_tables"]
    assert len(result["raw_plan"]) > 0

    # 包含主键过滤，不应当是全表扫描
    sql_pk = "SELECT * FROM movies WHERE id = 1"
    result_pk = db_manager.explain_query(sql_pk)
    
    assert result_pk["success"] is True
    # 主键过滤应该使用索引（Rowid/PK），因此不应包含全表扫描 SCAN TABLE
    # 注意：SQLite 有可能显示 SEARCH TABLE movies USING INTEGER PRIMARY KEY
    assert not any("SCAN" in r.get("detail", "") for r in result_pk["raw_plan"])


def test_create_and_drop_index(db_manager):
    """测试索引创建、读取与删除"""
    # 1. 确认初始没有自定义索引
    initial_indexes = db_manager.get_indexes()
    custom_indexes = [idx for idx in initial_indexes if idx["is_custom"]]
    assert len(custom_indexes) == 0

    # 2. 在 movies(rating) 字段上创建索引
    idx_name = "idx_movies_rating"
    create_res = db_manager.create_index("movies", "rating", idx_name)
    assert create_res["success"] is True

    # 3. 验证索引是否已存在且被标记为自定义
    current_indexes = db_manager.get_indexes()
    matching = [idx for idx in current_indexes if idx["index_name"] == idx_name]
    assert len(matching) == 1
    assert matching[0]["is_custom"] is True
    assert matching[0]["table_name"] == "movies"

    # 4. 删除索引
    drop_res = db_manager.drop_index(idx_name)
    assert drop_res["success"] is True

    # 5. 验证索引已被移除
    final_indexes = db_manager.get_indexes()
    matching_final = [idx for idx in final_indexes if idx["index_name"] == idx_name]
    assert len(matching_final) == 0


def test_optimization_effect(db_manager):
    """测试创建索引后对执行计划的优化效果"""
    sql = "SELECT * FROM reviews WHERE rating = 8.0"
    
    # 优化前：应该是 SCAN TABLE reviews
    result_before = db_manager.explain_query(sql)
    assert result_before["has_table_scan"] is True
    assert "reviews" in result_before["scan_tables"]
    
    # 创建索引
    idx_name = "idx_reviews_rating"
    db_manager.create_index("reviews", "rating", idx_name)
    
    # 优化后：应该是 USING INDEX
    result_after = db_manager.explain_query(sql)
    # 因为建了索引，对 rating 的过滤就不应该是 SCAN TABLE
    assert result_after["has_table_scan"] is False
    assert len(result_after["scan_tables"]) == 0
    
    # 检查详细计划中是否使用了该索引
    has_index_usage = False
    for r in result_after["raw_plan"]:
        detail = r.get("detail", "")
        if "USING INDEX idx_reviews_rating" in detail or "USING COVERING INDEX idx_reviews_rating" in detail:
            has_index_usage = True
            break
    assert has_index_usage is True

    # 清理索引
    db_manager.drop_index(idx_name)
