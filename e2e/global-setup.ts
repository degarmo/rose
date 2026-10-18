import { execSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { FIXTURES_FILE } from './tests/support'

/** Reset the known test data on the server and keep a copy for the tests. */
export default function globalSetup() {
  if (process.env.E2E_SMOKE === '1') return
  const command =
    process.env.E2E_FIXTURES_CMD ??
    'docker compose -f ../docker-compose.e2e.yml exec -T app python manage.py e2e_fixtures --json'
  const output = execSync(command, { encoding: 'utf8' })
  const json = output.slice(output.indexOf('{'))
  writeFileSync(FIXTURES_FILE, json)
}
