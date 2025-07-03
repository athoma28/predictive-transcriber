/*********************************************************************
 *  A.  prediction logic (unchanged from previous step-up version)
 *********************************************************************/
const ta   = document.getElementById('editor');
const sug  = document.getElementById('sug');
const save = document.getElementById('save');

let preds=[], lastReq=0, queued=false;
const HOT  = { "Tab":0, "1":0, "2":1, "3":2, "4":3, "5":4 };

ta.addEventListener('input', ()=>{
  if(Date.now()-lastReq>200){ updatePred(); lastReq=Date.now();}
  else if(!queued){ queued=true; setTimeout(()=>{queued=false;updatePred();},220);}
});
ta.addEventListener('keydown', e=>{
  if(e.key in HOT && (e.key==="Tab" || e.ctrlKey || e.metaKey)){
    e.preventDefault(); choosePred(HOT[e.key]);
  }
});

function choosePred(i){
  if(i>=preds.length) return;
  ta.setRangeText(preds[i]+" ", ta.selectionStart, ta.selectionStart,"end");
  updatePred(); refreshChunks();             // keep both views live
}

function renderPred(){
  const keys=['Tab','⌘/Ctrl + 1','⌘/Ctrl + 2','⌘/Ctrl + 3','⌘/Ctrl + 4'];
  sug.innerHTML = preds.map((p,i)=>`<kbd>${keys[i]}</kbd> ${p}`).join(' · ');
}

async function updatePred(){
  if(!ta.value.trim()){ sug.textContent=''; return; }
  const body={context:ta.value};
  const res=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!res.ok) return;
  const data=await res.json();
  const pre = ta.value.endsWith(" ")? "" : ta.value.split(/\s+/).pop();
  preds = mergeWithPrefix(data.merged, pre);
  renderPred();
}
function mergeWithPrefix(arr, pre){
  if(!pre) return arr.slice(0,5);
  const extras = arr.filter(w=>w.startsWith(pre)&&w!==pre).map(w=>w.slice(pre.length));
  return [...arr, ...extras].filter((v,i,self)=>self.indexOf(v)===i).slice(0,5);
}
save.onclick = async ()=>{
  const fn=prompt('Save as (lessonNN.txt):'); if(!fn) return;
  await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:fn,text:ta.value})});
};


/*********************************************************************
 *  B.  repeated-chunk picker
 *********************************************************************/
const panel = document.getElementById('chunkPanel');
const list  = document.getElementById('chunkList');
let colours = [];

document.addEventListener('keydown', e=>{
  // open/close with Ctrl/Cmd+R, close with Esc
  if((e.key==="r"||e.key==="R") && (e.ctrlKey||e.metaKey)){
    e.preventDefault(); togglePanel();
  } else if(e.key==="Escape" && !panel.hidden){
    hidePanel();
  }
});

ta.addEventListener('input', refreshChunks);   // keep counts live

function togglePanel(){ panel.hidden ? showPanel() : hidePanel(); }
function showPanel(){ refreshChunks(); panel.hidden=false; }
function hidePanel(){ panel.hidden=true; clearMarkers(); }

function refreshChunks(){
  if(panel.hidden) return;
  const seqs = extractRepeatedChunks(ta.value, 2, 3, 2, 15);
  colours = seqs.map((_,i)=>`hsl(${(i*57)%360} 70% 85%)`);
  list.innerHTML = seqs.map((s,i)=>`<li style="background:${colours[i]}" data-t="${s}">${s}</li>`).join("");
  list.querySelectorAll('li').forEach((li,i)=>{
    li.onclick=()=>{ insertChunk(li.dataset.t); hidePanel(); };
  });
  markChunksInTextarea(seqs);
}

function insertChunk(text){
  ta.setRangeText(text+" ", ta.selectionStart, ta.selectionStart, "end");
  updatePred();   // keep suggestions in sync
}

// ---------- chunk mining ---------------------------------------------
function extractRepeatedChunks(txt, minLen, maxLen, minCount, topN){
  const tokens = txt.trim().split(/\s+/);
  const counts = {};
  for(let n=minLen; n<=maxLen; n++){
    for(let i=0; i<=tokens.length-n; i++){
      const seq = tokens.slice(i,i+n).join(" ");
      counts[seq] = (counts[seq]||0)+1;
    }
  }
  return Object.entries(counts)
    .filter(([,c])=>c>=minCount)
    .sort((a,b)=>b[1]-a[1])        // by frequency
    .slice(0, topN)
    .map(([s])=>s);
}

// ---------- colouring (simple overlay) -------------------------------
function markChunksInTextarea(seqs){
  // quick & dirty: replace textContent html in a <pre> overlay
  clearMarkers();
  const overlay = document.createElement('pre');
  overlay.id="overlay";
  overlay.style.cssText=`position:absolute; top:0; left:0; opacity:.35;
      pointer-events:none; white-space:pre-wrap; overflow-wrap:anywhere;`;
  overlay.textContent = ta.value;
  ta.parentNode.insertBefore(overlay, ta);
  // highlight each sequence
  let html = overlay.innerHTML;
  seqs.forEach( (seq,i)=>{
    const re = new RegExp(seq.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), "g");
    html = html.replace(re, `<mark style="background:${colours[i]}">${seq}</mark>`);
  });
  overlay.innerHTML = html;
}
function clearMarkers(){
  const ov=document.getElementById('overlay');
  if(ov) ov.remove();
}
