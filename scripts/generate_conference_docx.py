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
        "У статті розв'язано проблему деградації показників якості обслуговування (QoS) та виникнення ефекту блокування початку черги (Head-of-Line Blocking) у розподілених сервісах обробки транзакцій під час сплесків трафіку. Запропоновано метод динамічної пріоритезації на базі 8-вимірного вектора телеметрії інфраструктури, динамічного адаптивного порогу відсікання та трансляції навчених дерев рішень CART у нативний імперативний код (Tree-to-Code Compilation). Експериментальні дослідження підтвердили скорочення хвостової затримки P99 для критичних транзакцій на 95,2 % (до 44,1 мс при навантаженні 100 000 операцій), збільшення пропускної здатності на 142 % (до 3 100 RPS) та прискорення інференсу класифікатора до 0,301 мкс при ліквідації каскадних збоїв інфраструктури.",
        "Ключові слова:",
        "розподілені системи, черги повідомлень, Apache Kafka, якість обслуговування (QoS), Tree-to-Code, дерево рішень, P99 latency, хвостова затримка."
    )

    # Abstract ENG
    add_abstract_block(
        "Abstract.",
        "The paper addresses the problem of Quality of Service (QoS) degradation and the Head-of-Line Blocking phenomenon in distributed message queuing systems during transactional traffic spikes. A dynamic prioritization method is proposed based on an 8-dimensional infrastructure telemetry feature vector, adaptive saturation thresholds, and CART decision tree translation into imperative native conditional logic (Tree-to-Code Compilation). Empirical benchmarks confirm a 95.2% reduction in P99 tail latency for critical operations (down to 44.1 ms at 100k throughput), a 142% throughput increase (up to 3,100 RPS), and sub-microsecond classification latency (0.301 μs) preventing cascading infrastructure failures.",
        "Keywords:",
        "distributed systems, message queues, Apache Kafka, Quality of Service, QoS, Tree-to-Code, decision trees, P99 latency, tail latency."
    )

    # Introduction
    add_body_p(
        "Сучасні високонавантажені розподілені інформаційні платформи (платіжні шлюзи, процесингові центри, компоненти диспетчеризації Smart Grid) функціонують в умовах інтенсивного стохастичного вхідного трафіку [1, 2]. Раптові сплески навантаження призводять до деградації пропускної здатності, переповнення буферів брокерів повідомлень (зокрема Apache Kafka [3]), вичерпання пулу з'єднань із базами даних (HikariCP) та стрімкого зростання затримок хвоста розподілу (P95/P99), що порушує цільові нормативи угод про рівень обслуговування (SLA) [4].",
        bold_prefix="Вступ."
    )
    add_body_p(
        "Використання базових дисциплін диспетчеризації на основі черг FIFO (First-In, First-Out) спричиняє ефект блокування початку черги (Head-of-Line Blocking), за якого критичні бізнес-операції вимушені простоювати за важкими фоновими завданнями [1]. Статичні правила вибору пріоритетів не володіють зворотним зв'язком щодо поточної утилізації апаратних вузлів, що у фазі пікового навантаження викликає каскадні збої. Водночас виклик повнорозмірних бібліотек машинного навчання безпосередньо на критичному шляху обробки (hot path) створює неприпустимий оверхед (від 2,2 до 8,5 мс на операцію, виміряно на 100 000 ітераціях). Отже, побудова методу динамічної адаптивної пріоритезації з субмілісекундною реакцією є актуальним науково-технічним завданням."
    )
    add_body_p(
        "підвищення якості обслуговування (QoS) розподілених систем шляхом мінімізації хвостової затримки P99 для критично важливих транзакцій в умовах пікових сплесків навантаження за рахунок використання багатофакторної телеметрії та оптимізованого інференсу.",
        bold_prefix="Мета дослідження:"
    )

    # Mathematical Model
    add_body_p(
        "Для забезпечення повної контекстної обізнаності кожна транзакція T_i на етапі проходження через вхідний шлюз агрегується з поточними метриками системи і формалізується у вигляді 8-вимірного вектора ознак:",
        bold_prefix="Математична модель та запропонований метод."
    )
    add_formula(
        "x_i = (amount, type_code, retry_count, worker_cpu, consumer_lag, lag_growth_rate, db_pool_active, recent_p99_latency)",
        "1"
    )
    add_body_p(
        "де amount — фінансова вага операції; type_code — ординальне кодування типу операції за рівнем бізнес-критичності (HEALTH_CHECK=0, ADMIN_ACTION=1, BALANCE_UPDATE=2, REFUND=3, PAYMENT=4); retry_count — лічильник повторних спроб виконання для захисту від голодування черг (anti-starvation); worker_cpu — утилізація CPU пулу обробників; consumer_lag та lag_growth_rate — поточна черга брокера та динаміка її наростання [3]; db_pool_active — коефіцієнт насичення пулу з'єднань із базою даних HikariCP; recent_p99_latency — ковзне вікно затримки обробки за останні 60 секунд [4]."
    )
    add_body_p(
        "Для динамічного коректування порогу допуску транзакцій розраховується інтегральний коефіцієнт навантаження апаратної інфраструктури:"
    )
    add_formula(
        "L_sys(t) = (CPU(t) + MEM(t)) / 200.0,    L_sys(t) ∈ [0, 1]",
        "2"
    )
    add_body_p(
        "Динамічний поріг класифікації чутливості визначається за виразом:"
    )
    add_formula(
        "θ(t) = 0.5 + 0.3 · L_sys(t)",
        "3"
    )
    add_body_p(
        "У нормальному стані інфраструктури (L_sys → 0) поріг дорівнює 0,5. Під час пікового перевантаження (L_sys → 1,0) значення θ(t) збільшується до 0,8, внаслідок чого некритичний фоновий трафік автоматично песимізується до черги низького пріоритету (LOW), вивільняючи обчислювальні ресурси під життєво важливі операції (load shedding). Значення θ(t) передається до сервісу інференсу як параметр системного стану та використовується для коригування ієрархічних порогів класифікації трьох рівнів пріоритетності (CRITICAL, HIGH, STANDARD) відповідно до поточного ступеня насичення інфраструктури."
    )
    add_body_p(
        "Для подолання затримок серіалізації даних і важкого ML-рантайму навчене дерево рішень CART [5] транслюється у нативний машинний код умовних розгалужень (Tree-to-Code Compilation). Отримане бінарне дерево фіксованої глибини (≤ 5) оптимізує граф переходів, ліквідуючи оверхед виклику сторонніх аналітичних пакетів."
    )

    # Architectural Implementation
    add_body_p(
        "Створена мікросервісна система [2] побудована за багаторівневою модульною топологією (Рис. 1):",
        bold_prefix="Архітектурна реалізація."
    )

    # Layer list
    layers = [
        "1. Client Layer: включає генератор навантаження (Load Generator) для імітації стохастичних сплесків трафіку та панель адміністрування на базі фреймворку Angular 21 (Admin Dashboard).",
        "2. Backend Microservices Tier: точка входу API Gateway (Java 21 LTS / Spring Boot 3), сервіс субмілісекундного інференсу (Inference Engine) з підтримкою протоколу gRPC, та сервіс обробки транзакцій Core Processor. Вибір поліглотної архітектури (Java 21 LTS для API-шлюзу, Python 3.12 для сервісу інференсу) зумовлений перевагами відповідних екосистем: Java/Spring Boot — для реактивної HTTP/Kafka-взаємодії, Python — для ML-бібліотек (Scikit-Learn, NumPy). Протокол gRPC/Protobuf забезпечує ефективну міжмовну комунікацію зі зниженням розміру пакетів на ~70 % порівняно з JSON/REST.",
        "3. Data & Infrastructure Tier: брокер повідомлень Apache Kafka з 4 ізольованими QoS-топіками (critical, high, standard, low) [3], оперативне сховище стану системи Redis Cache та реляційна база даних PostgreSQL 17.",
        "4. Observability Tier: комплекс моніторингу на основі Prometheus, Grafana Dashboards та Kafka UI для збору апаратної телеметрії у реальному часі."
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
        "Сервіс Core Processor реалізує принцип диференційованої конкурентності споживачів (Tiered Concurrency): черга critical обробляється 4 паралельними воркерами (40 % ресурсів процесора), high — 3 (30 %), standard — 2 (20 %), low — 1 воркером (10 %). Для забезпечення детермінованого SLA реалізовано дворівневий механізм класифікації: у разі перевищення ML-інференсом часового бюджету 1 мс система автоматично перемикається на евристичний класифікатор на основі зважених правил (rule-based fallback), гарантуючи безперервність обробки транзакцій."
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
        ["Розподіл CRITICAL", "0 (0 %)", "990 (20 %)", "2 023 (40 %)"],
        ["Розподіл HIGH", "0 (0 %)", "0 (0 %)", "996 (20 %)"],
        ["Розподіл STANDARD", "5 000 (100 %)", "0 (0 %)", "1 006 (20 %)"],
        ["Розподіл LOW", "0 (0 %)", "4 010 (80 %)", "975 (20 %)"],
        ["Зворотний зв'язок за залізом", "Відсутній (Blind)", "Відсутній (Blind)", "Активний (CPU, Lag, HikariCP)"],
        ["Захист від голодування", "Природний FIFO", "Відсутній (голодування LOW)", "Активний (Retry Count Aging)"]
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

    # Experimental Results
    add_body_p(
        "Експериментальні дослідження охоплювали оцінку швидкодії механізму інференсу та поведінку комплексу під екстремальними навантаженнями.",
        bold_prefix="Результати досліджень."
    )
    add_body_p(
        "Результати мікро-бенчмаркінгу на 100 000 ітераціях підтвердили високу ефективність методу Tree-to-Code [5]: час прийняття рішення склав лише 0,301 мкс, що у 28 000 разів перевищує продуктивність стандартного методу Scikit-Learn predict() (8 500 мкс) та у 7 300 разів — TensorFlow Lite (2 200 мкс)."
    )
    add_body_p(
        "При моделюванні пікового навантаження (пакети від 1 000 до 100 000 транзакцій) базова черга FIFO продемонструвала критичне зростання затримки P99 до 912 мс через Head-of-Line Blocking [1, 4]. Статична маршрутизація вичерпує пул з'єднань БД і порушує цільовий норматив SLA (100 мс) вже при 20 000 операцій (сягаючи 230 мс на 100k)."
    )

    # FIGURE 2: P99 Tail Latency Scaling
    add_figure(IMG_P99_PATH, "Рисунок 2 — Хвостова затримка P99 під час пікового сплеску навантаження (1 000 – 100 000 транзакцій)", width_inches=6.0)

    add_body_p(
        "Запропонований метод Adaptive ML QoS утримує стабільну хвостову затримку на рівні 44,1 мс на всьому інтервалі випробувань (скорочення P99 latency на 95,2 % порівняно з базовою лінією). Водночас ефективна пропускна здатність комплексу зростає на 142 % (досягаючи 3 100 RPS проти 1 280 RPS у FIFO), а повне розвантаження черги брокера відбувається у 2,4 рази швидше (32,2 с проти 78,1 с). Локальний мережевий оверхед виклику gRPC на шлюзі (2,5 мс після прогріву TCP/HTTP2-з'єднання) повністю нівелюється відсутністю тривалого простою транзакцій у чергах брокера [3]."
    )

    # Conclusions
    add_body_p(
        "Розроблений метод динамічної пріоритезації транзакцій усуває блокування черг у високонавантажених брокерах повідомлень. Використання адаптивного індексу насичення системи L_sys(t), ієрархічних динамічних порогів та оптимізованого механізму Tree-to-Code гарантує виконання нормативів SLA для критичних бізнес-операцій (P99 < 50 мс) без ризику виникнення каскадних відмов компонентів інфраструктури. Отримані результати підтверджують ефективність застосування запропонованого підходу в компонентах диспетчеризації Smart Grid та платіжних платформах. Перспективами подальших досліджень є дослідження адаптивного навчання класифікатора в режимі реального часу (online learning) на основі зворотного зв'язку з реальних показників SLA системи.",
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
