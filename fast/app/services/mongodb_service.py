"""Real MongoDB service for Context Relay - Infrastructure Layer"""
import logging
from typing import Optional, List
from datetime import datetime

from app.models.context import ContextPacket, VersionInfo

logger = logging.getLogger(__name__)


class MongoDBService:
    """Real MongoDB service using Beanie ODM for context storage."""

    def __init__(self):
        """Initialize MongoDB service."""
        self.connected = True
        logger.info("✅ MongoDB Service initialized (using Beanie ODM)")

    async def store_context(self, context: ContextPacket) -> bool:
        """
        Store a new context packet in MongoDB.

        Args:
            context: ContextPacket to store

        Returns:
            True if successful
        """
        try:
            await context.insert()
            logger.info(f"Stored context: {context.context_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store context {context.context_id}: {e}")
            raise

    async def get_context(self, context_id: str) -> Optional[ContextPacket]:
        """
        Retrieve a context packet by ID.

        Args:
            context_id: Context ID to retrieve

        Returns:
            ContextPacket if found, None otherwise
        """
        try:
            context = await ContextPacket.find_one(
                ContextPacket.context_id == context_id
            )
            if context:
                logger.debug(f"Retrieved context: {context_id}")
            else:
                logger.warning(f"Context not found: {context_id}")
            return context
        except Exception as e:
            logger.error(f"Failed to retrieve context {context_id}: {e}")
            raise

    async def update_context(self, context: ContextPacket) -> bool:
        """
        Update an existing context packet.

        Args:
            context: ContextPacket to update

        Returns:
            True if successful, False if not found
        """
        try:
            # Find existing context
            existing = await ContextPacket.find_one(
                ContextPacket.context_id == context.context_id
            )

            if not existing:
                logger.warning(f"Context not found for update: {context.context_id}")
                return False

            # Update all fields
            existing.fragments = context.fragments
            existing.decision_trace = context.decision_trace
            existing.metadata = context.metadata
            existing.version = context.version

            await existing.save()
            logger.info(f"Updated context: {context.context_id} (version {context.version})")
            return True

        except Exception as e:
            logger.error(f"Failed to update context {context.context_id}: {e}")
            raise

    async def delete_context(self, context_id: str) -> bool:
        """
        Delete a context packet.

        Args:
            context_id: Context ID to delete

        Returns:
            True if successful, False if not found
        """
        try:
            context = await ContextPacket.find_one(
                ContextPacket.context_id == context_id
            )

            if not context:
                logger.warning(f"Context not found for deletion: {context_id}")
                return False

            await context.delete()
            logger.info(f"Deleted context: {context_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete context {context_id}: {e}")
            raise

    async def store_version(self, version_info: VersionInfo, context: ContextPacket) -> bool:
        """
        Store a version snapshot.

        Args:
            version_info: Version metadata
            context: Context packet to snapshot

        Returns:
            True if successful
        """
        try:
            # Store the full context snapshot
            version_info.snapshot = {
                "context_id": context.context_id,
                "fragments": [f.model_dump(mode="json") for f in context.fragments],
                "decision_trace": context.decision_trace,
                "metadata": context.metadata,
                "version": context.version
            }

            await version_info.insert()
            logger.info(f"Stored version snapshot: {version_info.version_id} for context {context.context_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store version {version_info.version_id}: {e}")
            raise

    async def get_versions(self, context_id: str) -> List[VersionInfo]:
        """
        Get all versions for a context.

        Args:
            context_id: Context ID

        Returns:
            List of VersionInfo objects
        """
        try:
            versions = await VersionInfo.find(
                VersionInfo.context_id == context_id
            ).to_list()

            logger.debug(f"Retrieved {len(versions)} versions for context {context_id}")
            return versions

        except Exception as e:
            logger.error(f"Failed to retrieve versions for context {context_id}: {e}")
            raise

    async def get_version(self, version_id: str) -> Optional[VersionInfo]:
        """
        Get a specific version by ID.

        Args:
            version_id: Version ID

        Returns:
            VersionInfo if found, None otherwise
        """
        try:
            version = await VersionInfo.find_one(
                VersionInfo.version_id == version_id
            )

            if version:
                logger.debug(f"Retrieved version: {version_id}")
            else:
                logger.warning(f"Version not found: {version_id}")

            return version

        except Exception as e:
            logger.error(f"Failed to retrieve version {version_id}: {e}")
            raise

    def set_connection_status(self, connected: bool):
        """
        Set connection status (for testing).

        Args:
            connected: Connection status
        """
        self.connected = connected
        logger.info(f"MongoDB connection status set to: {connected}")


# Singleton instance
_mongodb_service: Optional[MongoDBService] = None


def get_mongodb_service() -> MongoDBService:
    """Get or create singleton MongoDB service instance."""
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
    return _mongodb_service
