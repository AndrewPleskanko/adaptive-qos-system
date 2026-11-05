#!/usr/bin/env python3
"""
Automated Academic Word Document Generator (.docx) for MCETI-2026 Conference Paper
Department of Automation of Electrical and Mechatronic Complexes (KPI)

Formats according to Ukrainian Academic and Conference Publishing Standards:
  • Times New Roman (12 pt body, 13 pt bold title, 10.5 pt abstract/table)
  • Line spacing 1.15, first line indent 1.0 cm
  • Standard margins (Top/Bottom 20mm, Left 25mm, Right 15mm)
  • Embedded 300-DPI publication figures (Architecture & P99 latency scaling)
  • Styled tables with headers and cell borders
  • Professional mathematical formula styling
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_DOCX_PATH = os.path.join(PROJECT_ROOT, 'thesis', 'MCETI_2026_Pleskanko.docx')
IMG_ARCH_PATH = os.path.join(PROJECT_ROOT, 'thesis', 'images', 'architecture_diagram.png')
IMG_P99_PATH = os.path.join(PROJECT_ROOT, 'thesis', 'images', 'chart_p99_latency_scaling.png')


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for a table cell (in twips, 20 twips = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_shading(cell, color_hex):
    """Set cell background color."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def set_table_borders(table, color="CBD5E1", sz="4"):
    """Set uniform subtle borders for Word table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)


def build_document():
    doc = docx.Document()

    # ── Page Margins (A4) ──────────────────────────────────────────────────
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(25)
    section.right_margin = Mm(15)

    # ── Default Styles ────────────────────────────────────────────────────
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(15, 23, 42)  # #0f172a Dark Slate

    # ── Helper paragraph creators ─────────────────────────────────────────
    def add_meta_header(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.5)
        run.font.italic = True
        run.font.color.rgb = RGBColor(100, 116, 139)
        return p

    def add_section_header(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)
        run.font.bold = True
        return p

    def add_paper_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        run.font.bold = True
        return p

    def add_author(name, affiliation):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        r_name = p.add_run(name + "\n")
        r_name.font.bold = True
        r_name.font.size = Pt(11.5)
        r_aff = p.add_run(affiliation)
        r_aff.font.size = Pt(10)
        r_aff.font.italic = True
        p.paragraph_format.space_after = Pt(10)

    def add_abstract_block(label, text, kw_label, kw_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Mm(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.05
        
        r1 = p.add_run(label + " ")
        r1.font.bold = True
        r1.font.size = Pt(10)
        r2 = p.add_run(text)
        r2.font.size = Pt(10)

        p_kw = doc.add_paragraph()
        p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_kw.paragraph_format.first_line_indent = Mm(0)
        p_kw.paragraph_format.space_after = Pt(8)
        p_kw.paragraph_format.line_spacing = 1.05

        r_kw1 = p_kw.add_run(kw_label + " ")
        r_kw1.font.bold = True
        r_kw1.font.size = Pt(10)
        r_kw2 = p_kw.add_run(kw_text)
        r_kw2.font.size = Pt(10)

    def add_body_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Mm(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15

        if bold_prefix:
            r_pre = p.add_run(bold_prefix + " ")
            r_pre.font.bold = True
            r_pre.font.size = Pt(12)

        r_body = p.add_run(text)
        r_body.font.size = Pt(12)
        return p

    def add_formula(formula_text, formula_num):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15

        # We format as centered text with right-aligned numbering
        r_eq = p.add_run(f"    {formula_text}    ")
        r_eq.font.italic = True
        r_eq.font.size = Pt(11.5)

        r_num = p.add_run(f"({formula_num})")
        r_num.font.bold = True
        r_num.font.size = Pt(11.5)
        return p

    def add_figure(img_path, caption_text, width_inches=6.0):
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(6)
            p_img.paragraph_format.space_after = Pt(2)
            run = p_img.add_run()
            run.add_picture(img_path, width=Inches(width_inches))

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(8)
            r_cap = p_cap.add_run(caption_text)
            r_cap.font.bold = True
            r_cap.font.size = Pt(10.5)

    # ── DOCUMENT ASSEMBLY ──────────────────────────────────────────────────

    # Header
    add_meta_header("3 Міжнародна науково-практична конференція\n«Modern Challenges in Economic and Technological Innovation» (7–9 жовтня 2026, Болонья, Італія)")
    add_section_header("Секція: 11. Інформаційні технології та кібербезпека\nУДК 004.75:004.832.2")

    # Title & Author
    add_paper_title("МЕТОД ДИНАМІЧНОЇ ПРІОРИТЕЗАЦІЇ ТРАНЗАКЦІЙ У ВИСОКОНАВАНТАЖЕНИХ РОЗПОДІЛЕНИХ СИСТЕМАХ НА ОСНОВІ TREE-TO-CODE КОМПІЛЯЦІЇ ДЕРЕВ РІШЕНЬ")
    add_author("Плесканко А. В.",
               "магістрант кафедри автоматизації електротехнічних та мехатронних комплексів,\nНаціональний технічний університет України «Київський політехнічний інститут імені Ігоря Сікорського», м. Київ, Україна")

    # Abstract UKR
    add_abstract_block(
        "Анотація.",
        "У роботі вирішено науково-прикладну задачу зниження хвостової затримки (P99 latency) та запобігання каскадному блокуванню транзакційних черг у мікросервісних розподілених системах за пікових навантажень. Запропоновано комплексний метод адаптивної пріоритезації трафіку, що поєднує моніторинг інфраструктурної телеметрії (завантаження CPU, пам'яті, глибина черг Kafka, метрики пулу HikariCP) з алгоритмом класифікації на основі дерев рішень CART, скомпільованих у нативний програмний код (Tree-to-Code). Експериментальне моделювання масштабування до 100 000 транзакцій підтвердило зниження P99 latency на 95,2 % (з 912,4 мс у базовому FIFO до 44,1 мс в Adaptive ML) при утриманні частки високопріоритетного трафіку CRITICAL на рівні 8,76 %, що запобігає переповненню черг обробки.",
        "Ключові слова:",
        "розподілені системи, якість обслуговування (QoS), пріоритезація транзакцій, дерева рішень, Tree-to-Code, Apache Kafka, gRPC."
    )

    # Abstract ENG
    add_abstract_block(
        "Abstract.",
        "The paper addresses the challenge of tail latency (P99) mitigation and queue blockage prevention in distributed microservice architectures under peak workloads. A comprehensive adaptive QoS prioritization method is proposed, coupling real-time telemetry monitoring (CPU, memory, Kafka lag derivative, and HikariCP connection pool saturation) with a distilled CART decision tree compiled into native conditional branches (Tree-to-Code). Simulation benchmarks scaling up to 100,000 transactions demonstrate a 95.2% reduction in P99 tail latency (from 912.4 ms in FIFO baseline to 44.1 ms in Adaptive ML), maintaining the critical queue ratio at a sustainable 8.76% to prevent worker thread saturation.",
        "Keywords:",
        "distributed systems, Quality of Service (QoS), transaction prioritization, decision trees, Tree-to-Code, Apache Kafka, gRPC."
    )

    # Introduction
    add_body_p(
        "Сучасні транзакційні системи електронної комерції, платіжні шлюзи та компоненти диспетчеризації Smart Grid функціонують в умовах високодинамічного стохастичного навантаження. За виникнення пікових сплесків трафіку традиційні дисципліни обслуговування черг FIFO (First-In, First-Out) призводять до виникнення блокування початку черги (Head-of-Line Blocking) [1]. Недиференційована обробка потоку викликає лавиноподібне зростання хвостової затримки (P99 latency) [4] та деградацію ключових бізнес-процесів через взаємне блокування ресурсів реляційних СКБД. Статичні правила маршрутизації є неефективними за умов асиметричного насичення інфраструктури. Це зумовлює актуальність розроблення методів адаптивної пріоритезації, здатних коригувати правила диспетчеризації відповідно до поточного стану обчислювальних вузлів за жорстких часових обмежень (deadline < 1 мс).",
        bold_prefix="Вступ."
    )

    # Mathematical Model
    add_body_p(
        "Запропонований метод адаптивного управління якістю обслуговування (Adaptive QoS) базується на динамічному співвіднесенні вхідного вектора параметрів транзакції та поточного вектора стану інфраструктури:",
        bold_prefix="Методологія та математична модель."
    )
    add_formula(
        "x_i = (amount, type_code, retry_count, worker_cpu, consumer_lag, lag_growth_rate, db_pool_active, recent_p99_latency)",
        "1"
    )
    add_body_p(
        "де amount — нормалізований обсяг операції; type_code — порядковий код типу операції (0 — HEALTH_CHECK, 1 — ADMIN_ACTION, 2 — BALANCE_UPDATE, 3 — REFUND, 4 — PAYMENT); retry_count — лічильник повторних спроб обробки (механізм запобігання голодуванню черг); worker_cpu — утилізація процесора вузлів-обробників; consumer_lag — сумарне відставання груп споживачів брокера [3]; lag_growth_rate = ΔLag / Δt — дискретна похідна глибини черги; db_pool_active — коефіцієнт активних підключень пулу HikariCP; recent_p99_latency — хвостова затримка за ковзне вікно спостереження [4]."
    )
    add_body_p(
        "Для врахування загального насичення вузлів обчислюється інтегральний індекс навантаження системи:"
    )
    add_formula(
        "L_sys(t) = (CPU(t) + MEM(t)) / 200.0,    L_sys(t) ∈ [0, 1]",
        "2"
    )
    add_body_p(
        "Показник пам'яті MEM(t) використовується у формулі (2) як запобіжник від вичерпання heap-пам'яті JVM під час сплесків. Залежно від величини L_sys(t) здійснюється динамічна адаптація порогів допуску θ(t) для ієрархічних класів пріоритетності (CRITICAL, HIGH, STANDARD, LOW):"
    )
    add_formula(
        "θ(t) = θ_base + α · L_sys(t)",
        "3"
    )
    add_body_p(
        "де θ_base — базовий норматив допуску класу, α = 0,3 — коефіцієнт чутливості до перевантаження. Зростання L_sys(t) підвищує поріг допуску до вищих класів, забезпечуючи розвантаження критичних каналів (load shedding). Значення θ(t) передається до сервісу інференсу як параметр системного стану та використовується для коригування ієрархічних порогів класифікації."
    )
    add_body_p(
        "Навчання сурогатної моделі класифікації CART [5] здійснювалося на вибірці з 15 000 транзакцій, сформованій за статистичним профілем фінтех-трафіку PaySim. З метою усунення накладних витрат рантайм-бібліотек машинного навчання модель глибиною ≤ 5 рівнів скомпільована у прямі інструкції розгалуження мови програмування (підхід Tree-to-Code), що забезпечило F1-score на рівні 0,94."
    )

    # Architectural Implementation
    add_body_p(
        "Розроблена система побудована за принципами сервіс-орієнтованої архітектури [2] та включає такі рівні (Рис. 1):",
        bold_prefix="Архітектурна реалізація."
    )

    # Layer list
    layers = [
        "1. Client Layer: панель моніторингу та управління навантаженням (Admin Dashboard & Traffic Generator) на базі Angular 21, що генерує синтетичні транзакційні пакети за протоколом HTTP REST.",
        "2. Backend Microservices Tier: вхідний шлюз API Gateway (Java 21 LTS / Spring Boot 3), який формує вектор ознак (1) і передає його до сервісу інференсу Inference Engine (Python 3.12) через бінарний RPC-протокол gRPC. Сервіс Core Processor здійснює фінальну персистентну обробку транзакцій у БД PostgreSQL 17.",
        "3. Data & Infrastructure Tier: брокер повідомлень Apache Kafka з 4 ізольованими QoS-топіками (tx.priority.critical, high, standard, low) [3], розподілений кеш телеметрії Redis Cache та реляційна база PostgreSQL 17.",
        "4. Observability Tier: засоби моніторингу на основі Prometheus, Grafana та Kafka UI."
    ]
    for layer_text in layers:
        p_l = doc.add_paragraph()
        p_l.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_l.paragraph_format.first_line_indent = Mm(10)
        p_l.paragraph_format.space_after = Pt(2)
        p_l.paragraph_format.line_spacing = 1.15
        p_l.add_run(layer_text)

    # FIGURE 1: Architecture
    add_figure(IMG_ARCH_PATH, "Рисунок 1 — Багаторівнева архітектура мікросервісної системи адаптивної пріоритезації транзакцій", width_inches=6.2)

    add_body_p(
        "Сервіс Core Processor реалізує диференційовану конкурентність споживачів (Tiered Concurrency): топік critical обслуговується 4 паралельними воркерами (40 % пулу потоків), high — 3 (30 %), standard — 2 (20 %), low — 1 воркером (10 %). Власна тривалість операції визначається її типом (від 5 мс для HEALTH_CHECK до 200 мс для ADMIN_ACTION), тоді як черга пріоритету мінімізує час очікування. При перевищенні ліміту виконання інференсу 1 мс передбачено автоматичне перемикання на евристичний класифікатор (rule-based fallback)."
    )

    # TABLE 1
    p_tbl_cap = doc.add_paragraph()
    p_tbl_cap.paragraph_format.space_before = Pt(6)
    p_tbl_cap.paragraph_format.space_after = Pt(3)
    p_tbl_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_tc = p_tbl_cap.add_run("Таблиця 1 — Порівняльний аналіз розподілу транзакцій між пріоритетними чергами (n = 5 000 транзакцій, профіль: MIXED)")
    r_tc.font.bold = True
    r_tc.font.size = Pt(10.5)

    table_data = [
        ["Параметр порівняння", "FIFO Baseline", "Static Rules", "Adaptive ML (Запропонований)"],
        ["Розподіл CRITICAL", "0 (0,0 %)", "2 738 (54,76 %)", "438 (8,76 %)"],
        ["Розподіл HIGH", "0 (0,0 %)", "0 (0,0 %)", "1 352 (27,04 %)"],
        ["Розподіл STANDARD", "5 000 (100,0 %)", "0 (0,0 %)", "2 397 (47,94 %)"],
        ["Розподіл LOW", "0 (0,0 %)", "2 262 (45,24 %)", "813 (16,26 %)"],
        ["Зворотний зв'язок за залізом", "Відсутній (Blind)", "Відсутній (Blind)", "Активний (CPU, lag, HikariCP)"],
        ["Захист від голодування", "Природний FIFO", "Відсутній (деградація LOW)", "Активний (старіння через retry)"]
    ]

    col_widths = [Inches(2.5), Inches(1.2), Inches(1.3), Inches(1.6)]
    table = doc.add_table(rows=len(table_data), cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="CBD5E1", sz="4")

    for row_idx, row in enumerate(table_data):
        for col_idx, cell_value in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.width = col_widths[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

            p_cell = cell.paragraphs[0]
            p_cell.paragraph_format.space_before = Pt(0)
            p_cell.paragraph_format.space_after = Pt(0)
            p_cell.paragraph_format.line_spacing = 1.05

            run_cell = p_cell.add_run(cell_value)
            run_cell.font.name = 'Times New Roman'

            if row_idx == 0:
                set_cell_shading(cell, "F1F5F9")
                p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_cell.font.bold = True
                run_cell.font.size = Pt(10)
            else:
                run_cell.font.size = Pt(9.5)
                if col_idx == 0:
                    p_cell.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    run_cell.font.bold = True
                else:
                    p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    if col_idx == 3 and "Активний" in cell_value:
                        run_cell.font.bold = True

    add_body_p(
        "Як свідчать дані Таблиці 1, запропонований метод утримує частку черги CRITICAL на рівні 8,76 % (лише високобюджетні операції та транзакції після повторних спроб), тоді як статичні правила направляють у вищий пріоритет усі платежі незалежно від суми (54,76 %), перевантажуючи систему. Повний розподіл типів операцій за класами наведено у матриці: операції HEALTH_CHECK (502 од.) та ADMIN_ACTION (258 од.) спрямовано у чергу LOW; BALANCE_UPDATE (760 од.) розподілено переважно у STANDARD (83,9 %); платежі PAYMENT (2 738 од.) диференційовано на CRITICAL (14,9 %), HIGH (26,1 %) та STANDARD (59,0 %) залежно від суми та навантаження."
    )

    # Experimental Results
    add_body_p(
        "Оцінювання швидкодії механізму інференсу показало, що чистий час обчислення скомпільованого дерева (Tree-to-Code) у пам'яті складає 0,301 мкс (проти 8 500 мкс у Scikit-Learn predict() через оверхед верифікації numpy-масивів та 2 200 мкс у TensorFlow Lite). Повний час міжсервісного циклу (шлюз → gRPC → класифікація → повернення) становить 1,8–2,5 мс, що вкладається в допустимий бюджет обробки.",
        bold_prefix="Результати досліджень."
    )
    add_body_p(
        "При імітаційному моделюванні навантаження в діапазоні від 1 000 до 100 000 транзакцій черга FIFO продемонструвала деградацію затримки P99 з 38,5 мс до 912,4 мс внаслідок блокування черги важкими операціями [1, 4]. Статичний розподіл порушує поріг SLA (100 мс) за навантаження понад 20 000 транзакцій, сягаючи 231,0 мс на 100k."
    )

    # FIGURE 2: P99 Tail Latency Scaling
    add_figure(IMG_P99_PATH, "Рисунок 2 — Хвостова затримка P99 під час пікового сплеску навантаження (1 000 – 100 000 транзакцій)", width_inches=6.0)

    add_body_p(
        "Запропонований адаптивний метод утримує зростання затримки P99 у межах від 18,2 мс (при 1k) до 44,1 мс (при 100k), що на 95,2 % нижче за показник FIFO при максимальному масштабі. Ефективна швидкість спустошення буферів Kafka зростає у 2,4 рази (32,2 с проти 78,1 с), забезпечуючи розрахункову пропускну здатність до 3 105 RPS проти 1 280 RPS у базовій лінії."
    )

    # Conclusions
    add_body_p(
        "Запропонований метод адаптивної пріоритезації на основі скомпільованих дерев рішень та динамічного зворотного зв'язку за інфраструктурною телеметрією дозволяє утримувати хвостову затримку P99 у межах 44,1 мс за умов екстремальних сплесків трафіку. Обмеженням методу є потреба в адаптації базових порогів θ_base під специфіку конкретних транзакційних профілів. Напрямом подальших досліджень є реалізація механізму донавчання моделі у режимі реального часу (online learning) без перезапуску сервісу інференсу.",
        bold_prefix="Висновки."
    )

    # References Header
    p_ref_h = doc.add_paragraph()
    p_ref_h.paragraph_format.space_before = Pt(8)
    p_ref_h.paragraph_format.space_after = Pt(4)
    r_rh = p_ref_h.add_run("Список використаних джерел:")
    r_rh.font.bold = True
    r_rh.font.size = Pt(11)

    references = [
        "1. Kleppmann M. Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems. Sebastopol : O'Reilly Media, 2017. 616 p.",
        "2. Newman S. Building Microservices: Designing Fine-Grained Systems. 2nd ed. Sebastopol : O'Reilly Media, 2021. 612 p.",
        "3. Apache Kafka Documentation. Kafka 3.x : The Apache Software Foundation, 2024. URL: https://kafka.apache.org/documentation (дата звернення: 01.10.2026).",
        "4. Dean J., Barroso L. A. The Tail at Scale. Communications of the ACM. 2013. Vol. 56, No. 2. P. 74–80. DOI: 10.1145/2408776.2408794.",
        "5. Breiman L., Friedman J., Olshen R., Stone C. Classification and Regression Trees. New York : Routledge, 1984. 368 p."
    ]

    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.first_line_indent = Mm(10)
        p_ref.paragraph_format.space_after = Pt(2)
        p_ref.paragraph_format.line_spacing = 1.05
        r_ref = p_ref.add_run(ref)
        r_ref.font.size = Pt(10.5)

    os.makedirs(os.path.dirname(OUTPUT_DOCX_PATH), exist_ok=True)
    doc.save(OUTPUT_DOCX_PATH)
    print(f"\n✓ Publication-ready Word document created successfully: {OUTPUT_DOCX_PATH}")


if __name__ == '__main__':
    build_document()
