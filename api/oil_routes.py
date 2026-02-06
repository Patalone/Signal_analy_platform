# --- START OF FILE api/oil_routes.py ---

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.mysql_connector import mysql_conn
from datetime import datetime, timedelta
import json

# 【新增引用】引入核心计算库
from core.lib.oil_physics import FluidLevelCalculator, WellParams

router = APIRouter()

# ==========================================
# 1. 原有接口 (保持完全一致)
# ==========================================

@router.get("/well/list_all")
async def list_all_wells():
    """
    获取所有已登记的油井列表
    """
    conn = mysql_conn.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, well_name FROM well_info ORDER BY id"
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            wells = []
            for row in rows:
                wells.append({
                    "id": str(row['id']),
                    "name": row['well_name']
                })
            
            return {
                "count": len(wells),
                "wells": wells
            }
    except Exception as e:
        print(f"DB Error: {e}")
        return {"count": 0, "wells": [], "error": str(e)}
    finally:
        conn.close()

@router.get("/well/lookup")
async def lookup_well(query: str = Query(..., description="井号或井名")):
    """
    查找油井信息
    """
    conn = mysql_conn.get_connection()
    try:
        with conn.cursor() as cursor:
            well_id = None
            well_name = query.strip()
            
            if query.strip().isdigit():
                well_id = int(query.strip())
            else:
                for field in ['well_name', 'well_common_name', 'jh', 'name']:
                    try:
                        sql = f"SELECT id, {field} as name FROM well_info WHERE {field} LIKE %s LIMIT 1"
                        cursor.execute(sql, (f"%{query.strip()}%",))
                        row = cursor.fetchone()
                        if row:
                            well_id = row['id']
                            well_name = row.get('name', well_name)
                            break
                    except: continue
            
            if not well_id:
                return {"found": False, "message": "未找到该井"}

            sql = "SELECT COUNT(*) as cnt, MIN(collection_time) as min_t, MAX(collection_time) as max_t FROM data_graph WHERE well_id = %s"
            cursor.execute(sql, (well_id,))
            stats = cursor.fetchone()
            
            if not stats or stats['cnt'] == 0:
                return {"found": False, "message": "该井无功图数据"}
                
            return {
                "found": True,
                "well_id": well_id,
                "well_name": well_name,
                "record_count": stats['cnt'],
                "min_date": stats['min_t'].strftime("%Y-%m-%d") if stats['min_t'] else None,
                "max_date": stats['max_t'].strftime("%Y-%m-%d") if stats['max_t'] else None
            }
    except Exception as e:
        print(f"DB Error: {e}")
        return {"found": False, "message": str(e)}
    finally:
        conn.close()

