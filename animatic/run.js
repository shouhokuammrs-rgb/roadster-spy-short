const js=require('fs').readFileSync('test.js','utf8');
const handler={get:(t,k)=>{ if(k==='canvas')return {}; if(['measureText'].includes(k)) return ()=>({width:10}); if(['createLinearGradient','createRadialGradient'].includes(k)) return ()=>({addColorStop(){}}); return (...a)=>{}; }, set:()=>true};
const ctxProxy=new Proxy({},handler);
const els={};
global.document={getElementById:(id)=>els[id]||(els[id]={textContent:'',value:0,children:[],addEventListener(){},appendChild(ch){this.children.push(ch)},classList:{toggle(){}},innerHTML:'',dataset:{}}), createElement:()=>({className:'',innerHTML:'',addEventListener(){},classList:{toggle(){}}}), querySelectorAll:()=>[]};
els['cv']={getContext:()=>ctxProxy, width:540,height:960};
global.requestAnimationFrame=()=>{}; global.performance={now:()=>0};
let errs=[];
// expose t via hack: wrap setter by evaluating with modified code
const code=js.replace('let t=0,playing=false','global.__set=(v)=>{t=v;render();}; let t=0,playing=false');
try{ eval(code);}catch(e){console.log('load error',e.message)}
for(let tt=0;tt<57;tt+=0.5){ try{ global.__set(tt);}catch(e){ errs.push(tt+': '+e.message);} }
console.log(errs.slice(0,10).join('\n')||'no errors');
