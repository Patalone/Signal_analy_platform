from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.connector import minio_conn
from core.factory import get_processor
import pkgutil
import processors
import inspect
import traceback
import importlib # <--- 使用标准库导入

router = APIRouter()

# --- 定义请求体模型 ---
class AnalysisTask(BaseModel):
    id: str               
    params: Dict[str, Any] = {} 

class AnalysisRequest(BaseModel):
    file_path: str        
    tasks: List[AnalysisTask] 

class MultiAnalysisRequest(BaseModel):
    file_paths: List[str]     
    tasks: List[AnalysisTask] 
    target_axis: str = "X"    

# --- 辅助函数：自动扫描工具 ---
def scan_tools():
    tools_list = []
    # 遍历 processors 包下的所有模块
    for _, module_name, _ in pkgutil.iter_modules(processors.__path__):
        try:
            # 使用 importlib 动态导入
            module = importlib.import_module(f"processors.{module_name}")
            # 遍历模块中的所有成员
            for name, obj in inspect.getmembers(module):
                # 必须是类，且有 get_metadata 方法，且不是基类本身
                if inspect.isclass(obj) and hasattr(obj, 'get_metadata') and name != "SignalProcessor":
                    try:
                        meta = obj.get_metadata()
                        meta['id'] = name 
                        tools_list.append(meta)
                    except:
                        continue
        except Exception as e:
            print(f"Loading module {module_name} failed: {e}")
    return tools_list

# --- 接口定义 ---

@router.get("/tools")
async def get_tools():
    return scan_tools()

@router.post("/analyze")
async def run_analysis(request: AnalysisRequest):
    """单文件分析接口"""
    try:
        print(f"[Analyze] Loading file: {request.file_path}")
        parsed_data = minio_conn.get_file_data(request.file_path)
        
        df_norm = parsed_data['df_norm']
        fs = parsed_data['fs']
        metadata = parsed_data['meta']
        
        final_response = {
            "file_info": metadata,
            "fs": fs,
            "results": {} 
        }
        
        for axis in df_norm.columns:
            signal = df_norm[axis].values
            axis_results = []
            
            for task in request.tasks:
                try:
                    run_params = task.params.copy()
                    run_params['fs'] = fs
                    
                    processor_class = get_processor(task.id)
                    result = processor_class.process(signal, run_params)
                    
                    axis_results.append({
                        "tool_id": task.id,
                        "tool_name": processor_class.get_metadata().get('name'),
                        "output": result
                    })
                except Exception as e:
                    print(f"    ! Task {task.id} failed: {e}")
                    axis_results.append({
                        "tool_id": task.id,
                        "error": str(e)
                    })
            
            final_response["results"][axis] = axis_results
            
        minio_conn.save_analysis_history(request.file_path, "dynamic_analysis")
        return final_response

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/multi")
async def run_multi_analysis(request: MultiAnalysisRequest):
    """多文件对比分析接口"""
    try:
        final_response = {}
        
        for file_path in request.file_paths:
            file_name = file_path.split('/')[-1]
            try:
                # 1. 读取数据
                parsed_data = minio_conn.get_file_data(file_path)
                df_norm = parsed_data['df_norm']
                fs = parsed_data['fs']
                
                file_result = {}
                
                # 2. 遍历轴
                for axis in df_norm.columns:
                    signal = df_norm[axis].values
                    axis_task_results = []
                    
                    # 3. 执行任务
                    for task in request.tasks:
                        try:
                            run_params = task.params.copy()
                            run_params['fs'] = fs
                            
                            processor_class = get_processor(task.id)
                            res = processor_class.process(signal, run_params)
                            
                            axis_task_results.append({
                                "tool_id": task.id,
                                "output": res
                            })
                        except Exception as e:
                            print(f"Task error in {file_name} [{task.id}]: {e}")
                            # 返回错误信息，保持格式一致，这样前端不会报错，只是该文件该图表为空
                            axis_task_results.append({
                                "tool_id": task.id,
                                "error": str(e)
                            })
                    
                    file_result[axis] = axis_task_results
                
                final_response[file_name] = file_result
                
            except Exception as e:
                print(f"File error {file_name}: {e}")
                final_response[file_name] = {"error": str(e)}
                
        return final_response

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/list")
async def list_files(prefix: str = ""):
    return minio_conn.list_objects(prefix)

@router.get("/files/history")
async def get_history():
    return minio_conn.get_analysis_history()