@router.get("/well/{well_id}/diagrams")
async def get_diagrams(
    well_id: int,
    start_date: str,
    end_date: str,
    per_day: int = 1
):
    """
    获取功图数据
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    except:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    conn = mysql_conn.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    t.id, t.collection_time, t.wy, t.zh, t.s, t.cc, t.condition_id,
                    wc.condition_name
                FROM (
                    SELECT 
                        id, collection_time, wy, zh, s, cc, condition_id,
                        ROW_NUMBER() OVER (PARTITION BY DATE(collection_time) ORDER BY collection_time) as rn
                    FROM data_graph
                    WHERE well_id = %s 
                      AND collection_time >= %s AND collection_time < %s
                      AND error_data != 1
                ) t 
                LEFT JOIN well_condition wc ON t.condition_id = wc.id
                WHERE t.rn <= %s 
                ORDER BY t.collection_time
            """
            cursor.execute(sql, (well_id, start_dt, end_dt, per_day))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                try:
                    wy = json.loads(row['wy']) if isinstance(row['wy'], str) else row['wy']
                    zh = json.loads(row['zh']) if isinstance(row['zh'], str) else row['zh']
                    
                    if not wy or not zh: continue
                    
                    cond_name = row.get('condition_name')
                    if not cond_name:
                         cond_name = "未知"
                    
                    results.append({
                        "id": row['id'],
                        "time": row['collection_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        "wy": wy,
                        "zh": zh,
                        "condition": cond_name,
                        "stroke": row.get('s'),
                        "frequency": row.get('cc')
                    })
                except Exception as e: 
                    continue
                
            return {"diagrams": results}
    finally:
        conn.close()


# ==========================================
# 2. 【新增接口】动液面计算相关
# ==========================================

@router.get("/well/{well_id}/detail")
async def get_well_detail(well_id: int):
    """
    获取单口井的详细参数（融合静态管柱信息和最新动态生产数据）
    """
    conn = mysql_conn.get_connection()
    try:
        with conn.cursor() as cursor:
            # 联表查询：well_column (静态管柱) + data_graph (最新一条动态)
            # 注意：well_column 是通常存储泵深、套管尺寸的表。
            # 如果你的数据库里没有 well_column，请根据实际表名修改（例如 well_structure 等）
            sql = """
                SELECT 
                    wc.well_id,
                    wc.bs   as pump_depth,        -- 泵深
                    wc.wgs  as tail_depth,        -- 尾管深
                    wc.tgwj as casing_od,         -- 套管外径
                    wc.ygnj as tubing_id,         -- 油管内径
                    wc.md_yy as oil_density,      -- 原油相对密度
                    wc.md_trq as gas_density,     -- 天然气相对密度
                    
                    dg.id as diagram_id,
                    dg.ty as casing_pressure,     -- 套压
                    dg.hy as tubing_pressure,     -- 油压/回压
                    dg.hs as water_cut,           -- 含水
                    dg.jkwd as temp_wellhead,     -- 井口温度
                    dg.cyl_ss as liquid_prod,     -- 瞬时产液量
                    dg.collection_time
                    
                FROM well_column wc
                LEFT JOIN (
                    SELECT * 
                    FROM data_graph 
                    WHERE well_id = %s 
                    ORDER BY collection_time DESC 
                    LIMIT 1
                ) dg ON wc.well_id = dg.well_id
                
                WHERE wc.well_id = %s
            """
            
            cursor.execute(sql, (well_id, well_id))
            row = cursor.fetchone()
            
            if not row:
                return {"status": "error", "message": "该井未录入管柱数据(well_column)，无法进行机理计算"}
            
            # 数据清洗与默认值填充 (处理 NULL)
            data = {
                "well_id": row['well_id'],
                # --- 核心计算参数 ---
                "pump_depth": float(row['pump_depth'] or 2000),       
                "casing_pressure": float(row['casing_pressure'] or 0.0), 
                "tubing_pressure": float(row['tubing_pressure'] or 0.0), 
                "water_cut": float(row['water_cut'] or 0.0),       
                "temp_wellhead": float(row['temp_wellhead'] or 20),
                "temp_bottom": 80.0, # 井底温度默认值（如果数据库没字段）
                
                # --- 物理参数 ---
                "oil_density": float(row['oil_density'] or 0.85),
                "gas_density": float(row['gas_density'] or 0.7),
                "liquid_prod": float(row['liquid_prod'] or 10.0), # 产液量
                
                # --- 附加信息 ---
                "latest_time": row['collection_time'].strftime("%Y-%m-%d %H:%M:%S") if row['collection_time'] else "无生产数据"
            }
            
            return {
                "status": "success",
                "data": data
            }
            
    except Exception as e:
        print(f"DB Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


class LevelCalcRequest(BaseModel):
    well_id: int
    pump_depth: float
    casing_pressure: float 
    tubing_pressure: float
    water_cut: float
    temp_wellhead: float
    temp_bottom: float
    oil_density: float = 0.85
    gas_density: float = 0.7
    liquid_prod: float = 10.0

@router.post("/well/calc_level")
async def calculate_level(req: LevelCalcRequest):
    """
    机理模型计算动液面
    """
    try:
        # 1. 组装参数对象
        params = WellParams(
            pump_depth=req.pump_depth,
            casing_pressure=req.casing_pressure,
            tubing_pressure=req.tubing_pressure,
            water_cut=req.water_cut,
            oil_density=req.oil_density, 
            gas_density=req.gas_density,
            temp_wellhead=req.temp_wellhead,
            temp_bottom=req.temp_bottom,
            prod_liquid=req.liquid_prod
        )
        
        # 2. 估算泵吸入口压力 (此处仅为模拟，实际应结合功图计算)
        # 简单的经验估算：套压 + 一定液柱压力
        simulated_pump_inlet_p = req.casing_pressure + 2.0 + (req.water_cut * 0.5)

        # 3. 执行核心计算
        calculator = FluidLevelCalculator(params)
        result = calculator.solve_dynamic_level(simulated_pump_inlet_p)
        
        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@router.post("/well/ai_predict_level")
async def ai_predict_level(req: LevelCalcRequest):
    """
    AI 预测动液面 (Mock 接口)
    """
    import time
    import random
    time.sleep(0.5) 
    
    # 模拟预测值：在机理计算附近波动
    predicted_level = req.pump_depth * random.uniform(0.6, 0.8)
    
    return {
        "status": "success",
        "method": "LSTM_TimeSeries_v1",
        "prediction": {
            "level": round(predicted_level, 2),
            "confidence": 0.92
        }
    }