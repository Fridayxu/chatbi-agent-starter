# -*- coding: utf-8 -*-
"""
Reusable CJK PDF generation utilities.

Key insight: fpdf2's multi_cell() uses Western word-breaking (breaks at spaces).
For CJK text mixed with ASCII, this causes premature line breaks at ASCII-CJK boundaries.
Solution: Use cell() with character-by-character width measurement — this breaks at
the CHARACTER level, not the WORD level, producing uniform CJK line lengths.

Usage:
    from cjk_pdf_utils import CJKReport
    pdf = CJKReport()
    pdf.add_page()
    pdf.title1('Chapter Title')
    pdf.para('Long paragraph with mixed ASCII and CJK text...')
    pdf.data_table(headers, rows, col_widths)
    pdf.output('output.pdf')
"""
from fpdf import FPDF

class CJKReport(FPDF):
    """FPDF subclass with proper CJK text handling."""

    def __init__(self, font_path=None, font_bold_path=None):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(True, 14)
        self.set_left_margin(10)
        self.set_right_margin(10)

        # Default fonts
        if font_path is None:
            font_path = r'C:\Windows\Fonts\msyh.ttc'
        if font_bold_path is None:
            font_bold_path = r'C:\Windows\Fonts\msyhbd.ttc'

        self.add_font('CJK', '', font_path)
        self.add_font('CJK', 'B', font_bold_path)
        self.add_font('HF', '', font_path)   # header/footer font
        self.add_font('HF', 'B', font_bold_path)

    # ---- Page decorators ----
    def header(self):
        if self.page_no() > 1:
            self.set_font('HF', '', 6.5)
            self.set_text_color(160, 160, 160)
            self.cell(0, 4, '', align='C')  # Override in subclass for custom header
            self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_font('HF', '', 6.5)
        self.set_text_color(160, 160, 160)
        self.cell(0, 8, f'{self.page_no()}/{{nb}}', align='C')

    # ---- Typography ----
    def title1(self, txt):
        """Chapter title: bold 13pt, dark blue."""
        self.set_font('CJK', 'B', 13)
        self.set_text_color(47, 84, 150)
        self.cell(0, 7, txt)
        self.ln(10)

    def title2(self, txt):
        """Section title: bold 9.5pt, dark gray."""
        self.set_font('CJK', 'B', 9.5)
        self.set_text_color(60, 60, 60)
        self.cell(0, 5.5, txt)
        self.ln(8)

    def note(self, txt):
        """Small annotation: 7pt, gray, centered."""
        self.set_font('CJK', '', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4.5, txt, align='C')
        self.ln(5)

    def para(self, txt):
        """
        Body paragraph with PROPER CJK line breaking.

        Uses cell() with character-by-character width measurement.
        This is the KEY FIX: unlike multi_cell() which breaks at word boundaries
        (spaces), this approach breaks at the CHARACTER level, ensuring uniform
        line lengths for mixed CJK/ASCII text.
        """
        self.set_font('CJK', '', 7.5)
        self.set_text_color(50, 50, 50)
        max_w = self.w - self.l_margin - self.r_margin
        for paragraph in txt.split('\n'):
            if not paragraph:
                self.ln(4.8)
                continue
            line = ''
            for ch in paragraph:
                test = line + ch
                if self.get_string_width(test) > max_w and line:
                    self.cell(0, 4.8, line, new_x='LMARGIN', new_y='NEXT')
                    line = ch
                else:
                    line = ch if not line else line + ch
            if line:
                self.cell(0, 4.8, line, new_x='LMARGIN', new_y='NEXT')
        self.ln(1.2)

    # ---- Tables ----
    def data_table(self, headers, rows, col_widths):
        """
        Professional data table with dark blue header and zebra striping.
        Column widths are SCALED to fill the full page width.
        """
        w_total = self.w - self.l_margin - self.r_margin
        ratio = w_total / sum(col_widths)
        col_widths = [w * ratio for w in col_widths]

        # Header row
        self.set_fill_color(47, 84, 150)
        self.set_text_color(255, 255, 255)
        self.set_font('CJK', 'B', 6.5)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 5.5, h, border=1, fill=True, align='C')
        self.ln()

        # Data rows
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(245, 248, 252)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(50, 50, 50)
            self.set_font('CJK', '', 6.5)
            for i, v in enumerate(row):
                align = 'L' if i == 0 else 'C'
                self.cell(col_widths[i], 5.5, str(v), border=1, fill=True, align=align)
            self.ln()

    # ---- Helpers ----
    def divider(self):
        """Horizontal rule."""
        self.set_draw_color(208, 208, 208)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(4)

    def cover_title(self, title, subtitles=None):
        """Centered cover page."""
        self.ln(45)
        self.set_font('CJK', 'B', 24)
        self.set_text_color(47, 84, 150)
        self.cell(0, 14, title, align='C')
        self.ln(22)
        if subtitles:
            self.set_font('CJK', '', 9)
            self.set_text_color(100, 100, 100)
            for sub in subtitles:
                self.cell(0, 7, sub, align='C')
                self.ln(7)
