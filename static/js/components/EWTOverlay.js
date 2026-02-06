// --- START OF FILE static/js/EWTOverlay.js ---

export default {
    props: ['show', 'loading', 'n', 'axis', 'data', 'selectedFileName'],
    emits: ['close', 'update:n', 'run', 'update:axis'],
    template: `
    <div class="ewt-page" :class="{active: show}">
        <div class="ewt-header">
            <div style="font-weight:bold; display:flex; align-items:center;">
                <el-button circle size="small" @click="$emit('close')" style="margin-right:10px;">←</el-button>
                EWT 深度模态分解视图 
                <span style="font-weight:normal; margin-left:10px; color:#666; font-size:12px;">{{ selectedFileName }}</span>
            </div>
            <div>
                <span style="font-size:14px; margin-right:10px;">N:</span>
                <el-input-number :model-value="n" @update:model-value="$emit('update:n', $event)" 
                                 size="small" :min="2" :max="8" @change="$emit('run')"></el-input-number>
                <el-button type="primary" size="small" @click="$emit('run')" :loading="loading" style="margin-left:10px;">重新分解</el-button>
            </div>
        </div>
        
        <div class="ewt-body" v-loading="loading">
            <el-tabs :model-value="axis" @update:model-value="$emit('update:axis', $event)">
                <el-tab-pane v-for="ax in ['X','Y','Z']" :key="ax" :label="ax+'轴'" :name="ax">
                    <!-- 频谱划分 -->
                    <div class="chart-card">
                        <!-- [修复点] 增加 width: 100% -->
                        <div :id="'ewt-spectrum-'+ax" class="boundary-chart" style="height: 300px; width: 100%;"></div>
                    </div>
                    
                    <!-- 模态波形 -->
                    <div v-if="data[ax]">
                        <div v-for="(mode, idx) in data[ax].modes" :key="idx" class="chart-card" style="margin-top:10px;">
                            <div style="font-size:12px; font-weight:bold; color:#666;">{{ mode.name }}</div>
                            <!-- [修复点] 增加 width: 100% -->
                            <div :id="'ewt-mode-'+ax+'-'+idx" class="mode-chart" style="height: 200px; width: 100%;"></div>
                        </div>
                    </div>
                </el-tab-pane>
            </el-tabs>
        </div>
    </div>
    `
};