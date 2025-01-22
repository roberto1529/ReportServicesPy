from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

def generar_pdf_complejo(pdf_file):
    # Crear documento
    doc = SimpleDocTemplate(pdf_file, pagesize=letter)
    
    # Definir datos para la tabla
    data = [
        ['Nombre', 'Edad', 'Ciudad'],
        ['Juan', 28, 'Madrid'],
        ['Ana', 34, 'Barcelona'],
        ['Luis', 25, 'Valencia']
    ]
    
    # Crear una tabla
    table = Table(data)
    
    # Crear estilo para la tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Color de fondo de la primera fila (cabecera)
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Color de texto de la primera fila
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alineación central
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente en la primera fila
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Definir las líneas de la cuadrícula
    ])
    
    table.setStyle(style)
    
    # Añadir la tabla al documento
    doc.build([table])

# Llamar a la función para generar el PDF con la tabla
generar_pdf_complejo('./outputs/documento_con_tabla.pdf')
