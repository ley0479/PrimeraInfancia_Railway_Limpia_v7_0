(function(){
  'use strict';
  let tour=null,index=0,status='not_started',mode='automatic',paused=false,options={},identityPresented=false;
  const primaryControl={dashboard:'dashboard.cuentame.upload','base-maestra':'base-maestra.file.upload',talento:'talento.file.select','salud-nutricion':'salud-nutricion.tab.dashboard','calendario-inteligente':'calendario.pending.list','motor-documental':'motor-documental.file.upload','planeacion-pedagogica':'planeacion-pedagogica.period','gestion-pedagogica':'gestion-pedagogica.dashboard','componente-psicosocial':'componente-psicosocial.unit','familias-redes':'familias-redes.unit',formatos:'formatos.template.type','reportes-gerenciales':'reportes.period','relacion-mes':'relacion-mes.period','expediente-operativo-uca':'expediente-uca.year',administracion:'administracion.foundation.form',facturacion:'facturacion.dashboard','integrity-stability':'integrity.summary','manual-operativo':'manual.current'};
  const emit=(name,detail={})=>document.dispatchEvent(new CustomEvent(`elian:${name}`,{detail}));
  const current=()=>tour?.modules?.[index]||null;
  const messageFor=m=>[
    `${m.title}. ${m.purpose}`,
    `Quién puede utilizarlo: ${m.authorized_users}`,
    `Información requerida: ${(m.inputs||[]).join('; ')}.`,
    `Origen de los datos: ${m.data_source}`,
    `Validaciones: ${(m.validations||[]).join('; ')}.`,
    `Resultado: ${m.outputs}`,
    `Dónde se utiliza: ${m.downstream_use}`,
    `Errores frecuentes: ${(m.frequent_errors||[]).join('; ')||'consulta los mensajes estructurados de la pantalla'}.`,
    `Siguiente paso: ${m.next_step}`
  ].join(' ');
  async function save(nextStatus=status){
    if(!tour)return;
    const completed=tour.completed_modules||[],skipped=tour.skipped_modules||[];
    const body={status:nextStatus,mode,current_module_id:current()?.module_id||'',current_step:index,completed_modules:completed,skipped_modules:skipped};
    try{const data=await options.request('/elian/platform-tour/progress',{method:'PUT',body:JSON.stringify(body)});tour.progress=data.progress}catch(error){emit('tour-failed',{reason:'progress',message:error.message})}
  }
  function render(){
    const m=current(),total=tour?.modules?.length||0,pct=total?Math.round((Math.min(index,total))*100/total):0;
    window.LIAM_TABLET?.show({type:'progress',title:m?`${m.title} · ${index+1} de ${total}`:'Recorrido ELIAN',value:pct,label:`${pct} %`});
    const label=document.getElementById('elian-tour-status');if(label)label.textContent=m?`Módulo ${index+1} de ${total}: ${m.title} · ${pct} %`:'Recorrido finalizado';
  }
  async function waitReady(module){
    emit('module-open-requested',{module_id:module.module_id,route:module.route});emit('module-loading',{module_id:module.module_id});
    if(typeof window.mostrarSeccion!=='function')throw new Error('La navegación segura de la plataforma no está disponible.');
    window.LIAM_STATE?.set('teleport_out');window.mostrarSeccion(module.route);
    const deadline=Date.now()+15000;
    while(Date.now()<deadline){
      const active=(location.hash.replace(/^#/,'')||'dashboard')===module.route;
      if(active){await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);emit('module-ready',{module_id:module.module_id});window.LIAM_STATE?.set('teleport_in');return;}
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    throw new Error(`El módulo ${module.title} no confirmó que la pantalla estuviera lista.`);
  }
  async function present(){
    const module=current();if(!module)return finish();if(paused||status!=='in_progress')return;
    render();
    try{
      await waitReady(module);emit('module-guide-started',{module_id:module.module_id,index,total:tour.modules.length});
      window.LIAM_STATE?.set('guiding');
      const text=messageFor(module),control=primaryControl[module.module_id];if(control)await window.LIAM_MOVEMENT?.moveToControl(control,{mode:'walk',walk_enabled:true,message:`Herramienta principal de ${module.title}`});await options.announceAsync(text);window.LIAM_ANIMATION?.clear();window.LIAM_MOVEMENT?.remove();
      emit('module-guide-completed',{module_id:module.module_id,index});
      if(!tour.completed_modules.includes(module.module_id))tour.completed_modules.push(module.module_id);
      await save('in_progress');
      if(mode==='automatic'&&!paused){index+=1;return present()}
    }catch(error){status='paused';paused=true;await save('paused');options.announce(`No pude continuar con ${module.title}: ${error.message} Puedes reintentar o saltar este módulo.`);emit('tour-failed',{module_id:module.module_id,message:error.message})}
  }
  async function start(data,nextOptions={}){
    identityPresented=false;
    tour={...data,completed_modules:[...(data.progress?.completed_modules||[])],skipped_modules:[...(data.progress?.skipped_modules||[])]};options=nextOptions;mode=nextOptions.mode||data.progress?.mode||'automatic';
    const saved=data.progress?.current_module_id;index=Math.max(0,saved?data.modules.findIndex(m=>m.module_id===saved):0);if(index<0)index=0;status='in_progress';paused=false;
    const profile=data.profile||{};if(!profile.designer||!profile.created_date)throw new Error('La identidad institucional debe indicar diseñador y fecha de creación antes de iniciar el recorrido.');
    emit('tour-started',{tour_id:data.tour_id,total:data.modules.length,mode});await save('in_progress');
    if(!identityPresented){identityPresented=true;const collaboration=profile.development_contributor?` Contó con la colaboración de ${profile.development_contributor} en su desarrollo.`:'';const introduction=`Comencemos. Esta es ${profile.name}. Esta plataforma fue diseñada por ${profile.designer} y fue creada el ${profile.created_date}.${collaboration} Su versión actual es ${profile.version||'la versión institucional configurada'}. ${profile.description||'Su propósito es apoyar la gestión integral de Primera Infancia.'} A continuación conocerás solamente los módulos autorizados para tu rol.`;window.LIAM_STATE?.set('greeting');await options.announceAsync(introduction);}
    options.enterPresenter?.();
    return present();
  }
  async function pause(){if(!tour)return false;paused=true;status='paused';window.LIA_SPEECH?.pause();await save('paused');emit('module-guide-paused',{module_id:current()?.module_id});render();return true}
  async function resume(){if(!tour)return false;paused=false;status='in_progress';window.LIA_SPEECH?.resume();await save('in_progress');emit('module-guide-resumed',{module_id:current()?.module_id});return present()}
  async function next(){if(!tour)return false;window.LIA_SPEECH?.stop();index=Math.min(index+1,tour.modules.length);paused=false;status='in_progress';await save('in_progress');return present()}
  async function previous(){if(!tour)return false;window.LIA_SPEECH?.stop();index=Math.max(0,index-1);paused=false;status='in_progress';await save('in_progress');return present()}
  async function repeat(){if(!tour)return false;window.LIA_SPEECH?.stop();paused=false;status='in_progress';return present()}
  async function skip(){const m=current();if(!m)return false;if(!tour.skipped_modules.includes(m.module_id))tour.skipped_modules.push(m.module_id);emit('module-guide-skipped',{module_id:m.module_id});return next()}
  async function cancel(){if(!tour)return false;paused=true;status='cancelled';window.LIA_SPEECH?.stop();await save('cancelled');window.LIAM_ANIMATION?.clear();window.LIAM_MOVEMENT?.remove();emit('tour-cancelled',{});return true}
  async function finish(){status='completed';paused=false;await save('completed');render();window.LIAM_STATE?.set('success');await options.announceAsync(`Recorrido completado. Conociste ${tour.completed_modules.length} módulos y omitiste ${tour.skipped_modules.length}. Puedes repetirlo o iniciar una tarea real.`);emit('tour-completed',{completed:tour.completed_modules.length,skipped:tour.skipped_modules.length});return true}
  window.ELIAN_PLATFORM_TOUR=Object.freeze({start,pause,resume,next,previous,repeat,skip,cancel,state:()=>({status,mode,index,module:current()})});
})();
