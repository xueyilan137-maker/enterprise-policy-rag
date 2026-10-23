"""Generate an original text PDF test document from this project's synthetic Markdown."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]


def make_pdf(path,text):
    font=Path('C:/Windows/Fonts/simhei.ttf')
    if font.exists():
        pdfmetrics.registerFont(TTFont('ExampleChinese',str(font)))
        face='ExampleChinese'
    else:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        face='STSong-Light'
    output=canvas.Canvas(path if hasattr(path,'write') else str(path))
    output.setFont(face,12)
    for i,line in enumerate(text.splitlines()):output.drawString(60,790-i*28,line.removeprefix('# '))
    output.save()


if __name__=='__main__':
    target=ROOT/'.local/evidence/trip-note-001.pdf'
    make_pdf(target,(ROOT/'data/examples/trip-note-001.md').read_text(encoding='utf-8'))
    print('Generated private synthetic text PDF',target)
