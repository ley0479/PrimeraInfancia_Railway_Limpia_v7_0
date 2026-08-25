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
    ],
    'base-maestra.first-upload':[
      {control:'base-maestra.file.upload',anchor:'liam.anchor.base.upload',wait_for:'base-file-selected',message:'Selecciona una Base Cuéntame autorizada. El archivo todavía no se publica en este paso.'},
      {control:'base-maestra.units.search',anchor:'liam.anchor.base.search',message:'Después de la lectura puedes buscar y revisar las unidades detectadas.'},
      {control:'base-maestra.units.select-all',anchor:'liam.anchor.base.search',message:'Selecciona únicamente las unidades que realmente deseas procesar.'},
      {control:'base-maestra.units.process',anchor:'liam.anchor.base.process',message:'Procesa la selección cuando el resumen y las unidades sean correctos.'}
    ],
    'calendario.overview':[
      {control:'calendario.activity.create',anchor:'liam.anchor.calendar.create',message:'Crea un entregable manual cuando la actividad no provenga de otra fuente.'},
      {control:'calendario.schedule.upload',anchor:'liam.anchor.calendar.create',message:'También puedes cargar un cronograma y revisar las propuestas antes de guardarlas.'},
      {control:'calendario.view.month',anchor:'liam.anchor.calendar.view',message:'Cambia entre mes, semana, año y agenda según la consulta.'},
      {control:'calendario.pending.list',anchor:'liam.anchor.calendar.pending',message:'Aquí aparecen únicamente tus pendientes autorizados.'},
      {control:'calendario.alerts.list',anchor:'liam.anchor.calendar.pending',message:'Las alertas muestran vencimientos y situaciones que requieren atención.'}
    ],
    'motor-documental.first-read':[
      {control:'motor-documental.file.select',anchor:'liam.anchor.idp.select',wait_for:'document-file-selected',message:'Selecciona el documento original. El sistema conserva el archivo privado y valida su tipo.'},
      {control:'motor-documental.file.upload',anchor:'liam.anchor.idp.upload',wait_for:'document-received',message:'Cargar y analizar inicia la lectura; no aprueba ni importa información automáticamente.'},
      {control:'motor-documental.documents.list',anchor:'liam.anchor.idp.results',message:'Los documentos de la fundación aparecen en esta lista.'},
      {control:'motor-documental.document.detail',anchor:'liam.anchor.idp.results',message:'Revisa extracción, evidencias y validaciones antes de cualquier aprobación.'}
    ],
    'formatos.template-registration':[
      {control:'formatos.template.type',anchor:'liam.anchor.formats.type',message:'Selecciona el tipo real de plantilla oficial.'},
      {control:'formatos.template.file',anchor:'liam.anchor.formats.file',message:'Adjunta la plantilla sin modificar su estructura oficial.'},
      {control:'formatos.template.save',anchor:'liam.anchor.formats.save',message:'Guarda la plantilla para registrarla y conservar su versión.'},
      {control:'formatos.template.list',anchor:'liam.anchor.formats.save',message:'Comprueba aquí el estado y la versión registrada.'}
    ],
    'talento.overview':[
      {control:'talento.file.select',anchor:'liam.anchor.talent.file',wait_for:'talent-file-selected',message:'Selecciona la base autorizada de Talento Humano. Verifica que corresponda a la fundación y vigencia correctas.'},
      {control:'talento.file.upload',anchor:'liam.anchor.talent.file',message:'Guardar talento procesa el archivo; LIAM no activa este botón ni confirma información por ti.'},
      {control:'talento.sync.global',anchor:'liam.anchor.talent.sync',message:'La sincronización global propaga las asignaciones confirmadas a los módulos consumidores. Úsala después de revisar coordinadores, cargos y unidades.'},
      {control:'talento.manual.save',anchor:'liam.anchor.talent.sync',message:'El formulario manual permite corregir o agregar una persona verificada sin duplicar documentos.'},
      {control:'talento.people.list',anchor:'liam.anchor.talent.list',message:'La lista muestra el personal registrado. Revisa cargo, unidad, coordinador y estado antes de continuar.'}
    ],
    'salud-nutricion.overview':[
      {control:'salud-nutricion.tab.dashboard',anchor:'liam.anchor.nutrition.tabs',message:'El Dashboard resume indicadores de Salud y Nutrición sin reemplazar los registros fuente.'},
      {control:'salud-nutricion.tab.integral',anchor:'liam.anchor.nutrition.integral',message:'Expediente Integral organiza el seguimiento autorizado por participante y unidad.'},
      {control:'salud-nutricion.integral.unit-filter',anchor:'liam.anchor.nutrition.integral',message:'Filtra por UCA para evitar mezclar unidades durante la revisión.'},
      {control:'salud-nutricion.tab.alertas',anchor:'liam.anchor.nutrition.alerts',message:'Alertas reúne situaciones que requieren verificación profesional. Una alerta no constituye por sí sola un diagnóstico.'},
      {control:'salud-nutricion.tab.entregables',anchor:'liam.anchor.nutrition.deliverables',message:'Entregables permite consultar actividades, soportes y estados del componente.'}
    ],
    'planeacion-pedagogica.workflow':[
      {control:'planeacion-pedagogica.period',anchor:'liam.anchor.pedagogy.period',message:'Selecciona primero el periodo de trabajo. Este filtro organiza proyectos, planeaciones, evidencias y reportes.'},
      {control:'planeacion-pedagogica.tab.upload',anchor:'liam.anchor.pedagogy.upload',message:'En Cargar puedes adjuntar una planeación o crearla manualmente. Los hechos y responsables deben ser verificados por el profesional.'},
      {control:'planeacion-pedagogica.file',anchor:'liam.anchor.pedagogy.upload',message:'El archivo puede alimentar la planeación y proponer actividades en calendario; revisa unidad, docente, fecha, tema y objetivo antes de guardar.'},
      {control:'planeacion-pedagogica.tab.evidence',anchor:'liam.anchor.pedagogy.evidence',message:'En Evidencias vinculas soportes a una planeación existente, conservando la trazabilidad.'},
      {control:'planeacion-pedagogica.evidence.file',anchor:'liam.anchor.pedagogy.evidence',message:'Selecciona solamente una evidencia real y autorizada. LIAM no la carga ni la aprueba automáticamente.'}
    ],
    'gestion-pedagogica.overview':[
      {control:'gestion-pedagogica.dashboard',anchor:'liam.anchor.management.tabs',message:'El Dashboard resume coordinadores, entregables, documentos, cumplimiento y alertas.'},
      {control:'gestion-pedagogica.teams',anchor:'liam.anchor.management.tabs',message:'Equipos y Agentes se alimenta desde Talento Humano para evitar registros paralelos y duplicados.'},
      {control:'gestion-pedagogica.deliverables',anchor:'liam.anchor.management.deliverables',message:'Entregables organiza tipo, responsable, fecha límite, soporte y estado de revisión.'},
      {control:'gestion-pedagogica.calendar',anchor:'liam.anchor.management.deliverables',message:'Calendario presenta eventos pedagógicos y fechas de entrega relacionadas.'},
      {control:'gestion-pedagogica.alerts',anchor:'liam.anchor.management.deliverables',message:'Alertas permite identificar pendientes, vencimientos y devoluciones que requieren atención.'}
    ],
    'componente-psicosocial.overview':[
      {control:'componente-psicosocial.sync',anchor:'liam.anchor.psychosocial.sync',message:'Sincronizar expedientes reutiliza las fuentes autorizadas. No crea historias clínicas ni diagnósticos automáticos.'},
      {control:'componente-psicosocial.unit',anchor:'liam.anchor.psychosocial.filter',message:'Filtra por UCA para trabajar únicamente con expedientes del ámbito autorizado.'},
      {control:'componente-psicosocial.view',anchor:'liam.anchor.psychosocial.filter',message:'Selecciona vista de coordinación o intervención según tu rol y permisos.'},
      {control:'componente-psicosocial.cases',anchor:'liam.anchor.psychosocial.cases',message:'Los expedientes son referenciales y se enlazan con Familias y Redes sin duplicar participantes.'},
      {control:'componente-psicosocial.detail',anchor:'liam.anchor.psychosocial.cases',message:'El detalle reúne trazabilidad, planes y acciones. Todo cierre requiere criterio y validación profesional.'}
    ]
  };let active=null,index=0,flags={},kind='tour';
  const dashboardControlByModule={
    'base-maestra':'dashboard.cuentame.upload',talento:'dashboard.talent-human.open','salud-nutricion':'dashboard.nutrition.open',
    'calendario-inteligente':'dashboard.calendar.open','motor-documental':'dashboard.document-engine.open',formatos:'dashboard.formats.open'
  };
  async function show(){const step=active?.[index];if(!step)return finish();window.LIAM_ANIMATION?.clear();if(step.anchor)await window.LIAM_MOVEMENT.move({mode:flags.walk_enabled?'walk':'teleport',destination:step.anchor,duration_ms:800},flags);window.LIAM_TABLET?.show(step.tablet||{type:'progress',title:`Paso ${index+1} de ${active.length}`,value:Math.round((index+1)*100/active.length)});window.LIAM?.announce?.(step.message);if(step.control)window.LIAM_ANIMATION?.highlight(step.control,step.message);document.dispatchEvent(new CustomEvent('liam:tour-step',{detail:{kind,index,total:active.length,control:step.control||null}}));return true}
  function start(id,nextFlags={}){active=tours[id]||null;index=0;flags=nextFlags;kind='tour';if(!active)return false;show();return true}
  function startPresentation(data,nextFlags={}){const profile=data?.profile||{},modules=Array.isArray(data?.modules)?data.modules:[],workflow=Array.isArray(data?.workflow)?data.workflow:[];const identity=profile.identity_confirmed?`Esta plataforma fue diseñada por ${profile.designer} y creada el ${profile.created_date}.`:'La autoría y la fecha de creación todavía no están confirmadas en la identidad institucional.';active=[
    {message:`Bienvenido a la presentación de ${profile.name||'la Plataforma Primera Infancia'}. ${profile.description||''}`,tablet:{type:'module_preview',title:'Plataforma Primera Infancia',value:`Versión ${profile.version||'no configurada'}`}},
    {message:identity,tablet:{type:'message',title:'Identidad institucional',value:profile.identity_confirmed?'Información confirmada':'Información pendiente'}},
    {message:`Para tu rol ${data?.role||'actual'} hay ${modules.length} módulos autorizados. A continuación te explicaré cada uno.`,tablet:{type:'count',title:'Módulos autorizados',value:modules.length}},
    ...modules.map(item=>{const control=dashboardControlByModule[item.module];const anchor=control?`liam.anchor.dashboard.${item.module==='base-maestra'?'cuentame':item.module==='talento'?'talent-human':item.module==='salud-nutricion'?'nutrition':item.module==='calendario-inteligente'?'calendar':item.module==='motor-documental'?'document-engine':'formats'}`:null;return{control,anchor,message:`${item.title}. ${item.purpose||'Este módulo contiene funciones autorizadas para tu rol.'}`,tablet:{type:'module_preview',title:item.title,value:item.module}}}),
    {message:`El flujo general de trabajo es: ${workflow.map((step,i)=>`${i+1}. ${step}`).join(' ')}`,tablet:{type:'next_step',title:'Flujo general',value:`${workflow.length} etapas verificables`}},
    {message:'La presentación terminó. Puedes pedirme que explique esta pantalla o iniciar un recorrido guiado para realizar una tarea.',tablet:{type:'success',title:'Presentación completada',value:'LIAM sigue disponible'}}
  ];index=0;flags=nextFlags;kind='presentation';show();return true}
  function next(){if(!active)return false;index+=1;show();return true}
  function previous(){if(!active)return false;index=Math.max(0,index-1);show();return true}
  function finish(){const completedKind=kind;window.LIAM_ANIMATION?.clear();window.LIAM_STATE?.set('success');active=null;index=0;kind='tour';document.dispatchEvent(new CustomEvent('liam:tour-completed',{detail:{kind:completedKind}}));return true}
  function cancel(){window.LIAM_ANIMATION?.clear();active=null;index=0;kind='tour';window.LIAM_STATE?.set('idle')}
  document.addEventListener('liam:business-event',(event)=>{const expected=active?.[index]?.wait_for;if(expected&&event.detail?.name===expected)next()});
  window.LIAM_TOURS=Object.freeze({start,startPresentation,next,previous,cancel,ids:Object.freeze(Object.keys(tours))});
})();
