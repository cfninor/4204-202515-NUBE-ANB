# 🏀 ANB Rising Stars Showcase
## Desarrollo de software en la nube
### Universidad de los Andes

### 👥 Integrantes del Equipo

| Nombre | Correo |
| ------ | ------ |
| Daniel Beltrán Penagos | d.beltran@uniandes.edu.co |
| Víctor Alfonso Camacho Agudelo | v.camacho@uniandes.edu.co |
| Carlos Felipe Niño Rodríguez | cf.ninor1@uniandes.edu.co |
| Juan Sebastián Rodríguez Gómez | j.rodriguezg@uniandes.edu.co |

---

###  📁 Estructura del Proyecto

```
📦 4204-202515-NUBE-ANB/
├── 📂 anbapi/                         # Backend principal (FastAPI)
│   ├── 📂 app/                        # Código fuente de la API
│   │   ├── 📂 models/                 # Modelos (SQLAlchemy)
│   │   │   ├── 📜 __init__.py
│   │   │   ├── 📜 user.py
│   │   │   ├── 📜 video.py
│   │   │   └── 📜 videoStatus.py
│   │   ├── 📜 __init__.py               
│   │   ├── 📜 config.py                 # Configuración global (variables, entorno)
│   │   ├── 📜 database.py               # Conexión y manejo de la base de datos
│   │   ├── 📜 logging_config.py         # Configuración de logs
│   │   ├── 📜 main.py                   # Punto de entrada principal (FastAPI app)
│   │   └── 📜 prestart.py               # Script previo al inicio
│   ├── 📜 Dockerfile                    # Imagen base para la API
│   ├── 📜 requirements.txt              # Dependencias principales
│   └── 📜 requirements-dev.txt          # Dependencias adicionales para desarrollo
├── 📂 collections/                   # Colecciones de Postman y entornos de pruebas
├── 📂 docs/                          # Documentación general del proyecto
│   └── 📂 Entrega_1/                 # Entrega 1 - Documentos
├── 📂 sustentacion/                  # Recursos de sustentación
│   └── 📂 Entrega_1/                 # Entrega 1 - Sustentación
├── 📜 .env.example                   # Ejemplo de variables de entorno
├── 📜 .gitignore                     # Archivos/carpetas ignoradas por Git
├── 📜 docker-compose.yml             # Orquestación de contenedores (API, DB, Redis, etc.)
└── 📜 README.md                      # Documentación general del proyecto
```

###  📌 Requisitos previos

* 🐳 Docker y Docker Compose
* 🐍 Python 3.13+
* 📦 pip

###  🛠️ Configuración del entorno
1. Clonar el repositorio 
```bash 
git clone git@github.com:cfninor/4204-202515-NUBE-ANB.git
cd 4204-202515-NUBE-ANB
```

2. Configurar variables de entorno
    * Copiar el archivo de ejemplo .env.example a un archivo .env
```bash
cp .env.example .env
```

3. Verificar el archivo `docker-compose.yml`
    * Se pueden ajustar los nombres de los servicios, los puertos y las credenciales si se requiere.

### 🐳 Ejecución con Docker

1. Construir e iniciar los contenedores
```bash
docker compose up --build -d
```

2. Ver logs del servicio principal
```bash
docker compose logs -f api
```

3. Detener los contenedores
```bash
docker compose down
```

### 💻 Instalación local

1. Levantar servicios en Docker
```bash
docker compose up -d postgres pgbouncer redis rabbitmq
```

2. Configurar el archivo .env para apuntar a los puertos expuestos en localhost
```bash
# Ejemplo .env para API local usando infra en Docker
# DATABASE_URL=postgresql+psycopg2://anbuser:anbpass@localhost:6432/anbdb
# RABBIT_URL=amqp://guest:guest@localhost:5672//
# REDIS_URL=redis://localhost:6379/0
cp .env.example .\anbapi\app\.env
```

2. Crear un ambiente virtual 
```bash
python -m venv venv              # Instalar venv
# ACTIVAR AMBIENTE
source venv/bin/activate         # Linux/macOS
venv\Scripts\activate            # Windows
```

3. Instalar dependencias
```bash
cd .\anbapi\
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Ejecutar la aplicación
```bash
cd .\app\
python prestart.py && uvicorn main:app --reload
```
