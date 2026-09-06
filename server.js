import express from 'express';
import session from 'express-session';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.use(session({
  secret: 'bot-suite-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 86400000 }
}));

let botProcess = null;
let taskState = {
  status: 'Idle',
  email: '',
  logs: ['System initialized. Web Console connected to bot.py engine.']
};

function addLog(msg) {
  const timestamp = new Date().toLocaleTimeString();
  const cleanMsg = msg.toString().trim();
  if (cleanMsg) {
    taskState.logs.unshift(`[${timestamp}] ${cleanMsg}`);
    if (taskState.logs.length > 100) taskState.logs.pop();
  }
}

// Routes serving index.html
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/index', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// JSON API endpoint for status & logs
app.get('/api/status', (req, res) => {
  res.json({
    status: taskState.status,
    email: taskState.email,
    active: botProcess !== null,
    logs: taskState.logs
  });
});

// Start Task API Endpoint
app.post('/api/start', (req, res) => {
  const { email } = req.body;
  taskState.email = email;
  
  if (botProcess) {
    addLog('⚠️ Stopping active previous bot process...');
    try { botProcess.kill(); } catch (e) {}
  }

  addLog(`🚀 Launching bot.py engine for email: ${email}`);
  taskState.status = 'Running (Awaiting OTP)';

  const botPath = path.join(__dirname, 'bot.py');
  botProcess = spawn('python3', ['-u', botPath], { cwd: __dirname });

  setTimeout(() => {
    if (botProcess && botProcess.stdin) {
      botProcess.stdin.write(`${email}\n`);
      addLog(`📧 Sent email '${email}' to bot.py stdin prompt.`);
    }
  }, 1000);

  botProcess.stdout.on('data', (data) => {
    addLog(data.toString());
  });

  botProcess.stderr.on('data', (data) => {
    addLog(`[STDERR] ${data.toString()}`);
  });

  botProcess.on('close', (code) => {
    addLog(`🏁 bot.py finished execution with exit code ${code}`);
    taskState.status = `Completed (Exit Code ${code})`;
    botProcess = null;
  });

  res.json({ success: true, message: 'Task started successfully' });
});

// Submit OTP API Endpoint
app.post('/api/submit-otp', (req, res) => {
  const { otp } = req.body;
  taskState.otp = otp;
  
  if (botProcess && botProcess.stdin) {
    botProcess.stdin.write(`${otp}\n`);
    addLog(`🔑 Sent OTP Code '${otp}' to bot.py process.`);
    taskState.status = 'Processing OTP Code...';
    res.json({ success: true, message: 'OTP sent to process' });
  } else {
    addLog(`⚠️ No active bot.py process found to receive OTP.`);
    res.json({ success: false, message: 'No active bot process' });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Bot Suite Web Console connected and running at http://localhost:${PORT}`);
});
