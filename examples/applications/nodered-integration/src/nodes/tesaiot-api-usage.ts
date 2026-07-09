import { Node, NodeDef, NodeInitializer } from 'node-red';
import { AxiosInstance } from 'axios';

interface TesaiotApiUsageConfig extends NodeDef {
  gateway: string;
  window?: number;
}

type TesaiotApiUsageNode = Node & {
  getClient: () => AxiosInstance;
};

interface TesaiotApiGatewayNode extends Node {
  getClient: () => AxiosInstance;
}

const clampWindow = (value: number): number => {
  if (!Number.isFinite(value) || value <= 0) {
    return 60;
  }
  return Math.max(1, Math.min(value, 1440));
};

const nodeInit: NodeInitializer = (RED): void => {
  function TesaiotApiUsage(this: TesaiotApiUsageNode, config: TesaiotApiUsageConfig): void {
    RED.nodes.createNode(this, config);

    const gatewayNode = RED.nodes.getNode(config.gateway) as TesaiotApiGatewayNode | null;

    if (!gatewayNode) {
      this.status({ fill: 'red', shape: 'ring', text: 'missing gateway' });
      this.error('TESAIoT API Usage node requires a TESAIoT API Gateway config node.');
      return;
    }

    this.status({ fill: 'yellow', shape: 'ring', text: 'idle' });

    this.on('input', async (msg: any, send: (value: any) => void, done: (err?: any) => void) => {
      const payload = msg?.tesaiot?.apiUsage || {};
      const windowMinutes = clampWindow(Number(payload.window ?? msg.window ?? config.window ?? 60));

      try {
        const client = gatewayNode.getClient();
        const { data } = await client.get('/dashboard/stats', {
          params: { window: windowMinutes }
        });

        this.status({ fill: 'green', shape: 'dot', text: `window ${windowMinutes}m` });
        msg.payload = data;
        msg.metadata = {
          ...(msg.metadata || {}),
          source: 'tesaiot-api-usage',
          windowMinutes,
          fetchedAt: new Date().toISOString()
        };

        send(msg);
        done();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.status({ fill: 'red', shape: 'ring', text: 'error' });
        this.error(message, msg);
        done(message);
      }
    });
  }

  RED.nodes.registerType('tesaiot-api-usage', TesaiotApiUsage as any, {
    category: 'tesaiot',
    color: '#cc1f2f',
    inputs: 1,
    outputs: 1,
    icon: 'bridge.svg',
    paletteLabel: 'TESAIoT API usage',
    defaults: {
      name: { value: '' },
      gateway: { value: '', required: true },
      window: { value: 60 }
    }
  } as any);
};

export = nodeInit;
