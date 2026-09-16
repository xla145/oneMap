// Small, deterministic tools. Coordinates are WGS84 lon/lat unless stated otherwise.
const R=6371008.8, rad=Math.PI/180;
export const tools=[
  {id:'coordinate',name:'坐标转换',category:'基础空间工具',icon:'code',description:'WGS84 经纬度与 Web Mercator 坐标互转。',available:true},
  {id:'area',name:'面积量算',category:'基础空间工具',icon:'layers',description:'输入或绘制多边形，计算球面近似面积。',available:true},
  {id:'buffer',name:'点缓冲区分析',category:'基础空间工具',icon:'tool',description:'输入经纬度和距离，生成球面近似缓冲范围。',available:true},
  {id:'overlay',name:'叠加分析',category:'空间分析',icon:'layers',description:'多地块相交、差集、融合、面积量算与面缓冲，支持孔洞及 MultiPolygon。',available:true},
  {id:'compliance',name:'项目选址与合规性审查',category:'业务分析',icon:'shield',description:'上传或绘制地块，以示例规划、红线和基本农田数据运行空间核查并导出报告。',available:true}
];
export function number(value,label){if(!['string','number'].includes(typeof value)||String(value).trim()===''||!Number.isFinite(Number(value)))throw Error(`请填写有效的${label}`);return Number(value);}
export function lonlat(x,y){x=number(x,'经度');y=number(y,'纬度');if(Math.abs(x)>180||Math.abs(y)>85)throw Error('经度范围为 -180～180，纬度范围为 -85～85');return [x,y];}
export function convert(x,y,direction){
  if(!['forward','inverse'].includes(direction))throw Error('请选择有效的转换方向');
  if(direction==='forward'){[x,y]=lonlat(x,y);return {x:6378137*x*rad,y:6378137*Math.log(Math.tan(Math.PI/4+y*rad/2)),crs:'EPSG:3857',unit:'米'};}
  x=number(x,'X');y=number(y,'Y');if(Math.abs(x)>20037508.35||Math.abs(y)>19971868.89)throw Error('坐标超出本工具支持的 Web Mercator 范围');return {x:x/6378137/rad,y:(2*Math.atan(Math.exp(y/6378137))-Math.PI/2)/rad,crs:'EPSG:4326',unit:'度'};
}
function cross(a,b,c){return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
function on(a,b,c){return Math.abs(cross(a,b,c))<1e-10&&c[0]>=Math.min(a[0],b[0])-1e-10&&c[0]<=Math.max(a[0],b[0])+1e-10&&c[1]>=Math.min(a[1],b[1])-1e-10&&c[1]<=Math.max(a[1],b[1])+1e-10;}
export function polygon(input){
  let value;try{value=typeof input==='string'?JSON.parse(input):input;}catch{throw Error('请输入坐标数组或 GeoJSON Polygon');}
  if(value?.type==='Feature')value=value.geometry;
  if(value?.type==='Polygon'){if(value.coordinates?.length!==1)throw Error('当前量算仅支持无孔洞的单多边形');value=value.coordinates[0];}
  if(!Array.isArray(value)||value.length<3||value.length>500)throw Error('多边形需包含 3～500 个顶点');
  let ring=value.map(c=>{if(!Array.isArray(c)||c.length!==2)throw Error('每个顶点应为 [经度,纬度]');return lonlat(...c);});
  if(String(ring[0])===String(ring.at(-1)))ring.pop();
  if(ring.length<3||new Set(ring.map(String)).size!==ring.length)throw Error('多边形不能有重复顶点');
  if(Math.max(...ring.map(p=>p[0]))-Math.min(...ring.map(p=>p[0]))>180)throw Error('当前工具不支持跨日期变更线的多边形');
  for(let i=0;i<ring.length;i++)for(let j=i+1;j<ring.length;j++){
    if(j===i+1||(i===0&&j===ring.length-1))continue;
    const a=ring[i],b=ring[(i+1)%ring.length],c=ring[j],d=ring[(j+1)%ring.length];
    if((cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0)||on(a,b,c)||on(a,b,d)||on(c,d,a)||on(c,d,b))throw Error('多边形存在自相交，请检查顶点顺序');
  }
  ring.push([...ring[0]]);return ring;
}
export function area(ring){let sum=0;for(let i=0;i<ring.length-1;i++){const a=ring[i],b=ring[i+1];sum+=(b[0]-a[0])*rad*(2+Math.sin(a[1]*rad)+Math.sin(b[1]*rad));}const result=Math.abs(sum)*R*R/2;if(result<0.01)throw Error('多边形面积必须大于零');return result;}
export function buffer(x,y,distance){
  [x,y]=lonlat(x,y);distance=number(distance,'缓冲距离');if(distance<=0||distance>100000)throw Error('缓冲距离应大于 0 且不超过 100000 米');
  const lat=y*rad,lon=x*rad,d=distance/R,ring=[];
  for(let i=0;i<64;i++){const bearing=i/64*Math.PI*2,l=Math.asin(Math.sin(lat)*Math.cos(d)+Math.cos(lat)*Math.sin(d)*Math.cos(bearing)),o=lon+Math.atan2(Math.sin(bearing)*Math.sin(d)*Math.cos(lat),Math.cos(d)-Math.sin(lat)*Math.sin(l));ring.push([((o/rad+540)%360)-180,l/rad]);}
  return polygon(ring);
}
