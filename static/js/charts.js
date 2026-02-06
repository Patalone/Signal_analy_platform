// --- START OF FILE static/js/charts.js ---

// === 通用绘图入口 ===
export function drawChart(containerId, config, ctx, onBrushCallback) {
    const el = document.getElementById(containerId);
    if (!el) return;

    // 强制销毁旧实例，防止状态残留
    let myChart = echarts.getInstanceByDom(el);
    if (myChart) myChart.dispose(); 
    myChart = echarts.init(el);

    // 1. 3D 轨迹图
    if (config.is3D) {
        render3DOrbit(myChart, ctx.singleResult);
        window.addEventListener('resize', () => myChart.resize());
        return myChart;
    }

    // 2. 热力图 (STFT)
    if (config.isHeatmap) {
        renderHeatmap(myChart, config, ctx.singleResult);
        window.addEventListener('resize', () => myChart.resize());
        return myChart;
    }

    // 3. 通用 2D 折线图 (包含叠加对比、拼接视图、普通单文件视图)
    render2DLines(myChart, config, ctx, onBrushCallback);
    
    window.addEventListener('resize', () => myChart.resize());
    return myChart;
}

// === EWT 专用视图渲染 ===
// 解决 Tab 切换时图表压缩或空白的问题
export function renderEWTView(ewtData, axis) {
    const data = ewtData[axis];
    if (!data) return;

    // 辅助函数：强制销毁并重新初始化
    const forceInit = (domId) => {
        const el = document.getElementById(domId);
        if (!el) return null;

        const oldChart = echarts.getInstanceByDom(el);
        if (oldChart) {
            oldChart.dispose(); 
        }
        
        const chart = echarts.init(el);
        return chart;
    };

    // 1. 渲染频谱划分图
    const specChart = forceInit('ewt-spectrum-' + axis);
    if (specChart) {
        const zipped = data.spectrum_data.freqs.map((f, i) => [f, data.spectrum_data.amp[i]]);
        const marks = data.spectrum_data.boundaries.map(b => ({ xAxis: b }));
        specChart.setOption({
            title: { text: '频谱划分', left: 'center', textStyle: {fontSize: 14} },
            tooltip: { trigger: 'axis', formatter: p => `Freq: ${p[0].value[0].toFixed(1)}Hz<br>Amp: ${p[0].value[1].toFixed(4)}` },
            xAxis: { type: 'value', min: 0, max: 'dataMax' }, 
            yAxis: { type: 'value', show: false },
            series: [{ 
                type: 'line', 
                data: zipped, 
                symbol: 'none', 
                areaStyle: { opacity: 0.3 }, 
                markLine: { data: marks, symbol: 'none', lineStyle: { color: 'red', type: 'dashed' }, label: { formatter: '{c} Hz' }, animation: false } 
            }],
            grid: { top: 30, bottom: 20, left: 10, right: 10 }, 
            dataZoom: [{type:'inside'}, {type:'slider'}]
        });
    }

    // 2. 渲染模态波形图
    data.modes.forEach((mode, idx) => {
        const modeChart = forceInit(`ewt-mode-${axis}-${idx}`);
        if (modeChart) {
            const zipped = mode.x.map((t, i) => [t, mode.y[i]]);
            modeChart.setOption({
                tooltip: { trigger: 'axis' }, 
                xAxis: { type: 'value', show: false, min: 'dataMin', max: 'dataMax' }, 
                yAxis: { type: 'value', show: false },
                series: [{ 
                    type: 'line', 
                    data: zipped, 
                    showSymbol: false, 
                    itemStyle: { color: '#722ed1' } 
                }], 
                grid: { top: 5, bottom: 5, left: 0, right: 0 }
            });
        }
    });
}

// === 内部渲染函数 ===

