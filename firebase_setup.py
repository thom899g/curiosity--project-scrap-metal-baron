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