import streamlit as st
from datetime import datetime

# -------------------------- 全局页面配置 --------------------------
st.set_page_config(page_title="CLINICO 科林劳动争议风险评估器（HR内部使用）", layout="wide")
# 科林品牌色
COLOR_MAIN = "#F5B800"
COLOR_RED = "#C53030"
COLOR_GREEN = "#2F855A"
COLOR_WARN = "#d69e2e"

# 初始化页面状态（默认停在第一步）
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
# 存储所有填写数据
if "case_data" not in st.session_state:
    st.session_state.case_data = {}
if "evidence_selections" not in st.session_state:
    st.session_state.evidence_selections = {}
if "calc_result" not in st.session_state:
    st.session_state.calc_result = None

# -------------------------- 固定业务规则（和本地软件1:1复制） --------------------------
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
region_coeff = {"北京": 1.2, "其他高风险": 1.1, "其他低风险": 1.0, "上海": 0.9}
identity_abs_redline = ["三期女职工", "距退休不足5年员工"]
identity_multiplier = {"普通员工": 1.0, "带人经理": 1.2, "无固定期限合同员工": 1.5, "医疗期内员工": 1.8}
company_jurisdiction = {"科弘昌": ["北京", "天津", "河北"], "同科林": ["上海", "浙江", "江苏"], "同科林分公司": [], "其他": [], "外包": [], "派遣": []}

evidence_rules = {
    "严重违纪": [
        {"name": "违纪行为书面/实物证据（考勤、违规单据、监控截图等）", "type": "deduct", "level": "必备", "base_score": 20, "redline": True, "desc": "无直接事实证据，无法认定违纪行为存在"},
        {"name": "违纪事项沟通确认记录（书面签字/谈话录音/聊天记录）", "type": "deduct", "level": "必备", "base_score": 20, "redline": True, "desc": "未向员工告知违纪事项，处罚程序严重瑕疵"},
        {"name": "相关依据制度的签收记录", "type": "deduct", "level": "必备", "base_score": 20, "redline": True, "desc": "员工未知晓制度，处罚无合法支撑"},
        {"name": "已向员工送达限期整改/警告通知", "type": "deduct", "level": "重要", "base_score": 15, "redline": False, "desc": "未给整改机会，易被认定处罚过重、比例失当"},
        {"name": "违纪行为发生在近3个月内（处理时效合规）", "type": "deduct", "level": "重要", "base_score": 15, "redline": False, "desc": "处理间隔过久，处罚合理性存疑"},
        {"name": "员工未就解除提出书面异议", "type": "deduct", "level": "辅助", "base_score": 10, "redline": False, "desc": "员工未提异议可主张默认认可；已提书面异议则举证压力加大"}
    ],
    "不能胜任工作": [
        {"name": "首次不胜任工作的书面证据", "type": "deduct", "level": "必备", "base_score": 25, "redline": True, "desc": "无有效考核结论，不胜任主张直接不成立"},
        {"name": "PIP绩效改进目标清晰可量化", "type": "deduct", "level": "必备", "base_score": 20, "redline": True, "desc": "目标模糊主观，司法实践不予采信"},
        {"name": "PIP期间培训/辅导的书面记录与签字", "type": "deduct", "level": "必备", "base_score": 20, "redline": True, "desc": "无培训辅导记录，改进程序法定要件缺失"},
        {"name": "改进期后二次不胜任的考核证据", "type": "deduct", "level": "必备", "base_score": 15, "redline": True, "desc": "无二次不胜任证明，不满足法定解除条件"},
        {"name": "岗位说明书与明确考核标准", "type": "deduct", "level": "重要", "base_score": 12, "redline": False, "desc": "岗位标准越清晰，主张可信度越高；缺失不直接败诉"},
        {"name": "可向员工提供合理调岗机会", "type": "deduct", "level": "重要", "base_score": 8, "redline": False, "desc": "有调岗机会胜率更高；无调岗机会不直接导致违法"}
    ],
    "客观情况重大变化": [
        {"name": "【前置判定】部门是否要求立刻解决", "type": "precondition", "level": "前置红线", "base_score": 0, "redline": True, "desc": "要求立刻解决则无法履行法定协商程序，直接极高风险"},
        {"name": "部门愿意出具正式组织架构调整通知", "type": "deduct", "level": "重要", "base_score": 25, "redline": False, "desc": "无正式文件则客观变化无书面支撑"},
        {"name": "【联动项】是否存在其他同类型在岗岗位", "type": "link", "level": "联动规则", "base_score": 0, "redline": False, "field_key": "has_same_post", "desc": "无同类岗位则调岗义务自动豁免"},
        {"name": "可向员工提供合理调岗机会", "type": "deduct", "level": "重要", "base_score": 20, "redline": False, "link_field": "has_same_post", "desc": "无其他同类岗位时，该项不扣分"},
        {"name": "解除通知已书面有效送达员工", "type": "deduct", "level": "辅助", "base_score": 10, "redline": False, "desc": "程序瑕疵，不影响实体认定"},
        {"name": "【加分项】重大变化事项存在政策外因", "type": "bonus", "level": "正向加分", "base_score": 15, "redline": False, "desc": "有外部政策支撑，司法认可度大幅提升"},
        {"name": "【加分项】双方已就变更劳动合同协商并有书面记录", "type": "bonus", "level": "正向加分", "base_score": 20, "redline": False, "desc": "履行法定协商程序是核心要件"}
    ]
}

