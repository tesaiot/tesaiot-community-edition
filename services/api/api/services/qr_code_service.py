# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
QR Code Generation Service for Trust M Device Provisioning
Generates QR codes containing Trust M UID for device identification
"""

import qrcode
import io
import os
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QRCodeService:
    """
    Service for generating QR codes for Trust M device provisioning.

    QR Code Format: TESA:TRUSTM:{trustm_uid}:{device_id}
    Example: TESA:TRUSTM:cdcd000800140035004e00540054004e003400310031003200320041:4797831a-e4cb-41f0-8dbc-e7de2dffe696

    Legacy Format (backward compatible): TESA:TRUSTM:{trustm_uid}
    Example: TESA:TRUSTM:cdcd000800140035004e00540054004e003400310031003200320041
    """

    QR_FORMAT_PREFIX = "TESA:TRUSTM:"
    DEFAULT_BOX_SIZE = 10
    DEFAULT_BORDER = 4

    @staticmethod
    def generate_qr_code(
        trustm_uid: str,
        device_id: Optional[str] = None,
        box_size: int = DEFAULT_BOX_SIZE,
        border: int = DEFAULT_BORDER,
        return_base64: bool = True
    ) -> Dict[str, Any]:
        """
        Generate QR code for Trust M device.

        Args:
            trustm_uid: Trust M UID (54 hex characters)
            device_id: Optional device ID for metadata
            box_size: Size of each QR code box in pixels
            border: Border size in boxes
            return_base64: If True, return base64-encoded PNG; else return PIL Image

        Returns:
            Dictionary with QR code data:
            {
                "qr_content": "TESA:TRUSTM:...",
                "image_base64": "data:image/png;base64,...",  # if return_base64=True
                "image": PIL.Image,  # if return_base64=False
                "device_id": "...",
                "trustm_uid": "...",
                "generated_at": "2025-10-08T..."
            }

        Raises:
            ValueError: If trustm_uid is invalid
        """
        if not trustm_uid or len(trustm_uid) != 54:
            raise ValueError(f"Invalid Trust M UID: must be 54 hex characters, got {len(trustm_uid) if trustm_uid else 0}")

        # Format QR content as URL for mobile camera compatibility
        # Phase 1: Factory registration URL with query parameters
        # Domain-agnostic self-host: default the provisioning host from the
        # install's DOMAIN so onboarding QR codes point at THIS deployment, not
        # a baked-in tesaiot.dev. TESA_PROVISION_DOMAIN (wired by
        # generate-secrets.sh --domain) overrides when set.
        provision_domain = os.getenv(
            "TESA_PROVISION_DOMAIN",
            f"provision.{os.getenv('DOMAIN', 'localhost')}",
        )
        if device_id:
            qr_content = f"https://{provision_domain}/factory?uid={trustm_uid}&device={device_id}"
        else:
            # Fallback if no device_id
            qr_content = f"https://{provision_domain}/factory?uid={trustm_uid}"

        # Create QR code
        qr = qrcode.QRCode(
            version=1,  # Auto-adjust version based on data
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for Trust M
            box_size=box_size,
            border=border,
        )

        qr.add_data(qr_content)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        result = {
            "qr_content": qr_content,
            "device_id": device_id,
            "trustm_uid": trustm_uid,
            "generated_at": datetime.now().isoformat()
        }

        if return_base64:
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_bytes = buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            result["image_base64"] = f"data:image/png;base64,{img_base64}"
        else:
            result["image"] = img

        logger.info(f"Generated QR code for Trust M UID: {trustm_uid[:10]}... (device: {device_id})")
        return result

    @staticmethod
    def parse_qr_content(qr_content: str) -> Optional[Dict[str, str]]:
        """
        Parse QR code content to extract Trust M UID and device_id.

        Args:
            qr_content: QR code content string

        Returns:
            Dictionary with 'trustm_uid' and optional 'device_id' if valid, None otherwise

        Examples:
            >>> QRCodeService.parse_qr_content("TESA:TRUSTM:cdcd0008...:4797831a-e4cb-41f0-8dbc-e7de2dffe696")
            {"trustm_uid": "cdcd0008...", "device_id": "4797831a-e4cb-41f0-8dbc-e7de2dffe696"}

            >>> QRCodeService.parse_qr_content("TESA:TRUSTM:cdcd0008...")
            {"trustm_uid": "cdcd0008..."}
        """
        if not qr_content or not qr_content.startswith(QRCodeService.QR_FORMAT_PREFIX):
            return None

        payload = qr_content[len(QRCodeService.QR_FORMAT_PREFIX):]
        parts = payload.split(':')

        if not parts:
            return None

        trustm_uid = parts[0]

        # Validate UID format
        if len(trustm_uid) != 54 or not all(c in '0123456789abcdefABCDEF' for c in trustm_uid):
            return None

        result = {"trustm_uid": trustm_uid}

        # Extract device_id if present (new format)
        if len(parts) > 1 and parts[1]:
            result["device_id"] = parts[1]

        return result

    @staticmethod
    def generate_bulk_qr_codes(
        devices: List[Dict[str, Any]],
        box_size: int = DEFAULT_BOX_SIZE,
        border: int = DEFAULT_BORDER
    ) -> List[Dict[str, Any]]:
        """
        Generate QR codes for multiple devices.

        Args:
            devices: List of device dictionaries with 'trustm_uid' and 'device_id'
            box_size: QR code box size
            border: QR code border size

        Returns:
            List of QR code result dictionaries

        Example devices input:
        [
            {"device_id": "PSoC-E84-001", "trustm_uid": "cdcd0008..."},
            {"device_id": "PSoC-E84-002", "trustm_uid": "cdcd0009..."}
        ]
        """
        results = []
        errors = []

        for device in devices:
            trustm_uid = device.get('trustm_uid')
            device_id = device.get('device_id')

            if not trustm_uid:
                errors.append(f"Device {device_id}: Missing Trust M UID")
                continue

            try:
                qr_result = QRCodeService.generate_qr_code(
                    trustm_uid=trustm_uid,
                    device_id=device_id,
                    box_size=box_size,
                    border=border,
                    return_base64=True
                )
                results.append(qr_result)
            except ValueError as e:
                errors.append(f"Device {device_id}: {str(e)}")
                logger.warning(f"Failed to generate QR for device {device_id}: {e}")

        if errors:
            logger.warning(f"Bulk QR generation completed with {len(errors)} errors")

        return results

    @staticmethod
    def generate_qr_code_svg(
        trustm_uid: str,
        device_id: Optional[str] = None
    ) -> str:
        """
        Generate QR code as SVG string for scalable display.

        Args:
            trustm_uid: Trust M UID
            device_id: Optional device ID

        Returns:
            SVG string

        Raises:
            ValueError: If trustm_uid is invalid
        """
        if not trustm_uid or len(trustm_uid) != 54:
            raise ValueError(f"Invalid Trust M UID: must be 54 hex characters")

        import qrcode.image.svg

        # Format QR content with both trustm_uid and device_id
        if device_id:
            qr_content = f"{QRCodeService.QR_FORMAT_PREFIX}{trustm_uid}:{device_id}"
        else:
            # Legacy format for backward compatibility
            qr_content = f"{QRCodeService.QR_FORMAT_PREFIX}{trustm_uid}"

        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            image_factory=factory
        )

        qr.add_data(qr_content)
        qr.make(fit=True)

        img = qr.make_image()

        # Convert to SVG string
        buffer = io.BytesIO()
        img.save(buffer)
        svg_content = buffer.getvalue().decode('utf-8')

        logger.info(f"Generated SVG QR code for Trust M UID: {trustm_uid[:10]}... (device: {device_id})")
        return svg_content


# Singleton instance
qr_code_service = QRCodeService()
