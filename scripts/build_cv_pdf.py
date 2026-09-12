"""Build the downloadable CV from the existing HTML, using its visible headline, selected projects and experience text.

Requires reportlab. Run from any directory; optional --root selects the checkout.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import urljoin

from cv_content import load_cv_content

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether


def plain(fragment):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def section(source, section_id):
    match = re.search(r'<section[^>]+aria-labelledby="'+section_id+r'"[^>]*>(.*?)</section>', source, re.S)
    if not match:
        raise ValueError('Missing CV section: '+section_id)
    return match.group(1)


def build(root):
    source=(root/'index.html').read_text()
    content=load_cv_content(root)
    pine=colors.HexColor('#203e36')
    muted=colors.HexColor('#525952')
    styles={
        'name':ParagraphStyle('name',fontName='Times-Bold',fontSize=26,leading=28,textColor=pine,spaceAfter=4),
        'role':ParagraphStyle('role',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=pine,spaceAfter=5),
        'body':ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=11.5,textColor=colors.HexColor('#222b27'),spaceAfter=4),
        'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8,leading=10,textColor=muted,spaceAfter=4),
        'heading':ParagraphStyle('heading',fontName='Helvetica-Bold',fontSize=10,leading=12,textColor=pine,spaceBefore=8,spaceAfter=5,keepWithNext=True),
    }
    story=[]
    def add(text,style='body'):
        story.append(Paragraph(text,styles[style]))
    add('Alex Bethune','name')
    add(html.escape(content['role']),'role')
    add('Melbourne, Australia · <link href="mailto:abethuneplou@gmail.com">abethuneplou@gmail.com</link> · <link href="https://github.com/Likio3000">github.com/Likio3000</link>','small')
    add('<link href="https://likio3000.github.io/CV/portfolio.html">Portfolio: likio3000.github.io/CV/portfolio.html</link>','small')
    add(html.escape(content['summary']))
    add('SELECTED DATA PROJECTS','heading')
    for project in content['projects']:
        title=html.escape(project['title'])
        stack=html.escape(project['stack'])
        description=html.escape(project['description'])
        link=html.escape(urljoin('https://likio3000.github.io/CV/',project['href']),quote=True)
        story.append(KeepTogether([
            Paragraph('<b><link href="'+link+'">'+title+'</link></b> <font color="#525952">| '+stack+'</font>',styles['body']),
            Paragraph(description,styles['body'])]))
    add('EXPERIENCE','heading')
    # Copy all employment entries verbatim in their existing order. No new claims.
    for block in re.findall(r'<div>(.*?)</div>',section(source,'experience-title'),re.S):
        role=re.search(r'<dt>(.*?)</dt>',block,re.S)
        dates=re.search(r'<dd>(.*?)</dd>',block,re.S)
        if role and dates:
            add('<b>'+html.escape(plain(role.group(1)))+'</b> · '+html.escape(plain(dates.group(1))))
            for detail in re.findall(r'<dd class="experience-detail">(.*?)</dd>',block,re.S):
                add(html.escape(plain(detail)))
    add('TECHNICAL TOOLBOX','heading')
    toolbox=section(source,'toolbox-title')
    for block in re.findall(r'<div>(.*?)</div>',toolbox,re.S):
        label=re.search(r'<dt>(.*?)</dt>',block,re.S)
        values=re.search(r'<dd>(.*?)</dd>',block,re.S)
        if label and values:
            add('<b>'+html.escape(plain(label.group(1)))+':</b> '+html.escape(plain(values.group(1))))
    add('EDUCATION &amp; LANGUAGES','heading')
    for block in re.findall(r'<div>(.*?)</div>',section(source,'education-title'),re.S):
        title=re.search(r'<dt>(.*?)</dt>',block,re.S)
        dates=re.search(r'<dd>(.*?)</dd>',block,re.S)
        if title and dates:add('<b>'+html.escape(plain(title.group(1)))+'</b> · '+html.escape(plain(dates.group(1))))
    add('English, Spanish &amp; Catalan · Native proficiency')
    add('ADDITIONAL TRAINING','heading')
    for item in re.findall(r'<li>(.*?)</li>',section(source,'certifications-title'),re.S):add(html.escape(plain(item)),'small')
    target=root/'Alex-Bethune-CV.pdf'
    doc=SimpleDocTemplate(str(target),pagesize=(210*mm,297*mm),rightMargin=17*mm,leftMargin=17*mm,topMargin=13*mm,bottomMargin=12*mm,title='Alex Bethune - CV',author='Alex Bethune')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#b8c3b9'));canvas.line(17*mm,10*mm,193*mm,10*mm)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();build(args.root)
