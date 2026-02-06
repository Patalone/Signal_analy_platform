# --- START OF FILE oil_physics.py ---

import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ==========================================
# 1. 常量与基础配置
# ==========================================
G = 9.8                     # 重力加速度
MAX_ITER_COUNT = 30         # 最大迭代次数
DEFAULT_DEPTH_STEP = 10.0   # 积分步长 (m)
P_CASING_DEFAULT = 0.1      # 默认套压 (MPa)

# ==========================================
# 2. 基础数学辅助函数
# ==========================================

def cal_f_z(z: float, pr: float, tt: float) -> float:
    """Dranchuk-Abu-Kassem Z因子计算误差函数"""
    if z <= 0 or tt <= 0: return 1.0
    r5 = 0.27 * pr / (z * tt)
    f_z = 1 + (0.31506 - 1.0467 / tt - 0.583 / tt ** 3) * r5 + (
            0.5353 - 0.6123 / tt) * r5 ** 2 + 0.6815 * r5 ** 2 / tt ** 3 - z
    return f_z

def solve_z_factor(p_avg: float, t_avg: float, gas_density: float) -> float:
    """二分法求解气体压缩因子 Z"""
    # 临界参数
    tc = 168 + 325 * gas_density - 12.5 * (gas_density ** 2)
    pc = 667 + 15 * gas_density - 37.5 * (gas_density ** 2)
    
    pr = 14.22 * p_avg / pc  # 拟对比压力
    tt = (1.8 * t_avg + 492) / tc # 拟对比温度

    z_left, z_right = 0.01, 3.0
    
    # 快速收敛检查
    if cal_f_z(z_left, pr, tt) * cal_f_z(z_right, pr, tt) > 0:
        return 0.9 # 无法收敛时的兜底值

    z_final = 0.9
    for _ in range(10):
        z_mid = (z_left + z_right) / 2
        f_mid = cal_f_z(z_mid, pr, tt)
        
        if abs(f_mid) < 0.001:
            z_final = z_mid
            break
        
        if f_mid * cal_f_z(z_left, pr, tt) < 0:
            z_right = z_mid
        else:
            z_left = z_mid
            
    return z_final

# ==========================================
# 3. 参数数据类
# ==========================================

@dataclass
class WellParams:
    """
    井身结构与流体参数
    """
    # 必需参数
    pump_depth: float       # 泵挂深度 (m)
    casing_pressure: float  # 套压 (MPa)
    tubing_pressure: float  # 油压/回压 (MPa)
    water_cut: float        # 含水率 (0-1)
    oil_density: float      # 原油相对密度 (水=1)
    gas_density: float      # 天然气相对密度 (空气=1)
    temp_wellhead: float    # 井口温度 (℃)
    temp_bottom: float      # 井底/油层温度 (℃)
    prod_liquid: float      # 日产液量 (m3/d)

    # 可选参数 (带默认值)
    gor: float = 25.0          # 生产气油比 (m3/m3)
    casing_od: float = 139.7   # 套管外径 (mm)
    tubing_id: float = 62.0    # 油管内径 (mm)

# ==========================================
# 4. 物理计算核心引擎 (完整还原版)
# ==========================================

