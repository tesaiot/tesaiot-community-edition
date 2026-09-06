import { TesaiotClient } from '../lib/client';
import { Node, NodeDef, NodeInitializer } from 'node-red';
import { createTesaiotClient } from '../lib/client';

interface TesaiotApiGatewayConfig extends NodeDef {
  baseUrl?: string;
  timeout?: number;
  verifyTls?: boolean;
}

type TesaiotApiGatewayNode = Node & {
  credentials?: TesaiotApiGatewayCredentials;
  client?: TesaiotClient;
  getClient: () => TesaiotClient;
};

interface TesaiotApiGatewayCredentials {
  apiKey?: string;
}

const nodeInit: NodeInitializer = (RED): void => {
  function TesaiotApiGateway(this: TesaiotApiGatewayNode, config: TesaiotApiGatewayConfig): void {
    RED.nodes.createNode(this, config);

    const credentials = this.credentials || {};
    const defaultBaseUrl = 'https://localhost/api/v1';
    const baseUrl = (config.baseUrl || process.env.TESAIOT_BASE_URL || defaultBaseUrl).trim();
    const timeout = Number(config.timeout) || 10000;
    const verifyTls = config.verifyTls !== false;
    const apiKey = (credentials.apiKey || process.env.TESAIOT_API_KEY || '').trim();

    this.getClient = (): TesaiotClient => {
      throw new Error('TESAIoT API Gateway client is not initialised. Provide a base URL and API key.');
    };

    if (!baseUrl || !apiKey) {
      this.status({ fill: 'red', shape: 'ring', text: 'missing configuration' });
      this.error('TESAIoT API Gateway node requires base URL and API key.');
      return;
    }

    try {
      // lib/client.ts is fetch-based, not axios: the option is timeoutMs, and
      // TLS verification is Node's (set NODE_TLS_REJECT_UNAUTHORIZED=0 for a
      // stock install's private-PKI certificate) rather than a client option.
      this.client = createTesaiotClient({
        baseUrl,
        apiKey,
        timeoutMs: timeout
      });
      if (!verifyTls) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
      }

      this.getClient = (): TesaiotClient => {
        if (!this.client) {
          throw new Error('API client has not been initialised.');
        }
        return this.client;
      };

      this.status({ fill: 'green', shape: 'dot', text: 'ready' });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.status({ fill: 'red', shape: 'ring', text: 'config error' });
      this.error(message);
    }

    this.on('close', (done: () => void) => {
      this.client = undefined;
      done();
    });
  }

  RED.nodes.registerType('tesaiot-api-gateway', TesaiotApiGateway as any, {
    category: 'config',
    defaults: {
      name: { value: '' },
      baseUrl: { value: 'https://localhost/api/v1', required: false },
      timeout: { value: 10000 },
      verifyTls: { value: true }
    },
    credentials: {
      apiKey: { type: 'password' }
    }
  } as any);
};

export = nodeInit;
