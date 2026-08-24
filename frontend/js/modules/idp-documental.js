(function () {
    'use strict';
    const state = { documents: [], selected: null, initialized: false, previewUrl: null, pollTimer: null };
    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');

    async function api(path, options) {
        const response = await fetch(`${backendUrl}/api/idp${path}`, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `Error HTTP ${response.status}`);
        return data;
    }

    function message(text, type='info') {
        const box=$('idp-message'); if(!box)return;
        box.className=`idp-message ${type}`; box.textContent=text; box.classList.remove('hidden');
    }

    function badge(status) {
        const value=String(status||'RECIBIDO').toUpperCase();
        const tone=['APROBADO','IMPORTADO'].includes(value)?'green':value.includes('ERROR')?'red':value.includes('OCR')||value.includes('REVISION')?'yellow':'blue';
        return `<span class="idp-badge ${tone}">${esc(value.replaceAll('_',' '))}</span>`;
    }

    function renderList() {
        const target=$('idp-documents'); if(!target)return;
        if(!state.documents.length){target.innerHTML='<div class="idp-empty">No hay documentos cargados para esta fundación.</div>';return;}
        target.innerHTML=state.documents.map(doc=>`<button type="button" class="idp-document ${state.selected?.id===doc.id?'active':''}" onclick="IDPDocumental.select(${Number(doc.id)})"><div><strong>${esc(doc.nombre_original)}</strong><small>${esc(doc.tipo_documento)} · ${esc(doc.motor_lectura||'Pendiente')}</small></div><div>${badge(doc.estado)}<small>${Number(doc.progreso||0)}%</small></div></button>`).join('');
    }

    function confidence(field) {
        const value=Number(field.confianza||0);
        return value>=.9?'green':value>=.65?'yellow':'red';
    }

    function displayValue(value) {
        if(value===null||value===undefined||value==='')return '<em>No encontrado</em>';
        if(typeof value==='object')return esc(JSON.stringify(value));
        return esc(value);
    }

    function renderDetail() {
        const target=$('idp-detail'); if(!target)return;
        const doc=state.selected;
        if(!doc){target.innerHTML='<div class="idp-empty">Selecciona un documento para revisar sus resultados.</div>';return;}
        const fields=(doc.campos||[]).map(field=>{const suggestion=field.sugerencia_correccion;return `<div class="idp-field ${confidence(field)}" onclick="IDPDocumental.focusEvidence(${Number(field.id)},event)"><div><small>${esc(field.ruta_canonica)}</small><strong>${displayValue(field.valor)}</strong><span>Original: ${esc(field.texto_original||'No encontrado')} · Confianza ${(Number(field.confianza||0)*100).toFixed(0)}%</span><span>Evidencia: ${esc(JSON.stringify(field.evidencia||{}))}</span>${suggestion?`<span>Sugerencia aprobada (${Number(suggestion.apariciones||1)} coincidencia(s)): ${displayValue(suggestion.valor)}</span>`:''}</div><div>${suggestion?`<button type="button" class="idp-btn primary" onclick="event.stopPropagation();IDPDocumental.applySuggestion(${Number(field.id)})">Usar sugerencia</button>`:''}<button type="button" class="idp-btn secondary" onclick="event.stopPropagation();IDPDocumental.correct(${Number(field.id)})">Corregir</button></div></div>`;}).join('');
        const summary=doc.validaciones||{};
        const validations=(summary.resultados||[]).map(item=>`<div class="idp-validation ${String(item.nivel||'').toLowerCase()}"><strong>${esc(item.regla||item.codigo||'VALIDACION')}</strong><span>${esc(item.mensaje||'Sin detalle')}</span></div>`).join('');
        const validationSummary=`<div class="idp-validation-summary ${String(summary.semaforo||'GRIS').toLowerCase()}"><div><small>Semáforo</small><strong>${esc(summary.semaforo||'GRIS')}</strong></div><div><small>Coincidencias</small><strong>${Number(summary.coincidencias||0)} / ${Number(summary.total||0)}</strong></div><div><small>Errores críticos</small><strong>${Number(summary.errores_criticos||0)}</strong></div><div><small>Advertencias</small><strong>${Number(summary.advertencias||0)}</strong></div></div>`;
        const approvalBlocked=doc.estado!=='REQUIERE_REVISION'||Number(summary.errores_criticos||0)>0;
        const canGenerate=['APROBADO','IMPORTADO'].includes(doc.estado)&&doc.tipo_documento==='LISTADO_ASISTENCIA';
        const canImport=doc.estado==='APROBADO'&&doc.tipo_documento==='LISTADO_ASISTENCIA';
        const canRetryOcr=doc.estado==='REQUIERE_OCR'||doc.estado==='ERROR';
        const canCalendar=doc.tipo_documento==='CRONOGRAMA'&&doc.estado==='APROBADO';
        const templateVersion=doc.resultado_canonico?.metadatos?.plantilla_oficial;
        target.innerHTML=`<div class="idp-card p-5"><div class="idp-detail-head"><div><p class="idp-eyebrow">${esc(doc.tipo_documento)}</p><h3>${esc(doc.nombre_original)}</h3><p>Motor: ${esc(doc.motor_lectura||'Pendiente')} · Clasificación ${(Number(doc.confianza_clasificacion||0)*100).toFixed(0)}%</p><p>Plantilla vinculada: ${templateVersion?`${esc(templateVersion.codigo||templateVersion.tipo_formato)} · versión ${esc(templateVersion.version)}`:'Sin versión oficial publicada'}</p></div>${badge(doc.estado)}</div><div class="idp-progress"><span style="width:${Math.max(0,Math.min(100,Number(doc.progreso||0)))}%"></span></div>${validationSummary}<div class="idp-actions"><button class="idp-btn secondary" onclick="IDPDocumental.download(${Number(doc.id)})">Descargar original</button>${canRetryOcr?`<button class="idp-btn primary" onclick="IDPDocumental.retryOcr(${Number(doc.id)})">Reintentar OCR</button>`:''}<button class="idp-btn primary" ${approvalBlocked?'disabled':''} onclick="IDPDocumental.approve(${Number(doc.id)})">Aprobar sin importar</button>${canCalendar?`<button class="idp-btn primary" onclick="IDPDocumental.prepareCalendar(${Number(doc.id)})">Preparar para calendario</button>`:''}${canGenerate?`<button class="idp-btn primary" onclick="IDPDocumental.downloadOfficial(${Number(doc.id)})">Generar listado oficial</button>`:''}${canImport?`<button class="idp-btn primary" onclick="IDPDocumental.importAttendance(${Number(doc.id)})">Importar asistencia</button>`:''}</div>${validations}<div class="idp-review-grid"><section><h4 class="idp-review-title">Documento original privado</h4><div id="idp-preview" class="idp-preview"><div class="idp-empty">Preparando vista segura...</div></div><div id="idp-evidence-focus" class="idp-evidence-focus">Selecciona un campo para consultar su evidencia.</div></section><section><h4 class="idp-review-title">Información extraída</h4><div class="idp-fields">${fields||'<div class="idp-empty">No hay campos estructurados. Requiere mapeo u OCR.</div>'}</div></section></div></div>`;
    }

    async function load() {
        try { const data=await api('/documentos'); state.documents=data.documentos||[]; renderList(); }
        catch(error){message(error.message,'error');}
    }

    async function select(id) {
        try { const data=await api(`/documentos/${id}`); state.selected=data.documento; renderList(); renderDetail(); await loadPreview(); schedulePoll(); }
        catch(error){message(error.message,'error');}
    }

    function schedulePoll() {
        if(state.pollTimer){clearTimeout(state.pollTimer);state.pollTimer=null;}
        if(['EN_COLA','PROCESANDO'].includes(state.selected?.estado))state.pollTimer=setTimeout(()=>select(state.selected.id),2000);
    }

    async function upload() {
        const input=$('idp-file'); const file=input?.files?.[0];
        if(!file){message('Selecciona un archivo.','error');return;}
        if(file.size>50*1024*1024){message('El archivo supera 50 MB.','error');return;}
        const form=new FormData(); form.append('file',file);
        const button=$('idp-upload'); if(button)button.disabled=true;
        message('Validando, clasificando y extrayendo el documento...','info');
        try { const data=await api('/documentos',{method:'POST',body:form}); state.selected=data.documento; input.value=''; message(data.message,'success'); await load(); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error');}
        finally{if(button)button.disabled=false;}
    }

    async function correct(fieldId) {
        const field=(state.selected?.campos||[]).find(item=>Number(item.id)===Number(fieldId)); if(!field)return;
        const raw=prompt(`Corregir ${field.ruta_canonica}`,field.valor??''); if(raw===null)return;
        const reason=prompt('Motivo de la corrección (opcional)','Revisión humana')??'';
        try { const data=await api(`/documentos/${state.selected.id}/campos/${fieldId}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({valor:raw,motivo:reason})}); state.selected=data.documento; message(data.message,'success'); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error');}
    }

    async function applySuggestion(fieldId) {
        const field=(state.selected?.campos||[]).find(item=>Number(item.id)===Number(fieldId)),suggestion=field?.sugerencia_correccion; if(!suggestion)return;
        if(!confirm(`¿Usar la sugerencia aprobada para ${field.ruta_canonica}?`))return;
        try { const data=await api(`/documentos/${state.selected.id}/campos/${fieldId}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({valor:suggestion.valor,motivo:'Sugerencia de corrección aprobada previamente'})}); state.selected=data.documento; message('Sugerencia aplicada y registrada para auditoría.','success'); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error');}
    }

    async function approve(id) {
        if(!confirm('¿Aprobar el resultado revisado? Esta acción NO lo importará todavía a los módulos funcionales.'))return;
        try { const data=await api(`/documentos/${id}/aprobar`,{method:'POST'}); state.selected=data.documento; message(data.message,'success'); await load(); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error');}
    }

    function download(id) {
        window.descargarArchivoAutenticado(`${backendUrl}/api/idp/documentos/${id}/original`).catch(error=>message(error.message,'error'));
    }

    function downloadOfficial(id) {
        message('Generando el listado con la plantilla oficial de la fundación...','info');
        window.descargarArchivoAutenticado(`${backendUrl}/api/idp/documentos/${id}/listado-oficial`).then(()=>message('Listado oficial generado para imprimir.','success')).catch(error=>message(error.message,'error'));
    }

    async function loadPreview() {
        const target=$('idp-preview'),doc=state.selected; if(!target||!doc)return;
        if(state.previewUrl){URL.revokeObjectURL(state.previewUrl);state.previewUrl=null;}
        const extension=String(doc.extension||'').toLowerCase();
        if(!['.pdf','.png','.jpg','.jpeg','.bmp','.tif','.tiff','.heif','.heic'].includes(extension)){target.innerHTML='<div class="idp-empty">La vista integrada está disponible para PDF e imágenes. Usa “Descargar original” para revisar archivos Office.</div>';return;}
        try { const response=await fetch(`${backendUrl}/api/idp/documentos/${doc.id}/vista-previa`); if(!response.ok)throw new Error((await response.json().catch(()=>({}))).error||'No se pudo cargar la vista previa.'); const blob=await response.blob(); state.previewUrl=URL.createObjectURL(blob); target.innerHTML=extension==='.pdf'?`<iframe title="Vista previa del documento" src="${state.previewUrl}"></iframe>`:`<img alt="Vista previa del documento original" src="${state.previewUrl}">`; }
        catch(error){target.innerHTML=`<div class="idp-empty">${esc(error.message)}</div>`;}
    }

    function focusEvidence(fieldId,clickEvent) {
        const field=(state.selected?.campos||[]).find(item=>Number(item.id)===Number(fieldId)),target=$('idp-evidence-focus'); if(!field||!target)return;
        document.querySelectorAll('.idp-field.focused').forEach(item=>item.classList.remove('focused')); clickEvent?.currentTarget?.classList?.add('focused');
        target.textContent=`Evidencia de ${field.ruta_canonica}: ${JSON.stringify(field.evidencia||{})}. Texto original: ${field.texto_original||'No encontrado'}`;
    }

    async function retryOcr(id) {
        message('Ejecutando OCR y controles de calidad...','info');
        try { const data=await api(`/documentos/${id}/reintentar-ocr`,{method:'POST'}); state.selected=data.documento; message(data.message,'success'); await load(); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error'); await select(id);}
    }

    async function importAttendance(id) {
        const today=new Date().toISOString().slice(0,10),date=prompt('Fecha de la actividad (AAAA-MM-DD)',today); if(date===null)return;
        const activity=prompt('Nombre o tema de la actividad (opcional)','')??'';
        if(!confirm(`¿Importar definitivamente la asistencia del ${date}? El sistema evitará registros duplicados.`))return;
        try { const data=await api(`/documentos/${id}/importar-asistencia`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha_actividad:date,actividad})}); state.selected=data.documento; message(data.message,'success'); await load(); renderDetail(); await loadPreview(); }
        catch(error){message(error.message,'error');}
    }
    async function prepareCalendar(id){try{const data=await api(`/documentos/${id}/preparar-calendario`,{method:'POST'});if(typeof window.ciAbrirPreviewExterno!=='function')throw new Error('El calendario no está disponible en esta sesión. Recarga la página.');mostrarSeccion('calendario-inteligente');setTimeout(()=>window.ciAbrirPreviewExterno(data.preview),150);message(data.message,'success');}catch(error){message(error.message,'error');}}

    function init() {
        if(!state.initialized){state.initialized=true;$('idp-upload')?.addEventListener('click',upload);}
        load();
    }
    window.IDPDocumental={init,load,select,upload,correct,applySuggestion,approve,download,downloadOfficial,retryOcr,focusEvidence,importAttendance,prepareCalendar};
    window.idpDocumentalInit=init;
})();
