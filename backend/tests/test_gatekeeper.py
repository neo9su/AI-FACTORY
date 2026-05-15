"""Tests for gatekeeper permission logic."""
from uuid import uuid4

import pytest

from backend.core.gatekeeper import Gatekeeper, PermissionDeniedError
from backend.models.project import PermissionPolicy


def test_gatekeeper_allow_safe_operation():
    """Test gatekeeper allows safe operations."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
        max_cost=100.0,
    )

    result = Gatekeeper.check_permission(policy, "create_branch")
    assert result is True


def test_gatekeeper_block_deployment_without_permission():
    """Test gatekeeper blocks deployment without permission."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.check_permission(policy, "auto_deploy")


def test_gatekeeper_allow_deployment_with_permission():
    """Test gatekeeper allows deployment with permission."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=False,
        allow_delete_operation=False,
    )

    result = Gatekeeper.check_permission(policy, "auto_deploy")
    assert result is True


def test_gatekeeper_block_production_release():
    """Test gatekeeper blocks production release."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=False,
        allow_delete_operation=False,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.check_permission(policy, "deploy_to_production")


def test_gatekeeper_allow_production_with_permission():
    """Test gatekeeper allows production with permission."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=True,
        allow_delete_operation=False,
    )

    result = Gatekeeper.check_permission(policy, "deploy_to_production")
    assert result is True


def test_gatekeeper_block_delete_without_permission():
    """Test gatekeeper blocks delete operations."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.check_permission(policy, "delete_operation")


def test_gatekeeper_allow_delete_with_permission():
    """Test gatekeeper allows delete with permission."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=True,
    )

    result = Gatekeeper.check_permission(policy, "delete_operation")
    assert result is True


def test_gatekeeper_block_over_budget():
    """Test gatekeeper blocks operations over budget."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=False,
        allow_delete_operation=False,
        max_cost=10.0,
    )

    with pytest.raises(PermissionDeniedError) as exc_info:
        Gatekeeper.check_permission(policy, "create_branch", context={"cost": 15.0})

    assert "exceeds max allowed" in str(exc_info.value)


def test_gatekeeper_allow_within_budget():
    """Test gatekeeper allows operations within budget."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=False,
        allow_delete_operation=False,
        max_cost=100.0,
    )

    result = Gatekeeper.check_permission(policy, "create_branch", context={"cost": 50.0})
    assert result is True


def test_gatekeeper_allow_api_call():
    """Test gatekeeper allows external API calls."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
        allow_external_api_call=True,
    )

    result = Gatekeeper.check_permission(policy, "external_api_call")
    assert result is True


def test_gatekeeper_block_api_call():
    """Test gatekeeper blocks external API calls."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
        allow_external_api_call=False,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.check_permission(policy, "external_api_call")


def test_gatekeeper_block_dangerous_operation():
    """Test gatekeeper always blocks dangerous operations."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=True,
        allow_production_release=True,
        allow_delete_operation=True,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.check_permission(policy, "delete_production_data")


def test_gatekeeper_validate_task_retry():
    """Test gatekeeper validates task retry limits."""
    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=str(uuid4()),
        allow_auto_deploy=False,
        allow_production_release=False,
        allow_delete_operation=False,
        max_retry_count=3,
    )

    with pytest.raises(PermissionDeniedError):
        Gatekeeper.validate_task_retry(policy, retry_count=5)
