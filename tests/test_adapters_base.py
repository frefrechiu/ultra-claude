"""Tests for the Adapter Protocol and _SubprocessAdapterMixin.

Covers:
- ADP-01: Adapter is a typing.Protocol with runtime_checkable structural typing.
  isinstance(obj, Adapter) is True for any class declaring `name: str` and an
  `invoke(prompt, timeout) -> str` method, regardless of inheritance.
- ADP-02 (partial): _SubprocessAdapterMixin declares the cli_name and
  auth_error_markers class-level annotations that subclasses must populate.
  Concrete behaviour of _run_subprocess is exercised in test_adapter_claude.py
  (we don't double-test here -- ClaudeAdapter is the proof-of-concept consumer).

Verification logic intentionally avoids real subprocess calls; this file is
about types and structural conformance.
"""

from __future__ import annotations

from ultra_claude.adapters import Adapter, ClaudeAdapter, _SubprocessAdapterMixin

# ---------------------------------------------------------------------------
# Adapter Protocol structural typing (ADP-01)
# ---------------------------------------------------------------------------


def test_adapter_is_runtime_checkable_protocol() -> None:
    """Adapter must declare itself as a runtime_checkable Protocol so
    isinstance(obj, Adapter) works without forcing inheritance."""

    # Protocols decorated with @runtime_checkable expose this dunder.
    assert getattr(Adapter, "_is_runtime_protocol", False), (
        "Adapter must be decorated with @runtime_checkable so isinstance "
        "works for adapter discovery and orchestrator wiring."
    )


def test_claude_adapter_satisfies_adapter_protocol() -> None:
    """The concrete ClaudeAdapter from 04-02 must pass isinstance(_, Adapter).

    This is the canary -- if structural typing breaks, the orchestrator can't
    route turns and `ultra-claude doctor` can't enumerate adapters.
    """

    assert isinstance(ClaudeAdapter(), Adapter)


def test_duck_typed_object_satisfies_adapter_protocol() -> None:
    """Third-party adapters must NOT need to inherit anything.

    A class declaring `name: str` and an `invoke(prompt, timeout) -> str`
    method should pass isinstance(_, Adapter) by structural subtyping. This
    is the ADP-01 contract: the Protocol IS the public extension point.
    """

    class ThirdPartyAdapter:
        name: str = "third-party"

        def invoke(self, prompt: str, timeout: int) -> str:
            return f"third-party reply to {prompt!r} (timeout={timeout})"

    assert isinstance(ThirdPartyAdapter(), Adapter)


def test_object_missing_invoke_does_not_satisfy_protocol() -> None:
    """A class with `name` but no `invoke` method must FAIL isinstance.

    runtime_checkable Protocols check method PRESENCE (not signatures), so a
    class that has `name` but lacks `invoke` should not pass. This guards
    against the regression where someone accidentally relaxes the Protocol.
    """

    class HalfBaked:
        name: str = "half-baked"

    assert not isinstance(HalfBaked(), Adapter)


# ---------------------------------------------------------------------------
# _SubprocessAdapterMixin shape (ADP-02 partial -- behaviour in claude tests)
# ---------------------------------------------------------------------------


def test_mixin_declares_required_class_attributes() -> None:
    """_SubprocessAdapterMixin must declare cli_name and auth_error_markers
    so concrete adapters know what to populate.

    We check the class annotations rather than instance attributes because
    the mixin itself is abstract -- its instances aren't directly useful;
    only subclasses (ClaudeAdapter, GeminiAdapter, CodexAdapter) populate
    concrete values.
    """

    annotations = _SubprocessAdapterMixin.__annotations__
    assert "cli_name" in annotations, "Mixin must annotate cli_name: str"
    assert "auth_error_markers" in annotations, (
        "Mixin must annotate auth_error_markers: tuple[str, ...]"
    )


def test_claude_adapter_inherits_from_mixin() -> None:
    """ClaudeAdapter must inherit from _SubprocessAdapterMixin so it picks
    up _run_subprocess and the safe-contract enforcement.

    GeminiAdapter and CodexAdapter (Phase 7) will share the same parent
    class -- this test pins the inheritance so a future refactor that
    breaks the chain (and silently drops the safety guards) fails fast.
    """

    assert issubclass(ClaudeAdapter, _SubprocessAdapterMixin)


def test_claude_adapter_populates_required_class_attributes() -> None:
    """ClaudeAdapter must populate the abstract slots declared by the mixin."""

    assert ClaudeAdapter.cli_name == "claude"
    assert isinstance(ClaudeAdapter.auth_error_markers, tuple)
    assert len(ClaudeAdapter.auth_error_markers) >= 1
    # All markers must be plain strings (case-insensitive matching is the
    # mixin's responsibility, but we keep the source values lowercase for
    # readability and grep-ability).
    for marker in ClaudeAdapter.auth_error_markers:
        assert isinstance(marker, str)
        assert marker.strip() == marker, f"marker {marker!r} has whitespace"
