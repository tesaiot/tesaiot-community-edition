const path = require('path');
const fs = require('fs');

const distNodesDir = path.join(__dirname, 'dist', 'nodes');
const nodesDir = fs.existsSync(distNodesDir) ? [distNodesDir] : [];

module.exports = {
  flowFile: process.env.NODE_RED_FLOW_FILE || path.join('flows', 'tesaiot-dashboard.json'),
  flowFilePretty: true,
  credentialSecret: process.env.NODE_RED_CREDENTIAL_SECRET || 'change-me-in-production',
  httpAdminRoot: '/admin',
  httpNodeRoot: '/api',
  ui: { path: '/dashboard' },
  editorTheme: {
    page: {
      css: path.join(__dirname, 'theme', 'custom.css')
    },
    projects: { enabled: false },
    codeEditor: {
      lib: 'monaco',
      options: {
        theme: 'vs-dark'
      }
    }
  },
  runtimeState: {
    enabled: true,
    ui: true
  },
  functionExternalModules: true,
  exportGlobalContextKeys: true,
  functionGlobalContext: {
    TESAIOT_BASE_URL: process.env.TESAIOT_BASE_URL || 'https://admin.tesaiot.com/api/v1/external',
    TESAIOT_API_KEY: process.env.TESAIOT_API_KEY || undefined
  },
  nodesDir,
  logging: {
    console: {
      level: process.env.NODE_RED_LOG_LEVEL || 'info',
      metrics: false,
      audit: false
    }
  },
  contextStorage: {
    default: {
      module: 'memory'
    }
  },
  paletteCategories: {
    order: [
      'tesaiot',
      'dashboard',
      'function',
      'network',
      'storage',
      'input',
      'output'
    ]
  }
};
