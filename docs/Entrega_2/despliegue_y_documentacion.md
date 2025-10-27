**Modelo de Despliegue**

<img width="2042" height="1364" alt="Diagrama de despliegue" src="https://github.com/user-attachments/assets/f4f89986-beb0-4bcc-b58c-83e248528a99" />

| Elemento | Descripción |
|-----------|-------------|
| **VPC AWS** | Red virtual que agrupa todos los recursos. |
| **Public Subnet** | Contiene las instancias EC2 accesibles (API, Worker, NFS). |
| **EC2 API** | Instancia que aloja la aplicación web (API REST). Recibe tráfico externo en 80/443. |
| **EC2 Worker** | Instancia dedicada al procesamiento asíncrono (sin acceso público). |
| **EC2 NFS Server** | Servidor de archivos compartido (almacenamiento común). |
| **DB Subnet (privada)** | Contiene la base de datos administrada (Amazon RDS). |
| **RDS** | Base de datos SQL (PostgreSQL/MySQL). |
| **SSH KeyPair** | Par de claves para acceso administrativo seguro (por SSH). |

La aplicación está compuesta por **cuatro servicios principales**:  
- **API REST (EC2)**: interfaz pública que atiende a los usuarios.  
- **Worker (EC2)**: ejecuta tareas asíncronas delegadas por la API.  
- **NFS Server (EC2)**: almacenamiento compartido.  
- **Base de Datos (RDS)**: persistencia transaccional.  

Todo opera dentro de una **VPC de AWS**, con **subred pública** para las instancias y **subred privada** para la base de datos.  
La comunicación está protegida mediante **Security Groups** que limitan el tráfico a los **puertos estrictamente necesarios**, asegurando un entorno controlado, modular y escalable.
