(function(){
  'use strict';
  let timer=null,level=0;
  function target(){return document.getElementById('liam-avatar-wrap')}
  function start(){stop();const avatar=target();if(!avatar)return false;timer=setInterval(()=>{level=level>.5?.18:.82;avatar.style.setProperty('--liam-mouth',String(level))},110);return true}
  function update(value){level=Math.max(0,Math.min(1,Number(value)||0));target()?.style.setProperty('--liam-mouth',String(level))}
  function stop(){if(timer)clearInterval(timer);timer=null;level=0;target()?.style.setProperty('--liam-mouth','0')}
  window.LIAM_LIP_SYNC=Object.freeze({start,update,stop,isSupported:()=>Boolean(document.documentElement.style.setProperty)});
})();
