import streamlit as st
from datetime import datetime

# ========== 科林品牌配置 ==========
st.set_page_config(page_title="科林劳动争议风险评估器", layout="wide")
COLOR_MAIN = "#F5B800"
COLOR_RED = "#C53030"
COLOR_GREEN = "#2F855A"

# ========== 内置业务规则 ==========
# 1. 省份→风险等级映射
province_risk_map = {
    "北京": "北京", "上海": "上海",
    "广东": "其他高风险", "江苏": "其他高风险", "浙江": "其他高风险",
    "天津": "其他高风险", "重庆": "其他高风险", "四川": "其他高风险", "湖北": "其他高风险",
    "辽宁": "其他高风险", "吉林": "其他高风险", "黑龙江": "其他高风险",
    "山东": "其他低风险", "河北": "其他低风险", "福建": "其他低风险",
    "陕西": "其他低风险", "河南": "其他低风险", "湖南": "其他低风险", "安徽": "其他低风险",
    "江西": "其他低风险", "山西": "其他低风险", "云南": "其他低风险", "贵州": "其他低风险",
    "广西": "其他低风险", "海南": "其他低风险", "甘肃": "其他低风险", "青海": "其他低风险",
    "宁夏": "其他低风险", "新疆": "其他低风险", "内蒙古": "其他低风险", "西藏": "其他低风险"
}

# 2. 地域严格系数
region_coeff = {
    "北京": 1.2,
    "其他高风险": 1.1,
    "其他低风险": 1.0,
    "上海": 0.9
}

# 3. 员工身份规则
identity_abs_redline = ["三期女职工", "距退休不足5年员工"]
identity_multiplier = {
    "普通员工": 1.0,
    "带人经理": 1.2,
    "无固定期限合同员工": 1.5,
    "医疗期内员工": 1.8
}

# 4. 公司主体管辖范围
company_jurisdiction = {
    "科弘昌": ["北京", "天津", "河北"],
    "同科林": ["上海", "浙江", "江苏"],
    "同科林分公司": [],
    "其他": [],
    "外包": [],
    "派遣": []
}

# 5. 解除理由证据规则
evidence_rules = {
    "严重违纪": [
        {"name": "违纪行为书面/实物证据（考勤、违规单据、监控截图等）",
         "type": "deduct", "level": "必备", "base_score": 20, "redline": True,
         "desc": "无直接事实证据，无法认定违纪行为存在"},
        {"name": "违纪事项沟通确认记录（书面签字/谈话录音/聊天记录）",
         "type": "deduct", "level": "必备", "base_score": 20, "redline": True,
         "desc": "未向员工告知违纪事项，处罚程序严重瑕疵"},
        {"name": "相关依据制度的签收记录",
         "type": "deduct", "level": "必备", "base_score": 20, "redline": True,
         "desc": "员工未知晓制度，处罚无合法支撑"},
        {"name": "已向员工送达限期整改/警告通知",
         "type": "deduct", "level": "重要", "base_score": 15, "redline": False,
         "desc": "未给整改机会，易被认定处罚过重、比例失当"},
        {"name": "违纪行为发生在近3个月内（处理时效合规）",
         "type": "deduct", "level": "重要", "base_score": 15, "redline": False,
         "desc": "处理间隔过久，处罚合理性存疑"},
        {"name": "员工未就解除提出书面异议",
         "type": "deduct", "level": "辅助", "base_score": 10, "redline": False,
         "desc": "员工未提异议可主张默认认可；已提书面异议则举证压力加大"}
    ],
    "不能胜任工作": [
        {"name": "首次不胜任工作的书面证据",
         "type": "deduct", "level": "必备", "base_score": 25, "redline": True,
         "desc": "无有效考核结论，不胜任主张直接不成立"},
        {"name": "PIP绩效改进目标清晰可量化",
         "type": "deduct", "level": "必备", "base_score": 20, "redline": True,
         "desc": "目标模糊主观，司法实践不予采信"},
        {"name": "PIP期间培训/辅导的书面记录与签字",
         "type": "deduct", "level": "必备", "base_score": 20, "redline": True,
         "desc": "无培训辅导记录，改进程序法定要件缺失"},
        {"name": "改进期后二次不胜任的考核证据",
         "type": "deduct", "level": "必备", "base_score": 15, "redline": True,
         "desc": "无二次不胜任证明，不满足法定解除条件"},
        {"name": "岗位说明书与明确考核标准",
         "type": "deduct", "level": "重要", "base_score": 12, "redline": False,
         "desc": "岗位标准越清晰，主张可信度越高；缺失不直接败诉"},
        {"name": "可向员工提供合理调岗机会",
         "type": "deduct", "level": "重要", "base_score": 8, "redline": False,
         "desc": "有调岗机会胜率更高；无调岗机会不直接导致违法"}
    ],
    "客观情况重大变化": [
        {"name": "【前置判定】部门是否要求立刻解决",
         "type": "precondition", "level": "前置红线", "base_score": 0, "redline": True,
         "desc": "要求立刻解决则无法履行法定协商程序，直接极高风险"},
        {"name": "部门愿意出具正式组织架构调整通知",
         "type": "deduct", "level": "重要", "base_score": 25, "redline": False,
         "desc": "无正式文件则客观变化无书面支撑"},
        {"name": "【联动项】是否存在其他同类型在岗岗位",
         "type": "link", "level": "联动规则", "base_score": 0, "redline": False,
         "field_key": "has_same_post",
         "desc": "无同类岗位则调岗义务自动豁免"},
        {"name": "可向员工提供合理调岗机会",
         "type": "deduct", "level": "重要", "base_score": 20, "redline": False,
         "link_field": "has_same_post",
         "desc": "无其他同类岗位时，该项不扣分"},
        {"name": "解除通知已书面有效送达员工",
         "type": "deduct", "level": "辅助", "base_score": 10, "redline": False,
         "desc": "程序瑕疵，不影响实体认定"},
        {"name": "【加分项】重大变化事项存在政策外因",
         "type": "bonus", "level": "正向加分", "base_score": 15, "redline": False,
         "desc": "有外部政策支撑，司法认可度大幅提升"},
        {"name": "【加分项】双方已就变更劳动合同协商并有书面记录",
         "type": "bonus", "level": "正向加分", "base_score": 20, "redline": False,
         "desc": "履行法定协商程序是核心要件"}
    ]
}

