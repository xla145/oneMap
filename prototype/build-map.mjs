import {build} from 'esbuild';
import {copyFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
await mkdir(new URL('./frontend/vendor/',import.meta.url),{recursive:true});
await build({absWorkingDir:root,entryPoints:['frontend/ol-entry.js'],bundle:true,format:'esm',target:['es2020'],minify:true,outfile:'frontend/vendor/openlayers.js',legalComments:'eof'});
await copyFile(new URL('./node_modules/ol/LICENSE.md',import.meta.url),new URL('./frontend/vendor/OpenLayers-LICENSE.md',import.meta.url));
console.log('OpenLayers JavaScript, CSS and license built locally.');
