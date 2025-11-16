# Diagrama de componentes

![Diagrama de componentes](img/DiagramaComponentes.jpg)

# Presentation tier

## APP (Cliente externo)
* Corresponde al consumidor externo que realiza solicitudes HTTP al sistema.
* Solo interactúa con el Application Load Balancer (ALB).
* No interactúa directamente con la API ni con los servicios internos.

# API

## Application Load Balancer (ALB)
* Expuesto en la subred pública.
* Recibe todas las solicitudes HTTP/80 desde el cliente.
* Distribuye el tráfico entre las instancias EC2 del API.
* Usa health checks para verificar si una instancia sigue activa (ej. /health).
* Está asociado al Security Group anb-sg-web, que permite tráfico entrante HTTP desde internet y tráfico interno hacia la API.

## API REST (EC2 ASG - FastAPI + Gunicorn)
* Servicio principal que expone los endpoints HTTP.
* Está detrás de un Application Load Balancer (ALB) en la subred pública.
* Se despliega mediante un Auto Scaling Group (Lab Auto Scaling Group) que ajusta el número de instancias según la carga.
* Interactúa con:
    * RDS PostgreSQL para operaciones SQL.
    * S3 para guardar o consultar los videos cargados o procesados.
    * Amazon SQS para publicar tareas asíncronas hacia los Workers.

# Application Layer (Lógica de la aplicación)

## UserService (Gestión de usuarios)
* Implementa la lógica para manejo de usuarios y sesiones.

## VideoService (Gestión de videos)
* Procesa solicitudes relacionadas con archivos multimedia.
* Publica tareas pesadas hacia Amazon SQS (procesamiento de video).
* También consulta metadatos en la base de datos RDS.

## PublicService (Servicios públicos)
* Muestra los servicios que no requieren autorización.

## Amazon SQS (Broker de Mensajes)
* Reemplaza completamente a RabbitMQ.
* Cola administrada, escalable y sin mantenimiento.
* Flujo principal:
    * La API publica los videos a procesar en SQS (Publish).
    * Los Workers consumen los videos a procesar desde la misma cola (Consume).

## Worker (EC2 ASG – Celery / Procesamiento Asíncrono)
* Conjunto de instancias en un Auto Scaling Group independiente (Worker Auto Scaling Group).
* Solo accesibles dentro de la red privada.
* Procesa las tareas enviadas desde SQS.
* Interactúa con:
    * S3 (consulta de videos por procesar y almacenamiento de videos procesados).
    * RDS PostgreSQL para guardar resultados o actualizar estados.

# Data tier (capa de datos y almacenamiento)

## Amazon S3
* Servicio de almacenamiento de objetos.
* El api sube los videos a procesar.
* El Worker consulta los videos a procesar y guarda los videos procesados.
* La API REST puede consultar S3 a través de URLs firmadas o presignadas.

## Base de datos
* Almacena los datos de negocio o metadatos de las operaciones.
* El Worker y la API REST se comunican con ella mediante el ORM/Driver.
ORM / Driver
* Componente de software que conecta la lógica de aplicación (Python ORM, por ejemplo SQLAlchemy) con el motor de base de datos relacional (PostgreSQL).

## Redis (Cache distribuida)
* Proporciona almacenamiento temporal y cacheo rápido.
* Se usa dentro de los servicios públicos para devolver resultados de manera más eficiente.

# Monitoring tier (monitoreo, logs y métricas)

## Amazon CloudWatch
* Es el servicio de observabilidad principal.
* Supervisa en general a todos los componentes presentados.
* Alarmas para el escalamiento automático:
    * API (uso de CPU)
    * SQS (mensajes pendientes)

# Security Groups

## anb-sg-web
* Acepta tráfico HTTP del ALB.
* Permite salida a:
    * S3
    * SQS
    * RDS

## anb-sg-worker
* Permite conexión hacia:
    * SQS
    * S3
    * RDS

## anb-sg-postgres
* Solo permite acceso al puerto 5432 desde:
    * API
    * Worker
