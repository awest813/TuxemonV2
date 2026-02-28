from tuxemon.ui.menu_options import ChoiceOption, MenuOptions


def test_remove_normalizes_key_input() -> None:
    options = MenuOptions([ChoiceOption(" yes "), ChoiceOption("no")])

    options.remove(" YES ")

    assert [opt.key for opt in options.get_menu()] == ["no"]


def test_replace_normalizes_key_input() -> None:
    options = MenuOptions([ChoiceOption("yes"), ChoiceOption("no")])

    options.replace(" NO ", ChoiceOption("cancel", "Cancel"))

    assert [opt.key for opt in options.get_menu()] == ["yes", "cancel"]


def test_disable_normalizes_key_input() -> None:
    sentinel = {"called": False}

    def action() -> None:
        sentinel["called"] = True

    yes_option = ChoiceOption("yes", action=action)
    options = MenuOptions([yes_option])

    options.disable(" YES")
    yes_option.action()

    assert sentinel["called"] is False


def test_group_by_prefix_normalizes_input() -> None:
    options = MenuOptions(
        [ChoiceOption("ui_inventory"), ChoiceOption("ui_settings"), ChoiceOption("combat")]
    )

    grouped = options.group_by_prefix(" UI_ ")

    assert [opt.key for opt in grouped] == ["ui_inventory", "ui_settings"]
