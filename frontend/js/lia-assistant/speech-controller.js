(function(){
  'use strict';
  let recognition=null;
  const preferences=()=>({muted:localStorage.getItem('lia-muted')==='1',rate:Math.max(.6,Math.min(1.5,Number(localStorage.getItem('lia-rate')||.95)))});
  function listen(){return new Promise((resolve,reject)=>{const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition)return reject(new Error('Este navegador no admite dictado.'));recognition=new Recognition();recognition.lang='es-CO';recognition.interimResults=false;recognition.maxAlternatives=1;recognition.onresult=e=>resolve(e.results[0][0].transcript);recognition.onerror=e=>reject(new Error(e.error==='not-allowed'?'Permiso de micrófono rechazado.':'No pude transcribir el audio.'));recognition.onend=()=>{recognition=null};recognition.start()})}
  function cancelListening(){try{recognition?.abort()}catch(_){}recognition=null}
  function speak(text){if(!('speechSynthesis'in window)||preferences().muted)return false;stop();const utterance=new SpeechSynthesisUtterance(String(text||''));utterance.lang='es-CO';utterance.rate=preferences().rate;speechSynthesis.speak(utterance);return true}
  function pause(){if('speechSynthesis'in window)speechSynthesis.pause()}
  function resume(){if('speechSynthesis'in window)speechSynthesis.resume()}
  function stop(){if('speechSynthesis'in window)speechSynthesis.cancel()}
  function setMuted(value){localStorage.setItem('lia-muted',value?'1':'0');if(value)stop()}
  function setRate(value){localStorage.setItem('lia-rate',String(Math.max(.6,Math.min(1.5,Number(value)||.95))))}
  window.LIA_SPEECH=Object.freeze({listen,cancelListening,speak,pause,resume,stop,setMuted,setRate,preferences});
})();
