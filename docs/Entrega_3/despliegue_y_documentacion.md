# Despliegue y Documentación

Este documento describe los servicios incorporados para la escalabilidad en la capa web, siguiendo los lineamientos de la *Entrega 3 - Escalabilidad en la capa web*..

Se presenta:
* Modelo de despliegue.
* Explicación de las tecnologías y servicios incorporados.
* Cambios realizados con respecto a la entrega anterior.

---

## ☁️ Modelo de Despliegue

El nuevo modelo de despliegue está basado en una infraestructura modular dentro de una **VPC de AWS**, con subredes públicas y privadas.  
La **subred pública** aloja las instancias EC2 (API y Worker) y el **Application Load Balancer**, mientras que la **subred privada** contiene la base de datos RDS.  
El almacenamiento de archivos se realiza en **Amazon S3**, y **CloudWatch** supervisa todos los recursos para activar alarmas y escalar instancias de manera automática.



---

## 🧩 Tecnologías y Servicios Incorporados

| Servicio | Descripción |
|-----------|--------------|
| **Amazon EC2** | Instancias virtuales que ejecutan la capa web (API REST) y el Worker. |
| **Application Load Balancer (ALB)** | Distribuye equitativamente el tráfico HTTP/HTTPS entre las instancias API del Auto Scaling Group. |
| **Auto Scaling Group (ASG)** | Monitorea las métricas de CPU, memoria o tráfico y ajusta el número de instancias EC2 API según demanda. |
| **Amazon RDS (PostgreSQL)** | Base de datos relacional gestionada; mantiene la persistencia de los datos de la aplicación. |
| **Amazon S3** | Reemplaza al NFS como almacenamiento distribuido de objetos; almacena videos originales y procesados. |
| **Amazon CloudWatch** | Servicio de monitoreo de recursos (CPU, red, disco). Genera alarmas que activan las políticas de escalado automático. |
| **Security Groups** | Controlan los puertos y la comunicación entre los componentes internos de la VPC. |
---

## 🔩 Arquitectura Ajustada

La arquitectura fue modificada con respecto a la entrega #2 para poder responder a los requerimientos de escalabilidad, disponibilidad y eficiencia en la nube de AWS.

En la entrega se incorporan los servicios que permitan la ejecución automática de múltiples instancias de la capa web, la distribución de carga, y el monitoreo en tiempo real de los recursos.

Los cambios realizados son:
* Se implementa el balanceador de carga **(Application Load Balancer - ALB)**.
* Se configura el **Auto Scaling Group (ASG)** para la capa web.
* Se migra el almacenamiento de archivos desde el servidor NFS hacia **Amazon S3.**
* Se integra **Amazon CloudWatch** para el monitoreo y activación de las políticas de escalado.

---

## 🔄 Cambios Principales Respecto a la Entrega 2

| Componente | Entrega 2 | Entrega 3 (actual) |
|-------------|------------|--------------------|
| **API (EC2)** | Una sola instancia EC2 servía la API | Varias instancias EC2 bajo **Auto Scaling Group**, detrás de un **Load Balancer (ALB)** |
| **Worker (EC2)** | Instancia única dedicada al procesamiento asíncrono | Se mantiene igual, pero ahora monitoreada por **CloudWatch** |
| **NFS Server (EC2)** | Servidor compartido de archivos (NFS) | Eliminado. Los archivos ahora se almacenan en **Amazon S3** |
| **Base de datos** | PostgreSQL en RDS o EC2 | Se mantiene en **Amazon RDS**, accesible solo desde la VPC |
| **Monitoreo** | No existía | **Amazon CloudWatch** registra métricas y activa políticas de escalado |
| **Escalabilidad** | Manual o inexistente | **Auto Scaling Group** gestiona nuevas instancias EC2 API según la carga |

