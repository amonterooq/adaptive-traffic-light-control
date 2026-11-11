# Autoría, recursos y dependencias

Revisión: 11 de noviembre de 2026. La autora ha confirmado ser la única titular
del proyecto y no conocer restricciones de publicación. Ha confirmado que
`programa/web/assets/acueducto-merida.png` es propia y ha autorizado incluirla.
Esta confirmación no equivale a aplicar una licencia de software.

## Contenido que se distribuye

- Código y documentación del proyecto: Ana Montero Preciado. Licencia pendiente.
- Imagen del acueducto: obra propia, inclusión autorizada por la autora.
- Capturas de la aplicación y gráficos del proyecto: conservados desde la entrega.
- Cartografía y redes derivadas: © OpenStreetMap contributors, ODbL 1.0.
  Se conserva [ATRIBUCION.md](../datos/entrada/ATRIBUCION.md) y la atribución visible
  en la interfaz. Los parámetros operativos y la demanda son sintéticos.
- No se redistribuyen documentos administrativos, logotipos de la plantilla
  académica, artículos completos ni el PDF de la memoria.

OpenStreetMap exige atribución e identificación de la licencia de sus datos;
su licencia no se reemplaza por la futura licencia del código.
Fuentes: [OSM Copyright](https://www.openstreetmap.org/copyright) y
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

## Dependencias instaladas, no incorporadas como código del repositorio

El [inventario completo](dependencias-licencias.json) contiene las 44 distribuciones
del archivo de versiones, sus versiones instaladas, metadatos de licencia y
enlaces declarados por cada distribución. Se obtuvo del entorno local que
coincide con las versiones de la entrega. Los paquetes y sus binarios se
instalan con pip; `.venv` no se publica.

| Dependencia | Información de licencia |
| --- | --- |
| Eclipse SUMO, sumo-data, TraCI, sumolib | EPL-2.0 o GPL-2.0-or-later según sus metadatos |
| FastAPI, Pydantic, Ruff, pytest | MIT |
| Uvicorn, Starlette, HTTPX | BSD-3-Clause |
| NumPy | Metadatos con BSD-3-Clause y licencias adicionales de componentes |
| SciPy | Condiciones BSD y avisos de componentes en la distribución |
| Matplotlib | Acuerdo propio; texto completo en metadatos |
| ReportLab | BSD, según metadatos |
| PyMuPDF | AGPL-3.0 o licencia comercial de Artifex |
| certifi | MPL-2.0 |
| SQLite, biblioteca de Python | Dominio público según SQLite |
| Playwright 1.62.1, herramientas de navegador | Apache-2.0 según el package-lock instalado; no se publica node_modules |

No todas las dependencias del lock son necesarias para el servidor: se conserva
el entorno académico completo para no alterar la reproducción. PyMuPDF y otras
herramientas de autoría no deben confundirse con código propio. Antes de distribuir
un ejecutable que las incorpore o elegir la licencia definitiva, debe revisarse
esa composición. Aquí no se distribuye un ejecutable empaquetado.

Fuentes oficiales comprobadas: [licencias SUMO](https://sumo.dlr.de/docs/Libraries_Licenses.html),
[FastAPI](https://fastapi.tiangolo.com/) y [SQLite](https://www.sqlite.org/copyright.html).
El inventario es una revisión técnica de procedencia y metadatos, no una
resolución jurídica de compatibilidad para cualquier forma de distribución.

## Decisión pendiente sobre el código

Se puede valorar MIT para el código propio si la autora quiere permitir su
reutilización con atribución y sin garantía. No se aplica ni se añade `LICENSE`
sin autorización expresa. La futura licencia debe delimitar código propio,
datos OSM, imágenes y dependencias, manteniendo sus avisos respectivos.
