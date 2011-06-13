import sys

__all__ = ('Patatino', 'Default')

class Palatino(object):
    def __init__(self):
        self.name = 'Palatino'
        self.path = self._get_path()
        
    def _get_path(self):
        if sys.platform.find("linux") != -1:
            return '/usr/share/texmf-texlive/fonts/type1/urw/palatino/uplr8a.pfb'
        else:
            return '/usr/local/texlive/2009/texmf-dist/fonts/type1/urw/palatino/uplr8a.pfb'

Default = Palatino