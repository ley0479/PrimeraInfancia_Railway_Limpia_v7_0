const {test,expect}=require('@playwright/test');
test.setTimeout(90000);
test.use({channel:'msedge'});

async function installRenderer(page){
  await page.evaluate(()=>{
    document.body.innerHTML='<div id="liam-avatar-wrap" class="liam-avatar-wrap"><img class="ian-avatar-visual" alt=""></div>';
    const listeners=new Set();let state='idle';
    window.LIAM_STATE={
      get:()=>state,
      set:value=>{state=value;listeners.forEach(listener=>listener(value));},
      subscribe:listener=>{listeners.add(listener);return()=>listeners.delete(listener)}
    };
  });
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/liam-3d-renderer.js'});
  await page.waitForFunction(()=>Boolean(window.LIAM_3D));
}

for(const device of [
  {name:'desktop',viewport:{width:900,height:700},asset:'liam-lector.glb'},
  {name:'mobile',viewport:{width:390,height:844},asset:'liam-lector-movil.glb'}
]){
  test(`LIAM lector ${device.name}: un visor, estático y texturizado`,async({page})=>{
    await page.setViewportSize(device.viewport);
    const requests=[];
    page.on('request',request=>{if(/liam-lector(?:-movil)?\.glb/.test(request.url()))requests.push(request.url())});
    const assetResponse=page.waitForResponse(response=>response.url().includes(device.asset));
    await page.goto('http://127.0.0.1:8765/theme-lab/liam-3d.html');
    const labViewer=page.locator('#liam');
    expect((await assetResponse).status()).toBe(200);
    await expect(labViewer).toHaveAttribute('src',new RegExp(device.asset.replace('.','\\.')));
    expect(requests.some(url=>url.includes(device.asset))).toBe(true);
    expect(requests.filter(url=>/liam-lector(?:-movil)?\.glb/.test(url))).toHaveLength(1);

    await installRenderer(page);
    await page.evaluate(()=>window.LIAM_3D.mount('#liam-avatar-wrap',{enabled:true,gender:'male'}));
    await expect.poll(()=>page.locator('#liam-avatar-wrap').getAttribute('data-liam3d'),{timeout:35000}).toMatch(/model|poster/);
    const visualCount=await page.locator('#liam-avatar-wrap model-viewer, #liam-avatar-wrap .liam-lector-poster').count();
    expect(visualCount).toBe(1);
    const loaded=await page.locator('#liam-avatar-wrap').getAttribute('data-liam3d');
    if(loaded==='model')expect(await page.locator('#liam-avatar-wrap model-viewer').evaluate(element=>[...element.availableAnimations])).toEqual([]);
    await page.evaluate(()=>window.LIAM_STATE.set('speaking'));
    await expect(page.locator('#liam-avatar-wrap')).toHaveAttribute('data-liam-lector-state','speaking');
    await page.evaluate(()=>window.LIAM_3D.mount('#liam-avatar-wrap',{enabled:true,gender:'male'}));
    expect(await page.locator('#liam-avatar-wrap model-viewer, #liam-avatar-wrap .liam-lector-poster').count()).toBe(1);
    await page.evaluate(()=>window.LIAM_3D.unmount());
    await expect(page.locator('#liam-avatar-wrap model-viewer, #liam-avatar-wrap .liam-lector-poster')).toHaveCount(0);
  });
}

test('LIAM lector corresponde al perfil masculino y conserva el femenino',async({page})=>{
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  const result=await page.evaluate(async()=>({
    renderer:await (await fetch('../js/liam/liam-3d-renderer.js')).text(),
    controller:await (await fetch('../js/liam/liam-controller.js')).text()
  }));
  expect(result.renderer).toContain('liam-mujer-v1.glb');
  expect(result.renderer).toContain('liam-lector.glb');
  expect(result.controller).toContain('<option value="male">Hombre</option>');
});

test('LIAM lector degrada a la imagen frontal si falla el GLB',async({page})=>{
  await page.route(/liam-lector(?:-movil)?\.glb/,route=>route.abort());
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await installRenderer(page);
  await page.evaluate(()=>window.LIAM_3D.mount('#liam-avatar-wrap',{enabled:true,gender:'male'}));
  await expect(page.locator('#liam-avatar-wrap .liam-lector-poster')).toHaveCount(1,{timeout:30000});
  await expect(page.locator('#liam-avatar-wrap')).toHaveAttribute('data-liam3d','poster');
});

