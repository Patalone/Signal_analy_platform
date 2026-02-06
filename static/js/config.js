// 定义所有支持的图表类型及其对应的数据源和样式
// 开闭原则：新增算法只需在此处注册，无需修改绘图逻辑
export const CHART_DEFINITIONS = [
    { 
        id: 'time', 
        title: '时域波形 (Time Domain)', 
        toolId: 'TimeDomainStats', 
        subKey: 'data', 
        color: '#1890ff', 
        borderClass: 'border-blue' 
    },
    { 
        id: 'freq', 
        title: '频谱分析 (Frequency Domain)', 
        toolId: 'SpectrumAnalyzer', 
        subKey: 'data', 
        color: '#52c41a', 
        borderClass: 'border-green', 
        allowBrush: true 
    },
    { 
        id: 'psd', 
        title: '功率谱密度 (PSD)', 
        toolId: 'PSDProcessor', 
        subKey: 'data', 
        color: '#722ed1', 
        borderClass: 'border-purple' 
    },
    { 
        id: 'stft', 
        title: '时频声谱图 (Spectrogram)', 
        toolId: 'STFTProcessor', 
        subKey: 'data', 
        color: '#13c2c2', 
        borderClass: 'border-cyan', 
        isHeatmap: true 
    },
    { 
        id: 'env_time', 
        title: '包络时域波形 (Envelope Time)', 
        toolId: 'EnvelopeProcessor', 
        subKey: 'time_data', 
        color: '#fa8c16', 
        borderClass: 'border-orange' 
    },
    { 
        id: 'env_freq', 
        title: '包络谱 (Envelope Spectrum)', 
        toolId: 'EnvelopeProcessor', 
        subKey: 'freq_data', 
        color: '#eb2f96', 
        borderClass: 'border-pink' 
    },
    { 
        id: 'filtered_time', 
        title: '滤除指定频段后的波形 (Filtered)', 
        toolId: 'BandStopProcessor', 
        subKey: 'data', 
        color: '#ff4d4f', 
        borderClass: 'border-red' 
    },
        // 1. 合理功能：倒频谱
    { 
        id: 'cepstrum', 
        title: '倒频谱分析 (Cepstrum)', 
        toolId: 'CepstrumProcessor', 
        subKey: 'data', 
        color: '#8e44ad', 
        borderClass: 'border-purple' 
    },

    // 2. 不合理功能：强行拼接
    { 
        id: 'stitched_view', 
        title: '多文件拼接视图 (Stitched View)', 
        toolId: 'StitchProcessor', 
        subKey: 'data', 
        color: '#ff4d4f', 
        borderClass: 'border-red',
        isStitched: true  // <--- 这是一个自定义标记，告诉 charts.js 启用拼接逻辑
    }
];

// 需要在侧边栏隐藏的特殊工具
export const HIDDEN_TOOLS = ["EWTProcessor", "BandStopProcessor"];