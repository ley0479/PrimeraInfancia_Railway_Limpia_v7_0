(function(){
  'use strict';
  let timer=null,index=0,sequence=[],paused=false;
  const targets=()=>[document.getElementById('liam-avatar-wrap'),document.getElementById('ian-tour-avatar')].filter(Boolean);
  function shapeFor(char){if(/[.!?,;:\s]/.test(char))return 0;if(/[ou]/i.test(char))return .48;if(/[aá]/i.test(char))return 1;if(/[eéií]/i.test(char))return .72;return .34}
  function paint(value){targets().forEach(el=>el.style.setProperty('--liam-mouth',String(Math.max(0,Math.min(1,Number(value)||0)))));document.dispatchEvent(new CustomEvent('ian:speech:viseme',{detail:{value:Number(value)||0,index}}))}
  function tick(){if(paused||!sequence.length)return;paint(shapeFor(sequence[index%sequence.length]));index+=1}
  function start(text=''){stop();sequence=Array.from(String(text||'hablando')).slice(0,1200);if(!sequence.length)sequence=['a'];paused=false;tick();timer=setInterval(tick,105);return true}
  function update(value){paint(value)}
  function pause(){paused=true;paint(0)}
  function resume(text=''){if(text)sequence=Array.from(String(text));paused=false;tick();if(!timer)timer=setInterval(tick,105)}
  function stop(){if(timer)clearInterval(timer);timer=null;index=0;sequence=[];paused=false;paint(0)}
  window.LIAM_LIP_SYNC=Object.freeze({start,update,pause,resume,stop,isSupported:()=>Boolean(document.documentElement.style.setProperty),mode:'timed-text-fallback'});
})();
