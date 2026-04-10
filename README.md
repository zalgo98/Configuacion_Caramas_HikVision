# Camera Network Configurator

Aplicación de escritorio en Python/PySide6 para descubrir cámaras Hikvision en una red local, validar su estado, asignarlas a posiciones físicas, aplicar configuración básica y generar automáticamente un documento Word de asignación de IPs.

## Qué hace

- Detecta dispositivos en un rango de IP de la red local.
- Comprueba si los equipos responden como cámaras Hikvision por ISAPI.
- Valida y corrige el texto OSD esperado según operación, poste y posición.
- Permite asignar cámaras a un esquema visual de 6 posiciones.
- Aplica configuración final de cámara, audio, hora/NTP y snapshot.
- Abre el acceso web del router para apoyo durante la puesta en marcha.
- Genera un Word final con la tabla de cámaras y el diagrama de ubicación.

## Tecnologías

- Python 3
- PySide6
- requests
- python-docx
- lxml
- selenium
- python-vlc

## Estructura

```
app/
  discovery.py        # escaneo de red
  hikvision_api.py    # llamadas ISAPI y configuración de cámaras
  naming.py           # generación de nombres y RTSP
  positions.py        # posiciones del esquema
  router.py           # login al router
  settings.py         # configuración por variables de entorno
  workers.py          # tareas en segundo plano
ui/
  main_window.py      # pantalla principal
  assign_window.py    # asignación y aplicación final
fill_document.py      # relleno de la plantilla Word
main.pyw              # arranque de la aplicación
```

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Este repositorio está saneado para portfolio. Antes de usarlo, cambia los valores de credenciales y parámetros sensibles mediante variables de entorno o creando un `.env` a partir de `.env.example`.

Valores que debes revisar como mínimo:

- `CAMERA_USERNAME`
- `CAMERA_PASSWORD`
- `ROUTER_USERNAME`
- `ROUTER_PASSWORD`
- `PLATFORM_HOST`
- `PLATFORM_VERIFICATION_CODE`

Los valores incluidos en el repositorio son placeholders:

- usuario: `tu_Usuario`
- contraseña: `Tu_Contraseña`

## Uso

1. Ejecuta la aplicación.
2. Introduce operación y poste.
3. Pulsa **Buscar cámaras**.
4. Revisa las cámaras detectadas y asigna cada una a su posición.
5. Valida la asignación y aplica la configuración final.
6. El documento Word generado se guardará en la misma carpeta donde esté la plantilla usada.

## Plantilla Word

El proyecto incluye una plantilla pública: `Asignacion_IPs_template_publica.docx`.

Si quieres usar otra plantilla, colócala junto a la aplicación con uno de estos nombres:

- `Asignacion_IPs_template_publica.docx`
- `Asignacion de IPs.docx`
- `Asignación de IPs.docx`

## Seguridad y publicación

Antes de subir esta clase de herramientas a GitHub conviene revisar:

- credenciales embebidas
- ficheros temporales y `__pycache__`
- metadatos de documentos Office
- nombres internos de cliente, operación o infraestructura
- logs o ejemplos con datos reales

En esta versión se han eliminado los rastros privados detectados y se han sustituido por valores genéricos.

## Nota

Este proyecto se publica como muestra técnica. Adáptalo a tu entorno antes de usarlo en producción.
