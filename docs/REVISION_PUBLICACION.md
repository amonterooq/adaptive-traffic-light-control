# Revisión previa a la primera publicación

> Registro de la revisión previa, posteriormente aprobada por la autora.
> Se publicó primero en privado y después se autorizó MIT y la apertura pública:
> véase [PUBLICACION.md](PUBLICACION.md).
> El contenido siguiente conserva las decisiones presentadas antes de subir.

Estado: copia local preparada; **no publicada**. La autora pidió expresamente
aprobar el contenido antes de la primera subida y mantener inicialmente el
repositorio privado. La publicación y la licencia son decisiones separadas.

## Configuración propuesta

- Cuenta conectada y comprobada: `amonterooq`.
- Repositorio: `adaptive-traffic-light-control`.
- Visibilidad inicial: **privada**. No cambiar a pública sin autorización expresa.
- Descripción: `Adaptive traffic signal control and simulation using Python, SUMO, TraCI and FastAPI | Telematics Engineering Final Degree Project`.
- Temas: `python`, `sumo`, `traffic-simulation`, `intelligent-transportation-systems`,
  `adaptive-traffic-control`, `fastapi`, `traci`, `telematics`, `iot`.
- Historial: nuevo, sin importar el `.git` de la carpeta general ni inventar
  commits anteriores. Un commit inicial descriptivo es suficiente para esta entrega.

## Qué revisar

1. [README completo](../README.md), con estructura, instalación, arquitectura y resultados.
2. [Auditoría y decisiones](AUDITORIA.md).
3. [Validación técnica](VALIDACION.md) y sus evidencias.
4. [Listado exacto de archivos incluidos](INCLUIDOS.tsv).
5. [Listado de archivos del proyecto excluidos](EXCLUIDOS.tsv).
6. [Licencias y atribuciones](TERCEROS.md).
7. [Material de CV, LinkedIn e entrevistas](PORTFOLIO.md).

## Modificaciones realizadas

**No se modifica el código original de la aplicación**, sus redes,
importaciones ni dependencias Python. Se conserva su estructura funcional.

Se añade:

- README profesional en español y diagrama Mermaid editable.
- `.gitignore`, `.gitattributes` y `.python-version`.
- `examples/simulacion_breve.py`, comparación breve que evita sobrescribir una salida existente.
- Resúmenes compactos de las 336 ejecuciones y manifiestos originales.
- Informes de auditoría, validación, seguridad, autoría y material de portfolio.
- `programa/tests/package-lock.json`, generado al instalar las herramientas de navegador.

Se adapta una prueba de navegador, `programa/tests/browser_estudios.cjs`: si no
está el resumen entre las trazas brutas, lee la misma referencia del archivo
compacto de 336 resúmenes. Conserva las comparaciones de métricas y comprueba
que la referencia existe. No cambia el código de producción ni las pruebas Python.

Se modifica la documentación original `documentacion/REPRODUCCION.md`
para aclarar que las trazas masivas no se distribuyen y que `Proyecto` equivale
a la raíz del repositorio. `.gitattributes` evita normalizar los bytes originales
porque las auditorías científicas utilizan huellas SHA-256 de esos archivos.

## Exclusiones

El inventario TSV enumera cada exclusión dentro de `03_Proyecto`. También quedan
fuera del alcance de publicación los directorios administrativos y de defensa,
solicitudes, firmas, ZIP de entrega y memoria completa del directorio superior.
Los entornos y resultados nuevos de validación se guardan localmente y están
ignorados. Ninguno de estos archivos se ha borrado del original.

## Licencia

La autora confirmó ser la única titular, no conocer restricciones y autorizar
la imagen propia del acueducto. Se propone valorar **MIT para el código propio**,
manteniendo la cartografía ODbL y las condiciones de las dependencias.
La propuesta no está aplicada. Es posible hacer la primera subida privada sin
añadir licencia y decidirla después. No se concede autorización para reutilizar
material de terceros mediante una licencia general del proyecto.

## Después de la aprobación

Crear el repositorio privado, preparar el commit inicial solo con el inventario
revisado, subirlo, configurar descripción y temas, comprobar README, imágenes y
contenido remoto y entregar el enlace verificado. Si se autoriza la licencia,
actualizar sus avisos antes de subir. Una futura apertura pública requiere una
autorización expresa distinta.

El conector actual permite consultar la cuenta y trabajar con repositorios,
pero no expone una operación para crear repositorios o configurar sus temas.
Esa parte requerirá una sesión autorizada de GitHub en navegador u otra vía
disponible al publicar; no se ha probado todavía la capacidad de creación.
