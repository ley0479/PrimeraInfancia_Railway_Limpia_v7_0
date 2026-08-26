(function(){
  'use strict';
  const modes=new Set(['none','walk','teleport','return_home']);let active=null;
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  function remove(){active?.getAnimations?.().forEach(a=>a.cancel());active?.remove();active=null;document.getElementById('liam-avatar-wrap')?.classList.remove('ian-panel-avatar-away')}
  function create(){remove();const source=document.querySelector('#liam-avatar-wrap .ian-avatar-svg');if(!source)return null;active=document.createElement('div');active.id='ian-tour-avatar';active.className='ian-tour-avatar';active.setAttribute('aria-hidden','true');active.appendChild(source.cloneNode(true));document.body.appendChild(active);document.getElementById('liam-avatar-wrap')?.classList.add('ian-panel-avatar-away');return active}
  function state(next){window.LIAM_STATE?.set(next);if(active)active.dataset.state=next}
  async function moveToControl(helpId,options={}){
    const control=window.LIAM_CONTROLS?.resolve(helpId);if(!control)return false;control.scrollIntoView({behavior:reduced()?'auto':'smooth',block:'center'});await new Promise(resolve=>setTimeout(resolve,reduced()?0:260));
    const target=control.getBoundingClientRect(),avatar=create();if(!avatar)return false;const size={width:170,height:220};const place=window.LIAM_SAFE_ZONES?.placement(target,size,16)||{side:'home',left:innerWidth-188,top:innerHeight-238};const home={left:Math.max(8,innerWidth-190),top:Math.max(8,innerHeight-238)};avatar.style.left=`${home.left}px`;avatar.style.top=`${home.top}px`;
    const canWalk=(options.mode||'walk')==='walk'&&options.walk_enabled!==false&&innerWidth>1024&&!reduced()&&place.side!=='home';
    if(canWalk){const dx=place.left-home.left,dy=place.top-home.top,direction=Math.abs(dx)>=Math.abs(dy)?(dx<0?'walking_left':'walking_right'):(dy<0?'walking_up':'walking_down');state(direction);const animation=avatar.animate([{transform:'translate(0,0)'},{transform:`translate(${dx}px,${dy}px)`}],{duration:Math.min(1500,Math.max(650,Math.hypot(dx,dy)*1.25)),easing:'ease-in-out',fill:'forwards'});await animation.finished.catch(()=>{});avatar.style.left=`${place.left}px`;avatar.style.top=`${place.top}px`;avatar.style.transform='none';animation.cancel()}else{state('teleport_out');avatar.style.opacity='0';await new Promise(r=>setTimeout(r,reduced()?0:160));avatar.style.left=`${place.left}px`;avatar.style.top=`${place.top}px`;avatar.style.opacity='1';state('teleport_in');await new Promise(r=>setTimeout(r,reduced()?0:220))}
    const avatarRect=avatar.getBoundingClientRect(),targetCenter=target.left+target.width/2,avatarCenter=avatarRect.left+avatarRect.width/2;state(targetCenter<avatarCenter?'pointing_left':'pointing_right');window.LIAM_ANIMATION?.highlight(helpId,options.message||'Herramienta señalada por IAN');return true;
  }
  async function move(command={},flags={}){if(!modes.has(command.mode))return false;if(command.mode==='none')return true;if(command.mode==='return_home'){remove();state('idle');return true}const anchor=window.LIAM_ANCHORS?.get(command.destination);return anchor?moveToControl(anchor.control,{...flags,mode:command.mode,message:command.message}):false}
  window.LIAM_MOVEMENT=Object.freeze({move,moveToControl,remove,modes:Object.freeze([...modes])});
})();
