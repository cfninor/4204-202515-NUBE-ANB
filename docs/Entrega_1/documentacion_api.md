# 📚 Documentación de la API — ANB Rising Stars Showcase

> Versión: `v1`  
> Base URL (local): `http://localhost:8000/api`  
> Autenticación: **JWT Bearer** (en endpoints protegidos)

---

## 🧭 Índice

1. 🔐 Autenticación
2. 🎬 Gestión de Videos (Privado)
3. 🌎 Público / Votaciones / Ranking
4. 🧾 Códigos de estado
5. 🧱 Seguridad (JWT)
6. 📎 Especificación resumida de endpoints

---

## 🔐 Autenticación

### POST `/api/auth/signup`
Registra un nuevo jugador.

**Body (JSON)**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "password1": "StrongPass123",
  "password2": "StrongPass123",
  "city": "Bogotá",
  "country": "Colombia"
}
```

**Responses**
- `201 Created` – Usuario creado.
- `400 Bad Request` – Validación (email duplicado / contraseñas no coinciden).

---

### POST `/api/auth/login`
Autentica y devuelve token JWT.

**Body (JSON)**
```json
{ "email": "john@example.com", "password": "StrongPass123" }
```

**Respuesta 200**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Errores**
- `401 Unauthorized` – Credenciales inválidas.

> **Nota:** La identidad del usuario se obtiene **exclusivamente** del JWT en el header `Authorization: Bearer <token>`; el cliente **no** envía email en endpoints autenticados.

---

## 🎬 Gestión de Videos (Privado)

> Todo endpoint de esta sección requiere `Authorization: Bearer <token>`.

### POST `/api/videos/upload`
Sube un video y **encola** su procesamiento asíncrono (recorte a 30s, 16:9 @ 720p, marca ANB, sin audio).

**Content-Type:** `multipart/form-data`  
**Campos**
- `video_file` (**file**, requerido) — MP4 (máx. 100 MB)
- `title` (**string**, requerido)

**Respuesta 201**
```json
{
  "message": "Video subido correctamente. Procesamiento en curso.",
  "task_id": "123456"
}
```

**Errores**
- `400 Bad Request` – Tipo/tamaño inválido.
- `401 Unauthorized` – Falta autenticación.

---

### GET `/api/videos`
Lista mis videos con su estado de procesamiento.

**Respuesta 200**
```json
[
  {
    "video_id": "123456",
    "title": "Mi mejor tiro de 3",
    "status": "processed",
    "uploaded_at": "2025-03-10T14:30:00Z",
    "processed_at": "2025-03-10T14:35:00Z",
    "processed_url": "http://localhost:8000/media/processed/123456.mp4"
  },
  {
    "video_id": "654321",
    "title": "Habilidades de dribleo",
    "status": "uploaded",
    "uploaded_at": "2025-03-11T10:15:00Z"
  }
]
```

**Errores**
- `401 Unauthorized`

---

### GET `/api/videos/{video_id}`
Detalle de un video del usuario autenticado.

**Respuesta 200**
```json
{
  "video_id": "a1b2c3d4",
  "title": "Tiros de tres en movimiento",
  "status": "processed",
  "uploaded_at": "2025-03-15T14:22:00Z",
  "processed_at": "2025-03-15T15:10:00Z",
  "original_url": "http://localhost:8000/media/uploads/a1b2c3d4.mp4",
  "processed_url": "http://localhost:8000/media/processed/a1b2c3d4.mp4",
  "votes": 125
}
```

**Errores**
- `401 Unauthorized`
- `403 Forbidden` – No es propietario.
- `404 Not Found` – No existe o no pertenece al usuario.

---

### DELETE `/api/videos/{video_id}`
Elimina un video propio (original y procesado) **solo si** no está publicado para votación.

**Respuesta 200**
```json
{ "message": "El video ha sido eliminado exitosamente.", "video_id": "a1b2c3d4" }
```

**Errores**
- `400 Bad Request` – No cumple condiciones (p. ej., ya publicado).
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`

---

## 🌎 Público / Votaciones / Ranking

### GET `/api/public/videos`
Lista videos públicos disponibles para votar.

**Respuesta 200**
```json
[
    {
        "video_id": 10000,
        "title": "Video_cnino",
        "user_id": 1,
        "processed_url": "/data/processed/10000.mp4",
        "votes": [
            {
                "id": 1,
                "video_id": 10000,
                "user_id": 1,
                "created_at": "2025-10-20T02:07:49.761323"
            }
        ],
        "status": "processed"
    }
]
```

---

### POST `/api/public/videos/{video_id}/vote`
Emite un voto por un video.  
**Auth:** `Bearer <token>`

**Respuesta 200**
```json
{ "message": "Voto registrado exitosamente." }
```

**Errores**
- `400 Bad Request` – Ya votó este video.
- `401 Unauthorized`
- `404 Not Found`

---

### GET `/api/public/rankings`
Ranking actual por votos (admite filtros y paginación, p. ej., `?city=Bogotá&page=1&size=20`).

**Respuesta 200**
```json
[
    {
        "position": 1,
        "username": "cnino",
        "city": "Bogota",
        "votes": 1
    }
]
```

> **Performance:** Usar **cache** (p. ej., Redis TTL 1–5 min) o **vista materializada** en PostgreSQL para rankings con alto volumen.

---

## 🧾 Códigos de estado (resumen)

| Código | Significado |
|---|---|
| 200 | OK |
| 201 | Creado / Tarea encolada |
| 400 | Error de validación / Regla de negocio |
| 401 | No autenticado |
| 403 | Prohibido |
| 404 | No encontrado |

---

## 🧱 Seguridad (JWT)
- Enviar `Authorization: Bearer <access_token>` en endpoints protegidos.
- El backend obtiene la identidad únicamente del token (no se envían emails en requests autenticadas).

---

## 📎 Especificación resumida de endpoints

| # | Método | Endpoint | Auth | Descripción |
|---|---|---|---|---|
| 1 | POST | `/api/auth/signup` | No | Registro |
| 2 | POST | `/api/auth/login` | No | Login (JWT) |
| 3 | POST | `/api/videos/upload` | Sí | Subir video (tarea asíncrona) |
| 4 | GET | `/api/videos` | Sí | Listar mis videos |
| 5 | GET | `/api/videos/{video_id}` | Sí | Detalle de mi video |
| 6 | DELETE | `/api/videos/{video_id}` | Sí | Eliminar mi video (si aplica) |
| 7 | GET | `/api/public/videos` | Opcional | Listar videos públicos |
| 8 | POST | `/api/public/videos/{video_id}/vote` | Sí | Votar video público |
| 9 | GET | `/api/public/rankings` | No | Ranking |
