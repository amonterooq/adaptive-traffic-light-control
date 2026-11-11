1. REQUISITOS

Windows y Python 3.12 de 64 bits. La primera instalación necesita Internet.
SUMO y las demás dependencias se instalan al iniciar. Después se puede utilizar
la aplicación localmente.

2. INICIAR Y CERRAR

1) Extraer completamente el ZIP y entrar en la carpeta Proyecto.
2) Hacer doble clic en Iniciar aplicación.cmd.
3) Esperar a que termine la instalación. Se abrirá el navegador.
4) Mantener abierta la ventana del servidor mientras se utiliza la aplicación.

La dirección habitual es http://127.0.0.1:8765. Si está ocupada, el lanzador busca
otro puerto libre y abre su dirección. Si esta versión ya está funcionando,
abre la sesión existente.

Para cerrar el servidor, pulsar Ctrl+C en su ventana. Cerrar únicamente
el navegador mantiene el servidor en funcionamiento.

La instalación manual y las opciones de arranque están en
documentacion/REPRODUCCION.md.

3. PRIMERA SIMULACIÓN

1) Elegir el laboratorio, Lusitania o la rotonda del IES Santa Eulalia.
2) Seleccionar tráfico moderado, peatones frecuentes y dos minutos de llegadas.
3) Elegir un control y pulsar Iniciar simulación.
4) Usar Pausar/Continuar y el zoom para observar el cruce.
5) Pulsar un vehículo o peatón para ver sus datos; Desfijar cierra su ficha.
6) Esperar a Completada para consultar el resultado en el historial.

Los dos minutos indican el periodo de llegadas. Después se espera a que los
vehículos y peatones terminen sus recorridos. La velocidad de reproducción
(por ejemplo, 5x) acelera la visualización sin cambiar el experimento.

El control fijo cambia las luces con tiempos predefinidos. El adaptativo decide
según las colas y las solicitudes detectadas, respetando los tiempos de paso
y despeje. Para compararlos, repetir las mismas opciones y la misma semilla,
cambiando solo el control. El selector de estudios permite cargar esas opciones.

La demanda es simulada. Lusitania y Santa Eulalia parten de lugares de Mérida;
su regulación representa el modelo del proyecto. El CO2 mostrado es una
estimación de las emisiones de escape calculada por SUMO.

4. RESULTADOS

El historial guarda las opciones y métricas de cada ejecución y permite
descargar sus series en CSV. Se conserva en datos/sesiones/laboratorio.sqlite3.
Comparar resultados muestra las baterías de experimentos incluidas.

Si una simulación falla, Abrir informe muestra el motivo y permite descargar
el diagnóstico. Las ejecuciones detenidas o fallidas se conservan en el historial
con su estado y deben repetirse para obtener una comparación completa.

5. ORGANIZACIÓN

programa/       Aplicación, controladores, interfaz web y pruebas.
simulacion/     Redes SUMO, escenarios y scripts de experimentación.
datos/          Entradas, resultados y sesiones guardadas.
documentacion/  Guía de reproducción, diagramas, tablas, capturas e informes.

Para repetir los experimentos o ejecutar las pruebas:
    documentacion/REPRODUCCION.md

6. PROBLEMAS HABITUALES

- Python no se encuentra: comprobar que está instalado Python 3.12 de 64 bits.
- Falla la primera instalación: revisar la conexión y el mensaje de la consola.
  La guía de reproducción incluye los comandos de instalación manual.
- El navegador no conecta: comprobar que la ventana del servidor sigue abierta
  y utilizar la dirección que muestra.
- SUMO rechaza una ruta: extraer el proyecto en una ruta corta, como C:/TFG.
- Aparece un error durante el ensayo: consultar el informe de la aplicación
  antes de repetirlo.

Las fuentes de los datos se indican en datos/entrada/ATRIBUCION.md.
