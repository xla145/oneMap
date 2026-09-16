// Draft editing preserves source coordinates; server validation remains authoritative.
export function parcelCollection(text){
  if(!text.trim())return {type:'FeatureCollection',features:[]};
  let value=JSON.parse(text);
  if(Array.isArray(value))value={type:'Polygon',coordinates:[value]};
  const rows=value?.type==='FeatureCollection'?value.features:[value?.type==='Feature'?value:{type:'Feature',geometry:value,properties:{}}];
  if(!Array.isArray(rows)||rows.length>100)throw Error('最多 100 个地块');
  return {type:'FeatureCollection',features:rows.map((f,i)=>{
    if(f?.type!=='Feature'||!['Polygon','MultiPolygon'].includes(f.geometry?.type))throw Error('仅支持面或多面地块');
    return {...f,properties:{...f.properties,id:String(f.properties?.id??f.id??'parcel-'+(i+1)),name:String(f.properties?.name??'地块 '+(i+1))}};
  })};
}
export function updateParcel(data,index,geometry,name){
  const rows=data.features.map(f=>({...f,properties:{...f.properties}}));
  if(index!==null&&(!Number.isInteger(index)||index<0||index>=rows.length))throw Error('地块已变更，请重新选择');
  if(!['Polygon','MultiPolygon'].includes(geometry?.type))throw Error('仅支持面或多面地块');
  if(index===null){
    if(rows.length>=100)throw Error('最多 100 个地块');
    let i=1;while(rows.some(f=>f.properties.id==='parcel-'+i))i++;
    rows.push({type:'Feature',geometry,properties:{id:'parcel-'+i,name:name||'地块 '+i}});
  }else rows[index]={...rows[index],geometry,properties:{...rows[index].properties,name:name||rows[index].properties.name}};
  return {type:'FeatureCollection',features:rows};
}
