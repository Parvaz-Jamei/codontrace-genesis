export type Agent = {id:string;position:[number,number];energy:number|null;genome_digest:string};
export type Link = {source:string;target:string;kind:'parentage'|'two_parent_birth';source_position:[number,number];target_position:[number,number];historical_source:boolean};
export type Frame = {schema:'genesis_simulation_frame_v1';run_id:string;seed:number;generation:number;tick:number;world:{width:number;height:number};agents:Agent[];links:Link[];born_ids:string[];deaths:{id:string;position:[number,number]}[];metrics:{population:number;births:number|null;deaths:number|null;two_parent_births:number|null};lineage_recorded:boolean;metrics_scope?:string};
export type Page = {run_id:string;available:boolean;seeds:number[];seed?:number;cursor?:number;next_cursor?:number;total_frames:number;generations?:number[];frames:Frame[];reason?:string};
const finite=(x:unknown):x is number=>typeof x==='number'&&Number.isFinite(x);
const nonnegative=(x:unknown):x is number=>typeof x==='number'&&Number.isSafeInteger(x)&&x>=0;
const identity=(x:unknown,max=256):x is string=>typeof x==='string'&&x.length>0&&x.length<=max;
export function validatePage(raw:unknown):Page {
 const p=raw as Page;
 if(!p||!identity(p.run_id,128)||typeof p.available!=='boolean'||!Array.isArray(p.frames)||p.frames.length>32||!Array.isArray(p.seeds)||p.seeds.length>256||new Set(p.seeds).size!==p.seeds.length||!nonnegative(p.total_frames)||p.total_frames>100000||p.seeds.some(s=>!nonnegative(s)))throw Error('Invalid simulation page');
 for(const f of p.frames){
  if(f.schema!=='genesis_simulation_frame_v1'||!identity(f.run_id,128)||typeof f.lineage_recorded!=='boolean'||!Array.isArray(f.agents)||f.agents.length>20000||!Array.isArray(f.links)||f.links.length>60000||!Array.isArray(f.born_ids)||f.born_ids.length>20000||!Array.isArray(f.deaths)||f.deaths.length>20000||!nonnegative(f.seed)||!nonnegative(f.generation)||f.generation>999999999999||!nonnegative(f.tick)||!f.world||!nonnegative(f.world.width)||!nonnegative(f.world.height)||f.world.width<1||f.world.height<1||f.world.width>100000||f.world.height>100000||!f.metrics||f.metrics.population!==f.agents.length||(p.seed!==undefined&&f.seed!==p.seed))throw Error('Invalid recorded frame');
  const ids=new Set<string>();
  const position=(v:unknown):boolean=>Array.isArray(v)&&v.length===2&&v.every(nonnegative)&&v[0]<f.world.width&&v[1]<f.world.height;
  for(const a of f.agents){if(!identity(a.id)||!identity(a.genome_digest,128)||ids.has(a.id)||!position(a.position)||!(a.energy===null||finite(a.energy)))throw Error('Invalid agent data');ids.add(a.id)}
  const deaths=new Set<string>();
  for(const d of f.deaths){if(!identity(d.id)||!position(d.position)||ids.has(d.id)||deaths.has(d.id))throw Error('Invalid death record');deaths.add(d.id)}
  if(new Set(f.born_ids).size!==f.born_ids.length||f.born_ids.some(id=>!identity(id)||!ids.has(id)))throw Error('Invalid birth record');
  for(const key of ['births','deaths','two_parent_births'] as const)if(f.metrics[key]!==null&&!nonnegative(f.metrics[key]))throw Error('Invalid event count');
  if((f.metrics.births!==null&&f.born_ids.length>f.metrics.births)||(f.metrics.deaths!==null&&f.deaths.length>f.metrics.deaths)||(f.metrics.births!==null&&f.metrics.two_parent_births!==null&&f.metrics.two_parent_births>f.metrics.births))throw Error('Inconsistent event counts');
  for(const l of f.links)if(!['parentage','two_parent_birth'].includes(l.kind)||!identity(l.source)||!identity(l.target)||typeof l.historical_source!=='boolean'||!position(l.source_position)||!position(l.target_position)||(l.kind==='parentage'&&!ids.has(l.target)))throw Error('Invalid link data');
 }
 if(p.frames.some(f=>f.run_id!==p.frames[0].run_id))throw Error('Mixed engine runs');
 return p;
}
export function genomeColor(digest:string){let hash=0;for(const c of digest)hash=(hash*31+c.charCodeAt(0))>>>0;const h=(hash%360)/60,c=.4992,x=c*(1-Math.abs(h%2-1)),m=.4304;const rgb=h<1?[c,x,0]:h<2?[x,c,0]:h<3?[0,c,x]:h<4?[0,x,c]:h<5?[x,0,c]:[c,0,x];return '#'+rgb.map(v=>Math.round((v+m)*255).toString(16).padStart(2,'0')).join('')}
export function project(x:number,y:number,width:number,height:number,offset=0):[number,number]{const scale=Math.min(24,620/(width+height));return [490+(x-y-(width-height)/2)*scale,135+(x+y)*scale*.58+offset]}
export function nextIndex(current:number,total:number,loop:boolean){return current+1<total?current+1:loop&&total>0?0:current}
