# 使用reportlab生成PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册中文字体
try:
    pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))
    chinese_font = 'SimSun'
except:
    try:
        pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc'))
        chinese_font = 'SimSun'
    except:
        chinese_font = 'Helvetica'

# 创建PDF
doc = SimpleDocTemplate(
    '/root/.openclaw/workspace/output/严国贤_研发总监_简历_优化版.pdf',
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm
)

# 样式
styles = getSampleStyleSheet()

# 自定义样式
title_style = ParagraphStyle(
    'Title',
    parent=styles['Heading1'],
    fontName=chinese_font,
    fontSize=24,
    spaceAfter=12,
    textColor=colors.HexColor('#2c3e50')
)

heading2_style = ParagraphStyle(
    'Heading2',
    parent=styles['Heading2'],
    fontName=chinese_font,
    fontSize=14,
    spaceBefore=16,
    spaceAfter=8,
    textColor=colors.HexColor('#2c3e50')
)

heading3_style = ParagraphStyle(
    'Heading3',
    parent=styles['Heading3'],
    fontName=chinese_font,
    fontSize=12,
    spaceBefore=12,
    spaceAfter=6,
    textColor=colors.HexColor('#34495e')
)

heading4_style = ParagraphStyle(
    'Heading4',
    parent=styles['Heading4'],
    fontName=chinese_font,
    fontSize=11,
    spaceBefore=10,
    spaceAfter=4,
    textColor=colors.HexColor('#555')
)

body_style = ParagraphStyle(
    'Body',
    parent=styles['BodyText'],
    fontName=chinese_font,
    fontSize=10,
    leading=16,
    spaceAfter=6
)

bullet_style = ParagraphStyle(
    'Bullet',
    parent=styles['BodyText'],
    fontName=chinese_font,
    fontSize=10,
    leading=16,
    leftIndent=20,
    spaceAfter=4
)

# 内容
story = []

# 标题
story.append(Paragraph("个人简历", title_style))
story.append(Spacer(1, 0.3*cm))

# 基本信息
story.append(Paragraph("<b>严国贤</b>", ParagraphStyle('Name', parent=body_style, fontSize=14)))
story.append(Paragraph("📞 +86 158 2079 8214 | ✉ yanguoxian122@163.com", body_style))
story.append(Paragraph("🎯 <b>求职意向：研发总监</b>", body_style))
story.append(Spacer(1, 0.5*cm))

# 核心优势
story.append(Paragraph("核心优势", heading2_style))
advantages = [
    "<b>战略规划</b>：12年数据通信行业经验，专注企业级网络基础设施。历任无线、锐灵、数通产品线负责人，具备从战略洞察、产品体系规划到规模化交付的端到端闭环能力。",
    "<b>组织与平台双轮驱动</b>：既能统筹300人研发团队完成体系变革与效能提升，也能主导平台级架构重构与产品矩阵布局。",
    "<b>商业敏锐度</b>：深谙2B市场与头部客户大规模组网特征，服务过亚朵等行业标杆客户，具备从方案定义到招标落地的商业闭环能力。",
    "<b>长期价值构建</b>：擅长平衡商业模式与技术实现，推动产品价值转化与规模化交付。"
]
for adv in advantages:
    story.append(Paragraph(f"• {adv}", bullet_style))
story.append(Spacer(1, 0.3*cm))

# 工作经历
story.append(Paragraph("工作经历", heading2_style))
story.append(Paragraph("深信服科技股份有限公司 - 信锐网科", heading3_style))

# 数通产品总监
story.append(Paragraph("数通产品总监 | 2025.02 - 至今", heading4_style))
story.append(Paragraph("围绕智能运维与高可靠架构战略，负责数通产品体系顶层规划与平台能力升级，推动AI运维与可视化分析能力沉淀，支撑头部客户大规模组网市场突破。", body_style))
story.append(Paragraph("<b>工作内容：</b>", body_style))
work_content = [
    "系统梳理数通产品梯队与技术演进路径（AP/SW/控制器），明确能力边界与版本节奏",
    "主导全网智能3.0升级，整合AI运维助手与可视化网络管理，重构智能运维闭环体系",
    "规划高可靠集群平台能力，支撑Portal服务器与大规模组网场景",
    "建立头部客户联合创新机制，形成\"规划—验证—迭代\"快速闭环"
]
for item in work_content:
    story.append(Paragraph(f"• {item}", bullet_style))

