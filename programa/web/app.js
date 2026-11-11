"use strict";
const $ = id => document.getElementById(id);
const labels = {bajo:'Baja',medio:'Media',alto:'Alta',desequilibrado:'Desigual',dinamico:'Cambiante',escolar:'Escolar'};
const pedLabels = {desactivado:'Sin pasos',sin:'Sin llegadas',ocasional:'Ocasional',frecuente:'Frecuente',lento:'Marcha lenta',escolar:'Salida escolar'};
const statuses = {idle:'En espera',running:'En curso',complete:'Completada',cancelled:'Cancelada',failed:'Error'};
const arms = ['N','E','S','W'];
const armNames = ['Norte','Este','Sur','Oeste'];
const locationNames={lusitania:'Lusitania',laboratorio:'Laboratorio',santa_eulalia:'Reina Sofía · IES Santa Eulalia'};
const locationName=id=>locationNames[id||'laboratorio']||id;
const reasons = {prioridad_anillo:'Cesión de paso a la circulación del anillo',inicio:'Inicio',despeje:'Despeje de la intersección',eje_alterno:'Paso al eje opuesto',verde_maximo:'Verde máximo alcanzado',demanda_opuesta:'Cola del eje opuesto',respaldo_temporizado:'Respaldo por falta de datos',temporizacion_fija:'Fin del verde fijo'};
Object.assign(reasons,{despeje_peatonal:'Despeje peatonal',cruce_despejado:'Cruce peatonal libre',servicio_peatonal:'Paso exclusivo para peatones',espera_despeje_vehicular:'Esperando a que salgan los vehículos',solicitud_peatonal:'Atención a solicitud de paso'});
let trace=[],lastRun=null,lastStatus=null,viewHistory=false,mapView=[0,0,1800,1500],activeRun=false;
let mapDefault=[0,0,1800,1500];
let reportRequest=0,reportRun=null;
const fmt = (v,n=1) => v==null?'—':Number(v).toLocaleString('es-ES',{minimumFractionDigits:n,maximumFractionDigits:n});
const minutes = t => `${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;

async function api(url, options){
  const response=await fetch(url,options);
  if(!response.ok){let message='No se pudo completar la solicitud';try{const err=await response.json();message=typeof err.detail==='string'?err.detail:'Revisa los parámetros introducidos';}catch{}throw new Error(message);}
  return response.json();
}
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
function clearReport(){reportRequest++;reportRun=null;$('run-report').hidden=true;$('run-report').open=false;$('scene-incident').hidden=true;}
async function showRunReport(id,open=false){
  const request=++reportRequest;reportRun=id;
  const panel=$('run-report');panel.hidden=false;panel.open=open;
  $('report-summary').textContent='Cargando el informe…';
  $('report-incidents').replaceChildren();$('report-recommendations').replaceChildren();
  $('report-config').textContent='';$('report-download').hidden=true;$('report-retry').hidden=true;
  try{
    const report=await api(`/api/runs/${encodeURIComponent(id)}/diagnostico`);
    if(request!==reportRequest)return;
    $('report-summary').textContent=report.resumen;
    for(const incident of report.incidencias){const item=document.createElement('li');item.textContent=incident.detalle;$('report-incidents').append(item);}
    for(const recommendation of report.recomendaciones){const item=document.createElement('li');item.textContent=recommendation;$('report-recommendations').append(item);}
    const c=report.config||{};
    $('report-config').textContent=`${locationName(c.location)} · ${labels[c.scenario]||'Escenario sin iniciar'} · ${c.mode==='fijo'?'Tiempos fijos':'Control adaptativo'} · semilla ${c.seed??'—'} · ${fmt(c.horizon/60,0)} min de llegadas. ${report.apto_comparacion?'Recorridos completos y comprobaciones superadas.':'Resultado excluido de las comparaciones.'}`;
    $('report-download').href=`/api/runs/${encodeURIComponent(id)}/diagnostico?descargar=true`;
    $('report-download').hidden=false;
  }catch(error){
    if(request!==reportRequest)return;
    $('report-summary').textContent='No se pudo recuperar el informe. '+error.message;
    $('report-retry').hidden=false;
  }
}
$('report-retry').onclick=()=>{if(reportRun)showRunReport(reportRun,true);};
$('scene-report').onclick=()=>{$('run-report').open=true;$('run-report').scrollIntoView({behavior:'smooth',block:'center'});};
function element(tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;return e;}
function project([lon,lat]){return[(lon+6.350)*78000,(38.927-lat)*100000];}
function applyView(){$('map').setAttribute('viewBox',mapView.join(' '));}
function zoom(factor){const[x,y,w,h]=mapView;const nw=Math.max(150,Math.min(4500,w*factor));const nh=h*nw/w;mapView=[x+(w-nw)/2,y+(h-nh)/2,nw,nh];applyView();}

async function initMap(){
  const selected=$('location').value;const data=await api('/api/map?location='+selected);if(selected!==$('location').value)return;for(const id of ['map-features','map-labels','map-marker'])$(id).replaceChildren();
  const roads=[],areas=[],names=new Set();
  for(const f of data.features){
    const p=f.properties,poly=f.geometry.type==='Polygon';
    const c=poly?f.geometry.coordinates[0]:f.geometry.coordinates;
    const points=c.map(project);if(points.length<2)continue;
    const d=points.map((a,i)=>`${i?'L':'M'}${a[0].toFixed(2)},${a[1].toFixed(2)}`).join(' ')+(poly?' Z':'');
    if(poly){areas.push(element('path',{d,fill:p.natural==='water'?'#b7d6d2':p.leisure||p.landuse==='forest'?'#d1dfc6':'#e0e8d8',stroke:'none'}));}
    else if(p.highway){
      const major=['primary','secondary','tertiary'].includes(p.highway),minor=['footway','path','steps','cycleway'].includes(p.highway);
      roads.push(element('path',{d,fill:'none',stroke:major?'#c2cdbb':'#d5ddce','stroke-width':major?12:minor?2:7,'stroke-linejoin':'round'}));
      roads.push(element('path',{d,fill:'none',stroke:major?'#fffcf0':minor?'#edf0e6':'#f8faef','stroke-width':major?9:minor?1:4,'stroke-linejoin':'round'}));
      if(major&&p.name&&!names.has(p.name)&&points.length>4){names.add(p.name);const m=points[Math.floor(points.length/2)];$('map-labels').append(element('text',{x:m[0]+5,y:m[1]-12,fill:'#71836c','font-size':14,'font-family':'Segoe UI, Arial',stroke:'#f4f7ed','stroke-width':3,'paint-order':'stroke'},p.name));}
    }else if(p.waterway)areas.push(element('path',{d,fill:'none',stroke:'#b7d6d2','stroke-width':10}));
  }
  $('map-features').append(...areas,...roads);
  const centers={lusitania:[-6.3370584,38.910752],laboratorio:[-6.332157,38.9214575],santa_eulalia:[-6.337872646,38.911919954]};
  const [x,y]=project(centers[$('location').value]);
  if(selected!=='laboratorio')$('map-marker').append(element('circle',{cx:x,cy:y,r:45,fill:'#167266',opacity:'.1'}),element('circle',{cx:x,cy:y,r:27,fill:'#167266',stroke:'#fff','stroke-width':5}),element('text',{x,y:y+6,'text-anchor':'middle',fill:'white','font-size':17,'font-weight':700},'J1'));
  $('map-marker').setAttribute('tabindex',selected==='laboratorio'?'-1':'0');
  const span=$('location').value!=='laboratorio'?350:680;mapDefault=[x-span,y-span,span*2,span*2];mapView=[...mapDefault];applyView();
}
$('zoom-in').onclick=()=>zoom(.7);$('zoom-out').onclick=()=>zoom(1.4);$('recenter').onclick=()=>{mapView=[...mapDefault];applyView();};
$('map-marker').onclick=()=>{$('traffic-scene').scrollIntoView({behavior:'smooth',block:'center'});window.sceneView.recenter();};
$('map-marker').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('map-marker').onclick();}};
let drag=null;
$('map').addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,v:[...mapView]};$('map').setPointerCapture(e.pointerId);});
$('map').addEventListener('pointermove',e=>{if(!drag)return;const rect=$('map').getBoundingClientRect();mapView=[drag.v[0]-(e.clientX-drag.x)*drag.v[2]/rect.width,drag.v[1]-(e.clientY-drag.y)*drag.v[3]/rect.height,drag.v[2],drag.v[3]];applyView();});
$('map').addEventListener('pointerup',()=>drag=null);$('map').addEventListener('pointercancel',()=>drag=null);

for(const [i,a]of arms.entries()){
  const card=document.createElement('div');card.className='arm';
  card.innerHTML=`<div><span class="arm-name">${armNames[i]}</span><span class="state-word" id="word-${a}">Sin datos</span></div><b id="q-${a}">—</b><span class="lamp" id="lamp-${a}"></span>`;
  $('arms').append(card);
}
function draw(){
  const canvas=$('queue-chart'),rect=canvas.getBoundingClientRect();if(!rect.width)return;
  const ratio=window.devicePixelRatio||1;canvas.width=rect.width*ratio;canvas.height=rect.height*ratio;
  const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);const w=rect.width,h=rect.height,l=35,r=12,top=10,b=27;
  const max=Math.max(10,...trace.map(s=>s.queue_total||0));ctx.font='10px Segoe UI';
  for(let i=0;i<=3;i++){const y=top+(h-top-b)*i/3;ctx.strokeStyle='#e9ede6';ctx.beginPath();ctx.moveTo(l,y);ctx.lineTo(w-r,y);ctx.stroke();ctx.fillStyle='#718078';ctx.fillText(Math.round(max*(1-i/3)),2,y+3);}
  if(trace.length<2){ctx.fillStyle='#839086';ctx.fillText('Esperando muestras de la simulación',l+14,h/2);return;}
  const first=trace[0].t,last=trace.at(-1).t;
  const points=trace.map(s=>[l+(w-l-r)*(s.t-first)/(last-first||1),top+(h-top-b)*(1-s.queue_total/max)]);
  ctx.beginPath();ctx.moveTo(l,h-b);for(const[x,y]of points)ctx.lineTo(x,y);ctx.lineTo(w-r,h-b);ctx.closePath();ctx.fillStyle='#e7f1e9';ctx.fill();
  ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.strokeStyle='#167266';ctx.lineWidth=2;ctx.stroke();
  ctx.fillStyle='#718078';ctx.fillText(`${minutes(first)} sim.`,l,h-5);ctx.textAlign='right';ctx.fillText(`${minutes(last)} sim.`,w-r,h-5);
}
window.addEventListener('resize',draw);

function renderSample(s){
  renderCooperative(s);
  $('ped-state').textContent=s.ped_signal==null?'Red sin pasos':s.ped_signal==='G'?'Puede iniciar el cruce':s.ped_stage==='ped_clear'?'Despeje · no iniciar cruce':'Espere';
  $('ped-lamp').className='lamp '+(s.ped_signal==null?'':s.ped_signal==='G'?'green':'red');
  $('ped-waiting').textContent=fmt(s.ped_waiting,0);$('ped-crossing').textContent=fmt(s.ped_crossing,0);
  $('metric-queue').textContent=fmt(s.queue_total,0);$('metric-network').textContent=fmt(s.in_network,0);$('metric-arrived').textContent=fmt(s.arrived_total,0);$('metric-time').textContent=minutes(s.t);
  $('metric-period').textContent=s.draining?'Vaciado de la red':s.t<s.warmup?'Periodo de calentamiento':'Periodo de medida';
  for(const [i,a]of arms.entries()){
    $('q-'+a).textContent=s['q_'+a];const code=s.state[i],cls=['G','g'].includes(code)?'green':code==='y'?'yellow':'red';
    $('lamp-'+a).className='lamp '+cls;$('word-'+a).textContent=cls==='green'?'Verde':cls==='yellow'?'Amarillo':'Rojo';
  }
  $('phase-time').textContent=s.elapsed==null?'':`${s.elapsed} s de fase`;
  $('sample-age').textContent=s.sample_age==null?'Sin muestra':`${s.sample_age} s simulados`;
  $('effective-mode').textContent=s.fallback?'Respaldo fijo':s.mode==='fijo'?'Temporización fija':s.camera_active?'Colas + cámara + V2I disponible':s.sensing_mode==='hybrid'?'Colas + aproximaciones V2I':'Adaptación por colas';
  $('decision').textContent=reasons[s.reason]||'Serie histórica';
  if(s.fallback)notice('Muestras obsoletas. El controlador utiliza temporización de respaldo.',true);
}
function clearSample(preparing=true){
  renderCooperative(null);
  $('ped-state').textContent='Sin datos';$('ped-lamp').className='lamp';$('ped-waiting').textContent='—';$('ped-crossing').textContent='—';
  for(const id of ['metric-queue','metric-network','metric-arrived'])$(id).textContent='0';
  $('metric-time').textContent='00:00';$('metric-period').textContent=preparing?'Preparando ejecución':'Sin ejecución activa';
  for(const a of arms){$('q-'+a).textContent='—';$('lamp-'+a).className='lamp';$('word-'+a).textContent='Sin datos';}
  for(const id of ['phase-time','sample-age','effective-mode','decision'])$(id).textContent='—';
  trace=[];draw();
}
async function poll(){
  try{
    const data=await api('/api/state');$('connection').textContent='Servidor conectado';$('connection-dot').className='dot online';
    $('run-status').textContent=data.paused&&data.status==='running'?'En pausa':statuses[data.status]||data.status;
    const running=data.status==='running';$('start').disabled=running;$('stop').disabled=!running;
    activeRun=running;$('location').disabled=running;syncPointSelection();
    document.querySelectorAll('#run-form select:not(#speed), #run-form input').forEach(e=>e.disabled=running);
    if(running&&document.activeElement!==$('speed'))$('speed').value=String(data.speed);
    if(data.id!==lastRun){
      lastRun=data.id;lastStatus=null;clearSample(running);clearReport();viewHistory=false;
      if(window.sceneView)window.sceneView.lastSampleTime=null;
      if(running&&data.config){
        for(const [id,key]of [['location','location'],['scenario','scenario'],['mode','mode'],['pedestrian-profile','pedestrian_profile'],['seed','seed'],['horizon','horizon']])$(id).value=String(data.config[key]??(key==='location'?'laboratorio':''));
        $('min-green').value=data.config.timing.min_green;$('max-green').value=data.config.timing.max_green;$('fixed-green').value=data.config.timing.fixed_green;$('outage-start').value=data.config.outage_start??60;$('outage-end').value=data.config.outage_end??90;$('outage').checked=data.config.simulate_outage;
        const sensing=data.config.sensing||{};$('sensing-mode').value=sensing.mode||'sensors';
        for(const [id,key,fallback]of [['penetration','penetration',50],['v2x-range','range_m',120],['v2x-latency','latency_s',1],['v2x-loss','loss_percent',0]])$(id).value=String(sensing[key]??fallback);
        $('sensing-mode').onchange();
        $('fleet').value=data.config.traffic?.fleet||'coches';$('traffic-speeds').value=data.config.traffic?.speeds||'uniforme';
        $('camera-enabled').checked=data.config.camera?.enabled||false;
        $('camera-missed').value=String(data.config.camera?.missed_percent||0);$('camera-unknown').value=String(data.config.camera?.unclassified_percent||0);
        updateTrafficHelp();
        $('mode').onchange();$('pedestrian-profile').onchange();
      }
    }
    if(data.sample&&!viewHistory&&!window.sceneView?.preview){if(!window.sceneView?.frames.length)renderSample(data.sample);if(trace.at(-1)?.t!==data.sample.t){trace.push(data.sample);if(trace.length>1000)trace.shift();draw();}}
    if(data.status!==lastStatus){
      lastStatus=data.status;
      if(data.status==='complete'){notice(`Ejecución completada. Espera media: vehículos ${fmt(data.summary?.mean_wait_s)} s; peatones ${fmt(data.summary?.ped_mean_wait_s)} s. CO₂ de escape: ${fmt(data.summary?.co2_mean_g)} g/vehículo. Todos los recorridos han finalizado.`);loadHistory();}
      if(data.status==='cancelled'){notice('Ejecución detenida. Se conserva la serie parcial, excluida de la comparación experimental.');if(data.id)showRunReport(data.id);loadHistory();}
      if(data.status==='failed'){const summary=data.summary||{};const causes=[];if(summary.collisions)causes.push(`${summary.collisions} vehículos implicados en colisión (conteo acumulado)`);if(summary.teleports)causes.push(`${summary.teleports} teletransportes`);if(summary.ped_conflicts)causes.push(`${summary.ped_conflicts} conflictos peatonales`);notice(summary.error||(causes.length?`Ensayo no válido: ${causes.join(', ')}. Se conservan los datos, pero se excluye de las comparaciones.`:'Ejecución incompleta: consulta el informe para conocer el motivo.'),true);if(data.id)showRunReport(data.id);$('scene-incident-message').textContent=$('notice').textContent;$('scene-incident').hidden=false;loadHistory();}
    }
    if(data.paused&&running){$('freshness').textContent='Tiempo simulado detenido por el usuario.';notice('En pausa. Pulsa Continuar en la vista del cruce para seguir.');}
    else if(running&&data.transport_age_s>5)$('freshness').textContent='La simulación lleva más de 5 s reales sin entregar un estado nuevo.';
    else $('freshness').textContent='Posiciones de SUMO cada segundo simulado. La vista suaviza el movimiento entre muestras recibidas.';
    if(running&&!data.paused&&data.sample&&!data.sample.fallback)notice(data.sample.draining?'Ya no se generan nuevas llegadas. Esperamos a que todos terminen su recorrido.':'En marcha. Puedes pausar, cambiar la velocidad o ampliar el cruce.');
  }catch(e){$('connection').textContent='Sin conexión';$('connection-dot').className='dot offline';notice('No se puede contactar con el servidor. Los valores visibles son el último estado recibido.',true);}
  finally{setTimeout(poll,500);}
}
$('run-form').onsubmit=async e=>{
  e.preventDefault();const min=Number($('min-green').value),max=Number($('max-green').value);
  if(min>max){notice('El verde mínimo no puede superar el máximo.',true);return;}
  const config={location:$('location').value,scenario:$('scenario').value,mode:$('mode').value,seed:Number($('seed').value),speed:Number($('speed').value),horizon:Number($('horizon').value),timing:{min_green:min,max_green:max,fixed_green:Number($('fixed-green').value)},simulate_outage:$('outage').checked,outage_start:Number($('outage-start').value),outage_end:Number($('outage-end').value),pedestrian_profile:$('pedestrian-profile').value,
    sensing:{mode:$('sensing-mode').value,penetration:Number($('penetration').value),range_m:Number($('v2x-range').value),latency_s:Number($('v2x-latency').value),loss_percent:Number($('v2x-loss').value)},
    traffic:{fleet:$('fleet').value,speeds:$('traffic-speeds').value,emissions:true},
    camera:{enabled:$('camera-enabled').checked,range_m:80,missed_percent:Number($('camera-missed').value),unclassified_percent:Number($('camera-unknown').value)}};
  $('start').disabled=true;viewHistory=false;clearReport();
  try{await api('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});clearSample();$('chart-caption').textContent='Muestras de la ejecución actual.';notice('Preparando el escenario en SUMO…');$('traffic-scene').scrollIntoView({behavior:'smooth',block:'center'});}
  catch(err){notice(err.message,true);$('start').disabled=false;}
};
$('stop').onclick=async()=>{try{await api('/api/stop',{method:'POST'});notice('Deteniendo y guardando las muestras…');}catch(e){notice(e.message,true);}};
$('pause').onclick=async()=>{
  try{const result=await api('/api/playback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!window.sceneView.paused})});window.sceneView.paused=result.paused;}
  catch(e){notice(e.message,true);}
};
$('speed').onchange=async()=>{
  if(activeRun)try{await api('/api/playback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({speed:Number($('speed').value)})});}catch(e){notice(e.message,true);}
};
$('mode').onchange=()=>{$('mode-help').textContent=$('mode').value==='fijo'?`Alterna tiempos predefinidos: ${$('fixed-green').value} segundos de verde por eje. Con pasos, reserva una fase para peatones.`:'Decide cuándo cambiar según los coches en cola y las solicitudes de los peatones.';};
$('pedestrian-profile').onchange=()=>{
  const value=$('pedestrian-profile').value;
  const help={escolar:'Concentración en el tercio central del ensayo: 720 personas/h en N y S y 120 en E y O. Hipótesis de laboratorio, sin horario ni aforo escolar real.',frecuente:'Llegan personas con frecuencia: 180 por hora y paso. Puedes verlas esperar y cruzar.',ocasional:'Llegan pocas personas: 30 por hora y paso. Puede haber intervalos sin peatones.',lento:'Las personas caminan a 0,8 m/s. El controlador espera a que terminen de cruzar.',sin:'Los pasos existen, pero no llegan personas durante esta simulación.',desactivado:'Red de referencia solo para coches: se retiran los pasos y las aceras del modelo.'};
  $('ped-help').textContent=help[value];
  if(!activeRun){window.sceneView.showPreview(value!=='desactivado',$('location').value);clearSample(false);}
};
async function loadHistory(){
  try{
    const runs=await api('/api/runs'),body=$('history-body');body.replaceChildren();
    if(!runs.length){const tr=body.insertRow();const td=tr.insertCell();td.colSpan=12;td.textContent='Todavía no hay ejecuciones guardadas.';return;}
    for(const row of runs){
      const tr=body.insertRow();const values=[new Date(row.created_at).toLocaleString('es-ES'),locationName(row.config?.location),labels[row.scenario]+(row.config?.traffic?.fleet==='mixto'?' · mixto':'')+(row.config?.camera?.enabled?' · cámara':''),pedLabels[row.config?.pedestrian_profile||'desactivado'],(row.mode==='fijo'?'Fijo':'Adaptativo')+' · '+(row.config?.sensing?.mode==='hybrid'?'V2I '+row.config.sensing.penetration+' %':'sensores'),row.seed,fmt(row.config?.horizon/60,0)+' min',statuses[row.status],row.status==='complete'?fmt(row.summary?.mean_wait_s)+' s':'—',row.status==='complete'&&row.summary?.ped_mean_wait_s!=null?fmt(row.summary.ped_mean_wait_s)+' s':'—',row.status==='complete'&&row.summary?.co2_mean_g!=null?fmt(row.summary.co2_mean_g)+' g/veh.':'—'];
      values.forEach(v=>{tr.insertCell().textContent=v;});
      const td=tr.insertCell(),button=document.createElement('button');button.textContent='Ver serie';button.onclick=async()=>{
        const samples=await api(`/api/runs/${row.id}/samples`);viewHistory=true;trace=samples.map(s=>({...s,q_N:s.q_n,q_E:s.q_e,q_S:s.q_s,q_W:s.q_w,queue_total:s.q_n+s.q_e+s.q_s+s.q_w}));draw();$('chart-caption').textContent=`Histórico: ${locationName(row.config?.location)}, ${labels[row.scenario]}, ${row.mode}, semilla ${row.seed}. ${samples.length} muestras.`;
        $('queue-chart').scrollIntoView({behavior:'smooth',block:'center'});
      };td.append(button);const a=document.createElement('a');a.href=`/api/runs/${row.id}/export`;a.textContent='CSV';td.append(a);
      if(['failed','cancelled'].includes(row.status)){const report=document.createElement('button');report.textContent='Ver informe';report.onclick=async()=>{await showRunReport(row.id,true);$('run-report').scrollIntoView({behavior:'smooth',block:'center'});};td.append(report);}
    }
  }catch(e){notice(e.message,true);}
}
$('refresh-history').onclick=loadHistory;
async function loadResults(){
  const mixed=await api('/api/results/mixed');$('mixed-results-body').replaceChildren();
  const cases={coches:'Solo coches',mixto:'Tráfico mixto sin peatones',peatones:'Con peatones',velocidades:'Distintas velocidades',exceso:'Ensayo 30/50/70',omisiones:'Cámara omite 30 %',sin_clasificar:'Sin clasificación',sin_camara:'Cámara sin detecciones',v2i50:'Cámara y V2I 50 %',escolar:'Salida escolar'};
  for(const row of mixed.comparisons){const tr=$('mixed-results-body').insertRow();[locationName(row.location)+' · '+cases[row.case],...['mean_wait_s','ped_mean_wait_s','co2_mean_g'].map(k=>fmt(row['fijo_'+k])+' / '+fmt(row['adaptativo_'+k]))].forEach(v=>tr.insertCell().textContent=v);}

  const peds=await api('/api/results/pedestrians');$('ped-results-body').replaceChildren();
  for(const p of peds.profiles||[]){const tr=$('ped-results-body').insertRow();[p.label,fmt(p.vehicle.fixed_mean),fmt(p.vehicle.adaptive_mean),fmt(p.pedestrian.fixed_mean),fmt(p.pedestrian.adaptive_mean),fmt(p.co2?.fixed_mean),fmt(p.co2?.adaptive_mean)].forEach(v=>tr.insertCell().textContent=v);}
  const data=await api('/api/results'),body=$('results-body');$('emissions-results-body').replaceChildren();body.replaceChildren();$('result-bars').replaceChildren();
  if(!data.scenarios?.length){$('result-bars').textContent='Los resultados se generan con el script de experimentos y análisis.';return;}
  const max=Math.max(...data.scenarios.flatMap(r=>[r.fixed_mean,r.adaptive_mean]));
  for(const r of data.scenarios){
    const emissionRow=$('emissions-results-body').insertRow();[labels[r.scenario],fmt(r.fixed_co2),fmt(r.adaptive_co2),fmt(r.co2_delta_mean),`[${fmt(r.co2_ci_low)}, ${fmt(r.co2_ci_high)}]`,fmt(r.co2_relative_change_pct)+' %'].forEach(v=>emissionRow.insertCell().textContent=v);
    const row=document.createElement('div');row.className='bar-row';const label=document.createElement('span');label.className='bar-label';label.textContent=labels[r.scenario];row.append(label);
    const bars=document.createElement('div');bars.className='bars';for(const[value,cls]of[[r.fixed_mean,'bar'],[r.adaptive_mean,'bar adaptive']]){const b=document.createElement('div');b.className=cls;b.style.width=`${100*value/max}%`;b.title=fmt(value)+' s';bars.append(b);}row.append(bars);
    const values=document.createElement('div');values.className='bar-values';values.append(document.createTextNode('F '+fmt(r.fixed_mean)+' s'),document.createElement('br'),document.createTextNode('A '+fmt(r.adaptive_mean)+' s'));row.append(values);$('result-bars').append(row);
    const tr=body.insertRow();[labels[r.scenario],fmt(r.fixed_mean),fmt(r.adaptive_mean),fmt(r.delta_mean),`[${fmt(r.ci_low)}, ${fmt(r.ci_high)}]`,fmt(r.relative_change_pct)+' %'].forEach(v=>tr.insertCell().textContent=v);
  }
}
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{
  document.querySelectorAll('.view').forEach(view=>view.hidden=view.id!==button.dataset.tab);
  document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));
  if(button.dataset.tab==='results')loadResults().catch(e=>notice(e.message,true));
  if(button.dataset.tab==='monitor')draw();
});
window.onSceneLocation=geometry=>{
  const real=geometry.location!=='laboratorio';
  $('scene-title').textContent=geometry.name;$('location-tag').textContent=geometry.location==='lusitania'?'LOS BODEGONES':geometry.location==='santa_eulalia'?'AVENIDA REINA SOFÍA · ENTORNO ESCOLAR':'REFERENCIA DE LABORATORIO';
  $('location-description').textContent=real?'Trazado de OSM · regulación semafórica y tráfico simulados':'Geometría sintética · tráfico y semáforos simulados';
  $('location-limits').textContent=real?geometry.assumptions.join(' '):'Cuatro accesos rectos de 300 m y un carril por sentido. Es la red de referencia usada en los resultados de la memoria.';
  $('movement-help').textContent=geometry.location==='santa_eulalia'?'Circulan alrededor de la isla central y eligen una de cinco salidas.':real?'Los coches pueden seguir recto o girar.':'Los recorridos de este modelo son rectos.';
  document.querySelectorAll('.arm-name').forEach((e,i)=>e.textContent=geometry.location==='lusitania'?['A. H. Gil · noroeste','Lusitania · noreste','A. H. Gil · sureste','Lusitania · suroeste'][i]:real?geometry.arms[arms[i]].label:armNames[i]);
  document.querySelector('.map-site .site-number').textContent=real?'J1':'LAB';
  document.querySelector('.map-site div>span').textContent=real?'Ubicación real · modelo viario simplificado':'Vista general de Mérida · el laboratorio es una red sintética';
  $('map-site-name').textContent=real?geometry.name:'Laboratorio · referencia sintética';const center=geometry.geographic_center;$('map-site-coords').textContent=center?`${fmt(center[1],6)}° N / ${fmt(-center[0],6)}° O`:'Sin ubicación física';
  if($('location').value!==geometry.location)$('location').value=geometry.location;
  syncPointSelection();updateTrafficHelp();
  if(window.sceneView?.preview)renderCooperative(null);
  initMap().catch(()=>notice('No se ha podido cargar el mapa del entorno.',true));
};
function selectLocation(location){
  if(activeRun)return;
  $('location').value=location;updateTrafficHelp();syncPointSelection();
  window.sceneView.showPreview($('pedestrian-profile').value!=='desactivado',location);clearSample(false);notice('Lugar preparado. Pulsa Iniciar simulación para observarlo.');
}
function syncPointSelection(){
  document.querySelectorAll('.point-card').forEach(card=>{
    const selected=card.id==='point-'+$('location').value;
    card.classList.toggle('selected',selected);
    const button=card.querySelector('button');button.disabled=activeRun;button.setAttribute('aria-pressed',String(selected));
    button.textContent=selected?'Cruce seleccionado':'Observar este cruce';
  });
}
window.sceneView=new SceneView($('traffic-scene'),renderSample);
initMap().catch(()=>notice('No se ha podido cargar la cartografía local.',true));loadHistory();draw();poll();loadPointMetrics();

$('sensing-mode').onchange=()=>{
  const hybrid=$('sensing-mode').value==='hybrid';$('v2x-settings').hidden=!hybrid;
  $('sensing-help').textContent=hybrid?'Los sensores cuentan las colas y detectan peatones. Los coches equipados avisan de su aproximación.':'Los sensores del cruce detectan coches detenidos y personas esperando, aunque nadie envíe avisos.';
};
function renderCooperative(s){
  $('camera-readings').textContent=s?.camera_active?`${s.camera_detected} detectados: ${s.camera_coche} coches · ${s.camera_moto} motos · ${s.camera_bicicleta} bicicletas · ${s.camera_patinete} patinetes · ${s.camera_desconocido} sin clasificar. Mayor velocidad observada: ${fmt(s.camera_speed_max_kmh)} km/h.`:'Cámara sin activar o sin muestra. Los sensores de cola siguen disponibles.';
  $('fusion-readings').textContent=s?.camera_active?`${s.fusion_approaching} vehículos llegarían en ≤ 8 s; próxima llegada estimada: ${fmt(s.fusion_eta_min)} s. Cámara y V2I se combinan sin duplicados.${s.camera_used===0?' Entrega al controlador interrumpida.':''}`:'Una misma aproximación se cuenta una sola vez, aunque la detecten la cámara y V2I.';
  const hybrid=s?.sensing_mode==='hybrid';
  $('v2x-fresh').textContent=hybrid?fmt(s.v2x_fresh,0):'—';
  $('v2x-arrivals').textContent=hybrid?fmt(s.v2x_approaching,0):'—';
  $('v2x-eta').textContent=hybrid&&s.v2x_eta_min!=null?fmt(s.v2x_eta_min)+' s':'—';
  $('v2x-pedestrians').textContent=s?fmt(s.ped_waiting,0):'—';
  $('data-source').textContent=hybrid?'Sensores virtuales + avisos V2I':'Sensores virtuales SUMO';
  $('cooperative-status').textContent=hybrid?`${s.v2x_fresh} avisos vigentes · emulación V2I`:'Sensores de presencia virtuales';
  $('v2x-message').textContent=!s?'Inicia una simulación para observar los avisos y los sensores de presencia.':!hybrid?'Solo sensores: las personas y los coches se detectan en el cruce. No se utilizan avisos V2I.':`${s.v2x_received} avisos recibidos · ${s.v2x_lost} perdidos · ${s.v2x_expired} descartados al llegar tarde. Antigüedad máxima vigente: ${fmt(s.v2x_age_max,0)} s.${s.v2x_used===0?' Entrega al controlador interrumpida por el ensayo de fallo.':s.mode==='fijo'?' El control fijo muestra estos avisos, pero mantiene sus tiempos.':' El adaptativo considera las aproximaciones junto a las colas.'}`;
  $('sensor-readings').replaceChildren();
  for(const [i,a]of arms.entries()){
    const item=document.createElement('div'),name=document.createElement('b'),value=document.createElement('span');
    name.textContent=document.querySelectorAll('.arm-name')[i]?.textContent||armNames[i];
    value.textContent=s?`${s['q_'+a]} en cola${hybrid?' · '+s['v2x_'+a]+' aproximándose':''}${s['ped_wait_'+a]!=null?' · '+s['ped_wait_'+a]+' peatones esperando':''}`:'Sin muestra';
    item.append(name,value);$('sensor-readings').append(item);
  }
}
async function loadPointMetrics(){
  try{
    const {points}=await api('/api/locations/metrics');
    for(const point of points){
      let card=$('point-'+point.id);
      if(!card){
        card=document.createElement('article');card.id='point-'+point.id;card.className='point-card';
        const title=document.createElement('h3');title.textContent=point.name;
        const status=document.createElement('p');status.className='point-status';
        const figures=document.createElement('p');figures.className='point-values';
        const context=document.createElement('p');context.className='point-context';
        const scope=document.createElement('small');scope.textContent=point.id==='laboratorio'?'Red sintética · referencia de comparación':point.id==='lusitania'?'Los Bodegones · cruce con semáforos':'Reina Sofía · rotonda con semáforos';
        const button=document.createElement('button');button.type='button';button.textContent='Observar este cruce';button.onclick=()=>{if(activeRun)return;selectLocation(point.id);$('traffic-scene').scrollIntoView({behavior:'smooth',block:'center'});};
        card.append(title,status,figures,context,scope,button);$(point.id==='laboratorio'?'laboratory-card':'point-cards').append(card);
      }
      const last=point.origin==='session'?point.last_run:point.example,summary=last?.summary,config=last?.config;
      card.querySelector('button').disabled=activeRun;
      card.querySelector('.point-status').textContent=point.active?(point.paused?'Ejecución en pausa':'Simulación en curso'):point.origin==='session'?'Tu último ensayo · '+new Date(last.created_at).toLocaleString('es-ES'):point.origin==='example'?'Ejemplo simulado incluido':'Todavía sin ensayos';
      card.querySelector('.point-values').textContent=point.active&&point.sample?`Cola actual: ${point.sample.queue_total} vehículos · ${point.sample.ped_waiting??0} peatones esperando`:summary?`Cola media: ${fmt(summary.mean_queue)} · Espera: ${fmt(summary.mean_wait_s)} s/vehículo · ${fmt(summary.ped_mean_wait_s)} s/peatón · CO₂ ${fmt(summary.co2_mean_g)} g/vehículo`:'Inicia una simulación para obtener métricas.';
      card.querySelector('.point-context').textContent=point.active?'Las cifras cambian con la simulación.':config?`${labels[config.scenario]}${config.traffic?.fleet==='mixto'?' · mixto':''}${config.camera?.enabled?' · cámara':''} · ${config.sensing?.mode==='hybrid'?'V2I '+config.sensing.penetration+' %':'sensores'} · semilla ${config.seed} · ${config.horizon} s de llegadas`:'';
    }
    syncPointSelection();
  }catch{document.querySelectorAll('.point-status').forEach(e=>e.textContent='Sin actualizar · comprueba la conexión');}
  finally{setTimeout(loadPointMetrics,2000);}
}

function updateTrafficHelp(){
  const lab=$('location').value==='laboratorio';
  const option=$('traffic-speeds').querySelector('[value="exceso"]');option.disabled=!lab;
  if(!lab&&$('traffic-speeds').value==='exceso')$('traffic-speeds').value='variable';
  $('traffic-speed-help').textContent=lab?'Coches y motos: hasta 50 km/h; velocidad variable: 30 o 50 km/h; ensayo de exceso: 30, 50 o 70 km/h. Bicicletas: hasta 20; patinetes: hasta 25. Son velocidades deseadas: las colas y señales pueden reducirlas.':'En estos cruces el modelo usa 30 km/h. Con velocidades distintas, coches y motos desean 18 o 30 km/h; bicicletas hasta 20 y patinetes hasta 25. El ensayo a 70 km/h está reservado al laboratorio.';
}
$('traffic-speeds').onchange=updateTrafficHelp;
updateTrafficHelp();

let memoryStudies=[];
async function describeStudy(){
  const study=memoryStudies.find(s=>s.id===$('study-case').value);if(!study)return;
  const config=study.config;
  $('study-description').textContent=`${config.horizon/60} minutos de llegadas · ${study.seeds.length} semillas en la batería · ${locationName(config.location)}. Cargar las opciones no inicia la simulación.`;
  $('study-reference').textContent='Cada resultado del historial corresponde a una ejecución individual.';
  if(study.id.startsWith('principal_')){
    const seed=Number($('study-seed').value),data=await api('/api/results');
    if(study.id!==$('study-case').value||seed!==Number($('study-seed').value))return;
    const values=(data.executions||[]).filter(r=>r.scenario===config.scenario&&r.seed===seed);
    if(values.length===2)$('study-reference').textContent='Referencia incluida para esta semilla: '+['fijo','adaptativo'].map(mode=>{const r=values.find(v=>v.mode===mode);return `${mode==='fijo'?'Tiempos fijos':'Se adapta al tráfico'}: ${fmt(r.mean_wait_s,2)} s/veh. y ${fmt(r.co2_mean_g,2)} g CO₂/veh.`;}).join(' · ');
  }
}
function selectStudy(){
  const study=memoryStudies.find(s=>s.id===$('study-case').value);if(!study)return;
  $('study-seed').replaceChildren(...study.seeds.map(seed=>new Option(String(seed),String(seed))));
  $('study-mode').replaceChildren(...study.modes.map(mode=>new Option(mode==='fijo'?'Cambia con tiempos fijos':'Se adapta al tráfico',mode)));
  describeStudy().catch(e=>notice(e.message,true));
}
async function initStudies(){
  memoryStudies=await api('/api/studies');const groups=new Map();
  for(const study of memoryStudies){let group=groups.get(study.group);if(!group){group=document.createElement('optgroup');group.label=study.group;groups.set(study.group,group);$('study-case').append(group);}group.append(new Option(study.label,study.id));}
  selectStudy();
}
$('study-case').onchange=selectStudy;$('study-seed').onchange=()=>describeStudy().catch(e=>notice(e.message,true));
$('prepare-study').onclick=()=>{
  if(activeRun){$('study-status').textContent='Espera a que termine la ejecución actual antes de cargar otro estudio.';return;}
  const study=memoryStudies.find(s=>s.id===$('study-case').value);if(!study)return;
  const c=study.config;
  for(const [id,value]of Object.entries({'scenario':c.scenario,'mode':$('study-mode').value,'seed':$('study-seed').value,'horizon':c.horizon,'min-green':c.timing.min_green,'max-green':c.timing.max_green,'fixed-green':c.timing.fixed_green,'outage-start':c.outage_start,'outage-end':c.outage_end,'fleet':c.traffic.fleet,'traffic-speeds':c.traffic.speeds,'sensing-mode':c.sensing.mode,'penetration':c.sensing.penetration,'v2x-range':c.sensing.range_m,'v2x-latency':c.sensing.latency_s,'v2x-loss':c.sensing.loss_percent,'camera-missed':c.camera.missed_percent,'camera-unknown':c.camera.unclassified_percent,'pedestrian-profile':c.pedestrian_profile}))$(id).value=String(value);
  $('camera-enabled').checked=c.camera.enabled;$('outage').checked=c.simulate_outage;
  $('sensing-mode').onchange();$('mode').onchange();selectLocation(c.location);$('pedestrian-profile').onchange();
  $('study-status').textContent=`Opciones cargadas: ${study.label}, semilla ${$('seed').value}, ${$('mode').selectedOptions[0].textContent}. Pulsa Iniciar simulación. Para comparar, repite con el otro control y la misma semilla.`;
  notice('Estudio preparado con sus opciones completas. Pulsa Iniciar simulación.');
};
$('run-form').addEventListener('change',e=>{if(e.target.id!=='speed')$('study-status').textContent='Has cambiado opciones del formulario. Vuelve a cargar el estudio si quieres reproducir su configuración exacta.';});
$('fixed-green').onchange=()=>$('mode').onchange();
initStudies().catch(e=>notice(e.message,true));