test('la voz existente sigue siendo única y detener la cancela (audio simulado)',async({page})=>{
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await page.evaluate(()=>{
    const spoken=[];
    window.__speechTest={spoken,cancels:0,state:'idle'};
    const synth={
      getVoices:()=>[{name:'Voz local',voiceURI:'local',lang:'es-CO',localService:true}],
      speak:utterance=>spoken.push(utterance),cancel:()=>window.__speechTest.cancels++,pause(){},resume(){}
    };
    Object.defineProperty(window,'speechSynthesis',{configurable:true,value:synth});
    Object.defineProperty(window,'SpeechSynthesisUtterance',{configurable:true,value:class{constructor(text){this.text=text}}});
    window.LIA_AVATAR={setState:()=>{}};window.LIAM_LIP_SYNC={start(){},stop(){}};
    window.LIAM_STATE={set:value=>window.__speechTest.state=value};
  });
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/lia-assistant/speech-controller.js'});
  expect(await page.evaluate(()=>window.LIA_SPEECH.speak('Explicación autorizada'))).toBe(true);
  expect(await page.evaluate(()=>window.__speechTest.spoken.length)).toBe(1);
  await page.evaluate(()=>window.__speechTest.spoken[0].onstart());
  expect(await page.evaluate(()=>window.__speechTest.state)).toBe('speaking');
  await page.evaluate(()=>window.LIA_SPEECH.stop());
  expect(await page.evaluate(()=>window.__speechTest.cancels)).toBe(2);
  expect(await page.evaluate(()=>window.__speechTest.state)).toBe('idle');
});

test('el recorrido desplaza una sola copia del avatar 2D por poses',async({page})=>{
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await page.evaluate(()=>{
    document.body.innerHTML='<div id="liam-avatar-wrap"><span class="ian-avatar-2d ian-avatar-visual"><img class="ian-pose ian-pose-neutral" src="./assets/lia/2d/liam-male-neutral-v1.png"></span></div><button id="target">Destino</button>';
    window.LIAM_CONTROLS={resolve:()=>document.getElementById('target')};
    window.LIAM_SAFE_ZONES={placement:()=>({side:'right',left:20,top:20})};
    window.LIAM_ANIMATION={highlight:()=>true};window.LIAM_STATE={set:()=>{}};
  });
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/liam-movement-controller.js'});
  await page.evaluate(()=>window.LIAM_MOVEMENT.moveToControl('destino',{mode:'teleport',walk_enabled:false}));
  await expect(page.locator('#ian-tour-avatar .ian-avatar-2d')).toHaveCount(1);
  await expect(page.locator('.ian-avatar-2d')).toHaveCount(2);
  await page.evaluate(()=>window.LIAM_MOVEMENT.remove());
  await expect(page.locator('#ian-tour-avatar')).toHaveCount(0);
});

test('LÍA 2D cambia entre reposo, lectura y señalamiento con transparencia',async({page})=>{
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await page.addStyleTag({url:'http://127.0.0.1:8765/css/ian-avatar.css'});
  await page.evaluate(()=>{document.head.insertAdjacentHTML('afterbegin','<base href="/">');document.body.innerHTML='<div id="liam-avatar-wrap" class="liam-avatar-wrap" data-state="idle" style="width:290px;height:302px"></div>'});
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/ian-avatar-renderer.js'});
  await page.evaluate(()=>window.IAN_AVATAR.render('#liam-avatar-wrap',{gender:'female'}));
  await expect(page.locator('#liam-avatar-wrap .ian-pose')).toHaveCount(4);
  await expect(page.locator('.ian-pose-neutral')).toBeVisible();
  await page.locator('#liam-avatar-wrap').evaluate(node=>node.dataset.state='speaking');
  await expect(page.locator('.ian-pose-reading')).toBeVisible();
  await page.locator('#liam-avatar-wrap').evaluate(node=>node.dataset.state='pointing_left');
  await expect(page.locator('.ian-pose-left')).toBeVisible();
});

test('el lanzador 2D de respaldo aparece si el montaje autenticado tarda',async({page})=>{
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await page.evaluate(()=>{document.head.insertAdjacentHTML('afterbegin','<base href="/">');document.body.innerHTML='<main id="app-shell"></main>'});
  await page.addStyleTag({url:'http://127.0.0.1:8765/css/ian-avatar.css'});
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/ian-avatar-renderer.js'});
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/ian-visibility-guard.js'});
  await expect(page.locator('#ian-visibility-fallback .ian-avatar-2d')).toBeVisible({timeout:4000});
});

