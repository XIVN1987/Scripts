#! python3
from svglib import svglib
from reportlab.graphics import renderPM, renderPDF

svglib.register_font('DejaVu Sans', 'fonts/dejavu-fonts-ttf-2.37/DejaVuSans.ttf')


drawing = svglib.svg2rlg(r'C:\Users\WMX\Desktop\SCH_CH32V307_0-Core_2022-11-08.svg')
factor = 1280 / drawing.width
drawing.width *= factor
drawing.height *= factor
drawing.scale(factor, factor)
renderPM.drawToFile(drawing, "Cortex-A77.png", fmt="PNG")
