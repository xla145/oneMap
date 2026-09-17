/* Geographic calculations for the local interaction demo. Spherical approximations. */
(function(root){
 const R=6371008.8, rad=n=>n*Math.PI/180;
 const distance=(a,b)=>{const p=rad(b[1]-a[1]),q=rad(b[0]-a[0]);return 2*R*Math.asin(Math.min(1,Math.sqrt(Math.sin(p/2)**2+Math.cos(rad(a[1]))*Math.cos(rad(b[1]))*Math.sin(q/2)**2)));};
 function points(g){if(g.type==='Point')return [g.coordinates];if(g.type==='LineString'||g.type==='MultiPoint')return g.coordinates;if(g.type==='Polygon'||g.type==='MultiLineString')return g.coordinates.flat();if(g.type==='MultiPolygon')return g.coordinates.flat(2);return [];}
 function bbox(g){const p=points(g);return [Math.min(...p.map(x=>x[0])),Math.min(...p.map(x=>x[1])),Math.max(...p.map(x=>x[0])),Math.max(...p.map(x=>x[1]))];}
 function center(g){const b=bbox(g);return [(b[0]+b[2])/2,(b[1]+b[3])/2];}
 function onSegment(p,a,b){return Math.abs((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))<1e-10&&p[0]>=Math.min(a[0],b[0])-1e-10&&p[0]<=Math.max(a[0],b[0])+1e-10&&p[1]>=Math.min(a[1],b[1])-1e-10&&p[1]<=Math.max(a[1],b[1])+1e-10;}
 function inRing(p,ring){let yes=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if(onSegment(p,a,b))return true;if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;}
 function inside(p,g){if(g.type==='MultiPolygon')return g.coordinates.some(c=>inside(p,{type:'Polygon',coordinates:c}));return g.type==='Polygon'&&inRing(p,g.coordinates[0])&&!g.coordinates.slice(1).some(r=>inRing(p,r));}
 const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
 function segmentsIntersect(a,b,c,d){if(onSegment(a,c,d)||onSegment(b,c,d)||onSegment(c,a,b)||onSegment(d,a,b))return true;return cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0;}
 function segments(g){let rings=g.type==='Polygon'?g.coordinates:g.type==='MultiPolygon'?g.coordinates.flat():g.type==='LineString'?[g.coordinates]:g.type==='MultiLineString'?g.coordinates:[];return rings.flatMap(r=>r.slice(1).map((p,i)=>[r[i],p]));}
 function intersects(a,b){const ab=bbox(a),bb=bbox(b);if(ab[0]>bb[2]||ab[2]<bb[0]||ab[1]>bb[3]||ab[3]<bb[1])return false;if(a.type==='Point')return inside(a.coordinates,b);if(b.type==='Point')return inside(b.coordinates,a);if(points(a).some(p=>inside(p,b))||points(b).some(p=>inside(p,a)))return true;return segments(a).some(([p,q])=>segments(b).some(([r,s])=>segmentsIntersect(p,q,r,s)));}
 function area(g){if(g.type==='MultiPolygon')return g.coordinates.reduce((s,c)=>s+area({type:'Polygon',coordinates:c}),0);if(g.type!=='Polygon')return 0;const ringArea=r=>Math.abs(r.reduce((s,p,i)=>{const q=r[(i+1)%r.length];return s+rad(q[0]-p[0])*(2+Math.sin(rad(p[1]))+Math.sin(rad(q[1])));},0)*R*R/2);return Math.max(0,ringArea(g.coordinates[0])-g.coordinates.slice(1).reduce((s,r)=>s+ringArea(r),0));}
 function circle(c,meters){const lat=rad(c[1]),lng=rad(c[0]),ang=meters/R,ring=[];for(let i=0;i<=96;i++){const a=i/96*2*Math.PI,p=Math.asin(Math.sin(lat)*Math.cos(ang)+Math.cos(lat)*Math.sin(ang)*Math.cos(a)),q=lng+Math.atan2(Math.sin(a)*Math.sin(ang)*Math.cos(lat),Math.cos(ang)-Math.sin(lat)*Math.sin(p));ring.push([q*180/Math.PI,p*180/Math.PI]);}return {type:'Polygon',coordinates:[ring]};}
 const api={distance,points,bbox,center,inside,intersects,area,circle};root.Spatial=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