test('la vista previa administrativa usa el mismo avatar 2D seleccionado',async({page})=>{
  await page.route('**/api/asistente-capacitacion/elian/visual-config',route=>route.fulfill({json:{configuration:{assistant_name:'LIAM',avatar_gender:'female',avatar_variant:'afro_colombian_institutional'},editable:true}}));
  await page.goto('http://127.0.0.1:8765/theme-lab/index.html');
  await page.evaluate(()=>{document.head.insertAdjacentHTML('afterbegin','<base href="/">');document.body.innerHTML='<section id="elian-admin-config"><img id="elian-admin-preview"><select id="elian-config-gender"><option value="female">Mujer</option><option value="male">Hombre</option></select><select id="elian-config-variant"><option value="afro_colombian_institutional">Institucional</option></select><input id="elian-config-name"><select id="elian-config-motion"><option value="full">Completo</option></select><select id="elian-config-voice"><option value="female">Femenina</option></select><input id="elian-config-speed"><input id="elian-config-hologram" type="checkbox"><input id="elian-config-tablet" type="checkbox"><span id="elian-config-message"></span></section>'});
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/ian-avatar-renderer.js'});
  await page.addScriptTag({url:'http://127.0.0.1:8765/js/liam/elian-admin-config.js'});
  await page.evaluate(()=>document.dispatchEvent(new Event('DOMContentLoaded')));
  await expect(page.locator('#elian-admin-preview')).toHaveAttribute('src',/lia-female-neutral-v1\.png/);
  await page.locator('#elian-config-gender').selectOption('male');
  await expect(page.locator('#elian-admin-preview')).toHaveAttribute('src',/liam-male-neutral-v1\.png/);
});

test('el panel real abre, cierra y reabre sin duplicar asistente ni controles',async({page})=>{
  await page.route(/^https:\/\//,route=>route.abort());
  await page.addInitScript(()=>sessionStorage.setItem('primeraInfanciaAuthToken','token-prueba-visual'));
  await page.route('**/api/asistente-capacitacion/config',route=>route.fulfill({json:{elian:{enabled:true,avatar_3d_enabled:true,voice_enabled:false,hologram_enabled:false,platform_tour_enabled:false,tours_enabled:true,walk_enabled:true},platform_profile:{}}}));
  await page.route('**/api/asistente-capacitacion/elian/visual-config',route=>route.fulfill({json:{configuration:{assistant_name:'LIAM',avatar_gender:'female',avatar_variant:'afro_colombian_institutional',voice_gender:'female',voice_speed:.95,motion_level:'full'},editable:true}}));
  await page.route('**/api/asistente-capacitacion/contexto**',route=>route.fulfill({json:{rol:'SUPERADMIN',guia:{titulo:'Centro de control',resumen:'Explicación autorizada.',pasos:['Revisar la pantalla.']}}}));
  await page.goto('http://127.0.0.1:8765/index.html',{waitUntil:'domcontentloaded',timeout:75000});
  const tab=page.locator('#liam-tab');await expect(tab).toBeVisible({timeout:20000});
  await expect(tab.locator('.ian-avatar-2d')).toBeVisible();
  await expect(tab.locator('.ian-pose-neutral')).toBeVisible();
  await tab.click();
  await expect(page.locator('#liam-panel')).toBeVisible();
  await expect(page.locator('#liam-conversation')).toHaveCount(1);
  await expect(page.locator('[data-action="stop"]')).toHaveCount(1);
  await expect(page.locator('#liam-avatar-wrap .ian-avatar-2d')).toHaveCount(1);
  await expect(page.locator('#liam-avatar-wrap .ian-pose-neutral')).toHaveAttribute('src',/lia-female-neutral-v1\.png/);
  await page.locator('#liam-close').click();await expect(page.locator('#liam-panel')).toBeHidden();
  await expect(page.locator('#liam-avatar-wrap .ian-avatar-2d')).toHaveCount(1);
  await tab.click();await expect(page.locator('#liam-panel')).toBeVisible();
  expect(await page.locator('#liam-shell')).toHaveCount(1);
  expect(await page.locator('#liam-avatar-wrap .ian-avatar-2d').count()).toBe(1);
});
