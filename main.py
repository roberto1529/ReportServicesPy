from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
import shutil
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import asyncpg
from typing import List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fastapi.middleware.cors import CORSMiddleware
import subprocess

# Configuración de rutas
WORD_TEMPLATE_PATH = './templates/word/factura.docx'
OUTPUT_PATH = './outputs'
LOGO_PATH = './templates/img/Logo_Letras.png'
DATABASE_URL = "postgresql://admin:Techniza**@158.220.83.8:5432/postgres"

# Configuración de correo con Zoho Mail
SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 587
SMTP_USER = "onecore_mail@zohomail.com"
SMTP_PASSWORD = "Onecore2025**"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
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
        result = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'pdf',
            '--outdir', os.path.dirname(pdf_path), word_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"Error en LibreOffice: {result.stderr}")
        
        if not os.path.exists(pdf_path):
            raise Exception("El archivo PDF no se generó correctamente")
            
        return pdf_path
    except subprocess.TimeoutExpired:
        raise Exception("Tiempo de espera agotado para la conversión PDF")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al convertir a PDF: {str(e)}")

# Función para generar el documento Word
def generate_word(data: DocumentData, total):
    try:
        doc = DocxTemplate(WORD_TEMPLATE_PATH)
        context = data.dict()
        context['logo'] = InlineImage(doc, LOGO_PATH, width=Mm(70))
        context['total'] = total
        doc.render(context)
        word_output_path = os.path.join(OUTPUT_PATH, 'factura_generada.docx')
        doc.save(word_output_path)

        pdf_output_path = convertir_a_pdf(word_output_path)
        return pdf_output_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Función para conectar a PostgreSQL
async def connect_db():
    return await asyncpg.connect(DATABASE_URL)

# Función para obtener datos de la factura
async def datos_fact(id: int):
    try:
        conn = await connect_db()

        query1 = """
            SELECT LPAD(fm.id::text, 5, '0') AS id, fc.subtotal, fc.iva, fc.total, uc.nombre AS cliente, uc.correo, 
                TO_CHAR((CURRENT_DATE + fm.fecha_reg)::timestamp, 'YYYY-MM-DD HH24:MI:SS') AS fecha_fact
            FROM fact_maestro fm 
            JOIN fact_venta_costo fc ON fc.id_factura = fm.id 
            JOIN usu_cliente uc ON uc.id = fm.id_cliente
            WHERE fm.id = $1
        """

        query2 = """
            SELECT fi.id_factura, p.descripcion, fi.cantidad, 
                   CAST(p.venta AS NUMERIC) AS costo_unitario, 
                   (CAST(p.venta AS NUMERIC) * fi.cantidad) AS costo_total
            FROM fact_venta_item fi
            JOIN producto p ON p.id = fi.id_producto
            WHERE fi.id_factura = $1
        """

        result1 = await conn.fetchrow(query1, id)
        result2 = await conn.fetch(query2, id)
        await conn.close()

        if not result1:
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        return {
            "factura": dict(result1.items()),
            "detalles": [dict(row.items()) for row in result2]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Función para enviar correo con PDF adjunto
def enviar_correo(destinatario, archivo_adjunto):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = destinatario
        msg['Subject'] = "Factura - Techniza"

        mensaje = "Hola, te hacemos envío de tu factura - Techniza."
        msg.attach(MIMEText(mensaje, 'plain'))

        with open(archivo_adjunto, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(archivo_adjunto)}")
            msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, destinatario, msg.as_string())
        server.quit()

        return {"message": f"Correo enviado a {destinatario}"}
    except Exception as e:
        return {"error": f"Error al enviar correo: {str(e)}"}

# Endpoint para generar el documento y enviarlo por correo
@app.get("/generate-fact/{id}")
async def generate_fact_endpoint(id: int):
    limpiar_reportes()

    factura_data = await datos_fact(id)
    factura = factura_data["factura"]
    detalles = factura_data["detalles"]

    data = DocumentData(
        cliente=factura["cliente"],
        direc="Dirección del cliente",
        tell="Teléfono del cliente",
        id=f"FACT-{factura['id']}",
        fecha=factura["fecha_fact"],
        subtotal=factura["subtotal"],
        iva=factura["iva"],
        total=factura["total"],
        productos=[Producto(**item) for item in detalles]
    )

    pdf_path = generate_word(data, factura["total"])

    # Renombrar el PDF al código de factura
    nuevo_pdf_path = os.path.join(OUTPUT_PATH, f"{factura['id']}.pdf")
    os.rename(pdf_path, nuevo_pdf_path)

    # Enviar correo con el nombre correcto
    enviar_correo(factura["correo"], nuevo_pdf_path)

    # Enviar el PDF como respuesta al frontend
    with open(nuevo_pdf_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={factura['id']}.pdf"
    })
