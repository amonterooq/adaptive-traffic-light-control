# Informe de validación

Fecha: 11 de noviembre de 2026. Plataforma: Windows, Python 3.12.9 de 64 bits.
Se ha probado la copia preparada para GitHub; los originales se mantienen intactos.

| Comprobación | Resultado y alcance |
| --- | --- |
| Instalación limpia | Entorno nuevo creado e instalación completa de `requirements-lock.txt` finalizada; pip utilizó paquetes de caché |
| Integridad de dependencias | `python -m pip check`: sin requisitos incompatibles |
| Versiones | Las 44 distribuciones fijadas coinciden con el inventario instalado |
| pytest | **111 aprobadas**, 0 fallos; 281,93 s |
| Integración SUMO | 30 casos de las 111 pruebas; incluyen laboratorio, Lusitania y Santa Eulalia |
| Ruff | Sin incidencias con `--select F` en programa, simulación, diagramas y ejemplo |
| Ejemplo breve nuevo | Fijo y adaptativo completados, demanda idéntica, 70/70 vehículos en cada ejecución, 0 colisiones y 0 teletransportes |
| Auditoría de datos originales | 246 ensayos de referencia + 18 cooperativos + 72 mixtos: aprobadas las tres auditorías |
| Correspondencia con memoria | 336 comparaciones y cifras principales contrastadas con el PDF y agregados; inspección visual del análisis de demanda alta |
| Backend HTTP | Arranque real con `programa/iniciar.py --port` y 13 rutas con HTTP 200; servidor temporal cerrado al terminar |
| Navegador | **102 comprobaciones** en seis guiones Playwright/Edge, todos con código 0; detalle en `validacion-web.json` y `pruebas-navegador.json` |
| Imágenes del README | Capturas reales revisadas visualmente; procedencia del acueducto confirmada por la autora |
| Enlaces relativos | Comprobación de existencia en README y demás Markdown |
| Código de producción original | Python, JavaScript de la aplicación, HTML, CSS y redes conservan sus bytes originales; se adapta una prueba de navegador |
| Secretos | Búsqueda estática por patrones en la selección de publicación; sin credenciales confirmadas |

## Evidencias

- [pytest JUnit](validacion-pytest.xml).
- [Auditoría de referencia](auditoria-principal.json),
  [cooperativa](auditoria-cooperativo.json) y [mixta](auditoria-mixto.json).
- [Backend y navegador](validacion-web.json).
- [Revisión de seguridad](seguridad.json).
- [Inventario de versiones y licencias](dependencias-licencias.json).

Las tres auditorías leen viajes y trazas originales, recalculan métricas y
comprueban huellas y demandas. No son nuevas ejecuciones de las 336 simulaciones.
En conjunto comprueban 234.426 viajes de vehículos y 18.176 viajes peatonales.
Las trazas originales quedan fuera del repositorio y pueden regenerarse con
los scripts de la entrega.

El ejemplo breve obtuvo 10,5186 s/vehículo con fijo y 9,4152 s/vehículo con
adaptativo. Es una comprobación funcional de una semilla y una duración corta,
no una nueva conclusión estadística ni una sustitución de las cifras académicas.

## Incidencias del entorno resueltas

La primera pasada de `browser_estudios.cjs` necesitaba un resumen dentro de
las trazas excluidas. Se añadió una lectura alternativa del mismo resumen en
`datos/procesados/resumenes_336.json`, sin cambiar la comparación de resultados.
La repetición de ese guion y el guion de interfaz finalizó correctamente.

La primera creación de entorno falló durante `ensurepip` dentro del entorno
restringido. Se repitió con autorización y terminó correctamente. La primera
ejecución de pytest produjo 49 aprobadas y 62 errores de preparación de
temporales; el ejemplo no pudo abrir el socket TraCI. La repetición autorizada
fuera de esa restricción completó las 111 pruebas y el ejemplo. Los errores
iniciales no se contabilizan como comprobaciones superadas ni motivaron cambios
en la lógica del proyecto.

El lanzador `py` de este equipo no detecta instalaciones, aunque Python 3.12.9
sí existe. La creación del entorno se ejecutó usando la ruta real del intérprete;
el README exige comprobar qué intérprete corresponde al comando `python`.

pytest produjo dos avisos de obsolescencia de dependencias: uso de HTTPX desde
Starlette TestClient y alias `anyio.abc.BlockingPortal`. No impidieron las pruebas.
Se conservan las versiones para reproducir la entrega; una actualización de
dependencias sería una tarea posterior con nueva validación.

## Seguridad y límites

No se incluyen SQLite, sesiones, `.env`, claves privadas, entornos ni archivos
administrativos. La búsqueda de rutas personales detectó el literal ficticio
`C:\\Users\\nombre\\carpeta_privada` de una prueba que verifica que la API no
expone rutas. Es un dato de prueba deliberado, no una ruta privada real.
La búsqueda por patrones no garantiza la ausencia de cualquier secreto posible.

No se hereda ningún historial Git: la fuente `03_Proyecto` no contiene `.git`
y la primera publicación debe crear un historial nuevo. No se debe ejecutar
`git add` desde la carpeta general de trabajo que contiene otros documentos.

No se ha comprobado instalación en Linux/macOS, despliegue multiusuario,
hardware real, tráfico real ni servicios radio. No se ha repetido la batería
completa de 336 simulaciones ni los seis diagnósticos largos adicionales.
Se entregan capturas reales; no se ha generado GIF o vídeo.

Tras la autorización de la autora se creó el repositorio privado y se verificó
el README renderizado, el diagrama Mermaid y las cuatro imágenes incrustadas
en GitHub. Tras una segunda autorización expresa se añadió MIT al código propio
y se cambió la visibilidad a pública. Véase [PUBLICACION.md](PUBLICACION.md).
