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
├── 📂 anbapi/                          # Backend principal (FastAPI)
│   ├── 📂 app/                         # Código fuente de la API
│   │   ├── 📂 models/                  # Modelos (SQLAlchemy)
│   │   │   ├── 📜 __init__.py
│   │   │   ├── 📜 user.py
│   │   │   ├── 📜 video.py
│   │   │   └── 📜 videoStatus.py
│   │   ├── 📜 __init__.py               
│   │   ├── 📜 config.py                    # Configuración global (variables, entorno)
│   │   ├── 📜 database.py                  # Conexión y manejo de la base de datos
│   │   ├── 📜 logging_config.py            # Configuración de logs
│   │   ├── 📜 main.py                      # Punto de entrada principal (FastAPI app)
│   │   └── 📜 prestart.py                  # Script previo al inicio
│   ├── 📜 Dockerfile                       # Imagen base para la API
│   ├── 📜 requirements.txt                 # Dependencias principales
│   └── 📜 requirements-dev.txt             # Dependencias adicionales para desarrollo
├── 📂 collections/                     # Colecciones de Postman y entornos de pruebas
├── 📂 docs/                            # Documentación general del proyecto
│   ├── 📂 Entrega_1/                   # Entrega 1 - Documentos
│   │   └── 📜 despliegue_y_documentacion.md # Instalación y ejecución de la aplicación
├── 📂 sustentacion/                    # Recursos de sustentación
│   └── 📂 Entrega_1/                   # Entrega 1 - Sustentación
├── 📜 .env.example                     # Ejemplo de variables de entorno
├── 📜 .gitignore                       # Archivos/carpetas ignoradas por Git
├── 📜 docker-compose.yml               # Orquestación de contenedores (API, DB, Redis, etc.)
└── 📜 README.md                        # Documentación general del proyecto
```
