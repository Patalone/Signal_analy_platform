// --- START OF FILE static/js/components/LevelView.js ---

import { api } from '../api.js';

export default {
    props: ['wellInfo'], 
    
    template: `
    <div class="level-view" style="display: flex; height: 100%; gap: 15px; padding: 15px;" v-loading="initLoading">
        <!-- 左侧：参数与控制区 -->
        <div class="control-panel" style="width: 350px; background: white; padding: 15px; border-radius: 4px; display: flex; flex-direction: column; box-shadow: 0 1px 4px rgba(0,0,0,0.1);">
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #1890ff; padding-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
                <span>⚙️ 计算参数</span>
                <el-button link type="primary" size="small" @click="fetchWellData" icon="el-icon-refresh">重置</el-button>
            </div>
            
            <div style="font-size:12px; color:#999; margin-bottom:10px;" v-if="wellInfo">
                当前井: {{ wellInfo.well_name }} ({{ form.latest_time }})
            </div>

            <el-form label-position="left" label-width="110px" size="small">
                <el-divider content-position="left">井身结构 (Static)</el-divider>
                <el-form-item label="泵深 (m)">
                    <el-input-number v-model="form.pump_depth" :step="10" style="width:100%"></el-input-number>
                </el-form-item>
                
                <el-divider content-position="left">生产数据 (Dynamic)</el-divider>
                <el-form-item label="套压 (MPa)">
                    <el-input-number v-model="form.casing_pressure" :step="0.01" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item label="回压/油压 (MPa)">
                    <el-input-number v-model="form.tubing_pressure" :step="0.1" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item label="含水率 (0-1)">
                    <el-input-number v-model="form.water_cut" :step="0.01" :max="1" :min="0" style="width:100%"></el-input-number>
                </el-form-item>
                 <el-form-item label="井口温度 (℃)">
                    <el-input-number v-model="form.temp_wellhead" :step="1" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item label="井底温度 (℃)">
                    <el-input-number v-model="form.temp_bottom" :step="1" style="width:100%"></el-input-number>
                </el-form-item>
                <el-form-item label="日产液量 (m³)">
                    <el-input-number v-model="form.liquid_prod" :step="0.5" :min="0" style="width:100%"></el-input-number>
                </el-form-item>
            </el-form>

            <div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px;">
                <el-button type="primary" @click="runPhysicsCalc" :loading="calcLoading">
                    机理模型计算
                </el-button>
                <el-button type="success" @click="runAICalc" :loading="aiLoading" plain>
                    AI 智能预测
                </el-button>
            </div>
        </div>

        <!-- 右侧：可视化结果区 -->
        <div class="result-panel" style="flex: 1; background: white; padding: 15px; border-radius: 4px; display: flex; flex-direction: column; box-shadow: 0 1px 4px rgba(0,0,0,0.1);">
            
            <!-- 结果摘要卡片 -->
            <div class="result-cards" style="display: flex; gap: 20px; margin-bottom: 20px;">
                <div class="res-card" style="background: #e6f7ff; border: 1px solid #91d5ff;">
                    <div class="label">动液面深度</div>
                    <div class="value">{{ result.level !== undefined ? result.level : '--' }} <span class="unit">m</span></div>
                </div>
                <div class="res-card" style="background: #f6ffed; border: 1px solid #b7eb8f;">
                    <div class="label">沉没度</div>
                    <div class="value">{{ result.submergence !== undefined ? result.submergence : '--' }} <span class="unit">m</span></div>
                </div>
                <div class="res-card" style="background: #fff7e6; border: 1px solid #ffd591;">
                    <div class="label">泵吸入口压力</div>
                    <div class="value">{{ result.pump_intake_pressure !== undefined ? result.pump_intake_pressure : '--' }} <span class="unit">MPa</span></div>
                </div>
            </div>

            <!-- 图表容器 -->
            <div id="well-chart" style="flex: 1; min-height: 400px; width: 100%;"></div>
            
            <!-- AI 结果提示 -->
            <div v-if="aiResult" style="margin-top: 10px; padding: 10px; background: #f9f9f9; border-left: 4px solid #52c41a;">
                <span style="font-weight: bold; color: #52c41a;">🤖 AI 预测报告 ({{ aiResult.method }}):</span> 
                预测液面为 <b>{{ aiResult.prediction.level }}m</b> (置信度 {{ aiResult.prediction.confidence * 100 }}%)
            </div>
        </div>
    </div>
    `,
    
    data() {
        return {
            initLoading: false,
            calcLoading: false,
            aiLoading: false,
            form: {
                pump_depth: 2000,
                casing_pressure: 0.5,
                tubing_pressure: 2.0,
                water_cut: 0.8,
                temp_wellhead: 30,
                temp_bottom: 90,
                latest_time: ''
            },
            result: {},
            aiResult: null,
            chartInstance: null
        }
    },
    
    watch: {
        wellInfo: {
            handler(newVal) {
                if(newVal && newVal.well_id) {
                    this.fetchWellData();
                }
            },
            deep: true,
            immediate: true
        }
    },

    methods: {
        async fetchWellData() {
            if (!this.wellInfo || !this.wellInfo.well_id) return;
            
            this.initLoading = true;
            this.result = {}; // 清空上次结果
            this.aiResult = null;
            try {
                // 调用后端 API 获取详情
                const res = await axios.get(`/well/${this.wellInfo.well_id}/detail`); // 使用相对路径，假设 baseURL 已设置或代理
                // 如果没有设置 baseURL，使用 api.js 里的路径，这里假设 app.js 已全局挂载或直接用 axios
                
                if (res.data.status === 'success') {
                    Object.assign(this.form, res.data.data);
                    if(this.chartInstance) this.chartInstance.clear(); // 清空图表
                    this.initChart(); // 重绘坐标轴
                } else {
                    ElementPlus.ElMessage.warning(res.data.message || "获取参数失败");
                }
            } catch (e) {
                console.error(e);
                ElementPlus.ElMessage.error("连接服务器失败");
            } finally {
                this.initLoading = false;
            }
        },

        initChart() {
            const el = document.getElementById('well-chart');
            if(!el) return;
            
            if(this.chartInstance) this.chartInstance.dispose();
            this.chartInstance = echarts.init(el);
            
            this.chartInstance.setOption({
                title: { text: '井筒压力梯度与液面位置', left: 'center', top: 10 },
                tooltip: { trigger: 'axis', formatter: (p) => `深度: ${p[0].value[1].toFixed(1)}m<br>压力: ${p[0].value[0].toFixed(3)}MPa` },
                grid: { top: 60, bottom: 40, left: 60, right: 60 },
                xAxis: { name: '压力 (MPa)', type: 'value', position: 'top', splitLine: { show: true } },
                yAxis: { name: '深度 (m)', type: 'value', inverse: true, min: 0, max: this.form.pump_depth + 100 },
                series: []
            });
            window.addEventListener('resize', () => this.chartInstance.resize());
        },

        async runPhysicsCalc() {
            this.calcLoading = true;
            try {
                const res = await axios.post('/well/calc_level', {
                    well_id: this.wellInfo.well_id,
                    ...this.form
                });
                
                if(res.data.status === 'success') {
                    this.result = res.data.data;
                    this.updateChart(res.data.data.curve);
                    ElementPlus.ElMessage.success("计算完成");
                } else {
                    ElementPlus.ElMessage.error(res.data.message);
                }
            } catch(e) {
                ElementPlus.ElMessage.error("计算请求异常");
            } finally {
                this.calcLoading = false;
            }
        },
        
        async runAICalc() {
            this.aiLoading = true;
            this.aiResult = null;
            try {
                const res = await axios.post('/well/ai_predict_level', {
                    well_id: this.wellInfo.well_id,
                    ...this.form
                });
                this.aiResult = res.data;
                this.updateChart(this.result.curve); // 刷新图表，把AI线加上
            } catch(e) {
                ElementPlus.ElMessage.error("AI 服务暂不可用");
            } finally {
                this.aiLoading = false;
            }
        },
        
        updateChart(curveData) {
            if (!curveData) return;
            
            // 构造 ECharts 数据: [[pressure, depth], ...]
            const data = curveData.depth.map((d, i) => [curveData.pressure[i], d]);
            
            const series = [
                {
                    name: '机理压力梯度',
                    type: 'line',
                    smooth: true,
                    data: data,
                    lineStyle: { width: 3, color: '#1890ff' },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            { offset: 0, color: 'rgba(24,144,255,0.1)' },
                            { offset: 1, color: 'rgba(24,144,255,0.4)' }
                        ])
                    },
                    markLine: {
                        symbol: ['none', 'none'],
                        data: [
                            { yAxis: this.form.pump_depth, name: '泵深', lineStyle: { color: '#fa8c16', type: 'solid', width: 2 }, label: { position: 'end', formatter: '泵深\n{c}m' } },
                            { yAxis: this.result.level, name: '动液面', lineStyle: { color: '#52c41a', type: 'dashed', width: 2 }, label: { position: 'start', formatter: '动液面\n{c}m' } }
                        ]
                    }
                }
            ];

            // 如果有 AI 结果，加一条线
            if (this.aiResult) {
                series.push({
                    name: 'AI预测',
                    type: 'line',
                    data: [], // 不画实际线，只画 markLine
                    markLine: {
                        symbol: ['none', 'none'],
                        data: [{ yAxis: this.aiResult.prediction.level, name: 'AI预测' }],
                        lineStyle: { color: '#722ed1', type: 'dotted', width: 3 },
                        label: { formatter: 'AI: {c}m', position: 'insideEndTop', color: '#722ed1' }
                    }
                });
            }

            this.chartInstance.setOption({ series: series });
        }
    },
    // 内联样式
    styles: `
    .res-card {
        flex: 1;
        padding: 15px;
        border-radius: 6px;
        text-align: center;
        display: flex; flex-direction: column; justify-content: center;
    }
    .res-card .label { font-size: 13px; color: #666; margin-bottom: 5px; }
    .res-card .value { font-size: 24px; font-weight: bold; color: #333; }
    .res-card .unit { font-size: 12px; font-weight: normal; color: #999; }
    `
};