(function(){
  'use strict';
  let timer=null,sequence=[],index=0,paused=false;
  const root=()=>document.documentElement;
  function paint(value){root().style.setProperty('--liam-mouth',String(Math.max(.05,Math.min(1.8,value))))}
  function shapeFor(c){return /[aáeé]/.test(c)?1.55:/[oóuú]/.test(c)?1.15:/[bmp]/.test(c)?.12:.72}
  function shapes(text){return String(text||'').toLowerCase().split('').filter(c=>/[a-záéíóúüñ]/.test(c)).map(shapeFor)}
  function tick(){if(paused||!sequence.length)return;paint(sequence[index%sequence.length]);index+=1}
  function start(text=''){stop();sequence=shapes(text);if(!sequence.length)sequence=[.3,1.15,.55,1.45];paint(sequence[0]);timer=setInterval(tick,95);return true}
  function update(value){paint(Number(value)||.3)}
  function pause(){paused=true;paint(.08)}
  function resume(text){if(text)sequence=shapes(text);paused=false;if(!timer)timer=setInterval(tick,95);tick()}
  function stop(){if(timer)clearInterval(timer);timer=null;sequence=[];index=0;paused=false;paint(.05)}
  document.addEventListener('ian:speech:boundary',event=>{if(!paused&&sequence.length){index=Math.max(0,Number(event.detail?.charIndex)||index);tick()}});
  document.addEventListener('ian:speech:viseme',event=>{if(!paused)update(event.detail?.openness)});
  window.LIAM_LIP_SYNC=Object.freeze({start,update,pause,resume,stop,isSupported:()=>Boolean(root().style?.setProperty),mode:'timed-text-fallback'});
})();
