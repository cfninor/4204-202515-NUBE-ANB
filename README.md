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

# Documentación Entrega 1
| Documento                         | Descripción                                                                                                                                                                                  | Ruta                                                                                              |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Modelo de Datos**               | Diagrama Entidad-Relación (ERD) que representa las entidades principales del sistema, sus atributos y relaciones.                                                                            | [`/docs/Entrega_1/modelo_de_datos.md`](./docs/Entrega_1/modelo_de_datos.md)                             |
| **Documentación de la API**       | Descripción de los endpoints, parámetros, códigos de respuesta y ejemplos de uso. Incluye la colección de pruebas Postman.                                                                   | [`/docs/Entrega_1/documentacion_api.md`](./docs/Entrega_1/documentacion_api.md)                   |
| **Diagrama de Componentes**       | Representación visual de la arquitectura: API (FastAPI), Worker (Celery), Broker (RabbitMQ), Cache (Redis) y Base de Datos (PostgreSQL con PgBouncer).                                       | [`/docs/Entrega_1/diagrama_componentes.md`](./docs/Entrega_1/diagrama_componentes.md)             |
| **Diagrama de Flujo de Procesos** | Explicación detallada del flujo de carga, procesamiento (workers), y entrega de los videos.                                                                                                  | [`/docs/Entrega_1/diagrama_flujo.md`](./docs/Entrega_1/diagrama_flujo.md)       |
| **Despliegue y Documentación**    | Guía para la instalación, configuración de entorno, ejecución de contenedores Docker, y replicación del entorno local o en la nube.                                                          | [`/docs/Entrega_1/despliegue_y_documentacion.md`](./docs/Entrega_1/despliegue_y_documentacion.md) |
| **Reporte de Análisis SonarQube** | Evidencia del último análisis ejecutado sobre la rama principal. Incluye: métricas de *bugs*, *vulnerabilidades*, *code smells*, cobertura de pruebas unitarias y estado del *quality gate*. | [`/docs/Entrega_1/sonarqube_report.md`](./docs/Entrega_1/sonarqube_report.md)                     |

## Colecciones de Postman

Las colecciones y entornos se encuentran en el directorio  [`/collections`](./collections)

## Sustentación

El video de sustentación correspondiente a la Entrega 1 se encuentra disponible en la siguiente ruta:  [`/sustentacion/Entrega_1`](./sustentacion/Entrega_1)

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
│   │   │   ├── 📜 auth.py
│   │   │   └── 📜 video.py
│   │   ├── 📂 services/                 # Servicios
│   │   │   ├── 📜 __init__.py
│   │   │   ├── 📜 auth.py
│   │   │   ├── 📜 public_ranking.py
│   │   │   ├── 📜 public_video.py
│   │   │   ├── 📜 public.py
│   │   │   └── 📜 video.py
│   │   ├── 📂 storage_a/                # Abstracción lógica storage
│   │   │   ├── 📜 base.py
│   │   │   └── 📜 local.py
│   │   ├── 📂 test/                     # Pruebas unitarias
│   │   │   ├── 📜 conftest.py
│   │   │   ├── 📜 test_auth.py
│   │   │   ├── 📜 test_public.py
│   │   │   ├── 📜 test_ranking.py
│   │   │   ├── 📜 test_security.py
│   │   │   ├── 📜 test_task.py
│   │   │   ├── 📜 test_video.py
│   │   │   └── 📜 test_vote.py
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
│   ├── 📂 nginx/                           # Configuración de NGINX
│   │   ├── 📂 conf.d/ 
│   │   │   └──  📜 api.conf                # Configuración api 
│   │   └── 📜 nginx.conf                   # Configuración global de NGINX
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
