import json, subprocess, sys
from pathlib import Path
try:
 from codontrace.genesis.engine import GenesisEngine
 from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
 r=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7,tick_count=12,population=6)).run_ticks()
 data={'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'snapshot':r.snapshot.to_dict(),'digest':r.snapshot.digest(),'ticks':[t.to_dict() for t in r.ticks],'tick_digests':[t.digest() for t in r.ticks]}
 Path('../digest_evidence').mkdir(exist_ok=True)
 Path('../digest_evidence/'+data['commit']+'.json').write_text(json.dumps(data,sort_keys=True,indent=2))
 print(data['commit'],data['digest'],data['tick_digests'][0],flush=True)
 sys.exit(0 if data['digest']=='76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a' else 1)
except Exception as e:
 print(type(e).__name__,str(e),flush=True);sys.exit(125)
