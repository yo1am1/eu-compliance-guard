// Generate and check frontend types from the same validated Python schema.
import { readFile, writeFile } from 'node:fs/promises';
import { compileFromFile } from 'json-schema-to-typescript';

const path = new URL('../src/lib/contract.ts', import.meta.url);
const generated = await compileFromFile(new URL('../../eu_compliance_guard/contract.schema.json', import.meta.url).pathname, { unreachableDefinitions: true });
if (process.argv.includes('--check')) {
  if (await readFile(path, 'utf8') !== generated) throw new Error('Frontend contract types are out of date');
} else {
  await writeFile(path, generated);
}
