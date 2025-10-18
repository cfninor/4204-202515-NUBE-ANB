# Despliegue y Documentación

Este documento describe el procedimiento de instalación y ejecución de la aplicación **ANB Rising Stars Showcase**, se separa en:

* Ejecución con Docker.
* Instalación local. 

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

### 🧪 Pruebas locales

1. Desde la carpeta raíz del proyecto
```bash
python -m pytest
```
