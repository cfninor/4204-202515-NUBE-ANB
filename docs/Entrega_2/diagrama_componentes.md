**Modelo de Componentes**

![Diagrama de Componentes](https://github.com/user-attachments/assets/7245c598-3517-463e-ba6d-298e1e8afd7a)

| Componente | Descripción |
|-------------|--------------|
| **API REST** | Expone endpoints HTTP; valida peticiones, gestiona lógica de negocio y encola trabajos para el procesamiento asíncrono. |
| **Worker (<<async>>)** | Procesa tareas pesadas en segundo plano (por ejemplo, transformación de archivos o generación de resultados). |
| **ORM / Driver** | Interfaz de acceso a base de datos, utilizada por API y Worker. Maneja operaciones SQL hacia RDS. |
| **NFS Client (<<mount>>)** | Cliente de red que monta el sistema de archivos compartido (NFS). Tanto API como Worker lo utilizan. |
| **NFS Share** | Sistema de archivos compartido que almacena archivos de entrada, temporales y resultados procesados. |
| **Base de Datos** | Almacena datos estructurados, metadatos y estados del sistema. Implementada en Amazon RDS. |
| **Queue** | Cola de trabajos que desacopla la API del Worker (asincronía). |
| **Secretos (<<authentication>>)** | Servicio para gestión de credenciales, tokens o llaves de conexión. |
| **Logs** | Servicio de almacenamiento y monitoreo de registros (logs de aplicación y sistema). |
