// --- START OF FILE static/js/api.js ---

const API_BASE = ""; // 相对路径

export const api = {
    // ================= 原有接口: 文件分析 =================
    // 获取文件列表
    listFiles: (prefix) => axios.get(`${API_BASE}/files/list`, { params: { prefix } }),
    
    // 获取可用工具
    getTools: () => axios.get(`${API_BASE}/tools`),
    
    // 单文件分析
    analyze: (filePath, tasks) => axios.post(`${API_BASE}/analyze`, {
        file_path: filePath,
        tasks: tasks
    }),
    
    // 多文件对比分析
    analyzeMulti: (filePaths, tasks, targetAxis) => axios.post(`${API_BASE}/analyze/multi`, {
        file_paths: filePaths,
        tasks: tasks,
        target_axis: targetAxis
    }),

    // ================= 新增接口: 油井数据库 =================
    // 查找油井
    lookupWell: (query) => axios.get(`${API_BASE}/well/lookup`, { params: { query } }),
    
    // 获取功图数据
    getDiagrams: (wellId, start, end, perDay) => axios.get(`${API_BASE}/well/${wellId}/diagrams`, {
        params: { 
            start_date: start, 
            end_date: end, 
            per_day: perDay 
        }
    })
};