# -------------------------- 核心计算函数（和本地软件完全一致） --------------------------
def calculate_result():
    data = st.session_state.case_data
    choices = st.session_state.evidence_selections
    ev_list = evidence_rules[data["reason"]]
    triggered_redlines = []
    final_score = 0
    emp_status = data["emp_status"]
    risk_grade = data["risk_grade"]
    reason = data["reason"]

    # 身份绝对红线
    if emp_status in identity_abs_redline:
        triggered_redlines.append({"类型": "身份绝对保护红线", "描述": f"{emp_status}属法定不得解除情形，无论证据是否充分均认定违法解除", "依据": "《劳动合同法》第42条"})
        return 0.0, triggered_redlines

    # 客观情况重大变化专属逻辑
    if reason == "客观情况重大变化":
        if risk_grade == "北京":
            triggered_redlines.append({"类型": "地域裁判红线", "描述": "北京地区司法实践对「客观情况重大变化」认定标准极严，企业自主架构调整原则上不予认可", "依据": "北京地区劳动争议裁判指引"})
            return 0.0, triggered_redlines
        # 前置红线判定
        for idx, item in enumerate(ev_list):
            if item["type"] == "precondition" and choices[idx] == "是":
                triggered_redlines.append({"类型": "业务流程红线", "描述": "部门要求立刻解决，无法履行法定协商程序，解除行为必然存在程序瑕疵", "依据": "《劳动合同法》第40条第3项"})
                return 20.0, triggered_redlines
                break
        base_full = 65
        total_deduct = 0
        total_bonus = 0
        r_coeff = region_coeff[risk_grade]
        i_coeff = identity_multiplier.get(emp_status, 1.0)
        link_status = "是"
        for idx, item in enumerate(ev_list):
            if item["type"] == "link" and item.get("field_key") == "has_same_post":
                link_status = choices[idx]
                break
        for idx, item in enumerate(ev_list):
            itype = item["type"]
            if itype in ["precondition", "link"]:
                continue
            stat = choices[idx]
            factor = 0.0 if stat == "已具备" else 0.5 if stat == "部分具备" else 1.0
            if itype == "deduct":
                if item.get("link_field") == "has_same_post" and link_status == "否":
                    deduct = 0
                else:
                    deduct = item["base_score"] * factor * r_coeff * i_coeff
                total_deduct += deduct
                if item["redline"] and stat == "不具备":
                    triggered_redlines.append({"类型": "证据缺失红线", "描述": f"必备证据缺失：{item['name']}", "依据": item["desc"]})
            elif itype == "bonus":
                bonus = item["base_score"] * (1 - factor)
                total_bonus += bonus
        final_score = base_full - total_deduct + total_bonus
    else:
        r_coeff = region_coeff[risk_grade]
        i_coeff = identity_multiplier.get(emp_status, 1.0)
        total_deduct = 0
        for idx, item in enumerate(ev_list):
            stat = choices[idx]
            factor = 0.0 if stat == "已具备" else 0.5 if stat == "部分具备" else 1.0
            deduct = item["base_score"] * factor * r_coeff * i_coeff
            total_deduct += deduct
            if item["redline"] and stat == "不具备":
                triggered_redlines.append({"类型": "证据缺失红线", "描述": f"必备证据缺失：{item['name']}", "依据": item["desc"]})
        final_score = 100 - total_deduct
    final_score = max(0.0, min(100.0, final_score))
    return round(final_score, 1), triggered_redlines

