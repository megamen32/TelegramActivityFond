
from easysettings import EasySettings

from SaveFile import SaveFile

_settings = EasySettings("config/settings.conf")
data = SaveFile("data")
data_callbacks=[]
start_callbacks=[]
def startup():
    for callback in start_callbacks:
        callback()
def save():
    _settings.save()
    for callback in data_callbacks:
        callback()
    data.save()

class WrapperSettings():
    def __init__(self,_settings):
        self.dict=_settings
    def __getitem__(self, key):
        return self.dict.get(key)
settings=WrapperSettings(_settings)

#settings = {'TG_TOKEN':'5562991245:AAFdNvbq-DvToESKH5P-DqqsNUF80PMU-fU','START_BALANCE':10.0}

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
