/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Download } from 'lucide-react';
import { Device } from '../../types/device.types';

interface QRCodeDialogProps {
  device: Device | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  qrCodeData: string;
}

export function QRCodeDialog({
  device,
  open,
  onOpenChange,
  qrCodeData,
}: QRCodeDialogProps) {
  if (!device) return null;

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = qrCodeData;
    a.download = `${device.name}-qr.png`;
    a.click();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Device QR Code</DialogTitle>
          <DialogDescription>
            Scan this code to provision {device.name}
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex flex-col items-center space-y-4">
          {qrCodeData && (
            <img src={qrCodeData} alt="Device QR Code" className="w-64 h-64" />
          )}
          
          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              Device ID: {device.id}
            </p>
            <p className="text-sm text-muted-foreground">
              Serial: {device.serialNumber}
            </p>
          </div>
          
          <Button onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Download QR Code
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}