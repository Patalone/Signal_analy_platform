// --- START OF FILE static/js/components/Sidebar.js ---

export default {
    props: [
        'fileList', 'currentPath', 'selectedFiles', 'isMultiMode', 'loadingFiles', 'tools', 
        'activeMode', 'searchLoading'
    ],
    emits: [
        'load-files', 'go-up', 'select-file', 'toggle-file', 'open-ewt', 
        'change-mode', 'search-well', 'load-dyno'
    ],
    data() {
        return {
            searchQuery: '',     
            wellResult: null,    
            dateRange: [],       
            perDay: 1            
        }
    },
    template: `
    <div class="sidebar">
        <!-- 1. 顶部模式切换 Tabs -->
        <div class="mode-tabs">
            <div class="mode-tab" :class="{active: activeMode==='file'}" @click="$emit('change-mode', 'file')" title="文件分析">
                📂 文件
            </div>
            <div class="mode-tab" :class="{active: activeMode==='db'}" @click="$emit('change-mode', 'db')" title="功图查询">
                🛢️ 功图
            </div>
            <div class="mode-tab" :class="{active: activeMode==='level'}" @click="$emit('change-mode', 'level')" title="动液面计算">
                🌊 液面
            </div>
        </div>

        <!-- ================= 模式 A: 文件系统 ================= -->
        <div v-if="activeMode === 'file'" style="flex:1; display:flex; flex-direction:column; overflow:hidden;">
            <!-- 路径导航 -->
            <div style="padding: 10px; background: #f9f9f9; border-bottom: 1px solid #eee;">
                <el-input :model-value="currentPath" size="small" readonly>
                    <template #prepend><span @click="$emit('load-files', '')" style="cursor:pointer">🏠</span></template>
                    <template #append><el-button @click="$emit('go-up')">⬆</el-button></template>
                </el-input>
            </div>

            <!-- 文件列表 -->
            <div class="file-browser" v-loading="loadingFiles">
                <div v-for="item in fileList" :key="item.name" class="file-item" 
                     :class="{active: selectedFiles.includes(item.name) && !isMultiMode}">
                    
                    <div class="file-name-area" @click="$emit('select-file', item)">
                        <span style="margin-right: 8px; font-size: 14px;">{{ item.is_dir ? '📁' : '📊' }}</span>
                        <span style="word-break: break-all;">
                            {{ item.name.split('/').filter(Boolean).pop() }}
                        </span>
                    </div>
                    
                    <el-checkbox v-if="!item.is_dir" 
                                 :model-value="selectedFiles.includes(item.name)" 
                                 @change="$emit('toggle-file', item.name)">
                    </el-checkbox>
                </div>
            </div>

            <!-- 工具栏区域 (省略 EWT 和 工具链，保持原样) -->
            <div class="ewt-area">
                <button class="ewt-btn" @click="$emit('open-ewt')" :disabled="selectedFiles.length !== 1">
                    EWT 深度模态分解
                </button>
            </div>
            <div class="tool-panel">
                 <div v-for="tool in tools" :key="tool.id" class="tool-card">
                    <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:bold;">
                        {{ tool.name }} <el-switch v-model="tool.enabled" size="small"></el-switch>
                    </div>
                 </div>
            </div>
        </div>

        <!-- ================= 模式 B & C: 数据库查询通用 ================= -->
        <div v-else style="padding: 15px; flex:1; overflow-y:auto; background: #fff;">
            <!-- 搜索框 -->
            <div class="db-search-box">
                <div style="font-size:12px; font-weight:bold; margin-bottom:5px; color:#333;">🔍 查找油井 ({{ activeMode==='level'?'液面计算':'功图查询' }})</div>
                <el-input v-model="searchQuery" placeholder="输入井号或中文名" size="small" clearable @keyup.enter="handleSearch">
                    <template #append>
                        <el-button @click="handleSearch" :loading="searchLoading">查找</el-button>
                    </template>
                </el-input>
            </div>

            <!-- 搜索结果卡片 -->
            <div v-if="wellResult" class="well-card" :class="{'not-found': !wellResult.found}">
                <div v-if="wellResult.found">
                    <div style="font-size:16px; font-weight:bold; color:#d46b08; display:flex; align-items:center;">
                        <span style="margin-right:5px;">🛢️</span> {{ wellResult.well_name }}
                    </div>
                    <div style="font-size:12px; color:#666; margin-top:8px; line-height:1.6;">
                        <div>ID: <b>{{ wellResult.well_id }}</b></div>
                        <div>记录: <b>{{ wellResult.record_count }}</b> 条</div>
                    </div>
                    
                    <!-- 模式 B (db): 显示日期筛选 -->
                    <div v-if="activeMode === 'db'" style="margin-top:15px; border-top:1px dashed #d9d9d9; padding-top:10px;">
                        <div style="font-size:12px; margin-bottom:5px; font-weight:bold;">📅 日期范围</div>
                        <el-date-picker v-model="dateRange" type="daterange" size="small" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%" />
                        <el-button type="warning" style="width:100%; margin-top:15px;" @click="loadData" :disabled="!dateRange" icon="el-icon-data-line">加载功图</el-button>
                    </div>
                    
                    <!-- 模式 C (level): 提示进入计算 -->
                    <div v-if="activeMode === 'level'" style="margin-top:15px; border-top:1px dashed #d9d9d9; padding-top:10px; color:#1890ff; font-size:13px;">
                        <i class="el-icon-info"></i> 已选中该井，请在右侧设置参数进行计算。
                    </div>
                </div>
                <div v-else style="color: #ff4d4f; font-size: 13px; text-align:center;">
                    <i class="el-icon-error"></i> {{ wellResult.message }}
                </div>
            </div>
        </div>
    </div>
    `,
    methods: {
        async handleSearch() {
            if(!this.searchQuery) return;
            this.$emit('search-well', this.searchQuery, (res) => {
                this.wellResult = res;
                if(res.found && res.max_date) {
                    const end = new Date(res.max_date);
                    const start = new Date(end);
                    start.setDate(start.getDate() - 9);
                    this.dateRange = [start.toISOString().split('T')[0], res.max_date];
                }
            });
        },
        loadData() {
            if(!this.wellResult || !this.dateRange) return;
            this.$emit('load-dyno', {
                wellId: this.wellResult.well_id,
                start: this.dateRange[0],
                end: this.dateRange[1],
                perDay: this.perDay,
                info: this.wellResult
            });
        }
    }
};