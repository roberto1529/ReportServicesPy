from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import shutil
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import asyncpg
from typing import List
from docx2pdf import convert  # Nueva importación para conversión

# Configuración de rutas
WORD_TEMPLATE_PATH = './templates/word/factura.docx'
OUTPUT_PATH = './outputs'
LOGO_PATH = './templates/img/Logo_Letras.png'

app = FastAPI()

# Modelo de datos para la petición
class Producto(BaseModel):
    descripcion: str
    cantidad: int
    costo_unitario: float
    costo_total: float

class DocumentData(BaseModel):
    cliente: str
    direc: str
    tell: str
    id: str
    fecha: str
    subtotal: float
    iva: float
    total: float
    productos: List[Producto]

# Función para limpiar reportes
def limpiar_reportes():
    if os.path.exists(OUTPUT_PATH):
        shutil.rmtree(OUTPUT_PATH)
    os.mkdir(OUTPUT_PATH)

# Función para convertir Word a PDF
def convertir_a_pdf(word_path):
    pdf_path = word_path.replace(".docx", ".pdf")
    try:
        convert(word_path, pdf_path)  # Convierte usando docx2pdf
        return pdf_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al convertir a PDF: {str(e)}")

# Función para generar el documento Word
def generate_word(data: DocumentData):
    try:
        doc = DocxTemplate(WORD_TEMPLATE_PATH)
        context = data.dict()
        context['logo'] = InlineImage(doc, LOGO_PATH, width=Mm(40))

        # Renderizar la plantilla con la tabla dinámica
        doc.render(context)

        # Guardar el documento final en Word
        word_output_path = os.path.join(OUTPUT_PATH, 'factura_generada.docx')
        doc.save(word_output_path)

        # Convertir a PDF
        pdf_output_path = convertir_a_pdf(word_output_path)

        return {"message": "Documento generado correctamente", "word_path": word_output_path, "pdf_path": pdf_output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para generar el documento Word y PDF con datos temporales
@app.get("/generate-word")
async def generate_word_endpoint():
    limpiar_reportes()
    data = DocumentData(
        cliente="Juan Pérez",
        direc="Av. Reforma 123, CDMX",
        tell="555-123-4567",
        id="COT-20240325",
        fecha="2025-03-25",
        subtotal=5000.00,
        iva=800.00,
        total=5800.00,
        productos=[
            Producto(descripcion="Cámara de seguridad IP 1080p", cantidad=2, costo_unitario=1200.00, costo_total=2400.00),
            Producto(descripcion="DVR de 4 canales", cantidad=1, costo_unitario=2000.00, costo_total=2000.00),
            Producto(descripcion="Fuente de alimentación 12V 5A", cantidad=1, costo_unitario=600.00, costo_total=600.00)
        ]
    )
    return generate_word(data)

# Conexión a PostgreSQL
async def connect_db():
    return await asyncpg.connect(DATABASE_URL)

@app.get("/test-db")
async def test_db():
    try:
        conn = await connect_db()
        await conn.close()
        return {"message": "Conexión a la base de datos exitosa"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
