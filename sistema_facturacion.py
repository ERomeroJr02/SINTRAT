from flask import Flask, render_template, request, jsonify
import json
import datetime
import os
import re
import urllib.request
import ssl

app = Flask(__name__)

NOMBRE_NEGOCIO = "SINTRAT"
UBICACION = "Palacio de Justicia"

def obtener_tasas_bcv_automaticas():
    """Consulta las tasas oficiales de USD y EUR directamente desde el portal del BCV"""
    url = "https://www.bcv.org.ve/"
    context = ssl._create_unverified_context()
    
    # Valores de respaldo actualizados
    tasas = {"dolar": 784.66, "euro": 916.00}

    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            html = response.read().decode('utf-8')

            # Extraer tasa del Dólar (div id="dolar")
            match_dolar = re.search(r'id="dolar".*?<strong>\s*([\d,.]+)\s*</strong>', html, re.DOTALL)
            if match_dolar:
                tasa_usd_str = match_dolar.group(1).replace('.', '').replace(',', '.')
                tasas["dolar"] = round(float(tasa_usd_str), 2)

            # Extraer tasa del Euro (div id="euro")
            match_euro = re.search(r'id="euro".*?<strong>\s*([\d,.]+)\s*</strong>', html, re.DOTALL)
            if match_euro:
                tasa_eur_str = match_euro.group(1).replace('.', '').replace(',', '.')
                tasas["euro"] = round(float(tasa_eur_str), 2)

    except Exception as e:
        print(f"Aviso: No se pudo conectar al BCV ({e}). Usando tasas de respaldo.")

    return tasas

def cargar_productos():
    if os.path.exists('productos.json'):
        with open('productos.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.route('/')
def home():
    productos = cargar_productos()
    tasas = obtener_tasas_bcv_automaticas()
    return render_template('index.html', productos=productos, tasas=tasas)

@app.route('/api/generar-ticket', methods=['POST'])
def generar_ticket():
    datos = request.get_json()
    items = datos.get('items', [])
    tasa_usd = float(datos.get('tasa_usd', 0.0))
    tasa_eur = float(datos.get('tasa_eur', 0.0))
    
    if not items:
        return jsonify({'error': 'El carrito está vacío'}), 400

    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
    
    lineas = []
    lineas.append("========================================")
    lineas.append(f"{NOMBRE_NEGOCIO.center(40)}")
    lineas.append(f"{UBICACION.center(40)}")
    lineas.append(f"Fecha: {fecha_actual}")
    lineas.append(f"BCV USD: Bs. {tasa_usd:.2f} | EUR: Bs. {tasa_eur:.2f}")
    lineas.append("========================================")
    lineas.append(f"{'Cant. Producto':<20} {'P.Unit(Bs)':<10} {'Total(Bs)':<10}")
    lineas.append("----------------------------------------")

    subtotal_general_bs = 0.0

    for item in items:
        nombre = item['nombre']
        precio_bs = float(item['precio_bs'])
        cantidad = int(item['cantidad'])
        
        subtotal_linea_bs = precio_bs * cantidad
        subtotal_general_bs += subtotal_linea_bs

        nombre_cant = f"{cantidad}x {nombre}"
        if len(nombre_cant) > 19:
            nombre_cant = nombre_cant[:16] + "..."
            
        lineas.append(f"{nombre_cant:<20} {precio_bs:<10.2f} {subtotal_linea_bs:<10.2f}")

    lineas.append("========================================")
    lineas.append(f"TOTAL A PAGAR:      Bs. {subtotal_general_bs:>12.2f}")
    lineas.append("========================================")
    lineas.append(f"{'¡Gracias por su compra!'.center(40)}")
    lineas.append("========================================")

    ticket_texto = "\n".join(lineas)

    nombre_archivo = f"ticket_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(ticket_texto)

    return jsonify({
        'ticket': ticket_texto,
        'archivo_guardado': nombre_archivo
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)