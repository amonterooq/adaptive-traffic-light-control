"""Genera el estudio actualizado, su figura y las tablas urbanas desde los agregados."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analizar_mixto import tabla

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'datos/procesados'
NAMES={'lusitania':'Lusitania','santa_eulalia':'IES Santa Eulalia','laboratorio':'Laboratorio'}
METRICS=('mean_wait_s','ped_mean_wait_s','co2_mean_g')


def read(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def num(value):return f'{value:.2f}'.replace('.',',')
def percent(a,b):return 100*(b/a-1)
def direction(value):return 'aumenta' if value>0 else 'disminuye'


def main():
    long=read('movimientos_30min.json');mixed=read('mixto.json');old=read('historico_v1_6/mixto.json')
    co=read('multicruce.json');co_old=read('historico_v1_6/multicruce.json')
    output=ROOT/'docs/revision_movimientos';output.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,3,figsize=(11,6.7),layout='constrained')
    for row_index,row in enumerate(long['comparisons']):
        for col,(metric,label) in enumerate(zip(METRICS,('Espera vehicular (s)','Espera peatonal (s)','CO₂ de escape (g/veh.)'))):
            ax=axes[row_index,col];values=[row[m+'_'+metric] for m in ('fijo','adaptativo')]
            errors=[[values[i]-row[m+'_min_'+metric] for i,m in enumerate(('fijo','adaptativo'))],
                    [row[m+'_max_'+metric]-values[i] for i,m in enumerate(('fijo','adaptativo'))]]
            ax.bar(['Fijo','Adaptativo'],values,color=['#637d8e','#187565'],yerr=errors,capsize=4,width=.6)
            ax.set_title(NAMES[row['location']]+'\n'+label,fontsize=11)
            ax.spines[['top','right']].set_visible(False);ax.set_ylim(bottom=0)
            ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
            for i,value in enumerate(values):ax.text(i,value/2,num(value),ha='center',va='center',color='white',fontsize=10)
    fig.suptitle('Salida escolar · 30 minutos de llegadas\nMedia de tres semillas; barras de error: mínimo y máximo entre semillas',fontsize=13)
    fig.savefig(output/'comparacion_30min.png',dpi=170);fig.savefig(output/'comparacion_30min.svg');plt.close(fig)
    svg=output/'comparacion_30min.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    lines=['# Estudio actualizado del control semafórico','',f"Versión 1.7.1 · {long['date']}",'',
        '## Alcance de la revisión','',
        'Se mantienen los objetivos, la arquitectura ITS y el estudio del laboratorio. La corrección afecta a la regulación de Lusitania y Santa Eulalia. Se han vuelto a ejecutar **21 de los 336 ensayos**: nueve de adquisición cooperativa en Lusitania y doce de salida escolar en los dos emplazamientos. Los **315 ensayos de laboratorio** conservan exactamente sus resúmenes anteriores. Se añaden doce ensayos de treinta minutos, por lo que el estudio actual reúne **348 resultados**, de los cuales 33 se han ejecutado en esta revisión.','',
        'La memoria presentada no se reescribe. Los agregados originales se conservan en `datos/procesados/historico_v1_6`; el código anterior está en el commit `70f537a91d152af75ee40d79fe07a80c77a070e4`. Los agregados principales del repositorio y las tablas de la aplicación corresponden al programa actual.','',
        '## Qué cambia en el control','',
        'En Lusitania, una entrada permite recto e izquierda a la vez, además de derecha. Durante el turno completo del este pueden abrirse, por separado, las derechas del sur y del norte. Se emplean aperturas de seis segundos, amarillo y un despeje mínimo de dos segundos, prolongado si aún queda un vehículo de la apertura anterior. La derecha del norte cede al movimiento recto del este porque comparten salida. El turno adaptativo puede acabar antes de que se atiendan las dos aperturas; no se fuerza su duración para abrirlas siempre. Estos tiempos son hipótesis experimentales, no tiempos medidos en Mérida.','',
        'Los pasos peatonales se atienden individualmente junto con movimientos compatibles. Durante su servicio no se habilitan las derechas adicionales. En Santa Eulalia cada paso cierra únicamente su acceso y su salida. El laboratorio conserva su fase peatonal exclusiva. Las relaciones de cesión se han recalculado con netconvert, como indica la [documentación de SUMO](https://sumo.dlr.de/docs/Simulation/Traffic_Lights.html#interaction_between_signal_plans_and_right-of-way_rules).','',
        '## Comparación con los resultados anteriores','',
        'Para aislar el cambio de regulación se conservan duración, calentamiento, semillas, demanda, flota y reparto de giros. Se han comprobado las huellas de esas entradas y se han recalculado las esperas y el CO₂ a partir de los viajes de SUMO. Las tablas siguientes promedian las semillas 101, 102 y 103 con igual peso.','',
        '### Salida escolar corta: 180 s de llegadas y 30 s de calentamiento','',
        '| Lugar y control | Espera vehicular anterior → actual (s) | Espera peatonal anterior → actual (s) | CO₂ anterior → actual (g/veh.) |',
        '| --- | ---: | ---: | ---: |']
    for row in mixed['comparisons']:
        if row['location']=='laboratorio':continue
        previous=next(r for r in old['comparisons'] if r['location']==row['location'] and r['case']==row['case'])
        for mode in ('fijo','adaptativo'):
            lines.append('| '+NAMES[row['location']]+' · '+mode+' | '+' | '.join(num(previous[mode+'_'+k])+' → '+num(row[mode+'_'+k]) for k in METRICS)+' |')
    lines+=['','### Adquisición cooperativa en Lusitania: 180 s de llegadas','',
        'Control adaptativo, peatones frecuentes y 30 s de calentamiento. Estos casos no representan la salida escolar de la tabla anterior.','',
        '| Adquisición | Espera vehicular anterior → actual (s) | Espera peatonal anterior → actual (s) | CO₂ anterior → actual (g/veh.) |',
        '| --- | ---: | ---: | ---: |']
    profiles={'sensores':'Sensores','v2i50':'V2I 50 %','v2i100':'V2I 100 %'}
    for row in co['comparisons']:
        if row['location']!='lusitania':continue
        previous=next(r for r in co_old['comparisons'] if r['location']==row['location'] and r['profile']==row['profile'])
        lines.append('| '+profiles[row['profile']]+' | '+' | '.join(num(previous[k])+' → '+num(row[k]) for k in METRICS)+' |')
    lines+=['','## Comprobación de treinta minutos','',
        'Se comparan fijo y adaptativo con salida escolar, flota mixta, velocidades variables, cámara emulada y V2I al 50 %. Cada ensayo incluye 1800 s de llegadas, 300 s de calentamiento y vaciado de la red. La semilla es la misma dentro de cada pareja. Las doce ejecuciones han completado los viajes de vehículos y peatones sin colisiones, teletransportes ni conflictos peatonales registrados.','',
        '| Lugar | Vehículo fijo / adaptativo (s) | Peatón fijo / adaptativo (s) | CO₂ fijo / adaptativo (g/veh.) |',
        '| --- | ---: | ---: | ---: |']
    for row in long['comparisons']:
        lines.append('| '+NAMES[row['location']]+' | '+' | '.join(num(row['fijo_'+k])+' / '+num(row['adaptativo_'+k]) for k in METRICS)+' |')
    lines+=['','![Comparación de treinta minutos](revision_movimientos/comparacion_30min.png)','','## Interpretación','']
    for row in long['comparisons']:
        deltas=[percent(row['fijo_'+k],row['adaptativo_'+k]) for k in METRICS]
        lines.append(f"En **{NAMES[row['location']]}**, el control adaptativo {direction(deltas[0])} la espera vehicular un {num(abs(deltas[0]))} %, {direction(deltas[1])} la espera peatonal un {num(abs(deltas[1]))} % y {direction(deltas[2])} el CO₂ de escape por vehículo un {num(abs(deltas[2]))} % respecto al fijo, dentro de esta configuración escolar de treinta minutos.")
        lines.append('')
    lines+=['La corrección es relevante para las cifras urbanas: cambiar movimientos simultáneos y atención peatonal cambia la capacidad y el reparto de esperas. No invalida las comparaciones del laboratorio, pero impide utilizar las cifras urbanas antiguas para describir el código nuevo. Tampoco demuestra que el control adaptativo reduzca siempre las emisiones. La regla utiliza demanda y solicitudes, no optimiza directamente el CO₂.','',
        'Las pruebas cortas y largas responden a duraciones distintas y no se mezclan en una misma media. Tres semillas permiten una exploración, pero no una conclusión estadística general ni una estimación del tráfico real de Mérida. El CO₂ mide emisiones de escape dentro de la red; no incluye emisiones durante el retraso previo a la inserción, fabricación o electricidad. La espera vehicular sí incorpora ese retraso de inserción.','',
        '## Reproducción y archivos','',
        '```powershell',r'.\.venv\Scripts\python.exe simulacion/scripts/actualizar_estudio_movimientos.py --workers 3',
        r'.\.venv\Scripts\python.exe simulacion/scripts/analizar_movimientos.py','```','',
        'El primer script verifica o ejecuta los 33 ensayos de esta revisión y conserva los 315 resultados del laboratorio. Guarda cada ejecución bajo una carpeta identificada por el código del motor y sus redes para evitar reutilizar resultados de una lógica distinta. Los viajes masivos se generan localmente; el repositorio incluye configuraciones, resúmenes, CSV y figuras. En la aplicación, los dos estudios largos están en «7. Revisión urbana · treinta minutos».','',
        '- [Resultados cortos y cambios respecto al plan anterior](../datos/procesados/cambios_control.csv).',
        '- [Doce ensayos largos, configuraciones y resúmenes](../datos/procesados/movimientos_30min.json).',
        '- [Medias y rango entre semillas](../datos/procesados/movimientos_30min.csv).',
        '- [Comprobación de la revisión](../datos/procesados/revision_estudio.json).','']
    (ROOT/'docs/ESTUDIO_ACTUALIZADO.md').write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'documentacion/resultados/escolar_tabla.tex').write_text(tabla([r for r in mixed['comparisons'] if r['case']=='escolar'],True),encoding='utf-8')
    (ROOT/'documentacion/resultados/escolar_30min_tabla.tex').write_text(tabla(long['comparisons'],True),encoding='utf-8')
    table=[r'\begin{tabular}{llrrr}\toprule',r'Ubicación & Adquisición & Vehículo (s) & Peatón (s) & CO$_2$ (g/veh.)\\\midrule']
    for r in co['comparisons']:
        table.append(NAMES[r['location']]+' & '+profiles[r['profile']].replace('%',r'\%')+' & '+' & '.join(num(r[k]) for k in METRICS)+r'\\')
    table.append(r'\bottomrule\end{tabular}')
    (ROOT/'documentacion/resultados/multicruce_tabla.tex').write_text('\n'.join(table)+'\n',encoding='utf-8')


if __name__=='__main__':main()