story.append(Paragraph("<b>成果：</b>", body_style))
work_results = [
    "推动网络可视化分析产品立项，完善控制器与平台产品矩阵",
    "形成全网智能版本化演进路径，聚焦可闭环场景落地",
    "完成集群1.0高可靠架构落地，支撑亚朵等头部客户招标项目",
    "提升大规模组网项目竞争力与业务连续性能"
]
for item in work_results:
    story.append(Paragraph(f"• {item}", bullet_style))

# 研发副总监
story.append(Paragraph("研发副总监 | 2023.12 - 2025.01", heading4_style))
story.append(Paragraph("管理300人研发团队，负责研发体系组织建设（敏捷变革、人才培养、效能提升）。", body_style))
story.append(Paragraph("<b>成果：</b>", body_style))
rd_results = [
    "<b>【组织建设】</b>结合IPD流程与敏捷实践，推动体系敏捷变革，迭代周期从4周缩短至2周（缩短50%）",
    "<b>【效能提升】</b>引入AI工具链（代码生成、测试用例生成），测试效能提升20%",
    "<b>【人才培养】</b>实施\"舵航计划\"（技术骨干培养项目），培养20名技术负责人，认证通过率100%"
]
for item in rd_results:
    story.append(Paragraph(f"• {item}", bullet_style))

# 研发主管
story.append(Paragraph("研发主管 | 2018.05 - 2023.11", heading4_style))
story.append(Paragraph("统筹无线业务、IAM身份管理、锐灵团队的产品研发与团队组织建设。", body_style))
story.append(Paragraph("<b>成果：</b>", body_style))
manager_results = [
    "推动IAM产品立项，关键特性并入集团\"ID-Trust\"，形成零信任方案",
    "推动锐灵\"网络三件套+云平台\"战略落地，形成\"智简、安全、云服务\"品牌标签",
    "主导敏捷变革，需求返工减少50%，测试自动化率75%，迭代周期缩短50%",
    "荣获\"卓越管理者奖\"（Top 5%）"
]
for item in manager_results:
    story.append(Paragraph(f"• {item}", bullet_style))

# 技术经理
story.append(Paragraph("技术经理/项目经理 | 2015.11 - 2018.04", heading4_style))
story.append(Paragraph("负责统一认证平台与集结号2.0的设计与交付，带领30人团队完成大型项目。", body_style))
story.append(Paragraph("<b>成果：</b>", body_style))
tech_results = [
    "打造数通行业最丰富的认证方式，沿用至今，提升政府、教育行业竞争力",
    "荣获\"优秀管理人员奖\"（Top 10%）"
]
for item in tech_results:
    story.append(Paragraph(f"• {item}", bullet_style))

# 关键项目经验
story.append(Paragraph("关键项目经验", heading2_style))

# 项目1
story.append(Paragraph("锐灵\"网络三件套+云平台\"战略落地 | 研发主管 | 2021-2023", heading3_style))
story.append(Paragraph("<b>情景：</b>数通市场整体下沉，分销盘面增长，友商产品迭代快，需打造差异化标签。", body_style))
story.append(Paragraph("<b>任务：</b>面向中小微用户提供基础网络与云端服务（含云管、云认证、云安全等核心功能）。", body_style))
story.append(Paragraph("<b>行动：</b>开展客户调研与竞品分析，组建云与基础网络研发团队，推动云原生架构与敏捷变革。", body_style))
story.append(Paragraph("<b>结果：</b>首年销售额4000万，次年8000万；塑造\"智简、安全、云服务\"标签，推动SaaS化订阅落地。", body_style))

