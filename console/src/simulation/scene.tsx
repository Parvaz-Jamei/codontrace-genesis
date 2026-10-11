import type {Frame} from './model';
import {genomeColor,project} from './model';
export function Scene({frames,mode,spread,links,cap,selected,onSelect}:{frames:Frame[];mode:'slice'|'stack';spread:number;links:boolean;cap:number;selected:string|null;onSelect:(id:string)=>void}){
 const current=frames.at(-1);
 const height=650+(mode==='stack'?Math.max(0,frames.length-1)*spread:0);
 return <svg id="genesis-simulation-scene" className="sim-scene" viewBox={`0 0 980 ${height}`} width="980" height={height} role="group" aria-label="Recorded generation layers and organism positions" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="sim-floor" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#102d3e"/><stop offset="1" stopColor="#12202f"/></linearGradient><radialGradient id="sim-halo"><stop stopColor="#30dba9" stopOpacity=".13"/><stop offset="1" stopColor="#07111c" stopOpacity="0"/></radialGradient><pattern id="sim-dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".6" fill="#6186a1" opacity=".3"/></pattern></defs>
 <rect width="980" height={height} fill="#080f19"/><rect width="980" height={height} fill="url(#sim-dots)"/><ellipse cx="490" cy="365" rx="460" ry="250" fill="url(#sim-halo)"/>
 {!current?<g fill="#8297ab" textAnchor="middle"><text x="490" y="290" fontSize="24">Waiting for recorded spatial frames</text><text x="490" y="326" fontSize="14">Select a run and seed. No sample organisms are invented.</text></g>:null}
 {(mode==='stack'?frames:[...(current?[current]:[])]).map((frame,i,arr)=>{
  const active=i===arr.length-1,offset=active?0:(arr.length-1-i)*spread;
  const p=(pos:[number,number])=>project(pos[0],pos[1],frame.world.width,frame.world.height,offset);
  const corners:[[number,number],[number,number],[number,number],[number,number]]=[[0,0],[frame.world.width,0],[frame.world.width,frame.world.height],[0,frame.world.height]];
  const outline=corners.map(x=>p(x).join(',')).join(' '),born=new Set(frame.born_ids);
  const cells=Array.from({length:Math.min(32,Math.max(frame.world.width,frame.world.height))+1},(_,j)=>j);
  const glyphs=[...frame.agents].sort((a,b)=>a.position[0]+a.position[1]-b.position[0]-b.position[1]).slice(0,cap);
  return <g key={frame.generation} opacity={active?1:.38}>
   <polygon points={outline} fill="url(#sim-floor)" stroke={active?'#4fbab3':'#345267'} strokeWidth={active?1.6:1}/>
   {cells.map((j)=>{const x=j*frame.world.width/(cells.length-1),y=j*frame.world.height/(cells.length-1);const a=p([x,0]),b=p([x,frame.world.height]),c=p([0,y]),d=p([frame.world.width,y]);return <g key={j} stroke="#42617b" strokeWidth=".6" opacity=".32"><line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]}/><line x1={c[0]} y1={c[1]} x2={d[0]} y2={d[1]}/></g>})}
   <text x={p([0,frame.world.height])[0]-15} y={p([0,frame.world.height])[1]+22} fill={active?'#7de0ca':'#7694ac'} fontFamily="monospace" fontSize="12">GEN {frame.generation} · {frame.agents.length} agents</text>
   {links&&active?frame.links.slice(0,3000).map((l,j)=>{const a=p(l.source_position),b=p(l.target_position);return <g key={j}><line x1={a[0]} y1={a[1]-8} x2={b[0]} y2={b[1]-8} stroke={l.kind==='two_parent_birth'?'#d9a2ff':'#59d9b3'} strokeWidth={l.kind==='two_parent_birth'?2:1.2} strokeDasharray={l.historical_source?'4 4':undefined} opacity=".65"><title>{`${l.kind}: ${l.source} → ${l.target}${l.historical_source?' (historical position)':''}`}</title></line></g>}):null}
   {glyphs.map(a=>{const [x,y]=p(a.position),color=genomeColor(a.genome_digest);return <g key={a.id} transform={`translate(${x} ${y})`} role={active?'button':undefined} tabIndex={active?0:undefined} aria-label={`Organism ${a.id}`} onClick={active?()=>onSelect(a.id):undefined} onKeyDown={e=>{if(active&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onSelect(a.id)}}} className="sim-agent">
    <title>{`${a.id} · ATP ${a.energy??'not recorded'} · position ${a.position.join(',')}`}</title><ellipse cy="2" rx="10" ry="4" fill="#02080d" opacity=".6"/>
    <path d="M-7 -9 Q-7 -19 0 -19 Q7 -19 7 -9 L7 -3 Q0 3 -7 -3Z" fill={color} stroke={selected===a.id?'#fff':'#133c4e'} strokeWidth={selected===a.id?2.5:1}/><ellipse cy="-16" rx="7" ry="3.5" fill="#e8fff5" opacity=".35"/><circle cx="-2" cy="-10" r="1.5" fill="#07111c"/>
    {born.has(a.id)&&active?<g stroke="#64ffc4" strokeWidth="1.6"><circle cy="-10" r="13" fill="none"/><path d="M11 -24v8m-4 -4h8"/></g>:null}
   </g>})}
   {active?frame.deaths.slice(0,2000).map(d=>{const [x,y]=p(d.position);return <g key={d.id} transform={`translate(${x} ${y-10})`} stroke="#ff8e9b" strokeWidth="2"><title>{`Recorded death: ${d.id}; last recorded position`}</title><path d="M-5 -5L5 5M5 -5L-5 5"/><circle r="10" fill="none" opacity=".5"/></g>}):null}
  </g>
 })}
 <text x="28" y="608" fill="#7a98ae" fontSize="12" fontFamily="monospace">GENESIS / OBSERVATION SPACE</text><text x="28" y="629" fill="#517087" fontSize="11">Cell coordinates are measured; layer separation is a visual encoding of time.</text>
 </svg>
}
