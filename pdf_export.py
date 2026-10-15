# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Readable client handouts from reviewed Markdown; no client text leaves the machine."""
import io, re
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def make_pdf(title,text):
    font='Helvetica'
    for p in ['/usr/share/fonts/TTF/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(p).exists():
            if 'MMBody' not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont('MMBody',p))
            font='MMBody'; break
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MMTitle',fontName=font,fontSize=24,leading=31,textColor=HexColor('#402965'),spaceAfter=18))
    styles.add(ParagraphStyle(name='MMHeading',fontName=font,fontSize=14,leading=20,textColor=HexColor('#68429b'),spaceBefore=18,spaceAfter=8,keepWithNext=True))
    styles.add(ParagraphStyle(name='MMBody',fontName=font,fontSize=10.5,leading=16,textColor=HexColor('#26222d'),spaceAfter=8,splitLongWords=True))
    stream=io.BytesIO()
    doc=SimpleDocTemplate(stream,title=title,author='Mystical Mark',pagesize=(595.28,841.89),leftMargin=48,rightMargin=48,topMargin=58,bottomMargin=52)
    story=[Paragraph(escape(title),styles['MMTitle']),Paragraph('MYSTICAL MARK  /  READING REFERENCE',styles['MMBody']),HRFlowable(width='100%',thickness=1,color=HexColor('#cbb5e3')),Spacer(1,14)]
    for block in re.split(r'\n\s*\n',text):
        block=block.strip()
        if not block: continue
        if re.fullmatch(r'[-_*]{3,}',block): continue
        for line in block.splitlines():
            if line.startswith('#'):
                story.append(Paragraph(escape(line.lstrip('# ')),styles['MMHeading']))
            else:
                # Escape before supported Markdown emphasis; no remote assets or raw HTML.
                line=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',r'\1 (\2)',line)
                line=line.replace('**','').replace('`','')
                if line.startswith('|'):
                    if re.match(r'^\|[\s:|\-]+$',line): continue
                    line='  /  '.join(x.strip() for x in line.strip('|').split('|'))
                if line.startswith('- '): line='• '+line[2:]
                story.append(Paragraph(escape(line),styles['MMBody']))
    def page(c,doc):
        c.setStrokeColor(HexColor('#d7cce3')); c.line(48,40,547,40)
        c.setFillColor(HexColor('#786887')); c.setFont(font,8)
        c.drawString(48,27,'Mystical Mark · Private reading reference')
        c.drawRightString(547,27,str(doc.page))
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return stream.getvalue()
