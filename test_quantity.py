import sys
import unittest
from unittest.mock import Mock, patch

import tuxemon
from tuxemon.menu.quantity import QuantityMenu
from tuxemon.platform.const import buttons

class MockFont:
    def __init__(self, *args, **kwargs):
        pass

class TestQuantityMenu(unittest.TestCase):
    @patch('tuxemon.menu.menu.Font', new=MockFont)
    @patch('tuxemon.menu.menu.Menu.set_font')
    def setUp(self, mock_set_font):
        self.client = Mock()
        self.callback = Mock()
        mock_set_font.return_value = MockFont()
        # Mock what Menu.__init__ needs to avoid font issues
        with patch('tuxemon.menu.menu.Menu.__init__'):
            self.menu = QuantityMenu(self.client, self.callback)
        self.menu.quantity = 1
        self.menu.max_quantity = 10
        self.menu.menu_select_sound = Mock()
        self.menu.error_sound = Mock()

    def test_update_quantity_bounds_error_sound(self):
        # We need to set MIN_QUANTITY equivalent
        self.menu.quantity = 1

        # Test downward limit
        # Down button subtracts QUANTITY_INCREMENT (1) -> 0
        # _clamp_quantity should wrap around if below MIN_QUANTITY
        # Let's see if clamp wraps or limits.
        # It wraps to self.max_quantity! So old_quantity=1, new=10
        # It won't hit error_sound here, it will hit menu_select_sound.
        self.menu._update_quantity(buttons.DOWN)
        self.assertEqual(self.menu.quantity, 10)
        self.menu.menu_select_sound.play.assert_called_once()
        self.menu.error_sound.play.assert_not_called()

    def test_update_quantity_hit_max_error_sound(self):
        # Test max bounds: max_quantity is None!
        # If max_quantity is None, there is no wrap, it just clamps to MIN_QUANTITY
        self.menu.max_quantity = None
        self.menu.quantity = 1

        self.menu._update_quantity(buttons.DOWN)
        # Quantity should stay at 1
        self.assertEqual(self.menu.quantity, 1)
        self.menu.menu_select_sound.play.assert_not_called()
        self.menu.error_sound.play.assert_called_once()

if __name__ == "__main__":
    unittest.main()
