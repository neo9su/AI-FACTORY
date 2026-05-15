"""
Gatekeeper module for permission policy enforcement.

Blocks dangerous operations based on project permission policies.
"""
from typing import Optional

from backend.models.project import PermissionPolicy


class PermissionDeniedError(Exception):
    """Raised when an operation is blocked by permission policy."""

    pass


class Gatekeeper:
    """Permission policy enforcement manager."""

    # Operations that are always blocked
    BLOCKED_OPERATIONS = {
        "delete_production_data",
        "expose_api_key",
        "modify_payment_config",
        "unlimited_api_calls",
        "deploy_vulnerable_version",
    }

    # Operations that are always allowed
    ALLOWED_OPERATIONS = {
        "create_branch",
        "modify_code",
        "run_tests",
        "fix_bug",
        "deploy_staging",
        "generate_docs",
        "send_notification",
        "create_pr",
    }

    @staticmethod
    def check_permission(
        policy: PermissionPolicy,
        operation: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Check if an operation is allowed under the given permission policy.

        Args:
            policy: PermissionPolicy instance
            operation: Operation name to check
            context: Optional context information (e.g., cost, environment)

        Returns:
            bool: True if operation is allowed

        Raises:
            PermissionDeniedError: If operation is blocked by policy
        """
        # Always block dangerous operations
        if operation in Gatekeeper.BLOCKED_OPERATIONS:
            raise PermissionDeniedError(
                f"Operation '{operation}' is blocked by security policy"
            )

        # Check specific policy rules
        context = context or {}

        # Check cost limits BEFORE allowing safe operations
        if context.get("cost") and policy.max_cost:
            if context["cost"] > policy.max_cost:
                raise PermissionDeniedError(
                    f"Operation cost ${context['cost']} exceeds max allowed ${policy.max_cost}"
                )

        # Always allow safe operations (after cost check)
        if operation in Gatekeeper.ALLOWED_OPERATIONS:
            return True

        if operation == "deploy_to_production":
            if not policy.allow_production_release:
                raise PermissionDeniedError(
                    "Production releases are not allowed by policy"
                )
            return True

        if operation == "auto_deploy":
            if not policy.allow_auto_deploy:
                raise PermissionDeniedError(
                    "Automatic deployments are not allowed by policy"
                )
            return True

        if operation == "external_api_call":
            if not policy.allow_external_api_call:
                raise PermissionDeniedError(
                    "External API calls are not allowed by policy"
                )
            return True

        if operation == "database_migration":
            if not policy.allow_database_migration:
                raise PermissionDeniedError(
                    "Database migrations are not allowed by policy"
                )
            return True

        if operation == "delete_operation":
            if not policy.allow_delete_operation:
                raise PermissionDeniedError(
                    "Delete operations are not allowed by policy"
                )
            return True

        # Check retry limits
        if "retry_count" in context:
            if context["retry_count"] >= policy.max_retry_count:
                raise PermissionDeniedError(
                    f"Retry count {context['retry_count']} exceeds max allowed {policy.max_retry_count}"
                )

        # Default: allow unknown operations but log them
        print(f"Warning: Unknown operation '{operation}' - allowing by default")
        return True

    @staticmethod
    def validate_task_retry(policy: PermissionPolicy, retry_count: int) -> bool:
        """
        Validate if task can be retried based on policy.

        Args:
            policy: PermissionPolicy instance
            retry_count: Current retry count

        Returns:
            bool: True if retry is allowed

        Raises:
            PermissionDeniedError: If retry limit exceeded
        """
        return Gatekeeper.check_permission(
            policy,
            "retry_task",
            context={"retry_count": retry_count},
        )