# ========== 页面标题 ==========
st.markdown(f"<h2 style='color:{COLOR_MAIN};'>科林劳动争议风险评估器（HR内部使用）</h2>", unsafe_allow_html=True)
st.caption("创作权：李超Eddie")
st.divider()

# ========== 侧边栏：基础信息 ==========
with st.sidebar:
    st.subheader("案件核心信息")
    province = st.selectbox("工作省份", sorted(province_risk_map.keys()), index=1)
    company = st.selectbox("签约主体", ["科弘昌", "同科林", "同科林分公司", "其他", "外包", "派遣"], index=1)
    reason = st.selectbox("解除核心理由", list(evidence_rules.keys()), index=0)
    emp_status = st.selectbox("员工特殊身份",
                              ["普通员工", "带人经理", "无固定期限合同员工", "三期女职工", "距退休不足5年员工", "医疗期内员工"],
                              index=0)
    risk_grade = province_risk_map[province]
    st.info(f"地域裁判等级：{risk_grade}")

# ========== 主区域：证据核验 ==========
col1, col2 = st.columns([2, 1])
ev_list = evidence_rules[reason]
user_choices = {}

with col1:
    st.subheader("证据清单核验")
    st.caption("逐项选择当前证据状态，系统自动计算风险")
    
    for idx, item in enumerate(ev_list):
        item_type = item["type"]
        name = item["name"]
        level = item["level"]
        
        # 标签颜色
        if level == "必备":
            tag = f":red[【{level}】]"
        elif level == "正向加分":
            tag = f":green[【{level}】]"
        elif level in ["前置红线", "联动规则"]:
            tag = f":orange[【{level}】]"
        else:
            tag = f"【{level}】"
        
        if item_type in ["precondition", "link"]:
            choice = st.radio(f"{tag} {name}", ["是", "否"], index=1, horizontal=True, key=f"ev_{idx}")
        else:
            choice = st.radio(f"{tag} {name}", ["已具备", "部分具备", "不具备"], index=2, horizontal=True, key=f"ev_{idx}")
        
        user_choices[idx] = choice

