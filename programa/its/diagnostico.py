"""Informes de validez de una ejecución, sin rutas ni detalles privados del equipo."""
import json
import sqlite3


ERRORES = {
    'instalacion': 'No se encuentra un archivo o programa necesario para ejecutar la simulación.',
    'permisos': 'La aplicación no tiene permiso para leer o guardar los datos de la simulación.',
    'almacenamiento': 'No se han podido guardar las muestras en el historial local.',
    'configuracion': 'La configuración no es compatible con el modelo de simulación.',
    'simulador': 'El simulador se ha detenido antes de finalizar la ejecución.',
    'interrumpida': 'La ejecución quedó interrumpida al cerrarse el servidor.',
}


def error_publico(exc):
    if isinstance(exc, FileNotFoundError):
        codigo = 'instalacion'
    elif isinstance(exc, PermissionError):
        codigo = 'permisos'
    elif isinstance(exc, sqlite3.Error):
        codigo = 'almacenamiento'
    elif isinstance(exc, ValueError):
        codigo = 'configuracion'
    else:
        codigo = 'simulador'
    return {'error_code': codigo, 'error': ERRORES[codigo], 'completed': False}


def resumen_publico(summary):
    if not summary or not summary.get('error'):
        return summary
    result = dict(summary)
    codigo = result.get('error_code', 'simulador')
    if str(result['error']).startswith('Ejecución interrumpida por el cierre'):
        codigo = 'interrumpida'
    result['error_code'] = codigo if codigo in ERRORES else 'simulador'
    result['error'] = ERRORES[result['error_code']]
    return result


def informe(row):
    summary = resumen_publico(json.loads(row['summary_json'] or 'null')) or {}
    config = json.loads(row['config_json'])
    status = row['status']
    incidencias = []
    recomendaciones = []
    def incluir(tipo, cantidad, detalle):
        incidencias.append({'tipo': tipo, 'cantidad': cantidad, 'detalle': detalle})
    if summary.get('collisions'):
        incluir('colisiones', summary['collisions'],
                f"SUMO ha registrado {summary['collisions']} vehículos implicados en colisiones "
                '(conteo acumulado por paso). El ensayo queda excluido de las comparaciones.')
        recomendaciones.append('Revisar las conexiones, prioridades y fases del punto indicado en los eventos de colisión.')
    if summary.get('teleports'):
        incluir('teletransportes', summary['teleports'],
                'SUMO ha recolocado vehículos; sus recorridos no son válidos para comparar los controladores.')
    if summary.get('ped_conflicts'):
        incluir('conflictos_peatonales', summary['ped_conflicts'],
                'Se han detectado pasos de simulación con ocupación peatonal y autorización vehicular incompatibles.')
    pendientes = max(0, summary.get('generated', 0) - summary.get('arrived', 0))
    peatones = max(0, summary.get('ped_generated', 0) - summary.get('ped_arrived', 0))
    if pendientes or peatones:
        incluir('viajes_pendientes', pendientes + peatones,
                f'Quedan {pendientes} vehículos y {peatones} peatones sin completar su recorrido.')
        if status != 'cancelled':
            recomendaciones.append('La red no se ha vaciado dentro del tiempo máximo; revisar demanda y capacidad antes de comparar resultados.')
    if summary.get('error'):
        incluir(summary['error_code'], None, summary['error'])
        recomendaciones.append('Consultar la instalación y los pasos de ejecución de README.txt; conservar este informe para reproducir el fallo.')
    if status == 'cancelled':
        incluir('cancelacion', None, 'La ejecución se ha detenido desde la aplicación antes de finalizar.')
        recomendaciones.append('Repetir el estudio y dejar que finalice para obtener resultados comparables.')
    if status == 'failed' and not incidencias:
        incluir('incompleta', None, 'La ejecución no ha superado las comprobaciones de finalización del modelo.')
    apto = status == 'complete' and summary.get('completed') is True and not incidencias
    if apto:
        resumen = 'La ejecución ha finalizado y ha superado las comprobaciones de validez.'
    elif status == 'running':
        resumen = 'La simulación sigue en curso; todavía no se puede evaluar el resultado.'
    else:
        resumen = 'El ensayo no es válido para las comparaciones. ' + incidencias[0]['detalle'] if incidencias else 'No hay un resultado completo.'
    return {'id': row['id'], 'fecha': row['created_at'], 'status': status,
            'resumen': resumen, 'incidencias': incidencias, 'config': config,
            'recomendaciones': recomendaciones, 'apto_comparacion': apto,
            'eventos_colision': summary.get('collision_events', []),
            'model_version': summary.get('model_version')}
