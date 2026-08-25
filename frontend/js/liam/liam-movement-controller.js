(function(){
  'use strict';
  const modes=new Set(['none','walk','teleport','return_home']);
  async function move(command={},flags={}){if(!modes.has(command.mode))return false;if(command.mode==='none'||command.mode==='return_home')return true;const anchor=window.LIAM_ANCHORS?.get(command.destination);if(!anchor)return false;const control=window.LIAM_CONTROLS?.resolve(anchor.control);if(!control)return false;control.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});if(command.mode==='walk'&&flags.walk_enabled&&innerWidth>1024&&!matchMedia('(prefers-reduced-motion: reduce)').matches){window.LIAM_STATE.set(anchor.side==='left'?'walking_left':'walking_right');await new Promise(resolve=>setTimeout(resolve,Math.min(1400,Math.max(500,Number(command.duration_ms)||900))))}else{window.LIAM_STATE.set('teleport_out');await new Promise(resolve=>setTimeout(resolve,180));window.LIAM_STATE.set('teleport_in')}window.LIAM_ANIMATION?.highlight(anchor.control);window.LIAM_STATE.set(anchor.side==='left'?'pointing_right':'pointing_left');return true}
  window.LIAM_MOVEMENT=Object.freeze({move,modes:Object.freeze([...modes])});
})();
