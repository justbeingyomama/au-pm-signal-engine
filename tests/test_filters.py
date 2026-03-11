"""
tests/test_filters.py — Unit tests for role include/exclude keyword filtering.
"""
from pipeline import passes_role_filter


# ── Include cases ─────────────────────────────────────────────────────────────

def test_product_manager_included():
    assert passes_role_filter("Product Manager") is True


def test_senior_product_manager_included():
    assert passes_role_filter("Senior Product Manager") is True


def test_head_of_product_included():
    assert passes_role_filter("Head of Product") is True


def test_product_lead_included():
    assert passes_role_filter("Product Lead") is True


def test_group_product_manager_included():
    assert passes_role_filter("Group Product Manager") is True


def test_principal_pm_included():
    assert passes_role_filter("Principal Product Manager") is True


def test_technical_pm_included():
    assert passes_role_filter("Technical Product Manager") is True


# ── Exclude cases ─────────────────────────────────────────────────────────────

def test_project_manager_excluded():
    assert passes_role_filter("Project Manager", "We need a project manager for delivery") is False


def test_program_manager_excluded():
    assert passes_role_filter("Program Manager") is False


def test_delivery_manager_excluded():
    assert passes_role_filter("Delivery Manager") is False


def test_account_manager_excluded():
    assert passes_role_filter("Account Manager") is False


def test_product_marketing_manager_excluded():
    assert passes_role_filter("Product Marketing Manager") is False


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_irrelevant_role_excluded():
    assert passes_role_filter("Software Engineer") is False


def test_case_insensitive_include():
    assert passes_role_filter("PRODUCT MANAGER") is True


def test_case_insensitive_exclude():
    assert passes_role_filter("Product Marketing Manager") is False


def test_pm_in_body_text_included():
    assert passes_role_filter("Open Roles", "We are hiring a Product Manager in Sydney") is True
