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
import ssl

# Configuración de rutas
WORD_TEMPLATE_PATH = './templates/word/factura.docx'
OUTPUT_PATH = './outputs'
LOGO_PATH = './templates/img/Logo_Letras.png'
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:Techniza**@158.220.83.8:5432/postgres")

# Configuración de correo con Zoho Mail
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.zoho.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "onecore_mail@zohomail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "Onecore2025**")

# Configuración SSL
ssl_context = None
try:
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        os.getenv('SSL_CERT_PATH', '/app/certs/fullchain.pem'),
        os.getenv('SSL_KEY_PATH', '/app/certs/privkey.pem')
    )
    print("✅ Configuración SSL cargada correctamente")
except Exception as e:
    print(f"⚠️ Advertencia: No se pudo cargar la configuración SSL: {str(e)}")

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://admin.techniza.mx",
        "http://admin.techniza.mx",
        "http://localhost:4200"
    ],
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
    os.makedirs(OUTPUT_PATH, exist_ok=True)

# Función para convertir Word a PDF usando LibreOffice
def convertir_a_pdf(word_path: str) -> str:
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
def generate_word(data: DocumentData) -> str:
    try:
        # Verificar existencia de plantilla
        if not os.path.exists(WORD_TEMPLATE_PATH):
            raise FileNotFoundError(f"Plantilla no encontrada en {WORD_TEMPLATE_PATH}")
        
        doc = DocxTemplate(WORD_TEMPLATE_PATH)
        context = data.dict()
        
        # Añadir logo si existe
        if os.path.exists(LOGO_PATH):
            context['logo'] = InlineImage(doc, LOGO_PATH, width=Mm(40))
        else:
            print("⚠️ Logo no encontrado, se omitirá en el documento")

        doc.render(context)
        word_output_path = os.path.join(OUTPUT_PATH, 'factura_generada.docx')
        doc.save(word_output_path)

        return convertir_a_pdf(word_output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Función para conectar a PostgreSQL
async def connect_db():
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo conectar a la base de datos: {str(e)}"
        )

# Función para obtener datos de la factura
async def datos_fact(id: int) -> dict:
    try:
        conn = await connect_db()

        # Consulta datos maestros de la factura
        factura = await conn.fetchrow("""
            SELECT fm.id, fc.subtotal, fc.iva, fc.total, 
                   uc.nombre AS cliente, uc.correo, uc.direccion, uc.telefono,
                   TO_CHAR((CURRENT_DATE + fm.fecha_reg)::timestamp, 'YYYY-MM-DD') AS fecha_fact
            FROM fact_maestro fm 
            JOIN fact_venta_costo fc ON fc.id_factura = fm.id 
            JOIN usu_cliente uc ON uc.id = fm.id_cliente
            WHERE fm.id = $1
        """, id)

        if not factura:
            await conn.close()
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        # Consulta items de la factura
        detalles = await conn.fetch("""
            SELECT p.descripcion, fi.cantidad, 
                   CAST(p.venta AS NUMERIC) AS costo_unitario, 
                   (CAST(p.venta AS NUMERIC) * fi.cantidad AS costo_total
            FROM fact_venta_item fi
            JOIN producto p ON p.id = fi.id_producto
            WHERE fi.id_factura = $1
            ORDER BY fi.id
        """, id)

        await conn.close()

        return {
            "factura": dict(factura),
            "detalles": [dict(row) for row in detalles]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Función para enviar correo con PDF adjunto
def enviar_correo(destinatario: str, archivo_adjunto: str) -> dict:
    try:
        if not os.path.exists(archivo_adjunto):
            return {"error": f"Archivo {archivo_adjunto} no encontrado"}

        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = destinatario
        msg['Subject'] = "Factura Techniza"

        cuerpo = f"""
        Hola {destinatario.split('@')[0]},

        Adjuntamos tu factura de Techniza. 
        Gracias por tu preferencia.

        Atentamente,
        Equipo Techniza
        """
        msg.attach(MIMEText(cuerpo, 'plain'))

        with open(archivo_adjunto, "rb") as f:
            adjunto = MIMEBase("application", "octet-stream")
            adjunto.set_payload(f.read())
            encoders.encode_base64(adjunto)
            adjunto.add_header(
                "Content-Disposition",
                f"attachment; filename=Factura_Techniza_{os.path.basename(archivo_adjunto)}"
            )
            msg.attach(adjunto)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return {"success": f"Correo enviado a {destinatario}"}
    except Exception as e:
        return {"error": f"Error al enviar correo: {str(e)}"}

# Endpoint para generar factura
@app.get("/generate-fact/{id}", response_class=Response)
async def generate_fact_endpoint(id: int):
    """
    Genera una factura en PDF y la envía por correo
    """
    try:
        # Limpiar directorio de salida
        limpiar_reportes()

        # Obtener datos de la factura
        factura_data = await datos_fact(id)
        factura = factura_data["factura"]
        detalles = factura_data["detalles"]

        # Preparar datos para la plantilla
        data = DocumentData(
            cliente=factura["cliente"],
            direc=factura.get("direccion", "N/A"),
            tell=factura.get("telefono", "N/A"),
            id=f"FACT-{factura['id']}",
            fecha=factura["fecha_fact"],
            subtotal=factura["subtotal"],
            iva=factura["iva"],
            total=factura["total"],
            productos=[Producto(**item) for item in detalles]
        )

        # Generar PDF
        pdf_path = generate_word(data)

        # Enviar por correo
        if factura.get("correo"):
            email_result = enviar_correo(factura["correo"], pdf_path)
            print(f"📧 Resultado envío correo: {email_result}")

        # Devolver PDF como respuesta
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Factura_{id}.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar factura: {str(e)}"
        )

# Endpoint de salud
@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "details": {
            "database": "Connected" if await connect_db() else "Disconnected",
            "templates": {
                "word": os.path.exists(WORD_TEMPLATE_PATH),
                "logo": os.path.exists(LOGO_PATH)
            },
            "ssl": ssl_context is not None
        }
    }