// --- START OF FILE static/js/app.js ---

import { api } from './api.js';
import { CHART_DEFINITIONS, HIDDEN_TOOLS } from './config.js';
import { drawChart, renderEWTView } from './charts.js';

import Sidebar from './components/Sidebar.js';
import MainView from './components/MainView.js';
import EWTOverlay from './components/EWTOverlay.js';
import DynoView from './components/DynoView.js';
import LevelView from './components/LevelView.js';

const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

// 防抖函数：防止频繁触发分析请求
function debounce(fn, delay) {
    let timer; 
    return function(...args) { 
        clearTimeout(timer); 
        timer = setTimeout(() => fn.apply(this, args), delay); 
    }
}

const App = {
    components: { Sidebar, MainView, EWTOverlay, DynoView, LevelView },
    
    template: `
    <div id="app-root" style="height: 100vh; display: flex; flex-direction: column; overflow: hidden;">
        <!-- Header -->
        <div class="header" style="flex-shrink: 0;">
            <div class="logo"><span></span><span>Signal Platform & Oil Dyno</span></div>
            
            <div style="font-size: 12px; opacity: 0.9;">
                <span v-if="loading"><i class="el-icon-loading"></i> 处理中...</span>
                <span v-else>
                    {{ headerTitle }}
                </span>
            </div>
            
            <div class="filter-mode-switch" :class="{active: isFilterMode}" v-if="activeMode === 'file' && !isMultiMode && selectedFiles.length === 1">
                <span style="font-size:12px;">谱峰去除模式</span>
                <el-switch v-model="isFilterMode" size="small" active-color="#ff4d4f" inactive-color="#ffffff40"></el-switch>
            </div>
            <div v-else style="width: 120px;"></div>
        </div>

        <div class="container" style="flex: 1; display: flex; overflow-y: auto;">
            <!-- 左侧边栏 -->
            <Sidebar 
                :file-list="fileList" 
                :current-path="currentPath" 
                :selected-files="selectedFiles"
                :is-multi-mode="isMultiMode"
                :loading-files="loadingFiles"
                :tools="tools"
                :active-mode="activeMode"
                :search-loading="searchLoading"
                @load-files="loadFiles"
                @go-up="goUp"
                @select-file="handleSingleClick"
                @toggle-file="toggleFile"
                @open-ewt="openEWT"
                @change-mode="switchMode"
                @search-well="searchWell"
                @load-dyno="loadDynoData"
            />

            <!-- 主内容区 -->
            <div style="flex: 1; overflow-y: auto; overflow-x: hidden; position: relative; background-color: #f0f2f5; height: 100%;">
                
                <!-- 1. 文件分析模式 -->
                <MainView v-if="activeMode === 'file'"
                    :selected-files="selectedFiles"
                    :is-multi-mode="isMultiMode"
                    :compare-axis="compareAxis"
                    :active-chart-types="activeChartTypes"
                    :filter-result="filterResult"
                    :is-filter-mode="isFilterMode"
                    :get-file-name="getFileName"
                    @clear-selection="selectedFiles=[]"
                    @update:compare-axis="compareAxis = $event"
                />

                <!-- 2. 数据库-功图模式 -->
                <DynoView v-else-if="activeMode === 'db'"
                    :diagrams="dynoDiagrams"
                    :loading="loading"
                    :well-info="currentWellInfo"
                />

                <!-- 3. 数据库-动液面计算模式 -->
                <div v-else-if="activeMode === 'level'" style="height:100%">
                    <div v-if="!currentWellInfo" style="display:flex; height:100%; align-items:center; justify-content:center; color:#999; flex-direction:column;">
                        <div style="font-size:40px; margin-bottom:20px;">🌊</div>
                        <div>请在左侧搜索并选择一口油井以开始计算</div>
                    </div>
                    <LevelView v-else :well-info="currentWellInfo" />
                </div>

            </div>
        </div>

        <!-- EWT 弹窗覆盖层 -->
        <EWTOverlay
            :show="showEWT"
            :loading="ewtLoading"
            :n="ewtN"
            :axis="ewtAxis"
            :data="ewtData"
            :selected-file-name="getFileName(selectedFiles[0])"
            @close="showEWT=false"
            @update:n="ewtN = $event"
            @update:axis="ewtAxis=$event"
            @run="runEWT"
        />
    </div>
    `,
    
    setup() {
        // --- 状态定义 ---
        const activeMode = ref('file'); // 'file', 'db', 'level'
        const fileList = ref([]);
        const currentPath = ref("");
        const selectedFiles = ref([]);
        const tools = ref([]);
        
        const loading = ref(false);
        const loadingFiles = ref(false);
        
        const compareAxis = ref("X");
        const singleResult = ref(null);
        const multiResult = ref(null);
        
        // EWT 状态
        const showEWT = ref(false);
        const ewtN = ref(3);
        const ewtLoading = ref(false);
        const ewtAxis = ref("X");
        const ewtData = ref({});
        
        // 滤波模式状态
        const isFilterMode = ref(false);
        const filterRange = ref(null);
        const filterResult = ref(null);

        // 数据库模式状态
        const searchLoading = ref(false);
        const dynoDiagrams = ref([]);
        const currentWellInfo = ref(null);

        // --- 计算属性 ---
        const isMultiMode = computed(() => selectedFiles.value.length > 1);
        
        const headerTitle = computed(() => {
            if (activeMode.value === 'file') return isMultiMode.value ? '多文件对比' : '单文件精细模式';
            if (activeMode.value === 'db') return '油井功图数据库';
            if (activeMode.value === 'level') return '动液面机理计算';
            return '';
        });

        // 动态计算需要显示的图表列表
        const activeChartTypes = computed(() => {
            const enabledToolIds = tools.value.filter(t => t.enabled).map(t => t.id);
            let charts = CHART_DEFINITIONS.filter(def => enabledToolIds.includes(def.toolId));
            
            // 只有存在滤波结果时，才显示“滤除后波形”
            if (filterResult.value) {
                const fChart = CHART_DEFINITIONS.find(c => c.id === 'filtered_time');
                if (fChart && !charts.includes(fChart)) charts.push(fChart);
            } else {
                charts = charts.filter(c => c.id !== 'filtered_time');
            }
            
            // 多文件对比模式下，隐藏热力图和3D图（因为很难在同一坐标系叠加）
            if (isMultiMode.value) charts = charts.filter(c => !c.isHeatmap && !c.is3D);
            
            return charts;
        });

        const getFileName = (p) => p ? p.split('/').pop() : '';

        // --- 核心逻辑: 文件操作 ---
        
        const loadFiles = async (p) => { 
            loadingFiles.value = true; 
            try { 
                const res = await api.listFiles(p); 
                fileList.value = res.data; 
                currentPath.value = p; 
            } finally { 
                loadingFiles.value = false; 
            } 
        };
        
        const loadTools = async () => { 
            try { 
                const res = await api.getTools(); 
                // 过滤掉隐藏工具，并为工具初始化默认参数
                tools.value = res.data
                    .filter(t => !HIDDEN_TOOLS.includes(t.id))
                    .map(t => ({ 
                        ...t, 
                        enabled: true, 
                        values: Object.keys(t.params).reduce((acc, k) => { 
                            acc[k] = t.params[k].default; 
                            return acc; 
                        }, {}) 
                    })); 
            } catch(e) {
                console.error("Failed to load tools", e);
            } 
        };
        
        const handleSingleClick = (item) => { 
            if(item.is_dir) {
                loadFiles(item.name); 
            } else {
                // 单选逻辑
                if (activeMode.value !== 'file') activeMode.value = 'file';
                selectedFiles.value = [item.name]; 
            }
        };
        
        const toggleFile = (name) => { 
            const idx = selectedFiles.value.indexOf(name); 
            if(idx > -1) selectedFiles.value.splice(idx, 1); 
            else selectedFiles.value.push(name); 
        };
        
        const goUp = () => { 
            if(!currentPath.value) return; 
            let p = currentPath.value.split('/').filter(x=>x); 
            p.pop(); 
            loadFiles(p.length ? p.join('/')+'/' : ''); 
        };
        
        const switchMode = (mode) => {
            activeMode.value = mode;
        };

        // --- 核心逻辑: 分析与绘图 (修复部分) ---

        // 1. 发送分析请求
        const runAnalysis = async () => {
            // 前置检查
            if (activeMode.value !== 'file' || selectedFiles.value.length === 0) return;

            loading.value = true;
            try {
                // 构造任务参数：只发送已启用的工具
                const tasks = tools.value
                    .filter(t => t.enabled)
                    .map(t => ({ id: t.id, params: t.values }));

                // 如果是滤波交互模式，需要把BandStopProcessor加进去
                if (isFilterMode.value && filterRange.value) {
                    tasks.push({
                        id: 'BandStopProcessor',
                        params: {
                            low_freq: filterRange.value.min,
                            high_freq: filterRange.value.max,
                            order: 4
                        }
                    });
                }

                if (isMultiMode.value) {
                    // --- 多文件模式 ---
                    const res = await api.analyzeMulti(selectedFiles.value, tasks, compareAxis.value);
                    multiResult.value = res.data;
                    singleResult.value = null;
                } else {
                    // --- 单文件模式 ---
                    const res = await api.analyze(selectedFiles.value[0], tasks);
                    singleResult.value = res.data.results;
                    multiResult.value = null;
                    
                    // 提取滤波结果以便显示KPI
                    if (isFilterMode.value) {
                        const bandStopRes = {};
                        ['X','Y','Z'].forEach(ax => {
                            const found = res.data.results[ax]?.find(r => r.tool_id === 'BandStopProcessor');
                            if (found && found.output && !found.output.error) {
                                bandStopRes[ax] = found.output;
                            }
                        });
                        filterResult.value = Object.keys(bandStopRes).length ? bandStopRes : null;
                    } else {
                        filterResult.value = null;
                    }
                }

                // 数据更新后，等待 DOM 渲染完成，再绘图
                nextTick(() => {
                    renderAllCharts();
                });

            } catch (e) {
                console.error("Analysis failed:", e);
                ElementPlus.ElMessage.error("分析请求失败: " + (e.response?.data?.detail || e.message));
            } finally {
                loading.value = false;
            }
        };

        // 2. 渲染所有图表
        const renderAllCharts = () => {
            // 遍历所有需要展示的图表配置
            activeChartTypes.value.forEach(chartConfig => {
                const containerId = 'chart-' + chartConfig.id;
                
                // 准备上下文数据
                const ctx = {
                    isMultiMode: isMultiMode.value,
                    selectedFiles: selectedFiles.value,
                    singleResult: singleResult.value,
                    multiResult: multiResult.value,
                    compareAxis: compareAxis.value,
                    isFilterMode: isFilterMode.value,
                    filterResult: filterResult.value
                };

                // 交互回调（例如：在频谱图上框选）
                const onBrushCallback = (range) => {
                    if (range) {
                        filterRange.value = range;
                        // 框选后自动触发重新分析（带滤波参数）
                        runAnalysis();
                        ElementPlus.ElMessage.success(`已应用滤波: ${range.min.toFixed(1)} - ${range.max.toFixed(1)} Hz`);
                    }
                };

                // 调用 charts.js 里的通用绘图函数
                drawChart(containerId, chartConfig, ctx, onBrushCallback);
            });
        };

        // --- EWT (经验小波变换) 逻辑 ---
        
        const openEWT = () => {
            showEWT.value = true;
            if (Object.keys(ewtData.value).length === 0) {
                runEWT();
            } else {
                // 如果已有数据，重新渲染一下Tab内的图表
                nextTick(() => renderEWTView(ewtData.value, ewtAxis.value));
            }
        };

        const runEWT = async () => {
            if (selectedFiles.value.length !== 1) return;
            
            ewtLoading.value = true;
            try {
                // 单独调用 EWT 工具
                const res = await api.analyze(selectedFiles.value[0], [{
                    id: "EWTProcessor",
                    params: { num_modes: ewtN.value }
                }]);
                
                // 处理返回数据结构: { X: [...], Y: [...], ... }
                const result = {};
                ['X', 'Y', 'Z'].forEach(axis => {
                    const taskRes = res.data.results[axis]?.find(t => t.tool_id === "EWTProcessor");
                    if (taskRes && taskRes.output && !taskRes.output.error) {
                        result[axis] = taskRes.output;
                    }
                });
                
                ewtData.value = result;
                
                // 渲染 EWT 视图
                nextTick(() => {
                    renderEWTView(ewtData.value, ewtAxis.value);
                });
                
            } catch(e) {
                ElementPlus.ElMessage.error("EWT 分解失败");
            } finally {
                ewtLoading.value = false;
            }
        };
        
        // 监听 EWT Tab 切换，重绘图表防止宽度异常
        watch(ewtAxis, () => {
            if(showEWT.value) {
                nextTick(() => renderEWTView(ewtData.value, ewtAxis.value));
            }
        });

        // --- 数据库与油井逻辑 ---
        
        const searchWell = async (query, callback) => {
            searchLoading.value = true;
            try {
                const res = await api.lookupWell(query);
                if(res.data.found) {
                    currentWellInfo.value = res.data; // 保存当前选中的井
                }
                if (callback) callback(res.data);
            } catch(e) {
                if (callback) callback({ found: false, message: "服务器请求失败" });
            } finally {
                searchLoading.value = false;
            }
        };

        const loadDynoData = async (params) => {
            loading.value = true;
            currentWellInfo.value = params.info; 
            dynoDiagrams.value = [];
            try {
                const res = await api.getDiagrams(params.wellId, params.start, params.end, params.perDay);
                dynoDiagrams.value = res.data.diagrams;
            } catch(e) {
                console.error(e);
                ElementPlus.ElMessage.error("功图数据加载失败");
            } finally {
                loading.value = false;
            }
        };

        // --- 生命周期与监听器 ---

        // 使用防抖，避免拖动参数滑块时频繁请求
        const debouncedRun = debounce(runAnalysis, 800);
        
        // 监听文件选择变化 -> 触发分析
        watch(selectedFiles, () => { 
            if(activeMode.value === 'file') runAnalysis(); 
        }, { deep: true });
        
        // 监听工具参数变化 -> 触发分析
        watch(tools, debouncedRun, { deep: true });
        
        // 监听模式切换
        watch(activeMode, (newVal) => {
            if(newVal === 'file' && selectedFiles.value.length > 0) {
                // 切回文件模式时，重新渲染图表 (防止 Canvas 丢失)
                nextTick(renderAllCharts); 
            }
        });

        // 新增：监听对比轴变化 -> 仅重绘图表 (不需要重新请求后端)
        watch(compareAxis, () => {
            if (activeMode.value === 'file' && isMultiMode.value) {
                nextTick(renderAllCharts);
            }
        });

        // 初始化
        onMounted(() => { 
            loadFiles(""); 
            loadTools(); 
        });

        return {
            // Data
            fileList, currentPath, selectedFiles, loadingFiles, tools, loading,
            compareAxis, isMultiMode, activeChartTypes, activeMode,
            headerTitle,
            
            // EWT
            showEWT, ewtN, ewtLoading, ewtAxis, ewtData, 
            
            // Filter
            isFilterMode, filterResult,
            
            // DB
            searchLoading, dynoDiagrams, currentWellInfo,

            // Methods
            handleSingleClick, toggleFile, goUp, getFileName, loadFiles, switchMode,
            openEWT, runEWT,
            searchWell, loadDynoData
        };
    }
};

createApp(App).use(ElementPlus).mount('#app');