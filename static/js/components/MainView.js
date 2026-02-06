export default {
    props: [
        'selectedFiles', 'isMultiMode', 'compareAxis', 'activeChartTypes', 'filterResult', 'isFilterMode', 'getFileName'
    ],
    emits: ['clear-selection', 'update:compareAxis'],
    template: `
    <div class="main">
        <!-- 空状态 -->
        <div v-if="selectedFiles.length === 0" style="text-align:center; margin-top:100px; color:#ccc;">
            <div style="font-size: 80px; margin-bottom: 20px; color: #e8e8e8;"></div>
            <div>点击文件名查看详情，或勾选多个进行对比</div>
        </div>

        <div v-else>
            <!-- 状态栏: 多文件 -->
            <div class="status-bar" v-if="isMultiMode">
                <span>已选 <b>{{ selectedFiles.length }}</b> 个文件对比</span>
                <div class="axis-switcher">
                    <span style="font-size:12px; color:#666; margin-right:5px;">对比轴:</span>
                    <div class="axis-btn" :class="{active: compareAxis==='X'}" @click="$emit('update:compareAxis', 'X')">X 轴</div>
                    <div class="axis-btn" :class="{active: compareAxis==='Y'}" @click="$emit('update:compareAxis', 'Y')">Y 轴</div>
                    <div class="axis-btn" :class="{active: compareAxis==='Z'}" @click="$emit('update:compareAxis', 'Z')">Z 轴</div>
                </div>
                <el-button link type="primary" size="small" @click="$emit('clear-selection')">清空</el-button>
            </div>
            
            <!-- 状态栏: 单文件 -->
            <div class="status-bar" v-else style="background: #f6ffed; border-color: #b7eb8f;">
                <span style="color: #389e0d;"><b>单文件模式</b>: {{ getFileName(selectedFiles[0]) }}</span>
                <span style="font-size:12px; color:#666;">
                    {{ isFilterMode ? ' 正在进行交互式滤波...' : '多维特征分析' }}
                </span>
            </div>

            <!-- 图表循环 -->
            <div v-for="chartConfig in activeChartTypes" :key="chartConfig.id" class="chart-card" :style="{ borderTopColor: chartConfig.color }">
                <div class="chart-title" :class="chartConfig.borderClass">
                    {{ chartConfig.title }}
                    <el-tag size="small" effect="plain">{{ isMultiMode ? '对比' : (chartConfig.isHeatmap ? '单文件' : '叠加') }}</el-tag>
                </div>
                
                <!-- 滤波 KPI -->
                <div v-if="chartConfig.id === 'filtered_time' && filterResult" class="kpi-bar">
                    <template v-for="(res, axis) in filterResult" :key="axis">
                        <div class="kpi-item" v-for="(val, key) in res.kpi" :key="axis+key">
                            <span style="color:#333">{{ axis }}轴 {{ key }}:</span> <span class="kpi-value">{{ val }}</span>
                        </div>
                    </template>
                </div>

                <!-- 图表容器 (ID必须保持这种格式供 app.js 调用) -->
                <div :id="'chart-'+chartConfig.id" class="chart-container"></div>
            </div>
        </div>
    </div>
    `
};