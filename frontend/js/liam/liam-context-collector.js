(function(){
  'use strict';
  const modalSelectors=['[role="dialog"]:not(.hidden)','.ci-modal-backdrop','.giu-modal:not(.hidden)'];
  function module(){return location.hash.replace(/^#/,'')||'dashboard'}
  function visibleModal(){for(const selector of modalSelectors){const el=document.querySelector(selector);if(el&&el.getClientRects().length)return el.id||el.getAttribute('aria-labelledby')||'modal-visible'}return null}
  function activeTab(){const root=document.getElementById(module());const active=root?.querySelector('[role="tab"][aria-selected="true"],.ci-view-toggle .ci-active,[data-tab].active');return active?.id||active?.dataset?.tab||null}
  function activeHelp(){const el=document.activeElement?.closest?.('[data-help-id]');return el?.dataset?.helpId||null}
  function selectedValue(id){const el=document.getElementById(id);if(!el)return null;return String(el.value||'').trim()||null}
  function collect(){const period=window.periodoFormatosSeleccionado?.()||{};return{module_id:module(),view_id:'main',tab_id:activeTab(),modal_id:visibleModal(),active_help_id:activeHelp(),selected_unit:selectedValue('filtro-unidad'),selected_month:period.mes||null,selected_year:period.anio||null}}
  window.LIAM_CONTEXT=Object.freeze({collect});
})();
