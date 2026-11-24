const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
  const out=process.env.ITS_SCREENSHOTS||'tmp/capturas_derechas';fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:process.env.ITS_BROWSER||undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  try{
    await page.goto(process.env.ITS_URL||'http://127.0.0.1:8777');
    await page.waitForFunction(()=>window.sceneView?.geometry?.location==='lusitania');
    await page.locator('#pedestrian-profile').selectOption('desactivado');
    await page.locator('#mode').selectOption('fijo');
    await page.locator('#speed').selectOption('5');
    await page.locator('#start').click();
    for(const [arm,color] of [['S','G'],['N','g']]){
      await page.waitForFunction(({arm,color})=>{
        const s=window.sceneView.frames.at(-1)?.sample;
        return s?.right_turn_arm===arm&&s.right_turn_signal===color;
      },{arm,color},{timeout:60000});
      await page.locator('#pause').click();
      await page.waitForFunction(()=>window.sceneView.paused);
      const sample=await page.evaluate(()=>window.sceneView.frames.at(-1).sample);
      assert.equal(sample.right_turn_signal,color);
      assert.ok(Object.values(sample.movement_signals.E).every(v=>v==='G'));
      assert.equal(sample.movement_signals[arm].r,color);
      assert.equal(sample.movement_signals[arm].s,'r');
      assert.equal(sample.movement_signals[arm].l,'r');
      assert.equal(sample.movement_signals[arm==='S'?'N':'S'].r,'r');
      await page.locator('.scene-card').screenshot({path:path.join(out,'derecha_'+arm+'.png')});
      await page.locator('#pause').click();
    }
    await page.locator('#speed').selectOption('100');
    await page.waitForFunction(()=>window.sceneView.status==='complete',null,{timeout:60000});
    const state=await(await page.request.get(new URL('/api/state',page.url()).href)).json();
    assert.equal(state.summary.collisions,0);assert.equal(state.summary.teleports,0);
    await page.getByRole('button',{name:'Comparar resultados',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('#movement-results-body tr').length===2);
    assert.equal(await page.locator('#mixed-results-body tr').count(),12);
    await page.screenshot({path:path.join(out,'resultados_actuales.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert.deepEqual(errors,[]);
    const report={passed:true,checks:['este conserva todos sus movimientos','sur y norte abren por separado','norte cede el paso','recto e izquierda de la entrada auxiliar siguen rojos','ejecución completa sin incidentes','tablas cortas y largas separadas','vista móvil sin desbordamiento','sin errores JavaScript']};
    fs.writeFileSync(path.join(out,'prueba_derechas.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