# -------------------------- 页面切换函数 --------------------------
def next_step():
    st.session_state.current_step += 1
def prev_step():
    st.session_state.current_step -= 1
def reset_all():
    st.session_state.current_step = 1
    st.session_state.case_data = {}
    st.session_state.evidence_selections = {}
    st.session_state.calc_result = None

# -------------------------- 页面标题与底部版权（已修正CLINICO） --------------------------
st.markdown(f"<h2 style='color:{COLOR_MAIN};'>CLINICO 科林劳动争议风险评估器（HR内部使用）</h2>", unsafe_allow_html=True)
st.markdown("<div style='text-align:right;color:#999999;'>创作权：李超Eddie</div>", unsafe_allow_html=True)
st.divider()

# 步骤进度条展示
step_text = ["第一步：案件核心信息录入", "第二步：证据清单核验", "第三步：风险诊断报告"]
st.subheader(f"当前：{step_text[st.session_state.current_step - 1]}")
st.progress((st.session_state.current_step - 1) / 2)
st.divider()

# ====================== 第一步：基础信息录入 ======================
if st.session_state.current_step == 1:
    st.subheader("案件核心要素")
    province_list = sorted(list(province_risk_map.keys()))
    col1, col2 = st.columns(2)
    with col1:
        select_prov = st.selectbox("工作省份", province_list, index=province_list.index("上海"))
        select_reason = st.selectbox("解除核心理由", list(evidence_rules.keys()))
    with col2:
        select_company = st.selectbox("签约主体", ["科弘昌", "同科林", "同科林分公司", "其他", "外包", "派遣"], index=1)
        select_emp = st.selectbox("员工特殊身份", ["普通员工", "带人经理", "无固定期限合同员工", "三期女职工", "距退休不足5年员工", "医疗期内员工"])
    st.caption("* 系统自动匹配地域裁判口径、身份保护等级、异地诉讼博弈空间")
    # 保存数据到缓存
    st.session_state.case_data = {
        "province": select_prov,
        "risk_grade": province_risk_map[select_prov],
        "company": select_company,
        "reason": select_reason,
        "emp_status": select_emp
    }
    # 下一步按钮（科林黄色）
    st.button("下一步：证据核验 >>", on_click=next_step, type="primary", use_container_width=True)

