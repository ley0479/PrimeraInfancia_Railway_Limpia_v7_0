(function(){
  'use strict';
  const state={pc:null,dc:null,stream:null,audio:null,audioContext:null,raf:null,active:false,connecting:false,startedAt:0,idleTimer:null,maxTimer:null};
  const IDLE_MS=90000,MAX_MS=300000;
  const emit=(name,detail={})=>document.dispatchEvent(new CustomEvent(`liam:realtime-${name}`,{detail}));
  function clearTimers(){clearTimeout(state.idleTimer);clearTimeout(state.maxTimer);state.idleTimer=null;state.maxTimer=null}
  function touch(){if(!state.active)return;clearTimeout(state.idleTimer);state.idleTimer=setTimeout(()=>stop('idle_timeout'),IDLE_MS)}
  function cleanup(){
    clearTimers();if(state.raf)cancelAnimationFrame(state.raf);state.raf=null;state.audioContext?.close?.().catch(()=>{});
    try{state.dc?.close()}catch(_){}
    try{state.pc?.close()}catch(_){}
    for(const track of state.stream?.getTracks?.()||[])track.stop();
    if(state.audio){state.audio.pause();state.audio.srcObject=null;state.audio.remove()}
    Object.assign(state,{pc:null,dc:null,stream:null,audio:null,audioContext:null,active:false,connecting:false,startedAt:0});
  }
  function monitorAudio(stream){try{const context=new AudioContext(),source=context.createMediaStreamSource(stream),analyser=context.createAnalyser(),data=new Uint8Array(32);analyser.fftSize=64;source.connect(analyser);state.audioContext=context;const tick=()=>{analyser.getByteFrequencyData(data);emit('audio-level',{level:data.reduce((a,b)=>a+b,0)/(data.length*255)});state.raf=requestAnimationFrame(tick)};tick()}catch(_){}}
  function handleEvent(event){
    touch();if(event.type==='input_audio_buffer.speech_started')emit('speech-started');
    else if(event.type==='input_audio_buffer.speech_stopped')emit('speech-stopped');
    else if(event.type==='conversation.item.input_audio_transcription.delta')emit('user-delta',{delta:event.delta||''});
    else if(event.type==='conversation.item.input_audio_transcription.completed')emit('user-transcript',{text:event.transcript||''});
    else if(['response.output_audio_transcript.delta','response.audio_transcript.delta'].includes(event.type))emit('assistant-delta',{delta:event.delta||''});
    else if(['response.output_audio_transcript.done','response.audio_transcript.done'].includes(event.type))emit('assistant-transcript',{text:event.transcript||''});
    else if(event.type==='response.done'){const response=event.response||{};for(const item of response.output||[]){if(item.type==='function_call')emit('tool-call',{name:item.name,callId:item.call_id,args:item.arguments||'{}'})}emit('response-done',{response})}
    else if(event.type==='error')emit('error',{message:event.error?.message||'La conversación en tiempo real encontró un error.'});
  }
  async function start({endpoint,headers={},module='dashboard'}={}){
    if(state.active||state.connecting)return;state.connecting=true;emit('connecting');
    if(!navigator.mediaDevices?.getUserMedia||typeof RTCPeerConnection==='undefined'){cleanup();throw new Error('Este navegador no permite conversación WebRTC.')}
    try{
      const pc=new RTCPeerConnection();state.pc=pc;
      const audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.hidden=true;audio.setAttribute('aria-hidden','true');document.body.appendChild(audio);state.audio=audio;
      pc.ontrack=event=>{audio.srcObject=event.streams[0];audio.play().catch(()=>{});monitorAudio(event.streams[0])};
      pc.onconnectionstatechange=()=>{if(['failed','disconnected','closed'].includes(pc.connectionState)&&state.active)stop(`connection_${pc.connectionState}`)};
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});state.stream=stream;for(const track of stream.getAudioTracks())pc.addTrack(track,stream);
      const dc=pc.createDataChannel('oai-events');state.dc=dc;dc.onmessage=e=>{try{handleEvent(JSON.parse(e.data))}catch(_){}};
      const opened=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('OpenAI no abrió el canal de conversación a tiempo.')),15000);dc.onopen=()=>{clearTimeout(timer);resolve()};dc.onerror=()=>{clearTimeout(timer);reject(new Error('No se pudo abrir el canal WebRTC.'))}});
      const offer=await pc.createOffer();await pc.setLocalDescription(offer);
      const response=await fetch(endpoint,{method:'POST',headers:{...headers,'Content-Type':'application/sdp','X-Liam-Module':module},body:offer.sdp});
      const answer=await response.text();if(!response.ok)throw new Error((()=>{try{return JSON.parse(answer).error}catch(_){return answer}})()||'No se pudo iniciar la conversación en tiempo real.');
      await pc.setRemoteDescription({type:'answer',sdp:answer});await opened;state.active=true;state.connecting=false;state.startedAt=Date.now();state.maxTimer=setTimeout(()=>stop('maximum_duration'),MAX_MS);touch();emit('started',{maximumSeconds:MAX_MS/1000,idleSeconds:IDLE_MS/1000});
    }catch(error){cleanup();emit('error',{message:error.message});throw error}
  }
  function sendToolResult(callId,result){if(state.dc?.readyState!=='open')return false;state.dc.send(JSON.stringify({type:'conversation.item.create',item:{type:'function_call_output',call_id:callId,output:JSON.stringify(result)}}));state.dc.send(JSON.stringify({type:'response.create'}));touch();return true}
  function stop(reason='user'){const hadSession=state.active||state.connecting,duration=state.startedAt?Math.round((Date.now()-state.startedAt)/1000):0;cleanup();if(hadSession)emit('ended',{reason,duration})}
  window.LIAM_REALTIME=Object.freeze({start,stop,sendToolResult,get active(){return state.active},get connecting(){return state.connecting}});
})();
