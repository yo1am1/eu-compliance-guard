// Generate and check frontend types from the same validated Python schema.
import { readFile, writeFile } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';

const path = new URL('../src/lib/contract.ts', import.meta.url);
const { $defs, ...command } = JSON.parse(await readFile(new URL('../../eu_compliance_guard/contract.schema.json', import.meta.url), 'utf8'));
// The compiler visits unreachable definitions only beneath an object root.
const generated = await compile({ type: 'object', additionalProperties: false,
  $defs: { ...$defs, Command: command } }, 'ContractDefinitions', { unreachableDefinitions: true });
const exports = new Set([...generated.matchAll(/^export (?:interface|type) (\w+)/gm)].map(match => match[1]));
if ([...Object.keys($defs), 'Command'].some(name => !exports.has(name))) {
  throw new Error('Generated contract is missing public schema definitions');
}
if (process.argv.includes('--check')) {
  if (await readFile(path, 'utf8') !== generated) throw new Error('Frontend contract types are out of date');
} else {
  await writeFile(path, generated);
}
