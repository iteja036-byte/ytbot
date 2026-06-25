const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const os = require('os');

const D = path.join(os.homedir(), 'ytbot');
const SCOPES = ['https://www.googleapis.com/auth/youtube.upload'];

const TP = path.join(D, 'token.json');
const CP = path.join(D, 'credentials.json');

function askQuestion(query) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise(resolve => {
    rl.question(query, answer => {
      rl.close();
      resolve(answer);
    });
  });
}

async function authenticate() {
  // 1. Check credentials
  if (!fs.existsSync(CP)) {
    console.log('\nERROR: credentials.json not found!');
    console.log('Fix steps:');
    console.log('1. Go to https://console.cloud.google.com');
    console.log('2. Create project: ytbot');
    console.log('3. Enable YouTube Data API v3');
    console.log('4. Create OAuth 2.0 Desktop credentials');
    console.log('5. Download JSON → place in ~/ytbot/credentials.json');
    process.exit(1);
  }

  // 2. Read credentials
  const cr = JSON.parse(fs.readFileSync(CP));
  const { client_secret, client_id, redirect_uris } = cr.installed;

  const o = new google.auth.OAuth2(
    client_id,
    client_secret,
    redirect_uris[0]
  );

  // 3. If token exists → reuse it
  if (fs.existsSync(TP)) {
    const t = JSON.parse(fs.readFileSync(TP));

    if (t.expiry_date && Date.now() < t.expiry_date) {
      o.setCredentials(t);
      console.log('✅ Already logged in');
      return o;
    }
  }

  // 4. Need new login
  const authUrl = o.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES
  });

  console.log('\n👉 Open this URL and login:\n');
  console.log(authUrl);

  const code = await askQuestion('\nPaste Google code here: ');

  const { tokens } = await o.getToken(code.trim());

  o.setCredentials(tokens);

  fs.writeFileSync(TP, JSON.stringify(tokens));
  console.log('\n✅ Login saved forever!');

  return o;
}

module.exports = { authenticate };
