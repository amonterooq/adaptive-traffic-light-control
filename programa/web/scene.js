"use strict";

// El dibujo interpola las posiciones recibidas de SUMO.
class SceneView {
  constructor(canvas, onSample) {
    this.canvas=canvas; this.ctx=canvas.getContext('2d'); this.onSample=onSample;
    this.frames=[]; this.agents=[]; this.runId=null; this.cursor=-1; this.time=null;
    this.radius=65; this.speed=5; this.paused=false; this.status='idle'; this.geometry=null;
    this.location='lusitania';this.preview=true;this.camera=[0,0];
    this.connected=true; this.lastResponse=performance.now(); this.lastPaint=performance.now();
    this.selected=null; this.selectedAgent=null;this.lastSampleTime=null; this.enabled=true; this.generation=0;
    this.loadGeometry(true,this.location);
    new ResizeObserver(()=>this.resize()).observe(canvas);
    canvas.addEventListener('click',e=>{if(!this.dragged)this.select(e);});
    canvas.addEventListener('pointerdown',e=>{this.dragged=false;this.drag={x:e.clientX,y:e.clientY,c:[...this.camera]};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!this.drag)return;const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;if(Math.hypot(dx,dy)>4)this.dragged=true;if(this.dragged)this.camera=[Math.max(-300,Math.min(300,this.drag.c[0]-dx/this.scale)),Math.max(-300,Math.min(300,this.drag.c[1]+dy/this.scale))];});
    for(const event of ['pointerup','pointercancel'])canvas.addEventListener(event,()=>{this.drag=null;});
    canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom(e.deltaY>0?1.12:.89);},{passive:false});
    canvas.addEventListener('keydown',e=>{const keys={ArrowLeft:[-10,0],ArrowRight:[10,0],ArrowUp:[0,10],ArrowDown:[0,-10]};if(keys[e.key]){e.preventDefault();this.camera=this.camera.map((v,i)=>Math.max(-300,Math.min(300,v+keys[e.key][i])));}else if(e.key==='Home'){e.preventDefault();this.recenter();}else if(e.key==='Escape')this.clearSelection();});
    document.getElementById('scene-zoom-in').onclick=()=>this.zoom(.75);
    document.getElementById('scene-zoom-out').onclick=()=>this.zoom(1.4);
    document.getElementById('scene-close').onclick=()=>this.recenter();
    document.getElementById('scene-wide').onclick=()=>{this.radius=this.geometry?.wide_radius||315;this.camera=[0,0];};
    document.getElementById('entity-unpin').onclick=()=>this.clearSelection();
    this.resize(); this.poll(); requestAnimationFrame(t=>this.animate(t));
  }
  recenter(){this.radius=this.geometry?.detail_radius||38;this.camera=[0,0];}
  showPreview(enabled,location){
    this.preview=true;this.status='idle';this.paused=false;this.reset(null);this.loadGeometry(enabled,location);
    document.getElementById('scene-live').textContent='VISTA DEL CRUCE';
    const pause=document.getElementById('pause');pause.disabled=true;pause.textContent='Ⅱ Pausar';pause.setAttribute('aria-pressed','false');
  }
  async loadGeometry(enabled,location=this.location) {
    this.loadingGeometry=true;
    this.requestedGeometry={enabled,location};
    const generation=++this.generation;
    try {
      const response=await fetch('/api/scene/network?pedestrians='+enabled+'&location='+location);
      if(!response.ok)throw new Error('geometry');
      const geometry=await response.json();
      if(generation===this.generation){const changed=location!==this.geometry?.location;this.geometry=geometry;this.backgroundKey=null;this.location=location;this.enabled=enabled;this.geometryError=false;if(changed)this.recenter();this.descriptionKey=null;window.onSceneLocation?.(geometry);}
    } catch {this.geometryError=true;}
    finally {if(generation===this.generation)this.loadingGeometry=false;}
  }
  reset(id) {
    this.runId=id;this.cursor=-1;this.frames=[];this.agents=[];this.time=null;
    this.lastSampleTime=null;this.clearSelection();
  }
  async poll() {
    try {
      const response=await fetch(`/api/scene?after=${this.cursor}&run_id=${encodeURIComponent(this.runId||'')}`);
      if(!response.ok)throw new Error('scene');
      const data=await response.json();
      if(data.status==='running')this.preview=false;
      if(this.preview){this.status='idle';this.connected=true;if(this.geometryError&&!this.loadingGeometry)this.loadGeometry(this.requestedGeometry.enabled,this.requestedGeometry.location);return;}
      if(data.id!==this.runId||data.reset)this.reset(data.id);
      if(data.id&&(data.pedestrians!==this.enabled||data.location!==this.location))this.loadGeometry(data.pedestrians,data.location);
      else if(!this.geometry&&!this.loadingGeometry)this.loadGeometry(data.pedestrians,data.location);
      this.speed=data.speed; this.paused=data.paused&&data.status==='running'; this.status=data.status;
      for(const frame of data.frames){
        if(frame.time>this.cursor){this.frames.push(frame);this.cursor=frame.time;}
      }
      if(this.frames.length>180)this.frames.splice(0,this.frames.length-180);
      if(this.time===null&&this.frames.length)this.time=this.frames[0].time;
      if(this.paused&&this.frames.length)this.time=this.frames.at(-1).time;
      this.connected=true;this.lastResponse=performance.now();
      const pause=document.getElementById('pause');
      pause.disabled=data.status!=='running';pause.textContent=this.paused?'▶ Continuar':'Ⅱ Pausar';
      pause.setAttribute('aria-pressed',String(this.paused));
      document.getElementById('scene-live').textContent=this.paused?'EN PAUSA':data.status==='running'?'EN DIRECTO':data.status==='complete'?'FINALIZADA':data.status==='cancelled'?'DETENIDA':'VISTA DEL CRUCE';
    } catch {this.connected=false;}
    finally {setTimeout(()=>this.poll(),this.status==='running'?100:350);}
  }
  resize() {
    const rect=this.canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;
    this.width=rect.width;this.height=rect.height;
    this.canvas.width=Math.round(rect.width*ratio);this.canvas.height=Math.round(rect.height*ratio);
    this.ratio=ratio;
  }
  zoom(factor){this.radius=Math.max(18,Math.min(315,this.radius*factor));}
  point(x,y){const [cx,cy]=this.geometry?.center||[300,300];return [this.width/2+(x-cx-this.camera[0])*this.scale,this.height/2-(y-cy-this.camera[1])*this.scale];}
  path(shape,fill,stroke,width=1,dash=[]) {
    const ctx=this.ctx;ctx.beginPath();
    shape.forEach(([x,y],i)=>{const p=this.point(x,y);i?ctx.lineTo(...p):ctx.moveTo(...p);});
    if(fill){ctx.closePath();ctx.fillStyle=fill;ctx.fill();}
    if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width*this.scale;ctx.setLineDash(dash.map(v=>v*this.scale));ctx.stroke();ctx.setLineDash([]);}
  }
  paintBackground(){
    const key=[this.generation,this.geometry?.location,this.width,this.height,this.ratio,this.radius,...this.camera].join('|');
    if(this.backgroundKey!==key){
      const layer=document.createElement('canvas');layer.width=this.canvas.width;layer.height=this.canvas.height;
      const context=this.ctx;this.ctx=layer.getContext('2d');this.ctx.setTransform(this.ratio,0,0,this.ratio,0,0);
      this.background();this.ctx=context;this.backgroundLayer=layer;this.backgroundKey=key;
    }
    this.ctx.drawImage(this.backgroundLayer,0,0,this.width,this.height);
  }
  background() {
    const ctx=this.ctx,w=this.width,h=this.height;
    ctx.fillStyle='#e7eddf';ctx.fillRect(0,0,w,h);
    if(!this.geometry)return;
    const [cx,cy]=this.geometry.center;
    // Las aceras y calzadas siguen la red; la vegetación del laboratorio es esquemática.
    if(this.location==='laboratorio')for(const sx of [-1,1])for(const sy of [-1,1]){
      const p=this.point(cx+sx*26,cy+sy*26),size=16*this.scale;
      ctx.fillStyle='#d5dfcb';ctx.beginPath();ctx.roundRect(p[0]-size/2,p[1]-size/2,size,size,Math.min(12,size/5));ctx.fill();
      for(let i=0;i<3;i++){
        const t=this.point(cx+sx*(12+i*9),cy+sy*(19+(i%2)*12));
        ctx.fillStyle='#c7d7b9';ctx.beginPath();ctx.arc(t[0]+2,t[1]+3,2.1*this.scale,0,Math.PI*2);ctx.fill();
        ctx.fillStyle=i%2?'#a9c39c':'#b6cba9';ctx.beginPath();ctx.arc(...t,1.8*this.scale,0,Math.PI*2);ctx.fill();
      }
    }
    ctx.lineCap='butt';ctx.lineJoin='round';
    if(this.geometry.context){
      for(const f of this.geometry.context.filter(f=>f.polygon)){
        const p=f.properties;
        if(p.building)this.path(f.shape.map(([x,y])=>[x+.6,y-.7]),'#bdc7b750');
        this.path(f.shape,p.leisure||p.landuse==='grass'?'#c8d8b9':p.building?'#e4decf':'#d5dace',p.building?'#c8bfad':null,.18);
      }
      for(const f of this.geometry.context.filter(f=>!f.polygon)){
        const foot=['footway','path','steps'].includes(f.properties.highway),width=foot?1.5:Math.max(4,Number(f.properties.lanes||2)*3.2);
        this.path(f.shape,null,'#f1ebdd',width+3);this.path(f.shape,null,foot?'#d7daca':'#b6bcb3',width);
      }
    }
    const lanes=this.geometry.lanes;
    for(const lane of lanes.filter(l=>['sidewalk','walkingarea'].includes(l.kind))){
      if(lane.kind==='walkingarea')this.path(lane.shape,'#ede6d7','#c8c0af',.12);
      else {this.path(lane.shape,null,'#cec8ba',lane.width+.3);this.path(lane.shape,null,'#ede6d7',lane.width);}
    }
    const roads=lanes.filter(l=>['road','internal'].includes(l.kind));
    for(const lane of roads)this.path(lane.shape,null,'#c8c7b9',lane.width+.6);
    this.path(this.geometry.junction,'#58656a');
    for(const lane of roads)this.path(lane.shape,null,'#58656a',lane.width);
    for(const lane of lanes.filter(l=>l.kind==='road')){
      const index=Number(lane.id.split('_').at(-1)),edge=lane.id.replace(/_\d+$/,'');
      const adjacent=lanes.some(l=>l.kind==='road'&&l.id===edge+'_'+(index+1));
      this.path(this.offsetLine(lane.shape,lane.width/2),null,'#f1efdf',adjacent?.12:.1,adjacent?[2.2,2.2]:[]);
      if(index===0)this.path(this.offsetLine(lane.shape,-lane.width/2),null,'#eeeadd',.1);
    }
    if(this.location==='santa_eulalia'){
      const ring=lanes.filter(l=>l.kind==='road'&&l.id.startsWith('ring_')).sort((a,b)=>Number(a.id.split('_')[1])-Number(b.id.split('_')[1]));
      const island=ring.flatMap(lane=>this.offsetLine(lane.shape,lane.width/2+.2));
      if(island.length>2)this.path([...island,island[0]],'#c5d2b2','#e8dfcd',.3);
    }
    for(const lane of lanes.filter(l=>l.kind==='road'&&l.id.includes('_in_'))){
      const a=lane.id[0];
      const side={N:[1,0],E:[0,-1],S:[-1,0],W:[0,1]}[a];
      if(this.location==='laboratorio')this.path(lane.shape.map(([x,y])=>[x+side[0]*lane.width/2,y+side[1]*lane.width/2]),null,'#f1efdf',.1,[2,2]);
      const end=lane.shape.at(-1),start=lane.shape.at(-2),dx=end[0]-start[0],dy=end[1]-start[1],len=Math.hypot(dx,dy);
      const stop=[end[0]-dx/len*.35,end[1]-dy/len*.35];
      this.path([[stop[0]-dy/len*1.45,stop[1]+dx/len*1.45],[stop[0]+dy/len*1.45,stop[1]-dx/len*1.45]],null,'#fff9ea',.3);
      const p=this.point(end[0]-dx/len*14,end[1]-dy/len*14);
      ctx.save();ctx.translate(...p);ctx.rotate(Math.atan2(-dy,dx)+Math.PI/2);ctx.strokeStyle='#dce3d9';ctx.lineWidth=Math.max(1,.13*this.scale);
      const s=this.scale;ctx.beginPath();ctx.moveTo(0,2*s);ctx.lineTo(0,-2*s);ctx.moveTo(-.7*s,-1.2*s);ctx.lineTo(0,-2*s);ctx.lineTo(.7*s,-1.2*s);ctx.stroke();ctx.restore();
    }
    for(const lane of lanes.filter(l=>l.kind==='crossing')){
      this.path(lane.shape,null,'#4e5c60',lane.width);
      this.path(lane.shape,null,'#fcf9e8',lane.width-.35,[.5,.5]);
    }
    if(this.geometry.arms){
      ctx.font='600 11px Segoe UI';ctx.textAlign='center';
      for(const arm of Object.values(this.geometry.arms)){
        const s=arm.shape,p=s.at(-1),dx=p[0]-cx,dy=p[1]-cy,d=Math.hypot(dx,dy),q=this.point(cx+dx*.62-dy/d*14,cy+dy*.62+dx/d*14);
        let angle=Math.atan2(-dy,dx);if(angle>Math.PI/2)angle-=Math.PI;if(angle<-Math.PI/2)angle+=Math.PI;
        ctx.save();ctx.translate(...q);ctx.rotate(angle);ctx.strokeStyle='#f0f3e9';ctx.lineWidth=4;const name=arm.name.replace('Avenida','Av.').replace('Calle','C.');ctx.strokeText(name,0,0);ctx.fillStyle='#38594f';ctx.fillText(name,0,0);ctx.restore();
      }
      if(this.radius>=100)for(const landmark of this.geometry.landmarks){const p=this.point(...landmark.position);ctx.fillStyle='#167266';ctx.beginPath();ctx.arc(...p,4,0,Math.PI*2);ctx.fill();ctx.textAlign='left';ctx.strokeStyle='#f2f5ed';ctx.lineWidth=4;ctx.strokeText(landmark.name,p[0]+8,p[1]+4);ctx.fillText(landmark.name,p[0]+8,p[1]+4);}
    }
    ctx.font='600 11px Segoe UI';ctx.textAlign='center';ctx.fillStyle='#45615a';
    ctx.fillText('NORTE',w/2,21);ctx.fillText('SUR',w/2,h-15);
    ctx.textAlign='left';ctx.fillText('OESTE',14,h/2-17);ctx.textAlign='right';ctx.fillText('ESTE',w-14,h/2-17);
    ctx.textAlign='left';ctx.font='10px Segoe UI';
    const meters=this.radius>100?50:10,bar=meters*this.scale;
    ctx.strokeStyle='#45615a';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(20,h-26);ctx.lineTo(20+bar,h-26);ctx.stroke();ctx.fillText(meters+' m',20,h-32);
  }
  offsetLine(shape,offset){
    return shape.map(([x,y],i)=>{
      const a=shape[Math.max(0,i-1)],b=shape[Math.min(shape.length-1,i+1)];
      const length=Math.hypot(b[0]-a[0],b[1]-a[1]);
      return length?[x-(b[1]-a[1])/length*offset,y+(b[0]-a[0])/length*offset]:[x,y];
    });
  }
  signals(sample) {
    if(!this.geometry)return;
    const ctx=this.ctx,[cx,cy]=this.geometry.center;
    const positions=this.location!=='laboratorio'?['N','E','S','W'].map(a=>{
      const lane=this.geometry.lanes.find(l=>l.kind==='road'&&l.id.startsWith(a+'_in_')),s=lane.shape,b=s.at(-1),v=s.at(-2),d=Math.hypot(b[0]-v[0],b[1]-v[1]);return [b[0]-cx+(b[1]-v[1])/d*4,b[1]-cy-(b[0]-v[0])/d*4];
    }):[[-8,12],[12,8],[8,-12],[-12,-8]];
    const colors=['#ec7566','#f4c365','#67dbb2'];
    positions.forEach(([x,y],i)=>{
      const p=this.point(cx+x,cy+y),s=Math.max(1.4,Math.min(4,this.scale*.5));
      ctx.fillStyle='#263d3f';ctx.beginPath();ctx.roundRect(p[0]-2.1*s,p[1]-4.8*s,4.2*s,9.6*s,s);ctx.fill();
      const state=sample?.state?.[i],active=['G','g'].includes(state)?2:state==='y'?1:state==='r'?0:-1;
      colors.forEach((color,n)=>{ctx.fillStyle=active===n?color:'#506064';ctx.beginPath();ctx.arc(p[0],p[1]+(n-1)*2.65*s,.95*s,0,Math.PI*2);ctx.fill();});
    });
    if(this.geometry.pedestrians){
      const pedestrianPositions=this.location!=='laboratorio'?this.geometry.lanes.filter(l=>l.kind==='crossing').map(l=>[l.shape[0][0]-cx,l.shape[0][1]-cy]):[[8,5.2],[5.2,-8],[-8,-5.2],[-5.2,8]];
      for(const [x,y]of pedestrianPositions){
        const p=this.point(cx+x,cy+y),r=Math.max(4,Math.min(9,this.scale*1.15));
        ctx.fillStyle=sample?.ped_signal==='G'?'#167266':sample?.ped_signal?'#b9554c':'#7c8d83';
        ctx.beginPath();ctx.arc(...p,r,0,Math.PI*2);ctx.fill();
        ctx.fillStyle='#fff';ctx.font=`700 ${Math.max(6,r*1.2)}px Segoe UI`;ctx.textAlign='center';ctx.fillText('P',p[0],p[1]+r*.4);
      }
    }
  }
  car(agent) {
    const ctx=this.ctx,p=this.point(agent.x,agent.y),s=this.scale;
    const length=agent.length*s,width=agent.width*s;
    ctx.save();ctx.translate(...p);ctx.rotate(agent.angle*Math.PI/180);
    if(agent.id===this.selected){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.strokeRect(-width/2-3,-3,width+6,length+6);}
    let hash=0;for(const char of agent.id)hash=(hash*31+char.charCodeAt(0))|0;
    const colors=['#a6d8cb','#eece8b','#d9e1e1','#81b4cf','#daa893'];
    ctx.fillStyle='#243a3e30';ctx.beginPath();ctx.roundRect(-width/2+1,1,width,length,Math.min(4,width*.2));ctx.fill();
    ctx.fillStyle=colors[Math.abs(hash)%colors.length];ctx.beginPath();ctx.roundRect(-width/2,0,width,length,Math.min(4,width*.2));ctx.fill();
    ctx.fillStyle='#30494e';ctx.fillRect(-width*.38,length*.18,width*.76,length*.17);
    ctx.fillStyle='#466068';ctx.fillRect(-width*.35,length*.68,width*.7,length*.12);
    ctx.fillStyle='#fff6c8';ctx.fillRect(-width*.44,0,width*.22,Math.max(1,s*.16));ctx.fillRect(width*.22,0,width*.22,Math.max(1,s*.16));
    ctx.fillStyle=agent.speed<.1?'#ff5f50':'#bb584b';ctx.fillRect(-width*.44,length-s*.2,width*.22,Math.max(1,s*.2));ctx.fillRect(width*.22,length-s*.2,width*.22,Math.max(1,s*.2));
    ctx.restore();
    if(agent.connected_vehicle&&document.getElementById('show-sensing').checked){
      ctx.strokeStyle='#197bba';ctx.fillStyle=agent.v2x_received?'#197bba':'#f2f8fb';ctx.lineWidth=1.4;
      ctx.beginPath();ctx.arc(p[0],p[1]-5,3,0,Math.PI*2);ctx.fill();ctx.stroke();
    }
  }
  twoWheeler(agent){
    const ctx=this.ctx,p=this.point(agent.x,agent.y),s=this.scale;
    const length=Math.max(7,agent.length*s),width=Math.max(3,agent.width*s);
    const colors={moto:'#af7059',bicicleta:'#43b6ab',patinete:'#ad92d0'};
    ctx.save();ctx.translate(...p);ctx.rotate(agent.angle*Math.PI/180);
    ctx.strokeStyle='#243a3e';ctx.lineWidth=Math.max(1,s*.22);
    ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(0,length);ctx.moveTo(-width/2,length*.22);ctx.lineTo(width/2,length*.22);ctx.stroke();
    ctx.fillStyle=colors[agent.vehicle_type];
    ctx.beginPath();ctx.ellipse(0,length*.55,width*.5,length*.28,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#efd0aa';ctx.beginPath();ctx.arc(0,length*.4,Math.max(1.3,width*.3),0,Math.PI*2);ctx.fill();
    if(agent.id===this.selected){ctx.strokeStyle='#fff';ctx.strokeRect(-width/2-3,-3,width+6,length+6);}
    ctx.restore();
    if(agent.connected_vehicle&&document.getElementById('show-sensing').checked){ctx.fillStyle=agent.v2x_received?'#197bba':'#f2f8fb';ctx.strokeStyle='#197bba';ctx.beginPath();ctx.arc(p[0],p[1]-5,3,0,Math.PI*2);ctx.fill();ctx.stroke();}
  }
  sensing(sample,agents){
    if(!this.geometry||!document.getElementById('show-sensing').checked)return;
    const ctx=this.ctx,[cx,cy]=this.geometry.center;
    for(const lane of this.geometry.lanes.filter(l=>l.kind==='crossing')){
      for(const position of [lane.shape[0],lane.shape.at(-1)]){
        const present=agents.some(a=>a.kind==='person'&&a.waiting>0&&Math.hypot(a.x-position[0],a.y-position[1])<5);
        const p=this.point(...position),size=Math.max(5,2.6*this.scale);
        ctx.fillStyle=present?'#dea34538':'#24859410';ctx.strokeStyle=present?'#c38928':'#428d8c';ctx.lineWidth=1;ctx.setLineDash([3,3]);
        ctx.beginPath();ctx.roundRect(p[0]-size,p[1]-size,size*2,size*2,3);ctx.fill();ctx.stroke();ctx.setLineDash([]);
      }
    }
    if(sample?.sensing_mode!=='hybrid')return;
    const hub=this.point(cx+20,cy+20);
    const shown=agents.filter(a=>a.kind==='vehicle'&&a.v2x_received&&a.speed>1).slice(0,4);
    ctx.strokeStyle='#197bba55';ctx.lineWidth=1;ctx.setLineDash([3,5]);
    for(const a of shown){const p=this.point(a.x,a.y);ctx.beginPath();ctx.moveTo(...hub);ctx.lineTo(...p);ctx.stroke();}
    ctx.setLineDash([]);ctx.fillStyle='#eaf5fc';ctx.strokeStyle='#197bba';ctx.lineWidth=1.2;
    ctx.beginPath();ctx.roundRect(hub[0]-16,hub[1]-10,32,20,5);ctx.fill();ctx.stroke();
    ctx.fillStyle='#15699c';ctx.font='700 10px Segoe UI';ctx.textAlign='center';ctx.fillText('RSU',hub[0],hub[1]+3);
  }
  person(agent) {
    const ctx=this.ctx,p=this.point(agent.x,agent.y),r=Math.max(2.2,Math.min(7,this.scale*.7));
    ctx.save();ctx.translate(...p);ctx.rotate(agent.angle*Math.PI/180);
    const walking=agent.speed>.05,step=walking?Math.sin(this.time*7+agent.id.length)*r*.48:0;
    ctx.strokeStyle='#5f4741';ctx.lineWidth=Math.max(1,r*.38);ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-r*.4,0);ctx.lineTo(-r*.4,r*.9+step);ctx.moveTo(r*.4,0);ctx.lineTo(r*.4,r*.9-step);ctx.stroke();
    ctx.fillStyle=agent.waiting>0?'#d89945':'#b96552';ctx.beginPath();ctx.ellipse(0,0,r,r*.5,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#f0c8a3';ctx.beginPath();ctx.arc(0,-r*.24,r*.52,0,Math.PI*2);ctx.fill();
    if(agent.id===this.selected){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,r+3,0,Math.PI*2);ctx.stroke();}
    ctx.restore();
  }
  interpolate() {
    if(!this.frames.length)return {agents:[],sample:null};
    let index=this.frames.findIndex(f=>f.time>=this.time);
    if(index<0)index=this.frames.length-1;
    const b=this.frames[index],a=this.frames[Math.max(0,index-1)];
    const weight=a.time===b.time?1:Math.max(0,Math.min(1,(this.time-a.time)/(b.time-a.time)));
    const previous=new Map(a.agents.map(agent=>[agent.id,agent]));
    const agents=b.agents.map(agent=>{
      const old=previous.get(agent.id);if(!old)return {...agent,opacity:weight};
      const angle=((agent.angle-old.angle+540)%360)-180;
      return {...agent,x:old.x+(agent.x-old.x)*weight,y:old.y+(agent.y-old.y)*weight,angle:old.angle+angle*weight,opacity:1};
    });
    // Al salir, el agente se desvanece en su última posición recibida.
    const current=new Set(b.agents.map(agent=>agent.id));
    for(const agent of a.agents)if(!current.has(agent.id)&&weight<1)agents.push({...agent,opacity:1-weight});
    return {agents,sample:b.sample,frame:b};
  }
  animate(now) {
    const elapsed=Math.min(.1,(now-this.lastPaint)/1000);this.lastPaint=now;
    if(!this.width||!this.height){requestAnimationFrame(t=>this.animate(t));return;}
    if(this.frames.length&&this.connected&&!this.paused){
      const newest=this.frames.at(-1).time;
      const lag=newest-this.time,buffer=Math.max(1,this.speed*.25);
      if(this.status==='running'&&lag>buffer+this.speed*2)this.time=newest-buffer;
      const rate=this.status==='running'&&lag<buffer*.5?.8:1;
      this.time=Math.min(newest,this.time+elapsed*this.speed*rate);
    }
    this.scale=Math.min(this.width,this.height)/(this.radius*2);
    this.ctx.setTransform(this.ratio,0,0,this.ratio,0,0);
    this.paintBackground();const current=this.loadingGeometry?{agents:[],sample:null}:this.interpolate();this.agents=current.agents;
    this.signals(current.sample);
    this.sensing(current.sample,current.agents);
    for(const agent of current.agents){
      const p=this.point(agent.x,agent.y);if(p[0]<-30||p[1]<-30||p[0]>this.width+30||p[1]>this.height+30)continue;
      this.ctx.globalAlpha=agent.opacity;
      agent.kind==='vehicle'?(agent.vehicle_type&&['moto','bicicleta','patinete'].includes(agent.vehicle_type)?this.twoWheeler(agent):this.car(agent)):this.person(agent);
    }
    this.ctx.globalAlpha=1;
    if(current.frame&&current.frame.time!==this.lastSampleTime){
      this.lastSampleTime=current.frame.time;this.onSample({...current.sample,t:current.frame.time});
      this.canvas.dataset.frame=String(current.frame.time);
      this.canvas.dataset.vehicles=String(current.frame.agents.filter(a=>a.kind==='vehicle').length);
      this.canvas.dataset.persons=String(current.frame.agents.filter(a=>a.kind==='person').length);
      this.updateSelection(current.frame.agents);
    }
    this.describe(current.sample);
    requestAnimationFrame(t=>this.animate(t));
  }
  describe(sample) {
    const key=[this.location,this.connected,this.geometryError,this.status,this.paused,this.time>=this.cursor,sample?.ped_stage,sample?.state,sample?.t<20,sample?.draining,sample?.fallback].join('|');
    if(key===this.descriptionKey)return;this.descriptionKey=key;
    const title=document.getElementById('scene-phase'),message=document.getElementById('scene-message');
    if(this.geometryError){title.textContent='No se pudo cargar el cruce';message.textContent='Comprobando de nuevo la conexión con el servidor…';return;}
    if(!this.connected){title.textContent='Conexión interrumpida';message.textContent='La imagen está congelada en el último estado recibido.';return;}
    if(this.paused){title.textContent='Simulación en pausa';message.textContent='Puedes ampliar el cruce o tocar un coche o peatón. Pulsa Continuar para seguir.';return;}
    if(this.status==='idle'){title.textContent=this.location==='lusitania'?'Estás en Los Bodegones':'Tu cruce está listo';message.textContent='Pulsa Iniciar simulación. Arrastra la vista para explorar o usa Detalle del cruce para volver.';return;}
    if(this.status==='failed'){title.textContent='Este ensayo no es válido';message.textContent='El aviso y el informe junto a los controles explican el motivo. Puedes descargar el informe o abrirlo desde el historial.';return;}
    if(this.status==='cancelled'){title.textContent='Simulación detenida';message.textContent='La imagen conserva el último instante. Puedes iniciar otro ejemplo.';return;}
    if(this.status==='complete'&&this.time>=this.cursor){title.textContent='Todos han llegado a su destino';message.textContent='Puedes consultar la espera en el historial o probar otro tipo de semáforo.';return;}
    if(!sample){title.textContent='Preparando el tráfico…';message.textContent='Los coches llegarán desde los cuatro accesos.';return;}
    if(sample.ped_signal==='G'){title.textContent='Ahora cruzan los peatones';message.textContent='Los coches tienen rojo en las cuatro entradas.';}
    else if(sample.ped_stage==='ped_clear'){title.textContent='Dejamos terminar de cruzar';message.textContent='No entran nuevos peatones. Los coches esperan a que los pasos queden libres.';}
    else if(sample.state.includes('y')){title.textContent='El semáforo cambia a amarillo';message.textContent='Termina el paso de los coches antes de dar paso a otra dirección.';}
    else if(sample.state==='rrrr'){title.textContent='Un momento: todos en rojo';message.textContent='El cruce se despeja antes de abrir el siguiente paso.';}
    else {title.textContent=['G','g'].includes(sample.state[0])?'Pasan los coches de norte y sur':'Pasan los coches de este y oeste';message.textContent=sample.draining?'Ya no entran nuevos vehículos; esperamos a que los últimos terminen.':'Observa cómo avanzan los coches en verde y se forma la cola en rojo.';}
    if(this.location==='santa_eulalia'&&/[Gg]/.test(sample.state)){title.textContent='Circulación en la rotonda';message.textContent='Quien entra cede el paso a los vehículos del anillo. Los semáforos protegen el paso de peatones.';}
    else if(this.location!=='laboratorio'&&/[Gg]/.test(sample.state)){title.textContent='Pasan por '+this.geometry.arms[['G','g'].includes(sample.state[0])?'N':'E'].name;message.textContent='Los coches pueden seguir recto o girar. Al girar a la izquierda ceden a los movimientos prioritarios.';}
    if(sample.t<20)message.textContent=this.location!=='laboratorio'?'Los coches llegan por los cuatro accesos. Los puntos azules señalan vehículos equipados para enviar avisos.':'Los primeros coches se acercan desde accesos de 300 m. Usa «Toda la red» para verlos llegar.';
    if(sample.fallback)message.textContent='Faltan datos de los detectores: el semáforo está usando tiempos fijos de respaldo.';
  }
  select(event) {
    const rect=this.canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;
    let found=null,distance=Infinity;
    for(const agent of this.agents){
      const radians=agent.angle*Math.PI/180,offset=agent.kind==='vehicle'?agent.length/2:0;
      const p=this.point(agent.x-Math.sin(radians)*offset,agent.y-Math.cos(radians)*offset);
      const d=Math.hypot(x-p[0],y-p[1]);if(d<Math.max(12,this.scale*2.5)&&d<distance){found=agent;distance=d;}
    }
    if(!found){this.clearSelection();return;}
    this.selected=found.id;this.selectedAgent=found;this.updateSelection(this.agents);
  }
  clearSelection(){
    this.selected=null;this.selectedAgent=null;document.getElementById('entity-info').hidden=true;
  }
  updateSelection(agents){
    if(!this.selected)return;
    const current=agents.find(agent=>agent.id===this.selected);
    if(current)this.selectedAgent=current;
    const agent=this.selectedAgent;if(!agent)return;
    document.getElementById('entity-info').hidden=false;
    const name=agent.kind==='vehicle'?({moto:'Moto',bicicleta:'Bicicleta',patinete:'Patinete'}[agent.vehicle_type]||'Coche'):'Peatón';
    document.getElementById('entity-name').textContent=`${name} ${agent.id}`;
    document.getElementById('entity-description').textContent=`${(agent.speed*3.6).toLocaleString('es-ES',{maximumFractionDigits:1})} km/h · ${agent.waiting.toLocaleString('es-ES')} s detenido.${agent.connected_vehicle?' Equipado V2I · '+(agent.v2x_received?'aviso vigente.':'sin aviso vigente en el receptor.'):''}`;
    document.getElementById('entity-state').textContent=current?'Fijado · datos de la última muestra recibida.':'Ha salido de la escena. Se conservan sus últimos datos; puedes desfijarlo.';
  }
}
window.SceneView=SceneView;
