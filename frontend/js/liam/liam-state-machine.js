(function(){
  'use strict';
  const states=new Set(['hidden','loading','idle','greeting','listening','thinking','speaking','guiding','walking_left','walking_right','turning_left','turning_right','pointing_left','pointing_right','pointing_up','pointing_down','reading_tablet','teleport_out','teleport_in','success','warning','error','offline','muted','sleeping']);
  const listeners=new Set();let current='hidden';
  function set(next){if(!states.has(next))return false;if(current==='hidden'&&/^walking_/.test(next))return false;current=next;listeners.forEach(fn=>fn(next));return true}
  function subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn)}
  window.LIAM_STATE=Object.freeze({set,get:()=>current,subscribe,states:Object.freeze([...states])});
})();
