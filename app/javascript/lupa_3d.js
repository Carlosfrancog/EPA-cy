// Lightweight 3D projection of real LUPA feature sensitivities.
// Perspective/rotation only affects presentation; never computes new metrics.
const initialize = (root) => {
  if (root.dataset.initialized) return;
  root.dataset.initialized = "true";
  const canvas = root.querySelector("canvas");
  const detail = root.querySelector("[data-scene-detail]");
  let payload;
  try { payload = JSON.parse(root.querySelector("[data-scene-json]").textContent); }
  catch (_) { detail.textContent = "Dados indisponíveis."; return; }
  if (payload.schema !== "epa.lupa.scene.v1" || payload.protocols?.length !== 3) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const names = payload.protocols[0].features.map(f => f.name);
  const values = payload.protocols.flatMap((p,z) => p.features.map(f => ({
    x:names.indexOf(f.name), y:f.importance, z, ...f, protocol:p.protocol
  })));
  if (values.length !== 33 || values.some(v=>!Number.isFinite(v.y)||v.x<0)) return;
  const bound = Math.max(.001, ...values.map(v=>Math.abs(v.y)));
  let yaw=-.55, pitch=.34, zoom=1, active=null, positions=[];
  let featureFilter="all", protocolFilter="all", showDispersion=false;
  const featureSelect=root.querySelector("[data-feature-filter]");
  const protocolSelect=root.querySelector("[data-protocol-filter]");
  const dispersionInput=root.querySelector("[data-show-dispersion]");
  const visible=v=>(featureFilter==="all"||v.name===featureFilter)&&
                    (protocolFilter==="all"||v.protocol===protocolFilter);
  const w=canvas.width,h=canvas.height;
  const project=(x,y,z)=>{
    const a=(x-5)*64, b=y/bound*145, c=(z-1)*145;
    const dx=a*Math.cos(yaw)-c*Math.sin(yaw);
    const dz=a*Math.sin(yaw)+c*Math.cos(yaw);
    const dy=b*Math.cos(pitch)-dz*Math.sin(pitch);
    const depth=b*Math.sin(pitch)+dz*Math.cos(pitch);
    const s=zoom*700/(700+depth*.5);
    return [w/2+dx*s,h/2-dy*s,depth];
  };
  const line=(a,b,color,width=1)=>{
    ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();
    ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();
  };
  const draw=()=>{
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle="#f5faf9";ctx.fillRect(0,0,w,h);
    for(let z=0;z<3;z++){
      line(project(0,0,z),project(10,0,z),"#b7d8d3",1.3);
      line(project(0,-bound,z),project(0,bound,z),"#cddedb");
      ctx.fillStyle="#306f6a";ctx.font="bold 14px sans-serif";
      const pos=project(-.8,0,z);ctx.fillText("N"+(z+1),pos[0],pos[1]);
    }
    for(let x=0;x<11;x++){line(project(x,0,0),project(x,0,2),"#d5e4e1");}
    line(project(0,0,0),project(0,0,2),"#53968e",2);
    positions=values.map((v,i)=>({index:i,point:project(v.x,v.y,v.z),base:project(v.x,0,v.z),value:v})).filter(item=>visible(item.value));
    positions.sort((a,b)=>b.point[2]-a.point[2]);
    for(const item of positions){
      const isSelected=active===item.index;
      if(showDispersion&&item.value.dispersion>0){
        const low=project(item.value.x,item.value.y-item.value.dispersion,item.value.z);
        const high=project(item.value.x,item.value.y+item.value.dispersion,item.value.z);
        line(low,high,"#9871a8",2.5);
      }
      line(item.base,item.point,item.value.y<0?"#b36e57":"#499b8d",isSelected?3:1.5);
      ctx.fillStyle=item.value.y<0?"#c0745b":"#247e73";
      ctx.beginPath();ctx.arc(item.point[0],item.point[1],isSelected?8:5,0,Math.PI*2);ctx.fill();
      if(isSelected){ctx.strokeStyle="#173b38";ctx.lineWidth=2;ctx.stroke();}
    }
    ctx.fillStyle="#4b6870";ctx.font="12px sans-serif";
    ctx.fillText("Y: queda F1 (+ / −)",20,26);
    ctx.fillText("X: 11 variáveis  ·  Z: N1 → N3",20,46);
    ctx.fillText("Azul-esverdeado: positivo   |   Terracota: negativo",20,h-18);
  };
  const selectAt=(event)=>{
    const rect=canvas.getBoundingClientRect();
    const px=(event.clientX-rect.left)*w/rect.width,py=(event.clientY-rect.top)*h/rect.height;
    const nearest=positions.map(p=>({...p,d:Math.hypot(p.point[0]-px,p.point[1]-py)}))
      .sort((a,b)=>a.d-b.d)[0];
    if(nearest && nearest.d<22){
      active=nearest.index;const v=nearest.value;
      detail.textContent=v.protocol+" · "+v.name+" · Queda F1: "+v.importance.toFixed(4)+" · Desvio: "+v.dispersion.toFixed(4);
      draw();
    }
  };
  const filterUpdate=()=>{
    featureFilter=featureSelect?.value||"all";
    protocolFilter=protocolSelect?.value||"all";
    showDispersion=Boolean(dispersionInput?.checked);
    active=null;
    detail.textContent="Exibindo "+values.filter(visible).length+" de 33 medições. Desvio não é intervalo de confiança.";
    draw();
  };
  featureSelect?.addEventListener("change",filterUpdate);
  protocolSelect?.addEventListener("change",filterUpdate);
  dispersionInput?.addEventListener("change",filterUpdate);
  let drag=null;
  canvas.addEventListener("pointerdown",e=>{drag={x:e.clientX,y:e.clientY,moved:false};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener("pointermove",e=>{
    if(!drag)return;
    const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
    if(Math.abs(dx)+Math.abs(dy)>2)drag.moved=true;
    yaw+=dx*.006;pitch=Math.max(-1.1,Math.min(1.1,pitch+dy*.004));
    drag.x=e.clientX;drag.y=e.clientY;draw();
  });
  canvas.addEventListener("pointerup",e=>{if(drag&&!drag.moved)selectAt(e);drag=null;});
  canvas.addEventListener("keydown",e=>{
    if(e.key==="ArrowLeft")yaw-=.13;
    else if(e.key==="ArrowRight")yaw+=.13;
    else if(e.key==="ArrowUp")pitch=Math.max(-1.1,pitch-.10);
    else if(e.key==="ArrowDown")pitch=Math.min(1.1,pitch+.10);
    else if(e.key==="+")zoom=Math.min(2,zoom+.1);
    else if(e.key==="-")zoom=Math.max(.5,zoom-.1);
    else return;
    e.preventDefault();draw();
  });
  root.querySelectorAll("[data-rotate]").forEach(btn=>btn.addEventListener("click",()=>{yaw+=Number(btn.dataset.rotate)*.18;draw();}));
  root.querySelectorAll("[data-zoom]").forEach(btn=>btn.addEventListener("click",()=>{zoom=Math.max(.5,Math.min(2,zoom+Number(btn.dataset.zoom)*.12));draw();}));
  root.querySelector("[data-reset]")?.addEventListener("click",()=>{yaw=-.55;pitch=.34;zoom=1;active=null;if(featureSelect)featureSelect.value="all";if(protocolSelect)protocolSelect.value="all";if(dispersionInput)dispersionInput.checked=false;filterUpdate();});
  draw();
};
const boot=()=>document.querySelectorAll("[data-lupa-scene]").forEach(initialize);
document.addEventListener("turbo:load",boot);
if(document.readyState!=="loading")boot();
else document.addEventListener("DOMContentLoaded",boot);
