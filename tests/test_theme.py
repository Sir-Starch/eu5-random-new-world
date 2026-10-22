from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QEvent, QSize
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStyle,
    QStyleOption,
    QToolButton,
)

from rnw.gui.theme import contrast_ratio, install

if TYPE_CHECKING:
    from collections.abc import Iterator


def test_contrast_ratio_matches_wcag_reference_colors() -> None:
    assert contrast_ratio(QColor("#000000"), QColor("#ffffff")) == pytest.approx(21.0)


@pytest.fixture
def application() -> Iterator[QApplication]:
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication([])
    original_palette = app.palette()
    original_font = app.font()
    install(app)
    yield app
    app.setPalette(original_palette)
    app.setFont(original_font)


def _palette(
    active_colors: tuple[str, str, str, str],
    disabled_backgrounds: tuple[str, str, str],
) -> QPalette:
    palette = QPalette()
    active_window, active_base, active_button, foreground = active_colors
    disabled_window, disabled_base, disabled_button = disabled_backgrounds
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Active, role, QColor(foreground))
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(foreground))
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Window, QColor(active_window))
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Base, QColor(active_base))
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Button, QColor(active_button))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, QColor(disabled_window)
    )
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor(disabled_base))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor(disabled_button)
    )
    return palette


@pytest.mark.parametrize(
    "palette",
    [
        _palette(
            ("#f5f5f5", "#ffffff", "#eeeeee", "#777777"),
            ("#e8e8e8", "#e2e2e2", "#dddddd"),
        ),
        _palette(
            ("#171717", "#101010", "#202020", "#888888"),
            ("#292929", "#303030", "#353535"),
        ),
    ],
    ids=("light-palette", "dark-palette"),
)
def test_disabled_text_meets_contrast_without_changing_active_colors(
    application: QApplication, palette: QPalette
) -> None:
    active_before = {
        role: palette.color(QPalette.ColorGroup.Active, role)
        for role in (
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText,
        )
    }
    backgrounds = {
        foreground: palette.color(QPalette.ColorGroup.Disabled, background)
        for foreground, background in (
            (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
            (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
            (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
        )
    }

    application.setPalette(palette)
    actual = application.palette()

    for foreground, background in (
        (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
        (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
        (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    ):
        disabled_text = actual.color(QPalette.ColorGroup.Disabled, foreground)
        assert contrast_ratio(disabled_text, backgrounds[foreground]) >= 4.5
        assert actual.color(QPalette.ColorGroup.Active, foreground) == active_before[foreground]
        assert actual.color(QPalette.ColorGroup.Disabled, background) == backgrounds[foreground]


def test_disabled_text_stays_distinct_from_high_contrast_active_text(
    application: QApplication,
) -> None:
    palette = _palette(
        ("#ffffff", "#ffffff", "#ffffff", "#000000"),
        ("#ffffff", "#ffffff", "#ffffff"),
    )
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#eeeeee"))
    application.setPalette(palette)

    disabled = application.palette().color(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText
    )
    active = application.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText)
    background = application.palette().color(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button
    )

    assert contrast_ratio(disabled, background) >= 4.5
    assert disabled != active


def test_install_is_idempotent_and_applies_a_later_palette_change(
    application: QApplication,
) -> None:
    installed_style = application.style()
    install(application)
    assert application.style() is installed_style

    changed = _palette(
        ("#f0f0f0", "#ffffff", "#e5e5e5", "#666666"),
        ("#dddddd", "#d5d5d5", "#cccccc"),
    )
    application.setPalette(changed)

    palette = application.palette()
    for foreground, background in (
        (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
        (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
        (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    ):
        assert (
            contrast_ratio(
                palette.color(QPalette.ColorGroup.Disabled, foreground),
                palette.color(QPalette.ColorGroup.Disabled, background),
            )
            >= 4.5
        )


def test_theme_change_preserves_the_current_active_palette(application: QApplication) -> None:
    palette = _palette(
        ("#27384a", "#34495e", "#425a70", "#d8e7f2"),
        ("#1b2734", "#202e3d", "#263747"),
    )
    active_before = {
        role: palette.color(QPalette.ColorGroup.Active, role)
        for role in (
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText,
        )
    }
    application.setPalette(palette)

    _ = QApplication.sendEvent(application, QEvent(QEvent.Type.ThemeChange))

    actual = application.palette()
    for foreground, background in (
        (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
        (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
        (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    ):
        assert actual.color(QPalette.ColorGroup.Active, foreground) == active_before[foreground]
        assert (
            contrast_ratio(
                actual.color(QPalette.ColorGroup.Disabled, foreground),
                actual.color(QPalette.ColorGroup.Disabled, background),
            )
            >= 4.5
        )


def test_controls_follow_font_metrics_and_keep_the_application_style(
    application: QApplication,
) -> None:
    font = QFont("Sans Serif", 20)
    controls = (
        QPushButton("Action"),
        QToolButton(),
        QComboBox(),
        QLineEdit(),
        QSpinBox(),
        QDoubleSpinBox(),
        QCheckBox("Option"),
        QRadioButton("Choice"),
    )
    dialog = QDialog()
    dialog_button = QPushButton("Dialog action", dialog)
    for control in (*controls, dialog_button):
        control.setFont(font)
        control.ensurePolished()
        assert control.style() is application.style()
        assert control.sizeHint().height() >= max(32, control.fontMetrics().height() + 14)


def test_control_size_hook_accepts_a_valid_option_without_a_widget(
    application: QApplication,
) -> None:
    option = QStyleOption()
    size = application.style().sizeFromContents(
        QStyle.ContentsType.CT_PushButton, option, QSize(10, 10), None
    )

    assert size.height() >= max(32, option.fontMetrics.height() + 14)
