import { Node, NodeDef, NodeInitializer } from 'node-red';
import { AxiosInstance } from 'axios';

interface TesaiotDeviceProfileConfig extends NodeDef {
  gateway: string;
}

type TesaiotDeviceProfileNode = Node & {
  getClient: () => AxiosInstance;
};

interface TesaiotApiGatewayNode extends Node {
  getClient: () => AxiosInstance;
}

const nodeInit: NodeInitializer = (RED): void => {
  function TesaiotDeviceProfile(this: TesaiotDeviceProfileNode, config: TesaiotDeviceProfileConfig): void {
    RED.nodes.createNode(this, config);

    const gatewayNode = RED.nodes.getNode(config.gateway) as TesaiotApiGatewayNode | null;

    if (!gatewayNode) {
      this.status({ fill: 'red', shape: 'ring', text: 'missing gateway' });
      this.error('TESAIoT Device Profile node requires a TESAIoT API Gateway config node.');
      return;
    }

    this.status({ fill: 'yellow', shape: 'ring', text: 'idle' });

    this.on('input', async (msg: any, send: (value: any) => void, done: (err?: any) => void) => {
      const payload = msg?.tesaiot?.deviceProfile || {};
      const deviceId = payload.deviceId || msg.deviceId || msg.tesaiot?.deviceId;

      if (!deviceId) {
        const message = 'TESAIoT device profile node requires `deviceId` (msg.tesaiot.deviceProfile.deviceId or msg.deviceId).';
        this.status({ fill: 'red', shape: 'ring', text: 'missing deviceId' });
        this.error(message, msg);
        done(message);
        return;
      }

      try {
        const client = gatewayNode.getClient();
        const { data } = await client.get(`/devices/${deviceId}`);

        this.status({ fill: 'green', shape: 'dot', text: 'profile ok' });
        msg.payload = data;
        msg.metadata = {
          ...(msg.metadata || {}),
          source: 'tesaiot-device-profile',
          deviceId,
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

  RED.nodes.registerType('tesaiot-device-profile', TesaiotDeviceProfile as any, {
    category: 'tesaiot',
    color: '#cc1f2f',
    inputs: 1,
    outputs: 1,
    icon: 'bridge.svg',
    paletteLabel: "TESAIoT device profile",
    defaults: {
      name: { value: '' },
      gateway: { value: '', required: true }
    }
  } as any);
};

export = nodeInit;