# ====================== 第二步：证据核验页面 ======================
elif st.session_state.current_step == 2:
    data = st.session_state.case_data
    ev_list = evidence_rules[data["reason"]]
    st.caption(f"解除理由：{data['reason']} ｜ 地域裁判口径：{data['risk_grade']}，逐项选择状态实时计算得分")
    st.divider()
    choices = {}
    for idx, item in enumerate(ev_list):
        name = item["name"]
        level = item["level"]
        itype = item["type"]
        # 标签颜色区分
        if level == "必备":
            tag = f":red[【{level}】]"
        elif level == "正向加分":
            tag = f":green[【{level}】]"
        elif itype in ["precondition", "link"]:
            tag = f":orange[【{level}】]"
        else:
            tag = f"【{level}】"
        # 两选项（前置/联动）、三选项区分
        if itype in ["precondition", "link"]:
            opt = st.radio(f"{tag} {name}", ["是", "否"], index=1, horizontal=True, key=f"ev_{idx}")
        else:
            opt = st.radio(f"{tag} {name}", ["已具备", "部分具备", "不具备"], index=2, horizontal=True, key=f"ev_{idx}")
        choices[idx] = opt
    # 保存证据选择
    st.session_state.evidence_selections = choices
    # 底部按钮行
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        st.button("<< 上一步", on_click=prev_step, use_container_width=True)
    with col_btn2:
        st.button("生成诊断报告 >>", on_click=next_step, type="primary", use_container_width=True)

