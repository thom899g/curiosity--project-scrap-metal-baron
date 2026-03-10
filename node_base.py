"""
Base Node Class for Decentralized Intelligence Network
Purpose: Abstract base class for all node types with common functionality
Architecture: Template pattern with mandatory method implementations
"""
import abc
import uuid
import asyncio
import time
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field
from enum import Enum

# Import Firebase manager
try:
    from firebase_setup import get_firebase_manager, FirebaseManager
except ImportError:
    print("ERROR: firebase_setup.py not found. Run firebase_setup.py first.")
    raise

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Types of nodes in the decentralized network"""
    NFT = "nft"
    DOMAIN = "domain"
    SOCIAL = "social"
    BLOCKCHAIN = "blockchain"
    SCORING = "scoring"
    EXECUTION = "execution"

class NodeStatus(Enum):
    """Node operational status"""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

@dataclass
class Opportunity:
    """Standardized opportunity data structure"""
    asset_id: str
    asset_type: str
    source: str
    current_price: float
    floor_price: Optional[float] = None
    volume_24h: Optional[float] = None
    supply: Optional[int] = None
    days_since_last_sale: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dictionary"""
        return {
            'asset_id': self.asset_id,
            'asset_type': self.asset_type,
            'source': self.source,
            'current_price': self.current_price,
            'floor_price': self.floor_price,
            'volume_24h': self.volume_24h,
            'supply': self.supply,
            'days_since_last_sale': self.days_since_last_sale,
            'metadata': self.metadata,
            'discovered_at': self.discovered_at.isoformat(),
            'node_discovery_time': datetime.utcnow().isoformat()
        }

class BaseNode(abc.ABC):
    """
    Abstract base class for all network nodes
    
    Implements:
    - Node registration with Firebase
    - Heartbeat monitoring
    - Error handling and recovery
    - Rate limiting and backoff
    - Data validation
    """
    
    def __init__(self, node_type: NodeType, node_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize node with type and configuration
        
        Args:
            node_type: Type of node (NFT, DOMAIN, etc.)
            node_name: Human-readable node name
            config: Node-specific configuration
        """
        self.node_type = node_type
        self.node_name = node_name
        self.config = config or {}
        self.node_id = f"{node_type.value}_{uuid.uuid4().hex[:8]}"
        
        # Initialize Firebase manager
        try:
            self.firebase = get_firebase_manager()
            self.db = self.firebase.db
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
        
        # Operational state
        self.status = NodeStatus.STARTING
        self.last_heartbeat = None
        self.error_count = 0
        self.max_errors = self.config.get('max_errors', 10)
        self.retry_delay = self.config.get('retry_delay', 5)
        
        # Rate limiting
        self.request_count = 0
        self.request_window_start = time.time()
        self.max_requests_per_minute = self.config.get('max_requests_per_minute', 30)
        
        logger.info(f"Initializing {node_type.value} node: {node_name} (ID: {self.node_id})")
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded, implement exponential backoff"""
        current_time = time.time()
        
        # Reset window if more than 60 seconds have passed
        if current_time - self.request_window_start > 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        if self.request_count >= self.max_requests_per_minute:
            wait_time = min(2 ** self.error_count, 300)  # Exponential backoff, max 5 minutes
            logger.warning(f"Rate limit exceeded. Waiting {wait_time}s before retry.")
            time.sleep(wait_time)
            self.request_count = 0
            self.request_window_start = time.time()
            return False
        
        self.request_count += 1
        return True
    
    def _handle_api_error(self, error: Exception, context: str = "API call") -> None:
        """
        Handle API errors with exponential backoff and logging
        
        Args:
            error: Exception that occurred
            context: Context of the error for logging
        """
        self.error_count += 1
        
        # Log error to Firestore
        self.firebase.log_system_event(
            "ERROR",
            f"{context} failed: {str(error)}",
            self.node_id,
            error_type=type(error).__name__,
            error_count=self.error_count,
            retry_delay=self.retry_delay
        )
        
        if self.error_count > self.max_errors:
            self.status = NodeStatus.DEGRADED
            logger.error(f"Max errors ({self.max_errors}) exceeded. Node status: {self.status}")
            return
        
        # Exponential backoff
        backoff = self.retry_delay * (2 ** (self.error_count - 1))
        backoff = min(backoff, 300)  # Cap at 5 minutes
        logger.warning(f"API error. Backing off for {backoff}s")
        time.sleep(backoff)
    
    async def register_node(self) -> bool:
        """
        Register node with the decentralized network via Firebase
        
        Returns:
            bool: True if registration successful
        """
        try:
            node_data = {
                'node_id': self.node_id,
                'node_type': self.node_type.value,
                'node_name': self.node_name,
                'status': self.status.value,
                'registered_at': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat(),
                'capabilities': self.config.get('capabilities', []),
                'config_hash': str(hash(frozenset(self.config.items()))),
                'ip_address': self.config.get('ip_address', 'unknown')
            }
            
            # Update or create node registration
            node_ref = self.db.collection('node_registry').document(self.node_id)
            node_ref.set(node_data, merge=True)
            
            logger.info(f"Node registered: {self.node_id}")
            self.status = NodeStatus.HEALTHY
            return True
            
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            self.status = NodeStatus.DEGRADED
            return False
    
    async def send_heartbeat(self) -> None:
        """Send heartbeat to Firebase to indicate node is alive"""
        try:
            heartbeat_data = {
                'last_seen': datetime.utcnow().isoformat(),
                'status': self.status.value,
                'error_count': self.error_count,
                'request_count': self.request_count
            }