import React, { useRef, useState } from "react";
import type { ScientificChartSpec } from "@/lib/genesis/types";

const palettes = {
  accessible: ["#56b4e9", "#e69f00", "#009e73", "#f0e442", "#cc79a7", "#d55e00"],
  cool: ["#67e8f9", "#a5b4fc", "#6ee7b7", "#93c5fd", "#c4b5fd", "#2dd4bf"],
  warm: ["#fda4af", "#fdba74", "#fde047", "#f9a8d4", "#fb7185", "#fbbf24"],
  mono: ["#ffffff", "#e4e4e7", "#d4d4d8", "#a1a1aa", "#fafafa", "#bcbcbc"],
};
const dashes = ["", "8 3", "2 3", "8 3 2 3", "12 4", "4 4"];
function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}
export function ScientificChart({ spec }: { spec: ScientificChartSpec }) {
  const ref = useRef<SVGSVGElement>(null);
  const [table, setTable] = useState(false), [error, setError] = useState("");
  const colors = palettes[spec.palette ?? "accessible"] ?? palettes.accessible;
  const series = (Array.isArray(spec.series) ? spec.series : []).filter(s=>s && Array.isArray(s.points)).slice(0,12).map(s => ({...s, points:s.points.filter(p => Array.isArray(p) && p.length>=2 && p.every(Number.isFinite)).slice(0,2000)}));
  const points = series.flatMap(s=>s.points);
  const matrix = (Array.isArray(spec.matrix) ? spec.matrix : []).filter(Array.isArray).slice(0,100).map(r=>r.slice(0,100));
  const heat = spec.chart_type === "heatmap";
  const finite = matrix.flat().filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const boxes = spec.boxes ?? [];
  if (heat ? !finite.length : !points.length) return <p>No finite measured data for this chart.</p>;
  const transform = (v:number, scale?:string) => scale === "log" ? Math.log10(v) : v;
  if (!heat && points.some(p=>(spec.x_scale === "log" && p[0]<=0)||(spec.y_scale === "log" && p[1]<=0))) return <p role="alert">Log axes require positive values.</p>;
  const xt = points.map(p=>transform(p[0],spec.x_scale));
  const yValues = boxes.length ? boxes.flatMap(b=>[b.low,b.high,...b.outliers]) : points.flatMap(p=>spec.chart_type === "errorbar" ? [p[1],p[2],p[3]] : [p[1]]);
  const yt = yValues.map(v=>transform(v,spec.y_scale));
  const baseline = ["bar","histogram","area","density"].includes(spec.chart_type);
  let x0 = Math.min(...xt), x1 = Math.max(...xt), y0 = Math.min(...yt), y1 = Math.max(...yt);
  if (baseline) { y0 = Math.min(0,y0); y1 = Math.max(0,y1); }
  if (spec.chart_type === "histogram") { x0 -= (spec.bin_width ?? 0)/2; x1 += (spec.bin_width ?? 0)/2; }
  if (boxes.length || spec.chart_type === "violin") { x0 = -0.7; x1 = series.length - 0.3; }
  if (spec.chart_type === "violin") { y0 = Math.min(...points.map(p=>p[0])); y1 = Math.max(...points.map(p=>p[0])); }
  const px = (v:number)=>55+(transform(v,spec.x_scale)-x0)/(x1-x0||1)*500;
  const py = (v:number)=>295-(transform(v,spec.y_scale)-y0)/(y1-y0||1)*255;
  const inverse=(v:number,scale?:string)=>scale === "log" ? 10**v : v;
  const exportImage = async (format:"svg"|"png") => {
    if (!ref.current) return;
    setError("");
    try {
      const copy = ref.current.cloneNode(true) as SVGSVGElement;
      copy.setAttribute("xmlns","http://www.w3.org/2000/svg"); copy.setAttribute("width","1800"); copy.setAttribute("height","1320");
      const svg = new Blob([new XMLSerializer().serializeToString(copy)],{type:"image/svg+xml"});
      if (format === "svg") { save(svg,"scientific-chart.svg"); return; }
      const url=URL.createObjectURL(svg);
      try {
        const image=new Image(); image.src=url; await image.decode();
        const canvas=document.createElement("canvas"); canvas.width=1800;canvas.height=1320;
        const ctx=canvas.getContext("2d"); if(!ctx) throw Error("Canvas unavailable"); ctx.drawImage(image,0,0);
        const png=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error("PNG export failed")),"image/png")); save(png,"scientific-chart.png");
      } finally { URL.revokeObjectURL(url); }
    } catch(e) { setError(String(e)); }
  };
  return <div dir="ltr">
    <div className="mb-2 flex flex-wrap gap-2 text-xs">
      <button className="min-h-9 rounded bg-white/10 px-2" onClick={()=>void exportImage("svg")}>SVG ↓</button>
      <button className="min-h-9 rounded bg-white/10 px-2" onClick={()=>void exportImage("png")}>PNG ↓</button>
      <button className="min-h-9 rounded bg-white/10 px-2" aria-expanded={table} onClick={()=>setTable(v=>!v)}>Data / داده</button>
      <span>{spec.x_scale === "log" || spec.y_scale === "log" ? "Log scale" : "Linear scale"} · {spec.palette ?? "accessible"}</span>
    </div>
    {error && <p role="alert">{error}</p>}
    <svg ref={ref} viewBox="0 0 600 440" fontFamily="Arial, sans-serif" role="img" aria-label={spec.title} className="w-full">
      <title>{spec.title}</title><desc>Recorded observations. Series use labels and dash patterns as well as color. Data and provenance are available separately.</desc>
      <rect width="600" height="440" fill="#181a20"/>
      <text x="300" y="18" fill="#f4f4f5" fontSize="12" textAnchor="middle">{spec.title.slice(0,85)}</text>
      {heat ? <>
        {matrix.map((row,y)=>row.map((v,x)=>{
          const low=spec.color_min ?? Math.min(...finite), high=spec.color_max ?? Math.max(...finite);
          const f=typeof v === "number" && Number.isFinite(v) ? (v-low)/(high-low||1) : null;
          const color=f===null?"#52525b":spec.palette === "mono"?`hsl(0 0% ${25+60*f}%)`:`hsl(${spec.palette === "warm" ? 5+45*f : spec.palette === "cool" ? 270-90*f : 240-200*f} 65% ${38+15*f}%)`;
          const n=Math.max(1,...matrix.map(r=>r.length));
          return <g key={`${x}:${y}`}><rect x={55+x*500/n} y={30+y*250/matrix.length} width={500/n} height={250/matrix.length} fill={color} stroke="#181a20" strokeWidth="1"><title>{`${spec.row_labels?.[y]??y} / ${spec.column_labels?.[x]??x}: ${v??"missing"}`}</title></rect>{n<=12&&matrix.length<=12&&<text x={55+(x+.5)*500/n} y={30+(y+.5)*250/matrix.length} fill="#fff" fontSize="10" textAnchor="middle" stroke="#181a20" strokeWidth=".6" paintOrder="stroke">{v===null?"—":v?.toPrecision(2)}</text>}</g>;
        }))}
        {matrix.length <= 12 && matrix.map((r,y)=><text key={y} x="51" y={30+(y+.5)*250/matrix.length} fill="#d4d4d8" textAnchor="end" fontSize="8">{String(spec.row_labels?.[y]??y).slice(0,9)}</text>)}
        {(matrix[0]?.length ?? 0) <= 12 && (matrix[0]??[]).map((_,x)=><text key={x} x={55+(x+.5)*500/Math.max(1,matrix[0].length)} y="291" fill="#d4d4d8" textAnchor="middle" fontSize="8">{String(spec.column_labels?.[x]??x).slice(0,9)}</text>)}
        <text x="55" y="316" fill="#d4d4d8" fontSize="10">{`Color scale: ${(spec.color_min??Math.min(...finite)).toPrecision(3)} → ${(spec.color_max??Math.max(...finite)).toPrecision(3)}; gray = missing`}</text>
      </> : <>
        <path d="M55 30V295H560" stroke="#a1a1aa" fill="none"/>
        {[0,.25,.5,.75,1].map(v=><g key={v}>
          <path d={`M55 ${295-v*255}H555`} stroke="#3f3f46"/>
          <text x="48" y={299-v*255} fill="#d4d4d8" textAnchor="end" fontSize="10">{inverse(y0+v*(y1-y0),spec.y_scale).toPrecision(3)}</text>
          {!boxes.length && spec.chart_type !== "violin" && <text x={55+v*500} y="312" fill="#d4d4d8" textAnchor="middle" fontSize="10">{inverse(x0+v*(x1-x0),spec.x_scale).toPrecision(3)}</text>}
        </g>)}
        {(boxes.length > 0 || spec.chart_type === "violin") && series.map((s,i)=><text key={s.name} x={px(i)} y="312" fill="#d4d4d8" textAnchor="middle" fontSize="10">{i+1}</text>)}
        {series.map((s,i)=>{
          const color=colors[i%colors.length], kind=spec.chart_type;
          const path=s.points.map((p,j)=>`${j?"L":"M"}${px(p[0])},${py(p[1])}`).join(" ");
          const step=s.points.map((p,j)=>j?`H${px(p[0])}V${py(p[1])}`:`M${px(p[0])},${py(p[1])}`).join(" ");
          return <g key={s.name} stroke={color} fill={color}><title>{s.name}</title>
            {["line","step","area","ecdf","density"].includes(kind) ? <>
              {kind === "area" && <path d={`${path} L${px(s.points.at(-1)![0])},${py(0)} L${px(s.points[0][0])},${py(0)} Z`} opacity=".2" stroke="none"/>}
              <path d={["step","ecdf"].includes(kind)?step:path} fill="none" strokeWidth="2" strokeDasharray={dashes[i%dashes.length]}/>
            </> : kind === "box" ? boxes.filter(b=>b.index===i).map(b=><g key={b.name}>
              <path d={`M${px(i)} ${py(b.low)}V${py(b.high)} M${px(i)-10} ${py(b.low)}H${px(i)+10} M${px(i)-10} ${py(b.high)}H${px(i)+10}`} fill="none"/>
              <rect x={px(i)-16} y={py(b.q3)} width="32" height={Math.max(1,py(b.q1)-py(b.q3))} fill={color} fillOpacity=".25"/>
              <path d={`M${px(i)-16} ${py(b.median)}H${px(i)+16}`} strokeWidth="3"/>
              {b.outliers.map((v,j)=><circle key={j} cx={px(i)} cy={py(v)} r="2"/>)}
              <title>{`${b.name}: n=${b.n}, median=${b.median}, Q1=${b.q1}, Q3=${b.q3}`}</title>
            </g>) : kind === "violin" ? (()=>{
              const peak=Math.max(...s.points.map(p=>p[1]))||1;
              const width=150/series.length;
              const p=s.points.map(v=>`${px(i)-v[1]/peak*width},${py(v[0])}`).concat([...s.points].reverse().map(v=>`${px(i)+v[1]/peak*width},${py(v[0])}`)).join(" ");
              return <polygon points={p} fillOpacity=".3" strokeWidth="2"/>;
            })() : s.points.map((p,j)=><g key={j}><title>{`${s.name}: ${p.join(", ")}`}</title>
              {kind === "bar" || kind === "histogram" ? <rect x={px(p[0])-(kind === "histogram"?Math.abs(px(p[0]+(spec.bin_width??1))-px(p[0]))/2:3)} y={Math.min(py(p[1]),py(0))} width={kind === "histogram"?Math.max(1,Math.abs(px(p[0]+(spec.bin_width??1))-px(p[0]))-1):6} height={Math.max(1,Math.abs(py(p[1])-py(0)))} fillOpacity=".55"/> : <>
                {kind === "errorbar" && <path d={`M${px(p[0])} ${py(p[2])}V${py(p[3])} M${px(p[0])-4} ${py(p[2])}H${px(p[0])+4} M${px(p[0])-4} ${py(p[3])}H${px(p[0])+4}`} fill="none"/>}
                <circle cx={px(p[0])} cy={py(p[1])} r={kind === "bubble"?3+12*Math.sqrt(p[2]/(Math.max(...points.map(v=>v[2]??0))||1)):2.8} fillOpacity=".65"/>
              </>}
            </g>)}
          </g>;
        })}
      </>}
      <text x="300" y="341" textAnchor="middle" fill="#d4d4d8" fontSize="11">{spec.chart_type === "violin"?"group (see legend)":spec.x_label}</text>
      <text x="12" y="160" transform="rotate(-90 12 160)" textAnchor="middle" fill="#d4d4d8" fontSize="11">{spec.chart_type === "violin"?spec.x_label:spec.y_label}</text>
      {series.map((s,i)=><g key={`legend:${s.name}`}><path d={`M${20+(i%3)*195} ${366+Math.floor(i/3)*17}h20`} stroke={colors[i%colors.length]} strokeWidth="2" strokeDasharray={dashes[i%dashes.length]}/><text x={45+(i%3)*195} y={370+Math.floor(i/3)*17} fill="#f4f4f5" fontSize="9"><title>{s.name}</title>{`${i+1}. ${s.name.slice(0,27)}`}</text></g>)}
    </svg>
    <div className="flex flex-wrap gap-3 text-xs">{series.map((s,i)=><span key={s.name} style={{color:colors[i%colors.length]}}>{i+1}. {s.name}</span>)}</div>
    {table && <div className="max-h-72 overflow-auto"><table className="w-full text-xs"><caption>Displayed data (full artifact: JSON download)</caption><thead><tr><th>Series / row</th><th>x / column</th><th>Values</th></tr></thead><tbody>
      {heat ? matrix.flatMap((r,y)=>r.map((v,x)=><tr key={`${y}:${x}`}><td>{spec.row_labels?.[y]??y}</td><td>{spec.column_labels?.[x]??x}</td><td>{v??"missing"}</td></tr>)) : series.flatMap(s=>s.points.map((p,j)=><tr key={`${s.name}:${j}`}><td>{s.name}</td><td>{p[0]}</td><td>{p.slice(1).join(", ")}</td></tr>))}
    </tbody></table></div>}
  </div>;
}
