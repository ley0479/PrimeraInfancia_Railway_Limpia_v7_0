(function(){
  'use strict';
  const tours={
    'dashboard.platform':[
      {control:'dashboard.cuentame.upload',anchor:'liam.anchor.dashboard.cuentame',message:'Carga la fuente Cuéntame autorizada. El sistema validará el archivo antes de publicar información.'},
      {control:'dashboard.talent-human.open',anchor:'liam.anchor.dashboard.talent-human',message:'Talento Humano relaciona coordinadores, docentes y equipos con sus unidades.'},
      {control:'dashboard.nutrition.open',anchor:'liam.anchor.dashboard.nutrition',message:'Salud y Nutrición reúne seguimiento, alertas, actividades y reportes autorizados.'},
      {control:'dashboard.calendar.open',anchor:'liam.anchor.dashboard.calendar',message:'El Calendario muestra actividades, vencimientos, evidencias y estados.'},
      {control:'dashboard.document-engine.open',anchor:'liam.anchor.dashboard.document-engine',message:'El Motor Documental lee, valida y propone mapeos sujetos a revisión humana.'},
      {control:'dashboard.formats.open',anchor:'liam.anchor.dashboard.formats',message:'Formatos permite generar productos únicamente con datos confirmados por el sistema.'}
    ]
  };let active=null,index=0,flags={};
  async function show(){const step=active?.[index];if(!step)return finish();await window.LIAM_MOVEMENT.move({mode:flags.walk_enabled?'walk':'teleport',destination:step.anchor,duration_ms:800},flags);window.LIAM_TABLET?.show({type:'progress',title:`Paso ${index+1} de ${active.length}`,value:Math.round((index+1)*100/active.length)});window.LIAM?.announce?.(step.message);window.LIAM_ANIMATION?.highlight(step.control,step.message);document.dispatchEvent(new CustomEvent('liam:tour-step',{detail:{index,total:active.length,control:step.control}}));return true}
  function start(id,nextFlags={}){active=tours[id]||null;index=0;flags=nextFlags;if(!active)return false;show();return true}
  function next(){if(!active)return false;index+=1;show();return true}
  function previous(){if(!active)return false;index=Math.max(0,index-1);show();return true}
  function finish(){window.LIAM_ANIMATION?.clear();window.LIAM_STATE?.set('success');active=null;index=0;document.dispatchEvent(new CustomEvent('liam:tour-completed'));return true}
  function cancel(){window.LIAM_ANIMATION?.clear();active=null;index=0;window.LIAM_STATE?.set('idle')}
  window.LIAM_TOURS=Object.freeze({start,next,previous,cancel,ids:Object.freeze(Object.keys(tours))});
})();
