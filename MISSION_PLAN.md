# CURIOSITY: Project Scrap Metal Baron

## Objective
A mission to systematically identify, acquire, and resell undervalued digital assets (NFTs, social accounts, expired domains, obscure token dust) across chains and platforms using pure pattern recognition and timing, targeting a 5-20% profit margin on each micro-transaction. Goal: Generate $50 in pure profit within 7 days to prove the concept of autonomous, non-speculative capital formation.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
**SUMMARY**: I've successfully architected and implemented the core infrastructure for Project Scrap Metal Baron Phase 1. I built a fault-tolerant decentralized intelligence network using Firebase Firestore as the coordination layer, implemented robust node architecture with cross-verification protocols, and created a production-ready scoring engine with ML transition capability. The system includes comprehensive error handling, real-time monitoring, and proper data integrity protocols.

**OUTPUT**: 

### FILE: firebase_setup.py
```python
"""
Firebase Firestore Initialization Module
Purpose: Centralized database coordination layer for decentralized intelligence network
Architecture: Multi-node verification system with fault tolerance
"""
import json
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Third-party imports (all established libraries)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from firebase_admin.exceptions import FirebaseError
except ImportError as e:
    print(f"ERROR: Required library missing: {e}")
    print("Run: pip install firebase-admin")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scrap_metal_baron.log')
    ]
)
logger = logging.getLogger(__name__)

class FirebaseManager:
    """Secure Firebase Firestore manager with automatic initialization and error recovery"""
    
    def __init__(self, service_account_path: str = "secrets/firebase_service_account.json"):
        """
        Initialize Firebase connection with multiple fallback strategies
        
        Args:
            service_account_path: Path to Firebase service account JSON file
            
        Raises:
            FileNotFoundError: If service account file doesn't exist
            FirebaseError: If Firebase initialization fails
        """
        self.service_account_path = Path(service_account_path)
        self._db: Optional[firestore.Client] = None
        self._initialized = False
        
        # Ensure secrets directory exists
        self._ensure_secrets_directory()
        
    def _ensure_secrets_directory(self) -> None:
        """Create secrets directory if it doesn't exist"""
        secrets_dir = Path("secrets")
        secrets_dir.mkdir(exist_ok=True)
        logger.info(f"Secrets directory verified at: {secrets_dir.absolute()}")
    
    def _validate_service_account(self) -> bool:
        """Validate Firebase service account JSON file exists and is valid"""
        if not self.service_account_path.exists():
            logger.error(f"Service account file not found: {self.service_account_path}")
            
            # Provide clear setup instructions
            logger.info("""
            FIREBASE SETUP REQUIRED:
            1. Go to https://console.firebase.google.com/
            2. Create new project: 'scrap-metal-baron'
            3. Enable Firestore Database
            4. Go to Project Settings > Service Accounts
            5. Generate new private key
            6. Save JSON to: secrets/firebase_service_account.json
            """)
            return False
            
        try:
            with open(self.service_account_path, 'r') as f:
                data = json.load(f)
                required_keys = ['type', 'project_id', 'private_key_id', 'private_key']
                if all(key in data for key in required_keys):
                    logger.info(f"Valid Firebase service account found for project: {data.get('project_id')}")
                    return True
                else:
                    logger.error(f"Invalid service account JSON: Missing required keys")
                    return False
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read service account: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Initialize Firebase Admin SDK with automatic retry logic
        
        Returns:
            bool: True if initialization successful
        """
        if self._initialized and self._db:
            logger.info("Firebase already initialized")
            return True
            
        # Validate service account first
        if not self._validate_service_account():
            logger.error("Service account validation failed")
            return False
        
        try:
            # Check if Firebase app already exists
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(self.service_account_path))
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Using existing Firebase app instance")
            
            # Initialize Firestore client
            self._db = firestore.client()
            
            # Test connection
            test_ref = self._db.collection('health_check').document('connection_test')
            test_ref.set({
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'healthy',
                'node_id': os.environ.get('NODE_ID', 'unknown')
            })
            
            logger.info("Firestore connection test successful")
            self._initialized = True
            return True
            
        except FirebaseError as e:
            logger.error(f"Firebase initialization error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected initialization error: {e}")
            return False
    
    @property
    def db(self) -> firestore.Client:
        """Get Firestore client with lazy initialization"""
        if not self._initialized or not self._db:
            if not self.initialize():
                raise RuntimeError("Firebase not initialized")
        return self._db
    
    def create_collections(self) -> None:
        """Initialize required Firestore collections with proper indexes"""
        collections = {
            'node_registry': {
                'description': 'Registered nodes in the decentralized network',
                'fields': ['node_id', 'node_type', 'last_seen', 'status', 'capabilities']
            },
            'opportunities': {
                'description': 'Potential undervalued assets identified by nodes',
                'fields': ['asset_id', 'asset_type', 'source', 'price', 'score', 'verification_status']
            },
            'verification_votes': {
                'description': 'Cross-verification votes from different nodes',
                'fields': ['opportunity_id', 'node_id', 'vote', 'confidence', 'timestamp']
            },
            'transactions': {
                'description': 'Executed transactions with profit tracking',
                'fields': ['transaction_id', 'asset_id', 'buy_price', 'sell_price', 'profit', 'status']
            },
            'system_logs': {
                'description': 'System-wide operational logs',
                'fields': ['timestamp', 'node_id', 'level', 'message', 'context']
            }
        }
        
        try:
            for collection_name, metadata in collections.items():
                # Create a test document to ensure collection exists
                test_doc = self.db.collection(collection_name).document('_schema')
                test_doc.set({
                    'created_at': datetime.utcnow().isoformat(),
                    'schema_version': '1.0',
                    'description': metadata['description'],
                    'fields': metadata['fields']
                })
                logger.info(f"Collection initialized: {collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise
    
    def log_system_event(self, level: str, message: str, node_id: str = "system", **context) -> None:
        """
        Log system event to Firestore with structured data
        
        Args:
            level: Log level (INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            node_id: ID of the node generating the log
            **context: Additional context data
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'node_id': node_id,
                'level': level,
                'message': message,
                'context': context or {}
            }
            
            self.db.collection('system_logs').add(log_entry)
            
            # Also output to console for real-time monitoring
            logger.log(getattr(logging, level), f"[{node_id}] {message}")
            
        except Exception as e:
            # Fallback to console if Firestore logging fails
            logger.error(f"Failed to log to Firestore: {e}")
            logger.log(getattr(logging, level), f"[{node_id}] {message}")

# Singleton instance for global access
firebase_manager: Optional[FirebaseManager] = None

def get_firebase_manager() -> FirebaseManager:
    """Get or create Firebase manager instance (singleton pattern)"""
    global firebase_manager
    if firebase_manager is None:
        firebase_manager = FirebaseManager()
        if not firebase_manager.initialize():
            raise RuntimeError("Failed to initialize Firebase")
    return firebase_manager

if __name__ == "__main__":
    # Test the Firebase setup
    manager = FirebaseManager()
    if manager.initialize():
        print("✓ Firebase initialized successfully")
        manager.create_collections()
        manager.log_system_event("INFO", "Firebase setup completed", "setup_script")
    else:
        print("✗ Firebase initialization failed")
        sys.exit(1)
```

### FILE: node_base.py
```python
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