# ========== 核心计算逻辑 ==========
def calc_score():
    triggered_redlines = []
    final_score = 0

    # 1. 身份绝对红线
    if emp_status in identity_abs_redline:
        triggered_redlines.append({
            "类型": "身份绝对保护红线",
            "描述": f"{emp_status}属法定不得解除情形，无论证据是否充分均认定违法解除",
            "依据": "《劳动合同法》第42条"
        })
        return 0, triggered_redlines

    # 2. 客观情况重大变化专属规则
    if reason == "客观情况重大变化":
        # 地域红线：北京直接0分
        if risk_grade == "北京":
            triggered_redlines.append({
                "类型": "地域裁判红线",
                "描述": "北京地区司法实践对「客观情况重大变化」认定标准极严，企业自主架构调整原则上不予认可",
                "依据": "北京地区劳动争议裁判指引"
            })
            return 0, triggered_redlines

        # 业务前置红线：部门要求立刻解决
        for idx, item in enumerate(ev_list):
            if item["type"] == "precondition":
                if user_choices[idx] == "是":
                    triggered_redlines.append({
                        "类型": "业务流程红线",
                        "描述": "部门要求立刻解决，无法履行法定协商程序，解除行为必然存在程序瑕疵",
                        "依据": "《劳动合同法》第40条第3项"
                    })
                    return 20, triggered_redlines
                break

        # 正常评分
        base_full = 65
        total_deduct = 0
        total_bonus = 0
        r_coeff = region_coeff[risk_grade]
        i_coeff = identity_multiplier.get(emp_status, 1.0)

        # 联动项状态
        link_status = "是"
        for idx, item in enumerate(ev_list):
            if item["type"] == "link" and item.get("field_key") == "has_same_post":
                link_status = user_choices[idx]
                break

        # 遍历计算
        for idx, item in enumerate(ev_list):
            item_type = item["type"]
            if item_type in ["precondition", "link"]:
                continue
            status = user_choices[idx]
            if status == "已具备":
                factor = 0.0
            elif status == "部分具备":
                factor = 0.5
            else:
                factor = 1.0

            if item_type == "deduct":
                if item.get("link_field") == "has_same_post" and link_status == "否":
                    deduct = 0
                else:
                    deduct = item["base_score"] * factor * r_coeff * i_coeff
                total_deduct += deduct
                if item["redline"] and status == "不具备":
                    triggered_redlines.append({
                        "类型": "证据缺失红线",
                        "描述": f"必备证据缺失：{item['name']}",
                        "依据": item["desc"]
                    })
            elif item_type == "bonus":
                bonus = item["base_score"] * (1 - factor)
                total_bonus += bonus

        final_score = base_full - total_deduct + total_bonus

    else:
        # 严重违纪 / 不胜任工作
        r_coeff = region_coeff[risk_grade]
        i_coeff = identity_multiplier.get(emp_status, 1.0)
        total_deduct = 0

        for idx, item in enumerate(ev_list):
            status = user_choices[idx]
            if status == "已具备":
                factor = 0.0
            elif status == "部分具备":
                factor = 0.5
            else:
                factor = 1.0
            deduct = item["base_score"] * factor * r_coeff * i_coeff
            total_deduct += deduct
            if item["redline"] and status == "不具备":
                triggered_redlines.append({
                    "类型": "证据缺失红线",
                    "描述": f"必备证据缺失：{item['name']}",
                    "依据": item["desc"]
                })
        final_score = 100 - total_deduct

    final_score = max(0.0, min(100.0, final_score))
    return final_score, triggered_redlines

score, redlines = calc_score()

# ========== 结果判定 ==========
def get_verdict(score, line_count):
    if emp_status in identity_abs_redline or (reason == "客观情况重大变化" and risk_grade == "北京"):
        return "极高风险", COLOR_RED, "本案已触发法定禁止解除情形，解除行为缺乏法律依据，已构成违法解除。", "认定违法解除，员工主张赔偿金或恢复劳动关系大概率获得支持。"
    elif line_count >= 3 or score < 40:
        return "极高风险", "#822727", "用人单位举证严重不足，核心法定要件缺失，解除行为合法性无法成立。", "大概率认定违法解除，建议立即停止解除动作，主动协商降低赔偿。"
    elif score >= 80 and line_count == 0:
        return "低风险", COLOR_GREEN, "用人单位解除事实清楚、证据充分，程序符合法律规定，解除行为合法有效。", "合规解除概率大，仲裁及诉讼阶段胜诉把握较高。"
    elif 60 <= score < 80:
        return "中风险", "#d69e2e", "用人单位解除具备基本事实依据，但存在局部证据瑕疵或程序瑕疵。", "直接胜诉存在不确定性，建议优先调解协商，争取和解降低用工成本。"
    else:
        return "高风险", COLOR_RED, "用人单位证据存在明显不足，或已违反法定解除程序，解除行为合法性存疑。", "大概率认定违法解除，建议主动与员工协商，控制赔偿金额。"

