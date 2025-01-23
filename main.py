import os
import shutil
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

# Configuración de rutas
WORD_TEMPLATE_PATH = './templates/word/templete_test.docx'
OUTPUT_PATH = './outputs'
LOGO_PATH = './templates/img/logo.png'

def generate_word(data):
    """
    Esta función genera un archivo Word a partir de una plantilla y los datos proporcionados.
    """
    try:
        # Cargar la plantilla de Word
        doc = DocxTemplate(WORD_TEMPLATE_PATH)

        # Rellenar la plantilla con los datos
        context = {
            'Nombre': data['Nombre'],
            'Apellido': data['Apellido'],
            'nombre': data['nombre'],
            'apellido': data['apellido'],
            'city': data['city'],
            'age': data['age'],
            'cuerpoCarta': data['cuerpoCarta'],
            'logo': InlineImage(doc, LOGO_PATH, width=Mm(40)),  # Ajusta el tamaño del logo
            'empresa': data['empresa'],
            'version': data['version']
        }

        # Renderizar el documento con los datos
        doc.render(context)

        # Guardar el archivo Word generado
        word_output_path = os.path.join(OUTPUT_PATH, 'documento_generado.docx')
        doc.save(word_output_path)
        print(f"Documento Word generado: {word_output_path}")
        
        return word_output_path
    except Exception as e:
        print(f"Error generando el archivo Word: {e}")
        return None

def limpiarReportes():
    if(os.path.exists(OUTPUT_PATH)):
        shutil.rmtree(OUTPUT_PATH)
    os.mkdir(OUTPUT_PATH)

def main():
    """
    Función principal para generar el documento Word y luego convertirlo a PDF.
    """
    # Datos para llenar la plantilla
    data = {
        'Nombre': 'Juan',
        'Apellido': 'Pérez',
        'nombre': 'Juan',
        'apellido': 'Pérez',
        'city': 'Ciudad de México',
        'age': 30,
        'cuerpoCarta': 'Lorem Ipsum es simplemente el texto de relleno...',
        'logo': LOGO_PATH,  # Ruta del logo
        'empresa': 'Mi Empresa',
        'version': '1.0'
    }
    limpiarReportes()
    # Generar el documento Word
    generate_word(data)

if __name__ == '__main__':
    main()
