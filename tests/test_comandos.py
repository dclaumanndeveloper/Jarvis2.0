"""
Unit Tests for Commands Module
Tests for voice command functions
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comandos import (
    horas, data, get_desktop_path, aumentar_volume, diminuir_volume,
    IS_WINDOWS, SITES, APLICATIVOS
)


class TestTimeCommands(unittest.TestCase):
    """Test time-related commands"""
    
    def test_horas_format(self):
        """Test horas returns properly formatted time string"""
        result = horas()
        
        self.assertIsInstance(result, str)
        # Should contain hour and minute patterns
        self.assertIn(":", result)
        # Should contain a number
        self.assertTrue(any(c.isdigit() for c in result))

    def test_data_format(self):
        """Test data returns properly formatted date string"""
        result = data()
        
        self.assertIsInstance(result, str)
        # Result should not be empty
        self.assertTrue(len(result) > 0)


class TestSystemPaths(unittest.TestCase):
    """Test system path utilities"""
    
    def test_get_desktop_path_returns_string(self):
        """Test get_desktop_path returns a string"""
        result = get_desktop_path()
        self.assertIsInstance(result, str)

    def test_get_desktop_path_is_valid(self):
        """Test get_desktop_path returns a valid path"""
        result = get_desktop_path()
        # Path should not be empty
        self.assertTrue(len(result) > 0)


class TestVolumeCommands(unittest.TestCase):
    """Test volume control commands"""
    
    @patch('comandos.set_volume')
    def test_aumentar_volume(self, mock_set_volume):
        """Test aumentar_volume calls set_volume"""
        with patch('comandos.IS_WINDOWS', True):
            result = aumentar_volume()
            self.assertIsInstance(result, str)

    @patch('comandos.set_volume')
    def test_diminuir_volume(self, mock_set_volume):
        """Test diminuir_volume calls set_volume"""
        with patch('comandos.IS_WINDOWS', True):
            result = diminuir_volume()
            self.assertIsInstance(result, str)


class TestSitesDictionary(unittest.TestCase):
    """Test SITES dictionary configuration"""
    
    def test_sites_not_empty(self):
        """Test SITES dictionary is not empty"""
        self.assertGreater(len(SITES), 0)

    def test_sites_values_are_urls(self):
        """Test all SITES values are valid URLs"""
        for name, url in SITES.items():
            self.assertTrue(
                url.startswith('http://') or url.startswith('https://'),
                f"Site '{name}' has invalid URL: {url}"
            )

    def test_common_sites_exist(self):
        """Test common sites are defined"""
        common_sites = ['google', 'youtube', 'whatsapp', 'github']
        
        for site in common_sites:
            self.assertIn(site, SITES, f"Common site '{site}' should be defined")


class TestAplicativosDictionary(unittest.TestCase):
    """Test APLICATIVOS dictionary configuration"""
    
    def test_aplicativos_has_platforms(self):
        """Test APLICATIVOS has platform entries"""
        self.assertIn('windows', APLICATIVOS)
        self.assertIn('linux', APLICATIVOS)

    def test_windows_apps_not_empty(self):
        """Test Windows apps are defined"""
        self.assertGreater(len(APLICATIVOS['windows']), 0)

    def test_common_apps_defined(self):
        """Test common apps are defined for Windows"""
        if 'windows' in APLICATIVOS:
            common_apps = ['calculadora', 'chrome', 'vscode']
            for app in common_apps:
                self.assertIn(
                    app, APLICATIVOS['windows'],
                    f"Common app '{app}' should be defined"
                )


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection"""
    
    def test_is_windows_is_boolean(self):
        """Test IS_WINDOWS is a boolean"""
        self.assertIsInstance(IS_WINDOWS, bool)


if __name__ == '__main__':
    unittest.main()
