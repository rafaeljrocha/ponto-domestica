// Máscara monetária leve para campos type="text" data-money=""
document.querySelectorAll('input[data-money]').forEach(function(inp){
  function fmt(v){
    v = (v||'').replace(/\D/g,'');
    if(!v){ return ''; }
    v = (parseInt(v,10)/100).toFixed(2);
    return 'R$ ' + v.replace('.',',').replace(/\B(?=(\d{3})+(?!\d))/g,'.');
  }
  inp.addEventListener('input', function(){ inp.value = fmt(inp.value); });
  if(inp.value){ inp.value = fmt((parseFloat(inp.value)*100).toFixed(0)); }
});
