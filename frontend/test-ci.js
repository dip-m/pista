// Cross-platform test runner for CI
process.env.CI = 'true';
const { spawn } = require('child_process');
const path = require('path');

const testProcess = spawn('npm', ['test', '--', '--coverage', '--watchAll=false'], {
  cwd: __dirname,
  stdio: 'inherit',
  shell: true
});

testProcess.on('exit', (code) => {
  process.exit(code || 0);
});
