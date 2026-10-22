from __future__ import annotations

from typing import Final, override

from PySide6.QtCore import QEvent, QObject, QSize
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleOption, QWidget

_MIN_CONTROL_HEIGHT: Final = 32
_CONTROL_PADDING: Final = 14
_MIN_CONTRAST: Final = 4.5
_SRGB_THRESHOLD: Final = 0.04045
_COLOR_PAIRS: Final = (
    (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
    (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
)
_CONTROL_CONTENT_TYPES: Final = frozenset(
    (
        QStyle.ContentsType.CT_PushButton,
        QStyle.ContentsType.CT_CheckBox,
        QStyle.ContentsType.CT_RadioButton,
        QStyle.ContentsType.CT_ToolButton,
        QStyle.ContentsType.CT_ComboBox,
        QStyle.ContentsType.CT_LineEdit,
        QStyle.ContentsType.CT_SpinBox,
    )
)
_PALETTE_EVENTS: Final = frozenset(
    (
        QEvent.Type.ApplicationPaletteChange,
        QEvent.Type.PaletteChange,
        QEvent.Type.ThemeChange,
    )
)


def contrast_ratio(foreground: QColor, background: QColor) -> float:
    foreground_luminance = _luminance(foreground)
    background_luminance = _luminance(background)
    lighter, darker = sorted((foreground_luminance, background_luminance), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(color: QColor) -> float:
    channels = (color.redF(), color.greenF(), color.blueF())
    linear = tuple(
        channel / 12.92 if channel <= _SRGB_THRESHOLD else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    )
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _mix(source: QColor, target: QColor, amount: float) -> QColor:
    inverse = 1.0 - amount
    return QColor.fromRgbF(
        source.redF() * inverse + target.redF() * amount,
        source.greenF() * inverse + target.greenF() * amount,
        source.blueF() * inverse + target.blueF() * amount,
    )


def _accessible_disabled_color(source: QColor, background: QColor) -> QColor:
    target = source
    if contrast_ratio(source, background) < _MIN_CONTRAST:
        dark = QColor(0, 0, 0)
        light = QColor(255, 255, 255)
        target = (
            dark if contrast_ratio(dark, background) >= contrast_ratio(light, background) else light
        )
    low = 0.0
    high = 1.0
    for _ in range(24):
        middle = (low + high) / 2.0
        if contrast_ratio(_mix(background, target, middle), background) >= _MIN_CONTRAST:
            high = middle
        else:
            low = middle
    result = _mix(background, target, high)
    if contrast_ratio(result, background) >= _MIN_CONTRAST:
        return result
    return target


def _normalize_palette(palette: QPalette) -> None:
    for foreground_role, background_role in _COLOR_PAIRS:
        background = palette.color(QPalette.ColorGroup.Disabled, background_role)
        current = palette.color(QPalette.ColorGroup.Disabled, foreground_role)
        if contrast_ratio(current, background) < _MIN_CONTRAST:
            source = palette.color(QPalette.ColorGroup.Active, foreground_role)
            palette.setColor(
                QPalette.ColorGroup.Disabled,
                foreground_role,
                _accessible_disabled_color(source, background),
            )


class _PaletteChangeFilter(QObject):
    def __init__(self, application: QApplication) -> None:
        super().__init__(application)
        self._application: QApplication = application
        self._updating: bool = False

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        del watched
        if event.type() in _PALETTE_EVENTS:
            self.apply_palette(self._application.palette())
        return False

    def apply_palette(self, palette: QPalette) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            normalized = QPalette(palette)
            _normalize_palette(normalized)
            if normalized != self._application.palette():
                self._application.setPalette(normalized)
        finally:
            self._updating = False


class _ControlStyle(QProxyStyle):
    def __init__(self, base_style: QStyle, application: QApplication) -> None:
        super().__init__(base_style)
        self._application: QApplication = application
        self._palette_filter: _PaletteChangeFilter | None = None

    @override
    def sizeFromContents(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption,
        size: QSize,
        widget: QWidget,
    ) -> QSize:
        measured = super().sizeFromContents(contents_type, option, size, widget)
        if contents_type not in _CONTROL_CONTENT_TYPES:
            return measured
        minimum = max(_MIN_CONTROL_HEIGHT, option.fontMetrics.height() + _CONTROL_PADDING)
        return QSize(measured.width(), max(measured.height(), minimum))

    def attach_palette_filter(self) -> None:
        if self._palette_filter is None:
            self._palette_filter = _PaletteChangeFilter(self._application)
            self._application.installEventFilter(self._palette_filter)
        self._palette_filter.apply_palette(self._application.palette())


def install(application: QApplication) -> None:
    style = application.style()
    if isinstance(style, _ControlStyle):
        style.attach_palette_filter()
        return
    normalized = _ControlStyle(style, application)
    application.setStyle(normalized)
    normalized.attach_palette_filter()