# ====================== 第三步：诊断报告页面 ======================
elif st.session_state.current_step == 3:
    # 执行计算
    score, redlines = calculate_result()
    st.session_state.calc_result = (score, redlines)
    data = st.session_state.case_data
    line_count = len(redlines)
    emp_status = data["emp_status"]
    risk_grade = data["risk_grade"]
    reason = data["reason"]

    # 风险等级判定（和本地软件阈值完全一致）
    if emp_status in identity_abs_redline or (reason == "客观情况重大变化" and risk_grade == "北京"):
        risk_level = "极高风险"
        risk_color = COLOR_RED
        view_text = "本仲裁庭认为：本案已触发法定禁止解除情形，解除行为缺乏法律依据，已构成违法解除。"
        res_text = "裁决：认定违法解除，员工主张赔偿金或恢复劳动关系大概率获得支持。"
    elif line_count >= 3 or score < 40:
        risk_level = "极高风险"
        risk_color = "#822727"
        view_text = "本仲裁庭认为：用人单位举证严重不足，核心法定要件缺失，解除行为合法性无法成立。"
        res_text = "裁决：大概率认定违法解除，建议立即停止解除动作，主动协商降低赔偿。"
    elif score >= 80 and line_count == 0:
        risk_level = "低风险"
        risk_color = COLOR_GREEN
        view_text = "本仲裁庭认为：用人单位解除事实清楚、证据充分，程序符合法律规定，解除行为合法有效。"
        res_text = "裁决倾向：合规解除概率大，仲裁及诉讼阶段胜诉把握较高。"
    elif 60 <= score < 80:
        risk_level = "中风险"
        risk_color = COLOR_WARN
        view_text = "本仲裁庭认为：用人单位解除具备基本事实依据，但存在局部证据瑕疵或程序瑕疵。"
        res_text = "裁决倾向：直接胜诉存在不确定性，建议优先调解协商，争取和解降低用工成本。"
    else:
        risk_level = "高风险"
        risk_color = COLOR_RED
        view_text = "本仲裁庭认为：用人单位证据存在明显不足，或已违反法定解除程序，解除行为合法性存疑。"
        res_text = "裁决倾向：大概率认定违法解除，建议主动与员工协商，控制赔偿金额。"

    # 总览信息
    col_score, col_risk, col_region = st.columns(3)
    with col_score:
        st.metric("证据综合得分", f"{score} 分")
    with col_risk:
        st.markdown(f"<h4 style='color:{risk_color}'>风险等级：{risk_level}</h4>", unsafe_allow_html=True)
    with col_region:
        st.info(f"地域裁判等级：{risk_grade}")

    # 诉讼博弈提示
    jurisdiction = company_jurisdiction.get(data["company"], [])
    tip_text = ""
    if data["company"] == "科弘昌" and data["province"] not in jurisdiction:
        tip_text = "💡 诉讼博弈提示：员工签约主体为科弘昌，工作地不在管辖范围内，员工异地出庭存在时间差旅成本，可作为协商压价筹码。"
    elif data["company"] == "同科林" and data["province"] not in jurisdiction:
        tip_text = "💡 诉讼博弈提示：员工签约主体为同科林，工作地不在江浙沪管辖范围内，员工异地出庭存在时间差旅成本，可作为协商压价筹码。"
    elif data["company"] == "同科林分公司":
        tip_text = "💡 主体提示：属地分公司应诉无地域优势，务必完善全部证据链。"
    elif data["company"] == "外包":
        tip_text = "💡 主体提示：用工属于外包，可主张用工主体不适格，引导员工向外包公司维权。"
    elif data["company"] == "派遣":
        tip_text = "💡 主体提示：劳务派遣用工，可提出管辖异议拉长诉讼周期，增加员工维权成本。"
    if tip_text:
        st.info(tip_text)
    st.divider()

    # 分标签展示报告内容
    tab1, tab2, tab3 = st.tabs(["违法红线预警", "模拟仲裁裁决", "补证优化建议"])
    ev_list = evidence_rules[data["reason"]]
    choices = st.session_state.evidence_selections

    with tab1:
        if len(redlines) > 0:
            for idx, line in enumerate(redlines, 1):
                st.markdown(f"**{idx}. 【{line['类型']}】{line['描述']}**")
                st.caption(f"法律依据：{line['依据']}")
        else:
            st.success("✅ 未触发任何法定违法解除红线")

    with tab2:
        st.markdown(f"**仲裁员观点：** {view_text}")
        st.markdown(f"**最终裁决倾向：** {res_text}")

    with tab3:
        has_suggest = False
        for idx, item in enumerate(ev_list):
            if item["type"] in ["precondition", "link"]:
                continue
            stat = choices[idx]
            name = item["name"]
            if stat == "不具备":
                priority = "高优先级" if item["level"] == "必备" else "中优先级"
                st.write(f"• 【{priority}】补充材料：{name}")
                has_suggest = True
            elif stat == "部分具备":
                st.write(f"• 【中优先级】完善材料：{name}（补充签字原件/原始录音/书面凭证）")
                has_suggest = True
        if not has_suggest:
            st.success("✅ 当前全部证据完整，无需要补充完善的材料")

    st.divider()
    # 导出TXT报告函数
    def build_report_text():
        report = f"""{'='*62}
              CLINICO 科林劳动争议风险评估器 诊断报告
              生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*62}

【一、案件基础信息】
工作省份：{data['province']}（{data['risk_grade']}裁判口径）
签约主体：{data['company']}
解除理由：{data['reason']}
员工身份：{data['emp_status']}

【二、证据评估得分】
综合得分：{score} 分
风险等级：{risk_level}

【三、违法解除红线预警】
"""
        if redlines:
            for i, line in enumerate(redlines, 1):
                report += f"{i}. [{line['类型']}] {line['描述']}\n   依据：{line['依据']}\n\n"
        else:
            report += "未触发法定违法解除红线\n\n"

        report += f"""【四、模拟仲裁裁决】
仲裁观点：{view_text}
裁决倾向：{res_text}

【五、补证优化建议】
"""
        for idx, item in enumerate(ev_list):
            if item["type"] in ["precondition", "link"]:
                continue
            stat = choices[idx]
            if stat == "不具备":
                report += f"• 高优先级补充：{item['name']}\n"
            elif stat == "部分具备":
                report += f"• 中优先级完善：{item['name']}\n"
        return report

    st.download_button(
        label="📥 导出完整诊断报告（TXT）",
        data=build_report_text(),
        file_name=f"科林劳动争议诊断报告_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )
    st.divider()
    # 底部操作按钮
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        st.button("<< 返回证据核验", on_click=prev_step, use_container_width=True)
    with col_btn2:
        st.button("重新开始全部诊断", on_click=reset_all, use_container_width=True)