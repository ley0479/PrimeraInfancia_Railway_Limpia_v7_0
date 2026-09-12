(function(){
  'use strict';
  const ENGINE='./vendor/model-viewer/model-viewer-4.3.1.min.js';
  const ASSETS=Object.freeze({
    female:Object.freeze({
      desktop:'./assets/lia/3d/liam-lector.glb?v=lector-estatico-1',
      mobile:'./assets/lia/3d/liam-lector-movil.glb?v=lector-estatico-1',
      poster:'./assets/lia/3d/liam-lector-frontal.png?v=lector-estatico-1',
      static:true
    }),
    male:Object.freeze({
      desktop:'./assets/lia/3d/iam-hombre-v1.glb?v=texture-webgl-3',
      mobile:'./assets/lia/3d/iam-hombre-v1.glb?v=texture-webgl-3',
      poster:'',
      static:true
    })
  });
  let enginePromise=null,viewer=null,poster=null,unsubscribe=null,loadTimer=null,currentGender='female';
  let frameQuery=null,frameListener=null,lastDecision={allowed:false,reason:'not_evaluated'};
  function capability(enabled){
    if(!enabled)return {allowed:false,reason:'disabled'};
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)return {allowed:false,reason:'reduced_motion'};
    if(navigator.connection?.saveData)return {allowed:false,reason:'save_data'};
    if(Number(navigator.deviceMemory||4)<4)return {allowed:false,reason:'low_memory'};
    if(Number(navigator.hardwareConcurrency||4)<4)return {allowed:false,reason:'low_cpu'};
    const canvas=document.createElement('canvas');
    if(!canvas.getContext('webgl2')&&!canvas.getContext('webgl'))return {allowed:false,reason:'no_webgl'};
    return {allowed:true,reason:'ready'};
  }
  function loadEngine(){
    if(customElements.get('model-viewer'))return Promise.resolve();
    if(enginePromise)return enginePromise;
    enginePromise=new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.type='module';script.src=ENGINE;script.dataset.liam3dEngine='true';
      script.onload=()=>customElements.whenDefined('model-viewer').then(resolve);script.onerror=()=>reject(new Error('No se pudo cargar el visor 3D.'));
      document.head.appendChild(script);
    });
    return enginePromise;
  }
  function selectedSource(assets){
    const compact=matchMedia('(max-width: 768px)').matches;
    return compact||navigator.connection?.saveData?assets.mobile:assets.desktop;
  }
  function animate(state){
    const host=document.getElementById('liam-avatar-wrap');
    if(host)host.dataset.liamLectorState=String(state||'idle');
    // El lector es estático: el estado se comunica mediante el indicador visual.
    // El movimiento espacial continúa a cargo de LIAM_MOVEMENT sobre el contenedor.
  }
  function frame(){
    if(!viewer)return;const compact=frameQuery?.matches;
    viewer.setAttribute('camera-target','0m 0.42m 0m');
    viewer.setAttribute('camera-orbit',compact?'0deg 90deg 1.9m':'0deg 90deg 1.7m');
    viewer.setAttribute('field-of-view','36deg');
  }
  function showPoster(host,assets){
    clearTimeout(loadTimer);loadTimer=null;
    viewer?.remove();viewer=null;
    if(!assets.poster)return false;
    if(poster?.isConnected)return true;
    host.querySelectorAll(':scope > .liam-lector-poster').forEach(node=>node.remove());
    poster=document.createElement('img');poster.className='liam-lector-poster';poster.src=assets.poster;
    poster.alt='LIAM, vista frontal de respaldo del avatar lector';poster.decoding='async';
    host.appendChild(poster);host.classList.add('liam-3d-ready','liam-3d-static','liam-lector-ready');
    host.dataset.liam3d='poster';return true;
  }
  async function mount(target,options={}){
    const host=typeof target==='string'?document.querySelector(target):target;
    const gender=options.gender==='male'?'male':'female',assets=ASSETS[gender];
    lastDecision=capability(Boolean(options.enabled));
    if(host)host.dataset.liam3d=lastDecision.reason;
    if(!host||!lastDecision.allowed){if(viewer?.isConnected||poster?.isConnected)unmount();return false}
    if((viewer?.isConnected||poster?.isConnected)&&currentGender===gender)return true;
    if(viewer?.isConnected||poster?.isConnected)unmount();
    try{await loadEngine()}catch(_){return gender==='female'&&showPoster(host,assets)}
    viewer=document.createElement('model-viewer');currentGender=gender;
    host.classList.add('liam-3d-static');host.dataset.liamLectorPoster=assets.poster;
    viewer.className='liam-model-viewer';viewer.src=selectedSource(assets);viewer.alt=gender==='female'?'LIAM, avatar lector 3D estático':'LIAM hombre, asistente virtual 3D';
    if(assets.poster)viewer.poster=assets.poster;
    frameQuery=matchMedia('(max-width: 768px)');frameListener=()=>frame();frameQuery.addEventListener?.('change',frameListener);frame();
    viewer.setAttribute('interaction-prompt','none');viewer.setAttribute('shadow-intensity','0');viewer.setAttribute('environment-image','neutral');viewer.setAttribute('exposure','1');viewer.setAttribute('disable-pan','');viewer.setAttribute('disable-zoom','');viewer.setAttribute('camera-controls','');
    viewer.addEventListener('load',()=>{clearTimeout(loadTimer);loadTimer=null;host.classList.add('liam-3d-ready');if(gender==='female')host.classList.add('liam-lector-ready');host.dataset.liam3d='model';animate(window.LIAM_STATE?.get?.()||'idle')},{once:true});
    viewer.addEventListener('error',()=>{host.classList.remove('liam-3d-ready');if(gender==='female')showPoster(host,assets);else{viewer?.remove();viewer=null}},{once:true});
    host.appendChild(viewer);loadTimer=setTimeout(()=>{if(viewer&&!viewer.loaded){if(gender==='female')showPoster(host,assets);else{viewer.remove();viewer=null}}},25000);unsubscribe?.();unsubscribe=window.LIAM_STATE?.subscribe?.(animate)||null;
    return true;
  }
  function unmount(){
    unsubscribe?.();unsubscribe=null;clearTimeout(loadTimer);loadTimer=null;frameQuery?.removeEventListener?.('change',frameListener);frameQuery=null;frameListener=null;
    viewer?.pause?.();viewer?.remove();viewer=null;poster?.remove();poster=null;
    const host=document.querySelector('#liam-avatar-wrap');host?.classList.remove('liam-3d-ready','liam-3d-static','liam-lector-ready');
    if(host){delete host.dataset.liamLectorPoster;delete host.dataset.liamLectorState;host.dataset.liam3d='released'}
  }
  window.LIAM_3D=Object.freeze({mount,unmount,animate,capability,status:()=>({...lastDecision})});
})();
