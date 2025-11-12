# 🤖 Automatic CM - Community Manager Automático

Aplicación web desarrollada en Django que permite a community managers gestionar comentarios de Reddit y YouTube, generando respuestas automáticas con IA y publicándolas directamente en las plataformas.

- Python 
- Ollama instalado (Abajo se explica el paso a paso para la instalación y verirficación)
  


## 🔧 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/DorianAlejandroGuisaoO/AUTOMATIC_CM.git
cd automatic_cm
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Instalar Ollama y modelo de IA (Importante para que funcione la IA)
```bash
# Instalar Ollama (https://ollama.com)
#https://ollama.com/download, Una vez se descargue el .exe, ejecutar el .exe como admin
# Luego descargar el modelo
ollama pull llama3
# Verificar que corra en el puerto http://localhost:11434
ollama serve

# Es importante que para poder usar "ollama" en la consola debe estar en el PATH del OS, al abirir el .exe como admin esto deberia hacerse solo, si no, reiniciar el PC o agregarlo al PATH manualmente,
```

### 5. Realizar migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear superusuario
```bash
python manage.py createsuperuser
```
### 7. Correr el server

```bash
python manage.py runserver
```

### 8. Ir a la vista de admin y logearse

```bash
python manage.py runserver
```


### 9. Ir a la vista de admin y logearse con el superuser

```bash
http://127.0.0.1:8000/admin/
```


### 10. Ir a la vista de reddit o YT

```bash
http://127.0.0.1:8000/dashboard/reddit/

o

http://127.0.0.1:8000/dashboard/youtube/
```

### 10. Sincronizar post y comentarios, y si se quiere crear posts (de reddit) o responder a los comentarios de un post con la IA (reddit y YT)


## 🛠️ Tecnologías

- **Backend:** Django 4.2
- **APIs:** PRAW (Reddit), YouTube Data API v3
- **IA:** Ollama (Llama 3)
- **Frontend:** HTML, CSS (Tailwind-inspired), JavaScript
- **Base de datos:** SQLite (desarrollo)


