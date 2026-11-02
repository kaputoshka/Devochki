"""Общие функции для сборки отчётов (оформление как в отчёте ЛР4: Times New Roman 14, поля 3/1.5/2 см)."""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image, ImageDraw, ImageFont

FONT = "Times New Roman"
DEFAULT_AUTHORS = ("Айсин А.Х.", "Асянов Р.И.", "Вахапов А.А.")
MONO_FONTS = (r"C:\Windows\Fonts\consola.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")


def _mono_font(size: int) -> ImageFont.FreeTypeFont:
    for path in MONO_FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise OSError(f"Не найден моноширинный шрифт: {MONO_FONTS}")


def term_image(text: str, path: str, title: str = "", width_chars: int = 0, font_size: int = 17):
    """Рендерит текст вывода терминала в PNG (тёмная тема, моноширинный шрифт)."""
    font = _mono_font(font_size)
    lines = text.rstrip("\n").split("\n")
    cw = font.getbbox("M")[2]
    lh = font_size + 6
    w = (max(width_chars, max(len(l) for l in lines)) + 4) * cw
    top = 34 if title else 12
    img = Image.new("RGB", (w, top + lh * len(lines) + 14), (30, 30, 30))
    d = ImageDraw.Draw(img)
    if title:
        d.rectangle([0, 0, w, 26], fill=(60, 60, 60))
        d.text((10, 3), title, font=font, fill=(220, 220, 220))
    for i, l in enumerate(lines):
        d.text((2 * cw, top + i * lh), l, font=font, fill=(204, 204, 204))
    img.save(path)


class Report:
    def __init__(self):
        self.doc = Document()
        s = self.doc.sections[0]
        s.page_width, s.page_height = Cm(21), Cm(29.7)
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(3), Cm(1.5), Cm(2), Cm(2)
        st = self.doc.styles["Normal"]
        st.font.name, st.font.size = FONT, Pt(14)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        self.fig = 0

    def _fmt(self, p, align=None, indent=True, after=6, before=0, spacing=1.5, keep=False):
        pf = p.paragraph_format
        pf.space_after, pf.space_before, pf.line_spacing = Pt(after), Pt(before), spacing
        if indent:
            pf.first_line_indent = Cm(1.25)
        if align is not None:
            p.alignment = align
        if keep:
            pf.keep_with_next = True

    def center(self, text, bold=False, after=0, size=14):
        p = self.doc.add_paragraph()
        r = p.add_run(text); r.bold = bold; r.font.size = Pt(size)
        self._fmt(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=after, spacing=1.15)

    def right(self, text):
        p = self.doc.add_paragraph(); p.add_run(text)
        self._fmt(p, WD_ALIGN_PARAGRAPH.RIGHT, indent=False, after=0, spacing=1.15)

    def blank(self, n=1):
        for _ in range(n):
            p = self.doc.add_paragraph(); self._fmt(p, indent=False, after=0, spacing=1.15)

    def page_break(self):
        self.doc.add_page_break()

    def h(self, text):
        p = self.doc.add_paragraph()
        r = p.add_run(text); r.bold = True
        self._fmt(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False, before=10, after=6, keep=True)

    def p(self, text, bold_prefix=None):
        p = self.doc.add_paragraph()
        if bold_prefix:
            p.add_run(bold_prefix).bold = True
        p.add_run(text)
        self._fmt(p, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def item(self, text):
        p = self.doc.add_paragraph(); p.add_run(text)
        self._fmt(p, WD_ALIGN_PARAGRAPH.JUSTIFY, indent=False, after=2)
        p.paragraph_format.left_indent = Cm(1.25)

    def code(self, text, size=9):
        for line in text.rstrip("\n").split("\n"):
            p = self.doc.add_paragraph()
            r = p.add_run(line if line else " "); r.font.name = "Courier New"; r.font.size = Pt(size)
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
            self._fmt(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False, after=0, spacing=1.0)
        self.blank()

    def image(self, path, caption, width_cm=15.5):
        p = self.doc.add_paragraph(); p.add_run().add_picture(path, width=Cm(width_cm))
        self._fmt(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=2, spacing=1.0, keep=True)
        self.fig += 1
        c = self.doc.add_paragraph(); c.add_run(f"Рисунок {self.fig} — {caption}")
        self._fmt(c, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=10, spacing=1.15)

    def table(self, rows, widths=None):
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j); cell.text = ""
                run = cell.paragraphs[0].add_run(str(val)); run.font.size = Pt(12); run.bold = (i == 0)
                cell.paragraphs[0].paragraph_format.space_after = Pt(0)
                if widths:
                    cell.width = Cm(widths[j])
        self.blank()

    def title_page(self, num, subject_theme, authors=DEFAULT_AUTHORS):
        for t in ["Федеральное государственное бюджетное образовательное учреждение", "высшего образования",
                  "«Уфимский университет науки и технологий»", "Кафедра Автоматизированных систем управления"]:
            self.center(t)
        self.blank(6)
        self.center(f"Лабораторная работа №{num}", bold=True, size=16)
        self.center(f"На тему: «{subject_theme}»", after=6)
        self.center("по дисциплине: Информационно-аналитические системы")
        self.blank(6)
        p = self.doc.add_paragraph(); p.add_run("Выполнил: студент гр. ЭАС-401С")
        self._fmt(p, WD_ALIGN_PARAGRAPH.RIGHT, indent=False, after=0, spacing=1.15)
        for t in [*authors, "Проверил:", "Антонов В.В."]:
            self.right(t)
        self.blank(6)
        self.center("Уфа 2026 г.")
        self.page_break()

    def save(self, path):
        self.doc.save(path)