# 项目2
story.append(Paragraph("全网智能升级与集群高可靠平台建设 | 数通产品总监 | 2025", heading3_style))
story.append(Paragraph("<b>情景：</b>头部客户组网规模扩大，对智能运维效率与业务连续性要求显著提升，现有能力分散、闭环不足。", body_style))
story.append(Paragraph("<b>任务：</b>重构智能运维体系，打造高可靠平台能力，支撑规模化组网与招标项目突破。", body_style))
story.append(Paragraph("<b>行动：</b>", body_style))
project2_actions = [
    "从战略目标出发拆解能力结构，聚焦\"可验证、可闭环\"场景",
    "优化巡检与根因分析逻辑，重构智能能力优先级",
    "设计集群1.0架构，统一高可靠与兼容能力",
    "建立头部客户验证机制，缩短需求确认与版本迭代周期"
]
for item in project2_actions:
    story.append(Paragraph(f"• {item}", bullet_style))
story.append(Paragraph("<b>结果：</b>", body_style))
project2_results = [
    "明确全网智能升级路径并完成版本规划",
    "集群1.0成功落地并支撑头部客户招标答辩",
    "构建\"战略拆解—能力重构—客户共创—平台沉淀\"的可复制方法论"
]
for item in project2_results:
    story.append(Paragraph(f"• {item}", bullet_style))

# 项目3
story.append(Paragraph("基于敏捷变革的组织效能提升 | 研发副总监 | 2023-2025", heading3_style))
story.append(Paragraph("<b>情景：</b>业务快速发展，研发效能面临挑战，需要培养核心基层干部并沉淀组织过程资产。", body_style))
story.append(Paragraph("<b>任务：</b>通过敏捷变革提升交付质量，打造自组织团队；引入AI工具，提升整体效能。", body_style))
story.append(Paragraph("<b>结果：</b>测试自动化率75%，测试效能提升20%，迭代周期缩短50%，输出20名技术骨干。", body_style))

# 项目4
story.append(Paragraph("无线统一认证平台 | 技术经理/项目经理 | 2017-2018", heading3_style))
story.append(Paragraph("<b>情景：</b>政府、教育行业客户需兼容利旧多厂商设备，实现统一认证与漫游。", body_style))
story.append(Paragraph("<b>行动：</b>预研Aruba、Cisco、华为等厂商认证协议，设计无缝对接方案。", body_style))
story.append(Paragraph("<b>结果：</b>方案落地，支持多厂商设备统一认证，提升运维效率，拓展教育/政府行业市场。", body_style))

# 代表业绩表格
story.append(Paragraph("代表业绩", heading2_style))

table_data = [
    [Paragraph("<b>维度</b>", body_style), Paragraph("<b>成果</b>", body_style)],
    [Paragraph("组织能力", body_style), Paragraph("推动研发体系敏捷化升级，引入AI工具链与工程自动化能力，测试自动化率达75%，测试效能提升20%，迭代周期缩短50%，培养20名技术骨干，构建可持续人才梯队", body_style)],
    [Paragraph("平台能力", body_style), Paragraph("重构全网智能3.0体系，形成\"可闭环、可验证\"的智能运维演进路径；推动控制器与集群1.0高可靠平台建设，完善数通产品矩阵与架构竞争壁垒", body_style)],
    [Paragraph("商业能力", body_style), Paragraph("打造\"网络三件套+云平台\"，两年营收从4000万增长至8000万；主导亚朵招标高可靠方案，构建头部客户大规模组网标准化能力，提升业务连续性竞争力", body_style)],
    [Paragraph("行业突破", body_style), Paragraph("打造多厂商统一认证能力，兼容主流设备生态，提升政府/教育行业市场竞争力，形成差异化技术壁垒", body_style)]
]

table = Table(table_data, colWidths=[3*cm, 13*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('FONTNAME', (0, 0), (-1, -1), chinese_font),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
    ('PADDING', (0, 0), (-1, -1), 8),
]))
story.append(table)

# 教育背景
story.append(Paragraph("教育背景", heading2_style))
story.append(Paragraph("<b>西北大学</b> | 软件工程 | 本科 | 2009.09 - 2013.07", body_style))

# 资格证书
story.append(Paragraph("资格证书", heading2_style))
story.append(Paragraph("• PMP® 项目管理专业人士认证（2021）", bullet_style))
story.append(Paragraph("• ACP敏捷认证（完成培训）", bullet_style))

# 生成PDF
doc.build(story)
print("PDF generated successfully!")