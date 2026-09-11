(function(){
  'use strict';
  const ENGINE='./vendor/model-viewer/model-viewer-4.3.1.min.js';
  const MODEL='./assets/lia/3d/liam-semireal-v5.glb';
  const animationByState={
    idle:'Idle',sleeping:'Idle',greeting:'Wave',guiding:'Point',
    pointing_left:'Point',pointing_right:'Point',pointing_up:'Point',pointing_down:'Point',
    speaking:'Talk',listening:'Listen',thinking:'Think',walking_left:'Walk',walking_right:'Walk',
    walking_up:'Walk',walking_down:'Walk',success:'Wave',goodbye:'Wave'
  };
  let enginePromise=null,viewer=null,unsubscribe=null,frameQuery=null,frameListener=null,lastDecision={allowed:false,reason:'not_evaluated'};
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
  function animate(state){
    if(!viewer)return;const clip=animationByState[state]||'Idle';
    if(viewer.animationName!==clip)viewer.animationName=clip;
    viewer.play?.({repetitions:clip==='Wave'||clip==='Point'?2:Infinity}).catch?.(()=>{});
  }
  function frame(){
    if(!viewer)return;const compact=frameQuery?.matches;
    viewer.setAttribute('camera-target',compact?'0m 1.48m 0m':'auto auto auto');
    viewer.setAttribute('camera-orbit',compact?'8deg 82deg 2.55m':'12deg 82deg 3.9m');
    viewer.setAttribute('field-of-view',compact?'25deg':'28deg');
  }
  async function mount(target,options={}){
    const host=typeof target==='string'?document.querySelector(target):target;
    lastDecision=capability(Boolean(options.enabled));
    if(host)host.dataset.liam3d=lastDecision.reason;
    if(!host||!lastDecision.allowed)return false;
    if(viewer?.isConnected)return true;
    try{await loadEngine()}catch(_){return false}
    viewer=document.createElement('model-viewer');
    viewer.className='liam-model-viewer';viewer.src=MODEL;viewer.alt='LIAM, asistente virtual 3D';
    frameQuery=matchMedia('(max-width: 768px)');frameListener=()=>frame();frameQuery.addEventListener?.('change',frameListener);
    frame();
    viewer.setAttribute('interaction-prompt','none');viewer.setAttribute('shadow-intensity','0.75');
    viewer.setAttribute('environment-image','neutral');viewer.setAttribute('autoplay','');
    viewer.addEventListener('load',()=>{host.classList.add('liam-3d-ready');animate(window.LIAM_STATE?.get?.()||'Idle')},{once:true});
    viewer.addEventListener('error',()=>{host.classList.remove('liam-3d-ready');viewer?.remove();viewer=null},{once:true});
    host.appendChild(viewer);unsubscribe?.();unsubscribe=window.LIAM_STATE?.subscribe?.(animate)||null;
    return true;
  }
  function unmount(){unsubscribe?.();unsubscribe=null;frameQuery?.removeEventListener?.('change',frameListener);frameQuery=null;frameListener=null;viewer?.pause?.();viewer?.remove();viewer=null;const host=document.querySelector('#liam-avatar-wrap');host?.classList.remove('liam-3d-ready');if(host)host.dataset.liam3d='released'}
  window.LIAM_3D=Object.freeze({mount,unmount,animate,capability,status:()=>({...lastDecision})});
})();
