from domain.shared import ValueObject


class NsfwFilter(ValueObject):
    def __init__(self, enabled: bool = False):
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_disabled(self) -> bool:
        return not self._enabled

    def toggle(self) -> "NsfwFilter":
        return NsfwFilter(not self._enabled)

    def enable(self) -> "NsfwFilter":
        return NsfwFilter(True)

    def disable(self) -> "NsfwFilter":
        return NsfwFilter(False)

    def _equality_components(self) -> tuple:
        return (self._enabled,)

    def __bool__(self) -> bool:
        return self._enabled
