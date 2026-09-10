(function(){
  'use strict';
  const state={pc:null,dc:null,stream:null,audio:null,active:false,connecting:false};
  const emit=(name,detail={})=>document.dispatchEvent(new CustomEvent(`liam:realtime-${name}`,{detail}));
  function cleanup(){
    try{state.dc?.close()}catch(_){}
    try{state.pc?.close()}catch(_){}
    for(const track of state.stream?.getTracks?.()||[])track.stop();
    if(state.audio){state.audio.pause();state.audio.srcObject=null;state.audio.remove()}
    Object.assign(state,{pc:null,dc:null,stream:null,audio:null,active:false,connecting:false});
  }
  function handleEvent(event){
    if(event.type==='input_audio_buffer.speech_started')emit('speech-started');
    else if(event.type==='input_audio_buffer.speech_stopped')emit('speech-stopped');
    else if(event.type==='conversation.item.input_audio_transcription.completed')emit('user-transcript',{text:event.transcript||''});
    else if(['response.output_audio_transcript.delta','response.audio_transcript.delta'].includes(event.type))emit('assistant-delta',{delta:event.delta||''});
    else if(['response.output_audio_transcript.done','response.audio_transcript.done'].includes(event.type))emit('assistant-transcript',{text:event.transcript||''});
    else if(event.type==='response.done')emit('response-done',{response:event.response||{}});
    else if(event.type==='error')emit('error',{message:event.error?.message||'La conversación en tiempo real encontró un error.'});
  }
  async function start({endpoint,headers={},module='dashboard'}={}){
    if(state.active||state.connecting)return;state.connecting=true;emit('connecting');
    if(!navigator.mediaDevices?.getUserMedia||typeof RTCPeerConnection==='undefined'){cleanup();throw new Error('Este navegador no permite conversación WebRTC.')}
    try{
      const pc=new RTCPeerConnection();state.pc=pc;
      const audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.hidden=true;audio.setAttribute('aria-hidden','true');document.body.appendChild(audio);state.audio=audio;
      pc.ontrack=event=>{audio.srcObject=event.streams[0];audio.play().catch(()=>{})};
      pc.onconnectionstatechange=()=>{if(['failed','disconnected','closed'].includes(pc.connectionState)){const wasActive=state.active;cleanup();if(wasActive)emit('ended')}};
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});state.stream=stream;for(const track of stream.getAudioTracks())pc.addTrack(track,stream);
      const dc=pc.createDataChannel('oai-events');state.dc=dc;dc.onmessage=e=>{try{handleEvent(JSON.parse(e.data))}catch(_){}};
      const opened=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('OpenAI no abrió el canal de conversación a tiempo.')),15000);dc.onopen=()=>{clearTimeout(timer);resolve()};dc.onerror=()=>{clearTimeout(timer);reject(new Error('No se pudo abrir el canal WebRTC.'))}});
      const offer=await pc.createOffer();await pc.setLocalDescription(offer);
      const response=await fetch(endpoint,{method:'POST',headers:{...headers,'Content-Type':'application/sdp','X-Liam-Module':module},body:offer.sdp});
      const answer=await response.text();if(!response.ok)throw new Error((()=>{try{return JSON.parse(answer).error}catch(_){return answer}})()||'No se pudo iniciar la conversación en tiempo real.');
      await pc.setRemoteDescription({type:'answer',sdp:answer});await opened;state.active=true;state.connecting=false;emit('started');
    }catch(error){cleanup();emit('error',{message:error.message});throw error}
  }
  function stop(){const hadSession=state.active||state.connecting;cleanup();if(hadSession)emit('ended')}
  window.LIAM_REALTIME=Object.freeze({start,stop,get active(){return state.active},get connecting(){return state.connecting}});
})();
