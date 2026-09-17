// Extract local reference assets without changing the supplied demo.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL("../", import.meta.url));
const source=path.join(root,'../bak/内蒙古一张图demo');
const output=path.join(root,'assets/nmg-demo');
fs.mkdirSync(path.join(output,'data'),{recursive:true});
const scope={window:{}};vm.createContext(scope);
const names=['nmg_geo','nmg_county','nmg_stats','nmg_poi','nmg_town','nmg_nr','nmg_modules'];
const manifest={source:'bak/内蒙古一张图demo',notice:'原始模拟演示数据，非正式业务成果。原始坐标与字段完整保留。',files:[]};
for(const name of names){
 const raw=fs.readFileSync(path.join(source,'nmgyzt/data',name+'.js'));
 fs.writeFileSync(path.join(output,'data',name+'.js'),raw);
 vm.runInContext(raw.toString('utf8'),scope,{timeout:3000});
 manifest.files.push({name:'data/'+name+'.js',bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')});
}
for(const [name,value] of Object.entries(scope.window))fs.writeFileSync(path.join(output,'data',name.toLowerCase()+'.json'),JSON.stringify(value));
for(const name of ['内蒙古自然资源一张图.html','nmg_terrain_admin.png','nmg_province.geojson','nmg_cities.geojson','nmg_counties.geojson','nmg_centers.geojson']){
 const dest=name.endsWith('.html')?'index.html':name;fs.copyFileSync(path.join(source,name),path.join(output,dest));
 const raw=fs.readFileSync(path.join(output,dest));manifest.files.push({name:dest,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')});
}
manifest.counts={layers:scope.window.NMG_NR.LAYERS.length,features:scope.window.NMG_NR.FEATURES.length,counties:scope.window.NMG_COUNTY.features.length,towns:scope.window.NMG_TOWN.length,modules:scope.window.NMG_MODULES.length,functions:scope.window.NMG_MODULES.flatMap(m=>m.groups.flatMap(g=>g.items)).length};
fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2));
console.log(JSON.stringify(manifest.counts));
