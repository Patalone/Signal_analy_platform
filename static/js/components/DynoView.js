// --- START OF FILE static/js/components/DynoView.js ---

export default {
    props: ['diagrams', 'loading', 'wellInfo'],
    template: `
    <div class="dyno-view">
        <!-- 如果没有选择油井，显示提示 -->
        <div v-if="!wellInfo" class="empty-tip">
            <div style="font-size: 60px; margin-bottom: 20px;">🛢️</div>
            <div>请在左侧“数据库”模式中搜索油井</div>
            <div style="font-size: 12px; color: #999; margin-top: 10px;">输入井号或井名，点击查找</div>
        </div>
        
        <!-- 如果有数据，显示图表 -->
        <div v-else>
            <!-- 顶部信息栏 -->
            <div class="status-bar" style="background:#fff7e6; border-color:#ffd591;">
                <span style="color:#d46b08; font-weight:bold; display:flex; align-items:center;">
                    <span style="font-size:18px; margin-right:8px;">🛢️</span> 
                    {{ wellInfo.well_name }} 
                    <span style="font-weight:normal; font-size:12px; margin-left:8px; color:#874d00;">(ID: {{ wellInfo.well_id }})</span>
                </span>
                <span style="font-size:12px; color:#666;" v-if="diagrams.length > 0">
                    共加载 <b>{{ diagrams.length }}</b> 条功图 | 
                    范围: {{ diagrams[0]?.time.split(' ')[0] }} 至 {{ diagrams[diagrams.length-1]?.time.split(' ')[0] }}
                </span>
            </div>

            <!-- 图表容器 -->
            <div class="chart-card" style="border-top-color: #fa8c16; margin-top: 15px;">
                <div class="chart-title border-orange">
                    多日功图叠加分析
                    <el-tag size="small" type="warning" effect="plain">位移 - 载荷</el-tag>
                </div>
                
                <div v-if="loading" style="height: 600px; display:flex; align-items:center; justify-content:center; color:#fa8c16;">
                    <i class="el-icon-loading" style="margin-right:5px;"></i> 数据加载中...
                </div>
                <div v-else id="dyno-chart" class="chart-container" style="height: 600px;"></div>
            </div>
        </div>
    </div>
    `,
    watch: {
        // 监听数据变化，一旦有新数据就重绘图表
        diagrams: {
            handler(val) {
                if(val && val.length) {
                    this.$nextTick(this.renderChart);
                }
            },
            deep: true
        }
    },
    methods: {
        renderChart() {
            const el = document.getElementById('dyno-chart');
            if (!el) return;
            
            // 如果已经有实例，先销毁
            let myChart = echarts.getInstanceByDom(el);
            if (myChart) myChart.dispose();
            myChart = echarts.init(el);
            
            // 鲜明的颜色序列
            const colors = [
                '#ff9f43', '#4da8da', '#10b981', '#f97316', '#a78bfa', 
                '#ef4444', '#06b6d4', '#f59e0b', '#8b5cf6', '#ec4899'
            ];
            
            // 构建数据序列
            const series = this.diagrams.map((d, i) => {
                const data = d.wy.map((val, idx) => [val, d.zh[idx]]);
                if (data.length) data.push(data[0]); // 闭合曲线
                
                return {
                    name: d.time,
                    type: 'line',
                    smooth: true,
                    symbol: 'none', // 不显示数据点
                    lineStyle: { width: 1.5, opacity: 0.8 },
                    itemStyle: { color: colors[i % colors.length] },
                    data: data,
                    // 将额外信息存入 customInfo，方便 Tooltip 读取
                    customInfo: {
                        condition: d.condition,
                        stroke: d.stroke,
                        freq: d.frequency
                    }
                };
            });

            const option = {
                // 【Tooltip 优化】
                tooltip: {
                    trigger: 'axis',
                    // 控制浮层容器样式
                    extraCssText: 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); border-radius: 4px; border: 1px solid #eee;',
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    textStyle: { color: '#333' },
                    formatter: function (params) {
                        if (!params.length) return '';
                        
                        // 标题行
                        let html = `<div style="margin-bottom:8px; font-weight:bold; border-bottom:1px solid #eee; padding-bottom:6px; font-size:13px;">位移: ${params[0].axisValue} m</div>`;
                        
                        params.forEach(p => {
                            const info = series[p.seriesIndex].customInfo || {};
                            
                            // 工况显示逻辑：如果是“未知”或空，则不显示
                            let condStr = '';
                            if (info.condition && info.condition !== '未知') {
                                condStr = ` <span style="color:#666; font-weight:normal; margin-left:5px;">[${info.condition}]</span>`;
                            }

                            // 布局逻辑：使用 flex + gap 实现自适应宽度和分隔
                            html += `
                                <div style="display:flex; justify-content:space-between; align-items:center; min-width:350px; gap:5px; font-size:15px; margin-top:4px; line-height:1.6;">
                                    <span style="white-space:nowrap; display:flex; align-items:center;">
                                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${p.color}; margin-right:6px;"></span>
                                        ${p.seriesName}
                                    </span>
                                    <span style="font-weight:bold; white-space:nowrap; font-family:monospace;">
                                        ${p.value[1].toFixed(2)} kN${condStr}
                                    </span>
                                </div>
                            `;
                        });
                        return html;
                    }
                },
                // 【隐藏图例】
                legend: { show: false },
                
                grid: { left: '3%', right: '4%', bottom: '50px', containLabel: true },
                
                toolbox: {
                    feature: {
                        dataZoom: { yAxisIndex: 'none' },
                        restore: {},
                        saveAsImage: {}
                    },
                    right: 20
                },
                
                xAxis: { 
                    type: 'value', 
                    name: '位移 (m)', 
                    nameLocation: 'middle', 
                    nameGap: 30,
                    scale: true,
                    splitLine: { show: true, lineStyle: { type: 'dashed', color: '#f0f0f0' } },
                    axisLine: { lineStyle: { color: '#888' } }
                },
                
                yAxis: { 
                    type: 'value', 
                    name: '载荷 (kN)', 
                    scale: true,
                    splitLine: { show: true, lineStyle: { type: 'dashed', color: '#f0f0f0' } },
                    axisLine: { lineStyle: { color: '#888' } }
                },
                
                dataZoom: [
                    { type: 'inside' }, 
                    { type: 'slider', bottom: 10, height: 20 }
                ],
                
                series: series
            };

            myChart.setOption(option);
            window.addEventListener('resize', () => myChart.resize());
        }
    }
};