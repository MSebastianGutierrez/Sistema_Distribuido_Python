#!/usr/bin/env python3
"""
Servidor Distribuido para PFO 3
- Balanceador de carga + Workers + Cola
- Interfaz HTTP con Flask para navegador
"""

import socket
import threading
import sqlite3
import json
import os
import queue
import hashlib
from datetime import datetime
from typing import Dict, Tuple
from flask import Flask, render_template, request, jsonify

# ============================================
# CONFIGURACIÓN
# ============================================
HOST = 'localhost'
PORT_BALANCEADOR = 5000
PORT_HTTP = 5001          # Puerto para el navegador
NUM_WORKERS = 3
BUFFER_SIZE = 4096
ALMACENAMIENTO_DIR = 'almacenamiento'
DB_FILE = 'tareas.db'

# Cola de tareas (simula RabbitMQ)
cola_tareas = queue.Queue()

# Aplicación Flask para interfaz web
app = Flask(__name__)


# ============================================
# BASE DE DATOS (metadatos)
# ============================================
def inicializar_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                resultado TEXT,
                archivo_ruta TEXT,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                completado_en DATETIME
            )
        ''')
        conn.commit()
    print("✅ Base de datos inicializada")


def guardar_tarea(tarea_id: str, tipo: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tareas (id, tipo) VALUES (?, ?)',
            (tarea_id, tipo)
        )
        conn.commit()


def actualizar_tarea(tarea_id: str, estado: str, resultado: str = None, archivo_ruta: str = None):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if resultado:
            cursor.execute(
                'UPDATE tareas SET estado = ?, resultado = ?, completado_en = ? WHERE id = ?',
                (estado, resultado, datetime.now(), tarea_id)
            )
        elif archivo_ruta:
            cursor.execute(
                'UPDATE tareas SET estado = ?, archivo_ruta = ?, completado_en = ? WHERE id = ?',
                (estado, archivo_ruta, datetime.now(), tarea_id)
            )
        else:
            cursor.execute(
                'UPDATE tareas SET estado = ?, completado_en = ? WHERE id = ?',
                (estado, datetime.now(), tarea_id)
            )
        conn.commit()


def obtener_tareas(limit: int = 20):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM tareas ORDER BY creado_en DESC LIMIT ?',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_tarea_por_id(tarea_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tareas WHERE id = ?', (tarea_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ============================================
# ALMACENAMIENTO DE ARCHIVOS (simula S3)
# ============================================
def guardar_archivo(tarea_id: str, datos: bytes) -> str:
    os.makedirs(ALMACENAMIENTO_DIR, exist_ok=True)
    ruta = os.path.join(ALMACENAMIENTO_DIR, f"{tarea_id}.dat")
    with open(ruta, 'wb') as f:
        f.write(datos)
    return ruta


# ============================================
# WORKER (procesa tareas)
# ============================================
class Worker:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.running = True
        self.hilo = threading.Thread(target=self.ejecutar, daemon=True)

    def iniciar(self):
        self.hilo.start()
        print(f"👷 Worker {self.worker_id} iniciado")

    def ejecutar(self):
        while self.running:
            try:
                tarea = cola_tareas.get(timeout=1)
                self.procesar_tarea(tarea)
                cola_tareas.task_done()
            except queue.Empty:
                continue

    def procesar_tarea(self, tarea: Dict):
        tarea_id = tarea['id']
        tipo = tarea['tipo']
        datos = tarea['datos']

        print(f"🔧 Worker {self.worker_id} procesando tarea {tarea_id} ({tipo})")

        try:
            if tipo == 'hash':
                resultado = hashlib.sha256(datos.encode()).hexdigest()
                actualizar_tarea(tarea_id, 'completada', resultado=resultado)

            elif tipo == 'archivo':
                ruta = guardar_archivo(tarea_id, datos.encode())
                actualizar_tarea(tarea_id, 'completada', archivo_ruta=ruta)

            elif tipo == 'contar':
                resultado = str(len(datos))
                actualizar_tarea(tarea_id, 'completada', resultado=resultado)

            else:
                actualizar_tarea(tarea_id, 'error', resultado=f"Tipo desconocido: {tipo}")

            print(f"✅ Worker {self.worker_id} completó tarea {tarea_id}")

        except Exception as e:
            actualizar_tarea(tarea_id, 'error', resultado=str(e))
            print(f"❌ Worker {self.worker_id} falló: {e}")


# ============================================
# BALANCEADOR (recibe tareas por socket)
# ============================================
class Balanceador:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket_servidor = None
        self.running = True

    def iniciar(self):
        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_servidor.bind((self.host, self.port))
        self.socket_servidor.listen(100)
        self.socket_servidor.settimeout(1.0)

        print(f"⚖️ Balanceador de sockets en {self.host}:{self.port}")

        while self.running:
            try:
                cliente, direccion = self.socket_servidor.accept()
                self.atender_cliente(cliente, direccion)
            except socket.timeout:
                continue

    def atender_cliente(self, cliente: socket.socket, direccion: Tuple):
        try:
            datos = cliente.recv(BUFFER_SIZE).decode('utf-8')
            if not datos:
                return

            tarea = json.loads(datos)
            tarea_id = tarea.get('id', hashlib.md5(datos.encode()).hexdigest()[:8])
            tarea['id'] = tarea_id

            guardar_tarea(tarea_id, tarea.get('tipo', 'desconocido'))
            cola_tareas.put(tarea)

            respuesta = json.dumps({
                'estado': 'aceptado',
                'tarea_id': tarea_id,
                'mensaje': 'Tarea encolada'
            })
            cliente.send(respuesta.encode('utf-8'))

        except Exception as e:
            cliente.send(f'{{"error": "{str(e)}"}}'.encode())
        finally:
            cliente.close()


# ============================================
# INTERFAZ WEB CON FLASK
# ============================================
@app.route('/')
def index():
    """Página principal con formulario y listado de tareas"""
    tareas = obtener_tareas(20)
    return render_template('index.html', tareas=tareas)


@app.route('/api/tareas', methods=['POST'])
def api_crear_tarea():
    """Endpoint para crear tareas desde el navegador (AJAX)"""
    datos = request.json
    tipo = datos.get('tipo')
    contenido = datos.get('contenido')

    if not tipo or not contenido:
        return jsonify({'error': 'Faltan campos'}), 400

    tarea_id = hashlib.md5(f"{tipo}{contenido}{datetime.now()}".encode()).hexdigest()[:8]

    guardar_tarea(tarea_id, tipo)
    cola_tareas.put({
        'id': tarea_id,
        'tipo': tipo,
        'datos': contenido
    })

    return jsonify({
        'estado': 'aceptado',
        'tarea_id': tarea_id,
        'mensaje': 'Tarea encolada'
    }), 202


@app.route('/api/tareas/<tarea_id>')
def api_obtener_tarea(tarea_id):
    """Consultar estado de una tarea específica"""
    tarea = obtener_tarea_por_id(tarea_id)
    if not tarea:
        return jsonify({'error': 'Tarea no encontrada'}), 404
    return jsonify(tarea)


@app.route('/api/tareas')
def api_listar_tareas():
    """Listar todas las tareas"""
    tareas = obtener_tareas(50)
    return jsonify(tareas)


# ============================================
# INICIO (hilos separados)
# ============================================
if __name__ == '__main__':
    inicializar_db()

    def mostrar_acceso():
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                print("\n" + "=" * 50)
                print("📱 ACCESO DESDE CELULAR U OTRA PC")
                print("=" * 50)
                print(f"🌐 En tu celular (misma WiFi):")
                print(f"   http://{ip}:{PORT_HTTP}")
                print("=" * 50)
        except:
            pass

    # Mostrar información de acceso
    mostrar_acceso()

    # Iniciar workers
    workers = []
    for i in range(NUM_WORKERS):
        worker = Worker(i + 1)
        worker.iniciar()
        workers.append(worker)

    # Iniciar balanceador de sockets en segundo plano
    balanceador = Balanceador(HOST, PORT_BALANCEADOR)
    hilo_balanceador = threading.Thread(target=balanceador.iniciar, daemon=True)
    hilo_balanceador.start()

    # Iniciar servidor web Flask (para navegador)
    print(f"\n🌐 Interfaz web local: http://localhost:{PORT_HTTP}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=PORT_HTTP, debug=False, use_reloader=False)