class FluidLevelCalculator:
    def __init__(self, params: WellParams):
        self.p = params
        
        # 数据安全预处理
        self._cyl_ss = max(0.1, self.p.prod_liquid)
        self._hs = max(0.0, min(1.0, self.p.water_cut))
        self._scqyb = max(0.0, self.p.gor)
        
        # --- Ramey 温度场模型初始化 (还原旧代码 init_key_temperature_data) ---
        eff_depth = self.p.pump_depth if self.p.pump_depth > 0 else 2000
        # 地温梯度
        self._geo_gradient = (self.p.temp_bottom - self.p.temp_wellhead) / eff_depth
        
        # 热物性参数估算
        # 混合流体加权比热容项 (对应旧代码 _wq)
        # _b = 1.163 (水的相关系数)
        _wq_unit = (1 - self._hs) * self._geo_gradient + self._hs * 1.163 + \
                   (1 - self._hs) * self._scqyb * self._geo_gradient / 3 / 467
        
        # 质量流量热容因子
        self._wq = _wq_unit * self._cyl_ss * 1000 / 24 
        
        # 综合导热系数 (简化旧代码中复杂的 k2ll/rl 计算，取经验值)
        # 旧代码: _k2ll = 1 / (rl3 + rle) ...
        # 这里使用弛豫距离 A = wq / k 来表示热损耗速率
        # 经验上，综合导热系数 k 约为 1.5 ~ 2.0 W/(m·C)
        k_heat_transfer = 1.6 
        
        # 弛豫距离 A (Relaxation distance)
        self._relaxation_depth = self._wq / k_heat_transfer if k_heat_transfer > 0 else 100.0

        # 几何尺寸 (单位: m)
        self._d_casing_id = (self.p.casing_od - 13 * 2) * 1e-3 # 估算套管内径
        self._d_tubing_od = (self.p.tubing_id + 6.5 * 2) * 1e-3 # 估算油管外径
        self._d_tubing_id = self.p.tubing_id * 1e-3
        
        # 液面以下环空流动的等效直径 (水力直径)
        self._d_hydraulic = self._d_casing_id - self._d_tubing_od
        if self._d_hydraulic <= 0: self._d_hydraulic = 0.05
        
        # 环空截面积
        self._area_annulus = math.pi * (self._d_casing_id**2 - self._d_tubing_od**2) / 4
        if self._area_annulus <= 0: self._area_annulus = 0.01

    def _get_temp_at_depth(self, depth: float) -> float:
        """
        基于 Ramey 指数模型的温度计算 (还原旧代码非线性逻辑)
        """
        # 原始地温
        t_geo = self.p.temp_wellhead + self._geo_gradient * depth
        
        # 流动修正 (Ramey 解的简化形式)
        # T(z) = T_geo(z) + (T_bottom - T_geo(bottom)) * exp(-(H-z)/A)
        # 模拟流体从井底上来，温度逐渐冷却至地温的过程
        if self._relaxation_depth <= 0.1:
            return t_geo
            
        distance_from_bottom = max(0, self.p.pump_depth - depth)
        
        # 井底处的地层温度
        t_geo_bottom = self.p.temp_wellhead + self._geo_gradient * self.p.pump_depth
        
        # 温度增量 (流体携带的热量)
        delta_t = (self.p.temp_bottom - t_geo_bottom) * math.exp(-distance_from_bottom / self._relaxation_depth)
        
        # 修正系数：产液量极低时，温度完全回归地温
        flow_factor = min(1.0, self._cyl_ss / 5.0) 
        
        return t_geo + delta_t * flow_factor

    def _cal_pressure_gradient_full(self, p_avg: float, t_avg: float) -> float:
        """
        【完整版】多相流压力梯度计算
        严格还原旧代码 __cal_pressure_gradient 中的 Beggs-Brill / Hagedorn-Brown 混合逻辑
        包含：PVT(Vasquez-Beggs), 流型判断(L1-L4), 摩擦系数修正(S因子), 加速度项
        """
        if p_avg <= 0: p_avg = 0.01

        md_yy = self.p.oil_density
        md_trq = self.p.gas_density
        hs = self._hs
        cyl_ss = self._cyl_ss
        scqyb = self._scqyb

        # --- 1. PVT 物性计算 ---
        
        # 1.1 溶解气油比 Rs (Vasquez-Beggs)
        ap = 141.5 / md_yy - 131.5 # API度
        if ap <= 0: ap = 0.1
        
        if md_yy >= 0.8762: # 重油
            c1, c2, c3 = 0.0362, 1.0937, 25.724
        else: # 轻油
            c1, c2, c3 = 0.0178, 1.1870, 23.9310
            
        rs = 0.1845 * c1 * md_trq * ((145.3 * p_avg) ** c2) * math.exp(c3 * ap / (1.8 * md_yy * (273 + t_avg)))
        rs = min(rs, scqyb) # Rs 不能超过总气油比

        # 1.2 体积系数 Bo
        bo = (1000 * md_yy + 1.202 * rs * md_trq) / (md_yy * 1000)
        
        # 1.3 原油密度 ro (kg/m3)
        ro = (md_yy + 0.17812 * rs * md_trq * 1.206 / 1000) / bo * 1000
        ro = max(ro, 700.0)

        # 1.4 气体性质
        z = solve_z_factor(p_avg, t_avg, md_trq)
        rg = 3484.4 * md_trq * p_avg / z / (t_avg + 273) # 气体密度

        # 1.5 粘度计算 (还原旧代码)
        # 气体粘度 (Lee-Gonzalez-Eakin)
        ma = 28.96 * md_trq
        X_vis = 3.5 + 986 / (1.8 * t_avg + 492) + 0.01 * ma
        yy_vis = 2.4 - 0.2 * X_vis
        ak_vis = (9.4 + 0.02 * ma) * (1.8 * t_avg + 492) ** 1.5 / (701 + 19 * ma + 1.8 * t_avg)
        r1_vis = 0.51008 * p_avg * md_trq * 1.206 / (z * (1.8 * t_avg + 492))
        ug = ak_vis * 1e-4 * math.exp(X_vis * (r1_vis ** yy_vis)) # mPa.s
        
        # 液体粘度 (Beggs-Robinson)
        # 死油粘度
        ud_exp = 3.0324 - 0.02023 * ap
        Y_vis = (10 ** ud_exp) * ((1.8 * t_avg + 32) ** (-1.163))
        ud = (10 ** Y_vis) - 1
        # 活油粘度
        a1_vis = 10.715 * (rs + 100) ** (-0.515)
        bb_vis = 5.44 * (rs + 150) ** (-0.338)
        uo = a1_vis * (ud ** bb_vis)
        # 水粘度
        uw = math.exp(1.003 - 0.01479 * (t_avg * 1.8 + 32) + 1.982e-5 * (t_avg * 1.8 + 32) ** 2)
        # 混合液粘度
        ul = uw * hs + uo * (1 - hs)

        # 1.6 表面张力 (还原旧代码 Baker-Swerdloff 近似)
        try:
            tc_sig = 168 + 325 * md_trq - 12.5 * md_trq**2
            term_sig = (tc_sig - 1.8 * t_avg - 492) / (tc_sig - 528)
            if term_sig < 0: term_sig = 0.1
            
            a3_sig = (39.0964 - 0.2548 * ap) * (1.00783 * math.exp(-0.01041 * p_avg - 0.00783))
            sigma_o = a3_sig * (term_sig ** 1.2)
        except:
            sigma_o = 20.0
            
        sigma_w = 79.1 * math.exp(-0.08366 / uw)
        sigma_l = sigma_o * (1 - hs) + sigma_w * hs # 混合表面张力 dyn/cm

        # --- 2. 流体力学计算 ---

        # 2.1 流量与表观流速
        qo = cyl_ss * (1 - hs)
        qw = cyl_ss * hs
        # 井下自由气量
        qg = z * qo * max(0, scqyb - rs) * (t_avg + 273) / p_avg * 0.1 / 273
        
        # 井下液体体积流量
        ql = qo * bo + qw
        
        area = self._area_annulus
        vsl = ql / 86400 / area # 液相表观流速
        vsg = qg / 86400 / area # 气相表观流速
        vm = vsl + vsg          # 混合流速
        if vm == 0: vm = 0.001
        
        # 2.2 无量纲参数
        E1 = vsl / vm  # 输入持液率 (Input Liquid Content lambda_l)
        d_hyd = self._d_hydraulic
        nfr = vm ** 2 / (9.8 * d_hyd) # 弗劳德数 Froude Number
        
        # 2.3 流型判断 (Beggs-Brill Flow Regime)
        L1 = 316 * E1 ** 0.302
        L2 = 0.0009252 * E1 ** (-2.4684)
        L3 = 0.1 * E1 ** (-1.4516)
        L4 = 0.5 * E1 ** (-6.738)
        
        regime = "segregated"
        # Beggs-Brill 系数
        cona, conb, conc = 0.0, 0.0, 0.0
        
        if (E1 < 0.01 and nfr < L1) or (E1 >= 0.01 and nfr < L2):
            regime = "segregated" # 分离型
            cona, conb, conc = 0.98, 0.4846, 0.0868
        elif (E1 >= 0.01 and nfr > L2 and nfr < L3):
            regime = "transition" # 过渡型
        elif (E1 >= 0.01 and E1 < 0.4 and nfr > L3 and nfr <= L1) or \
             (E1 >= 0.4 and nfr > L3 and nfr <= L4):
            regime = "intermittent" # 间歇型
            cona, conb, conc = 0.845, 0.5351, 0.0173
        else:
            regime = "distributed" # 分散型
            cona, conb, conc = 1.065, 0.5824, 0.0609

        # 2.4 持液率 Hlo (无滑脱)
        if regime == "transition":
            # 过渡型采用分离型和间歇型的加权
            hlo_seg = 0.98 * E1 ** 0.4846 / (nfr ** 0.0868 if nfr>0 else 1)
            hlo_int = 0.845 * E1 ** 0.5351 / (nfr ** 0.0173 if nfr>0 else 1)
            A_tran = (L3 - nfr) / (L3 - L2)
            hlo = A_tran * hlo_seg + (1 - A_tran) * hlo_int
        else:
            if nfr <= 0: hlo = 1.0
            else: hlo = cona * (E1 ** conb) / (nfr ** conc)
        
        # 物理约束：持液率不能小于输入持液率，也不能大于1
        hlo = max(E1, min(1.0, hlo))
        
        # 2.5 倾角修正 (Incline Correction)
        # 对于动液面计算，假设垂直井 (Angle=90, sin=1)
        # 旧代码计算了 inclinec，但对于垂直井修正系数约为1
        # 此处直接使用 Hlo 作为 Hlsita (倾斜持液率)
        hlsita = hlo 

        # 2.6 混合密度
        rl_mix = (ro * qo * bo + 1000 * qw) / (qo * bo + qw)
        rho_mix = rl_mix * hlsita + rg * (1 - hlsita) # rtp

        # 2.7 摩阻计算 (Friction)
        # 混合粘度
        um = ul * E1 + ug * (1 - E1)
        # 雷诺数
        nre = d_hyd * vm * (rl_mix * E1 + rg * (1-E1)) / (um * 1e-3)
        if nre <= 0: nre = 1000
        
        # 无滑脱摩擦系数 fn
        fn = 0.0056 + 0.5 / (nre ** 0.32)
        
        # Beggs-Brill 摩擦修正因子 S
        try:
            y = E1 / (hlsita ** 2)
            if 1 < y < 1.2:
                ss = math.log(2.2 * y - 1.2)
            else:
                ln_y = math.log(y)
                ss = ln_y / (-0.0523 + 3.182 * ln_y - 0.8725 * ln_y**2 + 0.01853 * ln_y**4)
        except:
            ss = 0.0
            
        f_tp = fn * math.exp(ss) # 两相流摩擦系数
        
        # 摩擦梯度 (Pa/m) -> 使用无滑脱密度计算动能损耗是Beggs-Brill的特征
        rho_noslip = rl_mix * E1 + rg * (1 - E1)
        friction_loss = f_tp * rho_noslip * vm * vm / (2 * d_hyd)

        # 2.8 总压力梯度 (Total Gradient)
        # grad = (rho*g + friction) / (1 - Ek)
        
        grav_term = rho_mix * 9.8 
        # 加速度项 (动能变化)
        acc_term = rho_mix * vm * vsg / (p_avg * 1e6) 
        if acc_term >= 0.9: acc_term = 0.9 # 防止奇点
        
        grad_pa = (grav_term + friction_loss) / (1 - acc_term)
        grad_mpa = grad_pa * 1e-6
        
        # 兜底：如果梯度异常(例如负数)，回退到静水柱梯度
        if grad_mpa < 0 or grad_mpa > 0.03:
            grad_mpa = (rl_mix * (1-hs) + 1000*hs) * 9.8 * 1e-6
            
        return grad_mpa

    def solve_dynamic_level(self, pump_intake_pressure: float) -> dict:
        """
        反算动液面主入口
        算法：二分查找液面深度 + RK4 数值积分计算压力
        """
        p_casing = self.p.casing_pressure
        if p_casing <= 0: p_casing = P_CASING_DEFAULT
        
        # 异常情况快速返回
        if pump_intake_pressure <= p_casing:
             return {
                "level": self.p.pump_depth,
                "submergence": 0.0,
                "pip": round(pump_intake_pressure, 2),
                "curve": {"depth": [0, self.p.pump_depth], "pressure": [p_casing, p_casing]}
            }

        # 二分查找区间
        level_min = 0.0
        level_max = self.p.pump_depth
        
        result_level = 0
        final_curve = {}
        
        for _ in range(MAX_ITER_COUNT):
            mid_level = (level_min + level_max) / 2
            
            # --- 阶段1: 气柱段 (井口 -> 液面) ---
            # 简化为微小线性梯度 (气体自重)
            p_interface = p_casing * (1 + 0.00025 * mid_level)
            
            # --- 阶段2: 液柱段 (液面 -> 泵入口) ---
            curr_p = p_interface
            curr_d = mid_level
            
            # 记录积分路径
            depths_seg = [curr_d]
            press_seg = [curr_p]
            
            # RK4 积分循环
            while curr_d < self.p.pump_depth:
                step = DEFAULT_DEPTH_STEP
                if curr_d + step > self.p.pump_depth:
                    step = self.p.pump_depth - curr_d
                
                if step < 0.001: break
                
                # 准备RK4所需的中间点温度
                t_curr = self._get_temp_at_depth(curr_d)
                t_mid = self._get_temp_at_depth(curr_d + step/2)
                t_next = self._get_temp_at_depth(curr_d + step)
                
                # 计算梯度 k1-k4
                k1 = self._cal_pressure_gradient_full(curr_p, t_curr)
                k2 = self._cal_pressure_gradient_full(curr_p + step * k1 / 2, t_mid)
                k3 = self._cal_pressure_gradient_full(curr_p + step * k2 / 2, t_mid)
                k4 = self._cal_pressure_gradient_full(curr_p + step * k3, t_next)
                
                p_next = curr_p + (step / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
                
                curr_d += step
                curr_p = p_next
                
                # 记录数据 (为了减少数据量，可以每隔几步记录一次)
                depths_seg.append(round(curr_d, 2))
                press_seg.append(round(curr_p, 4))
                
            p_calc_bottom = curr_p
            
            # --- 二分判断 ---
            if abs(p_calc_bottom - pump_intake_pressure) < 0.02: # 误差 0.02 MPa
                result_level = mid_level
                final_curve = {"depth": depths_seg, "pressure": press_seg}
                break
            
            if p_calc_bottom > pump_intake_pressure:
                # 算出的压力偏大 -> 说明液柱太高 -> 液面太浅 -> 需要加深液面 (Level 增大)
                level_min = mid_level
            else:
                # 算出的压力偏小 -> 说明液柱太短 -> 液面太深 -> 需要抬升液面 (Level 减小)
                level_max = mid_level
        else:
            # 未收敛，取最后一次结果
            result_level = (level_min + level_max) / 2
            final_curve = {"depth": depths_seg, "pressure": press_seg}

        # 组装完整曲线
        full_depths = [0.0, result_level] + final_curve.get("depth", [])
        full_pressures = [p_casing, p_casing * (1 + 0.00025 * result_level)] + final_curve.get("pressure", [])

        # 去除重复点
        clean_d, clean_p = [], []
        if full_depths:
            clean_d.append(full_depths[0])
            clean_p.append(full_pressures[0])
            for i in range(1, len(full_depths)):
                if full_depths[i] > clean_d[-1] + 0.01:
                    clean_d.append(full_depths[i])
                    clean_p.append(full_pressures[i])

        return {
            "level": round(result_level, 2),
            "submergence": round(self.p.pump_depth - result_level, 2),
            "pip": round(pump_intake_pressure, 2),
            "curve": {
                "depth": clean_d,
                "pressure": clean_p
            }
        }

# ==========================================
# 5. 测试入口 (模拟调用)
# ==========================================
if __name__ == "__main__":
    # 模拟输入
    params = WellParams(
        pump_depth=2200.0,
        casing_pressure=0.3,
        tubing_pressure=1.5,
        water_cut=0.85,
        oil_density=0.86,
        gas_density=0.75,
        temp_wellhead=35.0,
        temp_bottom=85.0,
        prod_liquid=40.0,
        gor=30.0
    )

    print("--- 启动计算 ---")
    calculator = FluidLevelCalculator(params)
    
    # 假设泵吸入口压力
    target_pip = 10.5 
    print(f"设定目标 PIP: {target_pip} MPa")
    
    res = calculator.solve_dynamic_level(target_pip)
    
    print("\n[结果]")
    print(f"动液面: {res['level']} m")
    print(f"沉没度: {res['submergence']} m")
    
    print("\n[曲线样本]")
    d_list = res['curve']['depth']
    p_list = res['curve']['pressure']
    indices = [0, len(d_list)//2, -1]
    for i in indices:
        if i < len(d_list):
            print(f"D: {d_list[i]:.1f}m => P: {p_list[i]:.2f} MPa")