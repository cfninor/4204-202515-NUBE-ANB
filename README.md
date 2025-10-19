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
├── 📂 .github/
│ └── 📂 workflows/
│     └── 📜 ci.yml                     # Pipeline CI (tests, lint, cobertura, Sonar, etc.)
├── 📂 anbapi/                          # Backend principal (FastAPI)
│   ├── 📂 app/                         # Código fuente de la API
│   │   ├── 📂 models/                  # Modelos (SQLAlchemy)
│   │   │   ├── 📜 __init__.py
│   │   │   ├── 📜 user.py
│   │   │   ├── 📜 video.py
│   │   │   ├── 📜 videoStatus.py
│   │   │   └── 📜 videoVote.py
│   │   ├── 📂 schemas/                  # Schemas
│   │   │   ├── 📜 __init__.py
│   │   │   └── 📜 auth.py
│   │   ├── 📂 services/                 # Servicios
│   │   │   ├── 📜 __init__.py
│   │   │   ├── 📜 auth.py
│   │   │   └── 📜 video.py
│   │   ├── 📂 storage_a/                # Abstracción lógica storage
│   │   │   ├── 📜 base.py
│   │   │   └── 📜 local.py
│   │   ├── 📂 test/                     # Pruebas unitarias
│   │   │   ├── 📜 conftest.py
│   │   │   ├── 📜 test_auth.py
│   │   │   ├── 📜 test_security.py
│   │   │   ├── 📜 test_task.py
│   │   │   └── 📜 test_video.py
│   │   ├── 📂 workers/                  # Workers - RabbitMQ, tareas pesadas
│   │   │   ├── 📜 __init__.py
│   │   │   └── 📜 tasks.py
│   │   ├── 📜 __init__.py    
│   │   ├── 📜 celery_app.py                # Configuración celery            
│   │   ├── 📜 config.py                    # Configuración global (variables, entorno)
│   │   ├── 📜 database.py                  # Conexión y manejo de la base de datos
│   │   ├── 📜 logging_config.py            # Configuración de logs
│   │   ├── 📜 main.py                      # Punto de entrada principal (FastAPI app)
│   │   ├── 📜 prestart.py                  # Script previo al inicio
│   │   └── 📜 security.py                  # Configuración de seguridad
│   ├── 📜 __init__.py                      
│   ├── 📜 Dockerfile                       # Imagen base para la API
│   ├── 📜 requirements.txt                 # Dependencias principales
│   └── 📜 requirements-dev.txt             # Dependencias adicionales para desarrollo
├── 📂 collections/                     # Colecciones de Postman y entornos de pruebas
├── 📂 docs/                            # Documentación general del proyecto
│   ├── 📂 Entrega_1/                   # Entrega 1 - Documentos
│   │   └── 📜 despliegue_y_documentacion.md # Instalación y ejecución de la aplicación
├── 📂 sustentacion/                    # Recursos de sustentación
│   └── 📂 Entrega_1/                   # Entrega 1 - Sustentación
├── 📜 .coveragerc                      # Configuración de cobertura
├── 📜 .env.example                     # Ejemplo de variables de entorno
├── 📜 .env.example.local               # Ejemplo de variables de entorno local
├── 📜 .gitignore                       # Archivos/carpetas ignoradas por Git
├── 📜 docker-compose.yml               # Orquestación de contenedores (API, DB, Redis, etc.)
├── 📜 pytest.ini                       # Configuración pruebas
├── 📜 README.md                        # Documentación general del proyecto
└── 📜 sonar-project.properties         # Configuración Sonar
```
