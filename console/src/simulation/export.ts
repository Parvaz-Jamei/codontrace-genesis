import type {Frame} from './model';

// Capture the scope and data BEFORE any dynamic import or other asynchronous work.
// Later seed changes and cache eviction cannot change the exported experiment.
export function captureSequence(cache:ReadonlyMap<number,Frame>,index:number,run:string,seed:number|null,cap:number){
 const frames=[...cache.entries()].filter(([i])=>Math.abs(i-index)<=8).sort((a,b)=>a[0]-b[0]).slice(0,16).map(([,f])=>structuredClone(f));
 if(!frames.length||seed===null||frames.some(f=>f.seed!==seed||f.run_id!==frames[0].run_id))throw Error('Export requires one recorded seed and engine run');
 return {frames,manifest:{schema:'genesis_simulation_sequence_v1',run_id:run,engine_run_id:frames[0].run_id,seed,
  scope:'cached_recorded_window_max_16_frames',visible_glyph_budget:cap,generations:frames.map(f=>f.generation),ticks:frames.map(f=>f.tick),
  population_counts:frames.map(f=>f.metrics.population),interpolated:false}};
}