level, color, main_text, result_text = get_verdict(score, len(redlines))

# ========== 右侧结果展示 ==========
with col2:
    st.subheader("风险评估结果")
    st.metric("证据充足度", f"{round(score, 1)} 分")
    st.markdown(f"<h3 style='color:{color};'>风险等级：{level}</h3>", unsafe_allow_html=True)
    
    # 诉讼博弈提示
    jurisdiction = company_jurisdiction.get(company, [])
    if company == "科弘昌" and province not in jurisdiction:
        st.info("💡 **诉讼博弈提示**：员工需异地出庭，存在时间与差旅成本，可作为协商压价的博弈点。")
    elif company == "同科林" and province not in jurisdiction:
        st.info("💡 **诉讼博弈提示**：员工需异地出庭，存在时间与差旅成本，可作为协商压价的博弈点。")
    elif company == "同科林分公司":
        st.info("💡 **主体提示**：属地应诉无管辖优势，建议重点打磨证据链。")
    elif company == "外包":
        st.info("💡 **主体提示**：可主张用工主体不适格，引导员工向外包公司主张权利。")
    elif company == "派遣":
        st.info("💡 **主体提示**：可提出主体异议与管辖异议，拉长诉讼周期增加员工成本。")

st.divider()

# ========== 详细结果 ==========
tab1, tab2, tab3 = st.tabs(["红线预警", "模拟裁决", "补证建议"])

with tab1:
    if redlines:
        for i, line in enumerate(redlines, 1):
            st.markdown(f"**{i}. 【{line['类型']}】** {line['描述']}")
            st.caption(f"依据：{line['依据']}")
    else:
        st.success("✅ 未触发法定违法解除红线")

with tab2:
    st.markdown(f"**裁判观点**：{main_text}")
    st.markdown(f"**裁决倾向**：{result_text}")

with tab3:
    has_suggest = False
    for idx, item in enumerate(ev_list):
        if item["type"] in ["precondition", "link"]:
            continue
        status = user_choices[idx]
        name = item["name"]
        if status == "不具备":
            priority = "高优先级" if item["level"] == "必备" else "中优先级"
            st.write(f"• 【{priority}】补充：{name}")
            has_suggest = True
        elif status == "部分具备":
            st.write(f"• 【中优先级】完善：{name}（补充原件/签字/原始载体）")
            has_suggest = True
    if not has_suggest:
        st.success("✅ 证据链完整，建议保持现有证据留存规范")

# ========== 导出报告 ==========
st.divider()
def generate_report():
    report = f"""{'='*60}
          科林劳动争议风险评估器 诊断报告
          生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

【一、案件基础信息】
工作省份：{province}（{risk_grade}裁判口径）
签约主体：{company}
解除理由：{reason}
员工身份：{emp_status}

【二、证据充足度评估】
综合得分：{round(score, 1)} 分
风险等级：{level}

【三、违法解除红线预警】
"""
    if redlines:
        for i, line in enumerate(redlines, 1):
            report += f"{i}. [{line['类型']}] {line['描述']}\n   依据：{line['依据']}\n\n"
    else:
        report += "未触发法定违法解除红线\n\n"
    
    report += f"""【四、模拟仲裁裁决】
{main_text}
{result_text}

【五、补证优化建议】
"""
    for idx, item in enumerate(ev_list):
        if item["type"] in ["precondition", "link"]:
            continue
        status = user_choices[idx]
        if status == "不具备":
            report += f"• 【高优先级】补充：{item['name']}\n"
        elif status == "部分具备":
            report += f"• 【中优先级】完善：{item['name']}\n"
    return report

st.download_button(
    label="📥 导出诊断报告（TXT）",
    data=generate_report(),
    file_name=f"劳动争议风险诊断报告_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt",
    mime="text/plain"
)

# 底部版权
st.markdown("<div style='text-align:right;color:#999;font-size:12px;'>创作权：李超Eddie</div>", unsafe_allow_html=True)