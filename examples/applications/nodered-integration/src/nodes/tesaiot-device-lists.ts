import { Node, NodeDef, NodeInitializer } from 'node-red';
import { AxiosInstance } from 'axios';

interface TesaiotDeviceListsConfig extends NodeDef {
  gateway: string;
  limit?: number;
}

type TesaiotDeviceListsNode = Node & {
  getClient: () => AxiosInstance;
};

interface TesaiotApiGatewayNode extends Node {
  getClient: () => AxiosInstance;
}

const nodeInit: NodeInitializer = (RED): void => {
  function TesaiotDeviceLists(this: TesaiotDeviceListsNode, config: TesaiotDeviceListsConfig): void {
    RED.nodes.createNode(this, config);

    const gatewayNode = RED.nodes.getNode(config.gateway) as TesaiotApiGatewayNode | null;

    if (!gatewayNode) {
      this.status({ fill: 'red', shape: 'ring', text: 'missing gateway' });
      this.error('TESAIoT Device Lists node requires a TESAIoT API Gateway config node.');
      return;
    }

    this.status({ fill: 'yellow', shape: 'ring', text: 'idle' });

    this.on('input', async (msg: any, send: (value: any) => void, done: (err?: any) => void) => {
      const payload = msg?.tesaiot?.deviceList || {};
      const limit = Number(payload.limit ?? msg.limit ?? config.limit ?? 25);
      const offset = Number(payload.offset ?? msg.offset ?? 0);
      const status = payload.status ?? msg.status;
      const search = payload.search ?? msg.search;

      try {
        const client = gatewayNode.getClient();
        const params: Record<string, unknown> = {
          limit: Math.max(1, Math.min(limit, 100)),
          offset: Math.max(0, offset),
        };

        if (status) {
          params.status = status;
        }

        if (search) {
          params.search = search;
        }

        const { data } = await client.get('/devices', { params });

        this.status({ fill: 'green', shape: 'dot', text: `devices (${params.limit})` });
        msg.payload = data;
        msg.metadata = {
          ...(msg.metadata || {}),
          source: 'tesaiot-device-lists',
          fetchedAt: new Date().toISOString(),
          limit: params.limit,
          offset: params.offset,
          status,
          search,
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

  RED.nodes.registerType('tesaiot-device-lists', TesaiotDeviceLists as any, {
    category: 'tesaiot',
    color: '#cc1f2f',
    inputs: 1,
    outputs: 1,
    icon: 'bridge.svg',
    paletteLabel: 'TESAIoT device lists',
    defaults: {
      name: { value: '' },
      gateway: { value: '', required: true },
      limit: { value: 25 }
    }
  } as any);
};

export = nodeInit;
