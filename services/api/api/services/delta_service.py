# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Delta Update Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.

"""

import os
import json
import hashlib
import tempfile
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import lz4.frame
import zstandard as zstd

from ..core.exceptions import (
    APIException,
    ValidationError
)

logger = logging.getLogger(__name__)


class DeltaAlgorithm(Enum):
    """Supported delta algorithms"""
    BSDIFF = "bsdiff"
    XDELTA = "xdelta"
    ZSTD_DELTA = "zstd_delta"
    LZ4_DELTA = "lz4_delta"
    ROLLING_HASH = "rolling_hash"


class CompressionType(Enum):
    """Compression types for delta packages"""
    NONE = "none"
    LZ4 = "lz4"
    ZSTD = "zstd"
    GZIP = "gzip"


@dataclass
class DeltaPackage:
    """Delta package metadata"""
    id: Optional[str] = None
    from_version: str = ""
    to_version: str = ""
    device_type: str = ""
    algorithm: DeltaAlgorithm = DeltaAlgorithm.BSDIFF
    compression: CompressionType = CompressionType.ZSTD
    original_size: int = 0
    delta_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    delta_hash: str = ""
    verification_hash: str = ""
    created_at: Optional[datetime] = None
    storage_path: str = ""
    metadata: Dict = None


@dataclass
class DeltaChain:
    """Chain of delta updates"""
    from_version: str
    to_version: str
    device_type: str
    packages: List[DeltaPackage]
    total_size: int
    total_compressed_size: int
    is_optimal: bool = False


class DeltaService:
    """Service for generating and managing delta updates"""
    
    def __init__(self, db, storage_client, config: Optional[Dict] = None):
        """
        Initialize Delta Service
        
        Args:
            db: MongoDB database instance
            storage_client: Object storage client
            config: Service configuration
        """
        self.db = db
        self.storage_client = storage_client
        self.config = config or {}
        
        # Delta storage configuration
        self.delta_storage_path = self.config.get(
            'delta_storage_path',
            '/app/storage/deltas'
        )
        os.makedirs(self.delta_storage_path, exist_ok=True)
        
        # Algorithm preferences by device type
        self.algorithm_preferences = self.config.get('algorithm_preferences', {
            'esp32': DeltaAlgorithm.LZ4_DELTA,
            'esp8266': DeltaAlgorithm.LZ4_DELTA,
            'raspberry-pi': DeltaAlgorithm.ZSTD_DELTA,
            'arduino': DeltaAlgorithm.BSDIFF,
            'default': DeltaAlgorithm.BSDIFF
        })
        
        # Compression preferences
        self.compression_preferences = self.config.get('compression_preferences', {
            'esp32': CompressionType.LZ4,
            'esp8266': CompressionType.LZ4,
            'raspberry-pi': CompressionType.ZSTD,
            'arduino': CompressionType.LZ4,
            'default': CompressionType.ZSTD
        })
        
        # Initialize compression contexts
        self.zstd_compressor = zstd.ZstdCompressor(level=6)
        self.zstd_decompressor = zstd.ZstdDecompressor()
        
        logger.info("Delta Service initialized")
        
    async def generate_delta(
        self,
        from_firmware_id: str,
        to_firmware_id: str,
        algorithm: Optional[DeltaAlgorithm] = None,
        compression: Optional[CompressionType] = None
    ) -> DeltaPackage:
        """
        Generate delta package between two firmware versions
        
        Args:
            from_firmware_id: Source firmware ID
            to_firmware_id: Target firmware ID
            algorithm: Delta algorithm to use
            compression: Compression type to use
            
        Returns:
            DeltaPackage object
        """
        try:
            # Get firmware metadata
            from_firmware = await self._get_firmware(from_firmware_id)
            to_firmware = await self._get_firmware(to_firmware_id)
            
            # Validate compatibility
            if from_firmware['device_type'] != to_firmware['device_type']:
                raise ValidationError("Firmware device types don't match")
                
            # Check if delta already exists
            existing_delta = await self._get_existing_delta(
                from_firmware['version'],
                to_firmware['version'],
                from_firmware['device_type']
            )
            
            if existing_delta:
                logger.info(f"Delta already exists: {from_firmware['version']} -> {to_firmware['version']}")
                return DeltaPackage(**existing_delta)
                
            # Determine optimal algorithm and compression
            device_type = from_firmware['device_type']
            if not algorithm:
                algorithm = self.algorithm_preferences.get(
                    device_type,
                    self.algorithm_preferences['default']
                )
            if not compression:
                compression = self.compression_preferences.get(
                    device_type,
                    self.compression_preferences['default']
                )
                
            # Download firmware files
            from_firmware_data = await self._download_firmware(from_firmware_id)
            to_firmware_data = await self._download_firmware(to_firmware_id)
            
            # Generate delta
            delta_data = await self._generate_delta_data(
                from_firmware_data,
                to_firmware_data,
                algorithm
            )
            
            # Compress delta
            compressed_data, compression_ratio = await self._compress_delta(
                delta_data,
                compression
            )
            
            # Calculate hashes
            delta_hash = hashlib.sha256(delta_data).hexdigest()
            verification_hash = hashlib.sha256(
                from_firmware_data + to_firmware_data
            ).hexdigest()
            
            # Create delta package
            delta_package = DeltaPackage(
                from_version=from_firmware['version'],
                to_version=to_firmware['version'],
                device_type=device_type,
                algorithm=algorithm,
                compression=compression,
                original_size=len(to_firmware_data),
                delta_size=len(delta_data),
                compressed_size=len(compressed_data),
                compression_ratio=compression_ratio,
                delta_hash=delta_hash,
                verification_hash=verification_hash,
                created_at=datetime.utcnow(),
                metadata={
                    'from_firmware_id': from_firmware_id,
                    'to_firmware_id': to_firmware_id,
                    'from_hash': from_firmware['file_hash'],
                    'to_hash': to_firmware['file_hash']
                }
            )
            
            # Store delta package
            storage_path = await self._store_delta_package(
                compressed_data,
                delta_package
            )
            delta_package.storage_path = storage_path
            
            # Save to database
            delta_doc = asdict(delta_package)
            result = await self.db.delta_packages.insert_one(delta_doc)
            delta_package.id = str(result.inserted_id)
            
            logger.info(
                f"Generated delta {from_firmware['version']} -> {to_firmware['version']}: "
                f"{delta_package.delta_size} bytes ({compression_ratio:.1%} compression)"
            )
            
            return delta_package
            
        except Exception as e:
            logger.error(f"Error generating delta: {e}")
            raise APIException("Failed to generate delta package")
            
    async def find_optimal_delta_chain(
        self,
        from_version: str,
        to_version: str,
        device_type: str,
        max_chain_length: int = 5
    ) -> Optional[DeltaChain]:
        """
        Find optimal chain of delta updates
        
        Args:
            from_version: Starting version
            to_version: Target version
            device_type: Device type
            max_chain_length: Maximum chain length
            
        Returns:
            DeltaChain object or None if no path found
        """
        try:
            # Get all available deltas for device type
            deltas = await self.db.delta_packages.find({
                'device_type': device_type
            }).to_list(None)
            
            # Build delta graph
            delta_graph = self._build_delta_graph(deltas)
            
            # Find shortest path
            paths = self._find_delta_paths(
                delta_graph,
                from_version,
                to_version,
                max_chain_length
            )
            
            if not paths:
                return None
                
            # Select optimal path (shortest total size)
            optimal_path = min(paths, key=lambda p: p.total_compressed_size)
            
            return optimal_path
            
        except Exception as e:
            logger.error(f"Error finding delta chain: {e}")
            return None
            
    async def apply_delta(
        self,
        original_data: bytes,
        delta_package_id: str
    ) -> bytes:
        """
        Apply delta package to original firmware
        
        Args:
            original_data: Original firmware data
            delta_package_id: Delta package ID
            
        Returns:
            Updated firmware data
        """
        try:
            # Get delta package
            delta_package = await self._get_delta_package(delta_package_id)
            
            # Download delta data
            delta_data = await self._download_delta_package(delta_package)
            
            # Decompress if needed
            if delta_package['compression'] != CompressionType.NONE.value:
                delta_data = await self._decompress_delta(
                    delta_data,
                    CompressionType(delta_package['compression'])
                )
                
            # Apply delta based on algorithm
            algorithm = DeltaAlgorithm(delta_package['algorithm'])
            result_data = await self._apply_delta_data(
                original_data,
                delta_data,
                algorithm
            )
            
            # Verify result
            result_hash = hashlib.sha256(result_data).hexdigest()
            expected_hash = delta_package['metadata']['to_hash']
            
            if result_hash != expected_hash:
                raise ValidationError("Delta application verification failed")
                
            return result_data
            
        except Exception as e:
            logger.error(f"Error applying delta: {e}")
            raise APIException("Failed to apply delta package")
            
    async def _generate_delta_data(
        self,
        from_data: bytes,
        to_data: bytes,
        algorithm: DeltaAlgorithm
    ) -> bytes:
        """Generate delta data using specified algorithm"""
        
        if algorithm == DeltaAlgorithm.BSDIFF:
            return await self._generate_bsdiff_delta(from_data, to_data)
        elif algorithm == DeltaAlgorithm.XDELTA:
            return await self._generate_xdelta_delta(from_data, to_data)
        elif algorithm == DeltaAlgorithm.ZSTD_DELTA:
            return await self._generate_zstd_delta(from_data, to_data)
        elif algorithm == DeltaAlgorithm.LZ4_DELTA:
            return await self._generate_lz4_delta(from_data, to_data)
        elif algorithm == DeltaAlgorithm.ROLLING_HASH:
            return await self._generate_rolling_hash_delta(from_data, to_data)
        else:
            raise ValueError(f"Unsupported delta algorithm: {algorithm}")
            
    async def _generate_bsdiff_delta(
        self,
        from_data: bytes,
        to_data: bytes
    ) -> bytes:
        """Generate delta using bsdiff algorithm"""
        try:
            with tempfile.NamedTemporaryFile() as from_file, \
                 tempfile.NamedTemporaryFile() as to_file, \
                 tempfile.NamedTemporaryFile() as delta_file:
                
                # Write input files
                from_file.write(from_data)
                from_file.flush()
                to_file.write(to_data)
                to_file.flush()
                
                # Run bsdiff
                result = await asyncio.create_subprocess_exec(
                    'bsdiff',
                    from_file.name,
                    to_file.name,
                    delta_file.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    raise Exception(f"bsdiff failed: {stderr.decode()}")
                    
                # Read delta
                delta_file.seek(0)
                return delta_file.read()
                
        except Exception as e:
            logger.error(f"Error generating bsdiff delta: {e}")
            raise
            
    async def _generate_xdelta_delta(
        self,
        from_data: bytes,
        to_data: bytes
    ) -> bytes:
        """Generate delta using xdelta algorithm"""
        try:
            with tempfile.NamedTemporaryFile() as from_file, \
                 tempfile.NamedTemporaryFile() as to_file, \
                 tempfile.NamedTemporaryFile() as delta_file:
                
                # Write input files
                from_file.write(from_data)
                from_file.flush()
                to_file.write(to_data)
                to_file.flush()
                
                # Run xdelta
                result = await asyncio.create_subprocess_exec(
                    'xdelta3',
                    '-e',
                    '-s', from_file.name,
                    to_file.name,
                    delta_file.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    raise Exception(f"xdelta3 failed: {stderr.decode()}")
                    
                # Read delta
                delta_file.seek(0)
                return delta_file.read()
                
        except Exception as e:
            logger.error(f"Error generating xdelta delta: {e}")
            raise
            
    async def _generate_zstd_delta(
        self,
        from_data: bytes,
        to_data: bytes
    ) -> bytes:
        """Generate delta using Zstd dictionary compression"""
        try:
            # Use from_data as dictionary for compressing to_data
            dictionary = zstd.train_dictionary(
                dict_size=min(len(from_data), 64 * 1024),
                samples=[from_data]
            )
            
            compressor = zstd.ZstdCompressor(dict_data=dictionary)
            compressed = compressor.compress(to_data)
            
            # Create delta package with dictionary
            delta_data = {
                'type': 'zstd_delta',
                'dictionary': dictionary.as_bytes(),
                'compressed_data': compressed
            }
            
            return json.dumps(delta_data, default=lambda x: x.hex() if isinstance(x, bytes) else x).encode()
            
        except Exception as e:
            logger.error(f"Error generating zstd delta: {e}")
            raise
            
    async def _generate_lz4_delta(
        self,
        from_data: bytes,
        to_data: bytes
    ) -> bytes:
        """Generate delta using LZ4 with custom dictionary"""
        try:
            # Simple approach: find common blocks and encode differences
            block_size = 4096
            delta_ops = []
            
            from_blocks = [from_data[i:i+block_size] for i in range(0, len(from_data), block_size)]
            to_blocks = [to_data[i:i+block_size] for i in range(0, len(to_data), block_size)]
            
            # Build block hash map from source
            from_block_map = {hashlib.md5(block).hexdigest(): i for i, block in enumerate(from_blocks)}
            
            # Generate delta operations
            for i, to_block in enumerate(to_blocks):
                block_hash = hashlib.md5(to_block).hexdigest()
                
                if block_hash in from_block_map:
                    # Block exists in source
                    delta_ops.append({
                        'type': 'copy',
                        'from_block': from_block_map[block_hash],
                        'to_block': i
                    })
                else:
                    # New block
                    compressed_block = lz4.frame.compress(to_block)
                    delta_ops.append({
                        'type': 'new',
                        'to_block': i,
                        'data': compressed_block.hex()
                    })
                    
            delta_data = {
                'type': 'lz4_delta',
                'block_size': block_size,
                'operations': delta_ops
            }
            
            return json.dumps(delta_data).encode()
            
        except Exception as e:
            logger.error(f"Error generating lz4 delta: {e}")
            raise
            
    async def _generate_rolling_hash_delta(
        self,
        from_data: bytes,
        to_data: bytes
    ) -> bytes:
        """Generate delta using rolling hash algorithm"""
        try:
            # Simplified rolling hash implementation
            window_size = 64
            hash_map = {}
            
            # Build hash map of source
            for i in range(len(from_data) - window_size + 1):
                window = from_data[i:i+window_size]
                window_hash = hash(window)
                hash_map[window_hash] = i
                
            # Generate delta operations
            delta_ops = []
            to_pos = 0
            
            while to_pos < len(to_data):
                if to_pos + window_size <= len(to_data):
                    window = to_data[to_pos:to_pos+window_size]
                    window_hash = hash(window)
                    
                    if window_hash in hash_map:
                        # Found match
                        delta_ops.append({
                            'type': 'copy',
                            'from_pos': hash_map[window_hash],
                            'length': window_size
                        })
                        to_pos += window_size
                    else:
                        # No match, add literal byte
                        delta_ops.append({
                            'type': 'literal',
                            'data': to_data[to_pos]
                        })
                        to_pos += 1
                else:
                    # Remaining bytes
                    delta_ops.append({
                        'type': 'literal',
                        'data': to_data[to_pos]
                    })
                    to_pos += 1
                    
            delta_data = {
                'type': 'rolling_hash_delta',
                'window_size': window_size,
                'operations': delta_ops
            }
            
            return json.dumps(delta_data).encode()
            
        except Exception as e:
            logger.error(f"Error generating rolling hash delta: {e}")
            raise
            
    async def _compress_delta(
        self,
        delta_data: bytes,
        compression: CompressionType
    ) -> Tuple[bytes, float]:
        """Compress delta data"""
        
        if compression == CompressionType.NONE:
            return delta_data, 1.0
        elif compression == CompressionType.LZ4:
            compressed = lz4.frame.compress(delta_data)
            ratio = len(compressed) / len(delta_data)
            return compressed, ratio
        elif compression == CompressionType.ZSTD:
            compressed = self.zstd_compressor.compress(delta_data)
            ratio = len(compressed) / len(delta_data)
            return compressed, ratio
        elif compression == CompressionType.GZIP:
            import gzip
            compressed = gzip.compress(delta_data)
            ratio = len(compressed) / len(delta_data)
            return compressed, ratio
        else:
            raise ValueError(f"Unsupported compression type: {compression}")
            
    async def _store_delta_package(
        self,
        delta_data: bytes,
        delta_package: DeltaPackage
    ) -> str:
        """Store delta package to storage"""
        try:
            # Generate storage path
            filename = f"delta_{delta_package.device_type}_{delta_package.from_version}_{delta_package.to_version}_{delta_package.delta_hash[:8]}.bin"
            storage_path = os.path.join(self.delta_storage_path, filename)
            
            # Write to local storage
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            with open(storage_path, 'wb') as f:
                f.write(delta_data)
                
            # Upload to object storage if configured
            if self.storage_client:
                try:
                    object_key = f"deltas/{filename}"
                    await self.storage_client.put_object(
                        object_key,
                        delta_data,
                        content_type='application/octet-stream'
                    )
                    return object_key
                except Exception as e:
                    logger.warning(f"Failed to upload to object storage: {e}")
                    
            return storage_path
            
        except Exception as e:
            logger.error(f"Error storing delta package: {e}")
            raise
            
    def _build_delta_graph(self, deltas: List[Dict]) -> Dict[str, List[Dict]]:
        """Build graph of available delta packages"""
        graph = {}
        
        for delta in deltas:
            from_version = delta['from_version']
            if from_version not in graph:
                graph[from_version] = []
            graph[from_version].append(delta)
            
        return graph
        
    def _find_delta_paths(
        self,
        graph: Dict[str, List[Dict]],
        from_version: str,
        to_version: str,
        max_depth: int
    ) -> List[DeltaChain]:
        """Find all possible delta paths using BFS"""
        from collections import deque
        
        paths = []
        queue = deque([(from_version, [])])
        
        while queue:
            current_version, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
                
            if current_version == to_version:
                # Found target
                if path:
                    total_size = sum(d['delta_size'] for d in path)
                    total_compressed = sum(d['compressed_size'] for d in path)
                    
                    chain = DeltaChain(
                        from_version=from_version,
                        to_version=to_version,
                        device_type=path[0]['device_type'],
                        packages=[DeltaPackage(**d) for d in path],
                        total_size=total_size,
                        total_compressed_size=total_compressed
                    )
                    paths.append(chain)
                continue
                
            if current_version in graph:
                for delta in graph[current_version]:
                    new_path = path + [delta]
                    queue.append((delta['to_version'], new_path))
                    
        return paths


# Factory function
def create_delta_service(db, storage_client, config=None):
    """Create a Delta Service instance"""
    return DeltaService(db, storage_client, config)