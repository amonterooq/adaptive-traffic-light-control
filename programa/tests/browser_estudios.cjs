const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.ITS_BROWSER||undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],checks=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const check=(name,condition)=>{assert.ok(condition,name);checks.push(name);};
  const base=process.env.ITS_URL||'http://127.0.0.1:8765';
  const output=process.env.ITS_SCREENSHOTS||path.resolve('documentacion/capturas');
  fs.mkdirSync(output,{recursive:true});
  try{
    await page.goto(base);await page.waitForFunction(()=>document.querySelectorAll('#study-case option').length===38);
    await page.locator('#study-panel summary').click();
    const studies=await (await page.request.get(base+'/api/studies')).json();
    const forms=[];
    for(const study of studies){
      await page.locator('#study-case').selectOption(study.id);
      await page.locator('#prepare-study').click();
      await page.waitForFunction(location=>window.sceneView.geometry?.location===location,study.config.location);
      const actual=await page.evaluate(()=>{
        const value=id=>document.getElementById(id).value;
        return {location:value('location'),scenario:value('scenario'),mode:value('mode'),seed:+value('seed'),
          horizon:+value('horizon'),pedestrian_profile:value('pedestrian-profile'),
          timing:{min_green:+value('min-green'),max_green:+value('max-green'),fixed_green:+value('fixed-green')},
          simulate_outage:document.getElementById('outage').checked,outage_start:+value('outage-start'),outage_end:+value('outage-end'),
          traffic:{fleet:value('fleet'),speeds:value('traffic-speeds'),emissions:true},
          camera:{enabled:document.getElementById('camera-enabled').checked,range_m:80,missed_percent:+value('camera-missed'),unclassified_percent:+value('camera-unknown')},
          sensing:{mode:value('sensing-mode'),penetration:+value('penetration'),range_m:+value('v2x-range'),latency_s:+value('v2x-latency'),loss_percent:+value('v2x-loss')}};
      });
      const expected={...study.config,timing:{min_green:study.config.timing.min_green,max_green:study.config.timing.max_green,fixed_green:study.config.timing.fixed_green}};
      assert.deepEqual(actual,expected,study.id);forms.push(study.id);
    }
    check('38 estudios cargan todos los parámetros de sus lotes',forms.length===38);
    await page.locator('#study-case').selectOption('principal_medio');
    await page.locator('#study-mode').selectOption('adaptativo');await page.locator('#prepare-study').click();
    await page.waitForFunction(()=>document.querySelector('#study-reference').textContent.includes('Referencia incluida'));
    check('referencia individual distingue una semilla de la media',true);
    await page.locator('#study-panel').screenshot({path:path.join(output,'reproducir_estudio.png')});
    await page.setViewportSize({width:390,height:844});
    check('selector de estudios cabe en móvil',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.setViewportSize({width:1440,height:1100});
    await page.locator('#speed').selectOption('100');await page.locator('#start').click();
    await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='En curso');
    await page.locator('#prepare-study').click();
    check('no se cambia el estudio durante una ejecución',(await page.locator('#study-status').textContent()).includes('Espera a que termine'));
    await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='Completada',null,{timeout:180000});
    const state=await(await page.request.get(base+'/api/state')).json();
    const referencePath='datos/resultados/principal/medio_adaptativo_101/resumen.json';
    const reference=fs.existsSync(path.resolve(referencePath))
      ? JSON.parse(fs.readFileSync(path.resolve(referencePath),'utf8'))
      : JSON.parse(fs.readFileSync(path.resolve('datos/procesados/resumenes_336.json'),'utf8'))
        .find(entry=>entry.source===referencePath)?.summary;
    assert.ok(reference,'resumen de referencia incluido en la distribución');
    for(const key of ['mean_wait_s','co2_mean_g','mean_queue','fleet_sha256','demand_sha256','generated','arrived'])assert.deepEqual(state.summary[key],reference[key],key);
    check('ejecución desde el formulario coincide con el lote en espera emisiones demanda y flota',true);
    check('historial muestra duración',(await page.locator('#history-body').textContent()).includes('30 min'));
    await page.getByRole('button',{name:'Comparar resultados',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('#emissions-results-body tr').length===5);
    const data=await(await page.request.get(base+'/api/results')).json();
    check('tabla ambiental procede del agregado entregado',(await page.locator('#emissions-results-body').textContent()).includes(data.scenarios[2].adaptive_co2.toLocaleString('es-ES',{minimumFractionDigits:1,maximumFractionDigits:1})));
    await page.locator('#results').screenshot({path:path.join(output,'resultados_emisiones.png')});
    await page.route('**/api/state',route=>route.fulfill({json:{id:'incidencia',status:'failed',summary:{collisions:4,teleports:0,ped_conflicts:0}}}));
    await page.goto(base);
    await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('4 vehículos implicados en colisión'));
    check('ensayo no válido muestra la causa y su exclusión',(await page.locator('#notice').textContent()).includes('se excluye de las comparaciones'));
    check('sin errores JavaScript',errors.length===0);
    const report={passed:true,date:new Date().toISOString(),checks,forms,errors};
    fs.writeFileSync(path.join(output,'prueba_estudios.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
