const ta   = document.getElementById('editor');
const sug  = document.getElementById('s');
const toast= document.getElementById('toast');

const inputs = {
  ctx  : document.getElementById('ctx'),
  topk : document.getElementById('topk'),
  order: document.getElementById('order'),
  hk   : document.getElementById('hk')
};
const defaultCfg = {context_window:20, top_k:5, ngram_order:5, hotkey:'Tab'};
loadCfgToUI();

document.getElementById('saveSettings').onclick = () => {
  const cfg = readCfgFromUI();
  localStorage.setItem('cfg', JSON.stringify(cfg));
  notify('Settings saved');
};

let lastReq=0, queued=false, suggestions=[];
ta.addEventListener('input', ()=>{
  if(Date.now()-lastReq>200){ predict(); lastReq=Date.now();}
  else if(!queued){ queued=true; setTimeout(()=>{queued=false;predict();},220);}
});

ta.addEventListener('keydown', e=>{
  const cfg = currentCfg();
  if(e.key===cfg.hotkey){        // accept suggestion
    if(suggestions.length){ e.preventDefault(); insert(suggestions[0]); }
  }
});

function insert(word){
  ta.setRangeText(word+' ', ta.selectionStart, ta.selectionStart, 'end');
  predict();
}

async function predict(){
  if(!ta.value.trim()){ sug.textContent=''; return; }
  try{
    const cfg = currentCfg();
    const body = {
      context: ta.value.split(/\s+/).slice(-cfg.context_window).join(' '),
      settings: cfg
    };
    const res = await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!res.ok){ const err=await res.json(); throw err.error||res.statusText; }
    const data = await res.json();
    suggestions = data.suggestions;
    sug.innerHTML = '<kbd>'+cfg.hotkey+'</kbd> → '+suggestions.join(' · ');
  }catch(err){ notify('Error: '+err); }
}

document.getElementById('saveFile').onclick = async ()=>{
  const fn = prompt('Save as (lesson03.txt):');
  if(!fn) return;
  try{
    const res = await fetch('/save',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({filename:fn,text:ta.value,settings:currentCfg()})
    });
    if(!res.ok){ const js=await res.json(); throw js.error||res.statusText; }
    notify('Saved & retraining…');
  }catch(err){ notify('Error: '+err); }
};

function notify(msg){
  toast.textContent=msg;
  toast.style.opacity=1;
  setTimeout(()=>toast.style.opacity=0, 3000);
}

function loadCfgToUI(){
  const cfg = currentCfg();
  inputs.ctx.value  = cfg.context_window;
  inputs.topk.value = cfg.top_k;
  inputs.order.value= cfg.ngram_order;
  inputs.hk.value   = cfg.hotkey;
}
function readCfgFromUI(){
  return {
    context_window: +inputs.ctx.value,
    top_k:          +inputs.topk.value,
    ngram_order:    +inputs.order.value,
    hotkey:         inputs.hk.value.trim()||defaultCfg.hotkey
  };
}
function currentCfg(){
  return JSON.parse(localStorage.getItem('cfg')||JSON.stringify(defaultCfg));
}