function render3DOrbit(chart, singleResult) {
    if (!singleResult) return;
    const xTask = singleResult['X']?.find(t => t.tool_id === 'TimeDomainStats');
    const yTask = singleResult['Y']?.find(t => t.tool_id === 'TimeDomainStats');
    const zTask = singleResult['Z']?.find(t => t.tool_id === 'TimeDomainStats');

    if (xTask && yTask && zTask) {
        const xd = xTask.output.data.y, yd = yTask.output.data.y, zd = zTask.output.data.y;
        const fullData = [];
        const len = Math.min(xd.length, yd.length, zd.length);
        for(let i=0; i<len; i++) fullData.push([xd[i], yd[i], zd[i]]);

        chart.setOption({
            grid3D: { viewControl: { autoRotate: true, autoRotateSpeed: 20 }, boxWidth: 80, boxHeight: 80, boxDepth: 80 },
            xAxis3D: { name: 'X', type: 'value' }, yAxis3D: { name: 'Y', type: 'value' }, zAxis3D: { name: 'Z', type: 'value' },
            series: [{ type: 'line3D', data: fullData.slice(0, 500), lineStyle: { width: 4, color: '#fa8c16', opacity: 0.8 } }]
        });
    }
}

function renderHeatmap(chart, config, singleResult) {
    if (!singleResult) return;
    const axis = 'X'; 
    const taskRes = singleResult[axis]?.find(t => t.tool_id === config.toolId);
    if (taskRes && taskRes.output && taskRes.output.data) {
        const d = taskRes.output;
        chart.setOption({
            tooltip: { position: 'top' }, grid: { height: '80%', top: '10%' },
            xAxis: { type: 'category', data: d.axis_data.x_axis, name: 'Time' },
            yAxis: { type: 'category', data: d.axis_data.y_axis, name: 'Freq' },
            visualMap: { min: -100, max: 0, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%' },
            series: [{ type: 'heatmap', data: d.data, itemStyle: { emphasis: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }]
        });
    }
}

/**
 * 核心 2D 绘图逻辑
 * 支持：单文件多轴、多文件叠加、多文件拼接(New)
 */
function render2DLines(chart, config, ctx, onBrushCallback) {
    const series = [], legendData = [];
    let xData = [];
    const colorPalette = ['#1890ff', '#fa8c16', '#52c41a', '#eb2f96', '#722ed1', '#13c2c2', '#fadb14', '#f5222d'];
    const axisColors = { 'X': '#ff4d4f', 'Y': '#52c41a', 'Z': '#1890ff' };
    const STITCH_MAX_POINTS = config.stitchMaxPoints || 20000;

    const extract = (res) => {
        if(!res || !res.output) return null;
        return res.output[config.subKey] || res.output.data;
    };

    // --- 场景 A: 多文件模式 ---
    if (ctx.isMultiMode) {
        if (ctx.multiResult) {
            const axis = ctx.compareAxis;

            // >>> 新增功能：强行拼接模式 (Stitching) <<<
            // 只有当 config.js 中配置了 isStitched: true 时触发
            if (config.isStitched) {
                let combinedX = [];
                let combinedY = [];
                let timeOffset = 0;
                let stitchMarkers = []; // 用于标记拼接点
                let totalPoints = 0;

                ctx.selectedFiles.forEach((file) => {
                    const shortName = file.split('/').pop();
                    const fileRes = ctx.multiResult[shortName];
                    if(!fileRes || fileRes.error) return;

                    const taskRes = fileRes[axis]?.find(t => t.tool_id === config.toolId);
                    const d = extract(taskRes);

                    if (d && d.x && d.y && d.x.length > 0 && d.y.length > 0) {
                        totalPoints += Math.min(d.x.length, d.y.length);
                    }
                });

                const stride = Math.max(1, Math.ceil(totalPoints / STITCH_MAX_POINTS));


                ctx.selectedFiles.forEach((file) => {
                    const shortName = file.split('/').pop();
                    const fileRes = ctx.multiResult[shortName];
                    if(!fileRes || fileRes.error) return;

                    const taskRes = fileRes[axis]?.find(t => t.tool_id === config.toolId);
                    const d = extract(taskRes);

                    if (d && d.x && d.y && d.x.length > 0 && d.y.length > 0) {
                        // 计算平移后的 X 轴
                        const len = Math.min(d.x.length, d.y.length);
                        for (let i = 0; i < len; i += stride) {
                            combinedX.push(d.x[i] + timeOffset);
                            combinedY.push(d.y[i]);
                        }

                        // 更新偏移量：当前段最后的时间 + 一个采样周期(估算)
                        const step = len > 1 ? (d.x[1] - d.x[0]) : 1;
                        const lastTime = timeOffset + d.x[len - 1];
                        timeOffset = lastTime + step;

                        // 记录拼接点位置（画虚线）
                        stitchMarkers.push({ xAxis: lastTime, label: { show: false } });
                    }
                });

                if (combinedX.length > 0) {
                    xData = combinedX;
                    legendData.push("拼接视图");
                    series.push({
                        name: "拼接视图",
                        type: 'line',
                        showSymbol: false,
                        smooth: true,
                        data: combinedY,
                        sampling: 'lttb',
                        large: true,
                        largeThreshold: 2000,
                        progressive: 5000,
                        itemStyle: { color: '#ff4d4f' }, // 醒目的红色
                        // 标记线：显示文件连接处
                        markLine: {
                            symbol: 'none',
                            lineStyle: { type: 'dashed', color: '#ccc', width: 1 },
                            data: stitchMarkers
                        }
                    });
                }
            } 
            // >>> 原有功能：叠加对比模式 (Overlay) <<<
            else {
                ctx.selectedFiles.forEach((file, index) => {
                    const shortName = file.split('/').pop();
                    const fileRes = ctx.multiResult[shortName];
                    if(!fileRes || fileRes.error) return;
                    
                    const taskRes = fileRes[axis]?.find(t => t.tool_id === config.toolId);
                    const d = extract(taskRes);
                    
                    if (d) {
                        if(!xData.length) xData = d.x; // 以第一个文件的时间轴为准
                        legendData.push(shortName);
                        series.push({ 
                            name: shortName, 
                            type: 'line', 
                            showSymbol: false, 
                            smooth: true, 
                            data: d.y, 
                            itemStyle: { color: colorPalette[index % colorPalette.length] } 
                        });
                    }
                });
            }
        }
    } 
    // --- 场景 B: 单文件模式 ---
    else {
        if (ctx.singleResult) {
            ['X', 'Y', 'Z'].forEach(axis => {
                const taskRes = ctx.singleResult[axis]?.find(t => t.tool_id === config.toolId);
                const d = extract(taskRes);
                if (d) {
                    if(!xData.length) xData = d.x;
                    legendData.push(axis + "轴");
                    series.push({ 
                        name: axis + "轴", 
                        type: 'line', 
                        showSymbol: false, 
                        smooth: false, 
                        data: d.y, 
                        itemStyle: { color: axisColors[axis] } 
                    });
                }
            });
        }
    }

    // --- 图表工具配置 ---
    let toolbox = { feature: { saveAsImage: {}, dataZoom: {} } };
    let brush = null;
    
    // 只有在【单文件】且【允许框选】的图表（如频谱图）中开启滤波交互
    if (config.allowBrush && ctx.isFilterMode && !ctx.isMultiMode) {
        toolbox.feature.brush = { type: ['lineX'] };
        brush = { xAxisIndex: 'all', brushLink: 'all', throttleType: 'debounce', throttleDelay: 300 };
    }

    chart.setOption({
        tooltip: { trigger: 'axis' }, 
        legend: { data: legendData, top: 0, type: 'scroll' },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
        toolbox: toolbox, 
        brush: brush,
        dataZoom: [{ type: 'inside' }, { type: 'slider' }],
        xAxis: { type: 'category', data: xData }, // 注意：ECharts Category 轴对于大量数据性能更好，但也支持 value 轴
        yAxis: { type: 'value', scale: true },
        series: series
    }, true); // true 表示不合并，重置所有配置

    // --- 交互回调 (Brush End) ---
    if (config.allowBrush && onBrushCallback) {
        chart.off('brushEnd');
        chart.on('brushEnd', (params) => {
            if (!params.areas.length) { onBrushCallback(null); return; }
            
            const range = params.areas[0].coordRange;
            const startIdx = Math.floor(range[0]), endIdx = Math.ceil(range[1]);
            
            if (xData && xData.length > endIdx) {
                // 返回实际的频率范围（或时间范围）
                onBrushCallback({ min: xData[startIdx], max: xData[endIdx] });
                // 清除选框，防止视觉干扰
                chart.dispatchAction({ type: 'brush', areas: [] });
            }
        });
    }
}