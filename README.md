
---

# PFO 3: Sistema Distribuido Cliente-Servidor

> **Transformación de una arquitectura monolítica a distribuida utilizando Sockets, Hilos y Colas en Python.**

Este proyecto implementa un sistema distribuido capaz de recibir tareas desde múltiples clientes (Web, Móvil y Consola), balancear la carga, procesarlas asíncronamente mediante un pool de workers y persistir los resultados en almacenamiento local simulando servicios cloud.

## ️ Arquitectura del Sistema

El sistema sigue un patrón de **Cliente-Servidor** con balanceo de carga integrado. Aunque está diseñado para ejecutarse nativamente en un solo host (para facilitar la colaboración sin Docker), su estructura lógica replica una arquitectura de nube moderna (AWS-style).

```mermaid
flowchart TB
    %% Estilos
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef lb fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef queue fill:#e3f2fd,stroke:#2196f3,stroke-width:2px;
    classDef worker fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef storage fill:#fce4ec,stroke:#e91e63,stroke-width:2px;

    subgraph CLIENTES["🌐 CAPA DE CLIENTES"]
        direction LR
        Web["📱 Web / Móvil<br/>(HTTP/JSON)"]:::client
        Console[" Consola Python<br/>(Socket TCP)"]:::client
    end

    subgraph SERVIDOR["⚙️ SERVIDOR DISTRIBUIDO (Python)"]
        
        subgraph ENTRY[" ENTRADA"]
            LB[" Balanceador de Carga<br/>Flask + Sockets<br/>Puertos: 5000/5001"]:::lb
        end

        subgraph CORE[" PROCESAMIENTO"]
            MQ[" Cola de Mensajes<br/>queue.Queue()"]:::queue
            
            subgraph WORKERS[" POOL DE WORKERS"]
                W1["Worker 1"]:::worker
                W2["Worker 2"]:::worker
                W3["Worker 3"]:::worker
            end
        end

        subgraph DATA[" ALMACENAMIENTO"]
            DB[(" SQLite<br/>tareas.db")]:::storage
            FS[(" File System<br/>/almacenamiento/")]:::storage
        end
    end

    Web -->|HTTP :5001| LB
    Console -->|TCP :5000| LB
    LB --> MQ
    MQ --> W1 & W2 & W3
    W1 & W2 & W3 --> DB & FS
```

###  Componentes Clave

1.  **Balanceador de Carga (Load Balancer):**
    *   Implementado en Python usando `socket` y `Flask`.
    *   Escucha en dos puertos: `5000` (TCP puro para consola) y `5001` (HTTP para web/móvil).
    *   Distribuye las tareas entrantes hacia la cola interna.

2.  **Cola de Mensajes (Message Queue):**
    *   Utiliza `queue.Queue()` de Python para desacoplar la recepción de tareas del procesamiento.
    *   Permite manejar picos de tráfico sin bloquear a los clientes.

3.  **Pool de Workers:**
    *   Hilos (`threading.Thread`) que consumen tareas de la cola.
    *   Cada worker puede realizar operaciones de:
        *    **Hash:** Cálculo SHA-256.
        *    **Contar:** Longitud de caracteres.
        *    **Archivos:** Guardado de contenido en disco.

4.  **Almacenamiento Distribuido (Simulado):**
    *   **SQLite:** Para metadatos, estados y resultados estructurados.
    *   **File System:** Simula un bucket de S3 para almacenamiento de objetos binarios o texto.

---

##  Tecnologías Utilizadas

*   **Lenguaje:** Python 3.8+
*   **Backend:** Flask (Web), Socket Library (TCP)
*   **Concurrencia:** Threading, Queue
*   **Base de Datos:** SQLite3
*   **Frontend:** HTML5 + CSS3 + JavaScript (Fetch API)

---

##  Instalación y Uso

### 1. Prerrequisitos
Asegúrate de tener Python instalado. No se requiere Docker ni bases de datos externas.

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/pfo3-sistema-distribuido.git
cd pfo3-sistema-distribuido

# Instalar dependencias
pip install flask
```

### 2. Ejecutar el Servidor
Inicia el servidor principal. Este levantará la interfaz web y el socket de escucha.

```bash
python server/servidor.py
```

> **Nota:** El servidor te mostrará en la terminal la IP local para acceder desde tu celular u otra PC en la misma red WiFi (ej: `http://192.168.1.15:5001`).

### 3. Usar el Cliente Web
Abre tu navegador en `http://localhost:5001` (o la IP mostrada).
*   Selecciona el tipo de tarea (Hash, Contar, Archivo).
*   Ingresa el contenido.
*   Haz clic en "Enviar Tarea".
*   Verás el resultado en la tabla inferior tras unos segundos.

### 4. Usar el Cliente de Consola
En otra terminal, ejecuta el cliente interactivo:

```bash
python client/cliente.py
```
Sigue el menú para enviar tareas vía Socket TCP directamente al balanceador.

---

## 📂 Estructura del Proyecto

```text
pfo3-sistema-distribuido/
├── server/
│   ├── servidor.py           # Lógica principal (LB, Workers, DB)
│   ── templates/
│       └── index.html        # Interfaz de usuario Web
├── client/
│   └── cliente.py            # Cliente de consola TCP
├── almacenamiento/           # Carpeta generada para archivos guardados
├── tareas.db                 # Base de datos SQLite generada
├── requirements.txt
└── README.md
```

---

##  Notas de Arquitectura (DevOps)

*   **Sin Docker:** El proyecto está diseñado para correr nativamente ("bare-metal") para evitar problemas de virtualización entre compañeros.
*   **Persistencia Local:** En un entorno de producción real, SQLite sería reemplazado por PostgreSQL RDS y la carpeta `/almacenamiento` por AWS S3.
*   **Escalabilidad:** Para escalar horizontalmente, la `queue.Queue()` debería ser reemplazada por un servicio externo como RabbitMQ o Redis, permitiendo que los Workers corran en diferentes máquinas.

---

##  Autore

*  Miguel Sebastián Gutierrez - *Estudiante de Desarrollo de Software*

---

## Licencia

Este proyecto es parte de la materia **Práctica Final Orientada (PFO)** y está destinado exclusivamente para fines educativos.