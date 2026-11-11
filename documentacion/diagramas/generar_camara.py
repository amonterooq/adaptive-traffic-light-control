"""Diagrama editable de la adquisición con cámaras y V2I."""
from generar import diagram


if __name__=='__main__':
    diagram('fusion_camara','Vehículos conectados y detección desde la infraestructura',(900,460),[
        ('cam',25,85,230,80,['Cámara emulada','Tipo, posición y velocidad','Con omisiones configurables'],'#e8f2ec'),
        ('v2i',335,85,230,80,['Avisos V2I','Fracción de coches y motos','Distancia, velocidad e instante'],'#e8f2ec'),
        ('e2',645,85,230,80,['Sensores del cruce','Colas E2 y peatones','Disponibles sin V2I'],'#f8eedc'),
        ('fusion',180,255,265,75,['Fusión por identificador','Una aproximación por vehículo','ETA con velocidad observada'],'#e8f2ec'),
        ('control',605,255,265,75,['Control local','Colas y próximas llegadas','Fases y despeje peatonal'],'#f3f5f1')],
        [('cam','fusion','',[(140,165),(140,210),(290,210),(290,255)]),
         ('v2i','fusion','',[(450,165),(450,210),(355,210),(355,255)]),
         ('e2','control','',None),('fusion','control','ETA hasta 8 s',None)],
        ['Posiciones y detecciones proceden de SUMO. No se procesan imágenes ni mensajes radio reales.',
         'La clasificación no cambia el peso del vehículo; un objeto sin clasificar sigue contando.'])
